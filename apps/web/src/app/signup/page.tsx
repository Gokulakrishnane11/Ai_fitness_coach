"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Mail, Lock, UserPlus, AlertCircle, CheckCircle2 } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmationRequired, setConfirmationRequired] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setErrorMessage("Email is required.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setErrorMessage("Password is required.");
      return;
    }

    if (password.length < 6) {
      setErrorMessage("Password must be at least 6 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const supabase = createClient();
      const { data, error } = await supabase.auth.signUp({
        email: trimmedEmail,
        password,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      if (data?.session) {
        // Immediate active session returned (email confirmation disabled in Supabase)
        router.push("/onboarding");
      } else if (data?.user && !data.session) {
        // User created, confirmation email sent
        setConfirmationRequired(true);
      } else {
        setErrorMessage("Signup could not be completed. Please try again.");
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "An unexpected error occurred during signup.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-8 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-extrabold gradient-text-cyan">Create Your Account</h1>
        <p className="text-sm text-gray-400">
          Start your transformation journey with the science-grounded FitEngine platform.
        </p>
      </div>

      {confirmationRequired ? (
        <div className="glass-card p-6 space-y-4 border-t-2 border-t-emerald-500 text-center">
          <div className="p-3 rounded-full bg-emerald-500/10 text-emerald-400 w-fit mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-gray-100">Check Your Email</h2>
          <p className="text-sm text-gray-300 leading-relaxed">
            We sent a verification link to <span className="font-semibold text-cyan-400">{email}</span>.
            Please open the link to confirm your account and get started.
          </p>
          <div className="pt-2">
            <Link
              href="/login"
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold transition"
            >
              Already verified? Proceed to Login &rarr;
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="glass-card p-6 space-y-5">
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-500/40 text-red-300 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5 text-cyan-400" /> Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none transition"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-cyan-400" /> Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              className="w-full p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none transition"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-cyan-400" /> Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              className="w-full p-2.5 rounded-lg bg-gray-900 border border-gray-800 text-sm focus:border-cyan-500 focus:outline-none transition"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold flex items-center justify-center gap-2 glow-btn transition disabled:opacity-50"
          >
            <UserPlus className="w-4 h-4" />
            {loading ? "Creating Account..." : "Create Account"}
          </button>

          <div className="text-center pt-2 text-xs text-gray-400">
            Already have an account?{" "}
            <Link href="/login" className="text-cyan-400 hover:text-cyan-300 font-semibold transition">
              Log In
            </Link>
          </div>
        </form>
      )}
    </div>
  );
}
