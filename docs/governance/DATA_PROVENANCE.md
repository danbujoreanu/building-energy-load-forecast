# Data Provenance — Building Energy Load Forecast
*Author: Dan Alexandru Bujoreanu · Last updated: 2026-03-28*
*Purpose: Document origin, consent basis, and handling of all data sources used in this project.*

---

## What Is Data Provenance?

Data provenance answers: *Where did this data come from? Who owns it? Under what terms is it used? How was it transformed?* This document exists to ensure any deployment of this model can demonstrate that its training data was obtained and used appropriately — a requirement under GDPR, EU AI Act Article 10, and enterprise AI governance frameworks (ISO/IEC 42001, NIST AI RMF).

---

## Data Sources

### Source 1 — COFACTOR Drammen Dataset

| Field | Value |
|-------|-------|
| **Name** | COFACTOR Drammen Building Energy Dataset |
| **Description** | Hourly electricity consumption for 45 Norwegian public buildings (schools, kindergartens) in Drammen municipality |
| **Time range** | January 2018 – March 2022 |
| **Records** | ~3.9M hourly readings (45 buildings × ~86,400 hours) |
| **Data owner** | Drammen municipality (Norway) + SINTEF Energy Research |
| **Access basis** | Academic research licence — MSc AI thesis, NCI Dublin 2025 |
| **Personally identifiable** | No. Building-level aggregate consumption only. No occupant data. |
| **Redistribution rights** | None. Raw data not included in repository. Preprocessed features only. |
| **Storage** | Local machine only. Not pushed to GitHub (gitignore'd). |
| **GDPR basis** | N/A — no personal data. |

**Consent chain:**
```
Drammen municipality → provided to SINTEF research programme (COFACTOR project)
→ SINTEF made available for academic research
→ NCI Dublin MSc research access
→ Dan Bujoreanu (personal academic use)
→ Research results published AICS 2025 (no raw data shared)
```

---

### Source 2 — SINTEF Oslo Dataset

| Field | Value |
|-------|-------|
| **Name** | SINTEF Oslo Building Energy Dataset |
| **Description** | Hourly electricity consumption for 48 Norwegian public buildings in Oslo |
| **Data owner** | SINTEF Energy Research |
| **Access basis** | Academic research — cross-city validation of Drammen model |
| **Personally identifiable** | No. Building-level aggregate only. |
| **Redistribution rights** | None. Not redistributed. |
| **Storage** | Local machine only. |

---

### Source 3 — OpenMeteo Weather API

| Field | Value |
|-------|-------|
| **Name** | OpenMeteo Historical Weather API |
| **Description** | Hourly temperature, humidity, and solar irradiance data (historical reanalysis) |
| **Provider** | OpenMeteo (open-source, non-commercial) |
| **URL** | https://open-meteo.com |
| **Terms** | Free for non-commercial use; attribution required |
| **Personally identifiable** | No. Grid-level weather data. |
| **Data freshness** | Reanalysis data — validated against weather station observations |
| **Coverage** | Drammen (Norway), Oslo (Norway), Maynooth (Ireland) for home trial |

**How it's used:** Temperature and solar irradiance features are joined to building consumption data by timestamp and location. Not stored separately — only joined dataset is retained.

---

### Source 4 — ESB Networks Smart Meter Data (Home Trial)

| Field | Value |
|-------|-------|
| **Name** | Personal smart meter consumption data |
| **Description** | 30-minute interval electricity import/export readings from Dan Bujoreanu's home smart meter |
| **Provider** | ESB Networks (via myenergi Eddi API + manual HDF export) |
| **Data subject** | Dan Bujoreanu (sole occupant / data controller) |
| **Consent basis** | GDPR Article 6(1)(a) — explicit consent (own data) |
| **Access method** | Eddi API (OAuth authenticated) + ESB Networks HDF file export (manual) |
| **Regulatory basis** | CRU202517 — SMDS (Smart Metering Data Service) framework grants consumers right to access own data |
| **Personally identifiable** | Yes — linked to specific MPRN (Meter Point Reference Number) and property address |
| **Storage** | Local machine only. Not pushed to GitHub. Excluded from all published outputs. |
| **Retention** | Retained for duration of home trial and product validation. |

**Production note:** For multi-household deployment, each user must grant explicit SMDS OAuth consent via the ESCO registration process under CRU202517. No data is collected without active consumer opt-in.

---

### Source 5 — myenergi Eddi API

| Field | Value |
|-------|-------|
| **Name** | myenergi Eddi Home Energy Management API |
| **Description** | Real-time and historical data from Eddi immersion heater controller — demand, solar divert, grid import |
| **Provider** | myenergi Ltd (UK) |
| **Access basis** | Personal device — OAuth API key authentication |
| **Data subject** | Dan Bujoreanu |
| **Personally identifiable** | Yes — linked to physical device and home address |
| **Storage** | Local machine only. API credentials in `.env` (gitignored). |

---

## Data Transformation Chain

```
Raw Sources
  │
  ├─ COFACTOR Drammen CSVs (building consumption, hourly)
  │    └─► src/energy_forecast/data.py (load_raw_data)
  │         └─► data/processed/drammen/ (gitignored)
  │
  ├─ OpenMeteo API (temperature, solar)
  │    └─► Joined by timestamp in feature pipeline
  │
  └─ ESB Smart Meter HDF (home trial only)
       └─► Manual import → separate trial pipeline

Feature Engineering (src/energy_forecast/features.py)
  │
  ├─ Cyclical encoding: hour (24), day_of_week (7), month (12)
  ├─ Lag features: 1h, 24h, 167h, 168h, 169h (DST-robust)
  ├─ Rolling statistics: 24h mean, std, min, max
  └─ Temperature interactions: temp × hour_sin, temp × hour_cos

Training (src/energy_forecast/models.py)
  └─► checkpoints/lightgbm_h24.pkl (gitignored — model weights only, no raw data)

Evaluation (scripts/run_pipeline.py --stages evaluate)
  └─► outputs/ (metrics, charts — no raw data)
```

---

## Regulatory Compliance Notes

| Regulation | Requirement | This project |
|-----------|-------------|-------------|
| **GDPR Art. 5** | Data minimisation | Home trial data never uploaded. Training data is aggregate only. |
| **GDPR Art. 6** | Lawful basis | Academic licence (COFACTOR). Explicit consent (home trial). |
| **EU AI Act Art. 10** | Data governance for high-risk AI | Not classified as high-risk (energy optimisation advisory, not safety-critical). Model card and provenance doc maintained regardless. |
| **CRU202517** | SMDS consumer data rights | Production deployment requires ESCO registration and per-household OAuth consent. Appendix A draft prepared. |
| **OpenMeteo ToS** | Attribution | Attribution included in all publications and documentation. |

---

## Audit Trail

| Date | Change | Author |
|------|--------|--------|
| 2025 | COFACTOR dataset acquired under academic licence | Dan Bujoreanu |
| 2025 | SINTEF Oslo dataset acquired for cross-city validation | Dan Bujoreanu |
| 2026-03 | Home trial initiated — ESB smart meter data collected | Dan Bujoreanu |
| 2026-03 | Eddi API integration completed | Dan Bujoreanu |
| 2026-03-28 | This provenance document created | Dan Bujoreanu |

*Update this document whenever a new data source is added or data handling changes.*
