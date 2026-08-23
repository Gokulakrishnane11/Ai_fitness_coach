-- Supabase V1 Schema Migration
-- Migration Name: 20260810000000_v1_schema.sql

-- 0. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS PROFILE TABLE (Extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    first_name TEXT,
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),
    age INT CHECK (age BETWEEN 13 AND 100),
    height_cm NUMERIC(5,2) CHECK (height_cm BETWEEN 100 AND 250),
    weight_kg NUMERIC(5,2) CHECK (weight_kg BETWEEN 30 AND 300),
    target_weight_kg NUMERIC(5,2) CHECK (target_weight_kg BETWEEN 30 AND 300),
    body_fat_pct NUMERIC(4,1) CHECK (body_fat_pct BETWEEN 3 AND 60),
    activity_level TEXT CHECK (activity_level IN ('sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extra_active')),
    goal_type TEXT CHECK (goal_type IN ('fat_loss', 'muscle_gain', 'weight_gain', 'recomposition')),
    dietary_preference TEXT CHECK (dietary_preference IN ('anything', 'vegetarian', 'vegan', 'keto', 'paleo')),
    workout_days_per_week INT CHECK (workout_days_per_week BETWEEN 1 AND 7),
    experience_level TEXT CHECK (experience_level IN ('beginner', 'intermediate', 'advanced')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. BODY MEASUREMENTS TABLE
CREATE TABLE IF NOT EXISTS public.body_measurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    waist_cm NUMERIC(5,2),
    chest_cm NUMERIC(5,2),
    hips_cm NUMERIC(5,2),
    bicep_cm NUMERIC(5,2),
    thigh_cm NUMERIC(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_measurement_date UNIQUE (user_id, log_date)
);

-- 3. FITNESS ASSESSMENTS TABLE
CREATE TABLE IF NOT EXISTS public.fitness_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL,
    pushups_max INT CHECK (pushups_max >= 0),
    plank_sec INT CHECK (plank_sec >= 0),
    estimated_1rm_squat_kg NUMERIC(5,2),
    estimated_1rm_bench_kg NUMERIC(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. FOOD ITEM LIBRARY (Deterministic Database)
CREATE TABLE IF NOT EXISTS public.foods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT CHECK (category IN ('protein', 'carbs', 'fats', 'vegetable', 'fruit', 'dairy', 'combined')),
    is_vegetarian BOOLEAN DEFAULT TRUE,
    is_vegan BOOLEAN DEFAULT FALSE,
    calories_per_100g NUMERIC(6,2) NOT NULL,
    protein_g NUMERIC(5,2) NOT NULL DEFAULT 0,
    carbs_g NUMERIC(5,2) NOT NULL DEFAULT 0,
    fat_g NUMERIC(5,2) NOT NULL DEFAULT 0,
    fiber_g NUMERIC(5,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. EXERCISE LIBRARY (Deterministic Database)
CREATE TABLE IF NOT EXISTS public.exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT CHECK (category IN ('push', 'pull', 'legs', 'core', 'cardio')),
    primary_muscle TEXT NOT NULL,
    equipment_required TEXT CHECK (equipment_required IN ('bodyweight', 'dumbbell', 'barbell', 'machine', 'cable', 'full_gym')),
    difficulty TEXT CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    instructions TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. USER MEAL PLANS
CREATE TABLE IF NOT EXISTS public.user_meal_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    target_calories INT NOT NULL,
    target_protein_g INT NOT NULL,
    target_carbs_g INT NOT NULL,
    target_fat_g INT NOT NULL,
    plan_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. USER WORKOUT PLANS
CREATE TABLE IF NOT EXISTS public.user_workout_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    split_type TEXT NOT NULL,
    days_per_week INT NOT NULL,
    routine_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. DAILY TRACKING LOGS
CREATE TABLE IF NOT EXISTS public.daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    weight_kg NUMERIC(5,2),
    calories_consumed INT,
    protein_consumed_g INT,
    carbs_consumed_g INT,
    fat_consumed_g INT,
    water_liters NUMERIC(3,1),
    workout_completed BOOLEAN DEFAULT FALSE,
    energy_rating INT CHECK (energy_rating BETWEEN 1 AND 10),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_log_date UNIQUE (user_id, log_date)
);

-- 9. SIMULATIONS RECORD
CREATE TABLE IF NOT EXISTS public.simulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    goal_type TEXT NOT NULL,
    start_weight_kg NUMERIC(5,2) NOT NULL,
    daily_caloric_deficit_surplus INT NOT NULL,
    adherence_pct INT CHECK (adherence_pct BETWEEN 50 AND 100),
    duration_weeks INT NOT NULL CHECK (duration_weeks BETWEEN 4 AND 52),
    weekly_projection JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. JOURNAL & AI COACHING FEEDBACK
CREATE TABLE IF NOT EXISTS public.journal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    entry_text TEXT NOT NULL,
    sentiment_tag TEXT,
    ai_feedback JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS) Policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.body_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fitness_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.foods ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_meal_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_workout_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.simulations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users access own profile" ON public.profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "Users access own measurements" ON public.body_measurements FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users access own assessments" ON public.fitness_assessments FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Public read foods" ON public.foods FOR SELECT USING (true);
CREATE POLICY "Public read exercises" ON public.exercises FOR SELECT USING (true);
CREATE POLICY "Users access own meal plans" ON public.user_meal_plans FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users access own workout plans" ON public.user_workout_plans FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users access own daily logs" ON public.daily_logs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users access own simulations" ON public.simulations FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users access own journal entries" ON public.journal_entries FOR ALL USING (auth.uid() = user_id);
