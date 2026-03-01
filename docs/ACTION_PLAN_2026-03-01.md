# Action Plan — March 1st 2026

**Author:** Dan Alexandru Bujoreanu
**Context:** Post-AICS 2025, post-V2 production package refactor.
This document captures the full research direction and priority list as of March 1st 2026.

---

## Where We Are

| What | Status |
|------|--------|
| MSc thesis (3 Jupyter notebooks) | ✅ Submitted summer 2025 |
| TAI Dublin conference (June 2025) | ✅ Presented with Faithful Onwuegbuche |
| AICS 2025 Full Paper (Springer CCIS) | ✅ Accepted & published December 2025 |
| AICS 2025 Student Paper (DCU Press) | ✅ Accepted & published December 2025 |
| V2 production package (refactor) | ✅ Complete, February–March 2026 |
| OOF stacking | ✅ Validated March 1st 2026 — MAE 1.744, RMSE 3.240, R² 0.9953 |
| TFT lightning.pytorch fix | ✅ Applied — needs validation run |

### Current V2 Results (H+1, 240,481 test samples, 42 buildings)

| Rank | Model | MAE (kWh) | R² | vs Thesis |
|------|-------|-----------|-----|-----------|
| 1 | Random Forest | **1.711** | 0.9947 | −48% |
| 2 | Stacking Ensemble (Ridge meta, OOF) | 1.744 | 0.9953 | −52% |
| 3 | LightGBM | 2.108 | 0.9938 | −41% |
| 4 | XGBoost | 2.228 | 0.9931 | −35% |
| 5 | Lasso | 3.064 | 0.9873 | −27% |
| 6 | Ridge | 3.069 | 0.9874 | −27% |
| 7 | LSTM | 3.582 | 0.9816 | −65% |
| 8 | GRU | 3.947 | 0.9812 | new in V2 |
| 9 | CNN-LSTM | 4.572 | 0.9767 | −63% |
| — | TFT | fix applied, needs re-run | — | — |
| — | Mean Baseline | 22.691 | 0.4415 | — |

> **Note on GRU:** GRU was not in the original MSc thesis results table. It was added new
> in the V2 pipeline and evaluated for the first time. LSTM and CNN-LSTM were in the thesis.

> **Note on RF vs Stacking:** RF has better MAE (1.711 vs 1.744) but Stacking wins on RMSE
> (3.240 vs 3.441) and R² (0.9953 vs 0.9947). Stacking reduces large-error outliers better.
> OOF coverage: 83.4% of training rows (954,535 / 1,144,535) — correct; first fold has no history.

> **Note on current results:** These are H+1 (single-step-ahead) with `lag_1h` available.
> The dominant predictor is `lag_1h` (r ≈ 0.977). This is "easy mode" — see Track A below.

---

## The Two Tracks

### Track A — Defend the existing paper

Addresses the top criticisms from AICS 2025 reviewers and AI Studio:

- **R2 (Full Paper):** "Single dataset limits generalisability" → **Oslo cross-dataset run**
- **R1 (Full Paper):** "H+1 + lag_1h is trivial; use H+24" → **H+24 honest evaluation**
- **AI Studio:** "lag_1h is the silver bullet — H+24 is where real forecasting lives"

These two experiments (Oslo + H+24) are pipeline-ready. No new code needed.

### Track B — Build the original novel ensemble (PhD/journal track)

The original research plan (documented July 2025) proposed:
> "A novel ensemble of CNN-LSTM + Informer + TFT + XGBoost"

The thesis found that trees dominated, which became the paper story. But the ensemble vision
remains valid — the problem was **lack of base learner diversity**, not the ensemble approach.

Track B adds:
1. **PatchTST** — outperforms Informer empirically; strong architectural diversity
2. **TFT QuantileLoss** — probabilistic outputs (P10/P50/P90)
3. **H+24 + paradigm parity** — DL gets raw sequences, trees get engineered features
4. **OOF stacking** (already implemented) — unbiased meta-learner

The paper this produces: *"H+24 Probabilistic Building Energy Load Forecasting: A Paradigm-Parity
Comparison of Tree Ensembles and Sequence Models"* — journal-level.

---

## AI Studio Paradigm Parity Experiment Design (March 2026)

This section documents the experiment design agreed with AI Studio in March 2026.
It addresses the central critique from AICS R1 (76/100) and AI Studio:

> *"Giving DL models engineered tabular features — including lag_1h — defeats their purpose.
> The feature parity trap: trees are inherently better at tabular data, so DL will always
> lose on their own ground. A fair comparison requires paradigm parity."*

### The Two-Branch Architecture

**Branch A — Tabular (Trees, causal H+24):**
```
Input features (all at t=0, no oracle future info):
  • Lag features: lag_24h, lag_25h, lag_26h, lag_48h, lag_167h, lag_168h, lag_169h
                  (all lags ≥ 24h — no oracle leakage)
  • Rolling stats: anchored at t−24 (e.g. rolling_mean_24h uses data up to t−24)
  • Cyclical time: hour_sin/cos, day_of_week_sin/cos, month_sin/cos, day_of_year_sin/cos
  • Building ID: one-hot encoded (42 buildings)
  • Known future covariates: observed temperature t+1..t+24 (oracle proxy for NWP;
                              in production: WeatherNext or MET Nordic NWP forecast)

Models: RF, LightGBM, XGBoost, Stacking (OOF, Ridge meta)
Output: 24 separate regression heads (multi-output; one per horizon step)
```

**Branch B — Sequential (DL / TFT, raw look-back):**
```
Encoder input: raw 72-hour look-back sequences per building
  • [load_kWh, temperature_C, solar_Wm2, wind_ms] — shape: (72, 4)
  • NO engineered lag features; NO rolling statistics; NO time-of-day features
  • Architecture advantage: LSTM/GRU/TFT learn temporal patterns from raw sequences

Known future inputs (decoder side for TFT, concatenated for LSTM/GRU):
  • weather forecast for t+1..t+24: [temperature_C, solar_Wm2]
  • TFT: passed as time_varying_known_reals
  • LSTM/GRU: concatenated to hidden state at each decoder step

Models: LSTM, GRU, CNN-LSTM, TFT, PatchTST (planned)
Output: 24-step multi-horizon (direct), shape: (n_samples, 24)
        TFT + LightGBM quantile: P10/P50/P90 per horizon step
```

### Sequencing

| Week | Task | Track |
|------|------|-------|
| Week 1 | Simple H+24 run (config change only, same 35 features minus oracle lags) | A |
| Week 2 | Branch A implementation (≥24h lags + known future weather) | B |
| Week 3 | Branch B raw sequence loader + DL multi-horizon head | B |
| Week 4 | TFT known-future weather inputs + quantile loss | B |
| Week 4-5 | PatchTST (architectural diversity) | B |
| Week 5-6 | Probabilistic metrics, combined paper write-up | B |

### Code Change Estimate

~150-170 new lines across 3 files:

| File | Change | Lines |
|------|--------|-------|
| `features/temporal.py` | Branch-aware feature builder: `paradigm=tabular` vs `paradigm=sequence` flag | ~40 |
| `models/dl_base.py` or new `dl_sequence.py` | Raw sequence DataLoader (72×4 tensors); multi-output head (output=24) | ~80 |
| `config/config.yaml` | Paradigm parity flags: `paradigm_parity: true`, `sequence_features: [load, temp, solar, wind]` | ~20 |
| `run_pipeline.py` | Branch routing: pass correct feature set per model family | ~30 |

> **Note:** The `forecast_horizon` guard already exists in `temporal.py`
> (`lag_windows = [w for w in all_lag_windows if w >= horizon]`). The paradigm parity
> branch builds on this — it's not a rewrite, it's an extension.

### Why This Is the Journal Paper

- Eliminates the feature parity trap from the AICS paper
- Each model family receives its natural input: trees → engineered tabular; DL → raw sequences
- Enables the first honest test: can TFT's attention mechanism beat RF's feature mastery when both are on home turf?
- Probabilistic outputs (P10/P50/P90) add direct decision-support value for utility operators
- Connects to production deployment: H+24 probabilistic forecast = demand response bid input

---

---

## Priority List

### 🔴 Immediate — Run now (no coding needed)

| # | Task | Command | Time | Why |
|---|------|---------|------|-----|
| 1 | Validate OOF stacking + all sklearn models | `run_pipeline.py --skip-slow` | ~10 min | Confirm OOF works, get fresh results |
| 2 | TFT overnight validation run | `run_pipeline.py` (full) | ~6-8h | TFT fix applied S7; never validated |
| 3 | Oslo dataset run | `city: oslo` in config, `--skip-slow` | ~10 min | Cross-dataset generalisability |

### 🔴 High priority — Code + run

| # | Task | Effort | Why |
|---|------|--------|-----|
| 4 | H+24 evaluation | Config change only, ~10 min run | Honest day-ahead forecast; removes lag_1h oracle |
| 5 | PatchTST implementation | 2-3 days coding | Architectural diversity; outperforms Informer per benchmarks |
| 6 | LightGBM quantile regression | < 1 day | P10/P50/P90 intervals, minimal code change |

### 🟡 Medium priority

| # | Task | Effort | Why |
|---|------|--------|-----|
| 7 | TFT QuantileLoss | 1-2 days | Probabilistic output from Transformer |
| 8 | Solar radiation feature | 1 day | SINTEF validated; ~18% missing → MICE imputation first |
| 9 | Informer implementation | 2-3 days | Planned in original research doc; lower priority than PatchTST |
| 10 | Peak load features | 1 day | `is_peak_hour`, `temp × is_peak_hour`; improves tail accuracy |

### 🔵 Lower priority / PhD track

| # | Task | Notes |
|---|------|-------|
| 11 | Oslo cross-dataset transfer learning | Train Drammen → test Oslo (vs. trained on Oslo) |
| 12 | H+24 + paradigm parity | DL gets raw 72h sequences; trees get 35 engineered features |
| 13 | Hierarchical BART | Partial pooling across buildings; PhD-track |
| 14 | FastAPI + Docker deployment | REST API for live predictions |
| 15 | Per-building profiles | `generate_eda_charts.py --profiles` |

---

## Production Deployment Architecture (Future Work)

### The core design question
A utility company, building manager, or demand response aggregator (e.g., Viotas) or data
center operator doesn't run all models simultaneously. They need **inference tiering**:

| Tier | Models | Latency | Use case |
|------|--------|---------|----------|
| Real-time (< 1ms) | LightGBM, RF | Sub-millisecond | Live dashboard, anomaly alert |
| Near real-time (< 10ms) | XGBoost | Milliseconds | Hourly monitoring report |
| Day-ahead batch (nightly) | LSTM, GRU, TFT | Minutes to hours (training); ms (inference) | H+24 demand forecast, DR bid |
| Weekly/monthly retrain | All models | Hours | Concept drift correction |

**Why this makes sense:**
- RF/LightGBM inference on 35 features is ~0.1ms → can run every minute
- TFT/LSTM *inference* is also fast (< 1ms); it's *training* that's slow
- Therefore: **train heavy models less often, infer from them always**

### Windowing / Online Learning (rolling retraining)

Building energy patterns drift over time (new tenants, renovations, seasonal occupancy
changes, new EV chargers). Static train/test splits don't capture this.

**Proposed production retraining loop:**
```
every 30 days:
    window = last 90 days of actual meter readings + weather
    retrain RF, LightGBM on window (fast: ~2 min)
    retrain LSTM, TFT on window (slow: scheduled overnight)
    evaluate on held-out last 7 days within window (rolling walk-forward)
    if MAE degrades > threshold → alert / trigger emergency retrain
```

**Key decisions for the paper/future work:**
1. Window size: 30 days? 90 days? Full history (growing window) vs. fixed rolling window?
2. Which models support incremental learning (LightGBM `init_model` for warm-start)?
3. Walk-forward validation (expanding window) vs. rolling window back-test
4. WeatherNext integration: replace oracle temperature with 4×daily forecast

**Connection to SINTEF NSBI:**
The Nordic Smart Building Initiative is the exact institutional use-case for a production
system like this — 45-building Drammen fleet is already a real deployment candidate.

### Inference API design (item #14 expanded)
```
POST /predict
{
  "building_id": "B001",
  "horizon": 24,          # hours ahead
  "model": "ensemble",    # "lgbm" | "rf" | "lstm" | "tft" | "ensemble"
  "return_quantiles": true  # P10/P50/P90 if model supports it
}
→ { "predictions": [...24 values...], "p10": [...], "p90": [...] }
```

---

## Model Inventory — Target State

| Model | Status | Notes |
|-------|--------|-------|
| Ridge, Lasso | ✅ Done | |
| Random Forest | ✅ Done | Best H+1 result: 1.711 kWh |
| LightGBM | ✅ Done | |
| XGBoost | ✅ Done | |
| LSTM | ✅ Done | |
| GRU | ✅ Done | New in V2 — not in original thesis |
| CNN-LSTM | ✅ Done | |
| TFT | ✅ Fixed — needs run | lightning.pytorch fix applied |
| PatchTST | 🔴 Planned | Strong architectural diversity addition |
| Informer | 🟡 Planned | Original research plan; lower priority than PatchTST |
| Stacking Ensemble (Ridge/LGBM meta) + OOF | ✅ Done | OOF validated March 1st 2026: MAE 1.744, RMSE 3.240, R² 0.9953 |
| Weighted Avg Ensemble | ✅ Done | |
| LightGBM quantile | 🔴 Planned | P10/P50/P90 |

---

## Session 11 Fixes (March 1st 2026 — evening)

| Fix | Detail |
|-----|--------|
| `tensorflow-metal` installed | LSTM/GRU/CNN-LSTM were running on CPU — now Metal GPU active |
| TFT hidden_size: 64→32 | Was 833K params (24h/run); now 242K params (~6-7h/run, matches thesis 163K) |
| TFT logger: False→True | Epoch output was completely suppressed; now `_EpochLogger` writes one line/epoch |
| H+24 confirmed as target | Current H+1 = fair tree/DL baseline; H+24 = paper's honest evaluation |
| 35 features → all models | Confirmed from notebooks: trees (2D), DL (3D sequences), TFT (categorised) |

### Why TFT Training Is Quiet (num_workers=0 bottleneck)

**The machine sounds different during TFT vs Random Forest — here's why:**

| Model | CPU usage | GPU usage | Machine sound |
|-------|-----------|-----------|---------------|
| Random Forest | 12 cores × 100% (`n_jobs=-1`) | N/A | Very loud (fan maxed) |
| TFT (current) | 1 core × 96% (DataLoader bottleneck) | MPS: 30-50% (waiting for data) | Quiet |

**Root cause:** `num_workers=0` in the PyTorch DataLoader means the data loading is
*synchronous* — the CPU must finish loading each batch before the GPU can compute the next.
PyTorch Lightning even warns about this explicitly in the log:

```
The 'train_dataloader' does not have many workers which may be a bottleneck.
Consider increasing num_workers to 11.
```

The GPU is confirmed active (`GPU available: True (mps), used: True` in log), but it's
spending ~50-70% of its time idle, waiting for the CPU to serve the next batch.

**RF sounds loud because:** `n_jobs=-1` saturates all 12 CPU cores simultaneously —
the CPU is the compute unit, and it's maxed. All 12 fans spin up.

**TFT is quiet because:** Only 1 CPU core is active (the DataLoader thread), and
the GPU is underutilised. The bottleneck is I/O, not compute.

**Planned fix:** `num_workers=4` in TFT and DL DataLoaders (will not be applied while
TFT is currently running — would require a restart).

---

## Key Methodological Context

**Why V2 results are better than thesis (H+1):**
1. DST-robust lags (167h/169h)
2. Extended rolling windows (3h, 168h) + min/max stats
3. `temp × hour_sin/cos` interaction features
4. Complete dataset (45 buildings vs ~43)

**Why H+1 results are "easy mode":**
`lag_1h` has r = 0.977 with the target. Any model that uses it performs well.
The real test is H+24 where lag_1h is not available.

**The paradigm parity problem (AI Studio + AICS R1):**
Giving DL models engineered tabular features (including lags) defeats their purpose.
A fair comparison: trees get engineered features; DL gets raw 72h sequences.
This is the experiment that produces the publishable journal result.

**Weather oracle limitation:**
All models use observed temperature, not forecast temperature.
Must be disclosed: "We assume perfect weather forecasts; real deployment adds forecast uncertainty."

---

## Key External Feedback

| Source | Finding | Our Response |
|--------|---------|--------------|
| AI Studio | H+1 + lag_1h = "easy mode"; H+24 is the honest evaluation | Plan H+24 experiment (Track A) |
| AI Studio | Feature parity ≠ paradigm parity | Plan paradigm-parity H+24 (Track B) |
| AICS R1 (76/100) | DL should get raw sequences, not engineered lags | Acknowledged; Track B |
| AICS R2 (64/100) | Single dataset | Oslo run (Track A) |
| AICS R3 (85/100) | Very clear presentation | Thank you |
| AICS R4 (78/100) | Figure 3 not needed | Figure 3 removed |
| AICS Student R2 (19/100) | Limited novelty, bullet-based writing | Accepted trade-off for conference level |
| AICS Student R3 (87/100) | Aligns with trees-over-DL literature | Confirms positioning |
| SINTEF Expert | Trees validated; solar radiation valid Phase 2 feature | Noted; in backlog |

---

## Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project context (auto-loaded each session) |
| `docs/SESSION_LOG.md` | Chronological record of all sessions |
| `docs/AI_STUDIO_FEEDBACK.md` | All external feedback (AI Studio, AICS reviewers, SINTEF) |
| `docs/PAPER_JOURNEY.md` | Notebooks → paper → package writeup |
| `docs/ACTION_PLAN_2026-03-01.md` | This document |
| `ROADMAP.md` | Research directions with phase tracking |
| `README.md` | GitHub portfolio page with AICS 2025 citation |

---

*Created: 2026-03-01*
*Author: Dan Alexandru Bujoreanu — dan.bujoreanu@gmail.com*
