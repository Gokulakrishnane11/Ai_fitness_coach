"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  getAuthToken,
  UserProfile,
  generateMealPlan,
  MealPlanResponse,
  generateWorkoutPlan,
  WorkoutPlanResponse,
  fetchAdaptationDecision,
  AdaptationDecision,
  AdaptationApiError,
  fetchActiveMealPlan,
  fetchActiveWorkoutPlan,
} from "@/lib/api";
import Link from "next/link";
import AdaptationSection from "./AdaptationSection";
import { Flame, Dumbbell, Droplets, Target, ShieldCheck, AlertTriangle, Utensils, Sparkles, Camera } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mealPlan, setMealPlan] = useState<MealPlanResponse | null>(null);
  const [mealPlanLoading, setMealPlanLoading] = useState(false);
  const [mealPlanError, setMealPlanError] = useState<string | null>(null);

  const [workoutPlan, setWorkoutPlan] = useState<WorkoutPlanResponse | null>(null);
  const [workoutPlanLoading, setWorkoutPlanLoading] = useState(false);
  const [workoutPlanError, setWorkoutPlanError] = useState<string | null>(null);

  // Independent Adaptation state
  const [adaptation, setAdaptation] = useState<AdaptationDecision | null>(null);
  const [adaptationLoading, setAdaptationLoading] = useState(false);
  const [adaptationError, setAdaptationError] = useState<string | null>(null);
  const [adaptationIncomplete, setAdaptationIncomplete] = useState(false);

  // Isolated Adaptation fetcher
  const fetchAdaptation = useCallback(async () => {
    setAdaptationLoading(true);
    setAdaptationError(null);
    setAdaptationIncomplete(false);
    try {
      const decision = await fetchAdaptationDecision();
      setAdaptation(decision);
    } catch (err: unknown) {
      if (err instanceof AdaptationApiError) {
        if (err.status === 422) {
          setAdaptationIncomplete(true);
          setAdaptationError(null);
        } else {
          setAdaptationError(err.message);
        }
      } else if (err instanceof Error) {
        setAdaptationError(err.message);
      } else {
        setAdaptationError("Failed to load adaptation insights.");
      }
    } finally {
      setAdaptationLoading(false);
    }
  }, []);

  const refreshActivePlans = useCallback(async () => {
    try {
      const [mPlan, wPlan] = await Promise.all([
        fetchActiveMealPlan(),
        fetchActiveWorkoutPlan(),
      ]);
      if (mPlan) setMealPlan(mPlan);
      if (wPlan) setWorkoutPlan(wPlan);
      await fetchAdaptation();
    } catch {
      // non-fatal
    }
  }, [fetchAdaptation]);

  const handleGenerateMealPlan = useCallback(async () => {
    if (!profile?.target_metrics) return;
    setMealPlanLoading(true);
    setMealPlanError(null);
    try {
      const plan = await generateMealPlan({
        target_calories: profile.target_metrics.target_calories,
        target_protein_g: profile.target_metrics.protein_g,
        target_carbs_g: profile.target_metrics.carbs_g,
        target_fat_g: profile.target_metrics.fat_g,
        dietary_preference: profile.dietary_preference,
      });
      setMealPlan(plan);
      await fetchAdaptation();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate meal plan";
      setMealPlanError(msg);
    } finally {
      setMealPlanLoading(false);
    }
  }, [profile, fetchAdaptation]);

  const handleGenerateWorkoutPlan = useCallback(async () => {
    if (!profile) return;
    setWorkoutPlanLoading(true);
    setWorkoutPlanError(null);
    try {
      const wPlan = await generateWorkoutPlan({
        goal_type: profile.goal_type,
        workout_days_per_week: profile.workout_days_per_week,
        experience_level: profile.experience_level,
      });
      setWorkoutPlan(wPlan);
      await fetchAdaptation();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate workout plan";
      setWorkoutPlanError(msg);
    } finally {
      setWorkoutPlanLoading(false);
    }
  }, [profile, fetchAdaptation]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
      return;
    }

    if (user) {
      (async () => {
        try {
          const authToken = await getAuthToken();
          const res = await fetch(`${API_BASE_URL}/profile`, {
            headers: { Authorization: `Bearer ${authToken}` },
          });

          if (res.status === 404) {
            // No profile exists yet — send user to complete onboarding
            router.replace("/onboarding");
            return;
          }

          if (!res.ok) {
            setError(`Failed to load your profile (HTTP ${res.status}). Please try again later.`);
            setLoading(false);
            return;
          }

          const data: UserProfile = await res.json();
          setProfile(data);

          // 1. Fetch adaptation decisions independently (non-blocking)
          fetchAdaptation();

          // 2. Meal plan: fetch active plan first, generate only if none active
          if (data.target_metrics) {
            setMealPlanLoading(true);
            setMealPlanError(null);
            try {
              let plan = await fetchActiveMealPlan();
              if (!plan) {
                plan = await generateMealPlan({
                  target_calories: data.target_metrics.target_calories,
                  target_protein_g: data.target_metrics.protein_g,
                  target_carbs_g: data.target_metrics.carbs_g,
                  target_fat_g: data.target_metrics.fat_g,
                  dietary_preference: data.dietary_preference,
                });
              }
              setMealPlan(plan);
            } catch (planErr: unknown) {
              const msg = planErr instanceof Error ? planErr.message : "Failed to load meal plan";
              setMealPlanError(msg);
            } finally {
              setMealPlanLoading(false);
            }
          }

          // 3. Workout plan: fetch active plan first, generate only if none active
          setWorkoutPlanLoading(true);
          setWorkoutPlanError(null);
          try {
            let wPlan = await fetchActiveWorkoutPlan();
            if (!wPlan) {
              wPlan = await generateWorkoutPlan({
                goal_type: data.goal_type,
                workout_days_per_week: data.workout_days_per_week,
                experience_level: data.experience_level,
              });
            }
            setWorkoutPlan(wPlan);
          } catch (wErr: unknown) {
            const msg = wErr instanceof Error ? wErr.message : "Failed to load workout plan";
            setWorkoutPlanError(msg);
          } finally {
            setWorkoutPlanLoading(false);
          }
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : "An unexpected error occurred.";
          setError(message);
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [authLoading, user, router, fetchAdaptation]);

  if (authLoading || loading) {
    return (
      <div className="space-y-8 py-2 animate-pulse">
        {/* Skeleton Hero Banner */}
        <div className="glass-card p-6 sm:p-8 space-y-4">
          <div className="flex flex-col sm:flex-row justify-between gap-4">
            <div className="space-y-2.5">
              <div className="h-4 w-36 rounded-full bg-gray-800" />
              <div className="h-8 w-64 rounded bg-gray-800" />
              <div className="h-4 w-80 rounded bg-gray-800/70" />
            </div>
            <div className="h-16 w-52 rounded-2xl bg-gray-800/80" />
          </div>
        </div>

        {/* Skeleton Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card p-5 space-y-3">
              <div className="flex justify-between">
                <div className="h-3 w-20 rounded bg-gray-800" />
                <div className="h-7 w-7 rounded-xl bg-gray-800" />
              </div>
              <div className="h-8 w-32 rounded bg-gray-800" />
              <div className="h-3 w-40 rounded bg-gray-800/60" />
            </div>
          ))}
        </div>

        {/* Skeleton Strategy Card */}
        <div className="glass-card p-6 space-y-4">
          <div className="h-5 w-48 rounded bg-gray-800" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="h-20 rounded-xl bg-gray-800/50" />
            <div className="h-20 rounded-xl bg-gray-800/50" />
            <div className="h-20 rounded-xl bg-gray-800/50" />
          </div>
        </div>

        {/* Skeleton Planning Card */}
        <div className="glass-card p-6 space-y-4">
          <div className="h-6 w-56 rounded bg-gray-800" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-44 rounded-xl bg-gray-800/40" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  if (error) {
    return (
      <div className="py-20 flex flex-col items-center justify-center gap-4">
        <div className="glass-card p-8 max-w-md w-full space-y-4 border border-red-500/30">
          <div className="flex items-center gap-3 text-red-400">
            <AlertTriangle className="w-6 h-6 flex-shrink-0" />
            <h2 className="text-lg font-bold">Dashboard Error</h2>
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="w-full py-2.5 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors text-sm shadow-sm"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  const m = profile.target_metrics;
  const weightDelta = profile.target_weight_kg - profile.weight_kg;
  const absRemaining = Math.abs(weightDelta).toFixed(1);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="space-y-8 py-2">
      {/* Hero / Welcome Banner */}
      <div className="glass-card p-6 sm:p-8 relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 border border-emerald-500/30 text-emerald-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                AI Coach Ready
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#0b1020] border border-white/[0.08] text-slate-300">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                Calibrated Profile
              </span>
              <Link
                href="/body-analysis"
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-300 transition"
              >
                <Camera className="w-3.5 h-3.5 text-cyan-400" />
                AI Body Analysis &rarr;
              </Link>
            </div>

            <div>
              <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
                {getGreeting()}, <span className="gradient-text-cyan">{profile.first_name || "Athlete"}</span>
              </h1>
              <p className="text-sm sm:text-base text-slate-400 mt-1 leading-relaxed">
                Here&apos;s your fitness snapshot for today.
              </p>
            </div>
          </div>

          {/* Goal & Weight Target Widget with Progress Bar */}
          <div className="p-4 rounded-2xl bg-[#0b1020] border border-white/[0.08] shadow-sm shrink-0 min-w-[280px] space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-left space-y-0.5">
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">Current</span>
                <span className="text-xl font-bold font-mono text-white">
                  {profile.weight_kg} <span className="text-xs text-slate-400 font-normal">kg</span>
                </span>
              </div>

              <div className="flex flex-col items-center justify-center px-2 text-slate-500">
                <span className="text-xs font-mono font-medium text-cyan-300 bg-cyan-950/70 px-2.5 py-0.5 rounded-full border border-cyan-800/40">
                  {absRemaining} kg remaining
                </span>
                <span className="text-sm leading-none mt-1">↓</span>
              </div>

              <div className="text-right space-y-0.5">
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">Target</span>
                <span className="text-xl font-bold font-mono text-emerald-400">
                  {profile.target_weight_kg} <span className="text-xs text-slate-400 font-normal">kg</span>
                </span>
              </div>
            </div>

            {/* Clean Progress Visualization */}
            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-white/[0.05]">
              <div
                className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(15, 100 - Number(absRemaining) * 5))}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Target Metric Cards (Dominant Primary Values, Clean Secondary Details) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Calories Card */}
        <div className="glass-card p-5 space-y-3 border-l-4 border-l-cyan-500 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Calories</span>
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-mono">
                {m?.target_calories?.toLocaleString()}
              </span>
              <span className="text-xs text-gray-400 font-medium">kcal</span>
            </div>
            <div className="mt-2 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[11px] text-gray-400">
              <span>Maintenance: {m?.tdee} kcal</span>
              <span className="text-gray-500 font-mono">BMR {m?.bmr}</span>
            </div>
          </div>
        </div>

        {/* Protein Card */}
        <div className="glass-card p-5 space-y-3 border-l-4 border-l-emerald-500 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Protein</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Dumbbell className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-mono">
                {m?.protein_g}
              </span>
              <span className="text-xs text-gray-400 font-medium">g</span>
            </div>
            <div className="mt-2 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[11px] text-gray-400">
              <span>~2.2g / kg bodyweight</span>
              <span className="text-emerald-400 font-medium">
                {m?.target_calories ? Math.round(((m.protein_g * 4) / m.target_calories) * 100) : 30}% kcal
              </span>
            </div>
          </div>
        </div>

        {/* Carbs Card */}
        <div className="glass-card p-5 space-y-3 border-l-4 border-l-purple-500 relative overflow-hidden group hover:border-purple-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Carbs</span>
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Target className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-mono">
                {m?.carbs_g}
              </span>
              <span className="text-xs text-gray-400 font-medium">g</span>
            </div>
            <div className="mt-2 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[11px] text-gray-400">
              <span>Fiber: {m?.fiber_g}g min</span>
              <span className="text-purple-400 font-medium">
                {m?.target_calories ? Math.round(((m.carbs_g * 4) / m.target_calories) * 100) : 45}% kcal
              </span>
            </div>
          </div>
        </div>

        {/* Hydration Card */}
        <div className="glass-card p-5 space-y-3 border-l-4 border-l-blue-500 relative overflow-hidden group hover:border-blue-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Hydration</span>
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Droplets className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-mono">
                {m?.water_liters}
              </span>
              <span className="text-xs text-gray-400 font-medium">L</span>
            </div>
            <div className="mt-2 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[11px] text-gray-400">
              <span>Includes workout factor</span>
              <span className="text-blue-400 font-medium">~{m?.water_liters ? Math.round(m.water_liters * 4) : 12} cups</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Daily Readiness & Dynamic Adaptation (Primary Differentiator) */}
      <AdaptationSection
        adaptation={adaptation}
        loading={adaptationLoading}
        error={adaptationError}
        incompleteProfile={adaptationIncomplete}
        onRetry={fetchAdaptation}
        onPlansUpdated={refreshActivePlans}
      />

      {/* TODAY'S PLAN: Two-column layout on desktop */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
                DAILY SYSTEM
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              TODAY&apos;S PLAN
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Calibrated nutritional fuel and progressive overload resistance routine
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-3 py-1 rounded-lg">
              Dynamic Synchronization Active
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Column 1: Daily Meal Plan */}
          <div className="glass-card p-6 space-y-6 border border-slate-800/80">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400">
                  <Utensils className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-100">
                    Today&apos;s Nutrition
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {mealPlan ? `${mealPlan.achieved_calories.toLocaleString()} kcal • ${mealPlan.achieved_protein_g}g protein` : "Target calorie allocation & portioned ingredients"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <Link
                  href="/coaching"
                  className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition"
                >
                  <Utensils className="w-3.5 h-3.5" />
                  <span>Log Meal</span>
                </Link>
                {profile?.target_metrics && (
                  <button
                    onClick={handleGenerateMealPlan}
                    disabled={mealPlanLoading}
                    className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 border border-slate-700/60 transition disabled:opacity-50"
                  >
                    {mealPlanLoading ? (
                      <>
                        <span className="animate-spin inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full" />
                        <span>Generating...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>{mealPlan ? "Regenerate" : "Generate Plan"}</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {mealPlanLoading && !mealPlan && (
              <div className="py-8 text-center text-gray-400 flex items-center justify-center gap-2">
                <span className="animate-spin inline-block w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full" />
                <span>Generating tailored nutritional meal plan...</span>
              </div>
            )}

            {mealPlanError && (
              <div className="text-sm text-red-400 bg-red-950/40 border border-red-500/30 p-4 rounded-xl flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400" />
                <span>{mealPlanError}</span>
              </div>
            )}

            {!mealPlanLoading && !mealPlanError && !mealPlan && (
              <div className="py-10 text-center text-gray-400 space-y-3 border border-dashed border-gray-800 rounded-2xl">
                <Utensils className="w-10 h-10 text-gray-600 mx-auto" />
                <p className="text-sm font-medium">No active meal plan found for your profile.</p>
                {profile?.target_metrics && (
                  <button
                    onClick={handleGenerateMealPlan}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-semibold transition inline-flex items-center gap-2 shadow-sm"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Generate Tailored Meal Plan
                  </button>
                )}
              </div>
            )}

            {mealPlan && (
              <div className="space-y-5">
                {/* Daily Macro Summary Row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
                    <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Calories</span>
                    <p className="text-base font-bold text-cyan-400 font-mono">
                      {mealPlan.achieved_calories ?? mealPlan.target_calories}
                      <span className="text-[10px] font-normal text-gray-500 font-sans block">kcal</span>
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
                    <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Protein</span>
                    <p className="text-base font-bold text-emerald-400 font-mono">
                      {mealPlan.achieved_protein_g ?? mealPlan.target_protein_g}
                      <span className="text-[10px] font-normal text-gray-500 font-sans block">g</span>
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
                    <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Carbs</span>
                    <p className="text-base font-bold text-purple-400 font-mono">
                      {mealPlan.achieved_carbs_g ?? mealPlan.target_carbs_g}
                      <span className="text-[10px] font-normal text-gray-500 font-sans block">g</span>
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-0.5">
                    <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Fat</span>
                    <p className="text-base font-bold text-amber-400 font-mono">
                      {mealPlan.achieved_fat_g ?? mealPlan.target_fat_g}
                      <span className="text-[10px] font-normal text-gray-500 font-sans block">g</span>
                    </p>
                  </div>
                </div>

                {/* Meal Cards (Breakfast, Lunch, Dinner, Snack) */}
                {Array.isArray(mealPlan.meals) && mealPlan.meals.length > 0 ? (
                  <div className="space-y-4">
                    {mealPlan.meals.map((meal, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors shadow-sm"
                      >
                        <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                          <span className="font-bold text-gray-100 text-sm">{meal.meal_name}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-cyan-300 font-mono bg-cyan-950/70 border border-cyan-800/50 px-2 py-0.5 rounded">
                              {meal.actual_calories ?? meal.target_calories} kcal
                            </span>
                            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/50 px-1.5 py-0.5 rounded">
                              {meal.protein_g}g P
                            </span>
                          </div>
                        </div>

                        {/* Food items & portions breakdown */}
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-semibold text-gray-400 block uppercase tracking-wider">
                            Ingredients & Portions
                          </span>
                          {Array.isArray(meal.items) && meal.items.length > 0 ? (
                            <ul className="space-y-1.5">
                              {meal.items.map((item, itemIdx) => (
                                <li
                                  key={itemIdx}
                                  className="text-xs flex items-center justify-between text-gray-300 py-1 border-b border-gray-800/40 last:border-0"
                                >
                                  <span className="truncate pr-2 text-gray-200">{item.food}</span>
                                  <span className="font-mono text-cyan-300 whitespace-nowrap bg-cyan-950/40 px-2 py-0.5 rounded text-[11px] border border-cyan-800/30">
                                    {item.portion_g}g
                                  </span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-gray-500 italic py-1">No items listed</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-sm text-gray-400 rounded-xl bg-gray-900/50 border border-gray-800">
                    No meal breakdown available for this plan.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Column 2: Structured Workout Plan */}
          <div className="glass-card p-6 space-y-6 border border-slate-800/80">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-400">
                  <Dumbbell className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-100">
                    {workoutPlan ? workoutPlan.title : "Workout Plan"}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Periodized training volume & resistance exercises
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <Link
                  href="/coaching"
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition"
                >
                  <Dumbbell className="w-3.5 h-3.5" />
                  <span>Start Workout</span>
                </Link>
                {profile && (
                  <button
                    onClick={handleGenerateWorkoutPlan}
                    disabled={workoutPlanLoading}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 border border-slate-700/60 transition disabled:opacity-50"
                  >
                    {workoutPlanLoading ? (
                      <>
                        <span className="animate-spin inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full" />
                        <span>Generating...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>{workoutPlan ? "Regenerate" : "Generate Plan"}</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {workoutPlanLoading && !workoutPlan && (
              <div className="py-8 text-center text-gray-400 flex items-center justify-center gap-2">
                <span className="animate-spin inline-block w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full" />
                <span>Generating customized workout split routine...</span>
              </div>
            )}

            {workoutPlanError && (
              <div className="text-sm text-red-400 bg-red-950/40 border border-red-500/30 p-4 rounded-xl flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400" />
                <span>{workoutPlanError}</span>
              </div>
            )}

            {!workoutPlanLoading && !workoutPlanError && !workoutPlan && (
              <div className="py-10 text-center text-gray-400 space-y-3 border border-dashed border-gray-800 rounded-2xl">
                <Dumbbell className="w-10 h-10 text-gray-600 mx-auto" />
                <p className="text-sm font-medium">No active workout plan found for your profile.</p>
                {profile && (
                  <button
                    onClick={handleGenerateWorkoutPlan}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition inline-flex items-center gap-2 shadow-sm"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Generate Training Split
                  </button>
                )}
              </div>
            )}

            {workoutPlan && (
              <div className="space-y-5">
                {/* Split Description & Target Strategy */}
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <p className="text-xs text-gray-300 leading-relaxed">
                    {workoutPlan.description || "Personalized workout routine based on your fitness goals."}
                  </p>
                  <div className="flex flex-wrap items-center gap-2.5 text-xs text-gray-400 font-mono">
                    <span className="text-emerald-400 font-semibold">{workoutPlan.days_per_week} Days / Wk</span>
                    <span>•</span>
                    <span className="text-cyan-400 font-semibold">{workoutPlan.split_type}</span>
                    <span>•</span>
                    <span className="text-purple-400 font-semibold capitalize">{workoutPlan.experience_level}</span>
                  </div>
                </div>

                {/* Routine Schedule Cards */}
                {Array.isArray(workoutPlan.routine) && workoutPlan.routine.length > 0 ? (
                  <div className="space-y-4">
                    {workoutPlan.routine.map((dayRoutine, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors shadow-sm"
                      >
                        <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                          <div>
                            <span className="text-[10px] uppercase font-mono tracking-wider text-emerald-400 font-semibold block">
                              {dayRoutine.day}
                            </span>
                            <h4 className="font-bold text-gray-100 text-sm">{dayRoutine.focus}</h4>
                          </div>
                          <span className="text-[11px] font-mono text-gray-400 bg-gray-800/60 px-2 py-0.5 rounded">
                            {Array.isArray(dayRoutine.exercises) ? dayRoutine.exercises.length : 0} Exercises
                          </span>
                        </div>

                        {/* Exercises List */}
                        {Array.isArray(dayRoutine.exercises) && dayRoutine.exercises.length > 0 ? (
                          <ul className="space-y-2">
                            {dayRoutine.exercises.map((ex, exIdx) => (
                              <li
                                key={exIdx}
                                className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5"
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <span className="font-medium text-xs text-gray-200 leading-snug">
                                    {ex.name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 text-xs font-mono flex-wrap">
                                  <span className="text-emerald-300 bg-emerald-950/50 border border-emerald-800/40 px-2 py-0.5 rounded text-[11px]">
                                    {ex.sets} Sets × {ex.reps} Reps
                                  </span>
                                  <span className="text-cyan-300 bg-cyan-950/50 border border-cyan-800/40 px-2 py-0.5 rounded text-[11px]">
                                    {ex.rest_sec}s Rest
                                  </span>
                                </div>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-gray-500 italic py-2">No exercises scheduled for this session.</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-sm text-gray-400 rounded-xl bg-gray-900/50 border border-gray-800">
                    No routine days scheduled in this plan.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Your Current Strategy (User-Centric Strategic Overview) */}
      <div className="glass-card p-6 space-y-4 border border-white/[0.06]">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-wider text-gray-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            Your Current Strategy
          </h3>
          <span className="text-xs text-gray-400 font-medium bg-slate-900/80 px-2.5 py-1 rounded-md border border-white/[0.05]">
            Current Plan
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <span className="text-xs text-gray-400 block font-medium">Dietary Protocol</span>
            <p className="font-bold capitalize text-cyan-300 flex items-center gap-1.5">
              <Utensils className="w-3.5 h-3.5 text-cyan-400" />
              {profile.dietary_preference} Nutrition
            </p>
            <span className="text-[11px] text-gray-400 block">Gram-precision portion allocation</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <span className="text-xs text-gray-400 block font-medium">Training Frequency</span>
            <p className="font-bold text-emerald-300 flex items-center gap-1.5">
              <Dumbbell className="w-3.5 h-3.5 text-emerald-400" />
              {profile.workout_days_per_week} Days / Week ({profile.experience_level})
            </p>
            <span className="text-[11px] text-gray-400 block">Progressive overload framework</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <span className="text-xs text-gray-400 block font-medium">Calibration Method</span>
            <p className="font-bold text-purple-300 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
              Mifflin-St Jeor + Bio Floors
            </p>
            <span className="text-[11px] text-gray-400 block">Clinically validated thermodynamics</span>
          </div>
        </div>
      </div>
    </div>
  );
}

