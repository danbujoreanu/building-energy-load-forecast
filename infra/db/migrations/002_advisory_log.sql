-- advisory_log: one row per household per advisory_date
-- Upserted at 06:30 daily by the morning_advisory scheduler job.
CREATE TABLE IF NOT EXISTS advisory_log (
    id                   BIGSERIAL PRIMARY KEY,
    household_id         UUID        NOT NULL,
    advisory_date        DATE        NOT NULL,
    recommendation       TEXT        NOT NULL,  -- SKIP_BOOST | PARTIAL | KEEP_BOOST
    ghi_forecast         NUMERIC(8,3),           -- kWh/m² total daily GHI
    peak_sun_hours       INTEGER,                -- hours where GHI > 200 W/m²
    estimated_solar_kwh  NUMERIC(8,1),           -- estimated panel output (kWh)
    expected_diversion_kwh NUMERIC(6,2),         -- DAN-144: min(est_solar, TANK_DAILY_KWH) in kWh
    issued_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (household_id, advisory_date)
);

CREATE INDEX IF NOT EXISTS idx_advisory_log_household_date
    ON advisory_log (household_id, advisory_date DESC);
