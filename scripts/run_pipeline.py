#!/usr/bin/env python
"""
run_pipeline.py
===============
Full end-to-end pipeline orchestrator.

Usage
-----
    # Full run on Drammen (all models)
    python scripts/run_pipeline.py --city drammen

    # Skip slow models (CNN-LSTM, TFT) — fast development run
    python scripts/run_pipeline.py --city drammen --skip-slow

    # Override config city from CLI
    python scripts/run_pipeline.py --city oslo

Architecture note
-----------------
This is the Task Orchestrator (MSc Engineering & AI Systems lecture) —
it coordinates independent pipeline stages without them knowing about each other.
"""

import argparse
import logging
import time

from energy_forecast.utils import load_config, set_global_seed, setup_logging
from scripts.stages import eda_stage, explain_stage, features_stage, train_stage

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Building Energy Load Forecast — full pipeline"
    )
    parser.add_argument(
        "--city",
        choices=["drammen", "oslo"],
        default=None,
        help="Dataset city. Overrides config.yaml if provided.",
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip slow models: CNN-LSTM and TFT.",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=["eda", "features", "training", "explain"],
        default=["eda", "features", "training"],
        help="Which pipeline stages to run (default: all except explain).",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config YAML (default: auto-detected config/config.yaml).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
    )
    parser.add_argument(
        "--save-predictions",
        action="store_true",
        help=(
            "Save test prediction error arrays to outputs/predictions/ "
            "for use with the Diebold-Mariano test (significance_test.py --mode dm). "
            "Files saved as: {model_name}_h24_test_errors.npy  (e_t = y_true - y_pred)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    cfg = load_config(args.config)
    if args.city:
        cfg["city"] = args.city

    set_global_seed(cfg.get("seed", 42))

    city = cfg["city"]
    logger.info("=" * 60)
    logger.info("Building Energy Load Forecast Pipeline")
    logger.info("City: %s | Skip slow: %s | Stages: %s | Save preds: %s",
                city, args.skip_slow, args.stages, args.save_predictions)
    logger.info("=" * 60)

    t0 = time.perf_counter()

    # ── Stage 1: EDA & Data Loading ───────────────────────────────────────────
    if "eda" in args.stages:
        eda_stage.run(cfg)

    # ── Stage 2: Feature Engineering ─────────────────────────────────────────
    if "features" in args.stages:
        features_stage.run(cfg)

    # ── Stage 3: Model Training & Evaluation ─────────────────────────────────
    if "training" in args.stages:
        train_stage.run(cfg, skip_slow=args.skip_slow, save_preds=args.save_predictions)

    # ── Stage 4: SHAP Explainability ─────────────────────────────────────────
    if "explain" in args.stages:
        explain_stage.run(cfg)

    elapsed = time.perf_counter() - t0
    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds (%.1f min)", elapsed, elapsed / 60)
    logger.info("Results → outputs/results/final_metrics.csv")
    logger.info("SHAP   → outputs/figures/shap/")
    logger.info("Figures → outputs/figures/")
    logger.info("=" * 60)



if __name__ == "__main__":
    main()
