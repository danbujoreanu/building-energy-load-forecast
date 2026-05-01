# research/scripts/

Thesis and research artefacts from the MSc AI dissertation (NCI, AICS 2025).
These scripts are not part of the production pipeline and are not imported by any
production code under `src/`, `deployment/`, or `scripts/`.

| Script | Purpose |
|--------|---------|
| `run_tft_only.py` | Train Temporal Fusion Transformer (research baseline) |
| `run_dl_h24_only.py` | Train deep-learning H+24 model (research baseline) |
| `run_grand_ensemble.py` | Grand ensemble across all model variants |
| `generate_paper_figures.py` | Generate journal paper figures (Applied Energy submission) |
| `significance_test.py` | Diebold-Mariano significance tests between models |
| `recover_tft_h1_prediction.py` | One-off recovery of TFT H+1 prediction artifact |
| `run_horizon_sweep.py` | Sweep all horizons H+1…H+24 for horizon analysis |
