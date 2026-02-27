"""Configure structured logging for the pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str | Path | None = None) -> None:
    """Set up root logger with a consistent format.

    Parameters
    ----------
    level:
        Logging level string: "DEBUG", "INFO", "WARNING", "ERROR".
    log_file:
        Optional path to also write logs to a file.
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )
    # Suppress noisy third-party loggers
    for noisy in ["matplotlib", "PIL", "tensorflow", "torch", "pytorch_lightning"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
