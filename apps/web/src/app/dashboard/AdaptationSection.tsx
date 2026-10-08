import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  AdaptationDecision,
  AdaptationHistoryRecord,
  AdaptationReason,
  fetchAdaptationHistory,
  applyAdaptationToPlans,
} from "@/lib/api";
import {
  Zap,
  Activity,
  AlertTriangle,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  CheckCircle2,
  Utensils,
  Dumbbell,
  Sparkles,
  Info,
  ArrowRight,
  ShieldAlert,
  Moon,
  HeartPulse,
  History,
  ChevronDown,
  ChevronUp,
  Check,
  Loader2,
} from "lucide-react";

export interface AdaptationSectionProps {
  adaptation: AdaptationDecision | null;
  loading: boolean;
  error: string | null;
  incompleteProfile: boolean;
  onRetry: () => void;
  onPlansUpdated?: () => void;
}

export default function AdaptationSection({
  adaptation,
  loading,
  error,
  incompleteProfile,
  onRetry,
  onPlansUpdated,
}: AdaptationSectionProps) {
  // Apply adaptation state
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<{
    status: "applied" | "already_applied";
    message: string;
  } | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);

  const handleApplyAdaptation = async (force: boolean = false) => {
    setApplying(true);
    setApplyError(null);
    try {
      const res = await applyAdaptationToPlans(force);
      setApplyResult({
        status: res.status,
        message: res.message,
      });
      if (res.applied) {
        // Refresh audit trail
        await loadHistory(true);
        // Notify parent dashboard to reload active meal & workout plans
        if (onPlansUpdated) {
          onPlansUpdated();
        }
      }
    } catch (err: unknown) {
      setApplyError(err instanceof Error ? err.message : "Failed to apply adaptation to active plans.");
    } finally {
      setApplying(false);
    }
  };

  // Collapsible states for secondary technical sections
  const [signalsOpen, setSignalsOpen] = useState(false);
  const [whyOpen, setWhyOpen] = useState(false);
  const [trendOpen, setTrendOpen] = useState(false);

  // History collapsible & item detail states
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<AdaptationHistoryRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [expandedHistoryIds, setExpandedHistoryIds] = useState<Record<string, boolean>>({});

  const toggleHistoryItem = (id: string) => {
    setExpandedHistoryIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const loadHistory = async (force: boolean = false) => {
    if (!force && history.length > 0) return;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await fetchAdaptationHistory(20);
      setHistory(res.history || []);
    } catch (err: unknown) {
      setHistoryError(err instanceof Error ? err.message : "Failed to load adaptation history.");
    } finally {
      setHistoryLoading(false);
    }
  };

  const toggleHistory = async () => {
    const nextState = !historyOpen;
    setHistoryOpen(nextState);
    if (nextState && history.length === 0) {
      await loadHistory(false);
    }
  };

  useEffect(() => {
    // Automatically load history on mount so the readiness trend sparkline renders immediately
    loadHistory(false);
  }, []);
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

  const isPlanOnTrack =
    diet_adjustment.calorie_delta === 0 &&
    !workout_adjustment.deload_recommended &&
    workout_adjustment.recovery_days === 0;

  // Helper for explicit delta formatting
  const formatDelta = (val: number, unit: string) => {
    if (val > 0) return `+${val} ${unit}`;
    if (val < 0) return `${val} ${unit}`;
    return `0 ${unit}`;
  };

  const getSignalLabel = (signal: string): string => {
    switch (signal) {
      case "recovery_score":
        return "Recovery Capacity";
      case "sleep_quality":
        return "Sleep Quality";
      case "stress_score":
        return "Systemic Stress";
      case "injury_risk":
        return "Muscle Soreness";
      case "adherence":
        return "Target Adherence";
      case "plateau":
        return "Plateau Signal";
      case "baseline":
        return "Telemetry Baseline";
      case "adaptation_outcome":
        return "Adaptation Outcome Feedback";
      default:
        return signal.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
  };

  const getEffectBadgeClass = (effect: "positive" | "neutral" | "negative") => {
    switch (effect) {
      case "positive":
        return "bg-emerald-950/60 border-emerald-500/40 text-emerald-400";
      case "negative":
        return "bg-rose-950/60 border-rose-500/40 text-rose-400";
      case "neutral":
      default:
        return "bg-blue-950/60 border-blue-500/40 text-blue-400";
    }
  };

  return (
    <div className="glass-card p-6 space-y-6 border border-cyan-500/20">
      {/* ========================================================================= */}
      {/* A. Section Header                                                         */}
      {/* ========================================================================= */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-gray-800/80 pb-5">
        <div className="flex items-start sm:items-center gap-3.5">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-sm shrink-0">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="text-xl font-bold text-white tracking-tight">
                AI Coach Recommendation
              </h3>
              <span className="text-[11px] font-medium px-2.5 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-700/60 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                Adaptive AI Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Today&apos;s recommendation · Personalized guidance calibrated to your recovery and habits
            </p>
          </div>
        </div>

        {/* Readiness Factor Display & Status Badge */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="px-3.5 py-1.5 rounded-xl bg-gray-900/90 border border-gray-800 flex items-center gap-2">
            <span className="text-xs text-gray-400 font-medium">Readiness:</span>
            <span className="text-base font-bold font-mono text-cyan-300">
              {objective_data_available ? readiness_factor.toFixed(2) : "1.00 (Baseline)"}
            </span>
          </div>
          <span
            className={`text-xs font-medium px-3 py-1.5 rounded-xl border flex items-center gap-2 ${
              objective_data_available ? readinessMeta.color : "text-cyan-300 bg-cyan-950/60 border-cyan-500/30"
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${objective_data_available ? readinessMeta.dotBg : "bg-cyan-400"}`} />
            <span>{objective_data_available ? readinessMeta.label : "Baseline Readiness"}</span>
          </span>
          {adaptation.feedback_outcome && adaptation.feedback_outcome.trajectory !== "insufficient_data" && (
            <span
              className={`text-xs font-medium px-3 py-1.5 rounded-xl border flex items-center gap-1.5 ${
                adaptation.feedback_outcome.trajectory === "improving"
                  ? "text-emerald-300 bg-emerald-950/60 border-emerald-500/40"
                  : adaptation.feedback_outcome.trajectory === "declining"
                  ? "text-rose-300 bg-rose-950/60 border-rose-500/40"
                  : "text-blue-300 bg-blue-950/60 border-blue-500/40"
              }`}
            >
              <span>
                {adaptation.feedback_outcome.trajectory === "improving"
                  ? "Trajectory: Improving"
                  : adaptation.feedback_outcome.trajectory === "declining"
                  ? "Trajectory: Increased Fatigue"
                  : "Trajectory: Stable"}
              </span>
            </span>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* B. PRIMARY AI RECOMMENDATION CARD                                         */}
      {/* ========================================================================= */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-950/30 via-gray-900/90 to-slate-900/90 border border-cyan-500/30 p-5 sm:p-6 shadow-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] font-mono uppercase tracking-widest text-cyan-400 font-semibold block">
                Coach&apos;s Take
              </span>
              <h4 className="text-base font-bold text-white tracking-tight">
                {isPlanOnTrack ? "Your plan is on track" : "Adjustments recommended"}
              </h4>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {isPlanOnTrack ? (
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                No changes needed today
              </span>
            ) : (
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                Updates available
              </span>
            )}
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-slate-900 text-slate-300 border border-white/10 font-semibold">
              Readiness: {objective_data_available ? `${(readiness_factor * 100).toFixed(0)}%` : "Baseline (1.00)"}
            </span>
          </div>
        </div>

        <p className="text-base text-slate-200 leading-relaxed font-medium italic border-l-2 border-cyan-400/80 pl-3.5 my-2">
          &ldquo;{coaching_summary || (isPlanOnTrack ? "Your recovery is strong today. Maintain your current training intensity and stay close to your protein target." : "Your training and nutrition have been fine-tuned based on your recent activity signals.")}&rdquo;
        </p>

        {/* Telemetry Snapshot Badges (Requirement 4: User-friendly baseline presentation) */}
        <div className="space-y-2">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-1">
            <div className="p-3 rounded-xl bg-gray-950/70 border border-gray-800/80 flex flex-col">
              <span className="text-[10px] uppercase font-mono text-slate-400">Readiness</span>
              <span className="text-sm sm:text-base font-bold font-mono text-cyan-300">
                {objective_data_available ? readiness_factor.toFixed(2) : "1.00"}
              </span>
              <span className="text-[9px] text-slate-500 font-sans mt-0.5">
                {objective_data_available ? "Evaluated" : "Baseline"}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/70 border border-gray-800/80 flex flex-col">
              <span className="text-[10px] uppercase font-mono text-slate-400">Recovery</span>
              <span className="text-sm sm:text-base font-bold font-mono text-emerald-400">
                {objective_data_available ? `${recovery_score}/100` : "Waiting for data"}
              </span>
              <span className="text-[9px] text-slate-500 font-sans mt-0.5">
                {objective_data_available ? "Physiological" : "Needs 2+ logs"}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/70 border border-gray-800/80 flex flex-col">
              <span className="text-[10px] uppercase font-mono text-slate-400">Sleep</span>
              <span className="text-sm sm:text-base font-bold font-mono text-blue-400">
                {objective_data_available ? `${sleep_quality}/100` : "Waiting for data"}
              </span>
              <span className="text-[9px] text-slate-500 font-sans mt-0.5">
                {objective_data_available ? "Rest quality" : "Log sleep"}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/70 border border-gray-800/80 flex flex-col">
              <span className="text-[10px] uppercase font-mono text-slate-400">Stress</span>
              <span className="text-sm sm:text-base font-bold font-mono text-purple-400">
                {objective_data_available ? `${stress_score}/100` : "Waiting for data"}
              </span>
              <span className="text-[9px] text-slate-500 font-sans mt-0.5">
                {objective_data_available ? "Autonomic load" : "Log wellness"}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-gray-950/70 border border-gray-800/80 flex flex-col col-span-2 sm:col-span-1">
              <span className="text-[10px] uppercase font-mono text-slate-400">Adherence</span>
              <span className="text-sm sm:text-base font-bold font-mono text-emerald-300">
                {objective_data_available ? `${adherence_score}%` : "Need more history"}
              </span>
              <span className="text-[9px] text-slate-500 font-sans mt-0.5">
                {objective_data_available ? "Target compliance" : "Initial phase"}
              </span>
            </div>
          </div>

          {!objective_data_available && (
            <p className="text-[11px] text-blue-300/85 font-medium flex items-center gap-1.5 pt-0.5">
              <Info className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span>Personalization is still learning · Complete a few days of consistent logging to unlock personalized readiness.</span>
            </p>
          )}
        </div>

        {/* Operational Flags: High Fatigue & Plateau Alerts (Only if active) */}
        {(high_fatigue_flag || plateau_detected || workout_adjustment.deload_recommended) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
            {high_fatigue_flag && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-center gap-3">
                <Activity className="w-5 h-5 text-rose-400 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-rose-200 block">Elevated Fatigue Detected</span>
                  <span className="text-[11px] text-rose-300/80">Recovery capacity constrained; prioritize rest.</span>
                </div>
              </div>
            )}

            {plateau_detected && (
              <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/40 flex items-center gap-3">
                <TrendingDown className="w-5 h-5 text-amber-400 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-amber-200 block">Plateau Indicator Active</span>
                  <span className="text-[11px] text-amber-300/80">Weight progress has slowed; stimuli calibrated.</span>
                </div>
              </div>
            )}

            {workout_adjustment.deload_recommended && (
              <div className="p-3 rounded-xl bg-purple-950/40 border border-purple-500/40 flex items-center gap-3">
                <ShieldAlert className="w-5 h-5 text-purple-400 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-purple-200 block">Deload Week Recommended</span>
                  <span className="text-[11px] text-purple-300/80">Fatigue accumulation warrants reduced loading.</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recommended Changes Summary & Action */}
        <div className="pt-3 border-t border-gray-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="text-xs space-y-1">
            <span className="font-semibold text-gray-300 block">Recommended Changes:</span>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-gray-400">
              <span>
                Nutrition:{" "}
                <span className="font-mono font-medium text-cyan-300">
                  {diet_adjustment.calorie_delta === 0 ? "Calories: 0 kcal (No change)" : formatDelta(diet_adjustment.calorie_delta, "kcal")}
                  {diet_adjustment.protein_delta_g !== 0 && ` • P: ${formatDelta(diet_adjustment.protein_delta_g, "g")}`}
                </span>
              </span>
              <span>
                Training:{" "}
                <span className="font-mono font-medium text-emerald-300">
                  {workout_adjustment.deload_recommended
                    ? "Deload Protocol (sets capped at 2, RPE 6)"
                    : `Intensity ${workout_adjustment.intensity}, Volume ${workout_adjustment.volume}`}
                </span>
              </span>
              {workout_adjustment.recovery_days > 0 && (
                <span className="text-amber-300 font-mono">+{workout_adjustment.recovery_days} Recovery Day(s)</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => handleApplyAdaptation(false)}
              disabled={applying}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-800 disabled:text-gray-500 text-white text-xs font-semibold transition-all shadow-sm"
            >
              {applying ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-300" />
                  <span>Applying...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-cyan-200" />
                  <span>Apply Adaptation to Plans</span>
                </>
              )}
            </button>
            {applyResult?.status === "already_applied" && (
              <button
                onClick={() => handleApplyAdaptation(true)}
                disabled={applying}
                title="Force regeneration of active plans"
                className="inline-flex items-center gap-1 px-2.5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition-colors border border-gray-700/60"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Re-apply</span>
              </button>
            )}
          </div>
        </div>

        {/* Status Messages */}
        {applyResult && (
          <div
            className={`p-3 rounded-xl border flex items-center gap-2.5 text-xs ${
              applyResult.status === "applied"
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                : "bg-blue-950/40 border-blue-500/40 text-blue-200"
            }`}
          >
            <Check className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              {applyResult.status === "applied"
                ? "✓ Adaptation applied successfully! Your active meal and workout plans have been updated."
                : "✓ Active plans are already up to date with this adaptation decision."}
            </span>
          </div>
        )}

        {applyError && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 flex items-center gap-2.5 text-xs">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{applyError}</span>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* C. COLLAPSIBLE: Your Fitness Signals                                      */}
      {/* ========================================================================= */}
      <div className="pt-2 border-t border-gray-800/70 space-y-3">
        <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 hover:border-gray-700/80 transition-colors">
          <button
            type="button"
            onClick={() => setSignalsOpen(!signalsOpen)}
            className="w-full flex items-center justify-between text-left text-xs font-semibold text-gray-200"
          >
            <div className="flex items-center gap-2.5">
              <Activity className="w-4 h-4 text-cyan-400" />
              <div>
                <span className="block text-gray-200">Your Fitness Signals</span>
                <span className="text-[11px] font-normal text-gray-400">
                  {objective_data_available
                    ? "Evaluated physiological indicators (6 dimensions)"
                    : "Learning baseline defaults (6 dimensions)"}
                </span>
              </div>
            </div>
            {signalsOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
        </div>

        {signalsOpen && (
          <div className="space-y-3 pt-1">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {/* 1. Adherence */}
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300 font-medium truncate">Adherence</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  </div>
                  <span className="text-[10px] text-gray-500 font-normal block">Target % adherence</span>
                </div>
                <div>
                  {objective_data_available ? (
                    <p className="text-xl font-bold font-mono text-cyan-400">
                      {adherence_score}
                      <span className="text-xs text-gray-500 font-normal"> / 100</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-gray-400">Need more history</p>
                  )}
                </div>
                <div
                  className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={objective_data_available ? adherence_score : 0}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Adherence Score"
                >
                  <div
                    className="bg-cyan-400 h-full rounded-full transition-all"
                    style={{ width: `${objective_data_available ? Math.min(100, Math.max(0, adherence_score)) : 0}%` }}
                  />
                </div>
              </div>

              {/* 2. Recovery */}
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300 font-medium truncate">Recovery</span>
                    <Activity className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  </div>
                  <span className="text-[10px] text-emerald-400/90 font-medium block">Higher is better</span>
                </div>
                <div>
                  {objective_data_available ? (
                    <p className="text-xl font-bold font-mono text-emerald-400">
                      {recovery_score}
                      <span className="text-xs text-gray-500 font-normal"> / 100</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-gray-400">Waiting for data</p>
                  )}
                </div>
                <div
                  className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={objective_data_available ? recovery_score : 0}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Recovery Score"
                >
                  <div
                    className="bg-emerald-400 h-full rounded-full transition-all"
                    style={{ width: `${objective_data_available ? Math.min(100, Math.max(0, recovery_score)) : 0}%` }}
                  />
                </div>
              </div>

              {/* 3. Stress */}
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300 font-medium truncate">Stress</span>
                    <HeartPulse className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  </div>
                  <span className="text-[10px] text-rose-400/90 font-medium block">Higher = worse</span>
                </div>
                <div>
                  {objective_data_available ? (
                    <p className="text-xl font-bold font-mono text-purple-400">
                      {stress_score}
                      <span className="text-xs text-gray-500 font-normal"> / 100</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-gray-400">Waiting for data</p>
                  )}
                </div>
                <div
                  className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={objective_data_available ? stress_score : 0}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Stress Score"
                >
                  <div
                    className="bg-purple-400 h-full rounded-full transition-all"
                    style={{ width: `${objective_data_available ? Math.min(100, Math.max(0, stress_score)) : 0}%` }}
                  />
                </div>
              </div>

              {/* 4. Sleep Quality */}
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300 font-medium truncate">Sleep Quality</span>
                    <Moon className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                  </div>
                  <span className="text-[10px] text-blue-400/90 font-medium block">Higher is better</span>
                </div>
                <div>
                  {objective_data_available ? (
                    <p className="text-xl font-bold font-mono text-blue-400">
                      {sleep_quality}
                      <span className="text-xs text-gray-500 font-normal"> / 100</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-gray-400">Waiting for data</p>
                  )}
                </div>
                <div
                  className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={objective_data_available ? sleep_quality : 0}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Sleep Quality"
                >
                  <div
                    className="bg-blue-400 h-full rounded-full transition-all"
                    style={{ width: `${objective_data_available ? Math.min(100, Math.max(0, sleep_quality)) : 0}%` }}
                  />
                </div>
              </div>

              {/* 5. Plateau Risk */}
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300 font-medium truncate">Plateau Risk</span>
                    <TrendingDown className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  </div>
                  <span className="text-[10px] text-amber-400/90 font-medium block">Probability score</span>
                </div>
                <div>
                  {objective_data_available ? (
                    <p className="text-xl font-bold font-mono text-amber-400">
                      {plateau_probability}
                      <span className="text-xs text-gray-500 font-normal"> / 100</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-gray-400">Monitoring</p>
                  )}
                </div>
                <div
                  className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={objective_data_available ? plateau_probability : 0}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Plateau Risk"
                >
                  <div
                    className="bg-amber-400 h-full rounded-full transition-all"
                    style={{ width: `${objective_data_available ? Math.min(100, Math.max(0, plateau_probability)) : 0}%` }}
                  />
                </div>
              </div>

              {/* 6. Soreness & Injury Risk */}
              <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col justify-between space-y-2 min-h-[110px]">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300 font-medium truncate">Soreness & Injury</span>
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                  </div>
                  <span className="text-[10px] text-rose-400/90 font-medium block">Higher = worse</span>
                </div>
                <div>
                  {objective_data_available ? (
                    <p className="text-xl font-bold font-mono text-rose-400">
                      {injury_risk}
                      <span className="text-xs text-gray-500 font-normal"> / 100</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-gray-400">Waiting for data</p>
                  )}
                </div>
                <div
                  className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={objective_data_available ? injury_risk : 0}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Injury Risk Index"
                >
                  <div
                    className="bg-rose-400 h-full rounded-full transition-all"
                    style={{ width: `${objective_data_available ? Math.min(100, Math.max(0, injury_risk)) : 0}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* D. COLLAPSIBLE: Why Your Plan Changed (Rationale & Signals)               */}
      {/* ========================================================================= */}
      <div className="pt-2 border-t border-gray-800/70 space-y-3">
        <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 hover:border-gray-700/80 transition-colors">
          <button
            type="button"
            onClick={() => setWhyOpen(!whyOpen)}
            className="w-full flex items-center justify-between text-left text-xs font-semibold text-gray-200"
          >
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <div>
                <span className="block text-gray-200">Why Your Plan Changed</span>
                <span className="text-[11px] font-normal text-gray-400">
                  {isPlanOnTrack ? "Signals stable · Protocols aligned" : "Active adjustment drivers and recommendations"}
                </span>
              </div>
            </div>
            {whyOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
        </div>

        {whyOpen && (
          <div className="space-y-4 pt-1">
            {/* Driving Signals Grid */}
            {adaptation.reasons && adaptation.reasons.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                {adaptation.reasons.map((reason, rIdx) => (
                  <div
                    key={rIdx}
                    className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1.5 flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-gray-300 text-[11px]">
                        {getSignalLabel(reason.signal)}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {reason.value !== null && reason.value !== undefined && (
                          <span className="font-mono text-gray-400 font-bold text-xs">
                            {typeof reason.value === "number" ? reason.value : String(reason.value)}
                          </span>
                        )}
                        <span
                          className={`text-[9px] uppercase font-mono px-1.5 py-0.5 rounded border ${getEffectBadgeClass(
                            reason.effect
                          )}`}
                        >
                          {reason.effect}
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-400 text-[11px] leading-relaxed">
                      {reason.message}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              /* Fallback Driving Signals Grid */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-300 text-[11px]">Adherence Signal</span>
                    <span className="font-mono text-cyan-400 font-bold text-xs">{adherence_score}%</span>
                  </div>
                  <p className="text-gray-400 text-[11px] leading-relaxed">
                    {adherence_score >= 80
                      ? "Consistent adherence to diet and workouts is well-assimilated by your metabolism."
                      : "Adherence variability noted; stabilizing habit baseline before escalating training volume."}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-300 text-[11px]">Wellness Telemetry</span>
                    <span className={`font-mono font-bold text-xs ${high_fatigue_flag ? "text-rose-400" : "text-emerald-400"}`}>
                      {high_fatigue_flag ? "High Fatigue" : "Normal"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-[11px] leading-relaxed">
                    {high_fatigue_flag
                      ? "Recovery markers or high muscle soreness detected; training volume reduced to protect joints."
                      : "Rest, recovery, and sleep scores support current prescribed intensity and stimuli."}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-300 text-[11px]">Progress Trend</span>
                    <span className={`font-mono font-bold text-xs ${plateau_detected ? "text-amber-400" : "text-cyan-400"}`}>
                      {plateau_detected ? "Plateau" : "Steady"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-[11px] leading-relaxed">
                    {plateau_detected
                      ? "Weight response has stalled across 14+ days with solid adherence; adjusting caloric delta."
                      : "Body weight and performance trends indicate steady physiological progression."}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-300 text-[11px]">Input Basis</span>
                    <span className="font-mono text-purple-400 font-bold text-xs">
                      {objective_data_available ? "Logs Active" : "Baseline"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-[11px] leading-relaxed">
                    {objective_data_available
                      ? "Decisions dynamically integrate your logged daily nutrition, workouts, and wellness telemetry."
                      : "Currently using computational Mifflin-St Jeor baseline defaults until daily logs are recorded."}
                  </p>
                </div>
              </div>
            )}

            {/* Actionable Recommendations */}
            {actionable_recommendations && actionable_recommendations.length > 0 && (
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Actionable Protocols</span>
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

      {/* ========================================================================= */}
      {/* E. COLLAPSIBLE: Your Recent Progress (Readiness Trend)                     */}
      {/* ========================================================================= */}
      <div className="pt-2 border-t border-gray-800/70 space-y-3">
        <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 hover:border-gray-700/80 transition-colors">
          <button
            type="button"
            onClick={() => setTrendOpen(!trendOpen)}
            className="w-full flex items-center justify-between text-left text-xs font-semibold text-gray-200"
          >
            <div className="flex items-center gap-2.5">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <div>
                <span className="block text-gray-200">Your Recent Progress</span>
                <span className="text-[11px] font-normal text-gray-400">
                  Readiness history across {history.length} evaluation snapshot(s)
                </span>
              </div>
            </div>
            {trendOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
        </div>

        {trendOpen && (
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-3">
            {historyLoading && history.length === 0 && (
              <div className="p-4 flex items-center justify-center gap-2 text-xs text-gray-400 animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                <span>Loading historical readiness snapshots...</span>
              </div>
            )}

            {historyError && history.length === 0 && (
              <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800 flex items-center justify-between text-xs text-gray-400">
                <span>Historical readiness trend temporarily unavailable.</span>
                <button
                  onClick={() => loadHistory(true)}
                  className="px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-[11px] transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {!historyLoading && !historyError && history.length === 0 && (
              <div className="p-3 text-xs text-gray-500 bg-gray-950/40 rounded-lg border border-gray-800/80">
                No historical adaptation snapshots recorded yet. Snapshots are recorded when your daily logs, wellness telemetry, or plans change.
              </div>
            )}

            {!historyLoading && history.length === 1 && (
              <div className="p-3 bg-gray-950/50 rounded-lg border border-gray-800/80 space-y-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  <span className="font-mono text-cyan-300 font-bold">
                    {history[0].readiness_factor.toFixed(2)} Readiness
                  </span>
                  <span className="text-gray-400 text-[11px]">
                    ({new Date(history[0].created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })})
                  </span>
                </div>
                <p className="text-[11px] text-gray-500 italic">
                  1 historical snapshot recorded. A trend line will plot chronologically as additional evaluations occur over time.
                </p>
              </div>
            )}

            {history.length >= 2 && (() => {
              const chronological = [...history].reverse().slice(-14);
              const count = chronological.length;
              const minRf = 0.45;
              const maxRf = 1.15;
              const baselineY = 75 - ((1.00 - minRf) / (maxRf - minRf)) * 60;
              const getX = (idx: number) => 35 + (idx / (count - 1)) * 430;
              const getY = (rf: number) => {
                const clamped = Math.max(minRf, Math.min(maxRf, rf));
                return 75 - ((clamped - minRf) / (maxRf - minRf)) * 60;
              };
              const points = chronological.map((r, i) => `${getX(i).toFixed(1)},${getY(r.readiness_factor).toFixed(1)}`).join(" ");
              const areaPath = `M ${getX(0).toFixed(1)},75 ` +
                chronological.map((r, i) => `L ${getX(i).toFixed(1)},${getY(r.readiness_factor).toFixed(1)}`).join(" ") +
                ` L ${getX(count - 1).toFixed(1)},75 Z`;

              return (
                <div className="space-y-2">
                  <div className="w-full overflow-hidden">
                    <svg viewBox="0 0 500 95" className="w-full h-24 select-none">
                      <defs>
                        <linearGradient id="readinessGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.25" />
                          <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>

                      {/* Horizontal Guide: 1.00 Baseline */}
                      <line
                        x1="30"
                        y1={baselineY}
                        x2="475"
                        y2={baselineY}
                        stroke="#4b5563"
                        strokeDasharray="4 4"
                        strokeWidth="1"
                      />
                      <text
                        x="475"
                        y={baselineY - 3}
                        textAnchor="end"
                        className="fill-gray-500 font-mono text-[8px]"
                      >
                        1.00 Baseline
                      </text>

                      {/* Area fill */}
                      <path d={areaPath} fill="url(#readinessGrad)" />

                      {/* Polyline */}
                      <polyline
                        fill="none"
                        stroke="#22d3ee"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={points}
                      />

                      {/* Nodes */}
                      {chronological.map((r, i) => {
                        const cx = getX(i);
                        const cy = getY(r.readiness_factor);
                        return (
                          <g key={r.id || i}>
                            <circle
                              cx={cx}
                              cy={cy}
                              r="4"
                              className="fill-cyan-400 stroke-gray-950 stroke-[1.5]"
                            />
                            <title>
                              {`${new Date(r.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}: ${r.readiness_factor.toFixed(2)} RF`}
                            </title>
                          </g>
                        );
                      })}

                      {/* Date labels on bottom axis */}
                      <text
                        x={getX(0)}
                        y="90"
                        textAnchor="start"
                        className="fill-gray-400 font-mono text-[8px]"
                      >
                        {new Date(chronological[0].created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      </text>
                      <text
                        x={getX(count - 1)}
                        y="90"
                        textAnchor="end"
                        className="fill-gray-400 font-mono text-[8px]"
                      >
                        {new Date(chronological[count - 1].created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      </text>
                    </svg>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[10px] text-gray-500 border-t border-gray-800/40 pt-1.5">
                    <span>Displaying {count} historical evaluation points chronologically.</span>
                    <span className="italic">Calibrates to logged recovery & training.</span>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* F. COLLAPSIBLE: Past Adaptation History                                   */}
      {/* ========================================================================= */}
      <div className="pt-2 border-t border-gray-800/70 space-y-3">
        <div className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 hover:border-gray-700/80 transition-colors">
          <button
            type="button"
            onClick={toggleHistory}
            className="w-full flex items-center justify-between text-left text-xs font-semibold text-gray-300 hover:text-white transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <History className="w-4 h-4 text-cyan-400" />
              <div>
                <span className="block text-gray-200">Past Adaptation History</span>
                <span className="text-[11px] font-normal text-gray-400">Previous adaptation decisions recorded over time</span>
              </div>
            </div>
            {historyOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {historyOpen && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                loadHistory(true);
              }}
              disabled={historyLoading}
              className="ml-3 p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-cyan-300 transition-colors shrink-0"
              title="Refresh history"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${historyLoading ? "animate-spin text-cyan-400" : ""}`} />
            </button>
          )}
        </div>

        {historyOpen && (
          <div className="space-y-3 pt-1">
            {historyLoading && (
              <div className="p-6 text-center text-xs text-gray-400 flex items-center justify-center gap-2 bg-gray-900/40 rounded-xl border border-gray-800">
                <span className="animate-spin inline-block w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full" />
                <span>Loading adaptation history audit trail...</span>
              </div>
            )}

            {historyError && (
              <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/30 text-xs text-red-300 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                  <span>{historyError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => loadHistory(true)}
                  className="px-3 py-1 rounded-lg bg-red-900/60 hover:bg-red-800/80 text-red-200 text-[11px] font-medium transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {!historyLoading && !historyError && history.length === 0 && (
              <div className="p-6 rounded-xl bg-gray-900/40 border border-gray-800 text-center text-xs text-gray-400 space-y-1">
                <p className="text-gray-300 font-medium">No past adaptation decisions recorded yet.</p>
                <p className="text-[11px] text-gray-500">
                  New audit records are created automatically when your daily logs, wellness telemetry, or active plans produce updated adaptation recommendations.
                </p>
              </div>
            )}

            {!historyLoading && history.length > 0 && (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {history.map((record) => {
                  const dateStr = record.created_at
                    ? new Date(record.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "Previous Decision";
                  const rfPercent = (record.readiness_factor * 100).toFixed(0);
                  const isDeload = record.workout_adjustment?.deload_recommended;
                  const isFatigue = record.high_fatigue_flag;
                  const isExpanded = !!expandedHistoryIds[record.id];

                  return (
                    <div
                      key={record.id}
                      className="p-4 rounded-xl bg-gray-900/70 border border-gray-800/80 text-xs space-y-3 hover:border-gray-700/80 transition-colors"
                    >
                      {/* Top Header Row */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800/60 pb-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] text-gray-400">{dateStr}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800/70 text-gray-400 border border-gray-700/50">
                            {record.objective_data_available ? "Measured Telemetry" : "Baseline"}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-cyan-300">
                            {rfPercent}% Readiness
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase font-mono ${
                              isDeload
                                ? "bg-purple-950 text-purple-300 border border-purple-800"
                                : isFatigue
                                ? "bg-rose-950 text-rose-300 border border-rose-800"
                                : record.readiness_factor >= 1.0
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : "bg-gray-800 text-gray-300"
                            }`}
                          >
                            {isDeload
                              ? "Deload"
                              : isFatigue
                              ? "Fatigued"
                              : record.readiness_factor >= 1.0
                              ? "Optimal"
                              : "Moderate"}
                          </span>
                        </div>
                      </div>

                      {/* Prescribed Adjustments Summary */}
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-300">
                        <div className="flex items-center gap-1.5">
                          <Utensils className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Diet:</span>
                          <strong className="font-mono text-cyan-300">
                            {formatDelta(record.diet_adjustment.calorie_delta, "kcal")}
                          </strong>
                        </div>
                        <span>•</span>
                        <div className="flex items-center gap-1.5">
                          <Dumbbell className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Training:</span>
                          <strong className="text-emerald-300 capitalize">
                            {record.workout_adjustment.intensity} Intensity, {record.workout_adjustment.volume} Vol
                          </strong>
                          {record.workout_adjustment.deload_recommended && (
                            <span className="text-[10px] text-purple-300 font-bold px-1.5 py-0.2 rounded bg-purple-950 border border-purple-800">
                              Deload
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Coaching Synthesis */}
                      {record.coaching_summary && (
                        <p className="text-gray-300 text-[11px] leading-relaxed bg-gray-950/40 p-2.5 rounded-lg border border-gray-800/60">
                          &ldquo;{record.coaching_summary}&rdquo;
                        </p>
                      )}

                      {/* Mini Telemetry Pill Grid */}
                      <div className="grid grid-cols-5 gap-1.5 text-[10px] text-center pt-1 border-t border-gray-800/60 font-mono text-gray-400">
                        <div className="p-1 rounded bg-gray-950/50">
                          <span className="block text-gray-500">Rec</span>
                          <strong className="text-emerald-400">{record.recovery_score}</strong>
                        </div>
                        <div className="p-1 rounded bg-gray-950/50">
                          <span className="block text-gray-500">Sleep</span>
                          <strong className="text-blue-400">{record.sleep_quality}</strong>
                        </div>
                        <div className="p-1 rounded bg-gray-950/50">
                          <span className="block text-gray-500">Stress</span>
                          <strong className="text-purple-400">{record.stress_score}</strong>
                        </div>
                        <div className="p-1 rounded bg-gray-950/50">
                          <span className="block text-gray-500">Sore</span>
                          <strong className="text-rose-400">{record.injury_risk}</strong>
                        </div>
                        <div className="p-1 rounded bg-gray-950/50">
                          <span className="block text-gray-500">Adh</span>
                          <strong className="text-cyan-400">{record.adherence_score}%</strong>
                        </div>
                      </div>

                      {/* Expandable Details Toggle */}
                      <div className="pt-1">
                        <button
                          type="button"
                          onClick={() => toggleHistoryItem(record.id)}
                          className="flex items-center gap-1.5 text-[11px] font-medium text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          {isExpanded ? (
                            <>
                              <ChevronUp className="w-3.5 h-3.5" />
                              <span>Hide Adjustment Breakdown</span>
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-3.5 h-3.5" />
                              <span>View Full Adjustment Breakdown</span>
                            </>
                          )}
                        </button>

                        {isExpanded && (
                          <div className="mt-3 p-3.5 rounded-xl bg-gray-950/70 border border-gray-800 space-y-3">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              {/* Diet Breakdown */}
                              <div className="space-y-1.5">
                                <span className="text-[11px] font-bold text-gray-300 uppercase tracking-wider block">
                                  Nutrition Deltas
                                </span>
                                <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono">
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Calories</span>
                                    <span className="text-cyan-300 font-bold">
                                      {formatDelta(record.diet_adjustment.calorie_delta, "kcal")}
                                    </span>
                                  </div>
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Protein</span>
                                    <span className="text-emerald-300 font-bold">
                                      {formatDelta(record.diet_adjustment.protein_delta_g, "g")}
                                    </span>
                                  </div>
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Carbs</span>
                                    <span className="text-purple-300 font-bold">
                                      {formatDelta(record.diet_adjustment.carb_delta_g, "g")}
                                    </span>
                                  </div>
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Fat</span>
                                    <span className="text-amber-300 font-bold">
                                      {formatDelta(record.diet_adjustment.fat_delta_g, "g")}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Workout Breakdown */}
                              <div className="space-y-1.5">
                                <span className="text-[11px] font-bold text-gray-300 uppercase tracking-wider block">
                                  Workout Parameters
                                </span>
                                <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Intensity</span>
                                    <span className="text-gray-200 font-bold capitalize">
                                      {record.workout_adjustment.intensity}
                                    </span>
                                  </div>
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Volume</span>
                                    <span className="text-gray-200 font-bold capitalize">
                                      {record.workout_adjustment.volume}
                                    </span>
                                  </div>
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Extra Recovery</span>
                                    <span className="text-cyan-300 font-bold font-mono">
                                      {record.workout_adjustment.recovery_days} Days
                                    </span>
                                  </div>
                                  <div className="p-2 rounded bg-gray-900/80 border border-gray-800">
                                    <span className="text-gray-400 block text-[10px]">Conditioning</span>
                                    <span className="text-blue-300 font-bold font-mono">
                                      {record.workout_adjustment.cardio_minutes} Min
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Historical Driving Reasons if any */}
                            {record.reasons && record.reasons.length > 0 && (
                              <div className="space-y-1.5 pt-1 border-t border-gray-800/60">
                                <span className="text-[10px] uppercase font-bold text-gray-400 block">
                                  Driving Engine Signals
                                </span>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  {record.reasons.map((reason, rIdx) => (
                                    <div
                                      key={rIdx}
                                      className="p-2 rounded bg-gray-900/80 border border-gray-800 flex items-start justify-between gap-2 text-[11px]"
                                    >
                                      <div className="space-y-0.5">
                                        <span className="font-semibold text-gray-200 block text-[10px]">
                                          {getSignalLabel(reason.signal)}
                                        </span>
                                        <span className="text-gray-400 block leading-tight text-[10px]">
                                          {reason.message}
                                        </span>
                                      </div>
                                      <span
                                        className={`text-[9px] uppercase font-mono px-1.5 py-0.5 rounded border shrink-0 ${getEffectBadgeClass(
                                          reason.effect
                                        )}`}
                                      >
                                        {reason.effect}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Recommendations if any */}
                            {record.actionable_recommendations && record.actionable_recommendations.length > 0 && (
                              <div className="space-y-1.5 pt-1 border-t border-gray-800/60">
                                <span className="text-[10px] uppercase font-bold text-gray-400 block">
                                  Historical Protocol Directives
                                </span>
                                <ul className="space-y-1 text-[11px] text-gray-300 list-disc list-inside">
                                  {record.actionable_recommendations.map((rec, rIdx) => (
                                    <li key={rIdx}>{rec}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Linked Archived Plan IDs (Metadata Reference) */}
                            {(record.active_meal_plan_id || record.active_workout_plan_id) && (
                              <div className="pt-2 border-t border-gray-800/60 flex flex-wrap items-center gap-2 text-[10px] font-mono text-gray-400">
                                <span className="font-semibold text-gray-500 uppercase tracking-wider">Plan Audit Snapshot:</span>
                                {record.active_meal_plan_id && (
                                  <span
                                    className="px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-cyan-400"
                                    title="Archived meal plan snapshot identifier"
                                  >
                                    Meal Plan #{record.active_meal_plan_id.slice(0, 8)} (Archived ID)
                                  </span>
                                )}
                                {record.active_workout_plan_id && (
                                  <span
                                    className="px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-emerald-400"
                                    title="Archived workout plan snapshot identifier"
                                  >
                                    Workout Plan #{record.active_workout_plan_id.slice(0, 8)} (Archived ID)
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
