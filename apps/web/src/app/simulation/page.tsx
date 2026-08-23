"use client";

import { useState } from "react";
import { runSimulation, WeeklySeriesPoint } from "@/lib/api";
import { Compass, ShieldAlert, Play, TrendingDown } from "lucide-react";

export default function SimulationPage() {
  const [deficit, setDeficit] = useState(-500);
  const [adherence, setAdherence] = useState(85);
  const [weeks, setWeeks] = useState(12);
  const [loading, setLoading] = useState(false);
  const [series, setSeries] = useState<WeeklySeriesPoint[] | null>(null);
  const [timeline, setTimeline] = useState<any>(null);

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const res = await runSimulation("test_token_user_demo", {
        start_weight_kg: 80.0,
        target_weight_kg: 72.0,
        height_cm: 176.0,
        age: 24,
        gender: "male",
        activity_level: "moderately_active",
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
    <div className="space-y-8 py-4">
      <div className="space-y-2">
        <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3">
          <Compass className="w-8 h-8 text-cyan-400" />
          <span className="gradient-text-cyan">Predictive Transformation Simulation</span>
        </h1>
        <p className="text-sm text-gray-400">
          Simulate physics-based body weight trajectories with metabolic adaptation (BMR decay) and adherence controls.
        </p>
      </div>

      {/* Control Panel */}
      <div className="glass-card p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <label className="text-xs text-gray-300 font-semibold flex justify-between">
              <span>Daily Caloric Deficit / Surplus</span>
              <span className="text-cyan-400 font-mono font-bold">{deficit} kcal/day</span>
            </label>
            <input
              type="range"
              min={-1000}
              max={800}
              step={50}
              value={deficit}
              onChange={(e) => setDeficit(Number(e.target.value))}
              className="w-full accent-cyan-500"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs text-gray-300 font-semibold flex justify-between">
              <span>Diet & Plan Adherence</span>
              <span className="text-emerald-400 font-mono font-bold">{adherence}%</span>
            </label>
            <input
              type="range"
              min={50}
              max={100}
              step={5}
              value={adherence}
              onChange={(e) => setAdherence(Number(e.target.value))}
              className="w-full accent-emerald-500"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs text-gray-300 font-semibold flex justify-between">
              <span>Simulation Horizon</span>
              <span className="text-purple-400 font-mono font-bold">{weeks} Weeks</span>
            </label>
            <input
              type="range"
              min={4}
              max={52}
              step={4}
              value={weeks}
              onChange={(e) => setWeeks(Number(e.target.value))}
              className="w-full accent-purple-500"
            />
          </div>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={loading}
          className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold flex items-center justify-center gap-2 glow-btn transition"
        >
          <Play className="w-4 h-4 fill-current" />
          {loading ? "Running Physics Simulation..." : "Execute Transformation Simulation"}
        </button>
      </div>

      {/* Simulation Results Table */}
      {series && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-cyan-950/40 border border-cyan-900/50 flex items-center justify-between">
            <div>
              <span className="text-xs text-gray-400">Estimated Timeline to Goal (72.0 kg)</span>
              <p className="text-2xl font-bold text-cyan-400">{timeline?.estimated_weeks} Weeks</p>
            </div>
            <div className="text-right">
              <span className="text-xs text-gray-400">Weekly Weight Rate</span>
              <p className="text-2xl font-bold text-emerald-400">{timeline?.weekly_rate_kg} kg/week</p>
            </div>
          </div>

          <div className="glass-card overflow-hidden">
            <div className="p-4 border-b border-gray-800 font-semibold text-sm flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-cyan-400" /> Week-by-Week Trajectory Data
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-gray-900/80 text-gray-400 uppercase">
                  <tr>
                    <th className="p-3">Week</th>
                    <th className="p-3">Weight (kg)</th>
                    <th className="p-3">Fat Mass (kg)</th>
                    <th className="p-3">Lean Mass (kg)</th>
                    <th className="p-3">Body Fat %</th>
                    <th className="p-3">Dynamic BMR</th>
                    <th className="p-3">Effective TDEE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {series.map((pt) => (
                    <tr key={pt.week} className="hover:bg-gray-800/40">
                      <td className="p-3 font-bold text-cyan-400">Week {pt.week}</td>
                      <td className="p-3 font-bold text-white">{pt.weight_kg}</td>
                      <td className="p-3 text-red-400">{pt.fat_mass_kg}</td>
                      <td className="p-3 text-emerald-400">{pt.lean_mass_kg}</td>
                      <td className="p-3 text-purple-400">{pt.body_fat_pct}%</td>
                      <td className="p-3 text-gray-400">{pt.bmr} kcal</td>
                      <td className="p-3 text-gray-400">{pt.tdee} kcal</td>
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
