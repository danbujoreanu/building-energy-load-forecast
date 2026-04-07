"""
deployment.live_inference
==========================
Morning brief script — probabilistic H+24 forecast + demand-response actions.

This standalone script chains together:
  1. CSVConnector      — last 72h of historical load from processed parquet
  2. OpenMeteoConnector — next-24h solar irradiance + temperature forecast
  3. Feature engineering (temporal.py) + scaler
  4. LightGBM model    — P10 / P50 / P90 point predictions
  5. ControlEngine     — per-hour demand-response decisions
  6. MockDeviceConnector — logs recommended actions (dry-run safe)

Usage
-----
    # Dry-run with mock data (no live API calls, no device commands):
    python deployment/live_inference.py --city drammen --dry-run

    # Live weather forecast for Dublin + mock load history:
    python deployment/live_inference.py --city drammen --location dublin

    # Specific hours only (e.g., morning water-heating window):
    python deployment/live_inference.py --city drammen --hours 6 7 8 --dry-run

    # Specific building from processed parquet:
    python deployment/live_inference.py --city drammen --building-id B001

AWS Conference Demo
-------------------
    python deployment/live_inference.py --dry-run
    # → prints P10/P50/P90 for each hour + recommended eddi action

Requirements
------------
    pip install -e ".[all]"       (full research env)
    OR
    pip install -r deployment/requirements.txt   (lightweight inference env)
"""

from __future__ import annotations

import argparse
import logging
import math
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup (works whether run from repo root or deployment/) ──────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ── Project imports ───────────────────────────────────────────────────────────
from energy_forecast.control.actions import EnvironmentState, ForecastBundle
from energy_forecast.control.controller import ControlEngine
from energy_forecast.utils.config import load_config

from deployment.connectors import (
    CSVConnector,
    MockDeviceConnector,
    MockPriceConnector,
    OpenMeteoConnector,
)
from deployment.mock_data import MOCK_SOLAR_24H

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("live_inference")

# ---------------------------------------------------------------------------
# Mock data helpers (for --dry-run mode)
# ---------------------------------------------------------------------------

def _mock_historical_df(n_hours: int = 72) -> pd.DataFrame:
    """Generate a plausible 72h load + weather history for demo mode."""
    rng = np.random.default_rng(42)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    idx = pd.date_range(end=now, periods=n_hours, freq="h", tz="UTC")

    hours = idx.hour
    base_load = 15 + 20 * np.exp(-((hours - 8) ** 2) / 18) + 25 * np.exp(-((hours - 17) ** 2) / 10)
    noise = rng.normal(0, 2, n_hours)
    temperature = 10 + 5 * np.sin(2 * np.pi * hours / 24) + rng.normal(0, 0.5, n_hours)

    df = pd.DataFrame(
        {
            "Electricity_Imported_Total_kWh": np.clip(base_load + noise, 5, 80),
            "Temperature_Outdoor_C": temperature,
            "Global_Solar_Horizontal_Radiation_W_m2": [
                MOCK_SOLAR_24H[h % 24] + rng.uniform(-10, 10) for h in hours
            ],
            "hour_of_day": hours,
            "day_of_week": idx.dayofweek,
            "day_of_year": idx.dayofyear,
            "month": idx.month,
            "is_weekend": (idx.dayofweek >= 5).astype(int),
        },
        index=idx,
    )
    return df


# ---------------------------------------------------------------------------
# Feature engineering (inference-time, no fitting)
# ---------------------------------------------------------------------------

def _build_inference_features(
    history_df: pd.DataFrame,
    cfg: dict,
    scaler_path: Path | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Build lag/rolling features from raw history and apply saved scaler.

    Only uses lags >= forecast_horizon to prevent oracle leakage (mirrors
    the training feature engineering in temporal.py).

    Returns (X_scaled_df, feature_names).
    """
    from energy_forecast.features.temporal import build_temporal_features

    target = cfg["data"]["target_column"]
    horizon = cfg["features"]["forecast_horizon"]

    # Wrap in MultiIndex so temporal.py groupby-per-building works
    df = history_df.copy()
    df["building_id"] = "LIVE"
    df = df.set_index(pd.MultiIndex.from_arrays(
        [df["building_id"], df.index], names=["building_id", "timestamp"]
    ))
    df = df.drop(columns=["building_id"], errors="ignore")

    df_feat = build_temporal_features(df, cfg, target=target)

    # Drop NaN rows introduced by lag/rolling
    df_feat = df_feat.dropna()
    if df_feat.empty:
        raise RuntimeError(
            "Feature engineering produced an empty DataFrame. "
            "Ensure history_df has at least 72 rows."
        )

    # Drop non-feature columns
    drop_cols = [target, "building_id", "timestamp"] + [
        c for c in df_feat.columns
        if c in {"building_category", "floor_area", "year_of_construction",
                 "number_of_users", "central_heating_system", "energy_label"}
    ]
    feature_cols = [c for c in df_feat.columns if c not in drop_cols]
    X = df_feat[feature_cols]

    # Apply saved scaler if available
    if scaler_path and scaler_path.exists():
        try:
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
            X_scaled = pd.DataFrame(scaler.transform(X), columns=X.columns, index=X.index)
            logger.info("Scaler applied from %s", scaler_path)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load scaler from {scaler_path}: {exc}. "
                "Re-run run_pipeline.py to regenerate the scaler."
            ) from exc
    else:
        logger.warning("No scaler found at %s — using unscaled features.", scaler_path)
        X_scaled = X

    return X_scaled, feature_cols


# ---------------------------------------------------------------------------
# Main inference loop
# ---------------------------------------------------------------------------

def run_morning_brief(
    city: str = "drammen",
    building_id: str = "B001",
    location: str = "dublin",
    target_hours: list[int] | None = None,
    dry_run: bool = True,
) -> None:
    """Run the full control pipeline and print the morning brief.

    Parameters
    ----------
    city:        Dataset city ("drammen" or "oslo").
    building_id: Building identifier for CSVConnector lookup.
    location:    Named location for OpenMeteoConnector weather fetch.
    target_hours: Which hours to report on (defaults to 6–22).
    dry_run:     If True, use mock data; no live API or device calls.
    """
    if target_hours is None:
        target_hours = list(range(6, 23))

    print(f"\n{'='*60}")
    print(f"  Building Energy Forecast — Morning Brief")
    print(f"  City: {city}  |  Building: {building_id}  |  Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    # ── Load config ────────────────────────────────────────────────────────
    cfg = load_config(Path(REPO_ROOT / "config" / "config.yaml"))

    # ── Step 1: Historical load + weather (last 72h) ────────────────────────
    if dry_run:
        logger.info("DRY-RUN: using mock historical data (72h)")
        history_df = _mock_historical_df(n_hours=72)
    else:
        logger.info("Fetching historical data via CSVConnector for building=%s", building_id)
        connector = CSVConnector(data_dir=REPO_ROOT / "data" / "processed")
        history_df = connector.fetch_last_n_hours(building_id, n_hours=72, city=city)

    # ── Step 2: Solar + temperature forecast (next 24h) ────────────────────
    if dry_run:
        logger.info("DRY-RUN: using mock solar forecast")
        solar_24h = MOCK_SOLAR_24H[:24]
        temp_24h = [10.0] * 24
    else:
        logger.info("Fetching weather forecast via OpenMeteoConnector for %s", location)
        weather = OpenMeteoConnector.for_city(location)
        weather_df = weather.fetch_last_n_hours("_", n_hours=24)
        solar_24h = weather_df["Global_Solar_Horizontal_Radiation_W_m2"].tolist()
        temp_24h = weather_df["Temperature_Outdoor_C"].tolist()

    # ── Step 3: Electricity price signals ─────────────────────────────────
    prices = MockPriceConnector().get_day_ahead_prices()

    # ── Step 4: Feature engineering + model inference ─────────────────────
    scaler_path = REPO_ROOT / "data" / "processed" / "splits" / f"{city}_scaler.pkl"
    model_glob = sorted((REPO_ROOT / "outputs" / "models").glob(f"{city}_LightGBM_*.joblib"))

    if model_glob:
        import joblib
        model_path = model_glob[-1]  # most recent
        model = joblib.load(model_path)
        logger.info("Loaded model from %s", model_path)

        try:
            X_scaled, _ = _build_inference_features(history_df, cfg, scaler_path=scaler_path)
            # Use last row for H+24 prediction
            X_last = X_scaled.iloc[[-1]]
            raw_pred = model.predict(X_last)
            # raw_pred shape: (1,) for single-output or (1, 24) for MultiOutput
            if hasattr(raw_pred[0], "__len__"):
                p50_24h = list(raw_pred[0])
            else:
                # Single-step model: replicate as flat forecast
                p50_24h = [float(raw_pred[0])] * 24
            logger.info("Model inference complete — P50 mean=%.1f kWh", sum(p50_24h) / len(p50_24h))
        except Exception as exc:
            logger.warning("Feature engineering or inference failed (%s) — using mock P50.", exc)
            p50_24h = [25.0 + 10 * math.sin(math.pi * h / 12) for h in range(24)]
    else:
        logger.warning("No LightGBM model found in outputs/models/ — using mock P50.")
        p50_24h = [25.0 + 10 * math.sin(math.pi * h / 12) for h in range(24)]

    # Build simple P10/P90 bounds (±15% of P50 as heuristic without quantile models)
    p10_24h = [max(0.0, v * 0.85) for v in p50_24h]
    p90_24h = [v * 1.15 for v in p50_24h]

    forecast = ForecastBundle(p10=p10_24h, p50=p50_24h, p90=p90_24h)
    env = EnvironmentState(
        solar_forecast_wh_m2=solar_24h,
        grid_price_eur_kwh=prices,
        timestamp=datetime.now(timezone.utc),
        building_id=building_id,
    )

    # ── Step 5: Control decisions ──────────────────────────────────────────
    engine = ControlEngine()
    actions = engine.decide(forecast, env, target_hours=target_hours)

    # ── Step 6: Print brief ────────────────────────────────────────────────
    print(f"  Forecast horizon: {len(p50_24h)} hours")
    print(f"  P50 total (24h): {sum(p50_24h):.1f} kWh")
    print(f"  Solar peak today: {max(solar_24h):.0f} W/m²\n")

    print(f"{'Hour':>6}  {'P10':>7}  {'P50':>7}  {'P90':>7}  {'Solar':>8}  {'Price':>7}  Action")
    print("-" * 75)
    for a in actions:
        h = a.target_hour
        print(
            f"  {h:02d}:00  {p10_24h[h]:6.1f}  {p50_24h[h]:6.1f}  {p90_24h[h]:6.1f}  "
            f"{solar_24h[h]:7.0f}W  {prices[h]:.3f}€  {a.action.value}"
        )

    print()
    print(engine.explain(actions))

    # ── Step 7: Send commands to device (mock) ─────────────────────────────
    device = MockDeviceConnector()
    for a in actions:
        if a.action.value in {"DEFER_HEATING", "ALERT_HIGH_DEMAND"}:
            device.send_command(a.action.value, building_id=building_id)

    print(f"\n  Commands sent to device: {len(device.command_log)}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Building Energy Forecast — Morning Brief + Demand-Response"
    )
    parser.add_argument("--city", default="drammen", choices=["drammen", "oslo"],
                        help="Dataset city (default: drammen)")
    parser.add_argument("--building-id", default="B001",
                        help="Building identifier (default: B001)")
    parser.add_argument("--location", default="dublin",
                        choices=list(OpenMeteoConnector._CITY_COORDS.keys()),
                        help="Location for weather forecast (default: dublin)")
    parser.add_argument("--hours", nargs="+", type=int, default=None,
                        help="Target hours to report on (default: 6–22)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Use mock data — no live API calls (default: True)")
    parser.add_argument("--live", action="store_true",
                        help="Use live data (overrides --dry-run)")
    args = parser.parse_args()

    dry_run = not args.live
    run_morning_brief(
        city=args.city,
        building_id=args.building_id,
        location=args.location,
        target_hours=args.hours,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
