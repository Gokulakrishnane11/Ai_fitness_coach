"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  getAuthToken,
  UserProfile,
  generateMealPlan,
  MealPlanResponse,
  generateWorkoutPlan,
  WorkoutPlanResponse,
} from "@/lib/api";
import { Flame, Dumbbell, Droplets, Target, ShieldCheck, AlertTriangle, Utensils } from "lucide-react";

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

          if (data.target_metrics) {
            setMealPlanLoading(true);
            setMealPlanError(null);
            try {
              const plan = await generateMealPlan({
                target_calories: data.target_metrics.target_calories,
                target_protein_g: data.target_metrics.protein_g,
                target_carbs_g: data.target_metrics.carbs_g,
                target_fat_g: data.target_metrics.fat_g,
                dietary_preference: data.dietary_preference,
              });
              setMealPlan(plan);
            } catch (planErr: unknown) {
              const msg = planErr instanceof Error ? planErr.message : "Failed to load meal plan";
              setMealPlanError(msg);
            } finally {
              setMealPlanLoading(false);
            }
          }

          // Workout plan generation
          setWorkoutPlanLoading(true);
          setWorkoutPlanError(null);
          try {
            const wPlan = await generateWorkoutPlan({
              goal_type: data.goal_type,
              workout_days_per_week: data.workout_days_per_week,
              experience_level: data.experience_level,
            });
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
  }, [authLoading, user, router]);

  if (authLoading || loading) {
    return <div className="py-20 text-center text-gray-400">Loading physiological dashboard...</div>;
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
          <p className="text-sm text-gray-300">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="w-full py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  const m = profile.target_metrics;

  return (
    <div className="space-y-8 py-4">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">
            Welcome Back, <span className="gradient-text-cyan">{profile.first_name}</span>
          </h1>
          <p className="text-sm text-gray-400">
            Goal: <span className="text-cyan-400 capitalize font-medium">{profile.goal_type.replace("_", " ")}</span> ({profile.weight_kg}kg → {profile.target_weight_kg}kg)
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-emerald-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Physics Engine Active</span>
        </div>
      </div>

      {/* Target Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="glass-card p-5 space-y-2 border-l-4 border-l-cyan-500">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Target Calories</span>
            <Flame className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-3xl font-bold text-cyan-400">{m?.target_calories} <span className="text-sm text-gray-400 font-normal">kcal/day</span></p>
          <p className="text-xs text-gray-500">TDEE: {m?.tdee} kcal (BMR: {m?.bmr})</p>
        </div>

        <div className="glass-card p-5 space-y-2 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Target Protein</span>
            <Dumbbell className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-3xl font-bold text-emerald-400">{m?.protein_g} <span className="text-sm text-gray-400 font-normal">g/day</span></p>
          <p className="text-xs text-gray-500">~2.2g per kg body weight</p>
        </div>

        <div className="glass-card p-5 space-y-2 border-l-4 border-l-purple-500">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Target Carbs</span>
            <Target className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-3xl font-bold text-purple-400">{m?.carbs_g} <span className="text-sm text-gray-400 font-normal">g/day</span></p>
          <p className="text-xs text-gray-500">Fiber: {m?.fiber_g}g minimum</p>
        </div>

        <div className="glass-card p-5 space-y-2 border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Daily Hydration</span>
            <Droplets className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-3xl font-bold text-blue-400">{m?.water_liters} <span className="text-sm text-gray-400 font-normal">Liters/day</span></p>
          <p className="text-xs text-gray-500">Includes workout hydration factor</p>
        </div>
      </div>

      {/* Overview Details */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-bold text-gray-200">Active Strategy Breakdown</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400">Dietary Preferences</span>
            <p className="font-semibold capitalize text-cyan-300">{profile.dietary_preference}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400">Workout Frequency</span>
            <p className="font-semibold text-emerald-300">{profile.workout_days_per_week} Days / Week ({profile.experience_level})</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400">Calculation Protocol</span>
            <p className="font-semibold text-purple-300">Mifflin-St Jeor + Biological Floors</p>
          </div>
        </div>
      </div>

      {/* Daily Meal Plan Section */}
      <div className="glass-card p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800/80 pb-4">
          <div className="flex items-center gap-2.5">
            <Utensils className="w-5 h-5 text-cyan-400" />
            <h3 className="text-xl font-bold text-gray-100">
              {mealPlan ? mealPlan.title : "Daily Meal Plan"}
            </h3>
          </div>
          {mealPlan && (
            <span className="text-xs font-mono text-cyan-400/90 bg-cyan-950/40 border border-cyan-500/30 px-2.5 py-1 rounded-md w-fit">
              Deterministic Portions Active
            </span>
          )}
        </div>

        {mealPlanLoading && (
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

        {mealPlan && (
          <div className="space-y-6">
            {/* Daily Macro Summary Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
                <span className="text-xs text-gray-400 block">Daily Calories</span>
                <p className="text-lg font-bold text-cyan-400">
                  {mealPlan.achieved_calories}{" "}
                  <span className="text-xs font-normal text-gray-500">/ {mealPlan.target_calories} kcal</span>
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
                <span className="text-xs text-gray-400 block">Achieved Protein</span>
                <p className="text-lg font-bold text-emerald-400">
                  {mealPlan.achieved_protein_g}{" "}
                  <span className="text-xs font-normal text-gray-500">g</span>
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
                <span className="text-xs text-gray-400 block">Achieved Carbs</span>
                <p className="text-lg font-bold text-purple-400">
                  {mealPlan.achieved_carbs_g}{" "}
                  <span className="text-xs font-normal text-gray-500">g</span>
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
                <span className="text-xs text-gray-400 block">Achieved Fat</span>
                <p className="text-lg font-bold text-amber-400">
                  {mealPlan.achieved_fat_g}{" "}
                  <span className="text-xs font-normal text-gray-500">g</span>
                </p>
              </div>
            </div>

            {/* Meal Cards Grid (Breakfast, Lunch, Dinner, Snack) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {mealPlan.meals.map((meal, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-gray-900/70 border border-gray-800 flex flex-col justify-between space-y-4 hover:border-gray-700 transition-colors"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-gray-200 text-base">{meal.meal_name}</h4>
                      <span className="text-xs font-semibold text-cyan-400 font-mono bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
                        {meal.actual_calories} kcal
                      </span>
                    </div>

                    {/* Macros per meal */}
                    <div className="grid grid-cols-3 gap-1.5 text-center text-xs py-1.5 px-2 rounded-lg bg-gray-950/60 border border-gray-800/80">
                      <div>
                        <span className="text-[10px] uppercase text-gray-500 block">P</span>
                        <span className="font-semibold text-emerald-400">{meal.protein_g}g</span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase text-gray-500 block">C</span>
                        <span className="font-semibold text-purple-400">{meal.carbs_g}g</span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase text-gray-500 block">F</span>
                        <span className="font-semibold text-amber-400">{meal.fat_g}g</span>
                      </div>
                    </div>

                    {/* Food items breakdown */}
                    <div className="space-y-1 pt-1">
                      <span className="text-[11px] font-medium text-gray-400 block uppercase tracking-wider">
                        Components & Portions
                      </span>
                      <ul className="space-y-1.5">
                        {meal.items.map((item, itemIdx) => (
                          <li
                            key={itemIdx}
                            className="text-xs flex items-center justify-between text-gray-300 py-1 border-b border-gray-800/50 last:border-0"
                          >
                            <span className="truncate pr-2">{item.food}</span>
                            <span className="font-mono text-cyan-300 whitespace-nowrap">{item.portion_g}g</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Structured Workout Plan Section */}
      <div className="glass-card p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800/80 pb-4">
          <div className="flex items-center gap-2.5">
            <Dumbbell className="w-5 h-5 text-emerald-400" />
            <h3 className="text-xl font-bold text-gray-100">
              {workoutPlan ? workoutPlan.title : "Structured Workout Routine"}
            </h3>
          </div>
          {workoutPlan && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-emerald-400/90 bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 rounded-md w-fit">
                {workoutPlan.split_type} Split
              </span>
              <span className="text-xs font-mono text-purple-400/90 bg-purple-950/40 border border-purple-500/30 px-2.5 py-1 rounded-md w-fit">
                {workoutPlan.experience_level}
              </span>
            </div>
          )}
        </div>

        {workoutPlanLoading && (
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

        {workoutPlan && (
          <div className="space-y-6">
            {/* Split Description & Target Strategy */}
            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-2">
              <p className="text-sm text-gray-300 leading-relaxed">
                {workoutPlan.description}
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-gray-400">
                <span>
                  Frequency: <strong className="text-emerald-400 font-semibold">{workoutPlan.days_per_week} Days / Week</strong>
                </span>
                <span>•</span>
                <span>
                  Split Protocol: <strong className="text-cyan-400 font-semibold">{workoutPlan.split_type}</strong>
                </span>
                <span>•</span>
                <span>
                  Target Level: <strong className="text-purple-400 font-semibold">{workoutPlan.experience_level}</strong>
                </span>
              </div>
            </div>

            {/* Routine Schedule Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {workoutPlan.routine.map((dayRoutine, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 flex flex-col justify-between space-y-4 hover:border-gray-700 transition-colors"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-gray-800/80 pb-2.5">
                      <div>
                        <span className="text-xs uppercase font-mono tracking-wider text-emerald-400 font-semibold block">
                          {dayRoutine.day}
                        </span>
                        <h4 className="font-bold text-gray-200 text-base">{dayRoutine.focus}</h4>
                      </div>
                      <span className="text-xs font-mono text-gray-400 bg-gray-800/60 px-2 py-0.5 rounded">
                        {dayRoutine.exercises.length} Exercises
                      </span>
                    </div>

                    {/* Exercises List */}
                    <ul className="space-y-2.5 pt-1">
                      {dayRoutine.exercises.map((ex, exIdx) => (
                        <li
                          key={exIdx}
                          className="p-2.5 rounded-lg bg-gray-950/60 border border-gray-800/80 space-y-1.5"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="font-medium text-sm text-gray-200 leading-snug">
                              {ex.name}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-xs font-mono flex-wrap">
                            <span className="text-emerald-300 bg-emerald-950/50 border border-emerald-800/40 px-1.5 py-0.5 rounded">
                              {ex.sets} Sets × {ex.reps} Reps
                            </span>
                            <span className="text-cyan-300 bg-cyan-950/50 border border-cyan-800/40 px-1.5 py-0.5 rounded">
                              {ex.rest_sec}s Rest
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

