"""
Shared Fitness Intelligence state and behavior adapters.

The AI estimates behavior, recovery, and readiness. Scientific calculators
remain responsible for body transformation numbers.
"""

from __future__ import annotations

from copy import deepcopy


DEFAULT_FITNESS_INTELLIGENCE = {
    "sentiment": "neutral",
    "urgency": "low",
    "key_issues": [],
    "fitness_scores": {
        "adherence_score": 90,
        "recovery_score": 80,
        "nutrition_score": 80,
        "training_quality": 80,
        "motivation_score": 80,
        "stress_score": 20,
        "sleep_quality": 80,
        "plateau_probability": 5,
        "injury_risk": 5,
        "confidence_score": 75,
    },
    "diet_adjustment": {
        "protein_delta": 0,
        "calorie_delta": 0,
        "carb_delta": 0,
        "fat_delta": 0,
    },
    "workout_adjustment": {
        "intensity": "maintain",
        "volume": "medium",
        "recovery_days": 0,
        "cardio_minutes": 20,
    },
    "recommendations": [],
    "motivation": "Stay consistent and keep moving forward.",
}


def clamp(value, low=0, high=100, default=0) -> int:
    try:
        return max(low, min(high, int(value)))
    except Exception:
        return default


def normalize_fitness_intelligence(raw: dict | None) -> dict:
    """Return a complete, clamped Fitness Intelligence object."""
    raw = raw if isinstance(raw, dict) else {}
    intel = deepcopy(DEFAULT_FITNESS_INTELLIGENCE)

    for key in ("sentiment", "urgency", "motivation"):
        if raw.get(key):
            intel[key] = raw[key]

    issues = raw.get("key_issues", [])
    intel["key_issues"] = issues if isinstance(issues, list) else []

    recs = raw.get("recommendations", raw.get("action_nudges", []))
    intel["recommendations"] = recs if isinstance(recs, list) else []

    raw_scores = raw.get("fitness_scores", {})
    if not isinstance(raw_scores, dict):
        raw_scores = {}
    for key, default in DEFAULT_FITNESS_INTELLIGENCE["fitness_scores"].items():
        source_value = raw_scores.get(key, raw.get(key, default))
        intel["fitness_scores"][key] = clamp(source_value, default=default)

    confidence = raw.get("confidence_score", raw_scores.get("confidence_score", 75))
    intel["confidence_score"] = clamp(confidence, default=75)
    intel["fitness_scores"]["confidence_score"] = intel["confidence_score"]

    raw_diet = raw.get("diet_adjustment", {})
    if not isinstance(raw_diet, dict):
        raw_diet = {}
    diet_aliases = {
        "protein_delta": ("protein_delta", "protein"),
        "calorie_delta": ("calorie_delta", "calories"),
        "carb_delta": ("carb_delta", "carbs"),
        "fat_delta": ("fat_delta", "fat"),
    }
    for key, aliases in diet_aliases.items():
        value = next((raw_diet[a] for a in aliases if a in raw_diet), intel["diet_adjustment"][key])
        intel["diet_adjustment"][key] = max(-2000, min(2000, int(value or 0)))

    raw_workout = raw.get("workout_adjustment", {})
    if not isinstance(raw_workout, dict):
        raw_workout = {}
    intensity = str(raw_workout.get("intensity", "maintain")).lower()
    intel["workout_adjustment"]["intensity"] = intensity if intensity in ("reduce", "maintain", "increase") else "maintain"
    volume = str(raw_workout.get("volume", "medium")).lower()
    intel["workout_adjustment"]["volume"] = volume if volume in ("low", "medium", "high") else "medium"
    intel["workout_adjustment"]["recovery_days"] = clamp(raw_workout.get("recovery_days", 0), 0, 7)
    intel["workout_adjustment"]["cardio_minutes"] = clamp(raw_workout.get("cardio_minutes", 20), 0, 120, 20)

    intel["score"] = intel["fitness_scores"]["recovery_score"]
    intel["action_nudges"] = intel["recommendations"]
    return intel


def get_session_intelligence(session_state) -> dict:
    return normalize_fitness_intelligence(session_state.get("fitness_intelligence"))


def store_session_intelligence(session_state, intelligence: dict) -> dict:
    intel = normalize_fitness_intelligence(intelligence)
    session_state["fitness_intelligence"] = intel
    session_state["feedback_issues"] = intel["key_issues"]
    session_state["fitness_scores"] = intel["fitness_scores"]
    return intel


def score(intelligence: dict | None, name: str, default: int = 75) -> int:
    intel = normalize_fitness_intelligence(intelligence)
    return intel["fitness_scores"].get(name, default)


def adherence_factor_from_intelligence(intelligence: dict | None, fallback: float = 0.92) -> float:
    if not intelligence:
        return fallback
    return max(0.35, min(1.0, score(intelligence, "adherence_score", int(fallback * 100)) / 100.0))


def prediction_behavior_factor(intelligence: dict | None) -> float:
    """Behavior multiplier for scientific/ML rates. Never creates body numbers."""
    if not intelligence:
        return 1.0
    s = normalize_fitness_intelligence(intelligence)["fitness_scores"]
    readiness = (
        s["adherence_score"] * 0.30
        + s["recovery_score"] * 0.20
        + s["nutrition_score"] * 0.20
        + s["training_quality"] * 0.15
        + s["motivation_score"] * 0.10
        + s["sleep_quality"] * 0.05
    ) / 100.0
    risk_penalty = (s["stress_score"] * 0.10 + s["plateau_probability"] * 0.12 + s["injury_risk"] * 0.12) / 100.0
    return max(0.45, min(1.12, readiness * (1.0 - risk_penalty)))


def adjusted_diet_targets(target_calories: float, macros: dict, intelligence: dict | None) -> tuple[float, dict]:
    intel = normalize_fitness_intelligence(intelligence)
    d = intel["diet_adjustment"]
    s = intel["fitness_scores"]
    calorie_delta = d["calorie_delta"]

    if s["stress_score"] >= 70 and calorie_delta < 0:
        calorie_delta = int(calorie_delta * 0.5)
    if s["plateau_probability"] >= 70 and abs(calorie_delta) < 50:
        calorie_delta = -100

    adjusted = dict(macros)
    adjusted["protein"] = max(0, int(adjusted.get("protein", 0) + d["protein_delta"]))
    adjusted["carbs"] = max(0, int(adjusted.get("carbs", 0) + d["carb_delta"]))
    adjusted["fat"] = max(0, int(adjusted.get("fat", 0) + d["fat_delta"]))
    return max(800, target_calories + calorie_delta), adjusted


def evolve_weekly_intelligence(intelligence: dict | None, week: int, result: dict) -> dict:
    """Simulate behavior drift from sleep, stress, risk, and weekly progress pressure."""
    intel = normalize_fitness_intelligence(intelligence)
    s = intel["fitness_scores"].copy()
    sleep_pressure = max(0, 70 - s["sleep_quality"]) / 10.0
    stress_pressure = max(0, s["stress_score"] - 60) / 12.0
    injury_pressure = max(0, s["injury_risk"] - 50) / 15.0
    plateau_pressure = min(8, week // 4) if s["plateau_probability"] > 45 else 0

    s["recovery_score"] = clamp(s["recovery_score"] - sleep_pressure - stress_pressure - injury_pressure + 1)
    s["motivation_score"] = clamp(s["motivation_score"] - plateau_pressure + (2 if result.get("weekly_rate", 0) > 0 else -1))
    s["nutrition_score"] = clamp(s["nutrition_score"] - (stress_pressure * 0.8) + (1 if s["adherence_score"] > 80 else -1))
    s["adherence_score"] = clamp((s["adherence_score"] * 0.7) + (s["motivation_score"] * 0.2) + (s["nutrition_score"] * 0.1))
    s["plateau_probability"] = clamp(s["plateau_probability"] + (2 if week % 3 == 0 else 0) - (2 if result.get("weekly_rate", 0) > 0.15 else 0))

    intel["fitness_scores"].update(s)
    intel["score"] = intel["fitness_scores"]["recovery_score"]
    return intel
