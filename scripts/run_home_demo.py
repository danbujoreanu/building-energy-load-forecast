#!/usr/bin/env python3
"""
run_home_demo.py — Personal Home Energy Analysis
================================================
Loads an ESB Networks HDF CSV export, trains a LightGBM forecast model
on the household's own consumption history, and produces a 24-hour
demand-response schedule using the actual Bord Gáis Energy tariff.

Usage:
    python scripts/run_home_demo.py --csv <path_to_esb_hdf.csv> [--city kildare]

Output:
    - outputs/results/home_forecast.csv   — hourly forecast for next 24h
    - outputs/results/home_schedule.json  — demand-response schedule
    - Console: morning brief with euro savings
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from energy_forecast.tariff import BGE as BGE_TARIFF, rate_for_slot  # noqa: E402

MAYNOOTH_COORDS = {"lat": 53.382, "lon": -6.593}  # Co Kildare


def load_esb_csv(path: str) -> pd.DataFrame:
    """Load ESB HDF CSV and return hourly import + export series."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["Read Date and End Time"], dayfirst=True)
    df = df.sort_values("timestamp")

    # Pivot to wide format (timestamp × read_type) before combining
    df["read_type_short"] = df["Read Type"].map({
        "Active Import Interval (kWh)": "import_kwh",
        "Active Export Interval (kWh)":  "export_kwh",
    })
    wide = (df.dropna(subset=["read_type_short"])
              .groupby(["timestamp", "read_type_short"])["Read Value"]
              .sum()
              .unstack(fill_value=0)
              .rename_axis(None, axis=1))
    # Ensure both columns exist
    for col in ("import_kwh", "export_kwh"):
        if col not in wide.columns:
            wide[col] = 0.0
    combined = wide
    hourly = combined.resample("1h").sum()
    hourly.index = hourly.index.tz_localize("Europe/Dublin", ambiguous="NaT",
                                            nonexistent="shift_forward")
    hourly = hourly[hourly.index.notna()]
    logger.info("Loaded %d hourly rows | %s → %s",
                len(hourly), hourly.index.min().date(), hourly.index.max().date())
    return hourly


def fetch_weather(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Fetch hourly temperature + solar from Open-Meteo archive/forecast.

    Splits request: archive endpoint for historical, forecast endpoint for future.
    """
    import urllib.request
    from datetime import date, timedelta

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    def _fetch_chunk(url: str) -> pd.DataFrame | None:
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read())
            times = pd.to_datetime(data["hourly"]["time"])
            df = pd.DataFrame({
                "temperature": data["hourly"]["temperature_2m"],
                "solar_wh_m2": data["hourly"]["shortwave_radiation"],
            }, index=times)
            df.index = df.index.tz_localize("Europe/Dublin", ambiguous="NaT",
                                             nonexistent="shift_forward")
            df = df[df.index.notna()]
            return df
        except Exception as e:
            logger.warning("Weather chunk failed (%s): %s", url[:80], e)
            return None

    chunks = []

    # Historical chunk (archive endpoint) — start → yesterday
    if start <= yesterday:
        hist_end = min(yesterday, end)
        arch_url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,shortwave_radiation"
            f"&timezone=Europe%2FDublin"
            f"&start_date={start}&end_date={hist_end}"
        )
        logger.info("Fetching archive weather: %s to %s", start, hist_end)
        chunk = _fetch_chunk(arch_url)
        if chunk is not None:
            chunks.append(chunk)

    # Forecast chunk (forecast endpoint) — today → end
    if end >= today:
        fc_start = max(today, start)
        fc_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,shortwave_radiation"
            f"&timezone=Europe%2FDublin"
            f"&start_date={fc_start}&end_date={end}"
        )
        logger.info("Fetching forecast weather: %s to %s", fc_start, end)
        chunk = _fetch_chunk(fc_url)
        if chunk is not None:
            chunks.append(chunk)

    if chunks:
        wdf = pd.concat(chunks).sort_index()
        wdf = wdf[~wdf.index.duplicated(keep="first")]
        return wdf

    logger.warning("All weather fetches failed — using zeros")
    idx = pd.date_range(start, end, freq="1h", tz="Europe/Dublin")
    return pd.DataFrame({"temperature": 10.0, "solar_wh_m2": 0.0}, index=idx)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add temporal + lag features for a single-building residential series."""
    df = df.copy()
    df["hour"] = df.index.hour
    df["dayofweek"] = df.index.dayofweek
    df["month"] = df.index.month
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["is_saturday"] = (df["dayofweek"] == 5).astype(int)

    for lag in [1, 2, 3, 6, 12, 24, 48, 168]:
        df[f"lag_{lag}h"] = df["import_kwh"].shift(lag)

    for w in [6, 24, 48, 168]:
        df[f"rolling_mean_{w}h"] = df["import_kwh"].shift(1).rolling(w, min_periods=1).mean()
        df[f"rolling_std_{w}h"]  = df["import_kwh"].shift(1).rolling(w, min_periods=1).std()

    # Tariff signal features (helps model learn free-Saturday pattern)
    df["rate_day"]  = df.index.map(lambda t: rate_for_slot(t)[1])
    df["is_free"]   = (df["rate_day"] == 0).astype(int)
    df["is_peak"]   = df.index.map(lambda t: 1 if 17 <= t.hour < 19 and t.weekday() < 5 else 0)
    df["is_night"]  = df.index.map(lambda t: 1 if t.hour >= 23 or t.hour < 8 else 0)

    df.dropna(inplace=True)
    return df


def train_lgbm(df: pd.DataFrame) -> tuple:
    """Train LightGBM on 90% of data, return (model, feature_cols, scaler)."""
    from lightgbm import LGBMRegressor

    feature_cols = [c for c in df.columns if c not in
                    ("import_kwh", "export_kwh", "temperature", "solar_wh_m2")]
    # Add weather if available
    for wc in ("temperature", "solar_wh_m2"):
        if wc in df.columns:
            feature_cols.append(wc)

    split_idx = int(len(df) * 0.90)
    X_train = df[feature_cols].iloc[:split_idx]
    y_train = df["import_kwh"].iloc[:split_idx]
    X_test  = df[feature_cols].iloc[split_idx:]
    y_test  = df["import_kwh"].iloc[split_idx:]

    model = LGBMRegressor(n_estimators=500, learning_rate=0.05,
                          num_leaves=63, min_child_samples=20,
                          subsample=0.8, colsample_bytree=0.8,
                          random_state=42, verbose=-1)
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              callbacks=[])

    test_pred = model.predict(X_test)
    mae  = np.mean(np.abs(test_pred - y_test.values))
    rmse = np.sqrt(np.mean((test_pred - y_test.values) ** 2))
    r2   = 1 - np.sum((test_pred - y_test.values) ** 2) / np.sum((y_test.values - y_test.mean()) ** 2)
    logger.info("Hold-out eval  MAE=%.4f kWh | RMSE=%.4f | R²=%.4f", mae, rmse, r2)

    return model, feature_cols, mae


def build_schedule(forecast_df: pd.DataFrame) -> list[dict]:
    """Produce hourly demand-response decisions given forecast + tariff."""
    decisions = []
    for ts, row in forecast_df.iterrows():
        rate_name, rate_eur = rate_for_slot(ts)
        kwh = max(row["p50_kwh"], 0)
        solar = row.get("solar_wh_m2", 0)
        cost  = kwh * rate_eur

        if rate_name == "free":
            action = "RUN_NOW"
            reason = "Free Saturday window — run all shiftable loads now (0 c/kWh)"
            saving = kwh * BGE_TARIFF["day"]  # vs day rate counterfactual
        elif rate_name == "night":
            action = "RUN_NOW"
            reason = f"Night rate {BGE_TARIFF['night']*100:.1f} c/kWh — cheapest grid window"
            saving = kwh * (BGE_TARIFF["day"] - BGE_TARIFF["night"])
        elif rate_name == "peak":
            action = "DEFER"
            reason = f"Peak rate {BGE_TARIFF['peak']*100:.1f} c/kWh — defer to night or next Saturday"
            saving = kwh * (BGE_TARIFF["peak"] - BGE_TARIFF["night"])
        elif solar > 150:
            action = "RUN_NOW"
            reason = f"Solar {solar:.0f} W/m² — self-generation covers likely load"
            saving = kwh * BGE_TARIFF["export"]  # avoid export, use self-gen
        else:
            action = "NORMAL"
            reason = f"Day rate {BGE_TARIFF['day']*100:.1f} c/kWh — standard window"
            saving = 0.0

        decisions.append({
            "hour": ts.strftime("%H:%M"),
            "day":  ts.strftime("%a"),
            "action": action,
            "rate": rate_name,
            "rate_eur_kwh": round(rate_eur, 4),
            "p50_kwh": round(kwh, 3),
            "cost_eur": round(cost, 4),
            "saving_vs_peak_eur": round(saving, 4),
        })
    return decisions


def fetch_eddi_status() -> dict | None:
    """Fetch live Eddi status if credentials are available (non-fatal)."""
    import os, sys
    serial  = os.environ.get("MYENERGI_SERIAL", "")
    api_key = os.environ.get("MYENERGI_API_KEY", "")
    if not serial or not api_key:
        return None
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "deployment"))
        from connectors import MyEnergiConnector
        c = MyEnergiConnector(serial=serial, api_key=api_key)
        return c.get_status()
    except Exception as e:
        logger.warning("Eddi status unavailable: %s", e)
        return None


def morning_brief(decisions: list[dict], mae: float,
                  eddi: dict | None = None) -> str:
    """Format a human-readable morning brief."""
    lines = ["=" * 65,
             "  ENERGY MORNING BRIEF — YOUR HOME (Maynooth, Co Kildare)",
             "  Bord Gáis Energy 'Free Time Saturday' tariff",
             f"  Model MAE: ±{mae:.3f} kWh/hour",
             "=" * 65]

    # Live Eddi block
    if eddi:
        mode_icon = {"diverting_solar": "☀", "paused": "—",
                     "boost": "↑", "boosting_grid": "↑"}.get(eddi["mode"], "?")
        lines.append(f"  Eddi now:  {mode_icon} {eddi['mode']}  "
                     f"{eddi['diverted_w']}W → tank  |  "
                     f"grid {'+' if eddi['grid_w'] >= 0 else ''}{eddi['grid_w']}W  |  "
                     f"today {eddi['today_kwh']} kWh diverted")
        if eddi.get("solar_lower_w", 0) > 0:
            lines.append(f"  Solar est: ≥{eddi['solar_lower_w']}W (Eddi div − grid import)")
        lines.append("")

    total_cost   = sum(d["cost_eur"] for d in decisions)
    total_saving = sum(d["saving_vs_peak_eur"] for d in decisions)

    lines.append(f"  Forecast period: {decisions[0]['day']} {decisions[0]['hour']} "
                 f"→ {decisions[-1]['day']} {decisions[-1]['hour']}")
    lines.append(f"  Est. electricity cost:  €{total_cost:.2f}")
    lines.append(f"  Est. saving (vs flat):  €{total_saving:.2f}")
    lines.append("")

    for d in decisions:
        icon = {"RUN_NOW": "✓", "DEFER": "↓", "NORMAL": "·"}[d["action"]]
        lines.append(f"  {d['day']} {d['hour']}  {icon} {d['action']:<8}  "
                     f"{d['rate']:<6}  {d['rate_eur_kwh']*100:.1f}c  "
                     f"~{d['p50_kwh']:.2f} kWh  save €{d['saving_vs_peak_eur']:.3f}")

    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to ESB HDF CSV file")
    parser.add_argument("--horizon", type=int, default=24)
    args = parser.parse_args()

    out_dir = Path("outputs/results")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Load ESB data ──────────────────────────────────────────
    hourly = load_esb_csv(args.csv)

    # ── 2. Fetch weather for full history + forecast horizon ──────
    hist_start = hourly.index.min().date().isoformat()
    from datetime import date, timedelta
    today      = date.today()
    fc_end     = (today + timedelta(days=2)).isoformat()
    weather    = fetch_weather(MAYNOOTH_COORDS["lat"], MAYNOOTH_COORDS["lon"],
                               hist_start, fc_end)

    # Align weather to hourly
    combined = hourly.join(weather, how="left")
    combined["temperature"] = combined["temperature"].ffill().bfill()
    combined["solar_wh_m2"] = combined["solar_wh_m2"].fillna(0)

    # ── 3. Build features & train ────────────────────────────────
    featured = build_features(combined)
    logger.info("Training on %d hourly rows (%s → %s)",
                len(featured), featured.index.min().date(), featured.index.max().date())
    model, feature_cols, mae = train_lgbm(featured)

    # ── 4. Forecast next 24h ────────────────────────────────────
    # Always forecast from the current hour, not from last data point.
    # Lag features are filled from historical data regardless of when it ends.
    import pytz
    now_dublin = pd.Timestamp.now(tz="Europe/Dublin").floor("1h")
    fc_index = pd.date_range(now_dublin, periods=args.horizon, freq="1h",
                             tz="Europe/Dublin")

    # Build forecast feature rows by carrying last known row forward
    fc_rows = []
    for ts in fc_index:
        row = {}
        row["hour"]        = ts.hour
        row["dayofweek"]   = ts.dayofweek
        row["month"]       = ts.month
        row["is_weekend"]  = int(ts.dayofweek >= 5)
        row["is_saturday"] = int(ts.dayofweek == 5)
        row["rate_day"]    = rate_for_slot(ts)[1]
        row["is_free"]     = int(row["rate_day"] == 0)
        row["is_peak"]     = int(17 <= ts.hour < 19 and ts.weekday() < 5)
        row["is_night"]    = int(ts.hour >= 23 or ts.hour < 8)
        # Lags from known history
        for lag in [1, 2, 3, 6, 12, 24, 48, 168]:
            ref = ts - pd.Timedelta(f"{lag}h")
            if ref in featured.index:
                row[f"lag_{lag}h"] = featured.at[ref, "import_kwh"]
            else:
                row[f"lag_{lag}h"] = featured["import_kwh"].iloc[-1]
        for w in [6, 24, 48, 168]:
            row[f"rolling_mean_{w}h"] = featured["import_kwh"].iloc[-w:].mean()
            row[f"rolling_std_{w}h"]  = featured["import_kwh"].iloc[-w:].std()
        # Weather
        if ts in weather.index:
            row["temperature"] = weather.at[ts, "temperature"]
            row["solar_wh_m2"] = weather.at[ts, "solar_wh_m2"]
        else:
            row["temperature"] = 10.0
            row["solar_wh_m2"] = 0.0
        fc_rows.append(row)

    fc_df    = pd.DataFrame(fc_rows, index=fc_index)
    fc_X     = fc_df[[c for c in feature_cols if c in fc_df.columns]]
    fc_preds = model.predict(fc_X).clip(min=0)

    forecast_df = pd.DataFrame({
        "p50_kwh":    fc_preds,
        "solar_wh_m2": fc_df.get("solar_wh_m2", 0).values,
        "temperature": fc_df.get("temperature", 10).values,
    }, index=fc_index)

    # ── 5. Build demand-response schedule ───────────────────────
    decisions = build_schedule(forecast_df)
    eddi_status = fetch_eddi_status()
    brief = morning_brief(decisions, mae, eddi=eddi_status)
    print("\n" + brief)

    # ── 6. Save outputs ─────────────────────────────────────────
    forecast_df.to_csv(out_dir / "home_forecast.csv")
    with open(out_dir / "home_schedule.json", "w") as f:
        json.dump({"tariff": "BGE Free Time Saturday",
                   "location": "Maynooth, Co Kildare",
                   "mae_kwh": round(mae, 4),
                   "decisions": decisions}, f, indent=2)
    logger.info("Outputs saved → outputs/results/home_forecast.csv + home_schedule.json")


if __name__ == "__main__":
    main()
