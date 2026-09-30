"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  fetchDailyLogs,
  submitDailyLog,
  DailyLog,
  DailyLogCreateRequest,
} from "@/lib/api";
import {
  Calendar,
  Scale,
  Flame,
  Dumbbell,
  Droplets,
  Zap,
  FileText,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  PlusCircle,
  Clock,
  TrendingUp,
  Target,
  Sparkles,
  Activity,
  HeartPulse,
  Moon,
} from "lucide-react";

function getTodayDateString(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function ProgressPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  // Data state
  const [logs, setLogs] = useState<DailyLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [logsError, setLogsError] = useState<string | null>(null);

  // Form submission state
  const [formData, setFormData] = useState({
    log_date: getTodayDateString(),
    weight_kg: "",
    calories_consumed: "",
    protein_consumed_g: "",
    carbs_consumed_g: "",
    fat_consumed_g: "",
    water_liters: "",
    workout_completed: false,
    energy_rating: "",
    notes: "",
    recovery_score: "",
    sleep_quality: "",
    stress_level: "",
    muscle_soreness: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  // Protect route
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  // Fetch daily logs
  const loadLogs = useCallback(async () => {
    setLoadingLogs(true);
    setLogsError(null);
    try {
      const res = await fetchDailyLogs();
      setLogs(res.logs || []);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load daily progress logs.";
      setLogsError(message);
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadLogs();
    }
  }, [user, loadLogs]);

  // If user selects a date that already has a log, pre-populate to assist upsert
  const handleDateChange = (newDate: string) => {
    setFormData((prev) => {
      const existing = logs.find((l) => l.log_date === newDate);
      if (existing) {
        return {
          log_date: newDate,
          weight_kg: existing.weight_kg !== null ? String(existing.weight_kg) : "",
          calories_consumed:
            existing.calories_consumed !== null ? String(existing.calories_consumed) : "",
          protein_consumed_g:
            existing.protein_consumed_g !== null ? String(existing.protein_consumed_g) : "",
          carbs_consumed_g:
            existing.carbs_consumed_g !== null ? String(existing.carbs_consumed_g) : "",
          fat_consumed_g: existing.fat_consumed_g !== null ? String(existing.fat_consumed_g) : "",
          water_liters: existing.water_liters !== null ? String(existing.water_liters) : "",
          workout_completed: existing.workout_completed,
          energy_rating: existing.energy_rating !== null ? String(existing.energy_rating) : "",
          notes: existing.notes || "",
          recovery_score:
            existing.recovery_score !== null && existing.recovery_score !== undefined
              ? String(existing.recovery_score)
              : "",
          sleep_quality:
            existing.sleep_quality !== null && existing.sleep_quality !== undefined
              ? String(existing.sleep_quality)
              : "",
          stress_level:
            existing.stress_level !== null && existing.stress_level !== undefined
              ? String(existing.stress_level)
              : "",
          muscle_soreness:
            existing.muscle_soreness !== null && existing.muscle_soreness !== undefined
              ? String(existing.muscle_soreness)
              : "",
        };
      }
      return { ...prev, log_date: newDate };
    });
  };

  const parseOptionalScore = (val: string, label: string): number | null => {
    if (val === "" || val === null || val === undefined) return null;
    const num = Number(val);
    if (!Number.isInteger(num) || num < 0 || num > 100) {
      throw new Error(`${label} must be an integer between 0 and 100.`);
    }
    return num;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setSubmitSuccess(null);
    setSubmitting(true);

    try {
      let recovery_score: number | null = null;
      let sleep_quality: number | null = null;
      let stress_level: number | null = null;
      let muscle_soreness: number | null = null;

      recovery_score = parseOptionalScore(formData.recovery_score, "Recovery");
      sleep_quality = parseOptionalScore(formData.sleep_quality, "Sleep Quality");
      stress_level = parseOptionalScore(formData.stress_level, "Stress Level");
      muscle_soreness = parseOptionalScore(formData.muscle_soreness, "Muscle Soreness");

      const req: DailyLogCreateRequest = {
        log_date: formData.log_date,
        weight_kg: formData.weight_kg !== "" ? parseFloat(formData.weight_kg) : null,
        calories_consumed:
          formData.calories_consumed !== "" ? parseInt(formData.calories_consumed, 10) : null,
        protein_consumed_g:
          formData.protein_consumed_g !== "" ? parseInt(formData.protein_consumed_g, 10) : null,
        carbs_consumed_g:
          formData.carbs_consumed_g !== "" ? parseInt(formData.carbs_consumed_g, 10) : null,
        fat_consumed_g:
          formData.fat_consumed_g !== "" ? parseInt(formData.fat_consumed_g, 10) : null,
        water_liters:
          formData.water_liters !== "" ? parseFloat(formData.water_liters) : null,
        workout_completed: formData.workout_completed,
        energy_rating:
          formData.energy_rating !== "" ? parseInt(formData.energy_rating, 10) : null,
        notes: formData.notes.trim() !== "" ? formData.notes.trim() : null,
        ...(recovery_score !== null ? { recovery_score } : {}),
        ...(sleep_quality !== null ? { sleep_quality } : {}),
        ...(stress_level !== null ? { stress_level } : {}),
        ...(muscle_soreness !== null ? { muscle_soreness } : {}),
      };

      await submitDailyLog(req);
      setSubmitSuccess(`Progress log for ${formData.log_date} successfully saved!`);

      // Refresh logs list
      await loadLogs();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred while saving.";
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="py-20 text-center text-gray-400">
        Loading progress tracking session...
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const isExistingDate = logs.some((l) => l.log_date === formData.log_date);

  return (
    <div className="max-w-6xl mx-auto space-y-10 py-6 px-4">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-cyan-400" />
            <span className="gradient-text-cyan">Daily Progress Tracker</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Log weight, nutrition, hydration, and training consistency. Updates automatically upsert by date.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
          <Target className="w-4 h-4 text-cyan-400" />
          <span>{logs.length} Logged {logs.length === 1 ? "Day" : "Days"}</span>
        </div>
      </div>

      {/* Progress Submission Form */}
      <div className="glass-card p-6 md:p-8 space-y-6 border border-gray-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800 pb-4">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-gray-100">
              {isExistingDate ? "Update Log for Selected Date" : "Log Today's Progress"}
            </h2>
          </div>
          {isExistingDate && (
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-amber-950/60 border border-amber-500/40 text-amber-300">
              Existing date selected (will update record)
            </span>
          )}
        </div>

        {submitSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-sm flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
            <span>{submitSuccess}</span>
          </div>
        )}

        {submitError && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400" />
            <span>{submitError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Row 1: Date & Body Weight */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Calendar className="w-3.5 h-3.5 text-cyan-400" /> Log Date
              </label>
              <input
                type="date"
                value={formData.log_date}
                onChange={(e) => handleDateChange(e.target.value)}
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-cyan-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Scale className="w-3.5 h-3.5 text-cyan-400" /> Weight (kg)
                <span className="text-gray-500 font-normal">(30 - 300 kg)</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="30"
                max="300"
                placeholder="e.g. 78.5"
                value={formData.weight_kg}
                onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-cyan-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Row 2: Macros & Calories */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Flame className="w-3.5 h-3.5 text-cyan-400" /> Calories (kcal)
                <span className="text-gray-500 font-normal">(500-8000)</span>
              </label>
              <input
                type="number"
                min="500"
                max="8000"
                placeholder="e.g. 2150"
                value={formData.calories_consumed}
                onChange={(e) =>
                  setFormData({ ...formData, calories_consumed: e.target.value })
                }
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Dumbbell className="w-3.5 h-3.5 text-emerald-400" /> Protein (g)
                <span className="text-gray-500 font-normal">(0-400)</span>
              </label>
              <input
                type="number"
                min="0"
                max="400"
                placeholder="e.g. 170"
                value={formData.protein_consumed_g}
                onChange={(e) =>
                  setFormData({ ...formData, protein_consumed_g: e.target.value })
                }
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Target className="w-3.5 h-3.5 text-purple-400" /> Carbs (g)
                <span className="text-gray-500 font-normal">(0-800)</span>
              </label>
              <input
                type="number"
                min="0"
                max="800"
                placeholder="e.g. 220"
                value={formData.carbs_consumed_g}
                onChange={(e) =>
                  setFormData({ ...formData, carbs_consumed_g: e.target.value })
                }
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-purple-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Fat (g)
                <span className="text-gray-500 font-normal">(0-300)</span>
              </label>
              <input
                type="number"
                min="0"
                max="300"
                placeholder="e.g. 70"
                value={formData.fat_consumed_g}
                onChange={(e) =>
                  setFormData({ ...formData, fat_consumed_g: e.target.value })
                }
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-amber-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Row 3: Hydration, Energy & Workout Complete */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Droplets className="w-3.5 h-3.5 text-blue-400" /> Water (Liters)
                <span className="text-gray-500 font-normal">(0 - 10 L)</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="10"
                placeholder="e.g. 3.2"
                value={formData.water_liters}
                onChange={(e) =>
                  setFormData({ ...formData, water_liters: e.target.value })
                }
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Zap className="w-3.5 h-3.5 text-yellow-400" /> Energy Rating (1-10)
              </label>
              <select
                value={formData.energy_rating}
                onChange={(e) =>
                  setFormData({ ...formData, energy_rating: e.target.value })
                }
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-yellow-500 focus:outline-none"
              >
                <option value="">Select energy rating</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((val) => (
                  <option key={val} value={val}>
                    {val} - {val <= 3 ? "Low Fatigue" : val <= 7 ? "Moderate / Good" : "Peak Energy"}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col justify-center">
              <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
                <Dumbbell className="w-3.5 h-3.5 text-emerald-400" /> Workout Completed
              </span>
              <label className="flex items-center gap-3 p-3 rounded-xl bg-gray-900 border border-gray-800 cursor-pointer hover:border-gray-700 transition">
                <input
                  type="checkbox"
                  checked={formData.workout_completed}
                  onChange={(e) =>
                    setFormData({ ...formData, workout_completed: e.target.checked })
                  }
                  className="w-4 h-4 text-cyan-600 rounded bg-gray-800 border-gray-700 focus:ring-cyan-500"
                />
                <span className="text-sm font-medium text-gray-300">
                  {formData.workout_completed ? "Workout Finished Today" : "Rest / Off Day"}
                </span>
              </label>
            </div>
          </div>

          {/* Row 4: Daily Wellness Telemetry (Optional) */}
          <div className="space-y-4 pt-4 border-t border-gray-800">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div>
                <h3 className="text-sm font-bold text-gray-200 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Daily Wellness Telemetry
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
                    Optional
                  </span>
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Subjective physiological telemetry that dynamically refines your AI readiness, workout volume, and recovery days.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Recovery */}
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="recovery-score-slider" className="text-xs font-semibold text-gray-200 flex items-center gap-1.5 cursor-pointer">
                    <Activity className="w-3.5 h-3.5 text-emerald-400" />
                    Recovery
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      {formData.recovery_score !== "" ? `${formData.recovery_score} / 100` : "Not set"}
                    </span>
                    {formData.recovery_score !== "" && (
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, recovery_score: "" })}
                        className="text-[10px] text-gray-500 hover:text-gray-300 transition underline"
                        aria-label="Clear recovery score"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <input
                  id="recovery-score-slider"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={formData.recovery_score === "" ? 50 : formData.recovery_score}
                  onChange={(e) => setFormData({ ...formData, recovery_score: e.target.value })}
                  aria-label="Recovery (0 = Very poor recovery, 100 = Fully recovered)"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={formData.recovery_score === "" ? undefined : parseInt(formData.recovery_score, 10)}
                  className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
                />
                <div className="flex justify-between text-[10px] text-gray-500 font-medium">
                  <span>0 = Very poor recovery</span>
                  <span>100 = Fully recovered</span>
                </div>
              </div>

              {/* Sleep Quality */}
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="sleep-quality-slider" className="text-xs font-semibold text-gray-200 flex items-center gap-1.5 cursor-pointer">
                    <Moon className="w-3.5 h-3.5 text-blue-400" />
                    Sleep Quality
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-blue-400">
                      {formData.sleep_quality !== "" ? `${formData.sleep_quality} / 100` : "Not set"}
                    </span>
                    {formData.sleep_quality !== "" && (
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, sleep_quality: "" })}
                        className="text-[10px] text-gray-500 hover:text-gray-300 transition underline"
                        aria-label="Clear sleep quality"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <input
                  id="sleep-quality-slider"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={formData.sleep_quality === "" ? 50 : formData.sleep_quality}
                  onChange={(e) => setFormData({ ...formData, sleep_quality: e.target.value })}
                  aria-label="Sleep Quality (0 = Very poor sleep, 100 = Excellent sleep)"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={formData.sleep_quality === "" ? undefined : parseInt(formData.sleep_quality, 10)}
                  className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-blue-400"
                />
                <div className="flex justify-between text-[10px] text-gray-500 font-medium">
                  <span>0 = Very poor sleep</span>
                  <span>100 = Excellent sleep</span>
                </div>
              </div>

              {/* Stress Level */}
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="stress-level-slider" className="text-xs font-semibold text-gray-200 flex items-center gap-1.5 cursor-pointer">
                    <HeartPulse className="w-3.5 h-3.5 text-purple-400" />
                    Stress Level
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-purple-400">
                      {formData.stress_level !== "" ? `${formData.stress_level} / 100` : "Not set"}
                    </span>
                    {formData.stress_level !== "" && (
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, stress_level: "" })}
                        className="text-[10px] text-gray-500 hover:text-gray-300 transition underline"
                        aria-label="Clear stress level"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <input
                  id="stress-level-slider"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={formData.stress_level === "" ? 50 : formData.stress_level}
                  onChange={(e) => setFormData({ ...formData, stress_level: e.target.value })}
                  aria-label="Stress Level (0 = No stress, 100 = Extreme stress)"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={formData.stress_level === "" ? undefined : parseInt(formData.stress_level, 10)}
                  className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
                />
                <div className="flex justify-between text-[10px] text-gray-500 font-medium">
                  <span>0 = No stress</span>
                  <span>100 = Extreme stress</span>
                </div>
              </div>

              {/* Muscle Soreness */}
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="muscle-soreness-slider" className="text-xs font-semibold text-gray-200 flex items-center gap-1.5 cursor-pointer">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    Muscle Soreness
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-amber-400">
                      {formData.muscle_soreness !== "" ? `${formData.muscle_soreness} / 100` : "Not set"}
                    </span>
                    {formData.muscle_soreness !== "" && (
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, muscle_soreness: "" })}
                        className="text-[10px] text-gray-500 hover:text-gray-300 transition underline"
                        aria-label="Clear muscle soreness"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <input
                  id="muscle-soreness-slider"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={formData.muscle_soreness === "" ? 50 : formData.muscle_soreness}
                  onChange={(e) => setFormData({ ...formData, muscle_soreness: e.target.value })}
                  aria-label="Muscle Soreness (0 = No soreness, 100 = Extreme soreness)"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={formData.muscle_soreness === "" ? undefined : parseInt(formData.muscle_soreness, 10)}
                  className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
                />
                <div className="flex justify-between text-[10px] text-gray-500 font-medium">
                  <span>0 = No soreness</span>
                  <span>100 = Extreme soreness</span>
                </div>
              </div>
            </div>
          </div>

          {/* Row 5: Notes */}
          <div>
            <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 mb-2">
              <FileText className="w-3.5 h-3.5 text-gray-400" /> Daily Notes
              <span className="text-gray-500 font-normal">(Max 500 characters)</span>
            </label>
            <textarea
              maxLength={500}
              rows={3}
              placeholder="e.g. Great session today. Felt strong on bench press. Drank extra water post-workout."
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm text-gray-200 focus:border-cyan-500 focus:outline-none resize-none"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3.5 px-6 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold flex items-center justify-center gap-2 glow-btn transition disabled:opacity-50"
          >
            <TrendingUp className="w-4 h-4" />
            {submitting ? "Saving Daily Log..." : isExistingDate ? "Update Daily Log" : "Submit Daily Log"}
          </button>
        </form>
      </div>

      {/* Historical Daily Logs Section */}
      <div className="glass-card p-6 md:p-8 space-y-6 border border-gray-800">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-gray-800 pb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-gray-100">Progress History</h2>
          </div>
          <button
            onClick={loadLogs}
            disabled={loadingLogs}
            className="flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-cyan-400 transition disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loadingLogs ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {loadingLogs ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            Loading daily progress history...
          </div>
        ) : logsError ? (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-sm flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400" />
              <span>{logsError}</span>
            </div>
            <button
              onClick={loadLogs}
              className="px-3 py-1 rounded-lg bg-red-900/60 hover:bg-red-800/60 text-xs font-medium text-red-200 transition"
            >
              Retry
            </button>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-gray-400 space-y-2">
            <Calendar className="w-8 h-8 mx-auto text-gray-600" />
            <p className="text-sm">No progress logs recorded yet.</p>
            <p className="text-xs text-gray-500">
              Submit your first daily log above to start tracking your physique metrics!
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-xs uppercase tracking-wider text-gray-400">
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-3">Weight</th>
                    <th className="py-3 px-3">Calories</th>
                    <th className="py-3 px-3">Macros (P / C / F)</th>
                    <th className="py-3 px-3">Water</th>
                    <th className="py-3 px-3">Workout</th>
                    <th className="py-3 px-3">Energy</th>
                    <th className="py-3 px-3">Wellness</th>
                    <th className="py-3 px-3">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      className="hover:bg-gray-900/50 transition-colors"
                    >
                      <td className="py-3.5 px-3 font-mono font-medium text-cyan-300">
                        {log.log_date}
                      </td>
                      <td className="py-3.5 px-3 font-semibold text-gray-100">
                        {log.weight_kg !== null ? `${log.weight_kg} kg` : "—"}
                      </td>
                      <td className="py-3.5 px-3 font-semibold text-gray-200">
                        {log.calories_consumed !== null ? `${log.calories_consumed} kcal` : "—"}
                      </td>
                      <td className="py-3.5 px-3 text-xs font-mono">
                        {log.protein_consumed_g !== null ||
                        log.carbs_consumed_g !== null ||
                        log.fat_consumed_g !== null ? (
                          <span className="space-x-1.5">
                            <span className="text-emerald-400">
                              {log.protein_consumed_g ?? 0}g P
                            </span>
                            <span className="text-gray-600">/</span>
                            <span className="text-purple-400">
                              {log.carbs_consumed_g ?? 0}g C
                            </span>
                            <span className="text-gray-600">/</span>
                            <span className="text-amber-400">
                              {log.fat_consumed_g ?? 0}g F
                            </span>
                          </span>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-3 text-blue-300 font-medium">
                        {log.water_liters !== null ? `${log.water_liters} L` : "—"}
                      </td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            log.workout_completed
                              ? "bg-emerald-950/70 border border-emerald-500/40 text-emerald-300"
                              : "bg-gray-800 border border-gray-700 text-gray-400"
                          }`}
                        >
                          {log.workout_completed ? "Completed" : "Rest Day"}
                        </span>
                      </td>
                      <td className="py-3.5 px-3">
                        {log.energy_rating !== null ? (
                          <span className="font-mono text-yellow-300">
                            {log.energy_rating} / 10
                          </span>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-3 text-xs font-mono">
                        {(log.recovery_score !== null && log.recovery_score !== undefined) ||
                        (log.sleep_quality !== null && log.sleep_quality !== undefined) ||
                        (log.stress_level !== null && log.stress_level !== undefined) ||
                        (log.muscle_soreness !== null && log.muscle_soreness !== undefined) ? (
                          <div className="flex flex-wrap gap-1 text-[11px]">
                            {log.recovery_score != null && (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40" title="Recovery Score">
                                R:{log.recovery_score}
                              </span>
                            )}
                            {log.sleep_quality != null && (
                              <span className="px-1.5 py-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-800/40" title="Sleep Quality">
                                S:{log.sleep_quality}
                              </span>
                            )}
                            {log.stress_level != null && (
                              <span className="px-1.5 py-0.5 rounded bg-purple-950/60 text-purple-400 border border-purple-800/40" title="Stress Level">
                                Str:{log.stress_level}
                              </span>
                            )}
                            {log.muscle_soreness != null && (
                              <span className="px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800/40" title="Muscle Soreness">
                                Sor:{log.muscle_soreness}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-3 text-xs text-gray-400 max-w-xs truncate" title={log.notes || ""}>
                        {log.notes || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden space-y-3">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-bold text-cyan-300">
                      {log.log_date}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        log.workout_completed
                          ? "bg-emerald-950/70 border border-emerald-500/40 text-emerald-300"
                          : "bg-gray-800 border border-gray-700 text-gray-400"
                      }`}
                    >
                      {log.workout_completed ? "Workout Done" : "Rest Day"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500 block">Weight</span>
                      <span className="font-bold text-gray-100">
                        {log.weight_kg !== null ? `${log.weight_kg} kg` : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Calories</span>
                      <span className="font-bold text-gray-100">
                        {log.calories_consumed !== null ? `${log.calories_consumed} kcal` : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Water</span>
                      <span className="font-bold text-blue-300">
                        {log.water_liters !== null ? `${log.water_liters} L` : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Energy</span>
                      <span className="font-bold text-yellow-300">
                        {log.energy_rating !== null ? `${log.energy_rating} / 10` : "—"}
                      </span>
                    </div>
                  </div>

                  {(log.protein_consumed_g !== null ||
                    log.carbs_consumed_g !== null ||
                    log.fat_consumed_g !== null) && (
                    <div className="text-xs font-mono pt-1 border-t border-gray-800/80 flex items-center justify-between">
                      <span className="text-emerald-400">P: {log.protein_consumed_g ?? 0}g</span>
                      <span className="text-purple-400">C: {log.carbs_consumed_g ?? 0}g</span>
                      <span className="text-amber-400">F: {log.fat_consumed_g ?? 0}g</span>
                    </div>
                  )}

                  {(log.recovery_score != null ||
                    log.sleep_quality != null ||
                    log.stress_level != null ||
                    log.muscle_soreness != null) && (
                    <div className="text-xs font-mono pt-1 border-t border-gray-800/80 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] text-gray-500 uppercase">Wellness:</span>
                      {log.recovery_score != null && <span className="text-emerald-400">Rec {log.recovery_score}</span>}
                      {log.sleep_quality != null && <span className="text-blue-400">Sleep {log.sleep_quality}</span>}
                      {log.stress_level != null && <span className="text-purple-400">Stress {log.stress_level}</span>}
                      {log.muscle_soreness != null && <span className="text-amber-400">Soreness {log.muscle_soreness}</span>}
                    </div>
                  )}

                  {log.notes && (
                    <div className="text-xs text-gray-400 bg-gray-950/40 p-2 rounded-lg border border-gray-800/60 italic">
                      "{log.notes}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
