"""
Unit & Integration Tests for Phase 4D: Applying Adaptation Decisions to Active Plans.
Covers:
- Authenticated access & 401 enforcement
- User isolation (RLS / user token forwarding)
- Missing & incomplete profile handling (404 / 422)
- Applying adaptation generates and persists new active meal and workout plans
- Previous active plans are archived (is_active=False)
- Idempotency: repeated calls without changes return already_applied and avoid plan churn
- force_apply=True bypasses idempotency
- Deload and caloric adjustments are reflected in generated active plans
- Adaptation history is updated with linked active plan IDs
"""

import sys
import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db import supabase as db_mod
from app.db.supabase import (
    ProfileRepository,
    DailyLogRepository,
    MealPlanRepository,
    WorkoutPlanRepository,
    AdaptationHistoryRepository,
)

client = TestClient(app)

TEST_USER_ID = "user_apply_adaptation_test"
AUTH_HEADER = {"Authorization": f"Bearer test_token_{TEST_USER_ID}"}


def _setup_base_profile(user_id: str = TEST_USER_ID, **overrides):
    profile = {
        "id": user_id,
        "weight_kg": 75.0,
        "height_cm": 178.0,
        "age": 28,
        "gender": "male",
        "activity_level": "moderately_active",
        "goal_type": "fat_loss",
        "dietary_preference": "vegetarian",
        "target_weight_kg": 70.0,
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
    }
    profile.update(overrides)
    db_mod._OFFLINE_TEST_DB["profiles"][user_id] = profile
    return profile


@pytest.fixture(autouse=True)
def clean_db():
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False):
        db_mod._OFFLINE_TEST_DB["profiles"].clear()
        db_mod._OFFLINE_TEST_DB["daily_logs"].clear()
        db_mod._OFFLINE_TEST_DB["journal_entries"].clear()
        db_mod._OFFLINE_TEST_DB["user_meal_plans"].clear()
        db_mod._OFFLINE_TEST_DB["user_workout_plans"].clear()
        db_mod._OFFLINE_TEST_DB["adaptation_history"].clear()
        yield


def test_apply_adaptation_unauthenticated():
    """POST /api/v1/planning/apply-adaptation requires valid JWT authorization."""
    res = client.post("/api/v1/planning/apply-adaptation", json={})
    assert res.status_code == 401


def test_apply_adaptation_missing_profile():
    """POST /api/v1/planning/apply-adaptation returns 404 when profile does not exist."""
    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 404
    assert "Profile not found" in res.json()["detail"]


def test_apply_adaptation_incomplete_profile():
    """POST /api/v1/planning/apply-adaptation returns 422 when profile is missing required biometrics."""
    db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = {
        "id": TEST_USER_ID,
        "weight_kg": 75.0,
        # missing height, age, gender, etc.
    }
    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 422
    assert "Cannot compute target metrics" in res.json()["detail"]


def test_apply_adaptation_success_generates_and_persists_plans():
    """Applying adaptation creates new active meal & workout plans and updates history."""
    _setup_base_profile()

    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "applied"
    assert data["applied"] is True
    assert "meal_plan" in data
    assert "workout_plan" in data
    assert "decision" in data

    # Verify active meal plan in DB
    active_meal = MealPlanRepository.get_active_meal_plan(TEST_USER_ID)
    assert active_meal is not None
    assert active_meal["is_active"] is True
    assert active_meal["target_calories"] == data["meal_plan"]["target_calories"]

    # Verify active workout plan in DB
    active_workout = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
    assert active_workout is not None
    assert active_workout["is_active"] is True
    assert active_workout["split_type"] == data["workout_plan"]["split_type"]

    # Verify adaptation history record linked to active plan IDs
    latest_hist = AdaptationHistoryRepository.get_latest_history(TEST_USER_ID)
    assert latest_hist is not None
    assert latest_hist["active_meal_plan_id"] == active_meal["id"]
    assert latest_hist["active_workout_plan_id"] == active_workout["id"]


def test_apply_adaptation_archives_previous_active_plans():
    """Applying adaptation with force_apply archives previous active meal and workout plans."""
    _setup_base_profile()

    # Pre-populate existing active plans
    old_meal = MealPlanRepository.save_meal_plan(TEST_USER_ID, {
        "title": "Old Meal Plan",
        "target_calories": 2000,
        "target_protein_g": 120,
        "target_carbs_g": 200,
        "target_fat_g": 60,
    })
    old_workout = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, {
        "title": "Old Workout Plan",
        "split_type": "FULL_BODY",
        "days_per_week": 3,
    })

    assert old_meal["is_active"] is True
    assert old_workout["is_active"] is True

    # Apply adaptation with force_apply=True
    res = client.post("/api/v1/planning/apply-adaptation", json={"force_apply": True}, headers=AUTH_HEADER)
    assert res.status_code == 200
    assert res.json()["applied"] is True

    # Verify old plans are archived
    all_meals = list(db_mod._OFFLINE_TEST_DB["user_meal_plans"].values())
    assert len(all_meals) == 2
    old_m = next(m for m in all_meals if m["id"] == old_meal["id"])
    assert old_m["is_active"] is False

    all_workouts = list(db_mod._OFFLINE_TEST_DB["user_workout_plans"].values())
    assert len(all_workouts) == 2
    old_w = next(w for w in all_workouts if w["id"] == old_workout["id"])
    assert old_w["is_active"] is False


def test_apply_adaptation_diet_only():
    """Diet adjustment regenerates only meal plan, preserving active workout plan."""
    _setup_base_profile(goal_type="muscle_gain")

    old_meal = MealPlanRepository.save_meal_plan(TEST_USER_ID, {
        "title": "Old Meal Plan",
        "target_calories": 2500,
        "target_protein_g": 160,
        "target_carbs_g": 300,
        "target_fat_g": 70,
    })
    old_workout = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, {
        "title": "Old Workout Plan",
        "split_type": "UPPER_LOWER",
        "days_per_week": 4,
    })

    # Plateau telemetry for muscle_gain: requires 14d and 28d weight stability + >=70% adherence
    for day in range(1, 30):
        DailyLogRepository.add_log(
            user_id=TEST_USER_ID,
            log_data={
                "log_date": f"2026-08-{day:02d}",
                "weight_kg": 75.0,
                "calories_consumed": 2500,
                "protein_consumed_g": 160.0,
                "workout_completed": True,
                "recovery_score": 85,
                "sleep_quality": 85,
                "stress_level": 25,
                "muscle_soreness": 20,
            },
        )

    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["applied"] is True
    assert data["decision"]["diet_adjustment"]["calorie_delta"] == 150
    assert data["decision"]["workout_adjustment"]["deload_recommended"] is False
    assert data["decision"]["workout_adjustment"]["intensity"] == "maintain"

    # Meal plan was regenerated & old meal plan archived
    all_meals = list(db_mod._OFFLINE_TEST_DB["user_meal_plans"].values())
    assert len(all_meals) == 2
    old_m = next(m for m in all_meals if m["id"] == old_meal["id"])
    assert old_m["is_active"] is False

    # Workout plan was NOT regenerated; old workout plan remains the only active workout plan
    all_workouts = list(db_mod._OFFLINE_TEST_DB["user_workout_plans"].values())
    assert len(all_workouts) == 1
    assert all_workouts[0]["id"] == old_workout["id"]
    assert all_workouts[0]["is_active"] is True


def test_apply_adaptation_workout_only():
    """Workout adjustment regenerates only workout plan, preserving active meal plan."""
    _setup_base_profile(goal_type="fat_loss")

    old_meal = MealPlanRepository.save_meal_plan(TEST_USER_ID, {
        "title": "Old Meal Plan",
        "target_calories": 2000,
        "target_protein_g": 150,
        "target_carbs_g": 200,
        "target_fat_g": 60,
    })
    old_workout = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, {
        "title": "Old Workout Plan",
        "split_type": "FULL_BODY",
        "days_per_week": 3,
    })

    # Severe fatigue with poor adherence: triggers deload workout adjustment while diet delta is 0
    for day in range(1, 6):
        DailyLogRepository.add_log(
            user_id=TEST_USER_ID,
            log_data={
                "log_date": f"2026-09-2{day}",
                "weight_kg": 75.0,
                "calories_consumed": 1500,
                "recovery_score": 20,
                "sleep_quality": 25,
                "stress_level": 90,
                "muscle_soreness": 85,
            },
        )

    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["applied"] is True
    assert data["decision"]["high_fatigue_flag"] is True
    assert data["decision"]["diet_adjustment"]["calorie_delta"] == 0

    # Workout plan was regenerated & archived
    all_workouts = list(db_mod._OFFLINE_TEST_DB["user_workout_plans"].values())
    assert len(all_workouts) == 2
    old_w = next(w for w in all_workouts if w["id"] == old_workout["id"])
    assert old_w["is_active"] is False

    # Meal plan was NOT regenerated; old meal plan remains the only active meal plan
    all_meals = list(db_mod._OFFLINE_TEST_DB["user_meal_plans"].values())
    assert len(all_meals) == 1
    assert all_meals[0]["id"] == old_meal["id"]
    assert all_meals[0]["is_active"] is True


def test_apply_adaptation_noop():
    """When no adjustments are required and plans exist, apply is a safe no-op."""
    _setup_base_profile()

    old_meal = MealPlanRepository.save_meal_plan(TEST_USER_ID, {
        "title": "Old Meal Plan",
        "target_calories": 2000,
        "target_protein_g": 120,
        "target_carbs_g": 200,
        "target_fat_g": 60,
    })
    old_workout = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, {
        "title": "Old Workout Plan",
        "split_type": "FULL_BODY",
        "days_per_week": 3,
    })

    # No logs -> baseline decision (no diet or workout adjustments)
    res = client.post("/api/v1/planning/apply-adaptation", json={"force_apply": False}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "already_applied"
    assert data["applied"] is False
    assert "No adaptation adjustments required" in data["message"]

    # Verify no new rows created
    assert len(db_mod._OFFLINE_TEST_DB["user_meal_plans"]) == 1
    assert len(db_mod._OFFLINE_TEST_DB["user_workout_plans"]) == 1
    assert old_meal["is_active"] is True
    assert old_workout["is_active"] is True


def test_apply_adaptation_missing_active_meal_plan_only():
    """Generates only missing meal plan when active workout plan already exists."""
    _setup_base_profile()

    old_workout = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, {
        "title": "Existing Workout Plan",
        "split_type": "UPPER_LOWER",
        "days_per_week": 4,
    })

    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["applied"] is True

    # Meal plan was created
    active_meal = MealPlanRepository.get_active_meal_plan(TEST_USER_ID)
    assert active_meal is not None
    assert active_meal["is_active"] is True

    # Workout plan was preserved (not regenerated)
    all_workouts = list(db_mod._OFFLINE_TEST_DB["user_workout_plans"].values())
    assert len(all_workouts) == 1
    assert all_workouts[0]["id"] == old_workout["id"]


def test_apply_adaptation_missing_active_workout_plan_only():
    """Generates only missing workout plan when active meal plan already exists."""
    _setup_base_profile()

    old_meal = MealPlanRepository.save_meal_plan(TEST_USER_ID, {
        "title": "Existing Meal Plan",
        "target_calories": 2100,
        "target_protein_g": 150,
        "target_carbs_g": 210,
        "target_fat_g": 65,
    })

    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["applied"] is True

    # Workout plan was created
    active_workout = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
    assert active_workout is not None
    assert active_workout["is_active"] is True

    # Meal plan was preserved (not regenerated)
    all_meals = list(db_mod._OFFLINE_TEST_DB["user_meal_plans"].values())
    assert len(all_meals) == 1
    assert all_meals[0]["id"] == old_meal["id"]


def test_apply_adaptation_idempotency_prevents_duplicate_churn():
    """Repeated calls with no changes detect already_applied and do not generate duplicate rows."""
    _setup_base_profile()

    # First application
    res1 = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res1.status_code == 200
    assert res1.json()["applied"] is True

    meal_count_1 = len(db_mod._OFFLINE_TEST_DB["user_meal_plans"])
    workout_count_1 = len(db_mod._OFFLINE_TEST_DB["user_workout_plans"])
    history_count_1 = len(db_mod._OFFLINE_TEST_DB["adaptation_history"])

    # Second application (identical state, force_apply=False)
    res2 = client.post("/api/v1/planning/apply-adaptation", json={"force_apply": False}, headers=AUTH_HEADER)
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["status"] == "already_applied"
    assert data2["applied"] is False
    assert "already applied" in data2["message"]

    # Verify no new rows created
    assert len(db_mod._OFFLINE_TEST_DB["user_meal_plans"]) == meal_count_1
    assert len(db_mod._OFFLINE_TEST_DB["user_workout_plans"]) == workout_count_1
    assert len(db_mod._OFFLINE_TEST_DB["adaptation_history"]) == history_count_1


def test_apply_adaptation_force_apply_bypasses_idempotency():
    """force_apply=True regenerates and archives plans even if already applied."""
    _setup_base_profile()

    res1 = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res1.status_code == 200
    assert res1.json()["applied"] is True

    meal_count_1 = len(db_mod._OFFLINE_TEST_DB["user_meal_plans"])

    # Force apply
    res2 = client.post("/api/v1/planning/apply-adaptation", json={"force_apply": True}, headers=AUTH_HEADER)
    assert res2.status_code == 200
    assert res2.json()["applied"] is True
    assert res2.json()["status"] == "applied"

    # New plan row created
    assert len(db_mod._OFFLINE_TEST_DB["user_meal_plans"]) == meal_count_1 + 1


def test_apply_adaptation_user_isolation():
    """User A's adaptation does not affect User B's active plans."""
    user_a = "user_a"
    user_b = "user_b"

    _setup_base_profile(user_id=user_a)
    _setup_base_profile(user_id=user_b)

    auth_a = {"Authorization": f"Bearer test_token_{user_a}"}
    auth_b = {"Authorization": f"Bearer test_token_{user_b}"}

    # User A applies adaptation
    res_a = client.post("/api/v1/planning/apply-adaptation", json={}, headers=auth_a)
    assert res_a.status_code == 200

    # User B has no active plans yet
    assert MealPlanRepository.get_active_meal_plan(user_b) is None
    assert WorkoutPlanRepository.get_active_workout_plan(user_b) is None

    # User B applies adaptation
    res_b = client.post("/api/v1/planning/apply-adaptation", json={}, headers=auth_b)
    assert res_b.status_code == 200

    active_a = MealPlanRepository.get_active_meal_plan(user_a)
    active_b = MealPlanRepository.get_active_meal_plan(user_b)

    assert active_a["user_id"] == user_a
    assert active_b["user_id"] == user_b
    assert active_a["id"] != active_b["id"]


def test_apply_adaptation_with_poor_telemetry_applies_deload():
    """Poor telemetry triggers deload in workout plan and diet adjustment in meal plan."""
    _setup_base_profile()

    # Inject 5 days of severe fatigue/soreness logs
    for day in range(1, 6):
        DailyLogRepository.add_log(
            user_id=TEST_USER_ID,
            log_data={
                "log_date": f"2026-09-2{day}",
                "weight_kg": 75.0,
                "calories_consumed": 2200,
                "recovery_score": 15,
                "sleep_quality": 20,
                "stress_level": 95,
                "muscle_soreness": 90,
            },
        )

    res = client.post("/api/v1/planning/apply-adaptation", json={}, headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()

    # Decision should flag high fatigue
    assert data["decision"]["high_fatigue_flag"] is True

    # Workout plan should reflect deload week
    workout_plan = data["workout_plan"]
    assert workout_plan["deload_active"] is True
    assert "Deload Week" in workout_plan["title"]
    assert "RPE 6" in workout_plan["intensity_target"]

    # Active plan in DB matches
    active_workout = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
    assert active_workout["routine_data"]["deload_active"] is True
