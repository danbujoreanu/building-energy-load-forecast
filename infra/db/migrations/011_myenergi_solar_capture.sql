-- 011_myenergi_solar_capture: add solar-specific capture columns to myenergi_readings
-- Splits eddi_kwh into grid (h1b) and solar-divert (h1d) components.
-- Also persists exp (grid export from solar) which was available in the API but not stored.
--
-- After applying this migration, run:
--   python scripts/myenergi_backfill.py --start-date 2023-01-20 --force
-- to back-populate eddi_divert_kwh and export_kwh for all historical rows.
--
-- solar_capture_kwh (for Grafana) = eddi_divert_kwh + export_kwh
-- (excludes direct house self-consumption — the missing ~10-15% until Harvi is installed)

ALTER TABLE myenergi_readings
    ADD COLUMN IF NOT EXISTS eddi_divert_kwh  NUMERIC(8,4),   -- h1d only: solar → Eddi (kWh)
    ADD COLUMN IF NOT EXISTS export_kwh       NUMERIC(8,4);   -- exp: solar → grid (kWh)

COMMENT ON COLUMN myenergi_readings.eddi_divert_kwh IS
    'Solar-sourced Eddi diversion only (h1d field, Joules/min). Excludes grid boost (h1b). kWh.';
COMMENT ON COLUMN myenergi_readings.export_kwh IS
    'Grid export from solar surplus (exp field, Joules/min). Not persisted before migration 011. kWh.';
