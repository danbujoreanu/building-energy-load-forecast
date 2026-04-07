# Run Commands — All Pipeline Scripts
*Copy-paste ready. Python path: `/Users/danalexandrubujoreanu/miniconda3/envs/ml_lab1/bin/python`*

---

## Setup
```bash
cd /Users/danalexandrubujoreanu/building-energy-load-forecast
pip install -e ".[all]"
export $(cat .env | grep -v '#' | xargs)   # load Eddi credentials
```

## Core Pipeline
```bash
# Fast run — sklearn only (~10 min)
python scripts/run_pipeline.py --city drammen --skip-slow

# Full run — all models including DL (~4–6h)
python scripts/run_pipeline.py --city drammen

# Oslo
python scripts/run_pipeline.py --city oslo --skip-slow
```

## Specific Stages
```bash
python scripts/run_pipeline.py --city drammen --stages eda
python scripts/run_pipeline.py --city drammen --stages features
python scripts/run_pipeline.py --city drammen --stages training --skip-slow
python scripts/run_pipeline.py --city drammen --stages explain   # SHAP
```

## PatchTST Setup C
```bash
python scripts/run_raw_dl.py --city drammen --save-predictions
python scripts/run_raw_dl.py --city oslo --save-predictions
```

## Horizon Sweep Sprint 2
```bash
python scripts/run_horizon_sweep.py --city drammen                   # sklearn only
python scripts/run_horizon_sweep.py --city drammen --include-dl      # adds LSTM
python scripts/run_horizon_sweep.py --city drammen --resume          # resume after crash
```

## Significance Tests
```bash
python scripts/significance_test.py --city drammen
```

## Home Demo & Billing
```bash
python scripts/run_home_demo.py --csv /Users/danalexandrubujoreanu/Downloads/HDF_calckWh_10306822417_22-10-2025.csv
python scripts/score_home_plan.py --csv /Users/danalexandrubujoreanu/Downloads/HDF_calckWh_10306822417_22-10-2025.csv
```

## Eddi Logging
```bash
python scripts/log_eddi.py --history 30    # pull 30 days of cloud history
python scripts/log_eddi.py --once          # single snapshot (use in cron at 23:55)
python scripts/log_eddi.py --interval 60  # continuous polling (always-on device only)
```

## Live Inference (Phase 6)
```bash
python deployment/live_inference.py --dry-run    # safe, no device control
python deployment/live_inference.py              # live (uses Eddi API)
```

## Docker (Phase 7)
```bash
make docker-build
make ecr-login    # requires AWS credentials
make ecr-push
make apprunner-deploy
```

## Tests
```bash
pytest tests/ -v --cov=src/energy_forecast
```
