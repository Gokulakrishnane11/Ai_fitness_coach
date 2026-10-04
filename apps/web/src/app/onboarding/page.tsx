"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { saveProfile, UserProfile } from "@/lib/api";
import { User, Activity, Flame, Utensils, CheckCircle2 } from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
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

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  if (authLoading) {
    return <div className="py-20 text-center text-gray-400">Loading onboarding...</div>;
  }

  if (!user) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await saveProfile(formData);
      setSaved(true);
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-4">
      {/* Header */}
      <div className="glass-card p-6 sm:p-8 border border-slate-800/80 relative overflow-hidden text-center space-y-2">
        <div className="absolute top-0 right-1/2 translate-x-1/2 -mt-12 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 mx-auto">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          Physiological Initialization
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white">
          <span className="gradient-text-cyan">Biometric Onboarding Wizard</span>
        </h1>
        <p className="text-sm text-gray-400 max-w-lg mx-auto">
          Configure your physical stats and fitness goals to activate your physiological calculation engine and deterministic planning models.
        </p>
      </div>

      {saved && (
        <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 flex items-center gap-3 shadow-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="text-sm font-medium">Profile saved successfully! Computing physiological targets and redirecting...</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="glass-card p-6 sm:p-8 space-y-6 border border-slate-800/80">
        {/* Basic Info */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-800/80 pb-3">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <User className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-gray-100 uppercase tracking-wider">
              Personal Biometrics
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">First Name</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Gender</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value as any })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Age</label>
              <input
                type="number"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
                min={13}
                max={100}
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Height (cm)</label>
              <input
                type="number"
                value={formData.height_cm}
                onChange={(e) => setFormData({ ...formData, height_cm: Number(e.target.value) })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
                min={100}
                max={250}
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Current Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={formData.weight_kg}
                onChange={(e) => setFormData({ ...formData, weight_kg: Number(e.target.value) })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Target Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={formData.target_weight_kg}
                onChange={(e) => setFormData({ ...formData, target_weight_kg: Number(e.target.value) })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
                required
              />
            </div>
          </div>
        </div>

        {/* Goal & Preferences */}
        <div className="space-y-4 border-t border-gray-800/80 pt-5">
          <div className="flex items-center gap-2 border-b border-gray-800/80 pb-3">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Flame className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-gray-100 uppercase tracking-wider">
              Fitness Goal & Activity Level
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Primary Goal</label>
              <select
                value={formData.goal_type}
                onChange={(e) => setFormData({ ...formData, goal_type: e.target.value as any })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
              >
                <option value="fat_loss">Fat Loss (-20% Deficit)</option>
                <option value="muscle_gain">Muscle Gain (+10% Surplus)</option>
                <option value="weight_gain">Weight Gain (+15% Surplus)</option>
                <option value="recomposition">Body Recomposition (Maintenance)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Daily Activity Level</label>
              <select
                value={formData.activity_level}
                onChange={(e) => setFormData({ ...formData, activity_level: e.target.value as any })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
              >
                <option value="sedentary">Sedentary (Office desk job)</option>
                <option value="lightly_active">Lightly Active (1-3 days exercise)</option>
                <option value="moderately_active">Moderately Active (3-5 days exercise)</option>
                <option value="very_active">Very Active (6-7 days heavy exercise)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Dietary Preference</label>
              <select
                value={formData.dietary_preference}
                onChange={(e) => setFormData({ ...formData, dietary_preference: e.target.value as any })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
              >
                <option value="anything">Anything (No Restriction)</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="keto">Keto (Low Carb)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">Workout Days / Week</label>
              <input
                type="number"
                value={formData.workout_days_per_week}
                onChange={(e) => setFormData({ ...formData, workout_days_per_week: Number(e.target.value) })}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition"
                min={1}
                max={7}
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold glow-btn transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              <span>Processing Profile...</span>
            </>
          ) : (
            "Save Profile & Compute Targets"
          )}
        </button>
      </form>
    </div>
  );
}
