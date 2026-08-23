"""
transformation_engine.goal_logic
────────────────────────────────
Goal-specific scientific rate calculations for the four supported goals.

This module holds the pure-exercise-science math that was inlined as the four
branches (Fat Loss / Muscle Gain / Weight Gain / Body Recomposition) inside the
monolith's calculate_weekly_rates. It produces RAW scientific rates — no ML
blend, no AI behavior factor. Those layers are applied by prediction_engine
(goal_logic must stay free of model_loader and fitness_intelligence imports).

Each goal branch returns the same dict shape so the orchestrator can treat
them uniformly:

    {
        "scientific_fat_loss":      float,
        "scientific_muscle_gain":   float,
        "scientific_weight_change": float,
        "muscle_loss_fraction":     float,   # Fat Loss only; 0.0 elsewhere
        "scientific_fat_gain":      float,   # Muscle/Weight Gain only
    }

All formulas, caps, and factors are copied verbatim from the original monolith
(parity-tested against tests/fixtures/baseline_predictions.json).
"""

from __future__ import annotations

from .utils import RATE_CAPS


def compute_goal_rates(goal: str, inputs: dict, scores: dict) -> dict:
    """
    Run the goal-specific scientific branch.

    Args:
        goal:    one of Fat Loss / Muscle Gain / Weight Gain / Body Recomposition.
        inputs:  validated physiological inputs (deficit, surplus, weight,
                 experience, workout_days, adherence_factor).
        scores:  readiness sub-scores from physiology_engine
                 (protein_adequacy, training_volume_score, recovery_score,
                 step_score, sleep_score, adherence_score).

    Returns the uniform scientific-rates dict described in the module docstring.
    """
    if goal == "Fat Loss":
        return _fat_loss(inputs, scores)
    if goal == "Muscle Gain":
        return _muscle_gain(inputs, scores)
    if goal == "Weight Gain":
        return _weight_gain(inputs, scores)
    if goal == "Body Recomposition":
        return _recomposition(inputs, scores)
    # validator rejects unknown goals, but defend in depth:
    return _fat_loss(inputs, scores)


def _fat_loss(inputs: dict, scores: dict) -> dict:
    deficit = inputs["deficit"]
    adherence = scores["adherence_score"]
    protein_adequacy = scores["protein_adequacy"]
    sleep_score = scores["sleep_score"]
    step_score = scores["step_score"]
    training_volume_score = scores["training_volume_score"]

    weekly_deficit_kcal = deficit * 7.0
    scientific_fat_loss = (weekly_deficit_kcal / 7700.0) * adherence
    protein_factor = 0.9 + 0.15 * min(1.0, protein_adequacy)
    sleep_factor = 0.9 + 0.1 * sleep_score
    step_factor = 0.9 + 0.1 * min(1.5, step_score)
    scientific_fat_loss *= (protein_factor * sleep_factor * step_factor)
    scientific_fat_loss = min(RATE_CAPS["Fat Loss"]["max"], max(0.0, scientific_fat_loss))

    muscle_preservation = 0.6 * min(1.0, protein_adequacy) + 0.4 * min(1.0, training_volume_score)
    muscle_loss_fraction = 0.35 * (1.0 - muscle_preservation)

    return {
        "scientific_fat_loss": scientific_fat_loss,
        "scientific_muscle_gain": 0.0,
        "scientific_weight_change": -(scientific_fat_loss / (1.0 - muscle_loss_fraction)),
        "muscle_loss_fraction": muscle_loss_fraction,
        "scientific_fat_gain": 0.0,
        "max_weekly_muscle_gain": None,  # not used by Fat Loss
    }


def _muscle_gain(inputs: dict, scores: dict) -> dict:
    surplus = inputs["surplus"]
    experience = inputs["experience"]
    adherence = scores["adherence_score"]
    protein_adequacy = scores["protein_adequacy"]
    training_volume_score = scores["training_volume_score"]
    recovery_score = scores["recovery_score"]

    weekly_surplus_kcal = surplus * 7.0
    max_weekly_muscle_gain = {"Beginner": 0.25, "Intermediate": 0.15, "Advanced": 0.06}.get(experience, 0.15)
    surplus_factor = min(1.0, surplus / 350.0) if surplus > 50 else (surplus / 50.0) * 0.15
    scientific_muscle_gain = (
        max_weekly_muscle_gain * surplus_factor
        * min(1.0, protein_adequacy)
        * min(1.0, training_volume_score)
        * min(1.0, recovery_score)
        * adherence
    )
    scientific_muscle_gain = min(max_weekly_muscle_gain, max(0.0, scientific_muscle_gain))

    total_surplus_weight_gain = (weekly_surplus_kcal / 7700.0) * adherence
    scientific_fat_gain = max(0.0, total_surplus_weight_gain - scientific_muscle_gain)
    scientific_weight_change = scientific_muscle_gain + scientific_fat_gain
    scientific_weight_change = min(RATE_CAPS["Muscle Gain"]["max"], max(0.0, scientific_weight_change))

    return {
        "scientific_fat_loss": 0.0,
        "scientific_muscle_gain": scientific_muscle_gain,
        "scientific_weight_change": scientific_weight_change,
        "muscle_loss_fraction": 0.0,
        "scientific_fat_gain": scientific_fat_gain,
        "max_weekly_muscle_gain": max_weekly_muscle_gain,
    }


def _weight_gain(inputs: dict, scores: dict) -> dict:
    surplus = inputs["surplus"]
    adherence = scores["adherence_score"]
    protein_adequacy = scores["protein_adequacy"]
    training_volume_score = scores["training_volume_score"]

    weekly_surplus_kcal = surplus * 7.0
    scientific_weight_change = (weekly_surplus_kcal / 7700.0) * adherence
    scientific_weight_change = min(RATE_CAPS["Weight Gain"]["max"], max(0.0, scientific_weight_change))

    # NOTE: scientific_muscle_gain stays 0.0 here — the monolith never assigns it
    # in the Weight Gain branch. The actual muscle split is recomputed in the
    # ML-blend block of prediction_engine from the post-blend weight change.
    weekly_muscle_change = (
        scientific_weight_change * 0.35
        * min(1.0, protein_adequacy)
        * min(1.0, training_volume_score)
    )
    scientific_fat_gain = max(0.0, scientific_weight_change - weekly_muscle_change)

    return {
        "scientific_fat_loss": 0.0,
        "scientific_muscle_gain": 0.0,
        "scientific_weight_change": scientific_weight_change,
        "muscle_loss_fraction": 0.0,
        "scientific_fat_gain": scientific_fat_gain,
        "max_weekly_muscle_gain": None,
    }


def _recomposition(inputs: dict, scores: dict) -> dict:
    deficit = inputs["deficit"]
    surplus = inputs["surplus"]
    experience = inputs["experience"]
    adherence = scores["adherence_score"]
    protein_adequacy = scores["protein_adequacy"]
    training_volume_score = scores["training_volume_score"]
    recovery_score = scores["recovery_score"]
    step_score = scores["step_score"]

    # Fat loss
    base_recomp_fat_loss = 0.06 * min(1.5, step_score) * min(1.0, protein_adequacy) * adherence
    deficit_fat_loss = (deficit * 7 / 7700.0) * adherence
    scientific_fat_loss = deficit_fat_loss + base_recomp_fat_loss
    scientific_fat_loss = min(RATE_CAPS["Body Recomposition"]["fat_loss_max"], max(0.0, scientific_fat_loss))

    # Muscle gain
    max_recomp_muscle = {"Beginner": 0.15, "Intermediate": 0.08, "Advanced": 0.03}.get(experience, 0.08)
    deficit_penalty = max(0.3, 1.0 - (deficit / 500.0)) if deficit > 0 else 1.0
    surplus_boost = min(1.2, 1.0 + (surplus / 350.0))
    scientific_muscle_gain = (
        max_recomp_muscle
        * min(1.0, protein_adequacy)
        * min(1.0, training_volume_score)
        * min(1.0, recovery_score)
        * adherence
        * deficit_penalty
        * surplus_boost
    )
    scientific_muscle_gain = min(RATE_CAPS["Body Recomposition"]["muscle_gain_max"], max(0.0, scientific_muscle_gain))

    return {
        "scientific_fat_loss": scientific_fat_loss,
        "scientific_muscle_gain": scientific_muscle_gain,
        "scientific_weight_change": scientific_muscle_gain - scientific_fat_loss,
        "muscle_loss_fraction": 0.0,
        "scientific_fat_gain": 0.0,
        "max_weekly_muscle_gain": None,
    }
