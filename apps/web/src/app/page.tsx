import Link from "next/link";
import { Activity, Compass, MessageSquareQuote, ShieldCheck, ArrowRight } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-12 py-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 max-w-3xl mx-auto">
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight">
          Precision Fitness Engine <br />
          <span className="gradient-text-cyan">Built on Real Human Thermodynamics</span>
        </h1>
        <p className="text-gray-400 text-lg">
          Decoupled, high-performance architecture. Grounded in clinical energy-balance math, dynamic BMR decay, and structured AI coaching feedback.
        </p>
        <div className="pt-4 flex items-center justify-center gap-4">
          <Link
            href="/onboarding"
            className="px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold flex items-center gap-2 glow-btn transition"
          >
            Start Biometric Profile <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl glass-card hover:bg-gray-800/60 text-gray-200 font-semibold transition"
          >
            View Dashboard
          </Link>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
        <div className="glass-card p-6 space-y-3 border-t-2 border-t-cyan-500">
          <div className="p-3 rounded-lg bg-cyan-500/10 text-cyan-400 w-fit">
            <Activity className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold">Deterministic Calculation Engine</h3>
          <p className="text-sm text-gray-400 leading-relaxed">
            BMI, Mifflin-St Jeor BMR, Katch-McArdle, TDEE, and macro splits computed with strict biological floors. Zero guess work.
          </p>
        </div>

        <div className="glass-card p-6 space-y-3 border-t-2 border-t-emerald-500">
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400 w-fit">
            <Compass className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold">Physics-Based Simulation</h3>
          <p className="text-sm text-gray-400 leading-relaxed">
            Multi-week weight, fat mass, and lean body mass projection incorporating adaptive thermogenesis BMR decay.
          </p>
        </div>

        <div className="glass-card p-6 space-y-3 border-t-2 border-t-purple-500">
          <div className="p-3 rounded-lg bg-purple-500/10 text-purple-400 w-fit">
            <MessageSquareQuote className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold">Structured AI Coaching</h3>
          <p className="text-sm text-gray-400 leading-relaxed">
            Groq/NVIDIA LLM parsing of journal entries into structured sentiment, actionable recovery tips, and progress analysis.
          </p>
        </div>
      </div>
    </div>
  );
}
