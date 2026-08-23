"""
transformation_engine.prediction_engine
────────────────────────────────────────
The orchestrator: validate → physiology → sub-scores → goal_logic → ML blend
→ behavior_adjuster.

This is the single place where all prediction layers meet. The goal-specific
scientific math comes from goal_logic, the ML corrections come from model_loader,
and the AI behavior factor comes from behavior_adjuster. Every other prediction
function in this module (predict_fat_loss, predict_muscle_gain, etc.) is a thin
wrapper around calculate_weekly_rates.

The wrappers accept both legacy positional args AND a PredictionContext so both
the old shim and new code work without changes.

All formulas and the 20% ML blend weight (alpha=0.20) are copied verbatim from
the original monolith. Parity-tested against tests/fixtures/baseline_predictions.json.
"""

from __future__ import annotations

import math
from copy import deepcopy

import pandas as pd

from .behavior_adjuster import apply_behavior_adjustment, behavior_factor, resolved_adherence_factor
from .context import PredictionContext
from .feature_processor import preprocess_inputs
from .model_loader import _predict_with_model, load_models
from .physiology_engine import calculate_body_metrics, calculate_readiness_subscores
from .goal_logic import compute_goal_rates
from .utils import DEFAULT_ADHERENCE, RATE_CAPS
from .validator import validate_inputs


# ── Internal orchestrator ─────────────────────────────────────────────────────

def calculate_weekly_rates(profile: dict | PredictionContext | None,
                           goal: str, calorie_delta: float, protein_g: float,
                           adherence_factor: float = DEFAULT_ADHERENCE,
                           fitness_intelligence: dict | None = None) -> dict:
    """
    The full 18-step prediction pipeline.

    1. Validate & clamp inputs
    2. Resolve fitness_intelligence (from explicit arg or embedded in profile)
    3. Override adherence from intelligence when present
    4. Compute body metrics (BMI, BMR, TDEE)
    5. Compute readiness sub-scores
    6. Run goal-specific scientific branch
    7. Build feature row for ML
    8. ML blend (alpha = 0.20)
    9. Apply AI behavior factor

    Returns the same rich dict as the original monolith (bmi, bmr, tdee,
    weekly_fat_loss, weekly_muscle_gain, weekly_weight_change, etc.).
    """
    # Handle PredictionContext input
    if isinstance(profile, PredictionContext):
        if fitness_intelligence is None:
            fitness_intelligence = profile.fitness_intelligence
        profile = profile.profile

    p = profile if isinstance(profile, dict) else {}

    # Step 1 — validate & clamp
    v = validate_inputs(p, goal, calorie_delta, protein_g, adherence_factor)
    goal = v["goal"]
    weight = v["weight"]
    height = v["height"]
    age = v["age"]
    gender = v["gender"]
    experience = v["experience"]
    workout_days = v["workout_days"]
    activity_level = v["activity_level"]
    sleep_hrs = v["sleep_hrs"]
    steps = v["steps"]
    protein_g = v["protein_g"]
    calorie_delta = v["calorie_delta"]
    adherence_factor = v["adherence_factor"]

    # Step 2 — resolve intelligence (mirrors monolith line 152)
    fitness_intelligence = fitness_intelligence or p.get("fitness_intelligence")

    # Step 3 — override adherence from intelligence
    if fitness_intelligence:
        adherence_factor = resolved_adherence_factor(fitness_intelligence, adherence_factor)

    # Step 4 — body metrics
    body = calculate_body_metrics(weight, height, age, gender,
                                workout_days, steps, activity_level)
    bmi = body["bmi"]
    bmr = body["bmr"]
    tdee = body["tdee"]
    maintenance_calories = body["maintenance_calories"]

    # Step 5 — readiness sub-scores
    scores = calculate_readiness_subscores(
        weight, protein_g, goal, workout_days, experience,
        sleep_hrs, steps, adherence_factor,
    )
    protein_adequacy = scores["protein_adequacy"]
    training_volume_score = scores["training_volume_score"]
    sleep_score = scores["sleep_score"]
    step_score = scores["step_score"]
    adherence_score = scores["adherence_score"]
    recovery_score = scores["recovery_score"]

    # Step 6 — goal-specific scientific rates
    deficit = max(0.0, -calorie_delta)
    surplus = max(0.0, calorie_delta)
    goal_inputs = {
        "deficit": deficit,
        "surplus": surplus,
        "experience": experience,
        "workout_days": workout_days,
    }
    gr = compute_goal_rates(goal, goal_inputs, scores)
    scientific_fat_loss = gr["scientific_fat_loss"]
    scientific_muscle_gain = gr["scientific_muscle_gain"]
    scientific_weight_change = gr["scientific_weight_change"]
    muscle_loss_fraction = gr["muscle_loss_fraction"]
    scientific_fat_gain = gr["scientific_fat_gain"]
    max_weekly_muscle_gain = gr.get("max_weekly_muscle_gain")

    # Step 7 — ML feature row
    alpha = 0.20
    norm_profile = {
        "age": age,
        "weight_kg": weight,
        "height_cm": height,
        "gender": gender,
        "experience": experience,
        "workout_days": workout_days,
        "protein_g": protein_g,
        "daily_steps": steps,
        "sleep_hrs": sleep_hrs,
        "adherence_factor": adherence_factor,
    }
    feature_row = preprocess_inputs(norm_profile, adherence_factor, calorie_delta, protein_g)
    models = load_models()

    # Step 8 — ML blend (20% weight)
    # Verbatim from monolith lines 311–380
    final_fat_loss = scientific_fat_loss
    final_muscle_gain = scientific_muscle_gain
    final_weight_change = scientific_weight_change

    ml_fat_loss = None
    ml_muscle_gain = None
    ml_weight_gain = None
    ml_recomp_fat_loss = None

    if goal == "Fat Loss":
        ml_fat_loss = _predict_with_model("Fat Loss", feature_row, models.get("Fat Loss"))
        if ml_fat_loss is not None and math.isfinite(ml_fat_loss):
            ml_fat_loss = max(0.0, float(ml_fat_loss))
            final_fat_loss = (1 - alpha) * scientific_fat_loss + alpha * ml_fat_loss

        final_fat_loss = min(RATE_CAPS["Fat Loss"]["max"], max(0.0, final_fat_loss))
        weekly_weight_change = -(final_fat_loss / (1.0 - muscle_loss_fraction))
        weekly_muscle_change = weekly_weight_change * muscle_loss_fraction
        weekly_fat_loss_change = -final_fat_loss

    elif goal == "Muscle Gain":
        ml_muscle_gain = _predict_with_model("Muscle Gain", feature_row, models.get("Muscle Gain"))
        if ml_muscle_gain is not None and math.isfinite(ml_muscle_gain):
            ml_muscle_gain = max(0.0, float(ml_muscle_gain))
            final_muscle_gain = (1 - alpha) * scientific_muscle_gain + alpha * ml_muscle_gain

        final_muscle_gain = min(max_weekly_muscle_gain, max(0.0, final_muscle_gain))

        final_weight_change = final_muscle_gain + scientific_fat_gain
        ml_weight_gain = _predict_with_model("Weight Gain", feature_row, models.get("Weight Gain"))
        if ml_weight_gain is not None and math.isfinite(ml_weight_gain):
            final_weight_change = (1 - alpha) * (final_muscle_gain + scientific_fat_gain) + alpha * max(0.0, float(ml_weight_gain))

        final_weight_change = min(RATE_CAPS["Muscle Gain"]["max"], max(0.0, final_weight_change))
        final_fat_gain = max(0.0, final_weight_change - final_muscle_gain)

        weekly_weight_change = final_weight_change
        weekly_muscle_change = final_muscle_gain
        weekly_fat_loss_change = -final_fat_gain

    elif goal == "Weight Gain":
        ml_weight_gain = _predict_with_model("Weight Gain", feature_row, models.get("Weight Gain"))
        if ml_weight_gain is not None and math.isfinite(ml_weight_gain):
            ml_weight_gain = max(0.0, float(ml_weight_gain))
            final_weight_change = (1 - alpha) * scientific_weight_change + alpha * ml_weight_gain
        else:
            final_weight_change = scientific_weight_change

        final_weight_change = min(RATE_CAPS["Weight Gain"]["max"], max(0.0, final_weight_change))
        weekly_muscle_change = final_weight_change * 0.35 * min(1.0, protein_adequacy) * min(1.0, training_volume_score)
        weekly_fat_loss_change = -(final_weight_change - weekly_muscle_change)
        weekly_weight_change = final_weight_change

    elif goal == "Body Recomposition":
        ml_recomp_fat_loss = _predict_with_model("Body Recomposition", feature_row, models.get("Body Recomposition"))
        if ml_recomp_fat_loss is not None and math.isfinite(ml_recomp_fat_loss):
            ml_recomp_fat_loss = max(0.0, float(ml_recomp_fat_loss))
            final_fat_loss = (1 - alpha) * scientific_fat_loss + alpha * ml_recomp_fat_loss

        ml_muscle_gain = _predict_with_model("Muscle Gain", feature_row, models.get("Muscle Gain"))
        if ml_muscle_gain is not None and math.isfinite(ml_muscle_gain):
            ml_recomp_muscle = max(0.0, float(ml_muscle_gain)) * 0.55
            final_muscle_gain = (1 - alpha) * scientific_muscle_gain + alpha * ml_recomp_muscle

        final_fat_loss = min(RATE_CAPS["Body Recomposition"]["fat_loss_max"], max(0.0, final_fat_loss))
        final_muscle_gain = min(RATE_CAPS["Body Recomposition"]["muscle_gain_max"], max(0.0, final_muscle_gain))

        weekly_weight_change = final_muscle_gain - final_fat_loss
        weekly_muscle_change = final_muscle_gain
        weekly_fat_loss_change = -final_fat_loss

    # Step 9 — AI behavior adjustment
    # Build the intermediate rates dict then let behavior_adjuster apply the factor
    from fitness_intelligence import normalize_fitness_intelligence
    ai_factor = behavior_factor(fitness_intelligence)
    rates = {
        "weekly_fat_loss": final_fat_loss,
        "weekly_muscle_gain": weekly_muscle_change,
        "weekly_weight_change": weekly_weight_change,
        "weekly_muscle_change": weekly_muscle_change,
        "weekly_fat_loss_change": weekly_fat_loss_change,
    }
    if fitness_intelligence:
        apply_behavior_adjustment(rates, fitness_intelligence)
    else:
        rates["ai_behavior_factor"] = 1.0

    return {
        "weekly_fat_loss": rates["weekly_fat_loss"],
        "weekly_muscle_gain": rates["weekly_muscle_gain"],
        "weekly_weight_change": rates["weekly_weight_change"],
        "weekly_fat_loss_change": rates["weekly_fat_loss_change"],
        "bmi": bmi,
        "bmr": bmr,
        "tdee": tdee,
        "maintenance_calories": maintenance_calories,
        "calorie_delta": calorie_delta,
        "protein_adequacy": protein_adequacy,
        "training_volume": training_volume_score,
        "recovery_score": recovery_score,
        "sleep_score": sleep_score,
        "step_score": step_score,
        "adherence_score": adherence_score,
        "scientific_fat_loss": scientific_fat_loss,
        "scientific_muscle_gain": scientific_muscle_gain,
        "scientific_weight_change": scientific_weight_change,
        "ml_fat_loss": ml_fat_loss,
        "ml_muscle_gain": ml_muscle_gain,
        "ml_weight_gain": ml_weight_gain,
        "ml_recomp_fat_loss": ml_recomp_fat_loss,
        "ai_behavior_factor": rates["ai_behavior_factor"],
        "fitness_intelligence": normalize_fitness_intelligence(fitness_intelligence)
                                if fitness_intelligence else None,
    }


# ── Public API wrappers (legacy signatures preserved) ─────────────────────────

def predict_fat_loss(weekly_deficit_kcal: float, weight_kg: float,
                     workout_days: int, protein_g: float,
                     model=None, feature_row=None,
                     profile: dict | None = None) -> float:
    """Wrapper: predict weekly fat loss (kg). Mirrors original monolith."""
    p = profile.copy() if profile is not None else {}
    p["weight_kg"] = weight_kg
    p["workout_days"] = workout_days
    daily_delta = -weekly_deficit_kcal / 7.0
    res = calculate_weekly_rates(
        p, "Fat Loss", daily_delta, protein_g,
        p.get("adherence_factor", DEFAULT_ADHERENCE),
    )
    return round(res["weekly_fat_loss"], 3)


def predict_muscle_gain(surplus_kcal_per_day: float, protein_g: float,
                         weight_kg: float, experience: str,
                         workout_days: int, model=None, feature_row=None,
                         profile: dict | None = None) -> float:
    """Wrapper: predict weekly muscle gain (kg). Mirrors original monolith."""
    p = profile.copy() if profile is not None else {}
    p["weight_kg"] = weight_kg
    p["experience"] = experience
    p["workout_days"] = workout_days
    res = calculate_weekly_rates(
        p, "Muscle Gain", surplus_kcal_per_day, protein_g,
        p.get("adherence_factor", DEFAULT_ADHERENCE),
    )
    return round(res["weekly_muscle_gain"], 3)


def predict_weight_change(calorie_delta_per_day: float, model=None,
                          feature_row=None, profile: dict | None = None,
                          protein_g: float = 120.0) -> float:
    """Wrapper: predict weekly weight change (kg). Mirrors original monolith."""
    p = profile.copy() if profile is not None else {}
    goal = p.get("goal", "Weight Gain")
    if calorie_delta_per_day < 0 and goal not in ("Body Recomposition",):
        goal = "Fat Loss"
    elif calorie_delta_per_day > 0 and goal not in ("Body Recomposition", "Muscle Gain"):
        goal = "Weight Gain"
    res = calculate_weekly_rates(
        p, goal, calorie_delta_per_day, protein_g,
        p.get("adherence_factor", DEFAULT_ADHERENCE),
    )
    return round(res["weekly_weight_change"], 3)


def predict_recomposition(protein_g: float, weight_kg: float,
                          workout_days: int, experience: str, model=None,
                          feature_row=None, profile: dict | None = None) -> dict:
    """Wrapper: predict recomposition (fat loss + muscle gain). Mirrors original monolith."""
    p = profile.copy() if profile is not None else {}
    p["weight_kg"] = weight_kg
    p["workout_days"] = workout_days
    p["experience"] = experience
    calorie_delta = p.get("calorie_delta", 0.0)
    res = calculate_weekly_rates(
        p, "Body Recomposition", calorie_delta, protein_g,
        p.get("adherence_factor", DEFAULT_ADHERENCE),
    )
    return {
        "fat_loss_kg": round(res["weekly_fat_loss"], 3),
        "muscle_gain_kg": round(res["weekly_muscle_gain"], 3),
        "net_weight_kg": round(res["weekly_weight_change"], 3),
        "note": (
            "Weight may stay same or decrease slightly while body composition "
            "improves. (Physiologically Grounded)"
            if res["weekly_weight_change"] <= 0
            else "Weight may stay same or increase slightly while body "
            "composition improves. (Physiologically Grounded)"
        ),
    }


def weeks_to_goal(current: float, target: float, weekly_change: float) -> int | None:
    """Weeks to reach target weight at a given weekly rate."""
    diff = abs(current - target)
    if weekly_change <= 0:
        return None
    return math.ceil(diff / weekly_change)


def generate_milestones(start_weight: float, target_weight: float,
                        weekly_change: float, goal: str) -> list[dict]:
    """Generate milestone projections at weeks 1, 2, 4, 8, 12, 16, 20."""
    milestones = []
    direction = -1 if goal in ("Fat Loss", "Body Recomposition") and target_weight < start_weight else 1

    for wk in sorted(set([1, 2, 4, 8, 12, 16, 20])):
        projected = start_weight + direction * weekly_change * wk
        if goal == "Fat Loss":
            projected = max(projected, target_weight)
        elif goal in ("Muscle Gain", "Weight Gain"):
            projected = min(projected, target_weight) if target_weight > start_weight else projected

        changed = abs(start_weight - projected)
        reached = (
            (goal in ("Fat Loss", "Body Recomposition") and projected <= target_weight + 0.1)
            or (goal not in ("Fat Loss", "Body Recomposition") and projected >= target_weight - 0.1)
        )
        milestones.append({
            "week": wk, "weight": round(projected, 1),
            "change": round(changed, 2), "reached_goal": reached,
        })
        if reached:
            break
    return milestones


def calculate_metrics(profile: dict, goal: str, calorie_delta: float,
                      protein_g: float,
                      adherence_factor: float = DEFAULT_ADHERENCE) -> dict:
    """Convenience: call calculate_weekly_rates and return a goal-specific summary."""
    res = calculate_weekly_rates(profile, goal, calorie_delta, protein_g, adherence_factor)
    if goal == "Fat Loss":
        wl = res["weekly_fat_loss"]
        return {
            "weekly_rate": wl,
            "weeks_to_goal": weeks_to_goal(
                profile.get("weight_kg", 70),
                profile.get("target_weight", 70), wl),
        }
    if goal == "Muscle Gain":
        return {"weekly_rate": res["weekly_muscle_gain"]}
    if goal == "Weight Gain":
        ww = res["weekly_weight_change"]
        return {
            "weekly_rate": ww,
            "weeks_to_goal": weeks_to_goal(
                profile.get("weight_kg", 70),
                profile.get("target_weight", 70), ww),
        }
    return {
        "fat_loss_kg": res["weekly_fat_loss"],
        "muscle_gain_kg": res["weekly_muscle_gain"],
        "net_weight_kg": res["weekly_weight_change"],
        "note": (
            "Weight may stay same or decrease slightly while body composition "
            "improves. (Physiologically Grounded)"
            if res["weekly_weight_change"] <= 0
            else "Weight may stay same or increase slightly while body "
            "composition improves. (Physiologically Grounded)"
        ),
    }


def predict_static(profile: dict, goal: str, calorie_delta: float,
                   protein_g: float,
                   adherence_factor: float = DEFAULT_ADHERENCE) -> dict:
    """Alias for calculate_metrics. Kept for backward compatibility."""
    return calculate_metrics(profile, goal, calorie_delta, protein_g, adherence_factor)
