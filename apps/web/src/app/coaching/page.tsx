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
    <div className="max-w-3xl mx-auto space-y-8 py-4">
      <div className="space-y-2 text-center">
        <h1 className="text-3xl font-extrabold tracking-tight flex items-center justify-center gap-3">
          <MessageSquareQuote className="w-8 h-8 text-purple-400" />
          <span className="gradient-text-cyan">AI Fitness Journal & Coaching Feedback</span>
        </h1>
        <p className="text-sm text-gray-400">
          Reflect on your daily workouts, fatigue, energy levels, and mood. Groq / NVIDIA LLM analyzes your sentiment and generates structured recovery tips.
        </p>
      </div>

      {/* Journal Entry Form */}
      <form onSubmit={handleSubmitJournal} className="glass-card p-6 space-y-4">
        <div>
          <label className="text-xs text-gray-300 font-semibold mb-2 block">
            Daily Workout & Mindset Journal Entry
          </label>
          <textarea
            value={entryText}
            onChange={(e) => setEntryText(e.target.value)}
            placeholder="e.g. Smashed my leg workout today! Hit a new personal record on squat. Feeling high energy, but slightly sore in the quads..."
            rows={4}
            className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-sm focus:border-purple-500 focus:outline-none resize-none"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading || !entryText.trim()}
          className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold flex items-center justify-center gap-2 glow-btn transition disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          {loading ? "Analyzing Sentiment with AI..." : "Submit Journal for AI Review"}
        </button>
      </form>

      {/* AI Feedback Cards */}
      {feedback && (
        <div className="glass-card p-6 space-y-6 border-t-4 border-t-purple-500">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" /> AI Coach Analysis
            </h3>
            <span className="px-3 py-1 rounded-full bg-purple-950 text-purple-300 border border-purple-800 text-xs font-mono capitalize font-semibold">
              Detected Sentiment: {feedback.sentiment_tag}
            </span>
          </div>

          <p className="text-sm text-gray-300 italic bg-gray-900/60 p-4 rounded-xl border border-gray-800">
            "{feedback.summary}"
          </p>

          <div className="space-y-3">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Actionable Recovery & Training Advice</h4>
            <div className="space-y-2">
              {feedback.actionable_tips?.map((tip: string, idx: number) => (
                <div key={idx} className="flex items-start gap-3 p-3 rounded-xl bg-gray-900/40 border border-gray-800/80 text-sm">
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-cyan-950/30 border border-cyan-900/40 text-center text-xs text-cyan-300 font-medium">
            "{feedback.encouragement_quote}"
          </div>
        </div>
      )}
    </div>
  );
}
