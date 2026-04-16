-- ─────────────────────────────────────────────────────────────────────────────
-- Sparc Energy — Database Initialisation
-- Runs once when the PostgreSQL container is first created.
-- ─────────────────────────────────────────────────────────────────────────────

-- Required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;   -- query performance monitoring

-- ─────────────────────────────────────────────────────────────────────────────
-- households — one row per registered property
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS households (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- auth.users(id) will be added when Supabase Auth is wired in.
    -- For local dev, user_id is just a UUID stored here.
    user_id             UUID NOT NULL,
    city                TEXT NOT NULL DEFAULT 'ireland',
    postcode            TEXT,
    tariff_name         TEXT,                           -- e.g. "BGE Free Saturday"
    tariff_start        DATE,
    tariff_end          DATE,
    day_rate_eur        NUMERIC(6,4),
    night_rate_eur      NUMERIC(6,4),
    peak_rate_eur       NUMERIC(6,4),
    has_solar           BOOLEAN DEFAULT FALSE,
    has_ev              BOOLEAN DEFAULT FALSE,
    has_heat_pump       BOOLEAN DEFAULT FALSE,
    hardware_id         TEXT,                           -- Eddi serial / hub serial
    btm_detected        JSONB,                          -- BTM asset inference output (E-25)
    onboarded_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- meter_readings — 30-min interval consumption data (HDF upload or P1 port)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meter_readings (
    id              BIGSERIAL,
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    recorded_at     TIMESTAMPTZ NOT NULL,
    import_kwh      NUMERIC(8,4) NOT NULL,              -- grid import for this interval
    export_kwh      NUMERIC(8,4) DEFAULT 0.0,           -- solar/battery export
    source          TEXT DEFAULT 'csv_upload'            -- 'csv_upload' | 'p1_port' | 'api'
);

-- Convert to TimescaleDB hypertable (automatic partitioning by time)
SELECT create_hypertable('meter_readings', 'recorded_at',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 month'
);

-- Unique constraint: one reading per (household, timestamp)
CREATE UNIQUE INDEX IF NOT EXISTS meter_readings_household_time_idx
    ON meter_readings (household_id, recorded_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- predictions — daily H+24 forecast output (one row per household per day)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    issued_at       TIMESTAMPTZ NOT NULL,               -- when the model ran (approx 16:00)
    forecast_date   DATE NOT NULL,                      -- the day being forecast
    p10_kwh         NUMERIC(8,4)[] NOT NULL,            -- 24-element array
    p50_kwh         NUMERIC(8,4)[] NOT NULL,
    p90_kwh         NUMERIC(8,4)[] NOT NULL,
    model_version   TEXT,                               -- ModelRegistry version_id
    UNIQUE (household_id, forecast_date)
);

-- TimescaleDB hypertable for prediction history (E-27)
SELECT create_hypertable('predictions', 'issued_at',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '3 months'
);

-- ─────────────────────────────────────────────────────────────────────────────
-- recommendations — ControlEngine output per household per day
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    prediction_id   UUID REFERENCES predictions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    target_hour     INT NOT NULL CHECK (target_hour BETWEEN 0 AND 23),
    action          TEXT NOT NULL,                      -- ActionType enum value
    confidence      NUMERIC(4,3) CHECK (confidence BETWEEN 0 AND 1),
    reasoning       TEXT,
    user_message    TEXT,                               -- Rory-voice plain English (E-24)
    p50_kwh         NUMERIC(8,4),
    price_eur_kwh   NUMERIC(6,4),
    solar_wh_m2     NUMERIC(8,2),
    dry_run         BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS recommendations_household_created_idx
    ON recommendations (household_id, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- recommendation_outcomes — did the user act on the advice? (P-16)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendation_outcomes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id   UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    household_id        UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    outcome             TEXT NOT NULL
                        CHECK (outcome IN ('accepted', 'ignored', 'partial')),
    recorded_at         TIMESTAMPTZ DEFAULT NOW(),
    savings_eur         NUMERIC(8,4),                   -- calculated post-hoc from meter data
    UNIQUE (recommendation_id)                          -- one outcome per recommendation
);

-- ─────────────────────────────────────────────────────────────────────────────
-- tariff_changes — investor North Star metric (P-17)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tariff_changes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    changed_at      TIMESTAMPTZ DEFAULT NOW(),
    old_tariff      TEXT,
    new_tariff      TEXT,
    attributed_to   TEXT DEFAULT 'app'
                    CHECK (attributed_to IN ('app', 'manual', 'unknown'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Customer tier view — P-18 behavioural segmentation
-- (materialised on query — update to materialised view at scale)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW customer_tiers AS
WITH stats AS (
    SELECT
        h.id                                                        AS household_id,
        h.user_id,
        COALESCE(
            COUNT(ro.id) FILTER (WHERE ro.outcome = 'accepted')::FLOAT
            / NULLIF(COUNT(ro.id), 0),
            0.0
        )                                                           AS acceptance_rate,
        MAX(ro.recorded_at)                                         AS last_active,
        COUNT(tc.id)                                                AS tariff_changes
    FROM households h
    LEFT JOIN recommendations rec   ON rec.household_id = h.id
    LEFT JOIN recommendation_outcomes ro ON ro.recommendation_id = rec.id
    LEFT JOIN tariff_changes tc     ON tc.household_id = h.id
    GROUP BY h.id, h.user_id
)
SELECT
    household_id,
    user_id,
    ROUND(acceptance_rate::NUMERIC, 3)  AS acceptance_rate,
    last_active,
    tariff_changes,
    CASE
        WHEN acceptance_rate >= 0.70
             AND last_active >= NOW() - INTERVAL '14 days'  THEN 'tier_1_optimiser'
        WHEN tariff_changes > 0                              THEN 'tier_3_switcher'
        WHEN last_active >= NOW() - INTERVAL '30 days'      THEN 'tier_2_tracker'
        ELSE                                                      'tier_4_dormant'
    END                                 AS tier
FROM stats;

-- ─────────────────────────────────────────────────────────────────────────────
-- Savings gap view — "you saved €28, you could have saved €47" (P-17)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW savings_gap AS
SELECT
    ro.household_id,
    DATE_TRUNC('month', ro.recorded_at)                 AS month,
    COALESCE(SUM(ro.savings_eur) FILTER
        (WHERE ro.outcome = 'accepted'), 0)              AS actual_savings_eur,
    COALESCE(SUM(ro.savings_eur), 0)                    AS potential_savings_eur,
    COALESCE(SUM(ro.savings_eur), 0)
    - COALESCE(SUM(ro.savings_eur) FILTER
        (WHERE ro.outcome = 'accepted'), 0)              AS left_on_table_eur
FROM recommendation_outcomes ro
GROUP BY ro.household_id, DATE_TRUNC('month', ro.recorded_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- updated_at trigger for households
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER households_updated_at
    BEFORE UPDATE ON households
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
