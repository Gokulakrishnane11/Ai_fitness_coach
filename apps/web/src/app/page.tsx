import Link from "next/link";
import { Activity, Compass, MessageSquareQuote, ShieldCheck, ArrowRight } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-12 py-6 max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="glass-card p-8 sm:p-12 border border-slate-800/80 relative overflow-hidden text-center space-y-6">
        <div className="absolute top-0 right-1/2 translate-x-1/2 -mt-16 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="space-y-4 max-w-3xl mx-auto relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 mx-auto">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            Clinical Human Thermodynamics · Multi-Signal AI
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Precision Fitness Platform <br />
            <span className="gradient-text-cyan">Built on Energy-Balance Science</span>
          </h1>

          <p className="text-gray-400 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
            High-performance architecture grounded in clinically calibrated Mifflin-St Jeor math, adaptive BMR decay, and multi-signal AI physiological coaching.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/onboarding"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold flex items-center justify-center gap-2 glow-btn transition shadow-sm"
            >
              Start Biometric Profile <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-gray-200 font-semibold transition text-center"
            >
              View Active Dashboard
            </Link>
          </div>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 sm:p-8 space-y-4 border border-slate-800/80 hover:border-cyan-500/40 transition-all shadow-sm">
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 w-fit">
            <Activity className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white">Deterministic Engine</h3>
          <p className="text-sm text-gray-400 leading-relaxed">
            BMI, Mifflin-St Jeor BMR, Katch-McArdle, TDEE, and macro splits computed with strict biological floors. Zero guesswork.
          </p>
        </div>

        <div className="glass-card p-6 sm:p-8 space-y-4 border border-slate-800/80 hover:border-emerald-500/40 transition-all shadow-sm">
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 w-fit">
            <Compass className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white">Physics-Based Simulation</h3>
          <p className="text-sm text-gray-400 leading-relaxed">
            Multi-week weight, fat mass, and lean body mass projection incorporating adaptive thermogenesis BMR decay.
          </p>
        </div>

        <div className="glass-card p-6 sm:p-8 space-y-4 border border-slate-800/80 hover:border-purple-500/40 transition-all shadow-sm">
          <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 w-fit">
            <MessageSquareQuote className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white">Structured AI Coaching</h3>
          <p className="text-sm text-gray-400 leading-relaxed">
            LLM parsing of journal entries into structured sentiment, actionable recovery tips, and progress analysis.
          </p>
        </div>
      </div>
    </div>
  );
}
