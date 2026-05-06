-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 006 — SEMO Day-Ahead Prices (DAN-164 Stream 4)
-- 2026-05-06
--
-- Stores Irish day-ahead SMP (System Marginal Price) from EirGrid.
-- Source: https://smartgriddashboard.com (free, no token required)
-- Populated by: scheduler job `fetch_semo_prices` at 14:00 daily
--               (day-ahead prices published ~13:00 the previous day)
-- Used by: LPThermalDispatcher (DAN-164 Stream 3) and morning_advisory.py
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS semo_prices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    price_date      DATE NOT NULL,          -- delivery date (the day these prices apply)
    hour            INT NOT NULL            -- 0–23 (local Dublin time)
                    CHECK (hour BETWEEN 0 AND 23),
    price_eur_kwh   NUMERIC(8,6) NOT NULL,  -- EUR/kWh (converted from EUR/MWh ÷ 1000)
    source          TEXT DEFAULT 'eirgrid'  -- 'eirgrid' | 'entsoe' | 'mock'
                    CHECK (source IN ('eirgrid', 'entsoe', 'mock')),
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (price_date, hour)
);

CREATE INDEX IF NOT EXISTS semo_prices_date_idx ON semo_prices (price_date DESC);

COMMENT ON TABLE semo_prices IS
    'Irish SEM day-ahead prices from EirGrid Smart Grid Dashboard. '
    'Populated daily at 14:00 by fetch_semo_prices scheduler job. '
    'Used by LPThermalDispatcher for optimal Eddi schedule.';
