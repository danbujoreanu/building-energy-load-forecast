# Activation Functions — Architecture Notes and Trade-offs

**Last updated:** 2026-03-15
**Scope:** Setup B (DL + engineered features) and Setup C (DL + raw sequences)

---

## Setup A — Tree-Based Models (no activations)

Setup A (LightGBM, XGBoost, RandomForest, Ridge, Lasso) does not use activation
functions. Decision trees split on feature thresholds; linear models use no
non-linearity at all. This is precisely why Setup A generalises extremely well to
unseen buildings and cities with minimal tuning — there is no internal non-linearity
to overfit.

---

## Setup B — Deep Learning on Engineered Features

All three DL models (LSTM, GRU, CNN-LSTM) in `src/energy_forecast/models/deep_learning.py`
follow the same activation pattern:

| Layer type | Activation | Reason |
|---|---|---|
| LSTM recurrent kernel | **tanh** (Keras default) | Standard — squashes cell state to [−1, 1], prevents unbounded growth |
| LSTM gate (input, forget, output) | **sigmoid** (Keras default) | Outputs gate ∈ (0, 1) — gates must be probabilities |
| GRU recurrent kernel | **tanh** (Keras default) | Same as LSTM |
| GRU gate | **sigmoid** (Keras default) | Same as LSTM |
| Dense hidden (LSTM, GRU, CNN-LSTM) | **ReLU** | Fast convergence, no vanishing gradient in projection layers |
| Conv1D (CNN-LSTM) | **ReLU** | Sparse activation — detects positive load-pattern motifs |
| Final Dense(horizon) — all models | **linear** (no activation) | Regression output; must allow negative residuals freely |

### Why linear on the output layer?

This is a critical correctness fix from the thesis pipeline. In the original thesis,
the output Dense layer inherited `activation="relu"` from copy-paste. ReLU clips
any value < 0 to zero, introducing systematic bias on near-zero load windows
(overnight/weekend periods). The v2 pipeline uses `Dense(horizon)` with no
activation keyword — Keras defaults to linear — which is the correct choice for
unbounded regression.

### Why ReLU in hidden Dense layers?

ReLU was chosen over tanh for the projection Dense layers for two reasons:

1. **Vanishing gradient**: tanh saturates at ±1; for deep stacks of Dense layers,
   gradients shrink multiplicatively. ReLU's gradient is exactly 1 for all positive
   pre-activations, which stabilises training.

2. **Sparse representation**: ReLU produces sparse hidden representations (many units
   output 0 for a given input). For energy load data dominated by repeated daily
   patterns, sparse coding is efficient — most units specialise in specific
   hour/building combinations and stay silent otherwise.

### Tanh vs ReLU on Apple Silicon (MPS)

The root ROADMAP.md notes an empirical finding: *"Tanh activation triggers hardware
acceleration on Apple Silicon (MPS), achieving ~10x speedup over ReLU."* This was
observed during early experimentation. If this holds, switching the Dense hidden
layers to tanh could dramatically reduce training time on M-series Macs at the cost
of potentially slightly slower convergence.

**This has not been applied to the current pipeline.** The current setup (ReLU in
Dense hidden layers) produces final results used in the journal paper and is the
baseline. If Sprint 2 horizon sweep re-training is needed, testing tanh for hidden
Dense layers is a low-risk change worth benchmarking — particularly for the
CNN-LSTM which has the most Dense hidden compute.

**Recommendation**: Benchmark tanh in Dense hidden layers for Setup B during Sprint 2
re-trains. If training time drops significantly with no MAE regression, adopt it and
document as a pipeline improvement in the journal paper's reproducibility section.

---

## Setup C — Deep Learning on Raw Sequences (PatchTST)

PatchTST (`src/energy_forecast/models/patchtst.py`) uses the Transformer architecture:

| Layer type | Activation | Reason |
|---|---|---|
| Multi-head self-attention | — (no activation, scaled dot-product) | Attention weights computed via softmax |
| Attention softmax | **softmax** | Normalises attention scores to sum to 1 |
| Feed-Forward Network (FFN) layers | **GELU** | Standard in transformers; smoother gradient than ReLU near zero |
| Final projection (forecast head) | **linear** | Regression output, same reasoning as Setup B |

### Why GELU in PatchTST vs ReLU in LSTM/GRU?

GELU (Gaussian Error Linear Unit) is the standard for Transformer FFN blocks
(BERT, GPT, PatchTST all use it). GELU is a smooth approximation to ReLU:

```
GELU(x) = x · Φ(x)   where Φ is the Gaussian CDF
```

The smooth gradient near zero helps transformers with very small pre-activations
(common in multi-head attention outputs after layer normalisation). For
LSTM/GRU-style Dense projections, ReLU works equally well and is computationally
cheaper.

**PatchTST's GELU partially explains why it outperforms CNN-LSTM/GRU in Setup C
(6.955 vs 8.0–8.4 kWh).** The patch-based temporal segmentation is the primary
factor, but the smoother GELU activations and the positional encoding together
create a better-calibrated sequence model for longer temporal dependencies
(24h+ patterns).

---

## Activation Function Summary Table

| Model | Hidden activation | Output activation | Training time (H+24) | MAE (kWh) |
|---|---|---|---|---|
| LightGBM (Setup A) | N/A | N/A | ~3 min | 4.029 |
| Ridge (Setup A) | N/A (linear) | N/A | <1 min | 7.460 |
| PatchTST (Setup C) | GELU (FFN) | linear | ~35 min | 6.955 |
| CNN-LSTM (Setup C) | ReLU | linear | ~45 min | 8.040 |
| CNN-LSTM (Setup B) | ReLU | linear | ~45 min | 9.375 |
| GRU (Setup B) | ReLU (Dense), tanh (recurrent) | linear | ~40 min | 9.639 |
| TFT (Setup B) | GLU (gating), ELU (temporal) | linear | ~94 min | 8.770 |
| LSTM (Setup B) | ReLU (Dense), tanh (recurrent) | linear | ~40 min | 8.380 |

### Key trade-off narrative for the paper

The activation function choice is not the primary differentiator between paradigms.
Setup A's advantage over Setup B/C stems from the representational match between
gradient boosting decision trees and the tabular, feature-rich building data —
not from activation functions. Within Setup B/C, activation choices affect:

1. **Training stability** — linear output prevents clipping bias (H+24 correctness)
2. **Training speed** — ReLU vs tanh in Dense layers affects MPS hardware acceleration
3. **Sequence modelling quality** — GELU in PatchTST contributes to better calibration
   of the attention-based temporal model

These are documented as implementation details in Section 3 of the journal paper,
not as primary experimental variables.

---

## Future Work (Sprint 2+)

- Benchmark tanh vs ReLU in Dense hidden layers for CNN-LSTM/GRU/LSTM training time
  on M3/M4 Mac (MPS backend)
- Consider GELU in CNN-LSTM Dense projection layers to align with PatchTST FFN style
- Swish activation (used in MobileNet-style models) — similar to GELU, worth a brief
  sensitivity experiment if DL training is revisited in sprint 2
