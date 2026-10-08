"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { saveProfile, UserProfile } from "@/lib/api";
import {
  User,
  Activity,
  Flame,
  Utensils,
  CheckCircle2,
  Check,
  Target,
  Dumbbell,
  Scale,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  TrendingDown,
  TrendingUp,
  Minus,
  ShieldCheck,
  Droplets,
  Lock,
} from "lucide-react";

// Deterministic client-side preview calculator (exact parity with apps/api/app/engine/bmr_tdee.py)
function calculateLiveTargetMetrics(formData: UserProfile) {
  const { weight_kg, height_cm, age, gender, activity_level, goal_type, body_fat_pct } = formData;
  if (!weight_kg || !height_cm || !age || weight_kg <= 0 || height_cm <= 0 || age <= 0) {
    return null;
  }

  // BMR Calculation: Katch-McArdle if body_fat_pct in [3, 60], otherwise Mifflin-St Jeor
  let bmr: number;
  if (body_fat_pct && body_fat_pct >= 3.0 && body_fat_pct <= 60.0) {
    const lbm = weight_kg * (1.0 - body_fat_pct / 100.0);
    bmr = 370.0 + 21.6 * lbm;
  } else {
    const base = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age;
    if (gender === "male") bmr = base + 5.0;
    else if (gender === "female") bmr = base - 161.0;
    else bmr = base - 78.0;
  }
  bmr = Math.max(bmr, 800.0);

  const multipliers: Record<string, number> = {
    sedentary: 1.2,
    lightly_active: 1.375,
    moderately_active: 1.55,
    very_active: 1.725,
    extra_active: 1.9,
  };
  const multiplier = multipliers[activity_level] || 1.2;
  const tdee = bmr * multiplier;

  // Caloric adjustment by goal
  let raw_calories = tdee;
  let protein_g_per_kg = 2.1;
  if (goal_type === "fat_loss") {
    const deficit = Math.min(tdee * 0.20, 750.0);
    raw_calories = tdee - deficit;
    protein_g_per_kg = 2.2;
  } else if (goal_type === "muscle_gain") {
    const surplus = Math.min(tdee * 0.12, 400.0);
    raw_calories = tdee + surplus;
    protein_g_per_kg = 2.0;
  } else if (goal_type === "weight_gain") {
    const surplus = Math.min(tdee * 0.15, 500.0);
    raw_calories = tdee + surplus;
    protein_g_per_kg = 1.8;
  }

  const calorieFloors: Record<string, number> = {
    male: 1500,
    female: 1200,
    other: 1350,
  };
  const floor = calorieFloors[gender] || 1350;
  const target_calories = Math.round(Math.max(raw_calories, floor));

  const protein_g = Math.round(weight_kg * protein_g_per_kg * 10) / 10;
  const min_fat_g = weight_kg * 0.8;
  const fat_from_pct = (target_calories * 0.25) / 9.0;
  const fat_g = Math.round(Math.max(fat_from_pct, min_fat_g) * 10) / 10;

  const remaining_calories = Math.max(target_calories - (protein_g * 4.0 + fat_g * 9.0), 0.0);
  const carbs_g = Math.round((remaining_calories / 4.0) * 10) / 10;

  const min_fiber = gender === "male" ? 38.0 : 25.0;
  const fiber_g = Math.round(Math.max((target_calories / 1000.0) * 14.0, min_fiber) * 10) / 10;
  const water_liters = Math.round(((weight_kg * 0.035) + 0.5) * 10) / 10;

  return {
    bmr: Math.round(bmr),
    tdee: Math.round(tdee),
    target_calories,
    protein_g,
    carbs_g,
    fat_g,
    fiber_g,
    water_liters,
    is_calorie_floor_applied: target_calories === floor,
  };
}

export default function OnboardingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [currentStep, setCurrentStep] = useState<1 | 2>(1);

  const [formData, setFormData] = useState<UserProfile>({
    first_name: "Gokul",
    gender: "male",
    age: 22,
    height_cm: 178,
    weight_kg: 78,
    target_weight_kg: 72,
    body_fat_pct: 18,
    activity_level: "moderately_active",
    goal_type: "fat_loss",
    dietary_preference: "vegetarian",
    workout_days_per_week: 4,
    experience_level: "intermediate",
  });

  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Authentication guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  // Live real-time preview computation
  const liveTargets = useMemo(() => {
    return calculateLiveTargetMetrics(formData);
  }, [formData]);

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
        <span className="animate-spin inline-block w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full" />
        <p className="text-sm font-medium text-slate-400">Loading physiological profile...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const validateStep1 = () => {
    if (!formData.first_name.trim()) {
      setError("Please enter your first name.");
      return false;
    }
    if (!formData.age || formData.age < 14 || formData.age > 100) {
      setError("Please enter a valid age between 14 and 100.");
      return false;
    }
    if (!formData.height_cm || formData.height_cm < 100 || formData.height_cm > 250) {
      setError("Please enter a valid height between 100 and 250 cm.");
      return false;
    }
    if (!formData.weight_kg || formData.weight_kg < 30 || formData.weight_kg > 300) {
      setError("Please enter a valid weight between 30 and 300 kg.");
      return false;
    }
    if (!formData.target_weight_kg || formData.target_weight_kg < 30 || formData.target_weight_kg > 300) {
      setError("Please enter a valid target weight between 30 and 300 kg.");
      return false;
    }
    setError(null);
    return true;
  };

  const validateStep2 = () => {
    if (!formData.goal_type) {
      setError("Please select your primary fitness goal.");
      return false;
    }
    if (!formData.activity_level) {
      setError("Please select your daily activity level.");
      return false;
    }
    if (!formData.dietary_preference) {
      setError("Please select your dietary preference.");
      return false;
    }
    setError(null);
    return true;
  };

  const goToNextStep = () => {
    if (currentStep === 1) {
      if (validateStep1()) setCurrentStep(2);
    }
  };

  const goToPrevStep = () => {
    setError(null);
    setCurrentStep(1);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!validateStep1() || !validateStep2()) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await saveProfile(formData);
      setSaved(true);
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to initialize profile. Please try again.");
      setLoading(false);
    }
  };

  const weightDelta = formData.target_weight_kg - formData.weight_kg;

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16">
      {/* 1. Top progress/step indicator */}
      <div className="glass-card p-6 sm:p-8 text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-cyan-950/70 border border-cyan-500/30 text-cyan-300">
            <Dumbbell className="w-3.5 h-3.5 text-cyan-400" />
            {currentStep === 1 ? "STEP 1 OF 2 • YOUR PROFILE" : "STEP 2 OF 2 • GOALS & TARGETS"}
          </span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
          {currentStep === 1 ? "Build your fitness baseline" : "Calibrate your fitness targets"}
        </h1>

        <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto leading-relaxed">
          {currentStep === 1
            ? "Tell us a few things about yourself so FitEngine can calculate your personalized targets."
            : "Fine-tune your activity, nutritional preferences, and training frequency."}
        </p>

        {/* 2-Step Visual Bar */}
        <div className="pt-3 max-w-sm mx-auto">
          <div className="grid grid-cols-2 gap-3 text-center text-[11px] font-mono uppercase tracking-wider">
            <button
              type="button"
              onClick={() => setCurrentStep(1)}
              className="flex flex-col items-center gap-1.5 cursor-pointer focus:outline-none"
            >
              <span className={`font-semibold flex items-center gap-1 ${currentStep === 1 ? "text-cyan-400" : "text-slate-300"}`}>
                {currentStep > 1 ? <Check className="w-3 h-3 text-cyan-400" /> : <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />}
                1. Profile
              </span>
              <div className={`w-full h-1 rounded-full ${currentStep === 1 ? "bg-cyan-400 shadow-sm shadow-cyan-400/50" : "bg-cyan-900"}`} />
            </button>

            <button
              type="button"
              onClick={() => {
                if (validateStep1()) setCurrentStep(2);
              }}
              className="flex flex-col items-center gap-1.5 cursor-pointer focus:outline-none"
            >
              <span className={`font-semibold flex items-center gap-1 ${currentStep === 2 ? "text-cyan-400" : "text-slate-500"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${currentStep === 2 ? "bg-cyan-400" : "bg-slate-600"}`} />
                2. Goals & Preview
              </span>
              <div className={`w-full h-1 rounded-full ${currentStep === 2 ? "bg-cyan-400 shadow-sm shadow-cyan-400/50" : "bg-slate-800"}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Success Notification Banner */}
      {saved && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 flex items-center gap-3.5 animate-in fade-in duration-200">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div className="flex-1 text-xs sm:text-sm">
            <span className="font-semibold text-white">Targets Calibrated Successfully!</span>
            <span className="text-emerald-300/80 ml-2">Redirecting to your dashboard...</span>
          </div>
          <span className="animate-spin inline-block w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full shrink-0" />
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5 animate-in fade-in duration-200">
          <span className="font-semibold text-rose-200">Validation Notice:</span>
          <span>{error}</span>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* STEP 1: PERSONAL INFORMATION & BODY METRICS                        */}
      {/* ------------------------------------------------------------------ */}
      {currentStep === 1 && (
        <div className="glass-card p-6 sm:p-8 space-y-6 animate-in fade-in duration-200">
          <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                2. Personal Information & Biometrics
              </h3>
              <p className="text-xs text-slate-400">Core parameters for Mifflin-St Jeor thermodynamic modeling</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* First Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                First Name <span className="text-cyan-400">*</span>
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                placeholder="e.g. Gokul"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 transition"
              />
              <p className="text-[11px] text-slate-500">Used for correspondence and greetings.</p>
            </div>

            {/* Biological Gender */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Biological Gender <span className="text-cyan-400">*</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["male", "female", "other"] as const).map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setFormData({ ...formData, gender: g })}
                    className={`py-2.5 px-3 rounded-xl text-xs font-semibold capitalize border transition-all ${
                      formData.gender === g
                        ? "bg-cyan-500/15 border-cyan-500/60 text-cyan-300 ring-1 ring-cyan-500/30"
                        : "bg-[#0b1020] border-white/[0.08] text-slate-400 hover:text-white hover:border-white/[0.15]"
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-slate-500">Calibrates standard biological constants.</p>
            </div>

            {/* Age */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Age <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={14}
                  max={100}
                  value={formData.age || ""}
                  onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                  placeholder="22"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 pr-16"
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono text-slate-500 pointer-events-none">
                  years
                </span>
              </div>
            </div>

            {/* Height */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Height <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={100}
                  max={250}
                  value={formData.height_cm || ""}
                  onChange={(e) => setFormData({ ...formData, height_cm: Number(e.target.value) })}
                  placeholder="178"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 pr-14"
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono text-slate-500 pointer-events-none">
                  cm
                </span>
              </div>
            </div>

            {/* Current Weight */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Current Weight <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  min={30}
                  max={300}
                  value={formData.weight_kg || ""}
                  onChange={(e) => setFormData({ ...formData, weight_kg: Number(e.target.value) })}
                  placeholder="78"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 pr-14"
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono text-slate-500 pointer-events-none">
                  kg
                </span>
              </div>
            </div>

            {/* Target Weight */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 block">
                  Target Weight <span className="text-cyan-400">*</span>
                </label>
                {weightDelta !== 0 && (
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                      weightDelta < 0
                        ? "bg-amber-950/60 text-amber-300 border border-amber-800/40"
                        : "bg-emerald-950/60 text-emerald-300 border border-emerald-800/40"
                    }`}
                  >
                    {weightDelta < 0 ? `↓ ${Math.abs(weightDelta).toFixed(1)} kg delta` : `↑ ${weightDelta.toFixed(1)} kg delta`}
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  min={30}
                  max={300}
                  value={formData.target_weight_kg || ""}
                  onChange={(e) => setFormData({ ...formData, target_weight_kg: Number(e.target.value) })}
                  placeholder="72"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 pr-14"
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono text-slate-500 pointer-events-none">
                  kg
                </span>
              </div>
            </div>
          </div>

          {/* Step 1 CTA */}
          <div className="flex justify-end pt-4 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={goToNextStep}
              className="py-3 px-8 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm tracking-wide transition shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-cyan-400/50 flex items-center gap-2 cursor-pointer"
            >
              <span>Continue to Goals & Activity</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* STEP 2: FITNESS GOAL & ACTIVITY + TARGET PREVIEW PANEL             */}
      {/* ------------------------------------------------------------------ */}
      {currentStep === 2 && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* 3. Fitness Goal & Activity Card */}
          <div className="glass-card p-6 sm:p-8 space-y-6">
            <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                <Target className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                  3. Fitness Goal & Activity
                </h3>
                <p className="text-xs text-slate-400">Configure energetic deficit/surplus, training cadence, and nutrition</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {/* Primary Goal */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Primary Goal <span className="text-cyan-400">*</span>
                </label>
                <select
                  value={formData.goal_type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      goal_type: e.target.value as UserProfile["goal_type"],
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30"
                >
                  <option value="fat_loss">Fat Loss (-20% Deficit, high protein)</option>
                  <option value="muscle_gain">Muscle Gain (+12% Caloric Surplus)</option>
                  <option value="recomposition">Maintenance / Recomposition (Equilibrium)</option>
                  <option value="weight_gain">Aggressive Mass Gain (+15% Surplus)</option>
                </select>
                <p className="text-[11px] text-slate-500">Determines energy balance calculations.</p>
              </div>

              {/* Daily Activity Level */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Daily Activity Level <span className="text-cyan-400">*</span>
                </label>
                <select
                  value={formData.activity_level}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      activity_level: e.target.value as UserProfile["activity_level"],
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30"
                >
                  <option value="sedentary">Sedentary (1.20× — Desk job, minimal walking)</option>
                  <option value="lightly_active">Lightly Active (1.38× — Exercise 1–3 days/wk)</option>
                  <option value="moderately_active">Moderately Active (1.55× — Exercise 3–5 days/wk)</option>
                  <option value="very_active">Very Active (1.73× — Heavy training 6–7 days/wk)</option>
                  <option value="extra_active">Extra Active (1.90× — Physical job & 2x training)</option>
                </select>
                <p className="text-[11px] text-slate-500">Calibrates Total Daily Energy Expenditure (TDEE).</p>
              </div>

              {/* Dietary Preference */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Dietary Preference <span className="text-cyan-400">*</span>
                </label>
                <select
                  value={formData.dietary_preference}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      dietary_preference: e.target.value as UserProfile["dietary_preference"],
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30"
                >
                  <option value="anything">Standard / Non-Vegetarian (Omnivorous)</option>
                  <option value="vegetarian">Vegetarian (Plant-focused + dairy & eggs)</option>
                  <option value="vegan">Vegan (100% plant-based)</option>
                  <option value="keto">Ketogenic (High fat, low carb)</option>
                  <option value="paleo">Paleo (Unprocessed whole foods)</option>
                </select>
                <p className="text-[11px] text-slate-500">Shapes automatic meal plan generation.</p>
              </div>

              {/* Workout Days / Week */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Workout Days / Week <span className="text-cyan-400">*</span>
                </label>
                <select
                  value={formData.workout_days_per_week}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      workout_days_per_week: Number(e.target.value),
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b1020] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30"
                >
                  <option value={2}>2 Days / Week (Full Body Maintenance)</option>
                  <option value={3}>3 Days / Week (Push / Pull / Legs)</option>
                  <option value={4}>4 Days / Week (Upper / Lower Split)</option>
                  <option value={5}>5 Days / Week (Body Part Periodization)</option>
                  <option value={6}>6 Days / Week (High Frequency PPL)</option>
                </select>
                <p className="text-[11px] text-slate-500">Customizes resistance workout frequency.</p>
              </div>
            </div>
          </div>

          {/* 4. Target preview panel */}
          <div className="glass-card p-6 sm:p-7 border border-cyan-500/30 bg-gradient-to-br from-cyan-950/20 via-[#0b1020] to-[#070b12] space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-white">
                  DAILY TARGET PREVIEW
                </span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40">
                Thermodynamic Model Live
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="p-3.5 rounded-xl bg-[#0b1020]/90 border border-white/[0.08] text-center space-y-0.5">
                <span className="text-[11px] font-mono uppercase text-slate-400 block flex items-center justify-center gap-1">
                  <Flame className="w-3.5 h-3.5 text-amber-400" /> Calories
                </span>
                <span className="text-lg sm:text-2xl font-extrabold font-mono text-cyan-300">
                  {liveTargets?.target_calories ?? 2172}
                </span>
                <span className="text-[10px] text-slate-400 block">kcal / day</span>
              </div>

              <div className="p-3.5 rounded-xl bg-[#0b1020]/90 border border-white/[0.08] text-center space-y-0.5">
                <span className="text-[11px] font-mono uppercase text-slate-400 block flex items-center justify-center gap-1">
                  <Dumbbell className="w-3.5 h-3.5 text-emerald-400" /> Protein
                </span>
                <span className="text-lg sm:text-2xl font-extrabold font-mono text-emerald-300">
                  {liveTargets ? Math.round(liveTargets.protein_g) : 172}
                </span>
                <span className="text-[10px] text-slate-400 block">g / day</span>
              </div>

              <div className="p-3.5 rounded-xl bg-[#0b1020]/90 border border-white/[0.08] text-center space-y-0.5">
                <span className="text-[11px] font-mono uppercase text-slate-400 block flex items-center justify-center gap-1">
                  <Droplets className="w-3.5 h-3.5 text-blue-400" /> Hydration
                </span>
                <span className="text-lg sm:text-2xl font-extrabold font-mono text-blue-300">
                  {liveTargets?.water_liters ?? 3.2}
                </span>
                <span className="text-[10px] text-slate-400 block">L / day</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
              <span>Estimated TDEE: {liveTargets?.tdee ?? 2715} kcal</span>
              <span>BMR: {liveTargets?.bmr ?? 1752} kcal</span>
            </div>
          </div>

          {/* 5. Primary CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <button
              type="button"
              onClick={goToPrevStep}
              className="w-full sm:w-auto py-3 px-5 rounded-xl bg-[#0b1020] border border-white/[0.08] hover:border-white/[0.18] text-slate-300 hover:text-white text-xs font-semibold flex items-center justify-center gap-2 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Profile</span>
            </button>

            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={loading || saved}
              className="w-full sm:w-auto py-3.5 px-10 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm tracking-wide transition shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-cyan-400/50 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full" />
                  <span>Calculating your targets...</span>
                </>
              ) : (
                <>
                  <span>Calculate My Targets &rarr;</span>
                </>
              )}
            </button>
          </div>

          {/* 6. Reassurance/footer text */}
          <div className="text-center pt-2">
            <p className="text-xs text-slate-500 flex items-center justify-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              <span>Your data is securely stored and used only to personalize your fitness plan.</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
