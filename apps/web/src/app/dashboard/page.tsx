"use client";

import { useEffect, useState } from "react";
import { fetchProfile, UserProfile } from "@/lib/api";
import { Flame, Dumbbell, Droplets, Target, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In local demo mode, fetch saved profile or default setup
    fetchProfile("test_token_user_demo")
      .then((res) => setProfile(res))
      .catch(() => {
        // Mock fallback if profile not saved yet
        setProfile({
          first_name: "Gokul",
          gender: "male",
          age: 22,
          height_cm: 178,
          weight_kg: 78,
          target_weight_kg: 72,
          activity_level: "moderately_active",
          goal_type: "fat_loss",
          dietary_preference: "vegetarian",
          workout_days_per_week: 4,
          experience_level: "intermediate",
          target_metrics: {
            bmr: 1780.0,
            tdee: 2759.0,
            target_calories: 2207,
            protein_g: 171.6,
            carbs_g: 223.5,
            fat_g: 61.3,
            fiber_g: 38.0,
            water_liters: 3.2,
          },
        });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-20 text-center text-gray-400">Loading physiological dashboard...</div>;
  }

  const m = profile?.target_metrics;

  return (
    <div className="space-y-8 py-4">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">
            Welcome Back, <span className="gradient-text-cyan">{profile?.first_name}</span>
          </h1>
          <p className="text-sm text-gray-400">
            Goal: <span className="text-cyan-400 capitalize font-medium">{profile?.goal_type.replace("_", " ")}</span> ({profile?.weight_kg}kg → {profile?.target_weight_kg}kg)
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
            <p className="font-semibold capitalize text-cyan-300">{profile?.dietary_preference}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400">Workout Frequency</span>
            <p className="font-semibold text-emerald-300">{profile?.workout_days_per_week} Days / Week ({profile?.experience_level})</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400">Calculation Protocol</span>
            <p className="font-semibold text-purple-300">Mifflin-St Jeor + Biological Floors</p>
          </div>
        </div>
      </div>
    </div>
  );
}
