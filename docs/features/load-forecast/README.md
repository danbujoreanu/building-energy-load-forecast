# Feature: Building Load Forecast

**Status:** ✅ Production
**Linear:** DAN-5 to DAN-14, DAN-32, DAN-33
**Owner:** Dan Bujoreanu

---

## Results (Drammen test set, H+24)

| Model | MAE (kWh) | R² | Notes |
|-------|-----------|-----|-------|
| **LightGBM** | **4.03** | **0.975** | Production model |
| Stacking Ensemble | 4.03 | 0.975 | Marginal gain — not deployed |
| PatchTST | 6.96 | 0.910 | DM test: −12.17*** vs LightGBM |
| TFT | 8.77 | 0.865 | |
| Mean Baseline | 22.67 | 0.442 | |

## Features (35 engineered)

Temporal: hour_of_day, day_of_week, month, is_weekend, is_holiday
Lag: lag_1h, lag_24h, lag_168h (critical — week-ago load)
Rolling: rolling_mean_7d, rolling_std_3d
Weather: temperature, solar_radiation (ERA5 reanalysis)
Target: load_kwh (log-transformed during training)

## Key files

- `src/energy_forecast/features/temporal.py` — `build_temporal_features(df, cfg, target)`
- `src/energy_forecast/models/sklearn_models.py` — LightGBM, XGBoost, Ridge wrappers
- `config/config.yaml` — single source of truth for all parameters
- `scripts/run_pipeline.py` — full pipeline (data → features → train → evaluate)
- `scripts/run_horizon_sweep.py` — H+1/6/12/24/48 sweep
- `outputs/models/` — trained .joblib artefacts

## Production decisions

- **Inference model**: LightGBM only (not ensemble — marginal gain doesn't justify complexity)
- **Cadence**: H+24 at 16:00 daily (post-SEMO prices), H+1 hourly for real-time
- **Retraining**: Monthly, rolling 24-month window
- **Drift trigger**: 7d MAE > 1.5× training MAE

## Horizon sweep results (Drammen MAE kWh)

| H+1 | H+6 | H+12 | H+24 | H+48 |
|-----|-----|------|------|------|
| 3.19 | 3.58 | 3.80 | 4.03 | 4.72 |
