"""
BMR, TDEE, and Target Macro Calculator Engine.
Single Source of Truth for BMR selection:
- Uses Katch-McArdle if body_fat_pct is present and in [3.0, 60.0]
- Uses Mifflin-St Jeor otherwise
- Enforces MAX(BMR, 800.0) clinical safety floor guard
"""

from typing import Dict, Any, Optional

ACTIVITY_MULTIPLIERS: Dict[str, float] = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}

CALORIE_FLOORS: Dict[str, int] = {
    "male": 1500,
    "female": 1200,
    "other": 1350,
}


def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    body_fat_pct: Optional[float] = None,
) -> float:
    """
    Single Source of Truth BMR Calculator.
    Enforces Katch-McArdle if body_fat_pct is present; Mifflin-St Jeor otherwise.
    """
    if body_fat_pct is not None and 3.0 <= body_fat_pct <= 60.0:
        # Katch-McArdle Formula (Lean Mass Based)
        lbm_kg = weight_kg * (1.0 - (body_fat_pct / 100.0))
        bmr = 370.0 + (21.6 * lbm_kg)
    else:
        # Mifflin-St Jeor Formula
        base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
        gender_lower = gender.lower() if gender else "other"
        if gender_lower == "male":
            bmr = base + 5.0
        elif gender_lower == "female":
            bmr = base - 161.0
        else:
            bmr = base - 78.0  # Midpoint average

    # Clinical Safety Floor Guard
    return round(max(bmr, 800.0), 1)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Calculates Total Daily Energy Expenditure (TDEE) in kcal/day."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.2)
    return round(bmr * multiplier, 1)


def calculate_target_metrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal_type: str,
    body_fat_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes complete target metrics including BMR, TDEE, Target Calories,
    Protein, Fat, Carbs, Fiber, and Water requirement.
    Enforces safe biological caloric floors.
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, gender, body_fat_pct)
    tdee = calculate_tdee(bmr, activity_level)

    goal = goal_type.lower() if goal_type else "recomposition"
    gender_key = gender.lower() if gender else "other"

    # Caloric Adjustment & Macro Distributions
    if goal == "fat_loss":
        deficit = min(tdee * 0.20, 750.0)
        raw_calories = tdee - deficit
        protein_g_per_kg = 2.2
    elif goal == "muscle_gain":
        surplus = min(tdee * 0.12, 400.0)
        raw_calories = tdee + surplus
        protein_g_per_kg = 2.0
    elif goal == "weight_gain":
        surplus = min(tdee * 0.15, 500.0)
        raw_calories = tdee + surplus
        protein_g_per_kg = 1.8
    else:  # recomposition / maintenance
        raw_calories = tdee
        protein_g_per_kg = 2.1

    # Enforce safe calorie floors
    calorie_floor = CALORIE_FLOORS.get(gender_key, 1350)
    target_calories = int(round(max(raw_calories, calorie_floor)))

    protein_g = round(weight_kg * protein_g_per_kg, 1)
    protein_calories = protein_g * 4.0

    min_fat_g = weight_kg * 0.8
    fat_from_pct = (target_calories * 0.25) / 9.0
    fat_g = round(max(fat_from_pct, min_fat_g), 1)
    fat_calories = fat_g * 9.0

    remaining_calories = max(target_calories - (protein_calories + fat_calories), 0.0)
    carbs_g = round(remaining_calories / 4.0, 1)

    min_fiber = 38.0 if gender_key == "male" else 25.0
    fiber_g = round(max((target_calories / 1000.0) * 14.0, min_fiber), 1)

    water_liters = round((weight_kg * 0.035) + 0.5, 1)

    return {
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": target_calories,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carbs_g": carbs_g,
        "fiber_g": fiber_g,
        "water_liters": water_liters,
        "is_calorie_floor_applied": target_calories == calorie_floor,
    }
