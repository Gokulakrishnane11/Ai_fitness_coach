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
from app.engine.workout_rules import select_workout_split, generate_deterministic_workout_plan
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


def test_workout_split_selection():
    assert select_workout_split("fat_loss", 3, "beginner") == "full_body"
    assert select_workout_split("muscle_gain", 4, "intermediate") == "upper_lower"
    assert select_workout_split("muscle_gain", 5, "advanced") == "ppl"


def test_deterministic_workout_plan():
    plan = generate_deterministic_workout_plan("muscle_gain", 4, "intermediate")
    assert plan["split_type"] == "UPPER_LOWER"
    assert len(plan["routine"]) == 2


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
