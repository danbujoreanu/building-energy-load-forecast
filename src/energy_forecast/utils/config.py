"""Load and validate the YAML configuration file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load config/config.yaml (or a custom path) and return as a dict.

    Parameters
    ----------
    config_path:
        Path to the YAML config file.  If None, searches up from the current
        working directory for ``config/config.yaml``.
    """
    if config_path is None:
        config_path = _find_config()

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open() as fh:
        cfg = yaml.safe_load(fh)

    return cfg


def _find_config() -> Path:
    """Walk up the directory tree to find config/config.yaml."""
    here = Path.cwd()
    for parent in [here, *here.parents]:
        candidate = parent / "config" / "config.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find config/config.yaml. "
        "Run scripts from the project root directory."
    )
