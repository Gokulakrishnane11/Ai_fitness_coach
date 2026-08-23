"""
ai_food.py — AI-Based Food Recommendation System
Uses content-based filtering with cosine similarity on nutrient vectors.
No external API required — pure scikit-learn + numpy.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

# ── Complete food database ────────────────────────────────────────────────────
# name: {cal, protein, carbs, fat, fiber, iron, calcium, vit_d, b12, magnesium, zinc, cost, prep_ease}
# cost: 1=very cheap, 5=expensive | prep_ease: 1=hard, 5=very easy
FOOD_DATABASE = {
    # Vegetarian protein sources
    "paneer (100g)":            {"cal":265,"protein":18,"carbs":1.2,"fat":20,"fiber":0,"iron":0.4,"calcium":208,"vit_d":0,"b12":0.3,"magnesium":8,"zinc":2.9,"cost":3,"prep":4,"veg":True,"tags":["high_protein","high_fat","muscle_gain","recomp"]},
    "tofu (100g)":              {"cal":76, "protein":8, "carbs":2,  "fat":4, "fiber":0.3,"iron":1.8,"calcium":350,"vit_d":0,"b12":0,"magnesium":30,"zinc":0.8,"cost":3,"prep":3,"veg":True,"tags":["high_protein","low_cal","fat_loss","recomp"]},
    "moong dal cooked (100g)":  {"cal":105,"protein":7,"carbs":18, "fat":0.4,"fiber":4, "iron":1.4,"calcium":27,"vit_d":0,"b12":0,"magnesium":48,"zinc":1,"cost":1,"prep":3,"veg":True,"tags":["high_fiber","high_protein","fat_loss"]},
    "rajma cooked (100g)":      {"cal":127,"protein":9,"carbs":22, "fat":0.5,"fiber":7, "iron":2.9,"calcium":43,"vit_d":0,"b12":0,"magnesium":45,"zinc":1.8,"cost":1,"prep":2,"veg":True,"tags":["high_fiber","high_protein","muscle_gain"]},
    "chickpeas cooked (100g)":  {"cal":164,"protein":9,"carbs":27, "fat":2.6,"fiber":7.6,"iron":2.9,"calcium":49,"vit_d":0,"b12":0,"magnesium":48,"zinc":1.5,"cost":1,"prep":2,"veg":True,"tags":["high_fiber","high_protein"]},
    "soya chunks dry (30g)":    {"cal":102,"protein":15,"carbs":6, "fat":0.5,"fiber":4, "iron":3,"calcium":75,"vit_d":0,"b12":0,"magnesium":60,"zinc":2,"cost":1,"prep":3,"veg":True,"tags":["very_high_protein","muscle_gain","cheap"]},
    "greek yogurt (100g)":      {"cal":59, "protein":10,"carbs":3.6,"fat":0.4,"fiber":0,"iron":0,"calcium":110,"vit_d":0,"b12":0.5,"magnesium":11,"zinc":0.5,"cost":3,"prep":5,"veg":True,"tags":["high_protein","gut_health","fat_loss"]},
    "curd dahi (100g)":         {"cal":60, "protein":3.5,"carbs":4.7,"fat":3.2,"fiber":0,"iron":0.1,"calcium":121,"vit_d":0,"b12":0.4,"magnesium":12,"zinc":0.5,"cost":1,"prep":5,"veg":True,"tags":["gut_health","calcium_rich"]},
    "milk full fat (200ml)":    {"cal":136,"protein":6.8,"carbs":10,"fat":7.6,"fiber":0,"iron":0,"calcium":240,"vit_d":2,"b12":0.9,"magnesium":20,"zinc":0.9,"cost":1,"prep":5,"veg":True,"tags":["calcium_rich","muscle_gain","weight_gain"]},
    "whey protein (30g)":       {"cal":120,"protein":24,"carbs":3, "fat":1.5,"fiber":0,"iron":0,"calcium":150,"vit_d":0,"b12":0,"magnesium":30,"zinc":1,"cost":5,"prep":5,"veg":True,"tags":["very_high_protein","post_workout"]},
    # Grains & carbs
    "oats dry (40g)":           {"cal":152,"protein":5.2,"carbs":26,"fat":3, "fiber":4, "iron":1.7,"calcium":16,"vit_d":0,"b12":0,"magnesium":50,"zinc":1.2,"cost":2,"prep":5,"veg":True,"tags":["high_fiber","slow_carb","fat_loss"]},
    "brown rice cooked (150g)": {"cal":165,"protein":3.5,"carbs":34,"fat":1.3,"fiber":1.8,"iron":0.8,"calcium":10,"vit_d":0,"b12":0,"magnesium":43,"zinc":0.8,"cost":2,"prep":3,"veg":True,"tags":["slow_carb","muscle_gain"]},
    "white rice cooked (150g)": {"cal":195,"protein":3.6,"carbs":43,"fat":0.3,"fiber":0.6,"iron":0.2,"calcium":9, "vit_d":0,"b12":0,"magnesium":12,"zinc":0.6,"cost":1,"prep":3,"veg":True,"tags":["fast_carb","weight_gain","post_workout"]},
    "whole wheat roti (1 roti)": {"cal":100,"protein":3,"carbs":20, "fat":0.9,"fiber":2, "iron":1,"calcium":11,"vit_d":0,"b12":0,"magnesium":25,"zinc":0.7,"cost":1,"prep":3,"veg":True,"tags":["fiber","staple"]},
    "sweet potato (100g)":      {"cal":86, "protein":1.6,"carbs":20,"fat":0.1,"fiber":3, "iron":0.6,"calcium":30,"vit_d":0,"b12":0,"magnesium":25,"zinc":0.3,"cost":1,"prep":3,"veg":True,"tags":["complex_carb","high_fiber","fat_loss"]},
    "banana medium (120g)":     {"cal":107,"protein":1.3,"carbs":27,"fat":0.4,"fiber":3.1,"iron":0.3,"calcium":6, "vit_d":0,"b12":0,"magnesium":32,"zinc":0.2,"cost":1,"prep":5,"veg":True,"tags":["quick_carb","pre_workout","weight_gain"]},
    # Fats & nuts
    "almonds (30g)":            {"cal":173,"protein":6,"carbs":6,  "fat":15,"fiber":3.5,"iron":1,"calcium":75,"vit_d":0,"b12":0,"magnesium":76,"zinc":0.9,"cost":4,"prep":5,"veg":True,"tags":["healthy_fat","magnesium_rich","snack"]},
    "peanut butter (2tbsp=32g)":{"cal":192,"protein":7,"carbs":7,  "fat":16,"fiber":1.6,"iron":0.6,"calcium":17,"vit_d":0,"b12":0,"magnesium":49,"zinc":0.9,"cost":2,"prep":5,"veg":True,"tags":["calorie_dense","healthy_fat","weight_gain"]},
    "walnuts (30g)":            {"cal":196,"protein":4.6,"carbs":4, "fat":19,"fiber":2, "iron":0.9,"calcium":28,"vit_d":0,"b12":0,"magnesium":44,"zinc":0.9,"cost":4,"prep":5,"veg":True,"tags":["omega3","healthy_fat","brain"]},
    "flaxseeds (1tbsp=10g)":    {"cal":55, "protein":1.9,"carbs":3, "fat":4.3,"fiber":2.8,"iron":0.6,"calcium":26,"vit_d":0,"b12":0,"magnesium":27,"zinc":0.4,"cost":1,"prep":5,"veg":True,"tags":["omega3","fiber","hormone_balance"]},
    # Vegetables
    "spinach (100g)":           {"cal":23, "protein":2.9,"carbs":3.6,"fat":0.4,"fiber":2.2,"iron":2.7,"calcium":99,"vit_d":0,"b12":0,"magnesium":79,"zinc":0.5,"cost":1,"prep":3,"veg":True,"tags":["iron_rich","low_cal","micronutrient"]},
    "broccoli (100g)":          {"cal":34, "protein":2.8,"carbs":7, "fat":0.4,"fiber":2.6,"iron":0.7,"calcium":47,"vit_d":0,"b12":0,"magnesium":21,"zinc":0.4,"cost":2,"prep":3,"veg":True,"tags":["low_cal","high_fiber","immune"]},
    "mushroom (100g)":          {"cal":22, "protein":3.1,"carbs":3.3,"fat":0.3,"fiber":1, "iron":0.5,"calcium":3,"vit_d":7,"b12":0,"magnesium":9,"zinc":0.5,"cost":2,"prep":3,"veg":True,"tags":["vit_d","low_cal"]},
    "pumpkin seeds (30g)":      {"cal":163,"protein":8.5,"carbs":4.2,"fat":13, "fiber":1.7,"iron":2.8,"calcium":15,"vit_d":0,"b12":0,"magnesium":156,"zinc":2.2,"cost":2,"prep":5,"veg":True,"tags":["zinc_rich","magnesium_rich","snack"]},
    # Non-veg protein
    "chicken breast (100g)":    {"cal":165,"protein":31,"carbs":0, "fat":3.6,"fiber":0,"iron":1,"calcium":15,"vit_d":0,"b12":0.3,"magnesium":29,"zinc":1,"cost":3,"prep":2,"veg":False,"tags":["very_high_protein","lean","muscle_gain","fat_loss"]},
    "egg whole (1=50g)":        {"cal":78, "protein":6,"carbs":0.6,"fat":5, "fiber":0,"iron":0.9,"calcium":28,"vit_d":44,"b12":0.6,"magnesium":6,"zinc":0.6,"cost":1,"prep":5,"veg":False,"tags":["complete_protein","vit_d","cheap"]},
    "egg white (1=35g)":        {"cal":17, "protein":3.6,"carbs":0.2,"fat":0.1,"fiber":0,"iron":0,"calcium":2,"vit_d":0,"b12":0,"magnesium":4,"zinc":0,"cost":1,"prep":5,"veg":False,"tags":["high_protein","low_cal","fat_loss"]},
    "tuna canned (100g)":       {"cal":132,"protein":28,"carbs":0, "fat":2, "fiber":0,"iron":1.3,"calcium":17,"vit_d":68,"b12":2.5,"magnesium":31,"zinc":0.9,"cost":3,"prep":5,"veg":False,"tags":["very_high_protein","omega3","b12"]},
    "salmon (100g)":            {"cal":208,"protein":20,"carbs":0, "fat":13, "fiber":0,"iron":0.8,"calcium":12,"vit_d":447,"b12":3.2,"magnesium":29,"zinc":0.6,"cost":5,"prep":2,"veg":False,"tags":["omega3","vit_d","b12","premium"]},
    "rohu fish (100g)":         {"cal":97, "protein":16,"carbs":0, "fat":3, "fiber":0,"iron":1,"calcium":30,"vit_d":100,"b12":2,"magnesium":25,"zinc":0.8,"cost":2,"prep":2,"veg":False,"tags":["lean_protein","vit_d","affordable"]},
    "mutton (100g)":            {"cal":294,"protein":25,"carbs":0, "fat":21, "fiber":0,"iron":2.7,"calcium":13,"vit_d":0,"b12":2.2,"magnesium":22,"zinc":4.5,"cost":4,"prep":2,"veg":False,"tags":["zinc_rich","iron_rich","b12","muscle_gain"]},
    "chicken liver (50g)":      {"cal":81, "protein":12,"carbs":1, "fat":3.4,"fiber":0,"iron":5,"calcium":4,"vit_d":0,"b12":28,"magnesium":11,"zinc":1.8,"cost":1,"prep":2,"veg":False,"tags":["iron_rich","b12_very_high","cheap"]},
}

GOAL_NUTRIENT_WEIGHTS = {
    "Fat Loss":           {"protein":2.5, "fiber":2.0, "cal":-1.5, "fat":-0.5, "carbs":-0.5},
    "Muscle Gain":        {"protein":3.0, "cal":1.5,   "carbs":1.0,"fat":0.5,  "fiber":0.5},
    "Weight Gain":        {"cal":2.5,     "protein":1.5,"carbs":1.5,"fat":1.0, "fiber":0.0},
    "Body Recomposition": {"protein":3.0, "fiber":1.5, "cal":0.0,  "fat":0.5,  "carbs":0.5},
}

MICRO_DEFICIT_BOOST = {
    "iron":      ["spinach (100g)","chicken liver (50g)","pumpkin seeds (30g)","rajma cooked (100g)","mutton (100g)"],
    "calcium":   ["milk full fat (200ml)","paneer (100g)","curd dahi (100g)","tofu (100g)","almonds (30g)"],
    "vit_d":     ["egg whole (1=50g)","tuna canned (100g)","salmon (100g)","rohu fish (100g)","mushroom (100g)"],
    "b12":       ["tuna canned (100g)","chicken liver (50g)","egg whole (1=50g)","salmon (100g)","mutton (100g)"],
    "magnesium": ["pumpkin seeds (30g)","almonds (30g)","spinach (100g)","oats dry (40g)","soya chunks dry (30g)"],
    "zinc":      ["mutton (100g)","pumpkin seeds (30g)","soya chunks dry (30g)","chickpeas cooked (100g)","paneer (100g)"],
}


def _build_nutrient_matrix():
    names = list(FOOD_DATABASE.keys())
    features = ["protein","carbs","fat","fiber","iron","calcium","vit_d","b12","magnesium","zinc"]
    matrix = np.array([[FOOD_DATABASE[n][f] for f in features] for n in names], dtype=float)
    scaler = MinMaxScaler()
    matrix_norm = scaler.fit_transform(matrix)
    return names, features, matrix_norm, scaler


def recommend_foods(goal: str, deficits: list, preference: str,
                    consumed: dict = None, top_n: int = 8) -> dict:
    """
    AI content-based filtering: rank foods by cosine similarity to user's need profile.
    Returns top recommendations split by veg/non-veg.
    """
    names, features, matrix_norm, scaler = _build_nutrient_matrix()

    # Build user need vector based on goal weights + micro deficits
    weights = GOAL_NUTRIENT_WEIGHTS.get(goal, GOAL_NUTRIENT_WEIGHTS["Fat Loss"])
    need_vec = np.array([
        max(0, weights.get("protein", 1.0)),
        max(0, weights.get("carbs",   0.5)),
        max(0, weights.get("fat",     0.5)),
        max(0, weights.get("fiber",   1.0)),
        1.0 if "iron"      in deficits else 0.3,
        1.0 if "calcium"   in deficits else 0.3,
        1.0 if "vit_d"     in deficits else 0.3,
        1.0 if "b12"       in deficits else 0.3,
        1.0 if "magnesium" in deficits else 0.3,
        1.0 if "zinc"      in deficits else 0.3,
    ], dtype=float)

    need_vec_norm = need_vec / (np.linalg.norm(need_vec) + 1e-9)
    scores = cosine_similarity(need_vec_norm.reshape(1,-1), matrix_norm)[0]

    # Boost deficit-specific foods
    boosted_names = set()
    for deficit in deficits:
        for fname in MICRO_DEFICIT_BOOST.get(deficit, []):
            boosted_names.add(fname)

    final_scores = {}
    for i, name in enumerate(names):
        food = FOOD_DATABASE[name]
        score = scores[i]
        if name in boosted_names:
            score *= 1.4
        # Affordability boost
        score += (food["cost"] == 1) * 0.05 + (food["cost"] == 2) * 0.02
        # Ease of prep boost
        score += (food["prep"] >= 4) * 0.03
        final_scores[name] = round(float(score), 4)

    sorted_foods = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    veg_recs, nonveg_recs = [], []
    for fname, score in sorted_foods:
        food = FOOD_DATABASE[fname]
        entry = {
            "name":    fname,
            "score":   score,
            "cal":     food["cal"],
            "protein": food["protein"],
            "tags":    food["tags"],
            "cost":    "₹" * food["cost"],
            "prep":    "⚡" * food["prep"],
            "reason":  _reason(fname, goal, deficits, food),
        }
        if food["veg"]:
            veg_recs.append(entry)
        else:
            nonveg_recs.append(entry)

    if preference == "Vegetarian":
        primary, secondary = veg_recs[:top_n], []
    else:
        primary   = nonveg_recs[:top_n//2] + veg_recs[:top_n//2]
        secondary = []

    return {
        "primary":    primary,
        "veg":        veg_recs[:top_n],
        "non_veg":    nonveg_recs[:top_n],
        "deficit_picks": _deficit_picks(deficits, preference),
    }


def _reason(name: str, goal: str, deficits: list, food: dict) -> str:
    tags = food.get("tags", [])
    reasons = []
    if food["protein"] > 15:  reasons.append(f"high protein ({food['protein']}g)")
    if food["fiber"]   > 3:   reasons.append("high fiber")
    if "iron"      in deficits and food["iron"]      > 1:  reasons.append("fixes iron deficit")
    if "calcium"   in deficits and food["calcium"]   > 100: reasons.append("fixes calcium deficit")
    if "vit_d"     in deficits and food["vit_d"]     > 50:  reasons.append("fixes Vitamin D deficit")
    if "b12"       in deficits and food["b12"]       > 1:   reasons.append("fixes B12 deficit")
    if "magnesium" in deficits and food["magnesium"] > 50:  reasons.append("fixes magnesium deficit")
    if "zinc"      in deficits and food["zinc"]      > 2:   reasons.append("fixes zinc deficit")
    if goal == "Fat Loss"    and food["cal"] < 100:  reasons.append("low calorie")
    if goal == "Weight Gain" and food["cal"] > 150:  reasons.append("calorie dense")
    if food["cost"] == 1: reasons.append("very affordable")
    return ", ".join(reasons) if reasons else "nutrient balanced"


def _deficit_picks(deficits: list, preference: str) -> dict:
    picks = {}
    pref = "Vegetarian"
    for deficit in deficits:
        foods = MICRO_DEFICIT_BOOST.get(deficit, [])
        if preference == "Vegetarian":
            foods = [f for f in foods if FOOD_DATABASE[f]["veg"]]
        picks[deficit] = foods[:3]
    return picks
