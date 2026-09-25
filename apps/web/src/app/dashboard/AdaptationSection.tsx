"use client";

import React from "react";
import Link from "next/link";
import { AdaptationDecision } from "@/lib/api";
import {
  Zap,
  Activity,
  AlertTriangle,
  RefreshCw,
  TrendingDown,
  CheckCircle2,
  Utensils,
  Dumbbell,
  Sparkles,
  Info,
  ArrowRight,
  ShieldAlert,
  Moon,
  HeartPulse,
} from "lucide-react";

export interface AdaptationSectionProps {
  adaptation: AdaptationDecision | null;
  loading: boolean;
  error: string | null;
  incompleteProfile: boolean;
  onRetry: () => void;
}

export default function AdaptationSection({
  adaptation,
  loading,
  error,
  incompleteProfile,
  onRetry,
}: AdaptationSectionProps) {
  // ---------------------------------------------------------------------------
  // 1. Loading State
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <div className="glass-card p-6 space-y-6 animate-pulse border border-cyan-500/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/20" />
            <div className="space-y-2">
              <div className="w-48 h-5 rounded bg-gray-800" />
              <div className="w-32 h-3 rounded bg-gray-800/60" />
            </div>
          </div>
          <div className="w-28 h-7 rounded-lg bg-gray-800" />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-2">
              <div className="w-16 h-3 rounded bg-gray-800" />
              <div className="w-12 h-6 rounded bg-gray-800" />
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-28 rounded-xl bg-gray-900/60 border border-gray-800" />
          <div className="h-28 rounded-xl bg-gray-900/60 border border-gray-800" />
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 2. Incomplete Profile State (HTTP 422)
  // ---------------------------------------------------------------------------
  if (incompleteProfile) {
    return (
      <div className="glass-card p-6 border-l-4 border-l-amber-500 border border-amber-500/30 bg-amber-950/20 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 shrink-0 mt-0.5">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <h3 className="font-bold text-base text-amber-200">
                Biometric Profile Incomplete for AI Adaptation
              </h3>
              <p className="text-sm text-gray-300 leading-relaxed">
                Your physiological engine needs complete biometric profile data (weight, height, age, activity level, and targets) to calculate dynamic daily readiness and adjustments.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium transition-colors"
          >
            <span>Complete Profile Setup</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-900/80 hover:bg-gray-800 border border-gray-700 text-gray-300 text-sm font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Re-check</span>
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 3. API Error State (Isolated & Non-blocking)
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="glass-card p-6 border-l-4 border-l-red-500 border border-red-500/30 bg-red-950/20 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 shrink-0 mt-0.5">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <h3 className="font-bold text-base text-red-200">
                Adaptation Engine Unavailable
              </h3>
              <p className="text-sm text-gray-300 leading-relaxed">
                {error}
              </p>
            </div>
          </div>
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-red-950/60 hover:bg-red-900/80 border border-red-500/40 text-red-300 text-xs font-medium transition-colors shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 4. No Adaptation Data Available (Null State Fallback)
  // ---------------------------------------------------------------------------
  if (!adaptation) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // 5. Successful Adaptation State & Baseline Handling
  // ---------------------------------------------------------------------------
  const {
    readiness_factor,
    adherence_score,
    recovery_score,
    stress_score,
    sleep_quality,
    plateau_probability,
    injury_risk,
    plateau_detected,
    high_fatigue_flag,
    diet_adjustment,
    workout_adjustment,
    actionable_recommendations,
    coaching_summary,
    objective_data_available,
  } = adaptation;

  // Readiness factor badge color & text
  const getReadinessBadge = (rf: number) => {
    if (rf >= 1.0) {
      return {
        label: "Optimal Readiness",
        color: "text-emerald-300 bg-emerald-950/60 border-emerald-500/40",
        meterBg: "bg-emerald-500",
      };
    }
    if (rf >= 0.8) {
      return {
        label: "Moderate Readiness",
        color: "text-amber-300 bg-amber-950/60 border-amber-500/40",
        meterBg: "bg-amber-500",
      };
    }
    return {
      label: "Low Readiness / Recovery Focus",
      color: "text-rose-300 bg-rose-950/60 border-rose-500/40",
      meterBg: "bg-rose-500",
    };
  };

  const readinessMeta = getReadinessBadge(readiness_factor);

  return (
    <div className="glass-card p-6 space-y-6 border border-cyan-500/20">
      {/* Header Row: Title & Readiness Factor Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold text-gray-100">
                AI Daily Readiness & Adaptation
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                Live Engine
              </span>
            </div>
            <p className="text-xs text-gray-400">
              Personalized multi-signal physiological adjustment
            </p>
          </div>
        </div>

        {/* Readiness Badge */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] uppercase font-mono tracking-wider text-gray-400 block">
              Readiness Factor
            </span>
            <span className="text-2xl font-black font-mono text-cyan-300">
              {readiness_factor.toFixed(2)}
            </span>
          </div>
          <span
            className={`text-xs font-semibold px-3 py-1.5 rounded-lg border font-mono ${readinessMeta.color}`}
          >
            {readinessMeta.label}
          </span>
        </div>
      </div>

      {/* Baseline / Limited Data Notice */}
      {!objective_data_available && (
        <div className="p-4 rounded-xl bg-cyan-950/30 border border-cyan-800/50 flex items-start gap-3">
          <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <p className="font-semibold text-cyan-200">
              Baseline Mode Active (Unimpaired Stand-in Calibration)
            </p>
            <p className="text-gray-300 leading-relaxed">
              Target energy metrics are running on baseline Mifflin-St Jeor thermodynamics. Numeric scores below are neutral defaults (unimpaired computational stand-ins), not empirical physiological measurements. As you log daily nutrition, workouts, and sleep over time, dynamic readiness will calibrate to your empirical behavioral trends.
            </p>
          </div>
        </div>
      )}

      {/* Operational Flags: High Fatigue & Plateau Alerts */}
      {(high_fatigue_flag || plateau_detected || workout_adjustment.deload_recommended) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {high_fatigue_flag && (
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-center gap-3">
              <Activity className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <div>
                <span className="text-xs font-bold text-rose-200 block">Elevated Fatigue Detected</span>
                <span className="text-[11px] text-rose-300/80">Recovery capacity constrained; prioritize rest and sleep.</span>
              </div>
            </div>
          )}

          {plateau_detected && (
            <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 flex items-center gap-3">
              <TrendingDown className="w-5 h-5 text-amber-400 flex-shrink-0" />
              <div>
                <span className="text-xs font-bold text-amber-200 block">Plateau Indicator Active</span>
                <span className="text-[11px] text-amber-300/80">Rate of progress has stalled; adjusting stimuli.</span>
              </div>
            </div>
          )}

          {workout_adjustment.deload_recommended && (
            <div className="p-3.5 rounded-xl bg-purple-950/40 border border-purple-500/40 flex items-center gap-3">
              <ShieldAlert className="w-5 h-5 text-purple-400 flex-shrink-0" />
              <div>
                <span className="text-xs font-bold text-purple-200 block">Deload Week Recommended</span>
                <span className="text-[11px] text-purple-300/80">Systemic fatigue accumulation warrants reduced loading.</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empirical Scores Grid */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="font-semibold uppercase tracking-wider text-gray-300">
            {objective_data_available ? "Evaluated Physiological Scores" : "Baseline Dimension Indicators"}
          </span>
          {!objective_data_available && (
            <span className="font-mono text-[10px] text-cyan-400">
              * Neutral Defaults
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Adherence */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400 block truncate">Adherence</span>
            <p className="text-xl font-bold font-mono text-cyan-400">
              {adherence_score}
              <span className="text-xs text-gray-500 font-normal"> /100</span>
            </p>
            <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-cyan-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, adherence_score))}%` }}
              />
            </div>
          </div>

          {/* Recovery */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400 block truncate">Recovery</span>
            <p className="text-xl font-bold font-mono text-emerald-400">
              {recovery_score}
              <span className="text-xs text-gray-500 font-normal"> /100</span>
            </p>
            <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-emerald-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, recovery_score))}%` }}
              />
            </div>
          </div>

          {/* Stress */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400 block truncate">Stress</span>
            <p className="text-xl font-bold font-mono text-purple-400">
              {stress_score}
              <span className="text-xs text-gray-500 font-normal"> /100</span>
            </p>
            <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-purple-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, stress_score))}%` }}
              />
            </div>
          </div>

          {/* Sleep Quality */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400 flex items-center gap-1 truncate">
              <Moon className="w-3 h-3 text-blue-400 shrink-0" />
              <span>Sleep</span>
            </span>
            <p className="text-xl font-bold font-mono text-blue-400">
              {sleep_quality}
              <span className="text-xs text-gray-500 font-normal"> /100</span>
            </p>
            <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-blue-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, sleep_quality))}%` }}
              />
            </div>
          </div>

          {/* Plateau Probability */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400 block truncate">Plateau Risk</span>
            <p className="text-xl font-bold font-mono text-amber-400">
              {plateau_probability}
              <span className="text-xs text-gray-500 font-normal"> /100</span>
            </p>
            <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-amber-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, plateau_probability))}%` }}
              />
            </div>
          </div>

          {/* Injury Risk */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs text-gray-400 flex items-center gap-1 truncate">
              <HeartPulse className="w-3 h-3 text-rose-400 shrink-0" />
              <span>Injury Risk</span>
            </span>
            <p className="text-xl font-bold font-mono text-rose-400">
              {injury_risk}
              <span className="text-xs text-gray-500 font-normal"> /100</span>
            </p>
            <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-rose-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, injury_risk))}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Adjustments Row (Diet & Workout) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Diet Adjustment Card */}
        <div className="p-4 rounded-xl bg-gray-900/70 border border-gray-800 space-y-3">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-2.5">
            <div className="flex items-center gap-2">
              <Utensils className="w-4 h-4 text-cyan-400" />
              <h4 className="font-bold text-gray-200 text-sm">Nutrition Adjustments</h4>
            </div>
            <span
              className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                diet_adjustment.calorie_delta === 0
                  ? "text-gray-400 bg-gray-800/50"
                  : diet_adjustment.calorie_delta > 0
                  ? "text-emerald-300 bg-emerald-950/60 border border-emerald-800/40"
                  : "text-amber-300 bg-amber-950/60 border border-amber-800/40"
              }`}
            >
              {diet_adjustment.calorie_delta > 0
                ? `+${diet_adjustment.calorie_delta} kcal`
                : `${diet_adjustment.calorie_delta} kcal`}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800/80">
              <span className="text-[10px] uppercase text-gray-500 block">Protein Δ</span>
              <span className="font-semibold font-mono text-emerald-400">
                {diet_adjustment.protein_delta_g >= 0
                  ? `+${diet_adjustment.protein_delta_g}g`
                  : `${diet_adjustment.protein_delta_g}g`}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800/80">
              <span className="text-[10px] uppercase text-gray-500 block">Carb Δ</span>
              <span className="font-semibold font-mono text-purple-400">
                {diet_adjustment.carb_delta_g >= 0
                  ? `+${diet_adjustment.carb_delta_g}g`
                  : `${diet_adjustment.carb_delta_g}g`}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800/80">
              <span className="text-[10px] uppercase text-gray-500 block">Fat Δ</span>
              <span className="font-semibold font-mono text-amber-400">
                {diet_adjustment.fat_delta_g >= 0
                  ? `+${diet_adjustment.fat_delta_g}g`
                  : `${diet_adjustment.fat_delta_g}g`}
              </span>
            </div>
          </div>
        </div>

        {/* Workout Adjustment Card */}
        <div className="p-4 rounded-xl bg-gray-900/70 border border-gray-800 space-y-3">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-2.5">
            <div className="flex items-center gap-2">
              <Dumbbell className="w-4 h-4 text-emerald-400" />
              <h4 className="font-bold text-gray-200 text-sm">Training Adjustments</h4>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-mono capitalize px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/40 text-emerald-300">
                {workout_adjustment.intensity} intensity
              </span>
              <span className="text-xs font-mono capitalize px-2 py-0.5 rounded bg-purple-950/60 border border-purple-800/40 text-purple-300">
                {workout_adjustment.volume} vol
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800/80">
              <span className="text-[10px] uppercase text-gray-500 block">Extra Rest Days</span>
              <span className="font-semibold font-mono text-cyan-300">
                {workout_adjustment.recovery_days > 0
                  ? `+${workout_adjustment.recovery_days} Day${workout_adjustment.recovery_days > 1 ? "s" : ""}`
                  : "0 (Standard)"}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800/80">
              <span className="text-[10px] uppercase text-gray-500 block">Recommended Cardio</span>
              <span className="font-semibold font-mono text-blue-300">
                {workout_adjustment.cardio_minutes > 0
                  ? `${workout_adjustment.cardio_minutes} mins/day`
                  : "0 mins"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Coaching Summary Quote */}
      {coaching_summary && (
        <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 flex items-start gap-3">
          <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 shrink-0 mt-0.5">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="space-y-1 text-sm">
            <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">
              AI Coach Executive Summary
            </span>
            <p className="text-gray-200 leading-relaxed italic">
              &ldquo;{coaching_summary}&rdquo;
            </p>
          </div>
        </div>
      )}

      {/* Actionable Recommendations Checklist */}
      {actionable_recommendations && actionable_recommendations.length > 0 && (
        <div className="space-y-2.5">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">
            Actionable Adaptation Protocols
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {actionable_recommendations.map((rec, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-gray-900/50 border border-gray-800 flex items-start gap-2.5 text-xs text-gray-300"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
