-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 007 — Household Profile (DAN-152)
-- 2026-05-06
--
-- Adds device/heating flags and solar calibration columns to households.
-- All ADD COLUMN IF NOT EXISTS — safe to re-run on any environment.
--
-- Columns added:
--   has_eddi             BOOLEAN  — household has a MyEnergi Eddi installed
--   heating_type         TEXT     — primary heating fuel (gas/oil/heat_pump/electric/unknown)
--   installed_pv_kw      NUMERIC  — rated PV peak power (kWp); NULL = no solar / unknown
--   panel_factor_seasonal JSONB   — per-month panel factor {YYYY-MM: float}
--                                   written by _recompute_panel_factor_seasonal scheduler job
--   panel_factor_obs     NUMERIC  — latest observed panel factor (single float, last good day)
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE households
    ADD COLUMN IF NOT EXISTS has_eddi             BOOLEAN       DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS heating_type         TEXT          DEFAULT 'unknown'
                             CHECK (heating_type IN ('gas', 'oil', 'heat_pump', 'electric', 'unknown')),
    ADD COLUMN IF NOT EXISTS installed_pv_kw      NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS panel_factor_seasonal JSONB,
    ADD COLUMN IF NOT EXISTS panel_factor_obs      NUMERIC(6,4);

COMMENT ON COLUMN households.has_eddi IS
    'True when a MyEnergi Eddi diverter is confirmed for this household '
    '(set automatically when myenergi_readings rows exist for hub_serial).';

COMMENT ON COLUMN households.heating_type IS
    'Primary space-heating fuel. Drives recommendation gating — e.g. heat-pump '
    'households get different DEFER_HEATING logic than gas boiler households.';

COMMENT ON COLUMN households.installed_pv_kw IS
    'Rated PV peak power in kWp. NULL = no solar or not yet set. '
    'Used by SolarBaselineModel to scale clear-sky generation estimate.';

COMMENT ON COLUMN households.panel_factor_seasonal IS
    'JSONB map of {YYYY-MM: panel_factor} computed monthly by _recompute_panel_factor_seasonal. '
    'panel_factor = (export_kwh + eddi_kwh) / ghi_actual. '
    'Written by scheduler at 23:45 after solar_actuals sync.';

COMMENT ON COLUMN households.panel_factor_obs IS
    'Most recent single-day observed panel factor. '
    'Snapshot of the last clean day''s (export_kwh + eddi_kwh) / ghi_actual.';
