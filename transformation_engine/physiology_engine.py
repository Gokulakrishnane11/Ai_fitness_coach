"""
transformation_engine.physiology_engine
───────────────────────────────────────
Core exercise-science calculations: BMI, BMR (Mifflin-St Jeor), TDEE, and the
activity-multiplier selection.

This is a DRY extraction: the original monolith computed these same quantities
twice — once inside calculate_weekly_rates and again inside run_simulation —
with identical formulas. Centralising them removes the duplication while
preserving the exact math (verified by the parity test).

No AI, no ML, no Streamlit. Pure deterministic physiology.
"""

from __future__ import annotations

from nutrition import ACTIVITY_MULTIPLIERS


def calculate_body_metrics(weight: float, height: float, age: int,
                           gender: str, workout_days: int, steps: float,
                           activity_level: str | None = None) -> dict:
    """
    Compute BMI, BMR, TDEE, activity multiplier, and maintenance calories.

    Args mirror the validated inputs produced by validator.validate_inputs.

    Activity multiplier resolution matches the original monolith:
      1. If the profile carries a known activity_level, use its multiplier.
      2. Otherwise infer from steps + workout_days bands.

    Returns dict: bmi, bmr, tdee, multiplier, maintenance_calories.
    """
    # BMI
    bmi = weight / ((height / 100.0) ** 2)

    # BMR — Mifflin-St Jeor
    base_bmr = 10.0 * weight + 6.25 * height - 5.0 * age
    bmr = base_bmr + 5.0 if gender == "Male" else base_bmr - 161.0

    # Activity multiplier
    if activity_level in ACTIVITY_MULTIPLIERS:
        multiplier = ACTIVITY_MULTIPLIERS[activity_level]
    else:
        if steps >= 12000 and workout_days >= 5:
            multiplier = 1.725
        elif steps >= 10000 or workout_days >= 4:
            multiplier = 1.55
        elif steps >= 5000 or workout_days >= 2:
            multiplier = 1.375
        else:
            multiplier = 1.2

    tdee = bmr * multiplier
    return {
        "bmi": bmi,
        "bmr": bmr,
        "tdee": tdee,
        "multiplier": multiplier,
        "maintenance_calories": tdee,
    }


def calculate_readiness_subscores(weight: float, protein_g: float, goal: str,
                                  workout_days: int, experience: str,
                                  sleep_hrs: float, steps: float,
                                  adherence_factor: float) -> dict:
    """
    The six readiness sub-scores (each in ~0–1.5 range) used by goal_logic.

    These were inlined in calculate_weekly_rates between the activity multiplier
    and the goal branches. Factored out here so goal_logic stays pure and so the
    sub-scores are testable in isolation. Formulas are unchanged.

    Returns: protein_adequacy, training_volume_score, sleep_score, step_score,
             adherence_score, recovery_score.
    """
    from .utils import PROTEIN_PER_KG

    # Protein adequacy vs goal-specific g/kg target
    target_protein = weight * PROTEIN_PER_KG.get(goal, 2.0)
    protein_adequacy = min(1.5, protein_g / max(1.0, target_protein))

    # Training volume vs experience-appropriate weekly frequency
    optimal_days = {"Beginner": 3, "Intermediate": 4, "Advanced": 5}.get(experience, 3)
    training_volume_score = min(1.2, workout_days / optimal_days)

    # Sleep quality (peak band 7–9h)
    if 7.0 <= sleep_hrs <= 9.0:
        sleep_score = 1.0
    elif sleep_hrs < 7.0:
        sleep_score = max(0.4, sleep_hrs / 7.0)
    else:
        sleep_score = max(0.8, 1.0 - (sleep_hrs - 9.0) * 0.05)

    # Step activity
    step_score = min(1.5, steps / 10000.0)

    # Adherence passes straight through (already clamped 0–1 upstream)
    adherence_score = adherence_factor

    # Composite recovery from sleep + protein + training balance
    training_balance = 1.0 - max(0, workout_days - 5) * 0.15
    recovery_score = (sleep_score * 0.4) + (protein_adequacy * 0.4) + (training_balance * 0.2)
    recovery_score = max(0.0, min(1.2, recovery_score))

    return {
        "protein_adequacy": protein_adequacy,
        "training_volume_score": training_volume_score,
        "sleep_score": sleep_score,
        "step_score": step_score,
        "adherence_score": adherence_score,
        "recovery_score": recovery_score,
    }
