"""Model Registry — full lineage tracking, promotion, rollback, and quality gates.

Registry state is persisted at:
    {registry_dir}/registry.json

Uses atomic writes (write to .tmp, rename) and advisory file locking via
``fcntl.flock`` to be safe under concurrent pipeline runs.

Thread safety: safe for concurrent reads; writes acquire a file lock.
"""

from __future__ import annotations

import dataclasses
import fcntl
import json
import logging
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RegistryError(ValueError):
    """Base exception for all registry errors."""


class ModelRegressionError(RegistryError):
    """Raised when a candidate model's MAE regresses beyond the allowed threshold."""


# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------


class ModelStatus(str, Enum):
    """Lifecycle status of a model version."""

    CANDIDATE = "candidate"  # just trained, not yet evaluated vs baseline
    ACTIVE = "active"  # currently serving in production
    RETIRED = "retired"  # superseded by a newer active version
    FAILED = "failed"  # failed quality gate, never promoted


@dataclass
class ModelMetrics:
    """Evaluation metrics for a single split."""

    MAE: float
    RMSE: float
    R2: float
    MAPE: float | None = None
    training_seconds: float | None = None


@dataclass
class ModelVersion:
    """Immutable record of a trained model artifact and its metadata."""

    version_id: str
    city: str
    model_name: str
    artifact_path: str
    trained_at: str
    git_commit: str
    feature_names: list[str]
    train_metrics: ModelMetrics
    val_metrics: ModelMetrics | None
    test_metrics: ModelMetrics | None
    status: ModelStatus
    config_snapshot: dict
    promoted_at: str | None = None
    retired_at: str | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _metrics_from_dict(d: dict | None) -> ModelMetrics | None:
    """Deserialise a dict into a ``ModelMetrics`` instance, or return None."""
    if d is None:
        return None
    return ModelMetrics(
        MAE=d["MAE"],
        RMSE=d["RMSE"],
        R2=d["R2"],
        MAPE=d.get("MAPE"),
        training_seconds=d.get("training_seconds"),
    )


def _version_from_dict(d: dict) -> ModelVersion:
    """Deserialise a dict into a ``ModelVersion`` instance."""
    return ModelVersion(
        version_id=d["version_id"],
        city=d["city"],
        model_name=d["model_name"],
        artifact_path=d["artifact_path"],
        trained_at=d["trained_at"],
        git_commit=d["git_commit"],
        feature_names=d["feature_names"],
        train_metrics=_metrics_from_dict(d["train_metrics"]),  # type: ignore[arg-type]
        val_metrics=_metrics_from_dict(d.get("val_metrics")),
        test_metrics=_metrics_from_dict(d.get("test_metrics")),
        status=ModelStatus(d["status"]),
        config_snapshot=d.get("config_snapshot", {}),
        promoted_at=d.get("promoted_at"),
        retired_at=d.get("retired_at"),
        notes=d.get("notes", ""),
    )


def _version_to_dict(v: ModelVersion) -> dict:
    """Serialise a ``ModelVersion`` to a plain dict suitable for JSON."""
    return dataclasses.asdict(v)


# ---------------------------------------------------------------------------
# Git helper
# ---------------------------------------------------------------------------


def _get_git_commit() -> str:
    """Return the short HEAD SHA, or 'unknown' if git is unavailable."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return sha.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        logger.debug("git rev-parse failed — using 'unknown' for commit SHA")
        return "unknown"


# ---------------------------------------------------------------------------
# Version ID generation
# ---------------------------------------------------------------------------


def _make_version_id(city: str, model_name: str) -> str:
    """Generate a deterministic-ish, human-readable version ID.

    Format: ``{city}_{safe_model}_{YYYYMMDDTHHmmss}_{uuid4_short}``
    """
    safe_model = model_name.lower().replace(" ", "_").replace("-", "_")
    compact_ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    uid_short = uuid.uuid4().hex[:8]
    return f"{city}_{safe_model}_{compact_ts}_{uid_short}"


# ---------------------------------------------------------------------------
# ModelRegistry
# ---------------------------------------------------------------------------


class ModelRegistry:
    """File-backed model registry for tracking trained model artifacts.

    Registry state is persisted at ``{registry_dir}/registry.json``.
    All mutating operations use an advisory file lock and atomic rename
    so concurrent pipeline runs cannot corrupt state.

    Args:
        registry_dir: Directory where ``registry.json`` and the lock file live.
            Created on first use if it does not exist.

    Example::

        registry = ModelRegistry(Path("outputs/registry"))
        version = registry.register(my_version)
        active = registry.promote_to_active(version.version_id)
    """

    REGRESSION_THRESHOLD: float = 1.05
    MAX_RETIRED_VERSIONS: int = 5

    def __init__(self, registry_dir: Path) -> None:
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._dir / "registry.json"
        self._lock_path = self._dir / "registry.lock"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, version: ModelVersion) -> ModelVersion:
        """Persist a newly trained model version with CANDIDATE status.

        If ``version.version_id`` is empty, a new ID is generated.
        The ``git_commit`` field is populated automatically when not set.

        Args:
            version: The ``ModelVersion`` to register. ``status`` is forced
                to ``CANDIDATE`` regardless of the value supplied.

        Returns:
            The registered ``ModelVersion`` with all fields populated.
        """
        if not version.version_id:
            version = dataclasses.replace(
                version,
                version_id=_make_version_id(version.city, version.model_name),
            )
        if version.git_commit in ("", None):
            version = dataclasses.replace(version, git_commit=_get_git_commit())
        version = dataclasses.replace(version, status=ModelStatus.CANDIDATE)

        with self._write_lock():
            versions = self._load()
            if any(v.version_id == version.version_id for v in versions):
                raise RegistryError(f"version_id '{version.version_id}' already exists in registry")
            versions.append(version)
            self._save(versions)

        logger.info(
            "Registered CANDIDATE version_id=%s  city=%s  model=%s",
            version.version_id,
            version.city,
            version.model_name,
        )
        return version

    def promote_to_active(
        self,
        version_id: str,
        *,
        force: bool = False,
    ) -> ModelVersion:
        """Promote a CANDIDATE version to ACTIVE.

        Checks for metric regression against the currently ACTIVE version for
        the same (city, model_name) pair. If the new test MAE exceeds
        ``REGRESSION_THRESHOLD × active_MAE``, ``ModelRegressionError`` is
        raised unless ``force=True``.

        The previously ACTIVE version is atomically moved to RETIRED before
        the new version becomes ACTIVE.  Retired versions beyond
        ``MAX_RETIRED_VERSIONS`` are pruned from the registry (marked FAILED
        in place; artifact files are never deleted).

        Args:
            version_id: The version to promote.
            force: Skip the regression check (use for first deploy or emergency).

        Returns:
            The newly ACTIVE ``ModelVersion``.

        Raises:
            ModelRegressionError: New MAE exceeds the quality gate.
            ValueError: ``version_id`` not found or not in CANDIDATE status.
        """
        with self._write_lock():
            versions = self._load()
            candidate = self._find_version(versions, version_id)

            if candidate is None:
                raise ValueError(f"version_id '{version_id}' not found in registry")
            if candidate.status != ModelStatus.CANDIDATE:
                raise ValueError(
                    f"version_id '{version_id}' is {candidate.status.value}, " "expected CANDIDATE"
                )

            current_active = self._find_active(versions, candidate.city, candidate.model_name)
            if not force and current_active is not None:
                self._check_regression(candidate, current_active)

            now_iso = datetime.now(tz=timezone.utc).isoformat()

            # Retire current active
            if current_active is not None:
                versions = self._replace_version(
                    versions,
                    dataclasses.replace(
                        current_active,
                        status=ModelStatus.RETIRED,
                        retired_at=now_iso,
                    ),
                )
                logger.info(
                    "Retired version_id=%s  city=%s  model=%s",
                    current_active.version_id,
                    current_active.city,
                    current_active.model_name,
                )

            # Promote candidate
            promoted = dataclasses.replace(
                candidate,
                status=ModelStatus.ACTIVE,
                promoted_at=now_iso,
            )
            versions = self._replace_version(versions, promoted)
            logger.info(
                "Promoted to ACTIVE version_id=%s  city=%s  model=%s",
                promoted.version_id,
                promoted.city,
                promoted.model_name,
            )

            # Purge excess retired versions
            versions = self._purge_retired(versions, promoted.city, promoted.model_name)
            self._save(versions)

        return promoted

    def rollback(self, city: str, model_name: str, steps: int = 1) -> ModelVersion:
        """Roll back to a previously RETIRED version.

        Atomically: the most recent RETIRED version becomes ACTIVE, and the
        currently ACTIVE version becomes RETIRED.

        Args:
            city: City identifier, e.g. ``"drammen"``.
            model_name: Model name, e.g. ``"LightGBM"``.
            steps: Number of retired versions to step back (default 1).

        Returns:
            The newly activated ``ModelVersion``.

        Raises:
            ValueError: No retired versions exist for this (city, model_name),
                or not enough versions to satisfy ``steps``.
        """
        with self._write_lock():
            versions = self._load()
            retired = self._sorted_retired(versions, city, model_name)

            if not retired:
                raise ValueError(
                    f"No retired versions found for city='{city}' model='{model_name}'"
                )
            if steps > len(retired):
                raise ValueError(
                    f"Requested rollback steps={steps} but only "
                    f"{len(retired)} retired version(s) available for "
                    f"city='{city}' model='{model_name}'"
                )

            target = retired[steps - 1]
            current_active = self._find_active(versions, city, model_name)
            now_iso = datetime.now(tz=timezone.utc).isoformat()

            if current_active is not None:
                versions = self._replace_version(
                    versions,
                    dataclasses.replace(
                        current_active,
                        status=ModelStatus.RETIRED,
                        retired_at=now_iso,
                    ),
                )
                logger.info(
                    "Rollback: retired current ACTIVE version_id=%s",
                    current_active.version_id,
                )

            restored = dataclasses.replace(
                target,
                status=ModelStatus.ACTIVE,
                promoted_at=now_iso,
                retired_at=None,
            )
            versions = self._replace_version(versions, restored)
            self._save(versions)
            logger.info(
                "Rollback: restored version_id=%s  city=%s  model=%s  steps=%d",
                restored.version_id,
                city,
                model_name,
                steps,
            )

        return restored

    def get_active(self, city: str, model_name: str) -> ModelVersion | None:
        """Return the currently ACTIVE version for (city, model_name), or None.

        Args:
            city: City identifier.
            model_name: Model name.

        Returns:
            The ACTIVE ``ModelVersion``, or ``None`` if none exists.
        """
        versions = self._load()
        return self._find_active(versions, city, model_name)

    def list_versions(
        self,
        city: str | None = None,
        model_name: str | None = None,
        status: ModelStatus | None = None,
    ) -> list[ModelVersion]:
        """List versions with optional filters, sorted by trained_at descending.

        Args:
            city: Filter by city (exact match).
            model_name: Filter by model name (exact match).
            status: Filter by ``ModelStatus``.

        Returns:
            Sorted list of matching ``ModelVersion`` objects.
        """
        versions = self._load()
        if city is not None:
            versions = [v for v in versions if v.city == city]
        if model_name is not None:
            versions = [v for v in versions if v.model_name == model_name]
        if status is not None:
            versions = [v for v in versions if v.status == status]
        return sorted(versions, key=lambda v: v.trained_at, reverse=True)

    def get_version(self, version_id: str) -> ModelVersion | None:
        """Look up a specific version by ID.

        Args:
            version_id: The version UUID string.

        Returns:
            The matching ``ModelVersion``, or ``None``.
        """
        versions = self._load()
        return self._find_version(versions, version_id)

    def summary(self) -> str:
        """Return a human-readable summary table of all registry entries.

        Columns: city | model | version_id (short) | status | test_MAE | trained_at

        Returns:
            Multi-line string suitable for logging or printing to stdout.
        """
        versions = self.list_versions()
        if not versions:
            return "Model Registry — no versions registered."

        header = (
            f"{'city':<12} {'model':<14} {'version (short)':<22} "
            f"{'status':<12} {'test_MAE':>10} {'trained_at':<25}"
        )
        separator = "-" * len(header)
        rows = [header, separator]

        for v in versions:
            mae_str = f"{v.test_metrics.MAE:.4f}" if v.test_metrics is not None else "N/A"
            vid_short = v.version_id[:20]
            rows.append(
                f"{v.city:<12} {v.model_name:<14} {vid_short:<22} "
                f"{v.status.value:<12} {mae_str:>10} {v.trained_at:<25}"
            )

        return "\n".join(rows)

    # ------------------------------------------------------------------
    # Private helpers — state transitions
    # ------------------------------------------------------------------

    def _check_regression(
        self,
        candidate: ModelVersion,
        active: ModelVersion,
    ) -> None:
        """Raise ``ModelRegressionError`` if candidate MAE regresses beyond threshold.

        Only compares test metrics if both versions have them; falls back to
        val metrics, then train metrics, in that order.

        Args:
            candidate: The version being promoted.
            active: The currently active version.

        Raises:
            ModelRegressionError: If new MAE > threshold × active MAE.
        """
        new_mae = self._best_mae(candidate)
        old_mae = self._best_mae(active)

        if new_mae is None or old_mae is None:
            logger.warning(
                "Skipping regression check — MAE not available for comparison "
                "(candidate=%s, active=%s)",
                new_mae,
                old_mae,
            )
            return

        threshold_mae = self.REGRESSION_THRESHOLD * old_mae
        if new_mae > threshold_mae:
            raise ModelRegressionError(
                f"Regression detected: candidate MAE={new_mae:.4f} > "
                f"{self.REGRESSION_THRESHOLD}× active MAE={old_mae:.4f} "
                f"(threshold={threshold_mae:.4f}). "
                "Use force=True to override."
            )

    @staticmethod
    def _best_mae(version: ModelVersion) -> float | None:
        """Return the best available MAE (test > val > train) for a version."""
        for metrics in (version.test_metrics, version.val_metrics, version.train_metrics):
            if metrics is not None:
                return metrics.MAE
        return None

    def _purge_retired(
        self,
        versions: list[ModelVersion],
        city: str,
        model_name: str,
    ) -> list[ModelVersion]:
        """Enforce ``MAX_RETIRED_VERSIONS`` for (city, model_name).

        Older retired versions beyond the cap are marked as FAILED (registry
        entry stays; artifact on disk is not touched).

        Args:
            versions: Current full list of versions.
            city: Scope the purge to this city.
            model_name: Scope the purge to this model name.

        Returns:
            Updated list of versions.
        """
        retired = self._sorted_retired(versions, city, model_name)
        excess = retired[self.MAX_RETIRED_VERSIONS :]
        for old in excess:
            logger.info(
                "Purging retired version_id=%s (exceeds MAX_RETIRED_VERSIONS=%d)",
                old.version_id,
                self.MAX_RETIRED_VERSIONS,
            )
            versions = self._replace_version(
                versions,
                dataclasses.replace(old, status=ModelStatus.FAILED),
            )
        return versions

    # ------------------------------------------------------------------
    # Private helpers — query
    # ------------------------------------------------------------------

    @staticmethod
    def _find_active(
        versions: list[ModelVersion],
        city: str,
        model_name: str,
    ) -> ModelVersion | None:
        for v in versions:
            if v.city == city and v.model_name == model_name and v.status == ModelStatus.ACTIVE:
                return v
        return None

    @staticmethod
    def _find_version(
        versions: list[ModelVersion],
        version_id: str,
    ) -> ModelVersion | None:
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    @staticmethod
    def _sorted_retired(
        versions: list[ModelVersion],
        city: str,
        model_name: str,
    ) -> list[ModelVersion]:
        """Return RETIRED versions for (city, model_name) sorted newest first."""
        retired = [
            v
            for v in versions
            if v.city == city and v.model_name == model_name and v.status == ModelStatus.RETIRED
        ]
        return sorted(retired, key=lambda v: v.retired_at or v.trained_at, reverse=True)

    @staticmethod
    def _replace_version(
        versions: list[ModelVersion],
        updated: ModelVersion,
    ) -> list[ModelVersion]:
        """Return a new list with the matching version_id replaced."""
        return [updated if v.version_id == updated.version_id else v for v in versions]

    # ------------------------------------------------------------------
    # Private helpers — persistence
    # ------------------------------------------------------------------

    def _load(self) -> list[ModelVersion]:
        """Load and deserialise registry from disk.

        Returns:
            List of all registered ``ModelVersion`` objects, or empty list
            if the registry file does not yet exist.
        """
        if not self._registry_path.exists():
            return []
        try:
            with open(self._registry_path, encoding="utf-8") as fh:
                raw = json.load(fh)
            return [_version_from_dict(d) for d in raw]
        except (json.JSONDecodeError, KeyError) as exc:
            raise RegistryError(
                f"Failed to load registry from {self._registry_path}: {exc}"
            ) from exc

    def _save(self, versions: list[ModelVersion]) -> None:
        """Serialise and atomically write the registry to disk.

        Writes to a ``.tmp`` file first, then uses ``os.replace()`` for an
        atomic rename.  This guarantees the on-disk file is never in a
        partially-written state.

        Args:
            versions: Full list of ``ModelVersion`` objects to persist.
        """
        tmp_path = self._registry_path.with_suffix(".json.tmp")
        payload = [_version_to_dict(v) for v in versions]
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, self._registry_path)

    def _write_lock(self) -> _FileLock:
        """Return a context manager that acquires an exclusive advisory lock."""
        return _FileLock(self._lock_path)


# ---------------------------------------------------------------------------
# Advisory file lock context manager
# ---------------------------------------------------------------------------


class _FileLock:
    """Context manager that acquires an exclusive ``flock`` on a lock file.

    Args:
        path: Path of the lock file (created if absent).
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fh = None

    def __enter__(self) -> _FileLock:
        self._fh = open(self._path, "w", encoding="utf-8")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            self._fh.close()
            raise
        return self

    def __exit__(self, *_: object) -> None:
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
