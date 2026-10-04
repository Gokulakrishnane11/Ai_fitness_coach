"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { submitJournal } from "@/lib/api";
import { MessageSquareQuote, Send, Sparkles, CheckCircle } from "lucide-react";

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
    return <div className="py-20 text-center text-gray-400">Loading AI coach session...</div>;
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
    <div className="max-w-3xl mx-auto space-y-8 py-2">
      <div className="space-y-3 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-500/30 text-purple-300 text-xs font-mono">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span>LLM Subjective Sentiment & Recovery Engine</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          AI Fitness Journal & <span className="gradient-text-purple">Coaching Feedback</span>
        </h1>
        <p className="text-sm text-gray-400 max-w-xl mx-auto leading-relaxed">
          Reflect on daily workout effort, perceived fatigue, and mindset. Structured AI feedback translates subjective sensations into recovery advice.
        </p>
      </div>

      {/* Journal Entry Form */}
      <form onSubmit={handleSubmitJournal} className="glass-card p-6 sm:p-7 space-y-5 border border-slate-800">
        <div className="space-y-2">
          <label className="text-xs text-gray-300 font-semibold tracking-wide uppercase flex items-center justify-between">
            <span>Daily Workout & Mindset Journal</span>
            <span className="text-[11px] text-gray-500 font-mono font-normal">Markdown supported</span>
          </label>
          <textarea
            value={entryText}
            onChange={(e) => setEntryText(e.target.value)}
            placeholder="e.g. Smashed my leg workout today! Hit a new personal record on squat at 100kg. Energy was high, but feeling slight soreness in the adductors. Sleep was 7 hours..."
            rows={5}
            className="w-full p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-sm text-gray-200 placeholder:text-gray-500 focus:border-purple-500/70 focus:outline-none focus:ring-1 focus:ring-purple-500/20 transition-all resize-none leading-relaxed"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading || !entryText.trim()}
          className="w-full py-3.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold flex items-center justify-center gap-2 shadow-sm transition-all disabled:opacity-50 text-sm cursor-pointer"
        >
          {loading ? (
            <>
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              <span>Analyzing Sentiment with AI Coach...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Submit Journal for AI Review</span>
            </>
          )}
        </button>
      </form>

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
              "{feedback.summary}"
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Actionable Recovery & Training Advice</h4>
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
              "{feedback.encouragement_quote}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}
