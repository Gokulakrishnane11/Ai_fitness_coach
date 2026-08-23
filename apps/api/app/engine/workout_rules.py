"""
Deterministic Workout Plan Rules Engine.
Replaces legacy DecisionTree classifier with transparent, clinical rule matrices.
Matches workout splits (Full Body, Upper/Lower, PPL, Recomp) based on goal,
days available per week, and experience level.
"""

from typing import Dict, Any, List

SPLIT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "full_body": {
        "title": "Full Body Compound Split",
        "description": "Targets major muscle groups each workout. High frequency, optimal for beginners or 2-3 day availability.",
        "schedule": [
            {
                "day": "Day 1",
                "focus": "Full Body A",
                "exercises": [
                    {"name": "Barbell Back Squat", "sets": 3, "reps": "8-10", "rest_sec": 120},
                    {"name": "Flat Bench Press", "sets": 3, "reps": "8-10", "rest_sec": 90},
                    {"name": "Bent Over Barbell Row", "sets": 3, "reps": "8-10", "rest_sec": 90},
                    {"name": "Dumbbell Overhead Press", "sets": 3, "reps": "10-12", "rest_sec": 60},
                    {"name": "Plank", "sets": 3, "reps": "45-60 sec", "rest_sec": 60},
                ],
            },
            {
                "day": "Day 2",
                "focus": "Full Body B",
                "exercises": [
                    {"name": "Conventional Deadlift", "sets": 3, "reps": "5", "rest_sec": 180},
                    {"name": "Incline Dumbbell Press", "sets": 3, "reps": "10-12", "rest_sec": 90},
                    {"name": "Lat Pulldown / Pull-ups", "sets": 3, "reps": "8-10", "rest_sec": 90},
                    {"name": "Romanian Deadlift", "sets": 3, "reps": "10-12", "rest_sec": 90},
                    {"name": "Hanging Leg Raises", "sets": 3, "reps": "12-15", "rest_sec": 60},
                ],
            },
        ],
    },
    "upper_lower": {
        "title": "Upper / Lower Split",
        "description": "Balances volume and frequency across upper and lower body movements. Ideal for 4-day availability.",
        "schedule": [
            {
                "day": "Day 1",
                "focus": "Upper Strength",
                "exercises": [
                    {"name": "Barbell Bench Press", "sets": 4, "reps": "6-8", "rest_sec": 120},
                    {"name": "Barbell Row", "sets": 4, "reps": "6-8", "rest_sec": 120},
                    {"name": "Overhead Press", "sets": 3, "reps": "8-10", "rest_sec": 90},
                    {"name": "Incline Dumbbell Flyes", "sets": 3, "reps": "10-12", "rest_sec": 60},
                    {"name": "Barbell Bicep Curls", "sets": 3, "reps": "10-12", "rest_sec": 60},
                ],
            },
            {
                "day": "Day 2",
                "focus": "Lower Strength",
                "exercises": [
                    {"name": "Barbell Squat", "sets": 4, "reps": "6-8", "rest_sec": 150},
                    {"name": "Romanian Deadlift", "sets": 3, "reps": "8-10", "rest_sec": 120},
                    {"name": "Leg Press", "sets": 3, "reps": "10-12", "rest_sec": 90},
                    {"name": "Hamstring Curls", "sets": 3, "reps": "12-15", "rest_sec": 60},
                    {"name": "Calf Raises", "sets": 4, "reps": "15-20", "rest_sec": 60},
                ],
            },
        ],
    },
    "ppl": {
        "title": "Push / Pull / Legs Split",
        "description": "High volume muscle-group hyper-targeting. Optimal for 5-6 day availability and intermediate/advanced lifters.",
        "schedule": [
            {
                "day": "Push Day",
                "focus": "Chest, Shoulders & Triceps",
                "exercises": [
                    {"name": "Barbell Bench Press", "sets": 4, "reps": "8-10", "rest_sec": 120},
                    {"name": "Seated Dumbbell Shoulder Press", "sets": 3, "reps": "10-12", "rest_sec": 90},
                    {"name": "Cable Chest Flyes", "sets": 3, "reps": "12-15", "rest_sec": 60},
                    {"name": "Lateral Raises", "sets": 4, "reps": "15-20", "rest_sec": 60},
                    {"name": "Tricep Rope Pushdowns", "sets": 3, "reps": "12-15", "rest_sec": 60},
                ],
            },
            {
                "day": "Pull Day",
                "focus": "Back, Rear Delts & Biceps",
                "exercises": [
                    {"name": "Lat Pulldown / Pull-ups", "sets": 4, "reps": "8-10", "rest_sec": 90},
                    {"name": "Seated Cable Rows", "sets": 3, "reps": "10-12", "rest_sec": 90},
                    {"name": "Face Pulls", "sets": 4, "reps": "15-20", "rest_sec": 60},
                    {"name": "Barbell Bicep Curls", "sets": 3, "reps": "10-12", "rest_sec": 60},
                    {"name": "Hammer Curls", "sets": 3, "reps": "12-15", "rest_sec": 60},
                ],
            },
            {
                "day": "Legs Day",
                "focus": "Quads, Hamstrings, Glutes & Calves",
                "exercises": [
                    {"name": "Barbell Back Squat", "sets": 4, "reps": "8-10", "rest_sec": 150},
                    {"name": "Romanian Deadlift", "sets": 3, "reps": "10-12", "rest_sec": 120},
                    {"name": "Walking Lunges", "sets": 3, "reps": "12 per leg", "rest_sec": 90},
                    {"name": "Leg Extension", "sets": 3, "reps": "12-15", "rest_sec": 60},
                    {"name": "Standing Calf Raises", "sets": 4, "reps": "15-20", "rest_sec": 60},
                ],
            },
        ],
    },
}


def select_workout_split(
    goal_type: str, workout_days: int, experience_level: str
) -> str:
    """
    Deterministically selects the optimal workout split.
    """
    days = max(1, min(workout_days, 7))
    exp = experience_level.lower() if experience_level else "beginner"

    if days <= 3 or exp == "beginner":
        return "full_body"
    elif days == 4:
        return "upper_lower"
    else:  # 5, 6, 7 days and intermediate/advanced
        return "ppl"


def generate_deterministic_workout_plan(
    goal_type: str,
    workout_days_per_week: int,
    experience_level: str,
) -> Dict[str, Any]:
    """
    Generates a structured weekly workout routine based on deterministic split rules.
    """
    split_key = select_workout_split(goal_type, workout_days_per_week, experience_level)
    template = SPLIT_TEMPLATES[split_key]

    return {
        "title": template["title"],
        "split_type": split_key.upper(),
        "days_per_week": workout_days_per_week,
        "experience_level": experience_level.capitalize(),
        "description": template["description"],
        "routine": template["schedule"],
    }
