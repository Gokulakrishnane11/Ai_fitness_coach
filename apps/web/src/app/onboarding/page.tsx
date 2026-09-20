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
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-extrabold gradient-text-cyan">Biometric Onboarding Wizard</h1>
        <p className="text-sm text-gray-400">
          Configure your physical stats and fitness goals to activate your physiological calculation engine.
        </p>
      </div>

      {saved && (
        <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          <span>Profile saved successfully! Computing physiological targets and redirecting...</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="glass-card p-6 space-y-6">
        {/* Basic Info */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <User className="w-4 h-4" /> Personal Biometrics
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-300">First Name</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300">Gender</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value as any })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-300">Age</label>
              <input
                type="number"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
                min={13}
                max={100}
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300">Height (cm)</label>
              <input
                type="number"
                value={formData.height_cm}
                onChange={(e) => setFormData({ ...formData, height_cm: Number(e.target.value) })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
                min={100}
                max={250}
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300">Current Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={formData.weight_kg}
                onChange={(e) => setFormData({ ...formData, weight_kg: Number(e.target.value) })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300">Target Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={formData.target_weight_kg}
                onChange={(e) => setFormData({ ...formData, target_weight_kg: Number(e.target.value) })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
                required
              />
            </div>
          </div>
        </div>

        {/* Goal & Preferences */}
        <div className="space-y-4 border-t border-gray-800 pt-4">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <Flame className="w-4 h-4" /> Fitness Goal & Activity Level
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-300">Primary Goal</label>
              <select
                value={formData.goal_type}
                onChange={(e) => setFormData({ ...formData, goal_type: e.target.value as any })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
              >
                <option value="fat_loss">Fat Loss (-20% Deficit)</option>
                <option value="muscle_gain">Muscle Gain (+10% Surplus)</option>
                <option value="weight_gain">Weight Gain (+15% Surplus)</option>
                <option value="recomposition">Body Recomposition (Maintenance)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-300">Daily Activity Level</label>
              <select
                value={formData.activity_level}
                onChange={(e) => setFormData({ ...formData, activity_level: e.target.value as any })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
              >
                <option value="sedentary">Sedentary (Office desk job)</option>
                <option value="lightly_active">Lightly Active (1-3 days exercise)</option>
                <option value="moderately_active">Moderately Active (3-5 days exercise)</option>
                <option value="very_active">Very Active (6-7 days heavy exercise)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-300">Dietary Preference</label>
              <select
                value={formData.dietary_preference}
                onChange={(e) => setFormData({ ...formData, dietary_preference: e.target.value as any })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
              >
                <option value="anything">Anything (No Restriction)</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="keto">Keto (Low Carb)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-300">Workout Days / Week</label>
              <input
                type="number"
                value={formData.workout_days_per_week}
                onChange={(e) => setFormData({ ...formData, workout_days_per_week: Number(e.target.value) })}
                className="w-full mt-1 p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none"
                min={1}
                max={7}
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold glow-btn transition disabled:opacity-50"
        >
          {loading ? "Processing Profile..." : "Save Profile & Compute Targets"}
        </button>
      </form>
    </div>
  );
}
