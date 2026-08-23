"""
nutrition.py  —  Nutrition calculations for Smart Body Transformation AI Coach
"""

# ── Activity multipliers ──────────────────────────────────────────────────────
ACTIVITY_MULTIPLIERS = {
    "Sedentary (desk job, no exercise)":        1.2,
    "Lightly Active (1–3 days/week)":           1.375,
    "Moderately Active (3–5 days/week)":        1.55,
    "Very Active (6–7 days/week)":              1.725,
    "Extremely Active (athlete/physical job)":  1.9,
}

# ── Calorie adjustments by goal ──────────────────────────────────────────────
GOAL_CALORIE_DELTA = {
    "Fat Loss":            -400,
    "Muscle Gain":         +350,
    "Weight Gain":         +650,
    "Body Recomposition":    0,
}

# ── Protein targets (g per kg bodyweight) ───────────────────────────────────
PROTEIN_PER_KG = {
    "Fat Loss":            2.2,
    "Muscle Gain":         2.5,
    "Weight Gain":         1.8,
    "Body Recomposition":  2.6,
}


def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor equation."""
    base = 10 * weight + 6.25 * height - 5 * age
    return base + 5 if gender == "Male" else base - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    return bmr * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)


def get_target_calories(tdee: float, goal: str) -> float:
    return tdee + GOAL_CALORIE_DELTA.get(goal, 0)


def calculate_macros(calories: float, weight: float, goal: str) -> dict:
    """Return protein / carbs / fat / fiber in grams."""
    protein_g  = weight * PROTEIN_PER_KG.get(goal, 2.0)
    protein_cal = protein_g * 4

    fat_pct = 0.22 if goal in ("Muscle Gain", "Weight Gain") else 0.27
    fat_cal = calories * fat_pct
    fat_g   = fat_cal / 9

    carb_cal = max(0, calories - protein_cal - fat_cal)
    carb_g   = carb_cal / 4
    fiber_g  = round(14 * (calories / 1000))   # 14 g per 1,000 kcal

    return {
        "protein": round(protein_g),
        "carbs":   round(carb_g),
        "fat":     round(fat_g),
        "fiber":   fiber_g,
    }


def calculate_micronutrients(weight: float, age: int, gender: str, goal: str) -> dict:
    """Evidence-based RDA micronutrient targets."""
    iron_mg     = 18 if (gender == "Female" and age < 51) else 8
    calcium_mg  = 1200 if age > 50 else 1000
    if goal == "Muscle Gain":
        calcium_mg += 200
    vit_d_iu    = 800 if age >= 70 else 600
    b12_mcg     = 2.4
    mag_base    = 420 if gender == "Male" else 320
    magnesium_mg = mag_base + (40 if goal in ("Muscle Gain", "Body Recomposition") else 0)
    zinc_mg     = 11 if gender == "Male" else 8
    if goal in ("Muscle Gain", "Body Recomposition"):
        zinc_mg += 2

    return {
        "iron":        iron_mg,
        "calcium":     calcium_mg,
        "vitamin_d":   vit_d_iu,
        "vitamin_b12": b12_mcg,
        "magnesium":   magnesium_mg,
        "zinc":        zinc_mg,
    }


# ── Food database for nutrient estimation ────────────────────────────────────
FOOD_DB = {
    # name: (calories, protein_g, carbs_g, fat_g) per 100 g / 100 ml
    "rice (cooked)":         (130,  2.7, 28.2,  0.3),
    "wheat roti":            (297,  9.0, 55.0,  3.7),
    "chicken breast":        (165, 31.0,  0.0,  3.6),
    "egg (1 whole ~50g)":    ( 78,  6.0,  0.6,  5.0),
    "dal (cooked)":          (116,  9.0, 20.0,  0.4),
    "paneer (100g)":         (265, 18.0,  1.2, 20.0),
    "milk (full fat, 200ml)":(136,  6.8, 10.0,  7.6),
    "curd (100g)":           ( 60,  3.5,  4.7,  3.2),
    "banana (1 medium)":     ( 89,  1.1, 23.0,  0.3),
    "apple (medium)":        ( 52,  0.3, 14.0,  0.2),
    "oats (dry, 40g)":       (152,  5.2, 26.6,  3.0),
    "peanut butter (2 tbsp)":(188,  8.0,  6.0, 16.0),
    "sweet potato (100g)":   ( 86,  1.6, 20.0,  0.1),
    "broccoli (100g)":       ( 35,  2.8,  7.0,  0.4),
    "spinach (100g)":        ( 23,  2.9,  3.6,  0.4),
    "tuna (canned, 100g)":   (132, 28.0,  0.0,  2.0),
    "almonds (30g)":         (173,  6.0,  6.0, 15.0),
    "whey protein (30g)":    (120, 24.0,  3.0,  1.5),
    "white bread (1 slice)": ( 79,  2.7, 15.0,  1.0),
    "olive oil (1 tbsp)":    (119,  0.0,  0.0, 14.0),
}


def estimate_intake(food_items: list[dict]) -> dict:
    """
    food_items = [{"name": "rice (cooked)", "qty_g": 200}, ...]
    Returns estimated total macros for the day.
    """
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for item in food_items:
        name = item.get("name", "").lower()
        qty  = item.get("qty_g", 0)
        if name in FOOD_DB:
            cal, pro, car, fat = FOOD_DB[name]
            factor = qty / 100
            totals["calories"] += cal * factor
            totals["protein"]  += pro * factor
            totals["carbs"]    += car * factor
            totals["fat"]      += fat * factor
    return {k: round(v) for k, v in totals.items()}


def compare_intake(consumed: dict, required_cal: float,
                   required_macros: dict, goal: str) -> dict:
    """Returns comparison dict with status and messages."""
    result = {}
    checks = {
        "calories": (consumed.get("calories", 0), required_cal),
        "protein":  (consumed.get("protein", 0),  required_macros["protein"]),
        "carbs":    (consumed.get("carbs", 0),     required_macros["carbs"]),
        "fat":      (consumed.get("fat", 0),       required_macros["fat"]),
    }
    goal_messages = {
        "protein_low_Muscle Gain":        "⚠️ Protein too low — muscle growth will stall!",
        "protein_low_Body Recomposition": "⚠️ Protein too low — needed for recomposition.",
        "calories_high_Fat Loss":         "🚨 Calories too high — this will stall fat loss.",
        "calories_low_Muscle Gain":       "⚠️ Calories too low — insufficient for muscle growth.",
        "calories_low_Weight Gain":       "⚠️ Calories too low for weight gain target.",
    }
    for nutrient, (consumed_val, required_val) in checks.items():
        pct = (consumed_val / required_val * 100) if required_val else 0
        if pct < 80:
            status = "deficit"
        elif pct > 115:
            status = "excess"
        else:
            status = "balanced"
        msg_key = f"{nutrient}_{status.replace('deficit','low').replace('excess','high')}_{goal}"
        result[nutrient] = {
            "consumed":  consumed_val,
            "required":  round(required_val),
            "pct":       round(pct),
            "status":    status,
            "message":   goal_messages.get(msg_key, ""),
        }
    return result
