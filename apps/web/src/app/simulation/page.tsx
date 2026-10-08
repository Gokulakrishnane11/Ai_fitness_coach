"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { runSimulation, WeeklySeriesPoint, fetchProfile, UserProfile } from "@/lib/api";
import { Compass, ShieldAlert, Play, TrendingDown } from "lucide-react";

export default function SimulationPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [deficit, setDeficit] = useState(-500);
  const [adherence, setAdherence] = useState(85);
  const [weeks, setWeeks] = useState(12);
  const [loading, setLoading] = useState(false);
  const [series, setSeries] = useState<WeeklySeriesPoint[] | null>(null);
  const [timeline, setTimeline] = useState<any>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (user) {
      fetchProfile().then(setProfile).catch(() => {});
    }
  }, [user]);

  if (authLoading) {
    return <div className="py-20 text-center text-gray-400">Loading simulation engine...</div>;
  }

  if (!user) {
    return null;
  }

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const res = await runSimulation({
        start_weight_kg: profile?.weight_kg || 80.0,
        target_weight_kg: profile?.target_weight_kg || 72.0,
        height_cm: profile?.height_cm || 176.0,
        age: profile?.age || 24,
        gender: profile?.gender || "male",
        activity_level: profile?.activity_level || "moderately_active",
        daily_caloric_deficit_surplus: deficit,
        adherence_pct: adherence,
        duration_weeks: weeks,
      });
      setSeries(res.weekly_series);
      setTimeline(res.timeline_summary);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 py-2 max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="glass-card p-6 sm:p-8 border border-slate-800/80 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-72 h-72 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 mb-2">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          Metabolic Trajectory Model
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
          <span className="gradient-text-cyan">Predictive Transformation Simulation</span>
        </h1>
        <p className="text-sm text-gray-400 max-w-2xl mt-1">
          Simulate physics-based body weight trajectories with metabolic adaptation (BMR decay) and adherence controls.
        </p>
      </div>

      {/* Control Panel */}
      <div className="glass-card p-6 sm:p-8 space-y-6 border border-slate-800/80">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 rounded-xl bg-[#0c1322]/80 border border-white/5 space-y-2.5">
            <label className="text-xs text-gray-300 font-semibold flex justify-between items-center">
              <span>Daily Caloric Delta</span>
              <span className="text-cyan-400 font-mono font-bold px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40">{deficit} kcal/day</span>
            </label>
            <input
              type="range"
              min={-1000}
              max={800}
              step={50}
              value={deficit}
              onChange={(e) => setDeficit(Number(e.target.value))}
              className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>

          <div className="p-4 rounded-xl bg-[#0c1322]/80 border border-white/5 space-y-2.5">
            <label className="text-xs text-gray-300 font-semibold flex justify-between items-center">
              <span>Diet & Plan Adherence</span>
              <span className="text-emerald-400 font-mono font-bold px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/40">{adherence}%</span>
            </label>
            <input
              type="range"
              min={50}
              max={100}
              step={5}
              value={adherence}
              onChange={(e) => setAdherence(Number(e.target.value))}
              className="w-full accent-emerald-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>

          <div className="p-4 rounded-xl bg-[#0c1322]/80 border border-white/5 space-y-2.5">
            <label className="text-xs text-gray-300 font-semibold flex justify-between items-center">
              <span>Simulation Horizon</span>
              <span className="text-purple-400 font-mono font-bold px-2 py-0.5 rounded bg-purple-950/60 border border-purple-800/40">{weeks} Weeks</span>
            </label>
            <input
              type="range"
              min={4}
              max={52}
              step={4}
              value={weeks}
              onChange={(e) => setWeeks(Number(e.target.value))}
              className="w-full accent-purple-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={loading}
          className="btn-primary w-full py-3.5 text-sm font-bold tracking-wide"
        >
          {loading ? (
            <>
              <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full" />
              <span>Running Physics Simulation...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Execute Transformation Simulation</span>
            </>
          )}
        </button>
      </div>

      {/* Current, Target, and Projected Milestone Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-card p-5 space-y-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Current Weight</span>
          <p className="text-2xl font-bold font-mono text-white">
            {profile?.weight_kg ?? 78} <span className="text-xs text-slate-500 font-normal">kg</span>
          </p>
          <span className="text-[11px] text-slate-500 block">Profile baseline</span>
        </div>

        <div className="glass-card p-5 space-y-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Target Weight</span>
          <p className="text-2xl font-bold font-mono text-emerald-400">
            {profile?.target_weight_kg ?? 72} <span className="text-xs text-slate-500 font-normal">kg</span>
          </p>
          <span className="text-[11px] text-slate-500 block">Goal objective</span>
        </div>

        <div className="glass-card p-5 space-y-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Projected Weight</span>
          <p className="text-2xl font-bold font-mono text-cyan-400">
            {series && series.length > 0 ? `${series[series.length - 1].weight_kg} kg` : "Run to calculate"}
          </p>
          <span className="text-[11px] text-slate-500 block">At horizon end ({weeks} wks)</span>
        </div>
      </div>

      {/* Simulation Results Table */}
      {series && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-[#0b1020] border border-cyan-500/25 flex items-center justify-between shadow-sm">
            <div>
              <span className="text-xs text-slate-400 font-medium">Estimated Timeline to Goal</span>
              <p className="text-2xl sm:text-3xl font-bold font-mono text-cyan-400">{timeline?.estimated_weeks} <span className="text-sm font-sans text-slate-400 font-normal">Weeks</span></p>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 font-medium">Weekly Weight Rate</span>
              <p className="text-2xl sm:text-3xl font-bold font-mono text-emerald-400">{timeline?.weekly_rate_kg} <span className="text-sm font-sans text-slate-400 font-normal">kg/week</span></p>
            </div>
          </div>

          <div className="glass-card overflow-hidden border border-slate-800/80">
            <div className="p-4 border-b border-gray-800/80 font-semibold text-sm flex items-center gap-2 text-gray-100">
              <TrendingDown className="w-4 h-4 text-cyan-400" /> Week-by-Week Trajectory Data
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/90 text-gray-400 uppercase text-[11px]">
                  <tr>
                    <th className="p-3.5">Week</th>
                    <th className="p-3.5">Weight (kg)</th>
                    <th className="p-3.5">Fat Mass (kg)</th>
                    <th className="p-3.5">Lean Mass (kg)</th>
                    <th className="p-3.5">Body Fat %</th>
                    <th className="p-3.5">Dynamic BMR</th>
                    <th className="p-3.5">Effective TDEE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 bg-slate-950/40">
                  {series.map((pt) => (
                    <tr key={pt.week} className="hover:bg-cyan-500/5 transition-colors">
                      <td className="p-3.5 font-bold text-cyan-400">Week {pt.week}</td>
                      <td className="p-3.5 font-bold text-white">{pt.weight_kg}</td>
                      <td className="p-3.5 text-red-400">{pt.fat_mass_kg}</td>
                      <td className="p-3.5 text-emerald-400">{pt.lean_mass_kg}</td>
                      <td className="p-3.5 text-purple-400">{pt.body_fat_pct}%</td>
                      <td className="p-3.5 text-gray-400">{pt.bmr} kcal</td>
                      <td className="p-3.5 text-gray-400">{pt.tdee} kcal</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
