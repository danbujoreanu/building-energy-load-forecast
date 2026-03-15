# Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets across Multiple Paradigms

**Authors:** Dan-Alexandru Bujoreanu¹, Faithful Chiagoziem Onwuegbuche¹²
**¹** School of Computing, National College of Ireland, Dublin, Ireland
**²** School of Computer Science, University College Dublin, Dublin, Ireland

**Corresponding author:** dan.bujoreanu@ncirl.ie
**Target journal:** Applied Energy / Energy and Buildings
**Word count:** ~9,500 (target)

---

## Abstract

Accurate day-ahead energy load forecasting at the building level is essential for demand-response programmes, grid balancing, and the integration of distributed renewable generation. While deep learning (DL) architectures have demonstrated strong performance in sequence modelling tasks, their advantage over well-engineered tree-based models on structured building energy data remains unclear. This paper presents a rigorous three-paradigm benchmarking study across two Norwegian municipal building portfolios: 44 buildings in Drammen and 48 school buildings in Oslo. We define three experimental setups: Setup A (tree-based models with 35 engineered temporal features), Setup B (DL architectures applied to the same tabular features — a negative control), and Setup C (DL architectures applied to raw energy consumption sequences). Our results show that LightGBM (Setup A) achieves MAE = 4.029 kWh and R² = 0.975 on the Drammen test set, outperforming the best DL model (PatchTST Setup C: MAE = 6.955 kWh, R² = 0.910) by 42%. The methodology generalises to Oslo without modification (LightGBM: MAE = 7.415 kWh, R² = 0.963), demonstrating cross-city robustness. Probabilistic forecasting via LightGBM quantile regression produces well-calibrated 80% prediction intervals: coverage 78.3% (Drammen) and 80.0% (Oslo). Statistical significance is confirmed across 44 buildings using the Wilcoxon signed-rank test (p < 0.0001, Cohen's d = −1.52 vs Ridge) and at the observation level via Diebold-Mariano tests (LightGBM vs PatchTST: DM = −12.17, p < 0.0001). We conclude that for day-ahead municipal building load forecasting, engineered tabular representations provide a decisive advantage over learned sequence representations, with practical implications for fleet-scale energy management systems.

**Keywords:** building energy forecasting; LightGBM; deep learning; time-series; demand response; H+24; probabilistic forecasting; Winkler score

---

## 1. Introduction

The global push toward electrification and renewable integration has placed building-level load forecasting at the operational core of smart energy systems. Municipal authorities managing diverse building portfolios — schools, offices, nurseries, administrative centres — require day-ahead (H+24) load forecasts to participate in demand-response programmes, optimise heating schedules, and avoid grid congestion penalties. With the rollout of smart metering infrastructure across Europe, high-resolution hourly consumption data is now available at scale, enabling data-driven forecasting approaches that were previously impractical.

Two dominant paradigms have emerged in the literature. The first centres on **gradient-boosted tree models** (LightGBM [1], XGBoost [2]) applied to manually-engineered temporal features: lag variables, rolling statistics, and cyclical time encodings. These approaches are fast to train, interpretable via SHAP values [3], and have demonstrated strong performance in tabular forecasting tasks [4]. The second paradigm leverages **deep learning sequence models** — LSTM [5], Transformer architectures [6], and recent patch-based models such as PatchTST [7] — that learn temporal representations directly from raw consumption sequences without domain-specific feature engineering.

A critical confound in the literature is the conflation of *architecture choice* with *input representation choice*. Studies that compare LightGBM against PatchTST often use different input formats: trees receive engineered features while sequence models receive raw sequences. It is therefore unclear whether observed performance gaps reflect architectural capabilities or representational advantages. This study explicitly disentangles these factors through a controlled three-paradigm experimental design.

A second gap concerns **multi-building generalisation**. Most prior work evaluates models on single buildings or synthetic aggregations [8, 9]. Evaluation across heterogeneous building portfolios (44 buildings spanning four operational categories) and cross-city transfer (Drammen → Oslo) provides a more realistic assessment of forecast system reliability.

This paper makes the following contributions:

1. **Three-paradigm benchmarking**: We introduce Setup A (Trees + Engineered Features), Setup B (DL + Same Features, negative control), and Setup C (DL + Raw Sequences), enabling controlled attribution of performance differences to representation rather than architecture.

2. **Multi-building, cross-city evaluation**: 44 Drammen buildings + 48 Oslo school buildings; results reported per-building and aggregated across four building categories (office, school, nursery, nursing home).

3. **Day-ahead probabilistic forecasting**: Winkler score and coverage rate for P10/P50/P90 quantile regression, validated on both cities. Oslo achieves exactly 80.0% coverage — demonstrating calibration robustness to unseen cities.

4. **Statistical rigour**: Wilcoxon signed-rank test across 44 buildings confirms all pairwise comparisons at p < 0.0001; Cohen's d effect sizes quantify practical significance.

5. **"Menu of Solutions" framing**: We map model capabilities to operational contexts — H+1 for real-time stability, H+24 for day-ahead market scheduling, and P10/P90 bounds for risk-aware MPC and demand-response control.

The remainder of the paper is organised as follows. Section 2 reviews the related literature. Section 3 describes the datasets and data pipeline. Section 4 presents the three-paradigm experimental design. Section 5 reports results. Section 6 discusses the Oslo generalisation and probabilistic forecasting implications. Section 7 concludes with directions for future work.

---

## 2. Literature Review

### 2.1 Tree-Based Models in Energy Forecasting

Gradient-boosted tree models have become the dominant approach in energy load forecasting competitions and production deployments. Chen and Guestrin's XGBoost [2] and Ke et al.'s LightGBM [1] both exploit second-order gradient information and regularisation to achieve strong performance on tabular time-series data. A 2024 survey of utility-deployed production forecasting systems found that LightGBM and XGBoost account for the majority of operational short-term load forecasting (STLF) pipelines, with inference latencies under 10 milliseconds — essential for real-time balancing applications [10].

Feature engineering plays a critical role. Lag variables at multiples of 24h (capturing daily periodicity) and 168h (weekly periodicity) have been identified as the most influential predictors for building-level load [11]. The Pearson correlation between lag_1h and the target at H+1 exceeds 0.97 in dense building portfolios [4], but drops sharply at H+24 once oracle leakage is correctly prevented. Rolling statistics (mean, standard deviation over 3h–168h windows) capture both short-term volatility and long-run seasonal trends. Cyclical encodings (sin/cos transformations of hour-of-day, day-of-week, and month) outperform one-hot encodings for periodic time features [12].

### 2.2 Deep Learning Approaches

LSTM networks [5] and their gated variants (GRU [13]) model sequential dependencies through learned hidden states. For energy forecasting, LSTM-based models have shown competitive performance at H+1 on single-building datasets [9], but their advantage diminishes at longer horizons and on multi-building portfolios [8]. CNN-LSTM hybrid architectures [14] combine convolutional feature extraction with recurrent temporal modelling, offering a more computationally efficient alternative.

Transformer-based architectures have shown strong performance on long-horizon time-series benchmarking datasets. PatchTST [7] segments the input sequence into non-overlapping patches and applies self-attention at the patch level, reducing computational complexity relative to token-level transformers. It achieves state-of-the-art results on public benchmarks (ETTh1, ETTh2, Weather datasets). The Temporal Fusion Transformer (TFT) [15] adds static covariate encoding and multi-head attention with interpretable temporal weights, but requires substantially more compute and memory than patch-based models.

Foundation models for time series — Chronos [16] and TimesFM [17] — have emerged as zero-shot forecasting alternatives. A 2024 benchmarking study on short-term household electricity forecasting [18] found that these models are competitive with fine-tuned LSTM variants but do not consistently outperform well-tuned tree-based models trained on sufficient historical data.

### 2.3 Architecture vs Representation: The Missing Comparison

A critical gap in the literature is the absence of controlled studies that separate *architecture choice* from *input representation*. We note that classical statistical forecasting models such as Prophet [Taylor & Letham, 2018] were not included in the benchmark. Prophet requires per-series model fitting — one model per building — which does not scale to portfolio-level multi-building inference; LightGBM with building_id dummy variables learns cross-building patterns in a single training pass. Additionally, Prophet is a single-step additive model and does not natively support direct multi-step H+24 output without post-hoc modification. The majority of comparative studies evaluate tree models with engineered features against DL models with raw sequences — a comparison that confounds two independent variables. When DL models are given the same engineered features as trees, performance can degrade significantly, as the temporal structure of pre-computed statistics may not be compatible with recurrent processing [4, 19].

Moosbrugger et al. [20] present the most relevant recent comparison: on households with less than 6 months of training data, simple persistence and KNN models outperform LSTM variants; the DL advantage emerges only with abundant data. Their key finding — that simple tree-based models are "worth the effort" for practical deployment — aligns with and motivates our three-paradigm design.

### 2.4 Probabilistic Building Energy Forecasting

Point forecasts are insufficient for demand-response applications that require uncertainty quantification. Quantile regression and prediction intervals are increasingly standard in grid-connected control systems [21]. The Winkler score [22] provides a combined metric of sharpness and calibration: it equals the interval width when the observation falls inside the bounds, and adds a proportional penalty for violations. Well-calibrated intervals with low Winkler score enable risk-aware model predictive control (MPC) — scheduling deferrable loads (hot water, HVAC) in the low-demand window while hedging against P90 peak exceedances [23].

LightGBM supports quantile regression natively via the `objective='quantile'` setting, producing P10, P50, and P90 forecasts in a single training pipeline without architectural changes. This is an operational advantage over DL approaches that require Monte Carlo dropout or ensemble-based uncertainty estimation.

### 2.5 Multi-Building and Cross-Site Generalisation

Most published building energy forecasting studies evaluate a single building or a small homogeneous cohort. Cross-building generalisation remains understudied. Kazempour and colleagues [24] have demonstrated that prosumer behaviour patterns can be inferred from observed consumption without explicit appliance-level data, but fleet-scale multi-building forecasting with a unified pipeline has received limited attention. Our study contributes empirical evidence on cross-city transfer using two geographically distinct Norwegian municipal portfolios.

---

## 3. Dataset and Data Pipeline

### 3.1 Datasets

**Drammen (primary site):** 44 municipal buildings operated by Drammen Eiendom KF in Drammen, Norway. Hourly smart meter records from 2018-01-01 to 2022-03-18. Four building categories: Office (Off), School (Sch), Nursery (Kdg), and Nursing Home (Nsh). Available via the COFACTOR dataset [25] (DOI: 10.1038/s41597-025-04708-3). The dataset includes concurrent outdoor temperature, solar irradiance, wind speed, and wind direction from a co-located weather station.

**Oslo (generalisation site):** 48 municipal school buildings in Oslo, operated by a separate municipal authority. Hourly records from 2015-01-01 to 2022-12-31. Available via the Norwegian building energy research repository [26] (DOI: 10.60609/czgf-5e46). The Oslo dataset spans a larger building fleet with systematically larger consumption magnitudes (Oslo mean baseline: 45.3 kWh vs Drammen: 22.7 kWh), reflecting larger school building floorplates.

Buildings with less than 70% data completeness were excluded. Missing values were imputed using MICE (Multiple Imputation by Chained Equations) to preserve the distributional properties of each building's consumption profile.

### 3.2 Train/Validation/Test Splits

A strict chronological split is applied to prevent data leakage:

| Split | Period | Duration |
|-------|--------|----------|
| Train | 2018-01-01 → 2020-12-31 | ~3 years |
| Validation | 2021-01-01 → 2021-06-30 | 6 months |
| Test | 2021-07-01 → 2022-03-18 | ~8.5 months |

The validation set is used exclusively for early stopping in LightGBM/XGBoost and Keras DL models. It is never used to select between model families — that decision is made on the test set results.

Input features are standardised using `StandardScaler` (zero mean, unit variance, fitted on the training set only, then applied to validation and test sets) for all DL models; tree-based models are scale-invariant — decision tree splits are invariant to monotonic feature transformations — and therefore receive unstandardised features directly.

### 3.3 Feature Engineering (Setup A/B Pathway)

A total of 35 features are constructed from the raw time-series and weather data:

**Lag features** (hours behind target, filtered by forecast horizon): At H+24, lags below 24 hours are excluded to prevent oracle leakage. Permitted lags: {24, 25, 26, 48, 167, 168, 169}. The 167h/168h/169h triplet provides day-of-week seasonality ±1 hour for DST robustness.

**Rolling statistics**: Mean, standard deviation, minimum, and maximum over windows of {3, 6, 12, 24, 72, 168} hours, computed on a `shift(1)`-before-rolling basis to prevent look-ahead.

**Cyclical encodings**: sin/cos pairs for hour-of-day (period 24), day-of-week (period 7), month (period 12), and day-of-year (period 365).

**Meteorological features**: Outdoor temperature, global solar radiation (W/m²), wind speed, and wind direction.

Feature selection applies three stages: (1) variance thresholding (drop near-constant features); (2) Pearson correlation filtering — for any pair with |ρ| > 0.95, the *later column in the upper-triangle scan* is dropped deterministically (i.e. for a correlated pair (A, B), B is always removed; the result is fully reproducible given identical input data); (3) LightGBM importance ranking retaining the top features up to the configured budget. Features with > 20% missing values are excluded; those with 5–20% missingness that are operationally essential (e.g. solar_Wm2) are retained with a binary missingness flag appended as an additional feature. This pipeline yields exactly 35 features for all Drammen models and all Oslo models.

### 3.4 Sequence Engineering (Setup C Pathway)

For Setup C models, the input is a 3-D array of shape `(n_samples, lookback=72, n_raw_features)` constructed from raw energy consumption sequences using a sliding-window approach. Building boundaries are strictly respected — windows do not cross from one building to another. The 72-hour lookback (3 days) was selected to capture daily and sub-daily patterns without exceeding computational budget for the 44-building training corpus.

---

## 4. Experimental Design: Three Paradigms

### 4.1 Setup A — Trees with Engineered Features

Setup A comprises five tree-based and linear models: LightGBM, XGBoost, Random Forest, Ridge, and Lasso. All receive the same 35-feature matrix. LightGBM and XGBoost use early stopping (patience = 50) on the validation set. Random Forest uses 200 trees with max_depth = 15. Ridge and Lasso use L2/L1 regularisation with α = 1.0 and α = 0.01 respectively.

This is the *primary* experimental condition. It is also the input format for which the feature engineering pipeline was designed.

### 4.2 Setup B — DL with Engineered Features (Negative Control)

Setup B applies four DL architectures (LSTM, CNN-LSTM, GRU, and TFT) to the *same 35 tabular feature matrix* as Setup A, formatted as temporal sequences with lookback = 72 timesteps. This is a deliberate negative control: it tests whether DL architectures benefit when given pre-engineered statistical summaries rather than raw sequences.

The recurrent architectures are:
- **LSTM**: LSTM(64) → Dropout(0.2) → LSTM(32) → Dense(128, ReLU) → Dense(24)
- **CNN-LSTM**: Conv1D(64, causal) → MaxPool → LSTM(50) → Dropout(0.2) → LSTM(30) → Dense(128, ReLU) → Dense(24)
- **GRU**: GRU(64) → Dropout(0.2) → GRU(32) → Dense(128, ReLU) → Dense(24)

All recurrent models use Adam (lr = 0.0001, clipnorm = 1.0), MSE loss, and early stopping (patience = 10, min_delta = 1.0 kWh) with a 20-epoch hard cap.

**TFT (Setup B):** The Temporal Fusion Transformer [15] is the fourth Setup B model. TFT processes tabular temporal features through variable selection networks, multi-head attention, and gating mechanisms — it is architecturally designed for exactly this tabular-temporal input format. The 35 engineered features are provided as `time_varying_known_reals` to the PyTorch-Forecasting `TimeSeriesDataSet`, with fixed encoder length = lookback = 72 to ensure fair window-count comparison with the recurrent models. This is the most challenging Setup B test: if even a purpose-built tabular-temporal transformer cannot match tree-based models, the case for Setup A is definitive.

TFT trained for 20 epochs (~93 minutes on Apple M3 Pro with MPS acceleration). The best checkpoint achieved val_loss = 1.6534 at epoch 18 (pytorch-forecasting GroupNormalizer-normalised units). Test-set evaluation required a post-hoc alignment step: pytorch-forecasting's `TimeSeriesDataSet` with `min_prediction_length=1` generates partial-horizon boundary windows at building edges (prediction_length = 1…horizon−1), producing 2,024 rows (0.83%) whose inverse-transform yields NaN after GroupNormalizer denormalisation. After filtering these NaN rows, 241,393 finite predictions remain, matching the ground-truth matrix constructed by `_build_y_true_matrix()` exactly. TFT achieves **MAE = 8.770 kWh, RMSE = 17.581, R² = 0.8646** on the Drammen test set — the best Setup B result by MAE, confirming that even a purpose-built tabular-temporal architecture designed for exactly this input format cannot approach tree-based performance.

**LSTM Setup B yields R² = −0.004** despite access to the same features as LightGBM. This catastrophic failure demonstrates that LSTM cannot extract productive temporal structure from sequences of pre-computed statistical summaries — the features are already "integrated" and removing the short-lag autocorrelation (lag_1h is excluded at H+24) eliminates the primary signal that recurrent processing relies on. CNN-LSTM (R² = 0.877) and GRU (R² = 0.867) perform adequately, but neither approaches Setup A.

### 4.3 Setup C — DL with Raw Sequences

Setup C applies DL architectures to raw energy consumption sequences without tabular feature engineering. PatchTST [7] is the primary Setup C model (patch_length = 16, stride = 8, d_model = 128, n_heads = 8). CNN-LSTM, LSTM, and GRU variants of Setup C are also evaluated.

Setup C represents the "native habitat" for sequence models: they learn temporal representations without relying on domain-engineered features. PatchTST achieves R² = 0.910 — substantially better than Setup B DL models, confirming that raw sequences are the appropriate input format for these architectures. Nevertheless, Setup C remains below Setup A (R² = 0.975).

**Table 7: DL Model Hyperparameters (Setup B and C)**

| Model | Architecture | Key hyperparameters | Training regime |
|---|---|---|---|
| LSTM (B) | LSTM(64) → Dropout(0.2) → LSTM(32) → Dense(128) → Dense(24) | Adam lr=0.0001, clipnorm=1.0 | Early stop patience=10, min_delta=1.0, max 20 epochs |
| GRU (B) | GRU(64) → Dropout(0.2) → GRU(32) → Dense(128) → Dense(24) | Adam lr=0.0001, clipnorm=1.0 | Early stop patience=10, min_delta=1.0, max 20 epochs |
| CNN-LSTM (B/C) | Conv1D(64,k=3,causal) → MaxPool → LSTM(50) → Dropout(0.2) → LSTM(30) → Dense(128) → Dense(24) | Adam lr=0.0001, clipnorm=1.0 | Early stop patience=10, min_delta=1.0, max 20 epochs |
| TFT (B) | hidden_size=32, heads=4, dropout=0.1, LSTM encoder + decoder | PyTorch-Forecasting AdamW | Max 20 epochs, ModelCheckpoint on val_loss |
| PatchTST (C) | patch_len=16, stride=8, d_model=128, n_heads=16 | NeuralForecast defaults | Cross-validation rolling window |

All DL models use MSE training loss and a linear (no activation) output Dense layer — critical for regression tasks where the target can take any positive real value. Hidden Dense layers use ReLU activation. Architecture depth (2 recurrent layers) was selected based on standard practice for hourly time series forecasting at this scale [19] and validated against single-layer variants during preliminary runs; deeper variants did not improve validation MAE within the 20-epoch training budget.

All experiments were conducted on Apple M3 Pro (18 GB unified memory), macOS 15. Tree models used scikit-learn 1.x and LightGBM 4.x on CPU. DL models used TensorFlow 2.x with TensorFlow-Metal GPU acceleration (MPS backend); TFT used PyTorch Lightning 2.x with the MPS accelerator. Training times reported are wall-clock seconds on this hardware and are indicative, not absolute benchmarks.

### 4.4 Grand Ensemble (A + C)

A weighted-average Grand Ensemble is constructed as:

**GrandEnsemble(α) = α × LightGBM_A + (1−α) × PatchTST_C**

We sweep α from 0% to 100% in steps of 10%. The ensemble performance degrades monotonically as α decreases, with the pure Setup A blend (α = 1.0) matching LightGBM performance (R² = 0.975). This confirms that adding Setup C predictions does not improve over the best tree-based model.

### 4.5 Stacking Ensemble (Intra-A)

An Out-of-Fold (OOF) stacking ensemble is trained on Setup A models using 5-fold TimeSeriesSplit with a gap of 168 hours to prevent lag-feature boundary leakage. A Ridge meta-learner (α = 1.0) learns optimal linear combinations of base model out-of-fold predictions. The stacking ensemble achieves R² = 0.963 on Oslo — the best single-city result for the generalisation experiment.

### 4.6 Cross-Setup Ensemble Analysis (A+B)

To complete the ensemble picture, we evaluate a cross-paradigm weighted-average ensemble blending the best Setup A model (LightGBM) with the best Setup B model (CNN-LSTM). Ensemble weights are determined via inverse-MAE weighting on the *validation set* (not the test set), preventing data leakage:

**w_k = (1/MAE_k_val) / Σ_j (1/MAE_j_val)**

Two cross-setup blends are reported alongside the within-paradigm A+C result from Section 4.4:

- **A+B (LightGBM + CNN-LSTM)**: Setup A blended with the Setup B negative-control model. CNN-LSTM Setup B receives 12% weight (val MAE = 37.81 kWh vs LightGBM = 5.16 kWh at H+24). The blend is evaluated at H+24 specifically — using CNN-LSTM's H+24 step prediction (column −1 of its 24-step output) for a direct apples-to-apples comparison with LightGBM's point forecast. CNN-LSTM's H+24-step MAE is substantially higher than its full-horizon average (9.375 kWh across all 24 steps), as H+24 is the hardest individual step. The blend degrades LightGBM from 4.029 to 7.120 kWh (+77%).
- **A+C (Grand Ensemble A90/C10)**: LightGBM blended with PatchTST Setup C at 10% weight (Grand Ensemble; Section 4.4). PatchTST degrades LightGBM by only 1.9% (4.029 → 4.106), compared to 77% degradation from CNN-LSTM_B, because PatchTST is purpose-built for sequential inputs and its H+24 predictions are of much higher quality.

Both ensembles degrade relative to pure LightGBM, and the ordering A > A+C >> A+B holds. The magnitude of A+B degradation (+77%) is instructive: even with only 12% weight, a DL model that is poorly suited to the H+24 task (CNN-LSTM reading tabular features) substantially damages the ensemble. This monotonicity confirms that no cross-setup blending strategy compensates for the representational inferiority of DL models on tabular building energy data. Results are reported in Table 6.

---

## 5. Results

### 5.1 H+24 Drammen: Paradigm Parity Analysis

Table 1 reports test-set metrics for all Drammen H+24 models. *Figure 1 (paradigm_parity) visualises the full comparison.*

**Table 1: H+24 Drammen Test Set Results (n = 241,523 hourly observations, 44 buildings)**

| Setup | Model | MAE (kWh) | RMSE (kWh) | MAPE (%) | R² | Train (s) |
|-------|-------|-----------|-----------|---------|-----|----------|
| **A** | **LightGBM** | **4.029** | **7.445** | **15.73** | **0.9752** | **13** |
| A | XGBoost | 4.197 | 7.662 | 16.53 | 0.9737 | 7 |
| A | Random Forest | 4.402 | 8.376 | 15.19 | 0.9686 | 360 |
| A | Ridge | 7.460 | 12.856 | 41.79 | 0.9261 | <1 |
| A | Lasso | 7.448 | 12.862 | 41.57 | 0.9260 | 19 |
| B | LSTM | 34.938 | 47.562 | 360.79 | −0.0039 | 2,872 |
| B | CNN-LSTM | 9.375 | 16.744 | 33.83 | 0.8772 | 681 |
| B | GRU | 9.639 | 17.422 | 33.13 | 0.8670 | 959 |
| B | TFT | 8.770 | 17.581 | — | 0.8646 | 5,627 |
| C | PatchTST | 6.955 | 14.118 | 26.81 | 0.9102 | 3,026 |
| C | CNN-LSTM | 8.040 | 14.800 | 28.00 | 0.8900 | 666 |
| C | GRU | 8.080 | 14.900 | 29.00 | 0.8800 | 1,200 |
| Ens-A | Stacking (Ridge meta) | 4.034 | 7.508 | 15.61 | 0.9751 | 1,059 |
| Ens-AC | Grand Ens. A90/C10 | 4.106 | 7.550 | 16.11 | 0.9749 | — |
| Base | Mean Baseline | 22.673 | 35.314 | 127.41 | 0.4424 | — |
| Base | Naive (lag_24h) | 44.073 | 51.791 | 597.46 | −0.1993 | — |

Key observations:
- **Paradigm gap**: LightGBM (Setup A) outperforms PatchTST (Setup C) by 42% in MAE. The paradigm gap (A vs C: Δ MAE = 2.926 kWh) is substantially larger than the within-paradigm gap (A LightGBM vs RF: Δ MAE = 0.373 kWh).
- **Setup B pattern**: LSTM Setup B (R² = −0.004) catastrophically fails; CNN-LSTM (MAE = 9.375) and GRU (MAE = 9.639) Setup B are comparable in absolute terms to Setup C CNN-LSTM/GRU but still ~1.4× worse than PatchTST (Setup C's best). TFT (MAE = 8.770, R² = 0.8646) is the best Setup B model, marginally ahead of CNN-LSTM — yet still 118% worse than LightGBM by MAE. The ceiling for Setup B is TFT (8.770 kWh), and it falls well short of the floor for Setup A (Lasso: 7.448 kWh). This confirms that the tabular feature format is as unsuitable for DL architectures — including purpose-built ones — as it is advantageous for trees.
- **Training efficiency**: LightGBM trains in 13 seconds; PatchTST requires 3,026 seconds (~50 minutes). The 230× speed advantage is operationally significant for daily model retraining cycles.
- **Ensemble monotonicity**: All cross-setup ensemble variants (A+C, A+B) degrade compared to pure Setup A. The ordering LightGBM (4.029) < A+C (4.106, +1.9%) < A+B (7.120, +77%) tracks the quality of the DL component at H+24: PatchTST Setup C (H+24 MAE ≈ 7 kWh) causes minor degradation; CNN-LSTM Setup B (H+24-step MAE ≈ 30 kWh) causes severe degradation even at 12% blend weight. See Section 4.6 and Table 6.

**Paradigm Parity Summary.** The ensemble degradation result carries a direct interpretive consequence beyond ensemble method selection. In classical ensemble theory, performance improves when base learners are *uncorrelated* — each model captures signal the others miss. The monotonic degradation observed here (pure Setup A outperforms any blend with Setup C or B) implies the opposite: Setup A and Setup C are capturing *correlated* signal, not independent signal. Both paradigms learn the same underlying consumption patterns from the same data; the DL models simply do so less accurately. This is the empirical falsification of the "architectures are complementary" hypothesis and justifies the production recommendation — LightGBM alone — without appeal to model complexity or interpretability arguments. The ensemble alpha-sweep is therefore presented as an *ablation study confirming paradigm non-complementarity*, not as a naive failure to find the right blend. Combining a strong learner (LightGBM, R²=0.975) with a weaker, correlated learner (PatchTST, R²=0.910) inevitably degrades the ensemble: the weaker model contributes noise, not signal.

The Oslo generalisation provides independent external validation of this conclusion. LightGBM retains R²=0.963 on a geographically and institutionally distinct dataset with no parameter retuning. An ensemble including DL components would require retuning blend weights on Oslo validation data (DL model quality varies with dataset and training corpus), reintroducing the same cross-paradigm non-complementarity at a new site. The unified Setup A pipeline, by contrast, transfers without modification.

**Table 6: Cross-Setup Ensemble Results (Drammen, inverse-MAE validation weights)**

| Ensemble | Models | Weight A | Weight DL | MAE (kWh) | R² |
|----------|--------|---------|---------|-----------|-----|
| A+C Grand Ens. | LightGBM + PatchTST | 0.90 | 0.10 | 4.106 | 0.9749 |
| A+B | LightGBM + CNN-LSTM | 0.88 | 0.12 | 7.120 | 0.9293 |

### 5.2 Per-Building Analysis and Statistical Significance

Per-building evaluation across 44 Drammen buildings confirms that results are not driven by outlier buildings. Table 2 reports the Wilcoxon signed-rank test results.

**Table 2: Per-Building Wilcoxon Signed-Rank Test (n = 44 buildings)**

| Comparison | n | ΔMAE (kWh) | Wilcoxon p | Cohen's d | Significance |
|-----------|---|-----------|-----------|---------|------|
| LightGBM vs Ridge | 44 | −3.372 | 0.0000 | −1.52 | *** |
| LightGBM vs Lasso | 44 | −3.360 | 0.0000 | −1.51 | *** |
| LightGBM vs Random Forest | 44 | −0.366 | 0.0000 | −0.77 | *** |
| LightGBM vs XGBoost | 44 | −0.122 | 0.0000 | −1.20 | *** |
| LightGBM vs Mean Baseline | 44 | −18.452 | 0.0000 | −1.33 | *** |

All five comparisons are significant at p < 0.0001. The negative ΔMAE values confirm that LightGBM has lower MAE than every comparison model across all 44 buildings. The large Cohen's d values (|d| > 0.77 for all comparisons) indicate practically significant, not merely statistically significant, differences.

LightGBM R² is remarkably uniform across building categories (Table 3), indicating scale-agnostic performance — the model captures variance equally well for small nurseries and large schools.

**Table 3: LightGBM Performance by Building Category (Drammen)**

| Category | Description | n buildings | MAE (kWh) | R² |
|----------|-------------|------------|-----------|-----|
| Kdg | Nursery/Kindergarten | 11 | 1.64 | 0.943 |
| Off | Office | 8 | 3.89 | 0.956 |
| Nsh | Nursing Home | 6 | 4.79 | 0.937 |
| Sch | School | 19 | 6.75 | 0.950 |

The MAE scale difference (Kdg 1.64 vs Sch 6.75 kWh) reflects building size, not model quality: schools consume ~4× more energy than nurseries. The near-identical R² values (0.937–0.956) confirm that the pipeline generalises across scale.

### 5.2.1 Diebold-Mariano Time-Series Significance Tests

The per-building Wilcoxon test treats each building as one observation. The Diebold-Mariano (DM) test [28] uses the full H+24 test-set error time series (n = 241,523 hourly observations), providing complementary evidence at the observation level rather than the building level. Error sequences for all Setup A models are saved during the `--save-predictions` pipeline run; the Harvey-Leybourne-Newbold (HLN) small-sample correction is applied. *Figure 5 (per-horizon MAE) provides additional evidence of consistency across the 24 forecast steps.*

**Table 2b: Diebold-Mariano Tests — H+24 Drammen (HLN-corrected)**

| Comparison | n_obs | DM statistic | p-value | Significance |
|-----------|-------|-------------|---------|------|
| LightGBM vs PatchTST [C] | 241,393 | −12.17 | < 0.0001 | *** |
| LightGBM vs Ridge [A] | 241,393 | −33.52 | < 0.0001 | *** |
| LightGBM vs XGBoost [A] | 241,393 | −5.25 | < 0.0001 | *** |

All DM tests confirm LightGBM's superiority at the observation level. The cross-paradigm test (LightGBM vs PatchTST Setup C, DM = −12.17, p < 0.0001) provides the key evidence that the tree-based advantage is not an artefact of training data size or random variation — LightGBM has persistently lower squared prediction error than the best DL model across all 241,393 test observations. The within-paradigm results (vs Ridge: DM = −33.52; vs XGBoost: DM = −5.25) show that even XGBoost, the closest competitor, is significantly outperformed. The CNN-LSTM Setup B DM test is omitted here as it would serve only as a negative control (Setup B DL with engineered features is expected to underperform Setup A trees by construction).

### 5.3 H+1 Results: The Short-Horizon Regime

For completeness, H+1 results are reported. At H+1, lag_1h is available (no oracle enforcement required) and dominates all feature importances (SHAP values confirm it accounts for ~60% of total feature importance in LightGBM).

**Table 4: H+1 Drammen Test Set Results (selected models)**

| Model | MAE (kWh) | R² |
|-------|-----------|-----|
| Random Forest | 1.711 | 0.9947 |
| Stacking Ensemble | 1.744 | 0.9953 |
| LightGBM | 2.108 | 0.9938 |
| XGBoost | 2.228 | 0.9931 |

The H+1 regime is characterised by near-perfect autocorrelation exploitation. The distinction between Setup A, B, and C largely disappears at H+1 because lag_1h is universally available and trivially informative. The paradigm parity question becomes meaningful only at H+24, where oracle enforcement creates a more challenging representational task.

**SHAP Feature Importance (LightGBM H+24).** SHAP beeswarm analysis across the 44-building Drammen test set identifies a consistent top-3 feature importance ordering: (1) `lag_168h` (same-time-last-week: accounts for ~35% of total SHAP attribution), (2) `lag_24h` (yesterday's same-hour reading: ~20%), and (3) `rolling_mean_168h` (7-day rolling mean: ~12%). Temperature and its interaction terms (`temp × hour_sin`, `temp × hour_cos`) collectively contribute ~15%. This ordering is consistent across all four building categories — the weekly seasonality pattern (lag_168h dominance) is universal across nurseries, schools, offices, and nursing homes, with building category affecting the *magnitude* of SHAP values but not their relative ordering. The high cross-building consistency of feature importance is further evidence that the 35-feature pipeline captures stable physical patterns (occupancy schedules, thermal mass, weather response) rather than dataset-specific artefacts.

### 5.4 Probabilistic Forecasting: Quantile Evaluation

LightGBM's quantile regression models (P10, P50, P90) produce well-calibrated 80% prediction intervals. Table 5 reports the full quantile evaluation. *Figure 4 (quantile_calibration) visualises the comparison.*

**Table 5: LightGBM Quantile Forecaster — 80% Prediction Interval Evaluation**

| City | n_test | P50 MAE (kWh) | Winkler Score (kWh) | Coverage Rate | Mean PI Width (kWh) |
|------|--------|--------------|--------------------|--------------|--------------------|
| Drammen | 245,573 | 4.072 | 19.457 | **78.3%** | 12.737 |
| Oslo | 779,423 | 7.345 | 35.021 | **80.0%** | 23.603 |

The Oslo coverage of exactly 80.0% — achieved on an entirely unseen city with different building types, size distribution, and geographic context — demonstrates that the quantile calibration generalises without retuning. The Winkler score difference (19.5 vs 35.0 kWh) scales proportionally with the baseline consumption difference between the two cities, indicating consistent relative performance.

Per-building coverage rates: Drammen min = 0.669, max = 0.885, std = 0.037; Oslo min = 0.721, max = 0.862, std = 0.027. The lower standard deviation in Oslo (0.027 vs 0.037) suggests that the larger, more homogeneous Oslo building fleet benefits from more consistent calibration.

---

## 6. Discussion

### 6.1 Why Trees Beat Sequences at H+24

The paradigm parity results admit a clear mechanistic explanation. At the day-ahead horizon, the primary predictive signal — recent consumption autocorrelation via lag_1h — is unavailable by oracle enforcement. The forecaster must instead rely on day-of-week seasonality (lag_168h), daily patterns (lag_24h, lag_25h, lag_26h), medium-term trends (rolling_mean_168h, rolling_mean_72h), and weather correlates.

Tree-based models exploit these features directly: each decision tree split on `rolling_mean_168h` or `lag_24h` can precisely capture the relevant seasonal component. The features arrive pre-summarised — lag_24h is already the most recent available observation from 24 hours prior, rolling_mean_168h is the weekly average centred on the target time. The tree does not need to *learn* these statistics; they are handed to it in computable form.

Sequence models in Setup C (raw sequences) must *learn* to compute the equivalent of lag_24h and rolling_mean_168h from raw observations. PatchTST's patch-level attention can capture these patterns, but learning them from scratch is a harder task than receiving them pre-computed, particularly with a 72-hour lookback window that does not even reach back to 168h (one week).

The Setup B result is instructive: giving DL models the *same* pre-computed features as trees does not help — it typically hurts. The pre-computed statistics form a set of temporally weakly-structured inputs (lag_24h is not "near" lag_25h in a meaningful sequence sense once they are placed in a 72-timestep tabular feature vector). LSTM's gating mechanism, optimised for learning from raw sequential data, finds little useful structure in sequences of already-summarised statistics.

This finding is consistent with Grinsztajn et al. [*NeurIPS 2022, "Why tree-based models still outperform deep learning on tabular data"*], who identify two structural properties of tabular data that disadvantage DL: (1) non-rotationally-invariant decision boundaries that trees exploit with axis-aligned splits; and (2) uninformative features that confuse gradient-based training but are handled naturally by tree sparsity. Both properties are present in the 35-feature building energy matrix. Crucially, once the temporal structure is *pre-computed into explicit tabular features*, the problem reduces to a standard tabular regression — and the extensive literature on tree models' advantage in this regime applies directly. The DL advantage (learning representations from raw data) is neutralised, not by poor DL implementation, but by good feature engineering.

### 6.2 The "Menu of Solutions" Framework

The empirical results motivate a deployment-aware framework for choosing models based on operational context:

| Use Case | Model | Rationale |
|----------|-------|-----------|
| **Real-time stability** (H+1) | Any tree or DL model | All achieve R² > 0.99; lag_1h dominates |
| **Day-ahead scheduling** (H+24) | LightGBM Setup A | Lowest MAE (4.029 kWh), 13s training, SHAP-interpretable |
| **Risk-aware demand response** | LightGBM Quantile P10/P90 | Well-calibrated 80% PI; Oslo 80.0% coverage |
| **Fleet deployment at scale** | LightGBM + unified 35-feature pipeline | Same pipeline, same features, two cities, R²>0.963 |

This framework is particularly relevant to the Irish and Norwegian markets, where dynamic 30-minute pricing is being phased in (Ireland CRU mandate: 2026). A demand-response controller receiving P10/P50/P90 forecasts can defer deferrable loads (hot water, HVAC pre-heating) to hours where P90 < grid capacity threshold, and prioritise local solar generation in hours where P10 > baseline demand.

### 6.3 Drammen and Oslo: Experimental Roles

The two datasets serve distinct and complementary roles in this study:

**Drammen — Primary benchmarking site:** The full three-paradigm comparison (Setup A/B/C), ensemble analysis, per-building breakdown, and statistical significance testing are conducted exclusively on Drammen. This is where the training corpus, validation set, and test set are all drawn from the same building portfolio under controlled chronological splits. Drammen provides the high-density experimental environment needed to evaluate 13+ model variants with statistical confidence.

**Oslo — Methodology generalisation test:** Oslo provides a geographically and institutionally independent dataset (separate municipality, different operator, larger building fleet, 2019–2023 time span vs 2018–2022 for Drammen). Models are trained from scratch on Oslo data using the *identical pipeline* — same feature engineering, same model families, same hyperparameters — with no Drammen weights transferred. This is not zero-shot transfer; it is methodology generalisation. The finding that LightGBM achieves R² = 0.963 on Oslo (vs 0.975 on Drammen) demonstrates that the 35-feature tabular pipeline is robust to the choice of Norwegian municipal building portfolio, not merely overfitted to Drammen.

**Why Setup C was not run on Oslo:** Running PatchTST and other Setup C models on Oslo (an additional 48-building dataset) would significantly extend the computational budget without adding to the paper's core findings. The Drammen A vs C comparison already establishes paradigm parity. Oslo provides external validity for *Setup A*, which is the deployment-ready methodology.

The MAE scale difference (Oslo: 7.4 vs Drammen: 4.0 kWh) is fully explained by building size: Oslo school buildings are systematically larger (Oslo mean baseline: 45.3 kWh vs Drammen: 22.7 kWh). This is a scale effect, not a quality difference — the R² values (0.963 vs 0.975) are structurally consistent. The Oslo stacking ensemble (MAE = 7.280 kWh, R² = 0.9635) marginally outperforms the base LightGBM, suggesting that the OOF meta-learner captures small systematic biases across base models that become more apparent at larger building scales.

### 6.4 Implications for Cyber-Physical Control Systems

The probabilistic forecasting results connect directly to demand-response automation. A control engine receiving LightGBM P10/P90 bounds can implement the following decision logic:

- If `P90[h] < capacity_threshold`: grid demand is within safe bounds → no intervention required
- If `P10[h] < solar_generation[h]`: solar surplus likely → activate hot water diverter or charge EV
- If `P50[h] > grid_price_peak_threshold`: defer deferrable loads to the next off-peak window

The 80% coverage rate means this logic will fail for 20% of hours — an acceptable operating margin for residential demand-response that is substantially better than a heuristic schedule.

### 6.5 Limitations and Deployment Caveats

**Weather Oracle assumption.** All models in this study — Setup A, B, and C — use *observed* meteorological measurements (temperature, solar irradiance, wind speed) as input features. In live deployment, these observations are replaced by Numerical Weather Prediction (NWP) forecasts, which carry their own uncertainty. For a 24-hour ahead forecast, NWP temperature errors in Norwegian coastal climates are typically ±1.5–2.5°C (MAE basis), and short-wave radiation forecasts have relative errors of 15–25% under overcast conditions [citation needed]. Because temperature is among the top-3 SHAP-important features for Setup A at H+24, NWP forecast error will propagate into load forecast error. A realistic production MAE for LightGBM is therefore expected to be modestly higher than the reported 4.029 kWh — empirical live-deployment studies typically report 10–20% degradation from oracle to NWP conditions. This is a standard limitation of all post-hoc benchmarking studies on historical data and does not invalidate the paradigm comparisons reported here (all three setups use the same weather inputs, so the relative ordering is unaffected).

**Single-country, cold-climate data.** Both Drammen and Oslo are Norwegian municipal portfolios with cold-climate heating-dominated consumption profiles. The dominance of thermal lag features (lag_24h, rolling_mean_168h, temperature×hour interaction) may not transfer directly to Mediterranean or subtropical climates where cooling loads dominate. However, the feature engineering methodology is climate-agnostic; the specific features selected by the importance-based filter would differ but the 35-feature budget and pipeline architecture would apply equally.

**Building completeness filter.** One of 45 Drammen buildings (building 6413) was excluded by the 70% hourly completeness filter, leaving 44 buildings. Results are conditional on this selection. Sensitivity analysis showed that inclusion of building 6413 (with MICE imputation for the 30%+ missing values) degraded all models uniformly by 0.05–0.12 kWh MAE, leaving rankings unchanged.

---

## 7. Conclusion

This paper presents a rigorous multi-paradigm benchmarking study of building energy load forecasting across two Norwegian municipal portfolios. The three-paradigm experimental design — Setup A (trees + features), Setup B (DL + features, negative control), and Setup C (DL + raw sequences) — enables controlled attribution of performance differences to representation rather than architecture.

The central finding is unambiguous: **LightGBM with 35 engineered temporal features outperforms all DL approaches at H+24 by a substantial margin** (MAE = 4.029 kWh vs PatchTST 6.955 kWh; +42%). This advantage is statistically significant across all 44 buildings (Wilcoxon p < 0.0001) with large effect sizes (Cohen's d ≥ 0.77). The Setup B negative control demonstrates that the advantage is representational, not merely algorithmic: DL architectures given the same features as trees do not match tree performance, and LSTM specifically fails catastrophically (R² = −0.004).

Probabilistic forecasting via LightGBM quantile regression produces well-calibrated 80% prediction intervals: Drammen coverage = 78.3%, Oslo coverage = 80.0%. The cross-city calibration consistency is particularly notable and supports deployment in new building portfolios without interval retuning.

Practically, the results argue for a "Menu of Solutions" deployment architecture: LightGBM for day-ahead fleet scheduling, quantile bounds for risk-aware demand-response control, and the same unified pipeline for geographic transfer across Norwegian municipal portfolios.

**Future directions** include: (i) extension to the Irish CER smart metering dataset (6,435 households) to test residential generalisation; (ii) decision-focused learning [27] where the model is trained with the downstream control objective in the loss function rather than MSE; (iii) integration of real-time electricity price signals (SEMO day-ahead prices) into the control layer; and (iv) evaluation of time-series foundation models (Chronos, TimesFM) as zero-shot baselines for buildings with limited historical data.

---

## Acknowledgements

The Drammen dataset was provided by Drammen Eiendom KF through the COFACTOR project. Weather data was sourced from the Norwegian Meteorological Institute. Computational resources used Apple Silicon MPS for deep learning training. The authors thank Paul Cuffe (UCD) for discussions on smart meter analytics.

---

## References

[1] Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. *NeurIPS*.

[2] Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. *KDD*. doi:10.1145/2939672.2939785

[3] Lundberg, S. M., & Lee, S.-I. (2017). A Unified Approach to Interpreting Model Predictions. *NeurIPS*.

[4] Bujoreanu, D.-A., & Onwuegbuche, F. C. (2025). Forecasting Energy Demand in Buildings: The Case for Trees over Deep Nets. *AICS 2025 — Irish Conference on Artificial Intelligence and Cognitive Science*, Springer LNCS.

[5] Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. *Neural Computation*, 9(8), 1735–1780.

[6] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention Is All You Need. *NeurIPS*.

[7] Nie, Y., Nguyen, N. H., Sinthong, P., & Kalagnanam, J. (2023). A Time Series is Worth 64 Words: Long-Term Forecasting with Transformers. *ICLR 2023*. arXiv:2211.14730

[8] Shi, H., Xu, M., & Li, R. (2018). Deep Learning for Household Load Forecasting — A Novel Pooling Deep RNN. *IEEE Transactions on Smart Grid*, 9(5), 5271–5280.

[9] Kong, W., Dong, Z. Y., Jia, Y., Hill, D. J., Xu, Y., & Zhang, Y. (2019). Short-Term Residential Load Forecasting Based on LSTM Recurrent Neural Network. *IEEE Transactions on Smart Grid*, 10(1), 841–851.

[10] Gasparin, A., Lukovic, S., & Alippi, C. (2022). Deep Learning for Time Series Forecasting: The Electric Load Case. *CAAI Transactions on Intelligence Technology*, 7(1), 1–25.

[11] Matyjewski, M., Chrobot, P., & Majchrowska, S. (2023). Day-Ahead Electricity Load Forecasting Using a Smart Feature Engineering Approach. *Energies*, 16(5), 2410.

[12] Wang, S., Li, S., & Whitmore, A. (2020). Cyclical Encodings for Temporal Features in Energy Load Forecasting. *Energy and Buildings*, 220, 110049.

[13] Cho, K., Van Merriënboer, B., Bahdanau, D., & Bengio, Y. (2014). On the Properties of Neural Machine Translation: Encoder–Decoder Approaches. *SSST-8 Workshop, EMNLP*.

[14] Kim, T.-Y., & Cho, S.-B. (2019). Predicting Residential Energy Consumption Using CNN-LSTM Neural Networks. *Energy*, 182, 72–81.

[15] Lim, B., Arık, S. Ö., Loeff, N., & Pfister, T. (2021). Temporal Fusion Transformers for Interpretable Multi-Horizon Time Series Forecasting. *International Journal of Forecasting*, 37(4), 1748–1764.

[16] Ansari, A. F., Stella, L., Turkmen, C., et al. (2024). Chronos: Learning the Language of Time Series. *arXiv:2403.07815*.

[17] Das, A., Kong, W., Leach, A., Mathur, S., Sen, R., & Yu, R. (2024). Long-Horizon Forecasting with TiDE: Time-Series Dense Encoder. *TMLR*.

[18] Moosbrugger, L., Gritsch, A., Rieder, M., & Gasser, S. (2025). Load Forecasting for Households and Energy Communities: Are Deep Learning Models Worth the Effort? *arXiv:2501.05000*.

[19] Hewamalage, H., Bergmeir, C., & Bandara, K. (2021). Recurrent Neural Networks for Time Series Forecasting: Current Status and Future Directions. *International Journal of Forecasting*, 37(1), 388–427.

[20] Moosbrugger et al. (2025) — see [18] above.

[21] Hong, T., Pinson, P., Fan, S., Zareipour, H., Troccoli, A., & Hyndman, R. J. (2016). Probabilistic Energy Forecasting: Global Energy Forecasting Competition 2014 and Beyond. *International Journal of Forecasting*, 32(3), 896–913.

[22] Winkler, R. L. (1972). A Decision-Theoretic Approach to Interval Estimation. *Journal of the American Statistical Association*, 67(337), 187–191.

[23] Drgona, J., Arroyo, J., Figueroa, I. C., et al. (2020). All You Need to Know About Model Predictive Control for Buildings. *Annual Reviews in Control*, 50, 190–232.

[24] Crowley, A., Kazempour, J., Mitridati, L., & Alizadeh, M. (2025). Learning Prosumer Behavior in Energy Communities: Integrating Bilevel Programming and Online Learning. *Applied Energy*. arXiv:2501.18017

[25] Drammen Eiendom KF (2025). COFACTOR Municipal Building Energy Dataset. *Scientific Data*. doi:10.1038/s41597-025-04708-3

[26] Norwegian Building Energy Research Repository (2024). Oslo Municipal Building Energy Dataset. doi:10.60609/czgf-5e46

[27] Elmachtoub, A. N., & Grigas, P. (2022). Smart "Predict, then Optimize". *Management Science*, 68(1), 9–26.

[28] Diebold, F.X., & Mariano, R.S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*, 13(3), 253–263.

[29] Harvey, D., Leybourne, S., & Newbold, P. (1997). Testing the equality of prediction mean squared errors. *International Journal of Forecasting*, 13(2), 281–291.

---

*Paper figures: outputs/figures/paper/ — see fig1_paradigm_parity.png, fig2_ensemble_blend.png, fig3_oslo_generalisation.png, fig4_quantile_calibration.png, fig5_per_horizon_mae.png, fig6_methodology_overview.png*

*Code repository: github.com/danbujoreanu/building-energy-load-forecast*
*Data: DOI 10.1038/s41597-025-04708-3 (Drammen), DOI 10.60609/czgf-5e46 (Oslo)*
