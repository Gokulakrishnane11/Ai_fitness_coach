"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { submitJournal } from "@/lib/api";
import { MessageSquareQuote, Send, Sparkles, CheckCircle } from "lucide-react";

const QUICK_PROMPTS = [
  "Workout felt difficult",
  "Feeling low energy",
  "Great recovery today",
  "Struggled with nutrition",
];

export default function CoachingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [entryText, setEntryText] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<any>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  if (authLoading) {
    return <div className="py-20 text-center text-slate-400">Loading AI coach session...</div>;
  }

  if (!user) {
    return null;
  }

  const handleSubmitJournal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entryText.trim()) return;
    setLoading(true);
    try {
      const res = await submitJournal(entryText);
      setFeedback(res.feedback);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-2">
      {/* Header Banner */}
      <div className="glass-card p-6 sm:p-8 border border-white/[0.08] relative overflow-hidden">
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-cyan-950/60 border border-cyan-500/25 text-cyan-300">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Adaptive Intelligence
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            AI Coach
          </h1>
          <p className="text-sm text-slate-400 max-w-xl leading-relaxed">
            Your training and nutrition companion.
          </p>
        </div>
      </div>

      {/* Journal Input & Chat Reflection Interface */}
      <div className="glass-card p-6 sm:p-7 space-y-5 border border-white/[0.08]">
        <div className="space-y-3">
          <label className="text-xs text-slate-300 font-semibold tracking-wide uppercase flex items-center justify-between">
            <span>Daily Workout & Mindset Reflection</span>
            <span className="text-[11px] text-slate-500 font-mono font-normal">Markdown supported</span>
          </label>

          {/* Quick Prompts */}
          <div className="space-y-1.5">
            <span className="text-[10px] text-slate-500 uppercase font-mono tracking-wider block">
              Quick prompts:
            </span>
            <div className="flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setEntryText(prompt)}
                  className="text-xs px-3 py-1.5 rounded-lg bg-[#0b1020] border border-white/[0.08] hover:border-cyan-500/40 text-slate-300 hover:text-white transition-all text-left"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmitJournal} className="space-y-4 pt-2">
            <textarea
              value={entryText}
              onChange={(e) => setEntryText(e.target.value)}
              placeholder="How did your day go? Reflect on workout effort, fatigue, nutrition discipline, or mental state..."
              rows={5}
              className="w-full p-4 rounded-xl bg-[#0b1020] border border-white/[0.08] text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500/70 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition-all resize-none leading-relaxed"
              required
            />

            <button
              type="submit"
              disabled={loading || !entryText.trim()}
              className="w-full py-3.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold flex items-center justify-center gap-2 shadow-sm transition-all disabled:opacity-50 text-sm cursor-pointer"
            >
              {loading ? (
                <>
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  <span>Analyzing Reflection with AI Coach...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Analyze Reflection & Get Recommendations</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* AI Feedback Cards */}
      {feedback && (
        <div className="glass-card p-6 sm:p-7 space-y-6 border-t-4 border-t-purple-500 border border-slate-800 shadow-sm animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800/80 pb-4">
            <h3 className="font-bold text-lg text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" /> AI Coach Assessment
            </h3>
            <span className="px-3 py-1 rounded-full bg-purple-950/80 text-purple-300 border border-purple-800/60 text-xs font-mono capitalize font-semibold w-fit">
              Sentiment: {feedback.sentiment_tag}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-purple-300 font-semibold block">Coach Summary</span>
            <p className="text-sm text-gray-200 italic leading-relaxed">
              &ldquo;{feedback.summary}&rdquo;
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Recommendations</h4>
            <div className="space-y-2">
              {feedback.actionable_tips?.map((tip: string, idx: number) => (
                <div key={idx} className="flex items-start gap-3 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-sm text-gray-200 leading-relaxed">
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          </div>

          {feedback.encouragement_quote && (
            <div className="p-4 rounded-xl bg-cyan-950/25 border border-cyan-800/40 text-center text-xs text-cyan-300 font-medium italic">
              &ldquo;{feedback.encouragement_quote}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  );
}
