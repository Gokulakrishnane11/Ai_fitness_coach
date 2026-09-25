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
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20" />
            <div className="space-y-2">
              <div className="w-56 h-5 rounded bg-gray-800" />
              <div className="w-40 h-3 rounded bg-gray-800/60" />
            </div>
          </div>
          <div className="w-36 h-8 rounded-xl bg-gray-800" />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-2 min-h-[110px]">
              <div className="w-16 h-3 rounded bg-gray-800" />
              <div className="w-12 h-6 rounded bg-gray-800" />
              <div className="w-full h-1.5 rounded-full bg-gray-800" />
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-32 rounded-2xl bg-gray-900/60 border border-gray-800" />
          <div className="h-32 rounded-2xl bg-gray-900/60 border border-gray-800" />
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
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 shrink-0 mt-0.5">
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
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium transition-colors shadow-sm"
          >
            <span>Complete Profile Setup</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-700 text-gray-300 text-sm font-medium transition-colors"
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
            <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 shrink-0 mt-0.5">
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
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-red-950/70 hover:bg-red-900/90 border border-red-500/40 text-red-200 text-xs font-medium transition-colors shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 4. Null State Fallback
  // ---------------------------------------------------------------------------
  if (!adaptation) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // 5. Successful Adaptation State
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

  // Readiness factor badge visual tiers
  const getReadinessBadge = (rf: number) => {
    if (rf >= 1.0) {
      return {
        label: "Optimal Readiness",
        color: "text-emerald-300 bg-emerald-950/60 border-emerald-500/40",
        dotBg: "bg-emerald-400",
      };
    }
    if (rf >= 0.8) {
      return {
        label: "Moderate Readiness",
        color: "text-amber-300 bg-amber-950/60 border-amber-500/40",
        dotBg: "bg-amber-400",
      };
    }
    return {
      label: "Low Readiness / Recovery Focus",
      color: "text-rose-300 bg-rose-950/60 border-rose-500/40",
      dotBg: "bg-rose-400",
    };
  };

  const readinessMeta = getReadinessBadge(readiness_factor);

  // Helper for explicit delta formatting
  const formatDelta = (val: number, unit: string) => {
    if (val > 0) return `+${val} ${unit}`;
    if (val < 0) return `${val} ${unit}`;
    return `0 ${unit}`;
  };

  return (
    <div className="glass-card p-6 space-y-6 border border-cyan-500/20">
      {/* ========================================================================= */}
      {/* A. Adaptation Header                                                      */}
      {/* ========================================================================= */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-gray-800/80 pb-5">
        <div className="flex items-start sm:items-center gap-3.5">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-sm shrink-0">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="text-xl font-bold text-gray-100 tracking-tight">
                AI Daily Readiness & Adaptation
              </h3>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-700/60 font-mono flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                Live Engine
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Personalized multi-signal physiological adjustment
            </p>
          </div>
        </div>

        {/* Readiness Factor Display & Status Badge */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="px-3.5 py-1.5 rounded-xl bg-gray-900/90 border border-gray-800 flex items-center gap-2">
            <span className="text-xs text-gray-400 font-medium">Readiness Factor:</span>
            <span className="text-lg font-bold font-mono text-cyan-300">
              {readiness_factor.toFixed(2)}
            </span>
          </div>
          <span
            className={`text-xs font-semibold px-3 py-2 rounded-xl border flex items-center gap-2 font-mono ${readinessMeta.color}`}
          >
            <span className={`w-2 h-2 rounded-full ${readinessMeta.dotBg}`} />
            <span>{readinessMeta.label}</span>
          </span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* B. Baseline Mode Banner                                                   */}
      {/* ========================================================================= */}
      {!objective_data_available && (
        <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-500/30 text-blue-200 flex items-start gap-3.5">
          <div className="p-1 rounded-lg bg-blue-500/10 text-blue-400 shrink-0 mt-0.5">
            <Info className="w-5 h-5" />
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-blue-100 text-sm">
                Baseline Engine Active
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-900/50 text-blue-300 border border-blue-700/50">
                Limited Objective Data
              </span>
            </div>
            <p className="text-gray-300 leading-relaxed">
              Your adaptation recommendations currently utilize baseline computational defaults derived from Mifflin-St Jeor thermodynamics. The numeric scores below are neutral placeholders, not measured physiological data.
            </p>
            <p className="text-blue-300/90 font-medium">
              Consistent logging of your daily nutrition, workouts, body weight, and sleep will unlock personalized physiological adaptation and dynamic readiness scores.
            </p>
          </div>
        </div>
      )}

      {/* Operational Flags: High Fatigue & Plateau Alerts */}
      {(high_fatigue_flag || plateau_detected || workout_adjustment.deload_recommended) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {high_fatigue_flag && (
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-center gap-3">
              <Activity className="w-5 h-5 text-rose-400 shrink-0" />
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

      {/* ========================================================================= */}
      {/* C. Score Cards Grid                                                       */}
      {/* ========================================================================= */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wider text-gray-300 text-[11px]">
            {objective_data_available ? "Evaluated Physiological Scores" : "Baseline Dimension Indicators (Neutral Defaults)"}
          </span>
          {!objective_data_available && (
            <span className="font-mono text-[10px] text-blue-400 bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800/40">
              Computational Defaults
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* 1. Adherence */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-medium truncate">Adherence</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            </div>
            <div>
              <p className="text-xl font-bold font-mono text-cyan-400">
                {adherence_score}
                <span className="text-xs text-gray-500 font-normal"> / 100</span>
              </p>
            </div>
            <div
              className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={adherence_score}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Adherence Score"
            >
              <div
                className="bg-cyan-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, adherence_score))}%` }}
              />
            </div>
          </div>

          {/* 2. Recovery */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-medium truncate">Recovery</span>
              <Activity className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            </div>
            <div>
              <p className="text-xl font-bold font-mono text-emerald-400">
                {recovery_score}
                <span className="text-xs text-gray-500 font-normal"> / 100</span>
              </p>
            </div>
            <div
              className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={recovery_score}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Recovery Score"
            >
              <div
                className="bg-emerald-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, recovery_score))}%` }}
              />
            </div>
          </div>

          {/* 3. Stress */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-medium truncate">Stress</span>
              <HeartPulse className="w-3.5 h-3.5 text-purple-400 shrink-0" />
            </div>
            <div>
              <p className="text-xl font-bold font-mono text-purple-400">
                {stress_score}
                <span className="text-xs text-gray-500 font-normal"> / 100</span>
              </p>
            </div>
            <div
              className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={stress_score}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Stress Score"
            >
              <div
                className="bg-purple-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, stress_score))}%` }}
              />
            </div>
          </div>

          {/* 4. Sleep Quality */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-medium truncate">Sleep Quality</span>
              <Moon className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            </div>
            <div>
              <p className="text-xl font-bold font-mono text-blue-400">
                {sleep_quality}
                <span className="text-xs text-gray-500 font-normal"> / 100</span>
              </p>
            </div>
            <div
              className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={sleep_quality}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Sleep Quality"
            >
              <div
                className="bg-blue-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, sleep_quality))}%` }}
              />
            </div>
          </div>

          {/* 5. Plateau Risk */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-medium truncate">Plateau Risk</span>
              <TrendingDown className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            </div>
            <div>
              <p className="text-xl font-bold font-mono text-amber-400">
                {plateau_probability}
                <span className="text-xs text-gray-500 font-normal"> / 100</span>
              </p>
            </div>
            <div
              className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={plateau_probability}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Plateau Risk"
            >
              <div
                className="bg-amber-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, plateau_probability))}%` }}
              />
            </div>
          </div>

          {/* 6. Injury Risk */}
          <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-medium truncate">Injury Risk</span>
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            </div>
            <div>
              <p className="text-xl font-bold font-mono text-rose-400">
                {injury_risk}
                <span className="text-xs text-gray-500 font-normal"> / 100</span>
              </p>
            </div>
            <div
              className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={injury_risk}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Injury Risk Index"
            >
              <div
                className="bg-rose-400 h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, injury_risk))}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* D & E. Dynamic Adjustments Row (Nutrition & Training)                     */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Nutrition Adjustments Card */}
        <div className="p-5 rounded-2xl bg-gray-900/70 border border-gray-800 flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
                <Utensils className="w-4 h-4" />
              </div>
              <div>
                <h4 className="font-bold text-gray-100 text-sm">Nutrition Adjustments</h4>
                <p className="text-[11px] text-gray-400">Target caloric and macronutrient deltas</p>
              </div>
            </div>
            <span
              className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-lg border ${
                diet_adjustment.calorie_delta === 0
                  ? "text-gray-300 bg-gray-800/70 border-gray-700/60"
                  : diet_adjustment.calorie_delta > 0
                  ? "text-emerald-300 bg-emerald-950/60 border-emerald-800/60"
                  : "text-amber-300 bg-amber-950/60 border-amber-800/60"
              }`}
            >
              Calories: {formatDelta(diet_adjustment.calorie_delta, "kcal")}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2.5 text-xs">
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 text-center space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Protein</span>
              <p className="font-bold font-mono text-emerald-400 text-sm">
                {formatDelta(diet_adjustment.protein_delta_g, "g")}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 text-center space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Carbs</span>
              <p className="font-bold font-mono text-purple-400 text-sm">
                {formatDelta(diet_adjustment.carb_delta_g, "g")}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 text-center space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Fat</span>
              <p className="font-bold font-mono text-amber-400 text-sm">
                {formatDelta(diet_adjustment.fat_delta_g, "g")}
              </p>
            </div>
          </div>
        </div>

        {/* Training Adjustments Card */}
        <div className="p-5 rounded-2xl bg-gray-900/70 border border-gray-800 flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                <Dumbbell className="w-4 h-4" />
              </div>
              <div>
                <h4 className="font-bold text-gray-100 text-sm">Training Adjustments</h4>
                <p className="text-[11px] text-gray-400">Stimulus, volume, and recovery modifications</p>
              </div>
            </div>
            {workout_adjustment.deload_recommended ? (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-rose-950/80 border border-rose-600/60 text-rose-300 flex items-center gap-1 font-mono">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                Deload Required
              </span>
            ) : (
              <span className="text-xs font-medium px-2.5 py-1 rounded-lg bg-gray-800/60 border border-gray-700/60 text-gray-300 font-mono">
                Standard Schedule
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Target Intensity</span>
              <p className="font-semibold text-gray-200 capitalize text-sm">
                Intensity: <span className="font-bold text-emerald-400">{workout_adjustment.intensity}</span>
              </p>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Training Volume</span>
              <p className="font-semibold text-gray-200 capitalize text-sm">
                Volume: <span className="font-bold text-purple-400">{workout_adjustment.volume}</span>
              </p>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Recovery Allocation</span>
              <p className="font-semibold text-gray-200 text-sm">
                Extra Recovery Days: <span className="font-bold text-cyan-400">{workout_adjustment.recovery_days}</span>
              </p>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/60 border border-gray-800/90 space-y-1">
              <span className="text-[11px] font-medium text-gray-400 block">Conditioning Target</span>
              <p className="font-semibold text-gray-200 text-sm">
                Recommended Cardio: <span className="font-bold text-blue-400">{workout_adjustment.cardio_minutes} minutes</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* F. AI Coach Executive Summary & Actionable Recommendations                */}
      {/* ========================================================================= */}
      {(coaching_summary || (actionable_recommendations && actionable_recommendations.length > 0)) && (
        <div className="space-y-4 pt-2 border-t border-gray-800/70">
          {/* Coaching Summary */}
          {coaching_summary && (
            <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-purple-950/30 to-indigo-950/20 border border-purple-800/40 space-y-2">
              <div className="flex items-center gap-2 text-purple-300 font-semibold text-xs tracking-wider uppercase">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span>AI Coach Executive Summary</span>
              </div>
              <p className="text-gray-100 text-sm leading-relaxed font-normal">
                &ldquo;{coaching_summary}&rdquo;
              </p>
            </div>
          )}

          {/* Actionable Recommendations */}
          {actionable_recommendations && actionable_recommendations.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Actionable Adaptation Protocols</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {actionable_recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/80 flex items-start gap-3 text-xs text-gray-200 hover:border-gray-700/80 transition-colors"
                  >
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60 text-[10px] font-bold shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
