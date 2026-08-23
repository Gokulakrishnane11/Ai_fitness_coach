"""
transformation_engine.feature_processor
───────────────────────────────────────
Turns a user profile dict into the exact one-row DataFrame the trained ML
pipelines expect (columns and order defined by utils.FEATURE_ORDER).

This module performs NO scientific calculation and NO prediction — it only
shapes and encodes inputs (e.g. gender → 0/1, experience label → 0/1/2). The
physiology and goal math lives in physiology_engine / goal_logic.

Moved verbatim from the original monolith.
"""

import pandas as pd

from .utils import DEFAULT_ADHERENCE, FEATURE_ORDER


def preprocess_inputs(profile: dict, adherence_factor: float | None = None,
                      calorie_delta: float = 0.0,
                      protein_g: float | None = None) -> pd.DataFrame:
    """
    Build a single-row feature DataFrame for an ML model call.

    Accepts the same profile dict keys used across the app (weight_kg / weight,
    height_cm / height, etc.) and normalises them to the FEATURE_ORDER columns.
    All keys have safe defaults so a partial profile still produces a valid row.
    """
    w = profile.get("weight_kg", profile.get("weight", 70.0))
    h = profile.get("height_cm", profile.get("height", 170.0))
    exp = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    row = {
        "age": profile.get("age", 25),
        "weight": w,
        "height": h,
        "bmi": w / (h / 100) ** 2,
        "gender": 1 if profile.get("gender") == "Male" else 0,
        "experience": exp.get(profile.get("experience"), 0),
        "workout_days": profile.get("workout_days", 3),
        "adherence": DEFAULT_ADHERENCE if adherence_factor is None else adherence_factor,
        "protein_g": protein_g if protein_g is not None else profile.get("protein_g", 120.0),
        "calorie_delta": calorie_delta,
        "sleep_hrs": profile.get("sleep_hrs", 7.0),
        "steps": profile.get("daily_steps", profile.get("steps", 8000)),
    }
    return pd.DataFrame([row], columns=FEATURE_ORDER)


def make_feature_row(profile: dict, adherence_factor: float, calorie_delta: float,
                     protein_g: float) -> pd.DataFrame:
    """Explicit-arity alias for preprocess_inputs (kept for call-site clarity)."""
    return preprocess_inputs(profile, adherence_factor, calorie_delta, protein_g)
