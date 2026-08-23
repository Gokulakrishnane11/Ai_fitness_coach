"""
transformation_engine.validator
───────────────────────────────
Input validation layer.

Formalises the inline max(min(...)) clamps that were scattered through the
monolith's calculate_weekly_rates (and re-clamps inside run_simulation) into a
single function with documented bounds. Every prediction path now funnels
through validate_inputs first, so the physiology and goal modules can assume
sanitised values.

Validation rules (preserving original numeric bounds exactly):
  weight        30 – 250 kg
  height        100 – 250 cm
  age           10 – 100
  workout_days  0 – 7
  sleep_hrs     0 – 24
  steps         >= 0
  protein_g     >= 0
  adherence     0 – 1
  calorie_delta no clamp (surplus/deficit handled downstream)

Raises ValueError only on truly impossible inputs (unknown goal, non-positive
height, missing profile). Everything else is clamped, matching prior behavior.
"""

from __future__ import annotations

from .context import PredictionContext
from .utils import DEFAULT_ADHERENCE, SUPPORTED_GOALS


def _coerce_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def validate_inputs(profile: dict | PredictionContext | None,
                    goal: str | None = None,
                    calorie_delta: float | None = None,
                    protein_g: float | None = None,
                    adherence_factor: float | None = None) -> dict:
    """
    Sanitise a profile (or a PredictionContext) into a clean dict of clamped
    physiological inputs plus the goal and calorie/protein/adherence values.

    Returns a dict with keys:
      goal, weight, height, age, gender, experience, workout_days, activity_level,
      sleep_hrs, steps, protein_g, calorie_delta, adherence_factor

    Raises ValueError if the goal is unsupported or height is non-positive.
    """
    # Accept a PredictionContext as the first arg for ergonomic call sites.
    if isinstance(profile, PredictionContext):
        if goal is None:
            goal = profile.goal
        if calorie_delta is None:
            calorie_delta = profile.calorie_delta
        if protein_g is None:
            protein_g = profile.protein_g
        if adherence_factor is None:
            adherence_factor = profile.adherence_factor
        profile = profile.profile

    profile = profile if isinstance(profile, dict) else {}
    resolved_goal = goal or profile.get("goal", "Fat Loss")
    if resolved_goal not in SUPPORTED_GOALS:
        raise ValueError(
            f"Unknown goal {resolved_goal!r}. Supported: {SUPPORTED_GOALS}"
        )

    weight = _coerce_float(profile.get("weight_kg", profile.get("weight", 70.0)), 70.0)
    height = _coerce_float(profile.get("height_cm", profile.get("height", 170.0)), 170.0)
    if height <= 0:
        raise ValueError(f"Height must be positive, got {height}")

    age = _coerce_int(profile.get("age", 25), 25)
    workout_days = _coerce_int(profile.get("workout_days", 3), 3)
    sleep_hrs = _coerce_float(profile.get("sleep_hrs", 7.0), 7.0)
    steps = _coerce_float(profile.get("daily_steps", profile.get("steps", 8000)), 8000)

    # Clamp to the same physiological bounds the monolith used inline.
    weight = max(30.0, min(250.0, weight))
    height = max(100.0, min(250.0, height))
    age = max(10, min(100, age))
    workout_days = max(0, min(7, workout_days))
    sleep_hrs = max(0.0, min(24.0, sleep_hrs))
    steps = max(0.0, steps)

    cal_delta = _coerce_float(calorie_delta, 0.0)
    protein = _coerce_float(protein_g, profile.get("protein_g", 120.0))
    protein = max(0.0, protein)

    adh = _coerce_float(adherence_factor, DEFAULT_ADHERENCE)
    adh = max(0.0, min(1.0, adh))

    return {
        "goal": resolved_goal,
        "weight": float(weight),
        "height": float(height),
        "age": int(age),
        "gender": profile.get("gender", "Male"),
        "experience": profile.get("experience", "Beginner"),
        "workout_days": int(workout_days),
        "activity_level": profile.get("activity_level"),
        "sleep_hrs": float(sleep_hrs),
        "steps": float(steps),
        "protein_g": float(protein),
        "calorie_delta": float(cal_delta),
        "adherence_factor": float(adh),
    }
