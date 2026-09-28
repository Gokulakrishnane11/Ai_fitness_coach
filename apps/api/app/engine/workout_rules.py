"""
Deterministic Workout Plan Rules Engine.
Replaces legacy DecisionTree classifier with transparent, clinical rule matrices.
Matches workout splits (Full Body, Upper/Lower, PPL, Recomp) based on goal,
days available per week, and experience level.
"""

from typing import Dict, Any, List, Optional
import copy
from app.engine.adaptation import WorkoutAdjustment

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


def apply_workout_adjustment(
    template: Dict[str, Any],
    workout_days_per_week: int,
    workout_adjustment: Optional[WorkoutAdjustment] = None,
) -> Dict[str, Any]:
    """
    Pure helper that deterministically applies physiological adaptation adjustments
    to a baseline workout split template.

    Rules applied:
    1. Deload (deload_recommended == True):
       - Caps every exercise at 2 sets (min(2, sets))
       - Sets deload_active = True
       - Appends "(Deload Week)" to title
       - Sets intensity_target = "RPE 6 (Active Deload / Recovery)"
       - Prepends deload guidance to description
    2. Volume (when not deload):
       - low: reduces each exercise's sets by 1, minimum 2 sets (max(2, sets - 1))
       - high: increases each exercise's sets by 1, maximum 5 sets (min(5, sets + 1))
       - medium: preserves template sets
    3. Intensity (guidance only, no load/1RM manipulation):
       - reduce: "RPE 6-7 (Submaximal Recovery)"
       - maintain: "RPE 7-8 (Standard)"
       - increase: "RPE 8-9 (Progressive Overload)"
    4. Recovery days:
       - effective_days = max(2, workout_days_per_week - recovery_days)
       - When recovery_days > 0, returns effective days and documents in description.
    5. Cardio:
       - When cardio_minutes > 0, appends one cardio finisher to each routine day:
         {"name": "Post-Workout Cardio (Zone 2 LISS)", "sets": 1, "reps": f"{cardio_minutes} min", "rest_sec": 0}
    """
    base_schedule: List[Dict[str, Any]] = template.get("schedule", [])
    base_title: str = template.get("title", "")
    base_description: str = template.get("description", "")

    # Neutral / baseline defaults
    volume: str = "medium"
    intensity: str = "maintain"
    recovery_days: int = 0
    cardio_minutes: int = 0
    deload_recommended: bool = False

    if workout_adjustment is not None:
        volume = workout_adjustment.volume
        intensity = workout_adjustment.intensity
        recovery_days = workout_adjustment.recovery_days
        cardio_minutes = workout_adjustment.cardio_minutes
        deload_recommended = workout_adjustment.deload_recommended

    # 1. Intensity guidance
    if deload_recommended:
        intensity_target = "RPE 6 (Active Deload / Recovery)"
    elif intensity == "reduce":
        intensity_target = "RPE 6-7 (Submaximal Recovery)"
    elif intensity == "increase":
        intensity_target = "RPE 8-9 (Progressive Overload)"
    else:
        intensity_target = "RPE 7-8 (Standard)"

    # 2. Sets modulation & routine generation
    adjusted_routine: List[Dict[str, Any]] = []
    for day_routine in copy.deepcopy(base_schedule):
        adjusted_exercises: List[Dict[str, Any]] = []
        for ex in day_routine.get("exercises", []):
            base_sets = int(ex.get("sets", 3))
            if deload_recommended:
                adjusted_sets = min(2, base_sets)
            elif volume == "low":
                adjusted_sets = max(2, base_sets - 1)
            elif volume == "high":
                adjusted_sets = min(5, base_sets + 1)
            else:
                adjusted_sets = base_sets

            exercise_copy = dict(ex)
            exercise_copy["sets"] = adjusted_sets
            adjusted_exercises.append(exercise_copy)

        # 3. Cardio finisher
        if cardio_minutes > 0:
            adjusted_exercises.append(
                {
                    "name": "Post-Workout Cardio (Zone 2 LISS)",
                    "sets": 1,
                    "reps": f"{cardio_minutes} min",
                    "rest_sec": 0,
                }
            )

        day_copy = dict(day_routine)
        day_copy["exercises"] = adjusted_exercises
        adjusted_routine.append(day_copy)

    # 4. Schedule frequency / recovery days
    if recovery_days > 0:
        effective_days = max(2, workout_days_per_week - recovery_days)
    else:
        effective_days = workout_days_per_week

    # 5. Title & Description
    if deload_recommended:
        final_title = f"{base_title} (Deload Week)"
        final_description = (
            f"[ACTIVE DELOAD PROTOCOL] High systemic fatigue detected. Working sets capped at 2 per movement "
            f"at {intensity_target} to facilitate physiological recovery. {base_description}"
        )
    else:
        final_title = base_title
        final_description = base_description

    if recovery_days > 0:
        final_description = (
            f"{final_description} [Recovery Allocation: {recovery_days} additional rest day(s) injected; "
            f"effective frequency: {effective_days} days/week.]"
        )

    return {
        "title": final_title,
        "days_per_week": effective_days,
        "description": final_description,
        "routine": adjusted_routine,
        "intensity_target": intensity_target,
        "deload_active": deload_recommended,
        "cardio_minutes": cardio_minutes,
        "recovery_days": recovery_days,
    }


def generate_deterministic_workout_plan(
    goal_type: str,
    workout_days_per_week: int,
    experience_level: str,
    workout_adjustment: Optional[WorkoutAdjustment] = None,
) -> Dict[str, Any]:
    """
    Generates a structured weekly workout routine based on deterministic split rules,
    applying optional physiological adaptation adjustments when provided.
    """
    split_key = select_workout_split(goal_type, workout_days_per_week, experience_level)
    template = SPLIT_TEMPLATES[split_key]

    adjusted = apply_workout_adjustment(
        template=template,
        workout_days_per_week=workout_days_per_week,
        workout_adjustment=workout_adjustment,
    )

    return {
        "title": adjusted["title"],
        "split_type": split_key.upper(),
        "days_per_week": adjusted["days_per_week"],
        "experience_level": experience_level.capitalize(),
        "description": adjusted["description"],
        "routine": adjusted["routine"],
        "intensity_target": adjusted["intensity_target"],
        "deload_active": adjusted["deload_active"],
        "cardio_minutes": adjusted["cardio_minutes"],
        "recovery_days": adjusted["recovery_days"],
    }
