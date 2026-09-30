-- Supabase V2 Schema Migration: Daily Log Wellness Telemetry
-- Migration Name: 20260928000000_v2_daily_logs_telemetry.sql
--
-- Adds four optional (nullable) wellness telemetry columns to daily_logs.
-- All four columns use a 0–100 integer scale and are unconstrained by NOT NULL
-- so that all existing rows and existing API clients remain fully compatible.
--
-- Semantic direction (same as the adaptation engine's corresponding fields):
--   recovery_score  : 0 = fully exhausted, 100 = fully recovered      (higher = better)
--   sleep_quality   : 0 = very poor sleep,  100 = excellent sleep      (higher = better)
--   stress_level    : 0 = no stress,         100 = extreme stress      (higher = worse)
--   muscle_soreness : 0 = no soreness,       100 = extreme soreness    (higher = worse)
--
-- Engine mapping:
--   daily_logs.recovery_score  → AdaptationInput.recovery_score  (direct, same direction)
--   daily_logs.sleep_quality   → AdaptationInput.sleep_quality   (direct, same direction)
--   daily_logs.stress_level    → AdaptationInput.stress_score    (direct, same direction)
--   daily_logs.muscle_soreness → AdaptationInput.injury_risk     (direct, same direction)

ALTER TABLE public.daily_logs
    ADD COLUMN IF NOT EXISTS recovery_score  INT CHECK (recovery_score  BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS sleep_quality   INT CHECK (sleep_quality   BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS stress_level    INT CHECK (stress_level    BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS muscle_soreness INT CHECK (muscle_soreness BETWEEN 0 AND 100);
