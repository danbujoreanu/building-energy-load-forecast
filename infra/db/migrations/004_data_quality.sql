-- 004_data_quality: MyEnergi vs ESB cross-validation (DAN-159)
-- Run: docker compose exec db psql -U sparc -d sparc_energy -f /dev/stdin < infra/db/migrations/004_data_quality.sql

-- ─── households: CT calibration factor ───────────────────────────────────────
-- Rolling 30-day mean of (esb_daily_import / myenergi_grid_import).
-- Expected ~0.85 (consumer-grade CT clamp reads 10-20% lower than billing meter).
-- Alert if drifts >10% from 90d average (CT clamp may have moved/degraded).
ALTER TABLE households ADD COLUMN IF NOT EXISTS ct_calibration_factor FLOAT;

-- ─── data_quality_events ─────────────────────────────────────────────────────
-- One row per (household, check_date) — daily cross-validation result.
-- Written by the 23:55 APScheduler job (_run_data_quality_check).
CREATE TABLE IF NOT EXISTS data_quality_events (
    id                      BIGSERIAL       PRIMARY KEY,
    household_id            UUID            NOT NULL REFERENCES households(id),
    check_date              DATE            NOT NULL,

    -- ESB billing meter (source of truth)
    esb_daily_kwh           NUMERIC(8,3),   -- sum(import_kwh) from meter_readings for check_date

    -- MyEnergi CT clamp
    myenergi_daily_kwh      NUMERIC(8,3),   -- sum(import_kwh) from myenergi_readings for check_date

    -- Cross-validation
    ratio                   NUMERIC(6,4),   -- myenergi_daily_kwh / esb_daily_kwh (expected 0.80–0.95)
    physical_violation      BOOLEAN         NOT NULL DEFAULT FALSE, -- myenergi > esb (impossible — data error)
    ratio_anomaly           BOOLEAN         NOT NULL DEFAULT FALSE, -- ratio outside mean ± 2σ of last 30d
    anomaly_detail          TEXT,           -- human-readable note, e.g. "ratio 1.12 vs mean 0.87 ±0.04"

    -- CT calibration
    ct_calibration_factor   NUMERIC(6,4),   -- 30d rolling mean of esb/myenergi (inverse of ratio)

    recorded_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (household_id, check_date)
);
CREATE INDEX IF NOT EXISTS idx_dqe_household_date
    ON data_quality_events (household_id, check_date DESC);
