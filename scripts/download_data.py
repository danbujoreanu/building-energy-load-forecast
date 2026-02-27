#!/usr/bin/env python
"""
download_data.py
================
Downloads the Oslo dataset from SINTEF's open data repository.

The Drammen dataset files must be placed manually in data/raw/drammen/
(they are included in the repository for reproducibility).

Usage
-----
    python scripts/download_data.py --dataset oslo
    python scripts/download_data.py --dataset all
"""

import argparse
import logging
from pathlib import Path

from energy_forecast.utils import setup_logging, load_config

logger = logging.getLogger(__name__)

# SINTEF Oslo dataset — DOI: 10.60609/2hvr-wc82
OSLO_DATASET_URL = "https://data.sintef.no/product/dp-679b0640-834e-46bd-bc8f-8484ca79b414"
OSLO_BUILDING_IDS = list(range(8091, 8139))   # 48 buildings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download building energy datasets")
    parser.add_argument(
        "--dataset",
        choices=["oslo", "all"],
        default="oslo",
        help="Which dataset to download.",
    )
    parser.add_argument("--config", default=None)
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    cfg  = load_config(args.config)

    if args.dataset in ("oslo", "all"):
        out_dir = Path(cfg["paths"]["raw_data"]["oslo"])
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Oslo dataset (48 buildings) requires manual download:")
        logger.info("1. Visit: %s", OSLO_DATASET_URL)
        logger.info("2. Download all CSV files")
        logger.info("3. Place them in: %s", out_dir.resolve())
        logger.info("")
        logger.info("Alternatively, if you have the files locally, run:")
        logger.info("   cp /path/to/oslo/files/*.csv %s/", out_dir.resolve())
        logger.info("")
        logger.info("Citation: Lien et al. (2025), Data in Brief.")
        logger.info("License: CC BY 4.0")


if __name__ == "__main__":
    main()
