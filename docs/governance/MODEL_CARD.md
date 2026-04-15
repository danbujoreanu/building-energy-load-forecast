# Model Card — LightGBM H+24 Energy Demand Forecast
*Format: Mitchell et al. (2019) / Hugging Face Model Card standard*
*Author: Dan Alexandru Bujoreanu · Last updated: 2026-03-28*

---

## Model Details

| Field | Value |
|-------|-------|
| **Model name** | LightGBM H+24 Building Energy Demand Forecast |
| **Model type** | Gradient Boosted Decision Trees (LightGBM) |
| **Task** | Multi-step time-series regression — 24-hour-ahead (H+24) electricity demand forecasting |
| **Version** | V2 Pipeline (2026) |
| **Author** | Dan Alexandru Bujoreanu, MSc AI, NCI Dublin |
| **Contact** | via LinkedIn: linkedin.com/in/danbujoreanu |
| **Published** | AICS 2025 — *"Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets"* — Springer CCIS Series |
| **License** | MIT |
| **Repository** | github.com/danbujoreanu/building-energy-load-forecast |

---

## Intended Use

### Primary intended use
Short-term (next 24 hours) electricity consumption forecasting for public buildings and residential properties. Designed to enable:
- Time-of-use tariff optimisation (scheduling flexible loads in cheap windows)
- Dynamic pricing preparation (CRU June 2026 mandate, Irish market)
- Heat pump and EV charging schedule optimisation
- Building energy management system integration

### Primary intended users
- Building energy managers (public sector)
- Residential energy app developers (Irish market)
- Smart home device manufacturers
- Energy suppliers building optimisation tools

### Out-of-scope uses
- Individual occupant identification or behaviour profiling (model operates at building/meter level only)
- Real-time (sub-hourly) control decisions without additional validation
- Safety-critical infrastructure control (grid balancing, frequency regulation)
- Forecasting beyond 24 hours without retraining

---

## Training Data

| Field | Value |
|-------|-------|
| **Primary dataset** | COFACTOR Drammen — 45 Norwegian public buildings (schools, kindergartens) |
| **Time range** | January 2018 – March 2022 (hourly resolution) |
| **Training samples** | ~3.9M hourly readings across 45 buildings |
| **Target variable** | `Electricity_Imported_Total_kWh` — net electricity imported per hour |
| **Second dataset** | SINTEF Oslo — 48 buildings (cross-city validation) |
| **Data source** | Drammen municipality + SINTEF research institute (Norway) |
| **Data access** | Academic licence. Not publicly redistributable. |
| **Preprocessing** | DST-robust lag features · cyclical time encoding (hour=24, day=7) · rolling min/max/mean/std · temperature interaction terms |

### Data limitations
- Training data is Norwegian public buildings (Scandinavian climate, commercial occupancy patterns)
- Direct transfer to Irish residential properties requires domain adaptation and local validation
- No sub-metering data — total electricity only (no HVAC/lighting/plug load breakdown)
- Holiday calendar specific to Norwegian public sector

---

## Evaluation Data

| Field | Value |
|-------|-------|
| **Test set** | COFACTOR Drammen holdout — July 2021 – March 2022 |
| **Test samples** | 241,523 hourly readings across 44 buildings |
| **Cross-city validation** | SINTEF Oslo — 48 buildings, independent test |
| **Home trial** | Dan Bujoreanu's own ESB smart meter, Maynooth, Ireland (Mar 2026) |

---

## Performance Metrics

### H+1 Horizon (Sprint 2 sweep — Drammen)

> H+1 is available as a real-time cadence. Primary published result is H+24.
> H+1 allows short-lag features (lag_1h r≈0.977 is dominant predictor).

| Model | MAE (kWh) | Degradation to H+48 |
|-------|-----------|---------------------|
| **LightGBM** | **3.188** | +48% at H+48 (4.724 kWh) |
| XGBoost | 3.339 | +45% |
| Ridge | 4.301 | +96% |

### H+24 Horizon — Full model comparison (COFACTOR Drammen, n=241,523)

| Setup | Model | MAE (kWh) | RMSE | R² | Train time |
|-------|-------|-----------|------|----|------------|
| **A** | **LightGBM** | **4.029** | **7.445** | **0.9752** | 13 s |
| A | XGBoost | 4.197 | 7.662 | 0.9737 | 7 s |
| A | Random Forest | 4.402 | 8.376 | 0.9686 | 360 s |
| A | Ridge | 7.460 | 12.856 | 0.9261 | <1 s |
| B | TFT | 8.770 | 17.581 | 0.8646 | 5,627 s |
| B | CNN-LSTM | 9.375 | 16.744 | 0.8772 | 681 s |
| B | LSTM | 34.938 | 47.562 | −0.0039 | 2,872 s |
| C | PatchTST | 6.955 | 14.118 | 0.9102 | 3,026 s |
| Ens | Stacking (Ridge meta) | 4.034 | 7.508 | 0.9751 | 1,059 s |
| — | Mean Baseline | 22.673 | 35.314 | 0.4424 | — |

> **Key finding:** LightGBM beats PatchTST (DL, raw sequence) by **42% MAE** (DM = −12.17, p < 0.0001). Ensemble stacking does not outperform LightGBM alone.

### H+24 Cross-city validation (SINTEF Oslo, n=779,423, 48 buildings)

| Model | MAE (kWh) | R² |
|-------|-----------|-----|
| **Stacking** | **7.280** | **0.9635** |
| LightGBM | 7.415 | 0.9630 |
| PatchTST | 13.616 | 0.8741 |
| Mean Baseline | 45.3 | — |

> Cross-city paradigm gap: PatchTST +84% MAE vs LightGBM on Oslo (wider than +42% on Drammen).

### Statistical significance (Diebold-Mariano, HLN-corrected)

| Comparison | DM statistic | p-value |
|-----------|-------------|---------|
| LightGBM vs PatchTST [C] | −12.17 | <0.0001 *** |
| LightGBM vs XGBoost [A] | −5.25 | <0.0001 *** |
| LightGBM vs Ridge [A] | −33.52 | <0.0001 *** |

### Home trial (Dan Bujoreanu's ESB smart meter, Maynooth, Ireland)
- MAE: **0.171 kWh/hour** on 17,302 hourly readings (Mar 2024 – Mar 2026)
- Plan score: 62/100 — significant room for tariff optimisation
- Annual saving opportunity: **€178.65/year** identified on first analysis
- myenergi Eddi API integrated for demand response automation

---

## Key Features

| Feature category | Examples | Importance |
|-----------------|---------|------------|
| Temporal | hour_sin, hour_cos, day_of_week_sin, day_of_week_cos, month, is_weekend | High |
| Lag features | lag_1h, lag_24h, lag_167h, lag_168h, lag_169h (DST-robust) | High |
| Rolling statistics | rolling_mean_24h, rolling_std_24h, rolling_min_24h, rolling_max_24h | Medium |
| Meteorological | temperature, temperature × hour_sin, temperature × hour_cos | Medium |
| Building ID | building_id (one-hot encoded) | Medium |

---

## Ethical Considerations

### Privacy
- **No personal data.** Model operates at building/meter level. No occupant identification.
- Training data is anonymised aggregate electricity consumption from public buildings.
- Home trial uses own smart meter data under explicit personal consent.
- Production deployment (Irish residential) requires: GDPR Data Processor agreement, explicit user consent for smart meter data access, SMDS OAuth per CRU202517.

### Fairness
- Model trained on Norwegian public buildings (schools, kindergartens). Performance on other building types (hospitals, industrial, retail) is unknown and should be validated before deployment.
- May underperform for buildings with atypical consumption patterns (24/7 operations, heavy industrial loads).
- Residential transfer requires Irish-specific retraining with local climate and tariff data.

### Transparency
- SHAP explainability built into evaluation pipeline (beeswarm, bar, waterfall, heatmap).
- Diebold-Mariano tests confirm statistical significance of performance differences.
- All limitations documented. No claims made beyond validated use cases.

### Environmental impact
- LightGBM is computationally efficient — training runs in minutes on standard hardware.
- Production inference is designed for edge deployment — LightGBM inference runs in ~2ms on standard hardware. Development and home trial run on Mac Mini M5 (Apple Silicon, macOS, no GPU required). Production hardware at scale is TBD (cost-optimised form factor, target <€30 BOM at >500 units/month). The P1 port USB adapter interface is hardware-agnostic (DSMR standard).
- Purpose of the model is energy efficiency — net environmental benefit expected.

---

## Caveats and Recommendations

1. **Domain transfer**: Validate on Irish residential data before production use. Norwegian public buildings ≠ Irish homes.
2. **Forecast horizon**: H+24 performance (R²=0.975) is for public buildings. Residential home trial performance should be independently validated at scale.
3. **Model drift**: Retrain monthly on rolling 24-month window as seasonal patterns evolve.
4. **Human oversight**: Automated decisions (battery charging, heat pump scheduling) should have user override capability. Model outputs are probabilistic forecasts, not certainties.
5. **Tariff dependency**: Accuracy of cost savings depends on correct tariff configuration. Validate tariff inputs against CRU-registered supplier rates.

---

## How to Use

```python
import joblib, yaml
from src.energy_forecast.features.temporal import build_temporal_features

# Load config (single source of truth for all parameters)
with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

# Load model and scaler
model  = joblib.load("outputs/models/lightgbm_h24.pkl")
scaler = joblib.load("outputs/models/scaler.pkl")

# Build features — cfg controls forecast_horizon (24), lag exclusions, etc.
# df must contain target column + weather columns at hourly resolution
X = build_temporal_features(df, cfg, target="Electricity_Imported_Total_kWh")

# Apply scaler (fitted on train set only — prevents leakage)
import pandas as pd
X_scaled = pd.DataFrame(scaler.transform(X), columns=X.columns, index=X.index)

# Predict (returns array of shape [n_samples,])
predictions = model.predict(X_scaled)
```

Full documentation: `docs/ops/HOW_TO_RUN.md`

---

## Citation

```bibtex
@inproceedings{bujoreanu2025forecasting,
  title={Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets},
  author={Bujoreanu, Dan Alexandru},
  booktitle={33rd Irish Conference on Artificial Intelligence and Cognitive Science (AICS 2025)},
  series={Communications in Computer and Information Science},
  publisher={Springer},
  year={2025}
}
```

---

*This model card was written following the standard established in Mitchell et al. (2019) "Model Cards for Model Reporting" (ACM FAccT). It will be updated as the model evolves toward production deployment.*
