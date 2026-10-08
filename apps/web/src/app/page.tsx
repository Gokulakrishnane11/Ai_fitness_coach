import Link from "next/link";
import {
  Activity,
  Compass,
  MessageSquareQuote,
  Camera,
  TrendingUp,
  Dumbbell,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Zap,
  CheckCircle2,
} from "lucide-react";

export default function Home() {
  const features = [
    {
      title: "AI Planning",
      badge: "Mifflin-St Jeor Engine",
      description:
        "Deterministic energy-balance thermodynamics and macronutrient partition modeling with strict biological safety floors. Zero synthetic guesswork.",
      icon: Dumbbell,
      accent: "cyan",
    },
    {
      title: "Body Analysis",
      badge: "MediaPipe Vision",
      description:
        "Computer-vision posture and anatomical landmark tracking. Observe bilateral symmetry and physical transformation with privacy-first EXIF stripping.",
      icon: Camera,
      accent: "emerald",
    },
    {
      title: "Adaptive Coaching",
      badge: "Multi-Signal Intelligence",
      description:
        "Dynamic physiological adjustment engine that scales caloric intake and workout volume based on sleep, fatigue, stress, and compliance.",
      icon: Sparkles,
      accent: "purple",
    },
    {
      title: "Progress Tracking",
      badge: "Kinetic Telemetry",
      description:
        "Holistic biometric telemetry tracking weight trajectories, neuromuscular fatigue state, and recovery kinetics across daily logs.",
      icon: TrendingUp,
      accent: "blue",
    },
  ];

  return (
    <div className="space-y-16 py-6 sm:py-10 max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="glass-card p-8 sm:p-14 lg:p-16 border border-white/[0.08] relative overflow-hidden text-center space-y-8">
        <div className="absolute top-0 right-1/2 translate-x-1/2 -mt-20 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="space-y-6 max-w-3xl mx-auto relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 mx-auto">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span>FitEngine AI • Production Precision Platform</span>
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.1]">
            Your body. <br />
            <span className="text-cyan-400">Your data.</span> <br />
            Your AI coach.
          </h1>

          <p className="text-slate-300 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
            FitEngine replaces arbitrary fitness routines with validated thermodynamic modeling, computer-vision body tracking, and multi-signal physiological adaptation.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/onboarding"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
            >
              <span>Start Your Fitness Journey</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#0b1020] hover:bg-slate-800/80 border border-white/[0.08] hover:border-white/[0.2] text-white font-semibold text-sm transition text-center"
            >
              Explore the Platform
            </Link>
          </div>
        </div>

        {/* Reassurance Metrics */}
        <div className="pt-8 border-t border-white/[0.06] grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto text-left">
          <div className="space-y-1">
            <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block">Engine Core</span>
            <span className="text-sm font-bold text-white flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" /> Mifflin-St Jeor
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block">Computer Vision</span>
            <span className="text-sm font-bold text-white flex items-center gap-1.5">
              <Camera className="w-4 h-4 text-emerald-400" /> 33 Landmarks
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block">Adaptation</span>
            <span className="text-sm font-bold text-white flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-purple-400" /> Multi-Signal
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block">Data Privacy</span>
            <span className="text-sm font-bold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-blue-400" /> EXIF Stripped
            </span>
          </div>
        </div>
      </div>

      {/* 4 Feature Cards Grid */}
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">
            Engine Architecture
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Built for Serious Athletic Progression
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
            Every recommendation is calculated from deterministic mathematical models and physiological signals.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div
                key={i}
                className="glass-card p-6 sm:p-8 space-y-4 border border-white/[0.08] hover:border-cyan-500/40 transition-all shadow-sm group"
              >
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 group-hover:scale-105 transition-transform">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[#0b1020] border border-white/[0.08] text-slate-300">
                    {f.badge}
                  </span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">{f.title}</h3>
                  <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                    {f.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Call to Action Bar */}
      <div className="p-8 sm:p-10 rounded-2xl bg-gradient-to-r from-cyan-950/40 via-[#0b1020] to-[#070b12] border border-cyan-500/30 flex flex-col sm:flex-row items-center justify-between gap-6 text-center sm:text-left">
        <div className="space-y-1">
          <h3 className="text-xl font-bold text-white">Ready to calibrate your physical baseline?</h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Set up your profile in under two minutes with zero arbitrary guesswork.
          </p>
        </div>
        <Link
          href="/onboarding"
          className="px-6 py-3.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm tracking-wide transition shrink-0 flex items-center gap-2"
        >
          <span>Start Now</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
