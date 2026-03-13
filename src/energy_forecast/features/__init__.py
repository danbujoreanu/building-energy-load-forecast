"""Feature engineering: temporal encoding, lag/rolling features, and selection."""

from .selection import select_features
from .temporal import build_temporal_features

__all__ = ["build_temporal_features", "select_features"]
