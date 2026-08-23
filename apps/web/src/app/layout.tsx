import "./globals.css";
import Link from "next/link";
import { Dumbbell, Activity, Compass, MessageSquareQuote, ShieldAlert } from "lucide-react";

export const metadata = {
  title: "AI Fitness Platform | Ground-Up Rebuild V1",
  description: "Deterministic physiological fitness engine with structured AI coaching feedback.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#0b0f19] text-gray-100 min-h-screen flex flex-col">
        {/* Navigation Header */}
        <header className="border-b border-gray-800 bg-[#0f172a]/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link href="/dashboard" className="flex items-center gap-3 group">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 group-hover:bg-cyan-500/20 transition">
                <Dumbbell className="w-5 h-5" />
              </div>
              <span className="font-bold text-lg tracking-wide gradient-text-cyan">
                FitEngine AI <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">V1</span>
              </span>
            </Link>

            <nav className="flex items-center gap-6 text-sm font-medium">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 text-gray-300 hover:text-cyan-400 transition"
              >
                <Activity className="w-4 h-4" /> Dashboard
              </Link>
              <Link
                href="/simulation"
                className="flex items-center gap-2 text-gray-300 hover:text-cyan-400 transition"
              >
                <Compass className="w-4 h-4" /> Simulation
              </Link>
              <Link
                href="/coaching"
                className="flex items-center gap-2 text-gray-300 hover:text-cyan-400 transition"
              >
                <MessageSquareQuote className="w-4 h-4" /> AI Coaching
              </Link>
              <Link
                href="/onboarding"
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium glow-btn transition"
              >
                Profile Setup
              </Link>
            </nav>
          </div>
        </header>

        {/* Methodology Standards Banner */}
        <div className="bg-cyan-950/40 border-b border-cyan-900/40 py-1.5 px-6 text-center text-xs text-cyan-300 flex items-center justify-center gap-2 font-mono">
          <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
          <span>V1 Engine Standard: Projections derived from validated Mifflin-St Jeor thermodynamics & dynamic energy balance equations. Zero synthetic ML models.</span>
        </div>

        {/* Main Page Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-6">{children}</main>

        {/* Footer */}
        <footer className="border-t border-gray-800 py-6 text-center text-xs text-gray-500">
          <p>© 2026 FitEngine V1 Architecture Rebuild. Ground-Up Decoupled Stack (Next.js + FastAPI + Supabase).</p>
        </footer>
      </body>
    </html>
  );
}
