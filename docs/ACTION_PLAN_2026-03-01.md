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
