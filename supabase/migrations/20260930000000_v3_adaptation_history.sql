-- Supabase V3 Schema Migration: Adaptation History & Decision Audit Trail
-- Migration Name: 20260930000000_v3_adaptation_history.sql

-- Ensure UUID extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 11. ADAPTATION DECISION HISTORY TABLE
CREATE TABLE IF NOT EXISTS public.adaptation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    readiness_factor NUMERIC(4,3) NOT NULL,
    high_fatigue_flag BOOLEAN NOT NULL DEFAULT FALSE,
    plateau_detected BOOLEAN NOT NULL DEFAULT FALSE,

    adherence_score INT NOT NULL,
    recovery_score INT NOT NULL,
    stress_score INT NOT NULL,
    sleep_quality INT NOT NULL,
    injury_risk INT NOT NULL,
    plateau_probability INT NOT NULL,

    diet_adjustment JSONB NOT NULL,
    workout_adjustment JSONB NOT NULL,

    actionable_recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    coaching_summary TEXT NOT NULL DEFAULT '',
    objective_data_available BOOLEAN NOT NULL DEFAULT FALSE,

    active_meal_plan_id UUID
        REFERENCES public.user_meal_plans(id)
        ON DELETE SET NULL,

    active_workout_plan_id UUID
        REFERENCES public.user_workout_plans(id)
        ON DELETE SET NULL,

    input_snapshot JSONB NOT NULL
);

-- Index for ordering history newest-first by user
CREATE INDEX IF NOT EXISTS idx_adaptation_history_user_created
    ON public.adaptation_history(user_id, created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.adaptation_history ENABLE ROW LEVEL SECURITY;

-- Allow users to only access their own adaptation history records
CREATE POLICY "Users access own adaptation history"
    ON public.adaptation_history
    FOR ALL
    USING (auth.uid() = user_id);
