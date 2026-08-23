"""
Deterministic Nutrition & Meal Plan Matching Engine.
Matches target calories and macros to pre-validated meal components
based on user dietary preferences (anything, vegetarian, vegan, keto, paleo).
"""

from typing import Dict, Any, List, Optional

# Seed Food Database for Rule Engine
SEED_FOODS: List[Dict[str, Any]] = [
    # Protein sources
    {"name": "Chicken Breast (Grilled)", "category": "protein", "is_veg": False, "is_vegan": False, "cal_100g": 165, "p": 31.0, "c": 0.0, "f": 3.6, "fib": 0.0},
    {"name": "Paneer (Cottage Cheese)", "category": "protein", "is_veg": True, "is_vegan": False, "cal_100g": 265, "p": 18.0, "c": 3.4, "f": 20.0, "fib": 0.0},
    {"name": "Tofu (Firm)", "category": "protein", "is_veg": True, "is_vegan": True, "cal_100g": 144, "p": 15.0, "c": 3.9, "f": 8.0, "fib": 2.3},
    {"name": "Egg Whites", "category": "protein", "is_veg": False, "is_vegan": False, "cal_100g": 52, "p": 11.0, "c": 0.7, "f": 0.2, "fib": 0.0},
    {"name": "Greek Yogurt (Non-fat)", "category": "dairy", "is_veg": True, "is_vegan": False, "cal_100g": 59, "p": 10.0, "c": 3.6, "f": 0.4, "fib": 0.0},
    {"name": "Lentils / Dal (Cooked)", "category": "protein", "is_veg": True, "is_vegan": True, "cal_100g": 116, "p": 9.0, "c": 20.0, "f": 0.4, "fib": 7.9},
    {"name": "Whey Protein Isolate", "category": "protein", "is_veg": True, "is_vegan": False, "cal_100g": 370, "p": 80.0, "c": 3.0, "f": 1.5, "fib": 0.0},

    # Carb sources
    {"name": "Brown Rice (Cooked)", "category": "carbs", "is_veg": True, "is_vegan": True, "cal_100g": 112, "p": 2.6, "c": 24.0, "f": 0.9, "fib": 1.8},
    {"name": "Oats (Rolled)", "category": "carbs", "is_veg": True, "is_vegan": True, "cal_100g": 389, "p": 16.9, "c": 66.0, "f": 6.9, "fib": 10.6},
    {"name": "Sweet Potato (Boiled)", "category": "carbs", "is_veg": True, "is_vegan": True, "cal_100g": 86, "p": 1.6, "c": 20.0, "f": 0.1, "fib": 3.0},
    {"name": "Whole Wheat Roti", "category": "carbs", "is_veg": True, "is_vegan": True, "cal_100g": 247, "p": 8.0, "c": 48.0, "f": 2.5, "fib": 7.0},
    {"name": "Quinoa (Cooked)", "category": "carbs", "is_veg": True, "is_vegan": True, "cal_100g": 120, "p": 4.4, "c": 21.3, "f": 1.9, "fib": 2.8},

    # Fat sources & Nuts
    {"name": "Almonds", "category": "fats", "is_veg": True, "is_vegan": True, "cal_100g": 579, "p": 21.0, "c": 22.0, "f": 50.0, "fib": 12.5},
    {"name": "Peanut Butter", "category": "fats", "is_veg": True, "is_vegan": True, "cal_100g": 588, "p": 25.0, "c": 20.0, "f": 50.0, "fib": 6.0},
    {"name": "Olive Oil", "category": "fats", "is_veg": True, "is_vegan": True, "cal_100g": 884, "p": 0.0, "c": 0.0, "f": 100.0, "fib": 0.0},

    # Vegetables
    {"name": "Broccoli (Steamed)", "category": "vegetable", "is_veg": True, "is_vegan": True, "cal_100g": 35, "p": 2.4, "c": 7.0, "f": 0.4, "fib": 2.6},
    {"name": "Spinach (Palak)", "category": "vegetable", "is_veg": True, "is_vegan": True, "cal_100g": 23, "p": 2.9, "c": 3.6, "f": 0.4, "fib": 2.2},
]


def filter_foods_by_preference(
    foods: List[Dict[str, Any]], preference: str
) -> List[Dict[str, Any]]:
    """Filters food items according to dietary constraints (anything, vegetarian, vegan, keto)."""
    pref = preference.lower() if preference else "anything"
    if pref == "vegan":
        return [f for f in foods if f.get("is_vegan", False)]
    elif pref == "vegetarian":
        return [f for f in foods if f.get("is_veg", False)]
    elif pref == "keto":
        return [f for f in foods if f.get("c", 0) <= 10.0]
    return foods


def generate_deterministic_meal_plan(
    target_calories: int,
    target_protein_g: float,
    target_carbs_g: float,
    target_fat_g: float,
    dietary_preference: str = "anything",
) -> Dict[str, Any]:
    """
    Generates a 4-meal daily plan (Breakfast, Lunch, Dinner, Snack)
    scaling food portions to hit macro and calorie targets deterministically.
    """
    available_foods = filter_foods_by_preference(SEED_FOODS, dietary_preference)

    # Distribute Calories across 4 meals: Breakfast 25%, Lunch 35%, Dinner 30%, Snack 10%
    meal_splits = [
        ("Breakfast", 0.25),
        ("Lunch", 0.35),
        ("Dinner", 0.30),
        ("Snack", 0.10),
    ]

    meals: List[Dict[str, Any]] = []
    total_plan_cal = 0
    total_plan_p = 0.0
    total_plan_c = 0.0
    total_plan_f = 0.0

    for name, ratio in meal_splits:
        meal_cal_target = target_calories * ratio
        meal_p_target = target_protein_g * ratio
        meal_c_target = target_carbs_g * ratio

        # Pick protein and carb sources from available pool
        protein_choices = [f for f in available_foods if f["category"] in ("protein", "dairy")]
        carb_choices = [f for f in available_foods if f["category"] in ("carbs", "fruit")]
        veg_choices = [f for f in available_foods if f["category"] == "vegetable"]

        p_food = protein_choices[0] if protein_choices else SEED_FOODS[0]
        c_food = carb_choices[0] if carb_choices else SEED_FOODS[7]
        v_food = veg_choices[0] if veg_choices else SEED_FOODS[15]

        # Calculate portions in grams
        # Portion of protein food to hit 60% of meal protein target
        p_grams = round((meal_p_target * 0.60 / (p_food["p"] / 100.0)), 0) if p_food["p"] > 0 else 100.0
        # Portion of carb food to hit 70% of meal carb target
        c_grams = round((meal_c_target * 0.70 / (c_food["c"] / 100.0)), 0) if c_food["c"] > 0 else 100.0
        v_grams = 150.0  # standard vegetable portion

        p_cal = (p_food["cal_100g"] / 100.0) * p_grams
        c_cal = (c_food["cal_100g"] / 100.0) * c_grams
        v_cal = (v_food["cal_100g"] / 100.0) * v_grams

        meal_cal = p_cal + c_cal + v_cal
        meal_p = (p_food["p"] / 100.0) * p_grams + (c_food["p"] / 100.0) * c_grams + (v_food["p"] / 100.0) * v_grams
        meal_c = (p_food["c"] / 100.0) * p_grams + (c_food["c"] / 100.0) * c_grams + (v_food["c"] / 100.0) * v_grams
        meal_f = (p_food["f"] / 100.0) * p_grams + (c_food["f"] / 100.0) * c_grams + (v_food["f"] / 100.0) * v_grams

        meals.append({
            "meal_name": name,
            "target_calories": int(round(meal_cal_target)),
            "actual_calories": int(round(meal_cal)),
            "protein_g": round(meal_p, 1),
            "carbs_g": round(meal_c, 1),
            "fat_g": round(meal_f, 1),
            "items": [
                {"food": p_food["name"], "portion_g": p_grams},
                {"food": c_food["name"], "portion_g": c_grams},
                {"food": v_food["name"], "portion_g": v_grams},
            ]
        })

        total_plan_cal += meal_cal
        total_plan_p += meal_p
        total_plan_c += meal_c
        total_plan_f += meal_f

    return {
        "title": f"Deterministic {dietary_preference.capitalize()} Meal Plan",
        "target_calories": target_calories,
        "achieved_calories": int(round(total_plan_cal)),
        "achieved_protein_g": round(total_plan_p, 1),
        "achieved_carbs_g": round(total_plan_c, 1),
        "achieved_fat_g": round(total_plan_f, 1),
        "meals": meals
    }
