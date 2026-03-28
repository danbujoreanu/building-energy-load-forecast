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
| **Test samples** | 240,481 hourly readings |
| **Cross-city validation** | SINTEF Oslo — 48 buildings, independent test |
| **Home trial** | Dan Bujoreanu's own ESB smart meter, Maynooth, Ireland (Mar 2026) |

---

## Performance Metrics

### H+1 Horizon (V2 Pipeline — uniform target)

| Model | MAE (kWh) | R² | vs. Thesis baseline |
|-------|-----------|-----|---------------------|
| **Random Forest** | **1.711** | **0.9947** | −48% |
| LightGBM | 2.108 | 0.9938 | −41% |
| Stacking Ensemble | 1.774 | 0.9953 | −52% |
| LSTM | 3.582 | 0.9816 | −65% |
| Mean Baseline | 22.691 | 0.4415 | — |

### H+24 Horizon (primary deployment target)

| Dataset | Model | R² | Notes |
|---------|-------|-----|-------|
| COFACTOR Drammen | LightGBM | **0.975** | Primary published result |
| SINTEF Oslo | LightGBM | **0.963** | Cross-city validation |
| Maynooth home (ESB) | LightGBM | TBC | Home trial — MAE 0.171 kWh/hr observed |

### Home trial result
- €178.65/year opportunity identified on first analysis of real Irish smart meter data
- Plan score: 62/100 (significant room for tariff optimisation)
- Digicel Eddi API integrated for demand response automation

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
- Production inference runs on Raspberry Pi-class hardware (edge deployment) — minimal energy overhead.
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
# Load model
import joblib
model = joblib.load('checkpoints/lightgbm_h24.pkl')

# Prepare features (see src/energy_forecast/features.py)
from src.energy_forecast.features import build_temporal_features
X = build_temporal_features(df, horizon=24)

# Predict (returns 24-step ahead forecast)
predictions = model.predict(X)
```

Full documentation: `docs/HOW_TO_RUN.md`

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
