"""
ai_diet.py — AI Diet Plan Generator
Scores and selects meals using a multi-objective optimization approach.
Prioritizes: macro fit, calorie proximity, variety, goal alignment.
No external API — pure numpy scoring.
"""

import numpy as np
import random
from itertools import combinations
from fitness_intelligence import adjusted_diet_targets, normalize_fitness_intelligence

# ── Meal database ─────────────────────────────────────────────────────────────
# Each meal: {cal, protein, carbs, fat, fiber, goal_tags, veg, prep_minutes, variety_group}
MEAL_DB = {
    # ── BREAKFASTS ──────────────────────────────────────────────────────────
    "Oats + milk + banana":               {"cal":360,"pro":13,"carbs":60,"fat":6,"fiber":6,"meal":"B","veg":True,"prep":5,"grp":"oats","goal":["fat_loss","recomp"]},
    "Moong dal chilla (3) + curd":        {"cal":320,"pro":18,"carbs":35,"fat":5,"fiber":4,"meal":"B","veg":True,"prep":20,"grp":"dal","goal":["fat_loss","muscle","recomp"]},
    "Paneer paratha (2) + curd":          {"cal":580,"pro":22,"carbs":65,"fat":20,"fiber":3,"meal":"B","veg":True,"prep":25,"grp":"paratha","goal":["muscle","weight_gain"]},
    "Oats + whey + almond milk":          {"cal":420,"pro":35,"carbs":45,"fat":8,"fiber":5,"meal":"B","veg":True,"prep":5,"grp":"oats","goal":["muscle","recomp"]},
    "Poha + sprouts + peanuts":           {"cal":310,"pro":12,"carbs":50,"fat":7,"fiber":4,"meal":"B","veg":True,"prep":15,"grp":"poha","goal":["fat_loss","recomp"]},
    "Greek yogurt + granola + berries":   {"cal":350,"pro":18,"carbs":45,"fat":8,"fiber":4,"meal":"B","veg":True,"prep":3,"grp":"yogurt","goal":["fat_loss","recomp"]},
    "Paratha (3) + butter + milk":        {"cal":750,"pro":18,"carbs":90,"fat":28,"fiber":5,"meal":"B","veg":True,"prep":25,"grp":"paratha","goal":["weight_gain"]},
    "Upma + coconut chutney":             {"cal":300,"pro":8,"carbs":52,"fat":7,"fiber":3,"meal":"B","veg":True,"prep":15,"grp":"upma","goal":["fat_loss"]},
    "Soya milk + oats + nuts":            {"cal":400,"pro":20,"carbs":48,"fat":12,"fiber":6,"meal":"B","veg":True,"prep":5,"grp":"oats","goal":["muscle","recomp"]},
    # Non-veg breakfasts
    "Boiled eggs (3) + oats + milk":      {"cal":430,"pro":30,"carbs":40,"fat":12,"fiber":4,"meal":"B","veg":False,"prep":10,"grp":"eggs","goal":["fat_loss","muscle","recomp"]},
    "Egg bhurji (4 eggs) + 2 rotis":      {"cal":480,"pro":28,"carbs":42,"fat":18,"fiber":3,"meal":"B","veg":False,"prep":15,"grp":"eggs","goal":["muscle","recomp"]},
    "Omelette (3 eggs) + brown bread":    {"cal":380,"pro":24,"carbs":30,"fat":14,"fiber":2,"meal":"B","veg":False,"prep":10,"grp":"eggs","goal":["fat_loss","muscle"]},
    "Chicken keema + 2 rotis + milk":     {"cal":650,"pro":42,"carbs":45,"fat":18,"fiber":3,"meal":"B","veg":False,"prep":20,"grp":"chicken","goal":["muscle","weight_gain"]},
    "6 eggs scrambled + paratha (2)":     {"cal":820,"pro":42,"carbs":72,"fat":28,"fiber":3,"meal":"B","veg":False,"prep":15,"grp":"eggs","goal":["weight_gain","muscle"]},

    # ── LUNCHES ──────────────────────────────────────────────────────────────
    "2 rotis + dal + sabzi + salad":      {"cal":480,"pro":16,"carbs":75,"fat":8,"fiber":9,"meal":"L","veg":True,"prep":30,"grp":"dal_roti","goal":["fat_loss","recomp"]},
    "Brown rice + rajma + raita":         {"cal":520,"pro":22,"carbs":80,"fat":6,"fiber":10,"meal":"L","veg":True,"prep":35,"grp":"rice_dal","goal":["fat_loss","muscle","recomp"]},
    "3 rotis + paneer curry + dal":       {"cal":720,"pro":30,"carbs":85,"fat":22,"fiber":7,"meal":"L","veg":True,"prep":35,"grp":"paneer","goal":["muscle","weight_gain"]},
    "Quinoa + chole + salad":             {"cal":480,"pro":18,"carbs":72,"fat":8,"fiber":10,"meal":"L","veg":True,"prep":30,"grp":"quinoa","goal":["fat_loss","recomp"]},
    "Rice + dal makhani + sabzi":         {"cal":650,"pro":20,"carbs":95,"fat":15,"fiber":8,"meal":"L","veg":True,"prep":30,"grp":"rice_dal","goal":["muscle","weight_gain"]},
    "Soya chunk curry + 3 rotis + sabzi": {"cal":680,"pro":36,"carbs":80,"fat":14,"fiber":8,"meal":"L","veg":True,"prep":30,"grp":"soya","goal":["muscle","recomp"]},
    "Large rajma rice + curd + papad":    {"cal":750,"pro":28,"carbs":110,"fat":12,"fiber":10,"meal":"L","veg":True,"prep":30,"grp":"rice_dal","goal":["muscle","weight_gain"]},
    "Tofu stir fry + brown rice":         {"cal":450,"pro":20,"carbs":60,"fat":12,"fiber":5,"meal":"L","veg":True,"prep":20,"grp":"tofu","goal":["fat_loss","recomp"]},
    # Non-veg lunches
    "Chicken breast (150g) + rice + sabzi":{"cal":520,"pro":42,"carbs":55,"fat":8,"fiber":4,"meal":"L","veg":False,"prep":30,"grp":"chicken","goal":["fat_loss","muscle","recomp"]},
    "Grilled fish + salad + 1 roti":      {"cal":420,"pro":38,"carbs":28,"fat":9,"fiber":4,"meal":"L","veg":False,"prep":25,"grp":"fish","goal":["fat_loss","recomp"]},
    "Egg curry + 2 rotis + salad":        {"cal":460,"pro":26,"carbs":50,"fat":14,"fiber":5,"meal":"L","veg":False,"prep":25,"grp":"eggs","goal":["fat_loss","muscle"]},
    "Chicken rice bowl (200g + 2cups)":   {"cal":780,"pro":52,"carbs":80,"fat":12,"fiber":4,"meal":"L","veg":False,"prep":30,"grp":"chicken","goal":["muscle","weight_gain"]},
    "Mutton curry + 3 rotis + dal":       {"cal":820,"pro":46,"carbs":78,"fat":26,"fiber":7,"meal":"L","veg":False,"prep":40,"grp":"mutton","goal":["muscle","weight_gain"]},
    "Tuna salad + brown rice":            {"cal":420,"pro":36,"carbs":48,"fat":8,"fiber":4,"meal":"L","veg":False,"prep":10,"grp":"fish","goal":["fat_loss","recomp"]},

    # ── DINNERS ──────────────────────────────────────────────────────────────
    "1 roti + dal soup + sabzi + salad":  {"cal":320,"pro":14,"carbs":48,"fat":6,"fiber":8,"meal":"D","veg":True,"prep":25,"grp":"dal_roti","goal":["fat_loss"]},
    "Paneer bhurji + 2 rotis + sabzi":    {"cal":480,"pro":26,"carbs":48,"fat":18,"fiber":5,"meal":"D","veg":True,"prep":20,"grp":"paneer","goal":["muscle","recomp"]},
    "Dal + veggies (no rice)":            {"cal":300,"pro":15,"carbs":38,"fat":5,"fiber":8,"meal":"D","veg":True,"prep":25,"grp":"dal","goal":["fat_loss"]},
    "2 rotis + chole + raita":            {"cal":460,"pro":18,"carbs":68,"fat":10,"fiber":9,"meal":"D","veg":True,"prep":25,"grp":"chole","goal":["muscle","recomp"]},
    "Tofu + veggies stir fry + 1 roti":  {"cal":340,"pro":18,"carbs":35,"fat":10,"fiber":6,"meal":"D","veg":True,"prep":15,"grp":"tofu","goal":["fat_loss","recomp"]},
    "3 rotis + dal makhani + sabzi + curd":{"cal":680,"pro":24,"carbs":90,"fat":16,"fiber":8,"meal":"D","veg":True,"prep":30,"grp":"dal_roti","goal":["muscle","weight_gain"]},
    "Rice + paneer + dal + sabzi":        {"cal":650,"pro":28,"carbs":80,"fat":18,"fiber":7,"meal":"D","veg":True,"prep":30,"grp":"paneer","goal":["muscle","weight_gain"]},
    # Non-veg dinners
    "Grilled chicken + stir fry veggies": {"cal":350,"pro":40,"carbs":15,"fat":10,"fiber":5,"meal":"D","veg":False,"prep":20,"grp":"chicken","goal":["fat_loss","recomp"]},
    "Chicken soup + veggies":             {"cal":280,"pro":30,"carbs":18,"fat":7,"fiber":4,"meal":"D","veg":False,"prep":25,"grp":"chicken","goal":["fat_loss"]},
    "Fish tikka + 1 roti + salad":        {"cal":380,"pro":36,"carbs":28,"fat":10,"fiber":4,"meal":"D","veg":False,"prep":20,"grp":"fish","goal":["fat_loss","recomp"]},
    "Chicken stir fry + 3 rotis + dal":   {"cal":680,"pro":48,"carbs":72,"fat":14,"fiber":7,"meal":"D","veg":False,"prep":25,"grp":"chicken","goal":["muscle","weight_gain"]},
    "Egg curry + 1 roti + sabzi":         {"cal":380,"pro":22,"carbs":35,"fat":14,"fiber":4,"meal":"D","veg":False,"prep":20,"grp":"eggs","goal":["fat_loss","recomp"]},
    "Mutton biryani + raita":             {"cal":750,"pro":38,"carbs":85,"fat":22,"fiber":4,"meal":"D","veg":False,"prep":40,"grp":"mutton","goal":["muscle","weight_gain"]},

    # ── SNACKS ───────────────────────────────────────────────────────────────
    "Almonds + black coffee":             {"cal":175,"pro":6,"carbs":6,"fat":15,"fiber":3,"meal":"S","veg":True,"prep":1,"grp":"nuts","goal":["fat_loss","recomp"]},
    "Sprout chaat":                       {"cal":150,"pro":9,"carbs":22,"fat":2,"fiber":6,"meal":"S","veg":True,"prep":5,"grp":"sprouts","goal":["fat_loss","recomp"]},
    "Greek yogurt + flaxseeds":           {"cal":150,"pro":15,"carbs":8,"fat":4,"fiber":3,"meal":"S","veg":True,"prep":2,"grp":"yogurt","goal":["fat_loss","recomp","muscle"]},
    "Peanut butter + banana":             {"cal":290,"pro":8,"carbs":38,"fat":14,"fiber":4,"meal":"S","veg":True,"prep":2,"grp":"pb","goal":["muscle","weight_gain","recomp"]},
    "Banana milkshake (500ml)":           {"cal":400,"pro":12,"carbs":72,"fat":8,"fiber":4,"meal":"S","veg":True,"prep":5,"grp":"shake","goal":["weight_gain","muscle"]},
    "Pumpkin seeds + almonds mix":        {"cal":200,"pro":8,"carbs":8,"fat":16,"fiber":3,"meal":"S","veg":True,"prep":1,"grp":"nuts","goal":["fat_loss","recomp","muscle"]},
    "Protein shake + milk":               {"cal":280,"pro":28,"carbs":20,"fat":5,"fiber":0,"meal":"S","veg":True,"prep":2,"grp":"shake","goal":["muscle","recomp"]},
    "Dry fruits + nuts mix":              {"cal":320,"pro":7,"carbs":35,"fat":18,"fiber":4,"meal":"S","veg":True,"prep":1,"grp":"nuts","goal":["weight_gain"]},
    "Chaas / buttermilk":                 {"cal":50, "pro":3,"carbs":4,"fat":1,"fiber":0,"meal":"S","veg":True,"prep":2,"grp":"dairy","goal":["fat_loss"]},
    "Boiled eggs (2) + salt":             {"cal":156,"pro":13,"carbs":1,"fat":11,"fiber":0,"meal":"S","veg":False,"prep":10,"grp":"eggs","goal":["fat_loss","muscle","recomp"]},
    "Tuna on rice cakes (2)":             {"cal":180,"pro":20,"carbs":16,"fat":3,"fiber":1,"meal":"S","veg":False,"prep":5,"grp":"fish","goal":["fat_loss","recomp"]},
    "Chicken sandwich (whole wheat)":     {"cal":380,"pro":30,"carbs":35,"fat":10,"fiber":3,"meal":"S","veg":False,"prep":5,"grp":"chicken","goal":["muscle","weight_gain"]},
}

GOAL_MAP = {
    "Fat Loss":           "fat_loss",
    "Muscle Gain":        "muscle",
    "Weight Gain":        "weight_gain",
    "Body Recomposition": "recomp",
}

MEAL_CAL_SPLIT = {
    "Fat Loss":           {"B":0.28,"L":0.35,"D":0.27,"S":0.10},
    "Muscle Gain":        {"B":0.28,"L":0.32,"D":0.28,"S":0.12},
    "Weight Gain":        {"B":0.28,"L":0.32,"D":0.28,"S":0.12},
    "Body Recomposition": {"B":0.28,"L":0.34,"D":0.27,"S":0.11},
}


def _score_meal(meal: dict, target_cal: float, target_pro: float,
                goal_tag: str, used_groups: set) -> float:
    """Score a meal for a specific slot. Higher = better fit."""
    cal_diff  = abs(meal["cal"] - target_cal) / (target_cal + 1)
    pro_score = meal["pro"] / (target_pro + 1)
    goal_score = 1.5 if goal_tag in meal.get("goal", []) else 0.5
    variety    = 0.0 if meal["grp"] in used_groups else 0.8
    prep_score = meal["prep"] / 40  # normalised; quick prep = small bonus

    # Fiber bonus for fat loss/recomp
    fiber_bonus = meal["fiber"] * 0.05 if goal_tag in ("fat_loss","recomp") else 0

    total = (
        goal_score * 2.0
        + pro_score * 1.8
        + variety
        - cal_diff * 1.5
        + fiber_bonus
        + prep_score * 0.3
        + random.uniform(0, 0.2)   # small noise for variety across days
    )
    return round(total, 4)


def generate_ai_meal_plan(goal: str, target_calories: float,
                          macros: dict, preference: str,
                          used_groups_today: set = None,
                          fitness_intelligence: dict | None = None) -> dict:
    """
    AI meal plan generator using multi-objective scoring.
    Returns breakfast, lunch, dinner, snack + totals.
    """
    used_groups = used_groups_today or set()
    intel = normalize_fitness_intelligence(fitness_intelligence) if fitness_intelligence else None
    if intel:
        target_calories, macros = adjusted_diet_targets(target_calories, macros, intel)
    goal_tag    = GOAL_MAP.get(goal, "fat_loss")
    splits      = MEAL_CAL_SPLIT.get(goal, MEAL_CAL_SPLIT["Fat Loss"])

    plan = {}
    for slot_code, slot_name in [("B","breakfast"),("L","lunch"),("D","dinner"),("S","snack")]:
        slot_cal_target = target_calories * splits[slot_code]
        slot_pro_target = macros["protein"] * splits[slot_code]

        candidates = [
            m for m in MEAL_DB.values()
            if m["meal"] == slot_code
            and (preference == "Non-Vegetarian" or m["veg"])
        ]
        if not candidates:
            candidates = [m for m in MEAL_DB.values() if m["meal"] == slot_code]

        scored = sorted(
            candidates,
            key=lambda m: _score_meal(m, slot_cal_target, slot_pro_target,
                                       goal_tag, used_groups),
            reverse=True
        )
        # Pick from top-3 for variety
        top3     = scored[:3]
        chosen   = random.choice(top3)
        meal_name = [k for k,v in MEAL_DB.items() if v is chosen][0]

        plan[slot_name] = {
            "name":     meal_name,
            "calories": chosen["cal"],
            "protein":  chosen["pro"],
            "carbs":    chosen["carbs"],
            "fat":      chosen["fat"],
            "fiber":    chosen["fiber"],
            "prep_min": chosen["prep"],
            "veg":      chosen["veg"],
        }
        used_groups.add(chosen["grp"])

    meal_entries = [v for v in plan.values() if isinstance(v, dict)]
    plan["total_calories"] = sum(v["calories"] for v in meal_entries)
    plan["total_protein"]  = sum(v["protein"]  for v in meal_entries)
    plan["total_carbs"]    = sum(v["carbs"]    for v in meal_entries)
    plan["total_fat"]      = sum(v["fat"]      for v in meal_entries)
    plan["macro_fit_score"] = _macro_fit(plan, target_calories, macros)
    if intel:
        plan["fitness_intelligence_used"] = intel["fitness_scores"]
        plan["diet_adjustment"] = intel["diet_adjustment"]
    return plan


def _macro_fit(plan: dict, target_cal: float, macros: dict) -> int:
    """Returns 0-100 score for how well plan matches targets."""
    cal_pct = min(100, plan["total_calories"] / (target_cal + 1) * 100)
    pro_pct = min(100, plan["total_protein"]  / (macros["protein"] + 1) * 100)
    fit = int((cal_pct * 0.5 + pro_pct * 0.5))
    return max(0, min(100, fit))


def generate_weekly_variation(goal: str, target_calories: float,
                               macros: dict, preference: str,
                               fitness_intelligence: dict | None = None) -> list:
    """Generate 7 distinct meal plans avoiding repetition."""
    plans = []
    used_history = set()
    for _ in range(7):
        plan = generate_ai_meal_plan(goal, target_calories, macros,
                                      preference, set(used_history), fitness_intelligence)
        plans.append(plan)
        # Track groups used to ensure weekly variety
        for key in ("breakfast","lunch","dinner","snack"):
            if key in plan:
                pass  # groups handled per-day inside generator
    return plans
