"""
Simplified Rule-Based Body Transformation & Simulation Engine.
Uses clean, transparent heuristic partitioning rules incorporating experience-level
muscle accretion caps, protein/workout multipliers, and dynamic caloric deficit/surplus recomposition.
"""

from typing import Dict, Any, List, Optional
import math
from app.engine.bmr_tdee import calculate_bmr, calculate_tdee

# Simplified Caloric Equivalents
KCAL_PER_KG_FAT_LOSS = 7700.0      # Standard 7,700 kcal per kg body fat
KCAL_PER_KG_MUSCLE = 2000.0        # Standard 2,000 kcal per kg lean tissue

# Experience Level Muscle Gain Caps (kg / week)
EXPERIENCE_MUSCLE_CAPS: Dict[str, float] = {
    "beginner": 0.30,      # ~1.2 kg / month max muscle gain
    "intermediate": 0.18,  # ~0.7 kg / month max muscle gain
    "advanced": 0.09,      # ~0.35 kg / month max muscle gain
}


def calculate_body_composition(
    weight_kg: float, body_fat_pct: Optional[float]
) -> Dict[str, float]:
    """Calculates initial fat mass and lean mass in kg."""
    if body_fat_pct is not None and 3.0 <= body_fat_pct <= 60.0:
        fat_mass_kg = weight_kg * (body_fat_pct / 100.0)
    else:
        fat_mass_kg = weight_kg * 0.22  # Baseline estimate (22% body fat)
    lean_mass_kg = weight_kg - fat_mass_kg
    return {
        "fat_mass_kg": round(fat_mass_kg, 2),
        "lean_mass_kg": round(lean_mass_kg, 2),
    }


def predict_transformation_timeline(
    current_weight_kg: float,
    target_weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    daily_caloric_deficit_surplus: int,
    adherence_pct: float = 85.0,
) -> Dict[str, Any]:
    """
    Predicts realistic weeks required to hit target weight.
    Returns expected weeks and a ±15% physiological uncertainty range.
    Uses standardized 7700.0 kcal/kg fat loss denominator.
    """
    delta_weight = target_weight_kg - current_weight_kg
    is_loss = delta_weight < 0

    if abs(delta_weight) < 0.1:
        return {
            "estimated_weeks": 0,
            "timeline_range_weeks": "0 - 0 weeks",
            "weekly_rate_kg": 0.0,
            "message": "Target weight is equal to current weight.",
        }

    effective_daily_diff = daily_caloric_deficit_surplus * (adherence_pct / 100.0)
    if is_loss and effective_daily_diff >= 0:
        effective_daily_diff = -500.0
    elif not is_loss and effective_daily_diff <= 0:
        effective_daily_diff = 350.0

    weekly_caloric_diff = effective_daily_diff * 7.0
    unbounded_weekly_change_kg = weekly_caloric_diff / KCAL_PER_KG_FAT_LOSS

    # Safe rate caps (max 1.0% body weight change per week)
    max_safe_weekly_rate = current_weight_kg * 0.010
    if is_loss:
        safe_weekly_rate = max(unbounded_weekly_change_kg, -max_safe_weekly_rate)
    else:
        safe_weekly_rate = min(unbounded_weekly_change_kg, max_safe_weekly_rate * 0.5)

    estimated_weeks = int(round(abs(delta_weight / safe_weekly_rate))) if safe_weekly_rate != 0 else 52
    estimated_weeks = max(1, min(estimated_weeks, 104))

    # ±15% Uncertainty Corridor
    lower_weeks = max(1, math.floor(estimated_weeks * 0.85))
    upper_weeks = math.ceil(estimated_weeks * 1.15)

    return {
        "estimated_weeks": estimated_weeks,
        "timeline_range_weeks": f"{lower_weeks} to {upper_weeks} weeks",
        "weekly_rate_kg": round(safe_weekly_rate, 2),
        "target_weight_kg": target_weight_kg,
        "is_safe_rate": abs(safe_weekly_rate) <= max_safe_weekly_rate,
        "estimation_model": "Simplified Rule Estimator (Experience Tiers & Dynamic Recomposition)",
        "uncertainty_margin": "±15% Range Corridor (Accounts for metabolic adaptation & water shifts)",
    }


def simulate_multi_week_transformation(
    start_weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    daily_caloric_deficit_surplus: int,
    adherence_pct: float = 85.0,
    duration_weeks: int = 12,
    body_fat_pct: Optional[float] = None,
    experience_level: str = "intermediate",
    goal_type: str = "fat_loss",
    protein_g_per_day: Optional[float] = None,
    workout_days_per_week: int = 4,
) -> List[Dict[str, Any]]:
    """
    Simulates week-by-week weight, fat mass, and lean mass trajectories.
    Dynamic recomposition handles deficit, maintenance, and surplus states cleanly.
    """
    initial_comp = calculate_body_composition(start_weight_kg, body_fat_pct)
    current_weight = start_weight_kg
    current_fat_mass = initial_comp["fat_mass_kg"]
    current_lean_mass = initial_comp["lean_mass_kg"]

    adherence_factor = max(0.5, min(adherence_pct / 100.0, 1.0))
    simulation_results: List[Dict[str, Any]] = []

    exp_key = experience_level.lower() if experience_level else "intermediate"
    max_weekly_muscle_cap = EXPERIENCE_MUSCLE_CAPS.get(exp_key, 0.18)

    target_p = start_weight_kg * 1.8
    actual_p = protein_g_per_day if protein_g_per_day is not None else target_p
    protein_ratio = min(1.1, max(0.6, actual_p / target_p))
    workout_ratio = min(1.0, max(0.4, workout_days_per_week / 4.0))
    training_stimulus_multiplier = protein_ratio * workout_ratio

    # Week 0 Baseline
    current_bf_pct = (current_fat_mass / current_weight) * 100.0
    bmr_0 = calculate_bmr(current_weight, height_cm, age, gender, current_bf_pct)
    tdee_0 = calculate_tdee(bmr_0, activity_level)

    simulation_results.append({
        "week": 0,
        "weight_kg": round(current_weight, 2),
        "fat_mass_kg": round(current_fat_mass, 2),
        "lean_mass_kg": round(current_lean_mass, 2),
        "body_fat_pct": round(current_bf_pct, 1),
        "weight_range_kg": f"{round(current_weight * 0.98, 1)} - {round(current_weight * 1.02, 1)}",
        "bmr": bmr_0,
        "tdee": tdee_0,
    })

    for week in range(1, duration_weeks + 1):
        current_bf_pct = (current_fat_mass / current_weight) * 100.0
        bmr = calculate_bmr(current_weight, height_cm, age, gender, current_bf_pct)
        base_tdee = calculate_tdee(bmr, activity_level)

        metabolic_adaptation_factor = 1.0
        if daily_caloric_deficit_surplus < 0:
            adaptation_cycles = week // 4
            metabolic_adaptation_factor = max(0.90, 1.0 - (adaptation_cycles * 0.015))

        effective_tdee = base_tdee * metabolic_adaptation_factor
        effective_daily_diff = daily_caloric_deficit_surplus * adherence_factor
        weekly_kcal_delta = effective_daily_diff * 7.0

        if goal_type.lower() == "recomposition":
            if weekly_kcal_delta < 0:
                # Deficit recomposition: User's real caloric deficit mobilizes fat mass
                fat_loss_energy = abs(weekly_kcal_delta)
                fat_loss_kg = fat_loss_energy / KCAL_PER_KG_FAT_LOSS
                potential_lean_gain = (fat_loss_energy * 0.40 / KCAL_PER_KG_MUSCLE) * training_stimulus_multiplier
                lean_gain_kg = min(potential_lean_gain, max_weekly_muscle_cap)
                fat_delta = -fat_loss_kg
                lean_delta = lean_gain_kg
            elif weekly_kcal_delta == 0:
                # Maintenance recomposition: 100 kcal/day (700 kcal/wk) energy shift from fat to muscle
                fat_loss_energy = 700.0
                fat_loss_kg = fat_loss_energy / KCAL_PER_KG_FAT_LOSS
                potential_lean_gain = (fat_loss_energy * 0.40 / KCAL_PER_KG_MUSCLE) * training_stimulus_multiplier
                lean_gain_kg = min(potential_lean_gain, max_weekly_muscle_cap)
                fat_delta = -fat_loss_kg
                lean_delta = lean_gain_kg
            else:
                # Surplus recomposition: Surplus fuels muscle up to cap; excess stores as fat mass
                lean_gain_raw = ((weekly_kcal_delta * 0.65) / KCAL_PER_KG_MUSCLE) * training_stimulus_multiplier
                lean_delta = min(lean_gain_raw, max_weekly_muscle_cap)
                fat_delta = max((weekly_kcal_delta - (lean_delta * KCAL_PER_KG_MUSCLE)) / KCAL_PER_KG_FAT_LOSS, 0.0)

        elif weekly_kcal_delta < 0:
            # Standard Deficit
            lean_loss_fraction = 0.15 / max(0.7, training_stimulus_multiplier)
            fat_loss_fraction = 1.0 - lean_loss_fraction
            fat_delta = (weekly_kcal_delta * fat_loss_fraction) / KCAL_PER_KG_FAT_LOSS
            lean_delta = (weekly_kcal_delta * lean_loss_fraction) / KCAL_PER_KG_MUSCLE
        else:
            # Standard Surplus
            lean_gain_raw = ((weekly_kcal_delta * 0.65) / KCAL_PER_KG_MUSCLE) * training_stimulus_multiplier
            lean_delta = min(lean_gain_raw, max_weekly_muscle_cap)
            fat_delta = max((weekly_kcal_delta - (lean_delta * KCAL_PER_KG_MUSCLE)) / KCAL_PER_KG_FAT_LOSS, 0.0)

        max_weekly_delta = current_weight * 0.010
        total_delta = fat_delta + lean_delta
        if abs(total_delta) > max_weekly_delta:
            scale = max_weekly_delta / abs(total_delta)
            fat_delta *= scale
            lean_delta *= scale

        current_fat_mass = max(3.0, current_fat_mass + fat_delta)
        current_lean_mass = max(20.0, current_lean_mass + lean_delta)
        current_weight = current_fat_mass + current_lean_mass

        lower_wt = round(current_weight * 0.985, 1)
        upper_wt = round(current_weight * 1.015, 1)

        simulation_results.append({
            "week": week,
            "weight_kg": round(current_weight, 2),
            "fat_mass_kg": round(current_fat_mass, 2),
            "lean_mass_kg": round(current_lean_mass, 2),
            "body_fat_pct": round((current_fat_mass / current_weight) * 100.0, 1),
            "weight_range_kg": f"{lower_wt} - {upper_wt}",
            "bmr": bmr,
            "tdee": round(effective_tdee, 1),
        })

    return simulation_results
