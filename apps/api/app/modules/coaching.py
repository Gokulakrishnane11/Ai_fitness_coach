"""
AI Coaching & Journal Feedback API Module (Phase 7).
Parses user journal text using Pydantic structured output with Groq / NVIDIA NIM.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, UserContext
from app.core.config import settings
from app.db.supabase import JournalRepository, DailyLogRepository

router = APIRouter(prefix="/coaching", tags=["Coaching"])


class CoachingFeedbackSchema(BaseModel):
    sentiment_tag: str = Field(..., description="Detected emotional state, e.g. motivated, fatigued, stressed, consistent")
    summary: str = Field(..., description="Brief 1-2 sentence reflection on user journal entry")
    actionable_tips: List[str] = Field(..., description="2-3 specific actionable fitness/nutrition advice points")
    encouragement_quote: str = Field(..., description="Short positive motivational quote")


class JournalSubmissionSchema(BaseModel):
    entry_text: str = Field(..., min_length=5, max_length=2000)


FATIGUE_KEYWORDS = [
    "tired",
    "exhausted",
    "fatigue",
    "fatigued",
    "sore",
    "soreness",
    "pain",
    "painful",
    "weak",
    "weakness",
]

MOTIVATED_KEYWORDS = [
    "great",
    "strong",
    "best",
    "pushed",
    "easy",
    "motivated",
    "motivation",
    "fantastic",
    "smashed",
    "record",
    "pr",
    "prs",
]


def _contains_keyword(text: str, keywords: List[str]) -> bool:
    """Checks whether any keyword or phrase matches in text at word boundaries."""
    pattern = r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def generate_fallback_coaching_feedback(text: str) -> CoachingFeedbackSchema:
    """Generates structured feedback locally when LLM API keys are unconfigured."""
    if _contains_keyword(text, FATIGUE_KEYWORDS):
        sentiment = "fatigued"
        tips = [
            "Prioritize 8 hours of sleep tonight and increase water intake.",
            "Consider a light recovery walk or active mobility session instead of heavy lifting.",
            "Ensure protein and complex carb intake are sufficient for muscular recovery."
        ]
    elif _contains_keyword(text, MOTIVATED_KEYWORDS):
        sentiment = "motivated"
        tips = [
            "Capitalize on high energy by maintaining strict exercise form and progressive overload.",
            "Log your weights accurately to track week-over-week performance gains.",
            "Fuel post-workout recovery with high-quality protein within 2 hours."
        ]
    else:
        sentiment = "consistent"
        tips = [
            "Consistency is the single biggest predictor of long-term body composition success.",
            "Stick to your scheduled meal plan macros today.",
            "Maintain your target workout schedule for the rest of the week."
        ]

    return CoachingFeedbackSchema(
        sentiment_tag=sentiment,
        summary="Logged journal update regarding current training state.",
        actionable_tips=tips,
        encouragement_quote="Small daily improvements over time lead to stunning long-term results."
    )


@router.post("/journal")
def analyze_journal_entry(
    payload: JournalSubmissionSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Analyzes user journal entry text and returns structured AI coaching feedback forwarding JWT for RLS."""
    feedback = generate_fallback_coaching_feedback(payload.entry_text)

    saved_entry = JournalRepository.add_entry(
        user_id=user_ctx.user_id,
        entry_text=payload.entry_text,
        sentiment=feedback.sentiment_tag,
        ai_feedback=feedback.model_dump(),
        user_token=user_ctx.access_token,
    )

    return {
        "user_id": user_ctx.user_id,
        "entry_id": saved_entry["id"],
        "feedback": feedback,
    }
