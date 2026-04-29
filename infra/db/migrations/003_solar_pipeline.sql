-- 003_solar_pipeline: weather forecasts, MyEnergi minute-level readings, and solar actuals
-- Run: docker compose exec db psql -U sparc -d sparc_energy -f /dev/stdin < infra/db/migrations/003_solar_pipeline.sql

-- ─── weather_log ─────────────────────────────────────────────────────────────
-- One row per (location, hour, data_type).
-- data_type = 'forecast' (written at forecast time) or 'actual' (written next day from Open-Meteo historical)
CREATE TABLE IF NOT EXISTS weather_log (
    id              BIGSERIAL   PRIMARY KEY,
    location        TEXT        NOT NULL DEFAULT 'maynooth',
    hour_utc        TIMESTAMPTZ NOT NULL,
    ghi_wh_m2       NUMERIC(8,2),           -- Wh/m² for this hour (shortwave_radiation from Open-Meteo)
    data_type       TEXT        NOT NULL,    -- 'forecast' | 'actual'
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (location, hour_utc, data_type)
);
CREATE INDEX IF NOT EXISTS idx_weather_log_hour ON weather_log (location, hour_utc DESC);

-- ─── myenergi_readings ───────────────────────────────────────────────────────
-- 30-min aggregated import and Eddi diversion from MyEnergi API.
-- Separate from meter_readings (ESB CSV) — ESB remains the official source.
-- import_kwh  = grid import in that 30-min slot (from `imp` centi-Watt samples)
-- eddi_kwh    = Eddi hot-water diversion in that 30-min slot (from `hsk` centi-Watt samples)
CREATE TABLE IF NOT EXISTS myenergi_readings (
    hub_serial      TEXT        NOT NULL,
    interval_start  TIMESTAMPTZ NOT NULL,   -- start of 30-min slot, UTC
    import_kwh      NUMERIC(8,4),
    eddi_kwh        NUMERIC(8,4),
    sample_count    SMALLINT,               -- number of minute samples in this slot (≤30)
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (hub_serial, interval_start)
);
SELECT create_hypertable('myenergi_readings', 'interval_start', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_myenergi_hub_interval ON myenergi_readings (hub_serial, interval_start DESC);

-- ─── solar_actuals ───────────────────────────────────────────────────────────
-- Daily solar summary: what did we actually generate vs what was forecast?
-- export_kwh    = from ESB CSV (or MyEnergi imp negative never available — see notes)
-- eddi_kwh      = Eddi diversion total for the day (from get_status che field)
-- ghi_actual    = daily GHI kWh/m² (sum of weather_log actual hours / 1000)
-- ghi_forecast  = daily GHI kWh/m² that was forecast the day before
-- panel_factor_obs = (export_kwh + eddi_kwh) / ghi_actual (lower bound — excludes house SC)
CREATE TABLE IF NOT EXISTS solar_actuals (
    id                  BIGSERIAL   PRIMARY KEY,
    solar_date          DATE        NOT NULL UNIQUE,
    export_kwh          NUMERIC(8,3),   -- ESB net export for the day
    eddi_kwh            NUMERIC(8,3),   -- Eddi diversion total (from MyEnergi che)
    ghi_actual          NUMERIC(8,3),   -- kWh/m² (observed)
    ghi_forecast        NUMERIC(8,3),   -- kWh/m² (was forecast the day before)
    panel_factor_obs    NUMERIC(6,4),   -- lower bound: (export + eddi) / ghi_actual
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_solar_actuals_date ON solar_actuals (solar_date DESC);
