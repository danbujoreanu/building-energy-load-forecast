-- Migration 009: expand weather_log to capture full Open-Meteo variable set
-- Matches Gardening project's weather_poller.py field list so both pipelines
-- draw from identical source variables (Energy → TimescaleDB, Gardening → InfluxDB).
--
-- New columns are nullable so existing 'actual' GHI rows are unaffected.
-- Applied: 2026-05-07

ALTER TABLE weather_log
    ADD COLUMN IF NOT EXISTS temp_c       NUMERIC(5,2),   -- 2m air temperature °C
    ADD COLUMN IF NOT EXISTS rh_pct       NUMERIC(5,1),   -- relative humidity %
    ADD COLUMN IF NOT EXISTS precip_mm    NUMERIC(6,2),   -- precipitation mm/h
    ADD COLUMN IF NOT EXISTS wind_kmh     NUMERIC(5,1),   -- wind speed km/h
    ADD COLUMN IF NOT EXISTS cloud_pct    SMALLINT,       -- cloud cover 0-100 %
    ADD COLUMN IF NOT EXISTS weather_code SMALLINT;       -- WMO weather interpretation code

-- ghi_wh_m2 already exists (shortwave_radiation in W/m² per hour = Wh/m²).
-- No rename to avoid breaking existing queries.

COMMENT ON COLUMN weather_log.ghi_wh_m2    IS 'shortwave_radiation W/m² (= Wh/m² per hour interval)';
COMMENT ON COLUMN weather_log.temp_c       IS '2m air temperature °C (Open-Meteo temperature_2m)';
COMMENT ON COLUMN weather_log.rh_pct       IS 'Relative humidity % (Open-Meteo relative_humidity_2m)';
COMMENT ON COLUMN weather_log.precip_mm    IS 'Precipitation mm/h (Open-Meteo precipitation)';
COMMENT ON COLUMN weather_log.wind_kmh     IS 'Wind speed km/h (Open-Meteo windspeed_10m)';
COMMENT ON COLUMN weather_log.cloud_pct    IS 'Cloud cover 0-100 % (Open-Meteo cloud_cover)';
COMMENT ON COLUMN weather_log.weather_code IS 'WMO weather code (Open-Meteo weather_code)';
