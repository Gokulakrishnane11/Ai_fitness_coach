"use client";

import "./globals.css";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dumbbell, Activity, TrendingUp, Compass, MessageSquareQuote, LogOut, Camera, User, Menu, X, ShieldCheck } from "lucide-react";
import { AuthProvider, useAuth } from "@/context/AuthContext";

function AuthNav({ onAction }: { onAction?: () => void }) {
  const { user, signOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  if (!user) return null;

  const handleSignOut = async () => {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await signOut();
      onAction?.();
    } catch (err) {
      console.error("Sign out error:", err);
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
      {/* System Status Indicator */}
      <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0b1020] border border-white/[0.08] text-[11px] font-mono text-slate-300">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-slate-400">Engine Active</span>
      </div>

      {/* User Indicator */}
      <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0b1020] border border-white/[0.08] text-[11px] font-mono text-slate-300 max-w-[150px] truncate">
        <User className="w-3 h-3 text-cyan-400 shrink-0" />
        <span className="truncate">{user.email}</span>
      </div>

      {/* Sign Out */}
      <button
        onClick={handleSignOut}
        disabled={signingOut}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-500/20 bg-rose-950/20 text-rose-300 hover:bg-rose-900/30 hover:border-rose-500/40 transition text-xs font-medium disabled:opacity-50"
      >
        <LogOut className="w-3.5 h-3.5 text-rose-400" />
        <span>{signingOut ? "Signing out..." : "Sign Out"}</span>
      </button>
    </div>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  const links = [
    { href: "/dashboard", label: "Dashboard", icon: Activity },
    { href: "/body-analysis", label: "Body Analysis", icon: Camera },
    { href: "/progress", label: "Progress", icon: TrendingUp },
    { href: "/simulation", label: "Simulation", icon: Compass },
    { href: "/coaching", label: "AI Coaching", icon: MessageSquareQuote },
    { href: "/onboarding", label: "Profile Setup", icon: User },
  ];

  return (
    <div className="flex flex-col md:flex-row md:items-center gap-1 sm:gap-1.5">
      {links.map(({ href, label, icon: Icon }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={`flex items-center gap-2 md:gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
              isActive
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/25"
                : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent"
            }`}
          >
            <Icon className={`w-3.5 h-3.5 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <html lang="en">
      <head>
        <title>FitEngine AI | Deterministic Physiological Platform</title>
        <meta
          name="description"
          content="Deterministic physiological fitness engine with structured AI coaching feedback."
        />
      </head>
      <body className="bg-[#070b12] text-slate-100 min-h-screen flex flex-col antialiased selection:bg-cyan-500/20 selection:text-cyan-300">
        <AuthProvider>
          {/* Navigation Header: Sticky, translucent, blurred, bordered, compact */}
          <header className="border-b border-white/[0.08] bg-[#070b12]/90 backdrop-blur-xl sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-4">
              <Link href="/dashboard" className="flex items-center gap-2.5 group shrink-0">
                <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 group-hover:bg-cyan-500/20 transition">
                  <Dumbbell className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base sm:text-lg tracking-tight text-white group-hover:text-cyan-300 transition">
                    FitEngine <span className="text-cyan-400 font-semibold">AI</span>
                  </span>
                </div>
              </Link>

              {/* Desktop Nav */}
              <nav className="hidden md:flex items-center gap-3">
                <NavLinks />
                <div className="h-4 w-px bg-white/[0.08]" />
                <AuthNav />
              </nav>

              {/* Mobile Menu Button */}
              <div className="flex md:hidden items-center gap-2">
                <AuthNav />
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  aria-label="Toggle navigation menu"
                  className="p-2 rounded-lg bg-[#0f1724] border border-white/[0.08] text-slate-300 hover:text-white"
                >
                  {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Mobile Dropdown Menu */}
            {mobileMenuOpen && (
              <div className="md:hidden border-t border-white/[0.08] bg-[#070b12]/95 backdrop-blur-2xl px-4 py-4 space-y-3 animate-in fade-in duration-150">
                <NavLinks onNavigate={() => setMobileMenuOpen(false)} />
              </div>
            )}
          </header>

          {/* Subheader Clinical & Thermodynamic Banner */}
          <div className="border-b border-white/[0.05] bg-[#0b1020]/60 py-1.5 px-4 text-center">
            <p className="text-[11px] font-mono text-cyan-400/80 tracking-wide flex items-center justify-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-cyan-400 inline" />
              <span>Physics Standard: Validated Mifflin-St Jeor thermodynamics & dynamic energy balance equations • Zero synthetic regression models.</span>
            </p>
          </div>

          {/* Main Content Viewport */}
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
            {children}
          </main>

          {/* Minimal Production Footer */}
          <footer className="border-t border-white/[0.08] bg-[#070b12] py-4 px-4 text-center text-xs text-slate-500">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Deterministic Engine v1.0 Online
              </span>
              <span>© 2026 FitEngine AI • Next.js + FastAPI + Supabase Decoupled Stack</span>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
