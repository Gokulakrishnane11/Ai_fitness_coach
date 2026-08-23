"""
ai_workout.py — AI Workout Plan Generator
Uses a Decision Tree trained on goal/experience/feedback features
to select and personalise workout plans.
No external API — scikit-learn DecisionTreeClassifier.
"""

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from fitness_intelligence import normalize_fitness_intelligence

# ── Training data for workout style classifier ───────────────────────────────
# Features: [goal_enc, exp_enc, fatigue(0/1), low_motivation(0/1),
#            injury_risk(0/1), workout_days, stress(0/1)]
# Label: workout_style

TRAINING_DATA = [
    # goal  exp   fat  mot  inj  days stress → style
    (0, 0,  0, 0, 0, 4, 0, "strength_cardio"),
    (0, 0,  1, 0, 0, 3, 0, "light_strength_cardio"),
    (0, 0,  0, 1, 0, 3, 0, "simple_strength"),
    (0, 0,  0, 0, 1, 3, 0, "machine_only"),
    (0, 0,  1, 1, 0, 2, 1, "recovery_walk"),
    (0, 1,  0, 0, 0, 5, 0, "strength_hiit"),
    (0, 1,  1, 0, 0, 3, 0, "deload_cardio"),
    (0, 2,  0, 0, 0, 5, 0, "advanced_cut"),
    (1, 0,  0, 0, 0, 4, 0, "hypertrophy_split"),
    (1, 0,  1, 0, 0, 3, 0, "deload_compound"),
    (1, 0,  0, 1, 0, 4, 0, "simple_compound"),
    (1, 1,  0, 0, 0, 5, 0, "ppl_split"),
    (1, 1,  1, 0, 0, 3, 0, "deload"),
    (1, 2,  0, 0, 0, 6, 0, "advanced_hypertrophy"),
    (1, 0,  0, 0, 1, 3, 0, "upper_machine"),
    (2, 0,  0, 0, 0, 4, 0, "strength_bulk"),
    (2, 0,  1, 0, 0, 3, 0, "light_compound"),
    (2, 1,  0, 0, 0, 4, 0, "strength_bulk"),
    (2, 2,  0, 0, 0, 5, 0, "powerlifting"),
    (3, 0,  0, 0, 0, 4, 0, "recomp_balanced"),
    (3, 0,  1, 0, 0, 3, 0, "light_recomp"),
    (3, 1,  0, 0, 0, 5, 0, "recomp_advanced"),
    (3, 0,  0, 1, 0, 3, 0, "simple_recomp"),
    (3, 1,  1, 1, 0, 2, 1, "recovery_walk"),
]

GOAL_ENC   = {"Fat Loss":0,"Muscle Gain":1,"Weight Gain":2,"Body Recomposition":3}
EXP_ENC    = {"Beginner":0,"Intermediate":1,"Advanced":2}

WORKOUT_TEMPLATES = {
    "strength_cardio": {
        "title": "Strength + Cardio (Fat Loss Focus)",
        "split": "4 days strength · 2 cardio · 1 rest",
        "intensity": "Moderate–High",
        "schedule": {
            "Monday":    ("Upper Push", [("Bench Press / Push-Up","4×10"),("Overhead Press","3×10"),("Tricep Dips","3×12"),("Lateral Raises","3×15"),("Plank","3×45s")], "Strength"),
            "Tuesday":   ("HIIT Cardio", [("Jump Rope / Sprints","20 min"),("Burpees","4×15"),("Mountain Climbers","4×30s"),("Box Jumps","3×12")], "Cardio"),
            "Wednesday": ("Lower Body", [("Squats","4×10"),("Romanian Deadlift","3×10"),("Lunges","3×12 each"),("Calf Raises","3×20")], "Strength"),
            "Thursday":  ("LISS / Active Rest", [("Brisk Walk","30–45 min"),("Stretching","15 min")], "Active Rest"),
            "Friday":    ("Upper Pull", [("Pull-Ups / Lat Pulldown","4×8"),("Bent-Over Row","3×10"),("Face Pulls","3×15"),("Bicep Curl","3×12")], "Strength"),
            "Saturday":  ("Full Body Circuit", [("Deadlift","4×6"),("Push-Up","3×15"),("Goblet Squat","3×12"),("Core Circuit","3 rounds")], "Strength"),
            "Sunday":    ("Rest", [("Full rest","—")], "Rest"),
        },
        "cardio": "2–3 HIIT sessions + 1–2 LISS walks. Avoid excessive cardio.",
        "progression": "Add 2 reps OR 2.5kg every 2 weeks on main lifts.",
        "recovery": ["7–8 hours sleep","High protein post-workout","Foam roll sore muscles"],
    },
    "hypertrophy_split": {
        "title": "Hypertrophy Split (Muscle Gain)",
        "split": "5 days strength · 1 light cardio · 1 rest",
        "intensity": "High",
        "schedule": {
            "Monday":    ("Chest + Triceps", [("Flat Bench Press","4×8"),("Incline DB Press","3×10"),("Cable Fly","3×12"),("Tricep Pushdown","3×12"),("Skull Crushers","3×10")], "Strength"),
            "Tuesday":   ("Back + Biceps", [("Deadlift","4×5"),("Pull-Ups","4×8"),("Barbell Row","3×10"),("Seated Cable Row","3×12"),("Barbell Curl","4×10")], "Strength"),
            "Wednesday": ("Rest / Light Walk", [("Walk 20 min","—"),("Stretching","15 min")], "Active Rest"),
            "Thursday":  ("Legs", [("Barbell Squat","4×8"),("Leg Press","3×12"),("Romanian Deadlift","3×10"),("Leg Curl","3×12"),("Calf Raises","4×15")], "Strength"),
            "Friday":    ("Shoulders + Traps", [("Overhead Press","4×8"),("Arnold Press","3×10"),("Lateral Raise","4×15"),("Face Pull","3×15"),("Shrugs","3×15")], "Strength"),
            "Saturday":  ("Arms + Core", [("Hammer Curl","3×12"),("Preacher Curl","3×10"),("Overhead Tricep Ext","3×12"),("Dips","3×10"),("Weighted Plank","3×45s")], "Strength"),
            "Sunday":    ("Rest", [("Full rest","—")], "Rest"),
        },
        "cardio": "Max 1–2 light cardio sessions (20 min walk). Too much impairs muscle gain.",
        "progression": "Add 2.5–5 kg every week on main compound lifts. Track every session.",
        "recovery": ["8 hours sleep mandatory","Eat within 30 min post-workout","Deload every 4–6 weeks"],
    },
    "ppl_split": {
        "title": "Push-Pull-Legs Split (Intermediate Muscle)",
        "split": "6 days PPL · 1 rest",
        "intensity": "High",
        "schedule": {
            "Monday":    ("Push A", [("Bench Press","4×8"),("Overhead Press","3×10"),("Incline DB","3×10"),("Lateral Raise","3×15"),("Tricep Pushdown","3×12")], "Strength"),
            "Tuesday":   ("Pull A", [("Deadlift","4×5"),("Pull-Ups","4×8"),("Cable Row","3×10"),("Face Pulls","3×15"),("Barbell Curl","3×10")], "Strength"),
            "Wednesday": ("Legs A", [("Squat","4×8"),("Leg Press","3×12"),("Leg Curl","3×12"),("Calf Raises","4×15"),("Abs Circuit","3 rounds")], "Strength"),
            "Thursday":  ("Push B", [("Incline Bench","4×8"),("DB Shoulder Press","3×10"),("Cable Fly","3×12"),("Lateral Raises","4×15"),("Dips","3×10")], "Strength"),
            "Friday":    ("Pull B", [("Barbell Row","4×8"),("Lat Pulldown","3×10"),("Hammer Curl","3×12"),("Rear Delt Fly","3×15"),("Shrugs","3×12")], "Strength"),
            "Saturday":  ("Legs B", [("Front Squat","4×6"),("Romanian DL","3×10"),("Walking Lunges","3×12"),("Leg Extension","3×15"),("Calf Raises","4×20")], "Strength"),
            "Sunday":    ("Rest", [("Full rest","—")], "Rest"),
        },
        "cardio": "Max 1 session per week. Focus is on training volume.",
        "progression": "Progressive overload on every session. Increase by reps first, then weight.",
        "recovery": ["Sleep 8+ hours","Eat at calorie surplus","Active recovery on rest days"],
    },
    "recomp_balanced": {
        "title": "Balanced Recomposition (Fat Loss + Muscle Gain)",
        "split": "4 strength · 2 cardio · 1 rest",
        "intensity": "Moderate",
        "schedule": {
            "Monday":    ("Upper Full", [("Bench Press","4×8"),("Pull-Ups","4×8"),("Overhead Press","3×10"),("DB Row","3×10"),("Core Circuit","3 rounds")], "Strength"),
            "Tuesday":   ("Moderate Cardio", [("Cycling / Elliptical","30 min zone 2"),("Jump Rope","15 min")], "Cardio"),
            "Wednesday": ("Lower", [("Squat","4×8"),("Romanian DL","3×10"),("Bulgarian Split Squat","3×10"),("Glute Bridge","3×15")], "Strength"),
            "Thursday":  ("Mobility / Yoga", [("Yoga / Stretching","30 min")], "Active Rest"),
            "Friday":    ("Push", [("Incline Press","4×8"),("Lateral Raises","4×12"),("Tricep Pushdown","3×12"),("Face Pulls","3×15")], "Strength"),
            "Saturday":  ("Cardio + Core", [("HIIT Circuit","20 min"),("Plank Variations","3×45s"),("Russian Twists","3×20")], "Cardio"),
            "Sunday":    ("Rest", [("Full rest","—")], "Rest"),
        },
        "cardio": "2–3 sessions at moderate intensity. Avoid overtraining — recomp is a slow process.",
        "progression": "Increase weight every 2 weeks. Track body measurements weekly.",
        "recovery": ["High protein diet is critical","7–9 hours sleep","Manage stress — cortisol kills recomp"],
    },
    "strength_bulk": {
        "title": "Strength Bulk (Weight Gain)",
        "split": "4 heavy days · minimal cardio · 3 rest",
        "intensity": "Very High",
        "schedule": {
            "Monday":    ("Push", [("Bench Press","5×5"),("Overhead Press","4×6"),("Incline Press","3×8"),("Tricep Dips","3×10")], "Strength"),
            "Tuesday":   ("Rest + Eat", [("Rest","—")], "Rest"),
            "Wednesday": ("Pull", [("Deadlift","5×5"),("Barbell Row","4×6"),("Pull-Ups","4×6"),("Barbell Curl","3×10")], "Strength"),
            "Thursday":  ("Rest + Eat", [("Rest","—")], "Rest"),
            "Friday":    ("Legs", [("Squat","5×5"),("Leg Press","4×8"),("Romanian DL","3×8"),("Calf Raises","4×15")], "Strength"),
            "Saturday":  ("Full Body", [("Power Clean","4×4"),("DB Press","3×10"),("Cable Row","3×10"),("Front Squat","3×8")], "Strength"),
            "Sunday":    ("Rest", [("Full rest","—")], "Rest"),
        },
        "cardio": "Avoid cardio — burns calories needed for weight gain.",
        "progression": "Prioritize adding weight on squat, bench, deadlift every session.",
        "recovery": ["Never skip meals","Protein shake before bed","9+ hours sleep"],
    },
    "deload": {
        "title": "Deload Week (Fatigue Recovery)",
        "split": "3 light days · 4 rest",
        "intensity": "Low — 60% of normal weights",
        "schedule": {
            "Monday":    ("Light Upper", [("Bench Press (60% weight)","3×8"),("Lat Pulldown","3×10"),("DB Lateral Raise","2×15")], "Light Strength"),
            "Tuesday":   ("Rest", [("Walk 20 min","—")], "Rest"),
            "Wednesday": ("Light Lower", [("Goblet Squat","3×10"),("Leg Press (60%)","3×12"),("Calf Raises","2×15")], "Light Strength"),
            "Thursday":  ("Rest", [("Yoga / Stretch","20 min")], "Rest"),
            "Friday":    ("Light Full Body", [("Push-Up","2×15"),("Dumbbell Row","2×12"),("Bodyweight Squat","2×15")], "Light Strength"),
            "Saturday":  ("Rest", [("Rest","—")], "Rest"),
            "Sunday":    ("Rest", [("Rest","—")], "Rest"),
        },
        "cardio": "Light 20 min walk only. No HIIT this week.",
        "progression": "This week is recovery. Return to normal next week.",
        "recovery": ["Sleep 9 hours","Eat at maintenance","Focus on stretching and mobility"],
    },
    "recovery_walk": {
        "title": "Active Recovery Week",
        "split": "Daily light activity · no lifting",
        "intensity": "Very Low",
        "schedule": {
            "Monday":    ("Light Walk", [("30 min brisk walk","—")], "Active Rest"),
            "Tuesday":   ("Yoga", [("Full body yoga / stretching","30 min")], "Active Rest"),
            "Wednesday": ("Walk", [("30 min walk","—")], "Active Rest"),
            "Thursday":  ("Mobility", [("Hip + shoulder mobility","20 min")], "Active Rest"),
            "Friday":    ("Light Walk", [("30 min walk","—")], "Active Rest"),
            "Saturday":  ("Yoga", [("Yoga / foam rolling","30 min")], "Active Rest"),
            "Sunday":    ("Rest", [("Full rest","—")], "Rest"),
        },
        "cardio": "Light walking only.",
        "progression": "Return to normal training when energy and mood recover.",
        "recovery": ["Sleep 9+ hours","Eat at maintenance","Address stress or sleep issues before training"],
    },
    "machine_only": {
        "title": "Machine Only (Injury Prevention)",
        "split": "3 days machines · 1 cardio · 3 rest",
        "intensity": "Low–Moderate",
        "schedule": {
            "Monday":    ("Upper Machine", [("Chest Press Machine","3×12"),("Lat Pulldown","3×12"),("Shoulder Press Machine","3×12"),("Cable Curl","3×12")], "Strength"),
            "Tuesday":   ("Rest", [("Rest","—")], "Rest"),
            "Wednesday": ("Lower Machine", [("Leg Press","3×12"),("Leg Curl","3×12"),("Leg Extension","3×12"),("Calf Raises","3×15")], "Strength"),
            "Thursday":  ("Low Impact Cardio", [("Swimming / Cycling","20 min"),("Light Elliptical","15 min")], "Cardio"),
            "Friday":    ("Full Body Machine", [("Chest Fly","3×12"),("Seated Row","3×12"),("Leg Press","3×12"),("Core Machine","3×12")], "Strength"),
            "Saturday":  ("Rest", [("Stretching","20 min")], "Rest"),
            "Sunday":    ("Rest", [("Rest","—")], "Rest"),
        },
        "cardio": "Low-impact only — no running, no jumping until injury resolves.",
        "progression": "Focus on technique. Add reps before weight.",
        "recovery": ["Rest the injured area completely","Ice + compression if swelling","See a physiotherapist if pain persists 48h"],
    },
    "simple_compound": {
        "title": "Simple Compound Lifts (Low Motivation)",
        "split": "3 days · full body each day",
        "intensity": "Moderate",
        "schedule": {
            "Monday":    ("Full Body A", [("Squat","3×8"),("Bench Press","3×8"),("Deadlift","3×5"),("Pull-Ups","3×6")], "Strength"),
            "Tuesday":   ("Rest / Walk", [("Walk 30 min","—")], "Active Rest"),
            "Wednesday": ("Full Body B", [("Squat","3×8"),("Overhead Press","3×8"),("Barbell Row","3×8"),("Dips","3×8")], "Strength"),
            "Thursday":  ("Rest", [("Rest","—")], "Rest"),
            "Friday":    ("Full Body C", [("Deadlift","4×5"),("Bench Press","3×8"),("Pull-Ups","3×6"),("Core","2×15")], "Strength"),
            "Saturday":  ("Rest", [("Rest","—")], "Rest"),
            "Sunday":    ("Rest", [("Rest","—")], "Rest"),
        },
        "cardio": "One 20-min walk per week. Keep it simple.",
        "progression": "Just show up. Add weight when it feels too easy.",
        "recovery": ["Simplicity beats complexity right now","Set 1 small goal each session","Reward yourself after each session"],
    },
}

# Fallback map for styles not yet in templates
FALLBACK_MAP = {
    "light_strength_cardio": "deload",
    "simple_strength":       "simple_compound",
    "strength_hiit":         "strength_cardio",
    "deload_cardio":         "deload",
    "deload_compound":       "deload",
    "advanced_cut":          "strength_cardio",
    "advanced_hypertrophy":  "ppl_split",
    "powerlifting":          "strength_bulk",
    "recomp_advanced":       "recomp_balanced",
    "light_recomp":          "recomp_balanced",
    "simple_recomp":         "recomp_balanced",
    "upper_machine":         "machine_only",
    "light_compound":        "deload",
}


def _train_classifier():
    X = np.array([[r[0],r[1],r[2],r[3],r[4],r[5],r[6]] for r in TRAINING_DATA])
    y = [r[7] for r in TRAINING_DATA]
    clf = DecisionTreeClassifier(max_depth=5, random_state=42)
    clf.fit(X, y)
    return clf

_CLASSIFIER = _train_classifier()


def get_ai_workout(goal: str, experience: str, feedback_issues: list,
                   workout_days: int, fitness_intelligence: dict | None = None) -> dict:
    """
    Uses trained Decision Tree to select workout style,
    then returns a personalised plan with feedback adjustments.
    """
    goal_enc    = GOAL_ENC.get(goal, 0)
    exp_enc     = EXP_ENC.get(experience, 0)
    intel       = normalize_fitness_intelligence(fitness_intelligence) if fitness_intelligence else None
    scores      = intel.get("fitness_scores", {}) if intel else {}
    fatigue     = int(any(i in feedback_issues for i in ["fatigue","overtraining","sleep issues"]) or scores.get("recovery_score", 100) < 55)
    low_mot     = int("low motivation" in feedback_issues or scores.get("motivation_score", 100) < 55)
    injury      = int("injury risk" in feedback_issues or scores.get("injury_risk", 0) > 55)
    stress      = int("stress" in feedback_issues or scores.get("stress_score", 0) > 65)
    days_capped = min(workout_days, 6)

    features = np.array([[goal_enc, exp_enc, fatigue, low_mot, injury, days_capped, stress]])
    predicted_style = _CLASSIFIER.predict(features)[0]

    # Resolve fallbacks
    template_key = FALLBACK_MAP.get(predicted_style, predicted_style)
    if template_key not in WORKOUT_TEMPLATES:
        template_key = "strength_cardio"

    plan = dict(WORKOUT_TEMPLATES[template_key])
    workout_adjustment = (intel or {}).get("workout_adjustment", {})
    if workout_adjustment:
        if workout_adjustment.get("intensity") == "reduce":
            plan["intensity"] = "Reduced"
        elif workout_adjustment.get("intensity") == "increase":
            plan["intensity"] = "High"
        if workout_adjustment.get("recovery_days", 0) > 0:
            plan["recovery"] = list(plan.get("recovery", [])) + [
                f"Add {workout_adjustment['recovery_days']} extra recovery day(s) this week"
            ]
        if workout_adjustment.get("cardio_minutes", 0):
            plan["cardio"] = f"{plan.get('cardio', '')} Target {workout_adjustment['cardio_minutes']} min cardio sessions."

    # Add AI explanation
    plan["ai_reasoning"] = _explain_prediction(
        goal, experience, feedback_issues, predicted_style, template_key, scores
    )

    # Trim schedule to requested days
    plan["schedule"] = _trim_to_days(plan["schedule"], workout_days, fatigue)

    return plan


def _trim_to_days(schedule: dict, workout_days: int, fatigue: bool) -> dict:
    """Adjust schedule if user has fewer days available."""
    if workout_days >= 6 or fatigue:
        return schedule
    all_days = list(schedule.items())
    rest_days = [(d,v) for d,v in all_days if v[2] in ("Rest","Active Rest")]
    active_days = [(d,v) for d,v in all_days if v[2] not in ("Rest","Active Rest")]
    if len(active_days) <= workout_days:
        return schedule
    trimmed_active = active_days[:workout_days]
    result = dict(trimmed_active)
    for d,v in rest_days[:7-workout_days]:
        result[d] = v
    return result


def _explain_prediction(goal, experience, issues, predicted, template_key, scores=None):
    reasons = [f"Goal: {goal} · Experience: {experience}"]
    if "fatigue" in issues or "overtraining" in issues:
        reasons.append("🔴 Fatigue detected → reduced intensity plan selected")
    if "injury risk" in issues:
        reasons.append("⚠️ Injury risk → machine-only plan to protect joints")
    if "low motivation" in issues:
        reasons.append("💛 Low motivation → simplified 3-day full body plan")
    if "stress" in issues:
        reasons.append("🧘 High stress → recovery emphasis added")
    scores = scores or {}
    if scores:
        reasons.append(
            f"AI scores: recovery {scores.get('recovery_score', 0)}/100, "
            f"training {scores.get('training_quality', 0)}/100, "
            f"motivation {scores.get('motivation_score', 0)}/100, "
            f"injury risk {scores.get('injury_risk', 0)}/100"
        )
    if template_key == predicted:
        reasons.append(f"✅ Plan: {template_key.replace('_',' ').title()}")
    else:
        reasons.append(f"✅ Closest plan: {template_key.replace('_',' ').title()}")
    return " · ".join(reasons)
