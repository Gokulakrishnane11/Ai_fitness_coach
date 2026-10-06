"use client";

import "./globals.css";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dumbbell, Activity, TrendingUp, Compass, MessageSquareQuote, ShieldAlert, LogOut, CheckCircle2, Camera } from "lucide-react";
import { AuthProvider, useAuth } from "@/context/AuthContext";

function AuthNav() {
  const { user, signOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  if (!user) return null;

  const handleSignOut = async () => {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await signOut();
    } catch (err) {
      console.error("Sign out error:", err);
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <button
      onClick={handleSignOut}
      disabled={signingOut}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/20 bg-red-950/30 text-red-300 hover:bg-red-900/50 hover:border-red-500/40 transition text-xs font-medium disabled:opacity-50"
    >
      <LogOut className="w-3.5 h-3.5 text-red-400" />
      <span>{signingOut ? "Signing out..." : "Sign Out"}</span>
    </button>
  );
}

function NavLinks() {
  const pathname = usePathname();

  const links = [
    { href: "/dashboard", label: "Dashboard", icon: Activity },
    { href: "/body-analysis", label: "Body Analysis", icon: Camera },
    { href: "/progress", label: "Progress", icon: TrendingUp },
    { href: "/simulation", label: "Simulation", icon: Compass },
    { href: "/coaching", label: "AI Coaching", icon: MessageSquareQuote },
  ];

  return (
    <div className="flex items-center gap-1.5 sm:gap-2">
      {links.map(({ href, label, icon: Icon }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
              isActive
                ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/40 border border-transparent"
            }`}
          >
            <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-gray-400"}`} />
            <span>{label}</span>
          </Link>
        );
      })}
    </div>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isOnboarding = pathname === "/onboarding";

  return (
    <html lang="en">
      <head>
        <title>FitEngine AI | Deterministic Physiological Platform</title>
        <meta
          name="description"
          content="Deterministic physiological fitness engine with structured AI coaching feedback."
        />
      </head>
      <body className="bg-[#090d16] text-gray-100 min-h-screen flex flex-col antialiased selection:bg-cyan-500/20 selection:text-cyan-300">
        <AuthProvider>
          {/* Navigation Header */}
          <header className="border-b border-gray-800/80 bg-[#090d16]/85 backdrop-blur-xl sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
              <Link href="/dashboard" className="flex items-center gap-2.5 group shrink-0">
                <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 group-hover:bg-cyan-500/20 transition">
                  <Dumbbell className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base sm:text-lg tracking-tight text-white group-hover:text-cyan-300 transition">
                    FitEngine<span className="text-cyan-400 font-mono font-semibold">.ai</span>
                  </span>
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                    V1
                  </span>
                </div>
              </Link>

              <nav className="flex items-center gap-2 sm:gap-4 overflow-x-auto py-1">
                <NavLinks />
                <div className="h-4 w-px bg-gray-800 hidden sm:block" />
                <Link
                  href="/onboarding"
                  className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-all shrink-0 ${
                    isOnboarding
                      ? "bg-cyan-600 text-white shadow-sm"
                      : "bg-gray-800/80 hover:bg-gray-700/80 border border-gray-700 text-gray-200"
                  }`}
                >
                  Profile Setup
                </Link>
                <AuthNav />
              </nav>
            </div>
          </header>

          {/* Methodology Standards Banner */}
          <div className="bg-slate-950/70 border-b border-gray-800/60 py-1.5 px-4 text-center text-[11px] text-gray-400 flex items-center justify-center gap-2 font-mono">
            <ShieldAlert className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="truncate">
              Physics Standard: Validated Mifflin-St Jeor thermodynamics & dynamic energy balance equations • Zero synthetic regression models.
            </span>
          </div>

          {/* Main Page Content */}
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">{children}</main>

          {/* Footer */}
          <footer className="border-t border-gray-800/80 py-6 text-center text-xs text-gray-500 bg-[#090d16]">
            <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-gray-400 font-mono text-[11px]">Thermodynamic Engine v1.0 Online</span>
              </div>
              <p>© 2026 FitEngine V1 Rebuild • Next.js + FastAPI + Supabase Decoupled Stack</p>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
