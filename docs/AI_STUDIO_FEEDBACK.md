# External Feedback Log
## AI Studio, AICS 2025 Conference Reviewers, and SINTEF

This document consolidates all external feedback received on the Building Energy Load Forecast
project — from AI Studio (Gemini) reviews of the V2 codebase, AICS 2025 peer reviewers, and
the SINTEF domain expert. It is the authoritative reference for understanding methodology
questions and prioritizing future work.

---

## 1. AI Studio (Gemini) Feedback — V2 Codebase Review

*Source: `Aditional resources/AI Studio feedback.pdf`, recorded 2026-03-01*

### 1A. Why Results Improved So Drastically (+48% to +65% MAE reduction)

AI Studio identified three root causes, **not** model superiority:

#### A. The `lag_1h` Factor ("The Silver Bullet")
- Thesis DL models were fed raw windowed data; they had to **learn** the lag implicitly
- V2 pipeline feeds `lag_1h` (r = 0.977 with target) as an explicit input feature
- Effect: DL models converge instantly — early stopping at epoch 12 instead of 50
- Building energy consumption is highly autoregressive; knowing t≈t−1 makes H+1 trivial

#### B. The Evaluation Horizon (H+1 vs. Multi-step)
- V2 evaluates all models on Single-Step-Ahead (H+1)
- If thesis DL results were for a harder task (multi-step H+24), that explains the gap
- **H+1 with lag_1h is "easy mode"** for energy forecasting (persistence baseline territory)
- Recommendation: Run H+24 to truly prove Trees beat DL on a meaningful task

#### C. Data Quality (43 vs 45 buildings)
- Building 6412: BOM encoding issues; Building 6417: malformed headers
- V2 loader.py handles UTF-8-sig encoding robustly → recovers both buildings
- More data diversity → lower average error across the portfolio

---

### 1B. Feedback on the Engineering Structure

> "Your refactoring is excellent and demonstrates Senior ML Engineer capabilities."

Specific praise:
- **Configuration as Code**: `config.yaml` as single source of truth
- **Reproducibility**: Explicit seeds + parquet caching = trustworthy comparisons
- **Resilience**: try/except blocks mean one bad file doesn't crash the pipeline
- **Modular Stages**: `--stages training` or `--stages eda` run independently

---

### 1C. The "Fair Comparison" Trap

**The Risk**: Publishing "Trees beat Deep Learning by 65%" invites reviewer challenge:
*"Did Trees get engineered features (Lags) that DL didn't receive in the original thesis?"*

**The Fix**: V2 pipeline gives **identical features** (scaled for DL, unscaled for Trees) to
all models. This is a scientifically rigorous comparison. Claim is valid **given this feature set**.

**But — Feature Parity vs. Paradigm Parity**:

> "Give models the data format they were designed for (Paradigm Parity > Input Parity)."

| Model Family | Designed for | Best Practice |
|---|---|---|
| Trees (XGB/LGBM/RF) | Tabular data — no concept of "time" | Engineered features: lags, rolling means, cyclical sin/cos |
| DL (LSTM/TFT) | Raw sequences — **automatically learn** lags internally | Raw 3D tensor: [samples, 72h lookback, raw features] |

**What happens when you give an LSTM your 35 engineered features?**
- 72h window × 35 features = massive redundancy + severe multicollinearity
- The 168h lag is already inside the 72h window at every step
- DL models overfit quickly or get "confused" → **this is why early stopping at epoch 12**
- For TFT specifically: it takes "known future inputs" (weather, time-of-day) and "unknown
  past inputs" (load history) — it should be fed raw sequences in its encoder/decoder format

**Thesis Red Flag (AI Studio identified)**: Table 5, Page 15 of thesis shows:
- Persist-24h (copy yesterday's data): MAE = **8.76**
- LSTM (complex neural network): MAE = **10.13**
- A complex NN performing **worse than copy-paste** is a sign of failure to learn,
  not merely underperformance relative to trees

---

### 1D. The Forecasting Horizon Ground Truth

> "The Verdict: 24H (Day-Ahead) is the industry and academic gold standard."

**The Problem with H+1 (Next-Hour)**:
- Predicting t+1 using t (lag_1h) is "near-trivial" — building thermal mass changes slowly
- A persistence model (next hour = this hour) yields artificially high R²
- Useful for real-time HVAC control; **useless for grid operators** who buy electricity a day ahead

**The Problem with V2 H+1 Evaluation (stated clearly)**:
- For a 24H forecast, standing at midnight predicting tomorrow, you do **not** have lag_1h
  for tomorrow afternoon — only data up to midnight today
- Most recent permissible lag for H+24: **lag_24h**

**V2 code correctly implements `forecast_horizon: 24` mode** — dynamically drops all lags
and rolling windows < 24h. AI Studio: *"This is the exact correct, rigorous way to do it."*

---

### 1E. Weather "Leakage" (The Oracle Trap)

V2 uses **actual observed** `Temperature_Outdoor_C` to predict electricity load for the same hour.

- In the real world: grid operators only have *tomorrow's weather forecast*, not actual weather
- Weather forecasts have errors → using actual weather is an "oracle" advantage
- **Accepted Practice**: Use actual weather as proxy for forecasted weather = *ex-post forecast*
- **Mandatory disclosure**: Must explicitly state this limitation in any paper:
  > *"We utilize actual recorded weather variables under the assumption of perfect
  > meteorological forecasts. Real-world deployment would introduce weather forecast
  > uncertainty."*

---

### 1F. Blueprint for a Bulletproof Journal Paper

| Step | Action |
|---|---|
| 1 | **Define the task**: Day-Ahead Forecasting (24H) |
| 2 | **Trees setup**: XGB/LGBM with minimum lag = 24h (lag_24h, lag_48h, lag_168h) |
| 3 | **DL setup**: LSTM/TFT on 72h sliding window of *raw* data → predict 24h horizon (Seq2Seq) |
| 4 | **Hypothesis**: *"Does automated sequence-learning outperform manual feature-engineering for day-ahead building energy forecasting?"* |

Prediction from AI Studio: *"LightGBM may still beat TFT under these strict conditions —
trees are incredibly strong on tabular data with < 10M rows."*

---

### 1G. Prioritized Next Steps (from AI Studio)

**Phase 1 — COMPLETED**: Compile and submit Camera-Ready PDF for AICS 2025

**Phase 2 — Close the Loop on V2 Codebase**:
- Run DL models (LSTM, GRU, CNN-LSTM, TFT) on V2 pipeline — **DONE** (overnight run completed)
  - LSTM: MAE=3.582, GRU: MAE=3.947, CNN-LSTM: MAE=4.572
  - TFT: fixed (pytorch-lightning 2.x import bug), needs final overnight validation run
- Update README.md table with final DL numbers — **DONE**

**Phase 3 — Elevate to Industry Standards (Next 1–2 Months)**:
- **Implement H+24 Day-Ahead Forecasting** — `forecast_horizon: 24` in config.yaml
  - Trains/evaluates without lag_1h through lag_23h
  - Proves understanding of real business problem (grid operators, battery scheduling)
- **Out-of-Fold (OOF) Stacking** — replace fixed-validation-set ensemble with K-Fold CV
  - Gold standard for ensembles (Kaggle Grandmaster approach)
  - Prevents meta-learner from overfitting to single validation period
- **Probabilistic Forecasting (Quantile Regression)** — LightGBM quantile objective
  - Predict 10th, 50th, 90th percentiles instead of point forecasts
  - Energy managers need risk bounds, not just expected load

**Phase 4 — Prove Generalization (Medium-Term)**:
- **Run on Oslo Dataset** — switch `city: oslo`, run without changing hyperparameters
  - Reviewer 2 (Full Paper) explicitly called out single-dataset limitation
  - Proving pipeline generalizes → "universally valuable" methodology

**Phase 5 — Career Leverage (Ongoing)**:
- Dual-threat profile: Published AICS 2025 researcher + production ML engineer
- CV Highlight 1: "Published peer-reviewed research on STBELF at AICS 2025"
- CV Highlight 2: "Refactored academic notebooks into production ML pipeline, MAE −48%"

---

## 2. AICS 2025 Conference Reviewer Feedback

*Source: `AICS 2025 (Full Paper) - Feedback.pdf` and `AICS 2025 (Student Paper _ Companion Proceedings) Feedback.pdf`*
*Date: 8 November 2025*

### Outcome

Paper accepted to **both tracks**:
- **Full Paper** (Paper 179) → Springer Nature, CCIS Series (main conference proceedings)
- **Student Paper** (Paper 178) → DCU Press, AICS 2025 Companion Proceedings
- Conference: 33rd AICS, 1–2 December 2025, Dublin (Hyatt Centric The Liberties)
- Camera-ready deadline: 10 December 2025

---

### 2A. Full Paper Reviewers (Paper 179)

#### Reviewer 1 — Score: 76/100

**Strengths:**
- Very well written; code available for reproducibility; compelling latency-to-performance comparison

**Weaknesses / Points to Address:**
1. "Deep learning models are generally better suited to raw data. It appears as though engineered
   features were used here: *'Sequence models operate on 3D tensors built via a sliding window
   (lookback 72, horizon 24) from the scaled feature panel.'*" → **Feature parity debate**
2. Why are Prophet-style time series models not compared?
3. Why scale for DL but not for ensembles?
4. How were DL model depth/hyperparameters decided?

**Nitpick**: The word "accuracy" is used throughout when discussing regression.
→ *In ML, "accuracy" strictly refers to classification tasks. Use "error", "loss", or "predictive performance".*

**Resolution**: Scrubbed "accuracy" from the final paper; framed feature parity as an explicit
experiment in *representation* (feature engineering + trees vs. tabularized DL).

---

#### Reviewer 2 — Score: 64/100

**Strengths:** Methodologically sound; authors aware of limitations

**Weaknesses:**
- Not hugely innovative
- **Single dataset** → results may not generalise to other contexts
- DL models might become more competitive with further tuning

**Minor Comments**: BESS is undefined; Section 6.2 should use sentences not note form

---

#### Reviewer 3 — Score: 85/100

> "Very clear, good structure, to the point."

No significant issues. Best score among Full Paper reviewers.

---

#### Reviewer 4 — Score: 78/100

**Feedback:** "Well written. Solid work and well presented."
- Only recommendation: **Figure 3 is not required** (data is comprehensible from Table 1 alone)

---

### 2B. Student Paper Reviewers (Paper 178)

#### Reviewer 1 — Score: 76/100

Good feature engineering work; demonstrates importance of explicit FE vs. feature learning.
"Single case study — unclear how much results depend on specific dataset/hyperparameter tuning."

---

#### Reviewer 2 — Score: 19/100 ⚠️ (Harshest review)

**Strengths identified:**
- Leakage-safe pipeline applied consistently across all model families
- Comprehensive evaluation (RF, XGB, LGBM, LSTM, CNN-LSTM, Transformer)
- Reproducibility: code repository + clear methodology description

**Weaknesses (major):**
1. **Limited novelty**: Primarily benchmarking existing methods; incremental contribution
2. **Writing and presentation**: Bullet-based and descriptive reporting; lacks narrative flow;
   "diminishes impact despite reasonable results"
3. **Contextual limitations**: Single Nordic municipal portfolio; minimal broader applicability discussion
4. **Shallow interpretive analysis**: "Limited exploration of why deep models underperform
   or under which conditions they might be competitive"

**Suggestions:**
- Emphasize methodological innovation OR broader generalization study
- Improve narrative writing (conventional, flowing academic style)
- Include deeper interpretive analysis (model behaviour across building types, weather, occupancy)
- Discuss implications for deployment in other climates

---

#### Reviewer 3 — Score: 87/100 ✅ (Best student paper score)

> "Overall, very interesting and excellently written paper."

*"This work aligns with recent studies demonstrating the superiority of tree-based models over
deep neural networks on tabular data. A step forward: demonstrates this in energy demand
forecasting, not just classification/regression."*

**Minor clarity issues:**
1. Feature correlation filter: how is which feature of a highly-correlated pair chosen to drop?
   Is one dropped randomly? What is "excessive missingness" threshold?
2. "Exact hardware is not critical" — disagrees; hardware + software environment matters for fair
   DNN benchmarks (PyTorch vs. TF yield different results). *Concedes: because trees are
   significantly faster, this is largely negligible for the main conclusion.*

---

#### Reviewer 4 — Score: 48/100

**Strengths:**
- Exemplary experimental setup — controls for data leakage, identical features, transparent reporting
- Valuable for practitioners; evidence-based model selection under realistic compute budgets
- Well written, well-structured

**Weaknesses:**
- Central conclusion (trees > DL on tabular structured data) is **already well established** in literature
- Limited analysis into **why** tree models succeed and **when** DL might catch up
- SHAP and feature importance mentioned but little in-depth discussion of model behaviour across scenarios

---

### 2C. What Reviewers Flagged — and How V2 Addresses Each

| Reviewer Criticism | V2 Status / Response |
|---|---|
| DL given engineered features (not raw sequences) | ⚠️ **Open** — valid concern, acknowledged as deliberate "representation experiment" |
| Single dataset — no generalization | 🔵 **Phase 4 planned** — Oslo dataset run |
| "Accuracy" used in regression context | ✅ **Fixed** — scrubbed from final paper |
| Bullet-based writing style | ✅ **Fixed** — narrative paragraphs in final Springer version |
| Figure 3 redundant | ✅ **Fixed** — removed |
| No Prophet/time-series models compared | 🔵 **Noted** — out of scope for current paper |
| Feature correlation drop rule unclear | 🔵 **To document** — lower variance feature dropped; missingness > column_min_coverage |
| Shallow "why" analysis for DL failure | 🔵 **Partial** — SHAP exists; mechanistic explanation weak |
| H+24 day-ahead horizon not tested | 🔵 **Phase 3 planned** |

---

## 3. SINTEF Expert Feedback

*Source: Verbal / informal feedback from SINTEF domain representative*
*Recorded from user notes, 2026-02-28*

### Key Points

1. **Tree models are good for this domain** — validated by SINTEF representative
2. **DNNs with transformer architectures can be very accurate** — but require significant time
   to understand and train properly
3. **Solar radiation as future feature** — `Global_Solar_Horizontal_Radiation_W_m2` already
   loaded in V2 but excluded from feature pool. Expert validated this as a meaningful addition:
   - Sunny day → building retains heat better → lower heating energy demand
   - Currently treated as Phase 2 addition (not yet in feature selection)

---

## 4. Methodology Ground Truth — H+1 vs H+24

*Critical question: "In my thesis, did I use H+24 for DL and H+1 for sklearn? Is the comparison fair?"*

### Verified Answer (from reading thesis notebook `3. Drammen_Model_Training_Final.ipynb`)

**The thesis used H+1 for ALL models — both DL and sklearn.**

Code evidence from thesis notebook:
```python
# LSTM evaluation (line ~2763):
y_true_flat = y_test_dl[:, 0]   # first step of the horizon
y_pred_flat = y_pred_lstm_test[:, 0]
model_performance_results = evaluate_predictions(y_true_flat, y_pred_flat, "LSTM", ...)

# CNN-LSTM evaluation (line ~2799):
y_true_flat_cnn = y_test_dl[:, 0]
y_pred_flat_cnn = y_pred_cnn_lstm_test[:, 0]

# Best DL model (line ~2959):
y_pred_dl_first_step = best_dl_model.predict(test_ds_tf)[:, 0]  # Select first hour (H+1)
y_true_dl_first_step = y_test_dl[:, 0]
```

Multiple H+1 references throughout the notebook (lines 5690, 5722, 5858, 6362, 6364, 6367,
6386, 6390, 6401, 6417, 6424, 6426, 6435, 6467, 6469).

**The difference**: Thesis DL models trained with **multi-step output** (horizon=24, predicting
24 steps simultaneously) but evaluated **only on step 0** (H+1). V2 trains DL for single-step
output (horizon=1) directly. The evaluation is the same — H+1 — but the training task differs.

### Is the V2 Comparison Fair Within H+1?

**Yes — V2 is internally consistent and scientifically rigorous:**
- All models (Trees + DL) evaluated on identical test set
- Same 35 features given to all (the deliberate "representation experiment")
- Same chronological splits (no data leakage)
- Same evaluation metrics (MAE, RMSE, MAPE, R²)

**The nuance (per AI Studio feedback)**:
- Thesis comparison was Trees (tabular, H+1) vs. DL (multi-step trained, H+1 evaluated)
- V2 comparison is Trees (tabular, H+1) vs. DL (single-step trained, H+1 evaluated)
- V2 actually gives DL a **fairer** shot because the training objective matches evaluation
- DL still underperforms Trees significantly → conclusion is even stronger in V2

### What Would Make It Stronger (Future Work)

For journal publication (H+24 evaluation):
```
Trees: lag_24h minimum, lag_48h, lag_168h, 24h rolling windows only
DL:   raw 72h sliding window → 24-step ahead (Seq2Seq), no engineered lags
Both: lag_1h through lag_23h EXCLUDED
```
This is already implemented in V2 via `forecast_horizon: 24` in `config.yaml`.

---

## 5. Original Thesis Methodological Issues Identified

*Cross-reference: AI Studio feedback + AICS reviewer feedback*

| Issue | Description | Status |
|---|---|---|
| **Feature Parity Trap** | DL models given 35 engineered features in 72h window → massive redundancy and multicollinearity → early stopping, poor learning | ✅ Acknowledged; framed as representation experiment |
| **H+1 Scope Mismatch** | Thesis abstract claimed "1–24h horizons" but evaluated strictly H+1 | ✅ Fixed — final paper explicitly scopes to H+1 |
| **"Accuracy" Terminology** | Used "accuracy" for MAE/RMSE/R² (classification term) | ✅ Fixed — removed from final paper |
| **Bullet-Point Writing** | Overreliance on lists; conference papers need narrative flow | ✅ Fixed — Springer LNCS format |
| **23/6 Denominator Bug** | Cyclical time encoding used 23/6 instead of 24/7 — collapsed endpoint categories | ✅ Fixed in V2 features |
| **Stacking on Validation Only** | DL training cost precluded OOF stacking → meta-learner overfitting risk | 🔵 Planned fix (Phase 3) |
| **2 Dropped Buildings** | Buildings 6412, 6417 dropped due to encoding issues | ✅ Fixed — V2 loader.py recovers both |
| **Weather Oracle** | Actual observed weather used for same-hour prediction | 🔵 Limitation stated in paper; fix in Phase 3 |

---

*Last updated: 2026-03-01*
*Author: Dan Alexandru Bujoreanu*
*Project: building-energy-load-forecast v2*
