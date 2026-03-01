# From Three Notebooks to a Conference Paper

**Dan Alexandru Bujoreanu — NCI Dublin MSc AI 2025 → AICS 2025**

This document tells the full story of this project: how a thesis born in Jupyter notebooks
became a clean Python package, and how that package became a peer-reviewed conference paper
at AICS 2025.

---

## The Starting Point: Three Jupyter Notebooks

The original MSc thesis code lived in three large Jupyter notebooks:

| Notebook | Contents |
|----------|----------|
| `1. Drammen_EDA_Preprocessing.ipynb` | Data loading, exploratory analysis, feature engineering |
| `2. Drammen_Feature_Engineering.ipynb` | Lag/rolling features, correlation analysis, feature selection |
| `3. Drammen_Model_Training_Final.ipynb` | Model training, evaluation, result tables |

These notebooks accumulated organically over months — individual cells scattered across
thousands of lines, magic numbers hardcoded everywhere, no tests, and no separation between
data, logic, and output. The code worked. It could not easily be shared, reproduced, or extended.

---

## The Transformation: Notebooks → Python Package

The V2 refactoring converted the notebooks into a clean, installable Python package following
academic software engineering best practices from the MSc *Engineering and Evaluating AI Systems* module.

### Architecture decisions

**Three-Tier Architecture:**
```
Presentation Tier  →  scripts/run_pipeline.py · scripts/generate_eda_charts.py
Application Tier   →  src/energy_forecast/  (the Python package)
Data Tier          →  data/ · config/config.yaml · outputs/
```

**Pipe-and-Filter ML pipeline:**
```
loader → preprocessing → splits → temporal_features → feature_selection → models → evaluation
```

Every stage is a pure function: receives DataFrames in, returns DataFrames out. Each stage
can be run and tested in isolation. The pipeline can be restarted from any cached stage.

### What changed from notebooks to package

| Concern | Notebooks | Package |
|---------|-----------|---------|
| Parameters | Hardcoded scalars | `config/config.yaml` — single source of truth |
| Data flow | Global variables | Typed function signatures, MultiIndex DataFrames |
| Model interface | Ad-hoc `fit`/`predict` per model | `BaseForecaster` ABC — uniform interface |
| Reproducibility | `random.seed(42)` scattered | Centralised seed utility, applied to all frameworks |
| Feature selection | Hand-filtered in notebook cells | 3-stage pipeline: variance → correlation → LightGBM |
| Evaluation | Per-model code blocks | `evaluation/metrics.py` — zero-exclusion MAPE, R² |
| Explainability | None | SHAP beeswarm, bar, waterfall (`--stages explain`) |
| Testing | None | 24 pytest tests, CI on Python 3.10 & 3.11 |
| Documentation | Markdown cells | Docstrings (Google style), CLAUDE.md, SESSION_LOG.md |

### Bugs fixed during refactoring

Two notable bugs from the original notebooks were identified and corrected:

1. **Cyclical encoding periods** — The thesis used `hour % 23` and `day_of_week % 6` instead of
   the correct `24` and `7`. The effect was small (lag_1h dominated), but the encoding was wrong.

2. **DL model evaluation alignment** — The thesis trained DL models with a 24-step output
   (`horizon=24`) but evaluated only the first step (`y_pred[:, 0]`). The V2 pipeline trains
   single-step models directly, which is cleaner and eliminates the mismatch.

---

## The Improvements: What Made Results Better

The V2 pipeline reproduced the thesis methodology exactly — same splits, same evaluation protocol,
same H+1 single-step-ahead task. Yet results improved substantially (−27% to −65% MAE):

| Root cause | Detail |
|-----------|--------|
| **DST-robust lag features** | Added `lag_167h` and `lag_169h` (same-time ±1h weekly). The original `lag_168h` shifts by exactly 7 days — but Daylight Saving Time means the same solar hour is sometimes 167h or 169h away. The new lags provide a cleaner weekly pattern. |
| **Extended rolling windows** | Added 3h and 168h windows (thesis had 6h/12h/24h/48h). The 168h (weekly) rolling mean captures multi-week load trends. |
| **Min/max rolling statistics** | Added `rolling_min` and `rolling_max` to existing `mean` and `std`. Tighter bounds on recent load range improve tree split quality. |
| **Interaction features** | `Temperature_Outdoor_C × hour_sin` and `× hour_cos` capture the time-varying sensitivity of building load to outdoor temperature — higher impact in morning and evening than midday. |
| **Complete dataset** | All 45 buildings pass the completeness filter in V2 (vs ~43 in the thesis due to encoding issues). More training data improves generalisation. |

The dominant predictor throughout is `lag_1h` (Pearson r = 0.977 with the target). Building
electricity consumption is strongly autoregressive — the current hour is the best predictor of
the next hour. This is why H+1 results look so good and why it's called "easy mode".

---

## The Paper: AICS 2025

### Submission

The paper *"Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets"* was
submitted to the **33rd Irish Conference on Artificial Intelligence and Cognitive Science (AICS 2025)**
in two tracks:

- **Full Paper** — reviewed by 4 researchers, published in Springer CCIS Series
- **Student Paper** — reviewed by 4 researchers, published in DCU Press Companion Proceedings

Both tracks were accepted. Dual-track acceptance is unusual and reflects the breadth of the work —
both as a rigorous empirical benchmarking study and as a student research contribution.

### Core argument

Trees beat deep nets on this dataset, for three compounding reasons:

1. **Strong autoregression** — `lag_1h` (r=0.977) is a near-perfect one-step predictor.
   Tree models use it directly as a split feature. DL models embed it inside a 72-step sequence
   with 35 other features, creating redundancy rather than signal.

2. **Tabular data structure** — This is an hourly panel dataset with engineered features,
   not raw temporal sequences. Tree models are designed for tabular data; DL models are
   designed for raw sequences. The feature engineering already extracts the temporal patterns.

3. **Feature parity vs paradigm parity** — Giving all models the same 35 engineered features
   tests whether the features are useful — not whether the model is better. A fair DL comparison
   would give DL models raw 72-hour sequences and no hand-crafted features.

### Reviewer feedback and what it means for future work

**AICS Full Paper reviewers (4 reviews, accepted):**

- *Reviewer 1 (76/100):* "Deep learning models are generally better suited to raw data...
  giving them engineered lags creates feature redundancy." → **Next step: paradigm-parity
  H+24 experiment with raw sequences for DL, engineered features for trees.**

- *Reviewer 2 (64/100):* "Limited to a single dataset." → **Next step: Oslo dataset run
  (48 buildings, pipeline-ready) proves geographic generalisation.**

- *Reviewer 3 (85/100):* "Very clear presentation, good structure."

- *Reviewer 4 (78/100):* "Well written. Figure 3 not needed." → **Fixed: Figure 3 removed.**

**AICS Student Paper reviewers (4 reviews, accepted):**

- *Reviewer 2 (19/100):* "Limited novelty, bullet-based writing, shallow analysis." →
  The main contribution is empirical benchmarking, which is incremental by nature.
  The response: framing the contribution as a rigorous ablation of paradigm parity,
  not a novel architecture.

- *Reviewer 3 (87/100):* "Aligns with trees-over-DL-on-tabular-data literature." →
  Confirms the scientific positioning is correct.

---

## What Comes Next

Based on all feedback, the research roadmap in priority order:

### 1. H+24 honest evaluation (highest impact)

Remove `lag_1h` and all short-range features. Evaluate true day-ahead forecasting.
Expected finding: DL gap narrows, tree advantage compresses, but trees likely still win
on tabular data even without the lag_1h advantage.

This is the difference between an empirical curiosity (H+1 + lag_1h) and a publishable
industrial result (H+24 + no oracles).

**Config change:** `forecast_horizon: 24` + `sequence.horizon: 24`.

### 2. Paradigm-parity DL experiment

Give DL models only raw 72-hour sequences (no engineered features).
Give tree models only engineered tabular features (no raw sequences).
This is the academically rigorous comparison that addresses Reviewer 1's critique.

### 3. Oslo dataset cross-validation

Run the full pipeline on 48 Oslo school buildings.
Compare Drammen models on Oslo data (transfer) and Oslo-trained models on Oslo data (local fit).
Demonstrates geographic and portfolio generalisation.

### 4. Probabilistic forecasting

LightGBM quantile regression (P10/P50/P90) — minimal code change, high impact for
demand-response and battery scheduling applications.

### 5. Out-of-fold stacking (implemented this session)

Replace the fixed-validation meta-learner with time-aware k-fold OOF.
More statistically sound; prevents meta-learner from overfitting to a single 6-month
validation window.

---

## Technical Notes for Reproducibility

### Thesis vs V2 methodology

| Aspect | MSc Thesis | V2 Pipeline |
|--------|-----------|-------------|
| Evaluation horizon | H+1 (single-step-ahead) | H+1 (identical) |
| DL training | Multi-step output (horizon=24), evaluate step 0 | Single-step output (horizon=1) |
| Lag windows | [1,2,3,4,5,6,12,24] | [1,2,3,24,25,26,48,167,168,169] |
| Rolling windows | [6,12,24,48] hours | [3,6,12,24,72,168] hours |
| Rolling stats | mean, std | mean, std, min, max |
| Feature selection | LightGBM top-35 | variance → correlation (|ρ|>0.99) → LightGBM top-35 |
| Cyclical encoding | hour%23, day%6 (bug) | hour%24, day%7 (correct) |
| Buildings used | ~43 | 45 (all pass 70% completeness filter) |

### The weather oracle limitation

All experiments use **observed** (not forecast) weather data. In real deployment,
a weather forecast must be used instead. This is disclosed as a limitation in the paper:

> *"We assume perfect meteorological forecasts; real deployment adds weather forecast
> uncertainty to the error budget."*

Future work: use historical NWP (Numerical Weather Prediction) forecasts rather than
observations to simulate the real operational setting.

---

## File Map for This Journey

```
docs/
├── SESSION_LOG.md       — Chronological record of all development sessions
├── AI_STUDIO_FEEDBACK.md — External feedback: AI Studio, AICS reviewers, SINTEF
├── PAPER_JOURNEY.md     — This document
└── HOW_TO_RUN.md        — Execution guide

CLAUDE.md                — Project context for AI-assisted development sessions
ROADMAP.md               — Research directions and phase tracking
README.md                — Academic portfolio page (GitHub-facing)
```

---

*Written: 2026-03-01*
*Author: Dan Alexandru Bujoreanu — dan.bujoreanu@gmail.com*
