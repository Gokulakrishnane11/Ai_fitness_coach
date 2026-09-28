"""
Unit Test Suite for Pure Engine Calculations (Phase 1 Verification).
Tests BMR/TDEE math, calorie floors, meal plan matching, workout split rules,
transformation timeline predictions, recomposition, and uncertainty corridors.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.bmr_tdee import (
    calculate_bmr,
    calculate_tdee,
    calculate_target_metrics,
    CALORIE_FLOORS,
)
from app.engine.nutrition_rules import generate_deterministic_meal_plan, filter_foods_by_preference, SEED_FOODS
from app.engine.adaptation import DietAdjustment, WorkoutAdjustment
from app.engine.workout_rules import select_workout_split, generate_deterministic_workout_plan, apply_workout_adjustment
from app.engine.transformation import predict_transformation_timeline, simulate_multi_week_transformation


def test_bmr_mifflin_male():
    bmr = calculate_bmr(80.0, 180.0, 25, "male")
    assert bmr == 1805.0


def test_bmr_mifflin_female():
    bmr = calculate_bmr(60.0, 165.0, 30, "female")
    assert abs(bmr - 1320.25) < 0.5


def test_bmr_katch_mcardle():
    bmr = calculate_bmr(80.0, 180.0, 25, "male", body_fat_pct=20.0)
    assert bmr == 1752.4


def test_tdee_calculation():
    bmr = 1800.0
    tdee_sedentary = calculate_tdee(bmr, "sedentary")
    assert tdee_sedentary == 2160.0
    tdee_mod = calculate_tdee(bmr, "moderately_active")
    assert tdee_mod == 2790.0


def test_target_metrics_calorie_floor_female():
    metrics = calculate_target_metrics(40.0, 150.0, 40, "female", "sedentary", "fat_loss")
    assert metrics["target_calories"] >= CALORIE_FLOORS["female"]
    assert metrics["is_calorie_floor_applied"] is True


def test_food_filtering_vegan():
    vegan_foods = filter_foods_by_preference(SEED_FOODS, "vegan")
    assert len(vegan_foods) > 0
    for food in vegan_foods:
        assert food["is_vegan"] is True


def test_deterministic_meal_plan():
    plan = generate_deterministic_meal_plan(
        target_calories=2000,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=60.0,
        dietary_preference="vegetarian",
    )
    assert plan["target_calories"] == 2000
    assert len(plan["meals"]) == 4
    assert plan["achieved_calories"] > 1000


def test_meal_plan_no_adjustment_unchanged():
    """Requirement A: No adjustment preserves existing meal-plan behavior."""
    plan_none = generate_deterministic_meal_plan(
        target_calories=2000,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=60.0,
        dietary_preference="anything",
        diet_adjustment=None,
    )
    plan_neutral = generate_deterministic_meal_plan(
        target_calories=2000,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=60.0,
        dietary_preference="anything",
        diet_adjustment=DietAdjustment(),
    )
    assert plan_none["target_calories"] == 2000
    assert plan_none["target_protein_g"] == 150.0
    assert plan_none["target_carbs_g"] == 200.0
    assert plan_none["target_fat_g"] == 60.0
    assert plan_none == plan_neutral


def test_meal_plan_muscle_gain_plateau_adaptation():
    """Requirement B: Muscle-gain plateau adjustment adapts target calories and macros."""
    baseline = generate_deterministic_meal_plan(
        target_calories=2000,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=60.0,
        dietary_preference="anything",
        diet_adjustment=None,
    )
    plateau_adj = DietAdjustment(
        calorie_delta=150,
        carb_delta_g=25.0,
        fat_delta_g=5.5,
        protein_delta_g=0.0,
    )
    adapted = generate_deterministic_meal_plan(
        target_calories=2000,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=60.0,
        dietary_preference="anything",
        diet_adjustment=plateau_adj,
    )
    assert adapted["target_calories"] == 2150
    assert adapted["target_carbs_g"] == 225.0
    assert adapted["target_fat_g"] == 65.5
    assert adapted["target_protein_g"] == 150.0
    assert adapted["achieved_calories"] > baseline["achieved_calories"]
    assert adapted["achieved_carbs_g"] > baseline["achieved_carbs_g"]


def test_meal_plan_deficit_safety_floor_enforced():
    """Requirement C: Negative calorie adjustment cannot push effective target below the safety floor (1200 kcal)."""
    cut_adj = DietAdjustment(calorie_delta=-200)
    # 1300 - 200 = 1100 -> clamped to 1200
    plan_clamped = generate_deterministic_meal_plan(
        target_calories=1300,
        target_protein_g=120.0,
        target_carbs_g=100.0,
        target_fat_g=40.0,
        dietary_preference="anything",
        diet_adjustment=cut_adj,
    )
    assert plan_clamped["target_calories"] == 1200

    # 1200 - 300 = 900 -> clamped to 1200
    plan_hard_floor = generate_deterministic_meal_plan(
        target_calories=1200,
        target_protein_g=100.0,
        target_carbs_g=100.0,
        target_fat_g=40.0,
        dietary_preference="anything",
        diet_adjustment=DietAdjustment(calorie_delta=-300),
    )
    assert plan_hard_floor["target_calories"] == 1200


def test_workout_split_selection():
    assert select_workout_split("fat_loss", 3, "beginner") == "full_body"
    assert select_workout_split("muscle_gain", 4, "intermediate") == "upper_lower"
    assert select_workout_split("muscle_gain", 5, "advanced") == "ppl"


def test_deterministic_workout_plan():
    plan = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate")
    assert plan["split_type"] == "UPPER_LOWER"
    assert len(plan["routine"]) == 2


def test_workout_plan_adjustment_none_preserves_baseline():
    plan = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=None)
    assert plan["split_type"] == "UPPER_LOWER"
    assert plan["days_per_week"] == 4
    assert len(plan["routine"]) == 2
    # Baseline upper lower Day 1 has Bench (4 sets), Row (4 sets), OHP (3 sets)
    day1_sets = [ex["sets"] for ex in plan["routine"][0]["exercises"]]
    assert day1_sets == [4, 4, 3, 3, 3]
    assert plan["deload_active"] is False
    assert plan["cardio_minutes"] == 0
    assert plan["recovery_days"] == 0
    assert plan["intensity_target"] == "RPE 7-8 (Standard)"


def test_workout_plan_neutral_adjustment_identical_to_baseline():
    plan_none = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=None)
    plan_neutral = generate_deterministic_workout_plan(
        "muscle_gain", 4, "intermediate", workout_adjustment=WorkoutAdjustment()
    )
    assert plan_none == plan_neutral


def test_workout_plan_volume_low_reduces_sets():
    adj = WorkoutAdjustment(volume="low")
    plan = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=adj)
    # Baseline sets [4, 4, 3, 3, 3] -> [3, 3, 2, 2, 2]
    day1_sets = [ex["sets"] for ex in plan["routine"][0]["exercises"]]
    assert day1_sets == [3, 3, 2, 2, 2]


def test_workout_plan_volume_high_increases_sets():
    adj = WorkoutAdjustment(volume="high")
    plan = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=adj)
    # Baseline sets [4, 4, 3, 3, 3] -> [5, 5, 4, 4, 4]
    day1_sets = [ex["sets"] for ex in plan["routine"][0]["exercises"]]
    assert day1_sets == [5, 5, 4, 4, 4]


def test_workout_plan_volume_floor_never_below_two():
    # If baseline is full_body (3 sets each), low volume makes them 2, but never 1 or 0
    adj = WorkoutAdjustment(volume="low")
    plan = generate_deterministic_workout_plan("fat_loss", 3, "beginner", workout_adjustment=adj)
    for day in plan["routine"]:
        for ex in day["exercises"]:
            assert ex["sets"] >= 2


def test_workout_plan_deload_caps_sets_at_two():
    adj = WorkoutAdjustment(
        intensity="reduce",
        volume="low",
        recovery_days=2,
        cardio_minutes=0,
        deload_recommended=True,
    )
    plan = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=adj)
    assert "Deload" in plan["title"]
    assert plan["deload_active"] is True
    assert "RPE 6" in plan["intensity_target"]
    for day in plan["routine"]:
        for ex in day["exercises"]:
            assert ex["sets"] == 2


def test_workout_plan_recovery_days_effective_frequency():
    # recovery_days = 1: 4 days -> 3 days
    adj1 = WorkoutAdjustment(recovery_days=1)
    plan1 = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=adj1)
    assert plan1["days_per_week"] == 3
    assert plan1["recovery_days"] == 1
    assert "Recovery Allocation: 1" in plan1["description"]
    assert len(plan1["routine"]) == 2  # routine card count preserved!

    # recovery_days = 2: 4 days -> 2 days
    adj2 = WorkoutAdjustment(recovery_days=2)
    plan2 = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate", workout_adjustment=adj2)
    assert plan2["days_per_week"] == 2
    assert plan2["recovery_days"] == 2
    assert "Recovery Allocation: 2" in plan2["description"]
    assert len(plan2["routine"]) == 2  # routine card count preserved!


def test_workout_plan_cardio_minutes_appends_finisher():
    adj = WorkoutAdjustment(cardio_minutes=30)
    plan = generate_deterministic_workout_plan("fat_loss", 4, "intermediate", workout_adjustment=adj)
    assert plan["cardio_minutes"] == 30
    for day in plan["routine"]:
        # 5 baseline exercises + 1 cardio finisher = 6
        assert len(day["exercises"]) == 6
        finisher = day["exercises"][-1]
        assert finisher["name"] == "Post-Workout Cardio (Zone 2 LISS)"
        assert finisher["sets"] == 1
        assert finisher["reps"] == "30 min"
        assert finisher["rest_sec"] == 0
        assert day["exercises"][0]["name"] in ("Barbell Bench Press", "Barbell Squat")


def test_transformation_timeline_uncertainty_corridor():
    timeline = predict_transformation_timeline(
        current_weight_kg=80.0,
        target_weight_kg=72.0,
        height_cm=175.0,
        age=25,
        gender="male",
        activity_level="moderately_active",
        daily_caloric_deficit_surplus=-500,
        adherence_pct=90.0,
    )
    assert timeline["estimated_weeks"] == 20
    assert timeline["timeline_range_weeks"] == "17 to 23 weeks"
    assert timeline["weekly_rate_kg"] == -0.41
    assert timeline["is_safe_rate"] is True
    assert "±15%" in timeline["uncertainty_margin"]


def test_recomposition_simulation():
    sim = simulate_multi_week_transformation(
        start_weight_kg=85.0,
        height_cm=175.0,
        age=25,
        gender="male",
        activity_level="moderately_active",
        daily_caloric_deficit_surplus=-150,
        adherence_pct=90.0,
        duration_weeks=12,
        body_fat_pct=22.0,
        goal_type="recomposition",
        protein_g_per_day=160.0,
        workout_days_per_week=4,
    )
    assert len(sim) == 13
    assert sim[0]["week"] == 0
    assert sim[0]["weight_kg"] == 85.0
    assert sim[0]["fat_mass_kg"] == 18.7
    assert sim[0]["lean_mass_kg"] == 66.3

    assert sim[12]["fat_mass_kg"] < 17.5
    assert sim[12]["lean_mass_kg"] > 67.0
    assert round(sim[12]["fat_mass_kg"] + sim[12]["lean_mass_kg"], 2) == sim[12]["weight_kg"]
