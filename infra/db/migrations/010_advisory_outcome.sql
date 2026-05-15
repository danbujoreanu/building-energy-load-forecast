-- Migration 010: advisory outcome feedback column
-- Supports POST /advisory/{date}/outcome endpoint (DAN-P1)
-- Records whether the user acted on the advisory (e.g. skipped the boost).
-- unauthenticated for single-household MVP; add auth before multi-household rollout (see ADR note).

ALTER TABLE advisory_log
    ADD COLUMN IF NOT EXISTS acted_on           boolean,
    ADD COLUMN IF NOT EXISTS outcome_recorded_at timestamp with time zone;
