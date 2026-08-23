"""
transformation_engine.behavior_adjuster
───────────────────────────────────────
The single chokepoint where AI-derived behavior modifies scientific predictions.

Per the architecture principle "the AI refines, never replaces" (Doc #1 / Doc
#2), all adjustment of physiological rates by the Fitness Intelligence profile
flows through this module. The scientific core (goal_logic, physiology_engine)
has zero knowledge of AI; only prediction_engine calls apply_behavior_adjustment
after the scientific + ML rates are computed.

This is an extraction of the `ai_factor` multiplication that lived at the tail
of the monolith's calculate_weekly_rates (lines 382–387). The factor itself is
computed by fitness_intelligence.prediction_behavior_factor, which blends the
adherence/recovery/nutrition/training/motivation/sleep scores and subtracts a
risk penalty (stress/plateau/injury).
"""

from __future__ import annotations

from fitness_intelligence import (
    adherence_factor_from_intelligence,
    normalize_fitness_intelligence,
    prediction_behavior_factor,
)


def behavior_factor(intelligence: dict | None) -> float:
    """
    The multiplicative factor (clamped ~0.45–1.12) by which behavior scales the
    scientific rate. Returns 1.0 when there is no intelligence profile, leaving
    the scientific prediction untouched.
    """
    if not intelligence:
        return 1.0
    return prediction_behavior_factor(intelligence)


def resolved_adherence_factor(intelligence: dict | None, fallback: float) -> float:
    """Adherence factor overridden by the AI adherence_score when present."""
    if not intelligence:
        return fallback
    return adherence_factor_from_intelligence(intelligence, fallback)


def apply_behavior_adjustment(rates: dict, intelligence: dict | None) -> dict:
    """
    Multiply every weekly rate in `rates` by the behavior factor, in place AND
    returned. Mirrors the monolith exactly:

        final_fat_loss        *= ai_factor
        final_muscle_gain     *= ai_factor
        weekly_weight_change  *= ai_factor
        weekly_muscle_change  *= ai_factor
        weekly_fat_loss_change*= ai_factor

    `rates` is expected to already contain the post-ML-blend values. The dict
    also gains an `ai_behavior_factor` key for transparency/UI.
    """
    factor = behavior_factor(intelligence)
    rates["weekly_fat_loss"] = rates.get("weekly_fat_loss", 0.0) * factor
    rates["weekly_muscle_gain"] = rates.get("weekly_muscle_gain", 0.0) * factor
    rates["weekly_weight_change"] = rates.get("weekly_weight_change", 0.0) * factor
    if "weekly_muscle_change" in rates:
        rates["weekly_muscle_change"] = rates["weekly_muscle_change"] * factor
    if "weekly_fat_loss_change" in rates:
        rates["weekly_fat_loss_change"] = rates["weekly_fat_loss_change"] * factor
    rates["ai_behavior_factor"] = factor
    return rates
