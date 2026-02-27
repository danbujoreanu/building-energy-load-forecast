# How to Run the Pipeline

This guide replaces the old Jupyter notebook workflow.
Previously you ran 3 notebooks in sequence. Now you run **one command**.

---

## Old workflow vs. New workflow

| Before (thesis notebooks) | After (this repo) |
|---------------------------|-------------------|
| Open Jupyter, run Notebook 1 manually | `python scripts/run_pipeline.py --stages eda` |
| Open Jupyter, run Notebook 2 manually | `python scripts/run_pipeline.py --stages features` |
| Open Jupyter, run Notebook 3 manually | `python scripts/run_pipeline.py --stages training` |
| Everything in one go | `python scripts/run_pipeline.py --city drammen` |
| Change a parameter → find it buried in a cell | Change one line in `config/config.yaml` |

---

## Step 0 — One-time setup

Open a Terminal, then:

```bash
# Go to the project
cd ~/building-energy-load-forecast

# Create a virtual environment (keeps your machine clean)
python -m venv .venv
source .venv/bin/activate          # Mac/Linux
# .venv\Scripts\activate           # Windows

# Install everything
pip install -e ".[all]"
```

You only need to do this once. Next time, just `source .venv/bin/activate`.

---

## Step 1 — Check the config

Open `config/config.yaml` in any text editor. The key settings:

```yaml
city: drammen          # change to "oslo" when ready

sequence:
  lookback: 72         # hours of history the model sees (3 days)
  horizon:  24         # hours ahead to forecast (1 day)

seed: 42               # change this to run a different random seed
```

Everything else can be left as-is for a standard run.

---

## Step 2 — Run the pipeline

### Option A: Full run (all models, ~10+ hours on CPU due to LSTM/TFT)
```bash
python scripts/run_pipeline.py --city drammen
```

### Option B: Skip slow models ← recommended for most runs
```bash
python scripts/run_pipeline.py --city drammen --skip-slow
```
This skips LSTM (~3h 45m), CNN-LSTM (~37m), and TFT (~6h).
You still get Random Forest, XGBoost, LightGBM, and Stacking — which are the **best performing models** anyway.

### Option C: Run one stage at a time
```bash
# Stage 1: EDA (parse files, clean, save processed data)
python scripts/run_pipeline.py --city drammen --stages eda

# Stage 2: Feature engineering (lag, rolling, cyclical, selection)
python scripts/run_pipeline.py --city drammen --stages features

# Stage 3: Train models and evaluate
python scripts/run_pipeline.py --city drammen --stages training --skip-slow
```

Stages remember their outputs — if you already ran EDA, running features won't re-parse the raw files.

---

## Step 3 — View results

After training, results are saved automatically:

```
outputs/
├── results/
│   └── final_metrics.csv          ← Model comparison table (all metrics)
└── figures/
    ├── model_comparison_mae.png    ← Bar chart comparing all models
    ├── building_profiles.png       ← Daily load profiles per building
    ├── temperature_sensitivity.png ← Electricity vs. outdoor temperature
    └── seasonal_patterns.png       ← Monthly + hourly distributions
```

Open them with any image viewer, or load the CSV in Excel.

---

## Training time reference (from MSc thesis, Apple Silicon)

| Model | Train time | Skip with --skip-slow? |
|-------|-----------|------------------------|
| LightGBM | ~3 seconds | No |
| XGBoost | ~3 seconds | No |
| Stacking Ensemble | <1 second | No |
| Random Forest | ~2 minutes | No |
| CNN-LSTM | ~37 minutes | **Yes** |
| LSTM | ~3 hours 45 min | **Yes** |
| TFT | ~6 hours | **Yes** |

---

## Running tests

```bash
pytest tests/ -v
```

All 19 tests should pass. The test suite uses synthetic data — no raw files needed.

---

## Switching to the Oslo dataset

```bash
# 1. Get the data (follow the instructions printed)
python scripts/download_data.py --dataset oslo

# 2. Place your oslo CSV files in data/raw/oslo/

# 3. Change one line in config/config.yaml:
#    city: oslo

# 4. Run the pipeline
python scripts/run_pipeline.py --city oslo --skip-slow
```

---

## Common issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: energy_forecast` | Run `pip install -e .` from the project root |
| `FileNotFoundError: config/config.yaml` | Run scripts from the project root, not from inside `scripts/` |
| LightGBM import error on Mac | `brew install libomp` |
| TFT import error | `pip install pytorch-forecasting pytorch-lightning` |
| Out of memory during TFT | Reduce `batch_size` in `config.yaml` under `training.tft` |
