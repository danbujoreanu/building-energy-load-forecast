"""
monitoring.drift_detector
=========================
Statistical drift detection for the LightGBM load-forecasting pipeline.

Detects two categories of model health problems:

1. **Covariate drift** — input feature distributions have shifted relative to
   the reference (training) dataset.  Measured via Kolmogorov–Smirnov two-sample
   test and Population Stability Index (PSI).

2. **Concept drift / performance regression** — the relationship between features
   and target has changed, or raw model accuracy has degraded.  Measured via
   target distribution shift (KS + mean/std shift %) and rolling MAE ratio.

PSI interpretation (industry standard):
    PSI < 0.10  → negligible drift (OK)
    PSI 0.10–0.20 → moderate drift (WARNING)
    PSI > 0.20  → significant drift (CRITICAL)

KS test:
    p_value < alpha (default 0.05) → statistically significant distribution shift

Rolling MAE ratio:
    rolling_mae / training_mae > threshold (default 1.5) → retrain trigger

Public API
----------
    DriftDetector  — main class; construct with cfg dict
    DriftReport    — dataclass returned by full_report()
    FeatureDriftResult, TargetDriftResult, RollingMAEResult, DriftSeverity
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations & result dataclasses
# ---------------------------------------------------------------------------


class DriftSeverity(str, Enum):
    """Severity levels for any single drift check or an aggregated report."""

    OK = "ok"           # All checks pass; no action needed
    WARNING = "warning" # Drift detected — monitor closely
    CRITICAL = "critical"  # Drift is severe — retrain recommended


@dataclass
class FeatureDriftResult:
    """KS + PSI drift assessment for a single feature column.

    Attributes:
        feature_name: Column name from the input DataFrame.
        ks_statistic: KS test statistic (0–1; higher = more different).
        ks_pvalue: Two-sided p-value from scipy.stats.ks_2samp.
        psi: Population Stability Index (0 = identical distributions).
        is_drifted: True if ks_pvalue < alpha OR psi >= psi_warning_threshold.
        severity: DriftSeverity based on PSI thresholds and KS significance.
    """

    feature_name: str
    ks_statistic: float
    ks_pvalue: float
    psi: float
    is_drifted: bool
    severity: DriftSeverity


@dataclass
class TargetDriftResult:
    """Distribution shift assessment for the target column (y).

    Attributes:
        ks_statistic: KS test statistic for y_reference vs y_check.
        ks_pvalue: Two-sided p-value.
        mean_shift_pct: Percentage shift in mean: 100 * (check_mean - ref_mean) / ref_mean.
        std_shift_pct: Percentage shift in std: 100 * (check_std - ref_std) / ref_std.
        is_drifted: True if ks_pvalue < alpha.
    """

    ks_statistic: float
    ks_pvalue: float
    mean_shift_pct: float
    std_shift_pct: float
    is_drifted: bool


@dataclass
class RollingMAEResult:
    """Rolling MAE window assessment — the primary retrain trigger.

    Attributes:
        window_days: Number of calendar days in the rolling window.
        rolling_mae: Mean absolute error over the check window.
        training_mae: Baseline MAE from the original training/test evaluation.
        ratio: rolling_mae / training_mae.
        threshold: The multiplier threshold (from config; default 1.5).
        is_triggered: True if ratio > threshold — retrain should be scheduled.
        severity: WARNING if ratio > 1.0, CRITICAL if is_triggered.
    """

    window_days: int
    rolling_mae: float
    training_mae: float
    ratio: float
    threshold: float
    is_triggered: bool
    severity: DriftSeverity


@dataclass
class DriftReport:
    """Complete drift report returned by DriftDetector.full_report().

    All fields are serialisable to JSON via to_json().

    Attributes:
        checked_at: ISO 8601 timestamp of when the check was run (UTC).
        city: Dataset city name (e.g., "drammen" or "oslo").
        model_name: Model identifier (e.g., "LightGBM").
        reference_period: (start, end) ISO strings for the training/reference data.
        check_period: (start, end) ISO strings for the recent data being checked.
        n_reference_samples: Number of rows in the reference set.
        n_check_samples: Number of rows in the check set.
        feature_results: Per-feature drift results, sorted by PSI descending.
        target_result: Target distribution drift result (or None if y not provided).
        rolling_mae_result: Rolling MAE trigger result (or None if no predictions).
        overall_severity: Maximum severity across all individual checks.
        summary: Human-readable one-paragraph summary.
        recommended_action: One of "no_action" | "monitor" | "retrain_scheduled" |
            "retrain_now".
    """

    checked_at: str
    city: str
    model_name: str
    reference_period: tuple[str, str]
    check_period: tuple[str, str]
    n_reference_samples: int
    n_check_samples: int
    feature_results: list[FeatureDriftResult]
    target_result: TargetDriftResult | None
    rolling_mae_result: RollingMAEResult | None
    overall_severity: DriftSeverity
    summary: str
    recommended_action: str

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serialisable dict."""

        def _severity(s: DriftSeverity | None) -> str | None:
            return s.value if s is not None else None

        def _feature(r: FeatureDriftResult) -> dict[str, Any]:
            return {
                "feature_name": r.feature_name,
                "ks_statistic": round(r.ks_statistic, 6),
                "ks_pvalue": round(r.ks_pvalue, 6),
                "psi": round(r.psi, 6),
                "is_drifted": r.is_drifted,
                "severity": _severity(r.severity),
            }

        def _target(r: TargetDriftResult | None) -> dict[str, Any] | None:
            if r is None:
                return None
            return {
                "ks_statistic": round(r.ks_statistic, 6),
                "ks_pvalue": round(r.ks_pvalue, 6),
                "mean_shift_pct": round(r.mean_shift_pct, 2),
                "std_shift_pct": round(r.std_shift_pct, 2),
                "is_drifted": r.is_drifted,
            }

        def _rolling(r: RollingMAEResult | None) -> dict[str, Any] | None:
            if r is None:
                return None
            return {
                "window_days": r.window_days,
                "rolling_mae": round(r.rolling_mae, 4),
                "training_mae": round(r.training_mae, 4),
                "ratio": round(r.ratio, 4),
                "threshold": round(r.threshold, 4),
                "is_triggered": r.is_triggered,
                "severity": _severity(r.severity),
            }

        return {
            "checked_at": self.checked_at,
            "city": self.city,
            "model_name": self.model_name,
            "reference_period": list(self.reference_period),
            "check_period": list(self.check_period),
            "n_reference_samples": self.n_reference_samples,
            "n_check_samples": self.n_check_samples,
            "feature_results": [_feature(r) for r in self.feature_results],
            "target_result": _target(self.target_result),
            "rolling_mae_result": _rolling(self.rolling_mae_result),
            "overall_severity": _severity(self.overall_severity),
            "summary": self.summary,
            "recommended_action": self.recommended_action,
        }

    def to_json(self) -> str:
        """Serialise report to a JSON string (pretty-printed, 2-space indent).

        Returns:
            JSON string representation of the full drift report.
        """
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        """Render the report as a Markdown string suitable for Slack / logging.

        Returns:
            Multi-line Markdown string with drift summary tables.
        """
        sev_icon = {
            DriftSeverity.OK: "OK",
            DriftSeverity.WARNING: "WARNING",
            DriftSeverity.CRITICAL: "CRITICAL",
        }

        lines: list[str] = [
            f"## Drift Report — {self.city} / {self.model_name}",
            f"",
            f"**Checked at:** {self.checked_at}",
            f"**Reference:** {self.reference_period[0]} → {self.reference_period[1]}"
            f" ({self.n_reference_samples:,} samples)",
            f"**Check window:** {self.check_period[0]} → {self.check_period[1]}"
            f" ({self.n_check_samples:,} samples)",
            f"**Overall status:** {sev_icon[self.overall_severity]}",
            f"**Recommended action:** `{self.recommended_action}`",
            f"",
            f"### Summary",
            self.summary,
            f"",
        ]

        # Rolling MAE
        if self.rolling_mae_result is not None:
            r = self.rolling_mae_result
            lines += [
                f"### Rolling MAE ({r.window_days}-day window)",
                f"",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Rolling MAE | {r.rolling_mae:.4f} kWh |",
                f"| Training MAE | {r.training_mae:.4f} kWh |",
                f"| Ratio | {r.ratio:.3f}× (threshold: {r.threshold}×) |",
                f"| Triggered | {'YES' if r.is_triggered else 'no'} |",
                f"| Severity | {sev_icon[r.severity]} |",
                f"",
            ]

        # Target drift
        if self.target_result is not None:
            t = self.target_result
            lines += [
                f"### Target (y) Distribution",
                f"",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| KS statistic | {t.ks_statistic:.4f} |",
                f"| KS p-value | {t.ks_pvalue:.4f} |",
                f"| Mean shift | {t.mean_shift_pct:+.1f}% |",
                f"| Std shift | {t.std_shift_pct:+.1f}% |",
                f"| Drifted | {'YES' if t.is_drifted else 'no'} |",
                f"",
            ]

        # Feature drift table — top 10 by PSI
        if self.feature_results:
            top_n = self.feature_results[:10]
            lines += [
                f"### Feature Drift (top {len(top_n)} by PSI)",
                f"",
                f"| Feature | PSI | KS p-value | Drifted | Severity |",
                f"|---------|-----|-----------|---------|----------|",
            ]
            for fr in top_n:
                drifted_str = "YES" if fr.is_drifted else "no"
                lines.append(
                    f"| {fr.feature_name} | {fr.psi:.4f} | {fr.ks_pvalue:.4f}"
                    f" | {drifted_str} | {sev_icon[fr.severity]} |"
                )
            if len(self.feature_results) > 10:
                n_remaining = len(self.feature_results) - 10
                drifted_remaining = sum(
                    1 for r in self.feature_results[10:] if r.is_drifted
                )
                lines.append(
                    f"\n_...{n_remaining} more features"
                    f" ({drifted_remaining} drifted, not shown)_"
                )
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main detector class
# ---------------------------------------------------------------------------


class DriftDetector:
    """Detects covariate drift and concept drift for the load-forecast pipeline.

    Combines three complementary signals:
    1. **Feature KS + PSI**: Are the input distributions still what the model
       was trained on?
    2. **Target KS + mean/std shift**: Has the load distribution changed?
    3. **Rolling MAE ratio**: Is the model's live accuracy degrading?

    PSI interpretation:
        PSI < 0.1  → negligible drift (OK)
        PSI 0.1–0.2 → moderate drift (WARNING)
        PSI > 0.2  → significant drift (CRITICAL)

    KS test: p_value < alpha (default 0.05) → statistically significant drift.

    Example:
        detector = DriftDetector(cfg)
        report = detector.full_report(
            city="drammen",
            model_name="LightGBM",
            X_reference=X_train,
            X_check=X_test_recent,
            y_reference=y_train,
            y_check=y_test_recent,
            training_mae=4.029,
        )
        print(report.to_markdown())
    """

    KS_ALPHA: float = 0.05
    PSI_WARNING_THRESHOLD: float = 0.1
    PSI_CRITICAL_THRESHOLD: float = 0.2
    PSI_N_BINS: int = 10

    def __init__(
        self,
        cfg: dict[str, Any],
        *,
        rolling_window_days: int = 7,
        mae_threshold_multiplier: float = 1.5,
        ks_alpha: float = 0.05,
    ) -> None:
        """Initialise the detector with pipeline configuration.

        Args:
            cfg: Full pipeline config dict (from config/config.yaml).  The
                ``monitoring`` sub-dict is read for thresholds; constructor
                kwargs override config values.
            rolling_window_days: Number of calendar days for the rolling MAE
                window.  Config key: ``monitoring.rolling_window_days``.
                Constructor kwarg takes precedence.
            mae_threshold_multiplier: Retrain trigger if rolling_mae >
                training_mae * multiplier.  Config key:
                ``monitoring.mae_threshold_multiplier``.
            ks_alpha: KS test significance level.  Config key:
                ``monitoring.ks_alpha``.
        """
        mon_cfg: dict[str, Any] = cfg.get("monitoring", {})

        self._rolling_window_days: int = (
            rolling_window_days
            if rolling_window_days != 7
            else int(mon_cfg.get("rolling_window_days", rolling_window_days))
        )
        self._mae_threshold_multiplier: float = (
            mae_threshold_multiplier
            if mae_threshold_multiplier != 1.5
            else float(mon_cfg.get("mae_threshold_multiplier", mae_threshold_multiplier))
        )
        self._ks_alpha: float = (
            ks_alpha
            if ks_alpha != 0.05
            else float(mon_cfg.get("ks_alpha", ks_alpha))
        )
        self._psi_warning: float = float(
            mon_cfg.get("psi_warning", self.PSI_WARNING_THRESHOLD)
        )
        self._psi_critical: float = float(
            mon_cfg.get("psi_critical", self.PSI_CRITICAL_THRESHOLD)
        )

        logger.debug(
            "DriftDetector initialised | window=%dd | mae_mult=%.2f | ks_alpha=%.3f"
            " | psi_warn=%.2f | psi_crit=%.2f",
            self._rolling_window_days,
            self._mae_threshold_multiplier,
            self._ks_alpha,
            self._psi_warning,
            self._psi_critical,
        )

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def check_feature_drift(
        self,
        X_reference: pd.DataFrame,
        X_check: pd.DataFrame,
        *,
        feature_names: list[str] | None = None,
    ) -> list[FeatureDriftResult]:
        """Run KS test + PSI on each feature column.

        Only numeric columns are processed.  Constant / zero-variance columns
        in the reference set are skipped (PSI is undefined for degenerate
        distributions).

        Args:
            X_reference: Feature matrix from the training/reference period.
            X_check: Feature matrix from the recent/check period.
            feature_names: Optional subset of column names to check.  If None,
                all numeric columns present in both DataFrames are checked.

        Returns:
            List of FeatureDriftResult, sorted by PSI descending (worst drift
            first).
        """
        if feature_names is None:
            numeric_cols = X_reference.select_dtypes(include=[np.number]).columns
            feature_names = [
                c for c in numeric_cols if c in X_check.columns
            ]

        results: list[FeatureDriftResult] = []

        for col in feature_names:
            ref_vals = X_reference[col].dropna().to_numpy(dtype=float)
            chk_vals = X_check[col].dropna().to_numpy(dtype=float)

            if len(ref_vals) < 2 or len(chk_vals) < 2:
                logger.debug("Skipping column '%s': too few non-null values.", col)
                continue

            # Skip constant / zero-variance columns (PSI is undefined)
            if np.std(ref_vals) < 1e-10:
                logger.debug("Skipping constant column '%s'.", col)
                continue

            ks_stat, ks_pval = stats.ks_2samp(ref_vals, chk_vals)
            psi = self._compute_psi(ref_vals, chk_vals, n_bins=self.PSI_N_BINS)

            severity = self._psi_severity(psi, ks_pval)
            is_drifted = (ks_pval < self._ks_alpha) or (psi >= self._psi_warning)

            results.append(
                FeatureDriftResult(
                    feature_name=col,
                    ks_statistic=float(ks_stat),
                    ks_pvalue=float(ks_pval),
                    psi=float(psi),
                    is_drifted=is_drifted,
                    severity=severity,
                )
            )

        results.sort(key=lambda r: r.psi, reverse=True)
        n_drifted = sum(1 for r in results if r.is_drifted)
        logger.info(
            "Feature drift check: %d/%d features drifted", n_drifted, len(results)
        )
        return results

    def check_target_drift(
        self,
        y_reference: pd.Series | np.ndarray,
        y_check: pd.Series | np.ndarray,
    ) -> TargetDriftResult:
        """Detect distribution shift in the target variable (y).

        Computes a KS two-sample test and reports mean/std percentage shifts.

        Args:
            y_reference: Target values from the reference (training) period.
            y_check: Target values from the check (recent) period.

        Returns:
            TargetDriftResult with KS statistics and shift percentages.
        """
        ref = np.asarray(y_reference, dtype=float)
        chk = np.asarray(y_check, dtype=float)

        ref = ref[np.isfinite(ref)]
        chk = chk[np.isfinite(chk)]

        ks_stat, ks_pval = stats.ks_2samp(ref, chk)

        ref_mean, ref_std = float(np.mean(ref)), float(np.std(ref))
        chk_mean, chk_std = float(np.mean(chk)), float(np.std(chk))

        # Avoid division by zero if reference is degenerate
        mean_shift_pct = (
            100.0 * (chk_mean - ref_mean) / ref_mean if ref_mean != 0.0 else 0.0
        )
        std_shift_pct = (
            100.0 * (chk_std - ref_std) / ref_std if ref_std != 0.0 else 0.0
        )

        is_drifted = float(ks_pval) < self._ks_alpha

        logger.info(
            "Target drift check: KS=%.4f p=%.4f | mean_shift=%+.1f%% std_shift=%+.1f%%"
            " | drifted=%s",
            ks_stat,
            ks_pval,
            mean_shift_pct,
            std_shift_pct,
            is_drifted,
        )
        return TargetDriftResult(
            ks_statistic=float(ks_stat),
            ks_pvalue=float(ks_pval),
            mean_shift_pct=mean_shift_pct,
            std_shift_pct=std_shift_pct,
            is_drifted=is_drifted,
        )

    def check_rolling_mae(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray,
        training_mae: float,
        *,
        timestamps: pd.DatetimeIndex | None = None,
    ) -> RollingMAEResult:
        """Compute rolling MAE and compare to the training baseline.

        If ``timestamps`` are provided, the rolling window is defined by
        calendar days (last ``window_days`` calendar days in the data).
        If not provided, the last ``window_days * 24`` samples are used as
        a sample-count fallback (assumes hourly data).

        Args:
            y_true: Ground-truth consumption values (kWh).
            y_pred: Model predictions aligned with y_true.
            training_mae: Baseline MAE from the training/validation evaluation.
            timestamps: Optional DatetimeIndex aligned with y_true.  Enables
                true calendar-day windowing.

        Returns:
            RollingMAEResult with ratio and severity.
        """
        y_true_arr = np.asarray(y_true, dtype=float)
        y_pred_arr = np.asarray(y_pred, dtype=float)

        if len(y_true_arr) != len(y_pred_arr):
            raise ValueError(
                f"y_true length ({len(y_true_arr)}) != y_pred length ({len(y_pred_arr)})"
            )

        if len(y_true_arr) == 0:
            raise ValueError("y_true and y_pred must not be empty.")

        if timestamps is not None:
            # True time-window rolling: last rolling_window_days calendar days
            ts_arr = pd.DatetimeIndex(timestamps)
            cutoff = ts_arr.max() - pd.Timedelta(days=self._rolling_window_days)
            mask = ts_arr >= cutoff
            if mask.sum() == 0:
                logger.warning(
                    "No samples in the last %d days; using all %d samples.",
                    self._rolling_window_days,
                    len(y_true_arr),
                )
                mask = np.ones(len(y_true_arr), dtype=bool)
            window_true = y_true_arr[mask]
            window_pred = y_pred_arr[mask]
        else:
            # Fallback: assume hourly, use last window_days * 24 samples
            n_samples = min(self._rolling_window_days * 24, len(y_true_arr))
            window_true = y_true_arr[-n_samples:]
            window_pred = y_pred_arr[-n_samples:]

        rolling_mae = float(np.mean(np.abs(window_true - window_pred)))
        ratio = rolling_mae / training_mae if training_mae > 0.0 else float("inf")
        is_triggered = ratio > self._mae_threshold_multiplier

        if is_triggered:
            severity = DriftSeverity.CRITICAL
        elif ratio > 1.0:
            severity = DriftSeverity.WARNING
        else:
            severity = DriftSeverity.OK

        logger.info(
            "Rolling MAE check: window=%dd | rolling_mae=%.4f | training_mae=%.4f"
            " | ratio=%.3f | threshold=%.2f | triggered=%s",
            self._rolling_window_days,
            rolling_mae,
            training_mae,
            ratio,
            self._mae_threshold_multiplier,
            is_triggered,
        )
        return RollingMAEResult(
            window_days=self._rolling_window_days,
            rolling_mae=rolling_mae,
            training_mae=training_mae,
            ratio=ratio,
            threshold=self._mae_threshold_multiplier,
            is_triggered=is_triggered,
            severity=severity,
        )

    def full_report(
        self,
        city: str,
        model_name: str,
        X_reference: pd.DataFrame,
        X_check: pd.DataFrame,
        y_reference: pd.Series,
        y_check: pd.Series,
        training_mae: float,
        y_pred: np.ndarray | None = None,
        reference_period: tuple[str, str] | None = None,
        check_period: tuple[str, str] | None = None,
    ) -> DriftReport:
        """Run all drift checks and return a complete DriftReport.

        Runs feature drift, target drift, and (if y_pred is provided) rolling
        MAE checks.  Combines results into a single severity rating with an
        actionable recommendation.

        overall_severity = maximum severity across all individual checks.

        Recommended action mapping:
            OK everywhere           → "no_action"
            WARNING on features     → "monitor"
            WARNING on rolling MAE  → "retrain_scheduled"
            Any CRITICAL            → "retrain_now"

        Args:
            city: City identifier, e.g., "drammen" or "oslo".
            model_name: Model identifier, e.g., "LightGBM".
            X_reference: Feature matrix from the training/reference period.
            X_check: Feature matrix from the recent/check period.
            y_reference: Target values from the reference period.
            y_check: Target values from the check period.
            training_mae: Baseline MAE from training/held-out evaluation.
            y_pred: Optional model predictions aligned with y_check.  Required
                for rolling MAE check.
            reference_period: Optional (start_iso, end_iso) strings describing
                the reference period for reporting.
            check_period: Optional (start_iso, end_iso) strings describing the
                check period.

        Returns:
            DriftReport with all results, severity, and recommended action.
        """
        checked_at = datetime.now(tz=timezone.utc).isoformat()

        ref_period = reference_period or ("unknown", "unknown")
        chk_period = check_period or ("unknown", "unknown")

        # 1. Feature drift
        feature_results = self.check_feature_drift(X_reference, X_check)

        # 2. Target drift
        target_result = self.check_target_drift(y_reference, y_check)

        # 3. Rolling MAE (only if predictions available)
        rolling_mae_result: RollingMAEResult | None = None
        if y_pred is not None:
            # Attempt to extract timestamps from y_check index
            ts_index: pd.DatetimeIndex | None = None
            if isinstance(y_check.index, pd.DatetimeIndex):
                ts_index = y_check.index
            elif isinstance(y_check.index, pd.MultiIndex):
                # MultiIndex (building_id, timestamp) — extract timestamp level
                for level_idx in range(y_check.index.nlevels):
                    level = y_check.index.get_level_values(level_idx)
                    if isinstance(level, pd.DatetimeIndex):
                        ts_index = level
                        break
            rolling_mae_result = self.check_rolling_mae(
                y_check,
                y_pred,
                training_mae,
                timestamps=ts_index,
            )

        # 4. Aggregate severity
        severities: list[DriftSeverity] = []
        for fr in feature_results:
            severities.append(fr.severity)
        if target_result.is_drifted:
            severities.append(DriftSeverity.WARNING)
        if rolling_mae_result is not None:
            severities.append(rolling_mae_result.severity)

        overall_severity = _max_severity(severities)

        # 5. Recommended action
        recommended_action = self._recommend_action(
            overall_severity, feature_results, rolling_mae_result
        )

        # 6. Human-readable summary
        summary = self._build_summary(
            city,
            model_name,
            feature_results,
            target_result,
            rolling_mae_result,
            overall_severity,
        )

        report = DriftReport(
            checked_at=checked_at,
            city=city,
            model_name=model_name,
            reference_period=ref_period,
            check_period=chk_period,
            n_reference_samples=len(X_reference),
            n_check_samples=len(X_check),
            feature_results=feature_results,
            target_result=target_result,
            rolling_mae_result=rolling_mae_result,
            overall_severity=overall_severity,
            summary=summary,
            recommended_action=recommended_action,
        )
        logger.info(
            "DriftReport complete | city=%s | model=%s | severity=%s | action=%s",
            city,
            model_name,
            overall_severity.value,
            recommended_action,
        )
        return report

    # ------------------------------------------------------------------
    # Static / private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_psi(
        reference: np.ndarray,
        actual: np.ndarray,
        n_bins: int = 10,
    ) -> float:
        """Compute Population Stability Index (PSI).

        PSI = sum_i { (actual_i% - reference_i%) * ln(actual_i% / reference_i%) }

        Bins are defined by equal-width intervals derived from the *reference*
        distribution.  Both distributions are then measured against these bins.
        Percentages are clipped to [1e-4, 1.0] to avoid log(0) and division by
        zero for empty bins.

        Args:
            reference: 1-D array from the reference (training) distribution.
            actual: 1-D array from the current (check) distribution.
            n_bins: Number of equal-width bins.  Default 10 (PSI convention).

        Returns:
            PSI value (float >= 0).  Higher = more drift.
        """
        reference = np.asarray(reference, dtype=float)
        actual = np.asarray(actual, dtype=float)

        # Build bin edges from the reference distribution range
        ref_min = float(np.min(reference))
        ref_max = float(np.max(reference))

        # Degenerate case: constant reference distribution
        if ref_max == ref_min:
            return 0.0

        # Extend edges slightly beyond the reference range so that actual
        # values outside the reference range are captured in the end bins
        eps = (ref_max - ref_min) * 1e-6
        bin_edges = np.linspace(ref_min - eps, ref_max + eps, n_bins + 1)

        ref_counts, _ = np.histogram(reference, bins=bin_edges)
        act_counts, _ = np.histogram(actual, bins=bin_edges)

        # Convert to proportions
        ref_pct = ref_counts / max(len(reference), 1)
        act_pct = act_counts / max(len(actual), 1)

        # Clip to avoid log(0) — PSI convention uses a small floor
        _CLIP = 1e-4
        ref_pct = np.clip(ref_pct, _CLIP, 1.0)
        act_pct = np.clip(act_pct, _CLIP, 1.0)

        psi = float(np.sum((act_pct - ref_pct) * np.log(act_pct / ref_pct)))
        return max(0.0, psi)  # PSI is non-negative by construction; guard fp noise

    def _psi_severity(self, psi: float, ks_pvalue: float) -> DriftSeverity:
        """Map PSI value (and KS significance) to a DriftSeverity level.

        Args:
            psi: Computed PSI value.
            ks_pvalue: KS test p-value.

        Returns:
            DriftSeverity.CRITICAL / WARNING / OK.
        """
        if psi >= self._psi_critical:
            return DriftSeverity.CRITICAL
        if psi >= self._psi_warning or ks_pvalue < self._ks_alpha:
            return DriftSeverity.WARNING
        return DriftSeverity.OK

    def _recommend_action(
        self,
        overall_severity: DriftSeverity,
        feature_results: list[FeatureDriftResult],
        rolling_mae_result: RollingMAEResult | None,
    ) -> str:
        """Derive the recommended action from severity and check results.

        Args:
            overall_severity: The aggregated severity.
            feature_results: Per-feature results (used to distinguish feature
                vs MAE warnings).
            rolling_mae_result: Rolling MAE result (may be None).

        Returns:
            One of "no_action" | "monitor" | "retrain_scheduled" | "retrain_now".
        """
        if overall_severity == DriftSeverity.CRITICAL:
            return "retrain_now"

        if overall_severity == DriftSeverity.WARNING:
            # Distinguish source: MAE degradation is more urgent than feature drift
            if (
                rolling_mae_result is not None
                and rolling_mae_result.severity == DriftSeverity.WARNING
            ):
                return "retrain_scheduled"
            return "monitor"

        return "no_action"

    def _build_summary(
        self,
        city: str,
        model_name: str,
        feature_results: list[FeatureDriftResult],
        target_result: TargetDriftResult,
        rolling_mae_result: RollingMAEResult | None,
        overall_severity: DriftSeverity,
    ) -> str:
        """Compose a human-readable one-paragraph summary of drift findings.

        Args:
            city: City identifier.
            model_name: Model identifier.
            feature_results: All feature drift results.
            target_result: Target drift result.
            rolling_mae_result: Rolling MAE result (may be None).
            overall_severity: Aggregated severity.

        Returns:
            A single paragraph string.
        """
        n_features = len(feature_results)
        n_drifted = sum(1 for r in feature_results if r.is_drifted)
        n_critical = sum(
            1 for r in feature_results if r.severity == DriftSeverity.CRITICAL
        )

        parts: list[str] = [
            f"Drift check for {model_name} on {city}:"
        ]

        # Features
        if n_features == 0:
            parts.append("No numeric features were available for drift assessment.")
        elif n_drifted == 0:
            parts.append(
                f"All {n_features} feature(s) are within normal distribution bounds."
            )
        else:
            worst = feature_results[0]
            parts.append(
                f"{n_drifted}/{n_features} feature(s) show statistically significant"
                f" drift (KS test or PSI threshold)."
                f" Worst: '{worst.feature_name}' (PSI={worst.psi:.4f})."
            )
            if n_critical > 0:
                parts.append(
                    f"{n_critical} feature(s) exceed the CRITICAL PSI threshold"
                    f" ({self._psi_critical})."
                )

        # Target
        if target_result.is_drifted:
            parts.append(
                f"Target distribution has shifted (KS p={target_result.ks_pvalue:.4f},"
                f" mean {target_result.mean_shift_pct:+.1f}%,"
                f" std {target_result.std_shift_pct:+.1f}%)."
            )
        else:
            parts.append("Target distribution is stable.")

        # Rolling MAE
        if rolling_mae_result is not None:
            r = rolling_mae_result
            if r.is_triggered:
                parts.append(
                    f"Rolling {r.window_days}-day MAE is {r.rolling_mae:.4f} kWh"
                    f" ({r.ratio:.2f}× training MAE {r.training_mae:.4f} kWh),"
                    f" exceeding the {r.threshold}× retrain threshold."
                )
            else:
                parts.append(
                    f"Rolling {r.window_days}-day MAE is {r.rolling_mae:.4f} kWh"
                    f" ({r.ratio:.2f}× training MAE — within threshold)."
                )
        else:
            parts.append(
                "No model predictions provided — rolling MAE check was skipped."
            )

        # Overall verdict
        sev_str = overall_severity.value.upper()
        parts.append(f"Overall status: {sev_str}.")

        return " ".join(parts)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _max_severity(severities: list[DriftSeverity]) -> DriftSeverity:
    """Return the most severe DriftSeverity from a list.

    Args:
        severities: List of DriftSeverity values (may be empty).

    Returns:
        DriftSeverity.OK if the list is empty; otherwise the maximum.
    """
    if not severities:
        return DriftSeverity.OK
    order = {DriftSeverity.OK: 0, DriftSeverity.WARNING: 1, DriftSeverity.CRITICAL: 2}
    return max(severities, key=lambda s: order[s])
