# Reviewer Response Matrix

**Purpose:** Maps every AICS 2025 critique to the journal paper's response.
Use this as a checklist when writing/revising the journal paper draft.

**Last updated:** 2026-03-15

---

## AICS 2025 Full Paper (Springer CCIS) — 4 Reviewers

### Review 1 — 76/100

| Critique | Journal paper response | Status |
|---|---|---|
| DL models given engineered features (not raw data) — feature parity trap | **Fixed by paradigm parity.** Setup B = DL + engineered features (negative control); Setup C = DL + raw 72h sequences. Section 3.1 documents both paradigms explicitly. | ✓ Done |
| Why not Prophet? | Add note to Section 2 / footnote: Prophet requires per-series fitting (45 separate models) and cannot pool information across buildings. LightGBM with building_id dummies is equivalent and learns cross-building patterns simultaneously. Prophet also does not support multi-step horizon output natively. | Needs paper note |
| Why scale for DL but not ensembles? | Add sentence to Section 3.2: "StandardScaler is applied to DL inputs only; tree-based models are scale-invariant (splits on thresholds, not magnitudes) and do not benefit from scaling." | Needs paper note |
| How were DL depths decided? | Add hyperparameter table (Table 3 or Appendix A). See below. | Needs table |

### Review 2 — 64/100

| Critique | Journal paper response | Status |
|---|---|---|
| Single dataset | Oslo generalisation study (48 buildings, different city, zero-shot). Section 5.2. | ✓ Done |
| More DL tuning might change results | Setup B is explicitly framed as a negative control — DL trained on the same features trees use. Section 3.1 states this. The TFT result (most expressive DL model) confirms the gap is not a tuning artefact: TFT MAE=8.770 vs LightGBM MAE=4.029. | ✓ Addressed — strengthen wording |
| BESS undefined | Add to abbreviations list: "BESS: Battery Energy Storage System" | Needs fix |
| Section 6.2 bullet-form writing | Journal paper uses full narrative sentences throughout. | ✓ Done |

### Review 3 — 85/100

| Critique | Journal paper response | Status |
|---|---|---|
| Very clear, good structure — no changes needed | N/A | N/A |

### Review 4 — 78/100

| Critique | Journal paper response | Status |
|---|---|---|
| Figure 3 not needed | Figure 3 removed from conference paper. Not in journal paper. | ✓ Done |

---

## AICS 2025 Student Paper (DCU Press) — 4 Reviewers

### Review 1 — 76/100

| Critique | Journal paper response | Status |
|---|---|---|
| Single case study; unclear if results depend on specific dataset/hyperparameter tuning | Oslo generalization (Setup A zero-shot R²=0.963). Sprint 3: CER Irish residential dataset will add a third, climate-different validation. | Partially done; CER pending |

### Review 2 — 19/100 *(harshest, most actionable for journal)*

| Critique | Journal paper response | Status |
|---|---|---|
| Limited novelty — empirical benchmarking only | Journal contribution is distinct: (1) 3-way paradigm parity at H+24 (not H+1), (2) Setup C raw sequences vs Setup B engineered features — first honest cross-paradigm comparison on this domain, (3) Oslo zero-shot generalization, (4) Diebold-Mariano significance tests, (5) Quantile bounds for MPC. This is methodology + empirical benchmarking + deployment framing. | ✓ Framed in Introduction |
| Bullet-based writing | Journal paper fully narrative. | ✓ Done |
| Shallow analysis of why DL underperforms | Add to Section 5.1: mechanistic explanation. Building energy load is dominated by a small number of highly predictive features (lag_168h, temperature × hour_sin, building_id). Once these are explicitly engineered, DL's implicit feature learning advantage is eliminated — the information bottleneck that DL is designed to overcome doesn't exist. Trees exploit this tabular structure directly via axis-aligned splits. This is consistent with Grinsztajn et al. (2022) "Why tree-based models still outperform deep learning on tabular data." | **High priority — needs writing** |
| Limited deployment discussion | Section 7 "Menu of Solutions" framing: H+1=operational stability, H+24=day-ahead planning, quantiles=risk-aware MPC. Production deployment architecture discussed in Section 7. | ✓ Draft done |

### Review 3 — 87/100

| Critique | Journal paper response | Status |
|---|---|---|
| Correlation tie-breaking: which of correlated pair is dropped? | Add sentence to Section 3.3: "For any correlated pair (A, B), feature B (the later column in the upper-triangle scan) is dropped deterministically. This is reproducible: given identical input data, identical features are always removed." | **Needs paper fix** |
| Missing rate definition for "excessive missingness" | Add: "Features with >20% missing values are excluded; those with 5–20% are retained if operationally essential (e.g., solar_Wm2), with a missingness flag appended." | **Needs paper fix** |
| Hardware spec: "exact hardware is not critical" — reviewer disagrees | Replace sentence with: "All experiments were conducted on Apple M3 Pro (18 GB unified memory), TensorFlow 2.x with TensorFlow-Metal backend for GPU acceleration, and scikit-learn 1.x. Training times are reported as wall-clock seconds on this hardware and should be treated as indicative, not absolute." | **Needs paper fix** |

### Review 4 — 48/100

| Critique | Journal paper response | Status |
|---|---|---|
| Central conclusion already established | Acknowledge in Section 2: "While the superiority of gradient boosting on tabular data is established (Grinsztajn et al., 2022; Moosbrugger et al., 2025), this is the first study to test it under paradigm-parity conditions for day-ahead building energy forecasting, and the first to quantify the generalization gap across cities." | ✓ Partially — strengthen |
| Limited SHAP discussion | Add 2–3 sentences to Section 5.3 interpreting the SHAP beeswarm: top features, cross-building consistency, why lag_168h dominates. Reference the SHAP figure. | **Needs writing** |

---

## Cross-Cutting Items (affects all tracks)

| Item | Action | Status |
|---|---|---|
| "accuracy" used for regression | Replace all occurrences of "accuracy" with "prediction error", "forecast error", or metric-specific language (MAE, RMSE, R²). | **Needs find-and-replace** |
| DL hyperparameter justification | Add Table 3: hyperparameters for LSTM/GRU/CNN-LSTM/TFT/PatchTST with brief justification column. See below. | **Needs table** |
| DM significance tests | LightGBM vs Ridge ✓, LightGBM vs XGBoost ✓. Cross-paradigm (vs PatchTST, vs CNN-LSTM_B) — pending saved predictions. | Partially done |

---

## DL Hyperparameter Table (to add as Table 3 in paper)

| Model | Key hyperparameters | Justification |
|---|---|---|
| LSTM | 2 layers, hidden=128, dropout=0.2, dense=128 | Standard LSTM stack; 2 layers sufficient for 72h lookback; dropout prevents overfitting on 45-building portfolio |
| GRU | 2 layers, hidden=128, dropout=0.2, dense=128 | Same as LSTM; GRU uses fewer parameters per layer (no separate cell state) |
| CNN-LSTM | Conv1D(64, k=3) + Conv1D(128, k=3) + LSTM(128), dense=128 | Conv layers extract short-range motifs (3h); LSTM captures longer 72h dependency |
| TFT | hidden=32, heads=4, dropout=0.1, 20 epochs | hidden_size reduced from 64 to avoid overfitting on 45 buildings; 20-epoch hard cap prevents MPS hang |
| PatchTST | patch_len=16, stride=8, d_model=128, heads=16 | NeuralForecast defaults tuned for H+24; patch_len=16 segments 72h lookback into ≈4h patches |
| All DL | Lookback=72h, horizon=24h, batch=32 | 72h captures 3 full daily cycles; 24h = day-ahead horizon |

---

## Summary: What's still needed before journal submission

**High priority (blocks submission):**
1. Section 5.1: Add mechanistic explanation of why DL underperforms (tabular structure argument)
2. Table 3: DL hyperparameter table
3. Section 3.3: Correlation tie-breaking + missingness threshold documented
4. Hardware spec paragraph (replace "exact hardware not critical")
5. "accuracy" → "prediction error" find-and-replace
6. DM cross-paradigm tests (LightGBM vs PatchTST, LightGBM vs CNN-LSTM_B)
7. BESS defined in abbreviations

**Medium priority (strengthens submission):**
8. Section 5.3: SHAP beeswarm interpretation paragraph
9. Prophet: brief footnote explaining deliberate omission
10. DL scaling justification sentence (StandardScaler for DL, not trees)
