# Feature Store Pattern — Sparc Energy Load Forecasting

**Module:** `src/energy_forecast/features/temporal.py`
**Public API:** `build_temporal_features(df, cfg, target) → pd.DataFrame`
**Feature count:** 35 (H+24 production configuration)
**Status:** Production — v0.9.0

---

## What This Is

A feature store pattern formalises how raw data is transformed into model-ready features, with guarantees around:
- **Leakage prevention** — no future data can leak into training or inference
- **Reproducibility** — same config produces same features, always
- **Discoverability** — every feature has a documented source and rationale
- **Governance** — feature pipeline is auditable (required for EU AI Act Art. 52)

The Sparc Energy feature pipeline is config-driven, building-isolated, and oracle-safe by design. It is the single source of truth for all models (LightGBM, Stacking Ensemble, quantile models).

---

## Input Schema

```
MultiIndex DataFrame: (building_id, timestamp)
Required columns:
  - <target>            : hourly electricity consumption (kWh)
  - Temperature_Outdoor_C : outdoor temperature
Optional columns:
  - hour_of_day, day_of_week, month, day_of_year  (cyclical encoding sources)
```

---

## Feature Groups

### Group 1: Cyclical Time Encoding (8 features)

Encodes periodic time variables as sin/cos pairs to preserve circular continuity (hour 23 is adjacent to hour 0).

| Feature | Formula | Period | Rationale |
|---------|---------|--------|-----------|
| `hour_of_day_sin` | sin(2π × hour / 24) | 24h | Morning demand ramp |
| `hour_of_day_cos` | cos(2π × hour / 24) | 24h | Morning demand ramp |
| `day_of_week_sin` | sin(2π × dow / 7) | 7d | Weekday/weekend occupancy |
| `day_of_week_cos` | cos(2π × dow / 7) | 7d | Weekday/weekend occupancy |
| `month_sin` | sin(2π × month / 12) | 12mo | Seasonal heating demand |
| `month_cos` | cos(2π × month / 12) | 12mo | Seasonal heating demand |
| `day_of_year_sin` | sin(2π × doy / 365) | 365d | Annual cycle |
| `day_of_year_cos` | cos(2π × doy / 365) | 365d | Annual cycle |

**Config key:** `features.cyclical`

---

### Group 2: Interaction Features (5 features)

Captures non-linear relationships that cyclical + temperature features alone cannot express.

| Feature | Formula | Rationale |
|---------|---------|-----------|
| `temp_x_hour_sin` | Temperature_Outdoor_C × hour_of_day_sin | Cold mornings → amplified heating demand ramp |
| `temp_x_hour_cos` | Temperature_Outdoor_C × hour_of_day_cos | Cold mornings → amplified heating demand ramp |
| `Is_Weekend` | 1 if day_of_week ≥ 5 else 0 | Binary occupancy signal |
| `temp_x_is_weekend` | Temperature_Outdoor_C × Is_Weekend | Cold weekends → different heating profile vs cold weekdays |

Note: SHAP analysis confirms `temp_x_hour_sin` and `temp_x_hour_cos` are in the top 5 features by importance for all buildings.

---

### Group 3: Lag Features (variable — 18 in H+24 config)

Historical values of target and temperature, shifted to be oracle-safe. Applied **per building** to prevent cross-building data leakage.

**Oracle-safe rule (ADR-003):** Only lags ≥ `forecast_horizon` are included. For H+24 production: lags {24, 25, 26, 48, 168} hours.

| Feature pattern | Example | Rationale |
|----------------|---------|-----------|
| `<target>_lag_<N>h` | `energy_lag_24h` | Same hour yesterday |
| `<target>_lag_<N>h` | `energy_lag_168h` | Same hour last week |
| `Temperature_Outdoor_C_lag_<N>h` | `Temperature_Outdoor_C_lag_24h` | Yesterday's temperature at this hour |

**Removed at H+24:** lags {1, 2, 3} hours — these would use future data at prediction time and are excluded with a logged warning.

**Config key:** `features.lag_windows`

---

### Group 4: Rolling Window Statistics (variable — ~24 in H+24 config)

Rolling mean, std, min, max over historical windows. Applied per building with `shift(1)` to exclude the current timestep from its own rolling window (prevents subtle target leakage).

**Oracle-safe rule:** Only rolling windows ≥ `forecast_horizon` are included. For H+24: windows {24, 72, 168} hours.

| Feature pattern | Example | Rationale |
|----------------|---------|-----------|
| `<col>_roll_<W>h_mean` | `energy_roll_24h_mean` | Average load over last 24h |
| `<col>_roll_<W>h_std` | `energy_roll_168h_std` | Load variability over last week |
| `<col>_roll_<W>h_min` | `energy_roll_72h_min` | Minimum load — captures baseline |
| `<col>_roll_<W>h_max` | `energy_roll_24h_max` | Peak demand signal |

**Config keys:** `features.rolling_windows`, `features.rolling_stats`

---

## Leakage Prevention — Summary

| Mechanism | Implementation | Verified by |
|-----------|---------------|-------------|
| Oracle-safe lag enforcement | `lag_windows = [w for w in all_lags if w >= horizon]` | ADR-003, assertion in config guard |
| Oracle-safe rolling enforcement | `roll_windows = [w for w in all_rolls if w >= horizon]` | temporal.py line 126 |
| Current-timestep exclusion in rolling | `group[col].shift(1).rolling(w)` | temporal.py line 201 |
| Per-building isolation | `groupby(level="building_id").apply(...)` | temporal.py line 121, 138 |
| Config guard assertion | `assert feat_horizon == seq_horizon` | temporal.py line 73 |

---

## Config Reference

```yaml
# config/config.yaml — features section
features:
  forecast_horizon: 24          # H+24 production — controls lag/rolling cutoff
  cyclical:
    - hour_of_day
    - day_of_week
    - month
    - day_of_year
  lag_windows: [1, 2, 3, 24, 25, 26, 48, 168]   # 1/2/3 removed at H+24
  rolling_windows: [3, 6, 12, 24, 72, 168]        # 3/6/12 removed at H+24
  rolling_stats: [mean, std, min, max]
```

---

## Extending the Feature Store

When adding new features, follow this checklist:

- [ ] Is the feature oracle-safe? (only uses data available at prediction time t-24h or earlier)
- [ ] Is it applied per-building? (use `groupby(level="building_id").apply(...)`)
- [ ] Is it documented in this file under the correct group?
- [ ] Is SHAP importance checked post-training? (remove if importance < 0.5% after 3 training runs)
- [ ] Is the config key documented?

---

## Usage

```python
from energy_forecast.features.temporal import build_temporal_features
from energy_forecast.utils.config import load_config

cfg = load_config("config/config.yaml")
df_features = build_temporal_features(df_raw, cfg, target="energy_kwh")
# Returns: 35-column DataFrame (H+24 config), NaN warmup rows dropped
```

---

## Related Files

| File | Purpose |
|------|---------|
| `src/energy_forecast/features/temporal.py` | Implementation |
| `config/config.yaml` | All feature parameters |
| `docs/adr/ADR-003-oracle-safe-features.md` | Design decision — why lag ≥ 24h |
| `docs/governance/DATA_LINEAGE.md` | Where features sit in the 8-stage pipeline |
