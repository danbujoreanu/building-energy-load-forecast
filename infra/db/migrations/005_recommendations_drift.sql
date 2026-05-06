-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 005 — Recommendations, Outcomes, Tariff Changes, Drift Log
-- 2026-05-06 — DAN-163 + relational tables missing from initial DB init
--
-- Why: init.sql was updated after DB volume was first initialised on NUC.
--   Tables in this migration exist in the current init.sql but were never
--   created because Docker only runs /docker-entrypoint-initdb.d/ once.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- recommendations — ControlEngine output per household per day
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    prediction_id   UUID REFERENCES predictions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    target_hour     INT NOT NULL CHECK (target_hour BETWEEN 0 AND 23),
    action          TEXT NOT NULL,
    confidence      NUMERIC(4,3) CHECK (confidence BETWEEN 0 AND 1),
    reasoning       TEXT,
    user_message    TEXT,
    p50_kwh         NUMERIC(8,4),
    price_eur_kwh   NUMERIC(6,4),
    solar_wh_m2     NUMERIC(8,2),
    dry_run         BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS recommendations_household_created_idx
    ON recommendations (household_id, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- recommendation_outcomes — did the user act on the advice?
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendation_outcomes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id   UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    household_id        UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    outcome             TEXT NOT NULL
                        CHECK (outcome IN ('accepted', 'ignored', 'partial')),
    recorded_at         TIMESTAMPTZ DEFAULT NOW(),
    savings_eur         NUMERIC(8,4)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- tariff_changes — North Star metric: did Sparc advice cause a tariff switch?
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
-- model_drift_log — DAN-163: rolling MAE + drift monitoring
--
-- Populated by Sunday 02:00 scheduler job (check_drift_sunday).
-- One row per week per household. model_mae_7d is the mean absolute error
-- over the last 7 days of predictions vs actuals (meter_readings).
-- alert_sent = TRUE means a Pushover notification was dispatched.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_drift_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_mae_7d    NUMERIC(8,4),   -- kWh mean absolute error, 7-day rolling
    model_mae_28d   NUMERIC(8,4),   -- kWh mean absolute error, 28-day rolling (baseline)
    drift_ratio     NUMERIC(6,3),   -- model_mae_7d / model_mae_28d (>1.25 = alert)
    alert_sent      BOOLEAN DEFAULT FALSE,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS model_drift_log_household_checked_idx
    ON model_drift_log (household_id, checked_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Customer tier view + Savings gap view (depend on tables above)
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
