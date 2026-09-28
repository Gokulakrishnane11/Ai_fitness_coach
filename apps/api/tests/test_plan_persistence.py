"""
Unit & Integration Tests for Plan Persistence (Phase 3A).
Covers:
- MealPlanRepository: save active, fetch active, archive previous active plan
- WorkoutPlanRepository: save active, fetch active, archive previous active plan
- Live Supabase repository tests: RLS JWT token forwarding, query shapes, update & insert
- Meal-plan API (POST /api/v1/planning/meal-plan): persists active plan to DB
- Workout-plan API (POST /api/v1/planning/workout-plan): persists active plan to DB
- apply_adaptation=False persists baseline generated plan for meal and workout plans
- Active plan retrieval endpoints (GET /api/v1/planning/active-meal-plan, GET /api/v1/planning/active-workout-plan)
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db import supabase as db_mod
from app.db.supabase import (
    MealPlanRepository,
    WorkoutPlanRepository,
    ProfileRepository,
)

client = TestClient(app)

TEST_USER_ID = "user_plan_persist_test"
AUTH_HEADER = {"Authorization": f"Bearer test_token_{TEST_USER_ID}"}
LIVE_TOKEN = "valid_user_jwt_token_persistence_test"


def _sample_meal_plan(**overrides):
    base = {
        "title": "Deterministic Vegetarian Meal Plan",
        "target_calories": 2200,
        "target_protein_g": 140.0,
        "target_carbs_g": 250.0,
        "target_fat_g": 65.0,
        "achieved_calories": 2185,
        "achieved_protein_g": 138.5,
        "achieved_carbs_g": 248.0,
        "achieved_fat_g": 64.0,
        "meals": [
            {
                "meal_name": "Breakfast",
                "target_calories": 550,
                "actual_calories": 540,
                "protein_g": 35.0,
                "carbs_g": 60.0,
                "fat_g": 16.0,
                "items": [{"food": "Oats (Rolled)", "portion_g": 80.0}],
            }
        ],
    }
    base.update(overrides)
    return base


def _sample_workout_plan(**overrides):
    base = {
        "title": "Upper / Lower Frequency Split",
        "split_type": "UPPER_LOWER",
        "days_per_week": 4,
        "experience_level": "Intermediate",
        "description": "4-day Upper/Lower split targeting strength and hypertrophy.",
        "routine": [
            {
                "day": "Upper Body (A)",
                "focus": "Chest, Back, Shoulders & Arms",
                "exercises": [
                    {"name": "Barbell Bench Press", "sets": 4, "reps": "6-8", "rest_sec": 120}
                ],
            }
        ],
        "intensity_target": "RPE 7-8",
        "deload_active": False,
        "cardio_minutes": 0,
        "recovery_days": 0,
    }
    base.update(overrides)
    return base


# ==============================================================================
# 1. REPOSITORY UNIT TESTS (OFFLINE DB)
# ==============================================================================

def test_save_active_meal_plan():
    """MealPlanRepository.save_meal_plan correctly sets is_active=True and stores all schema fields."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True):

        plan_data = _sample_meal_plan()
        saved = MealPlanRepository.save_meal_plan(TEST_USER_ID, plan_data)

        assert saved["user_id"] == TEST_USER_ID
        assert saved["is_active"] is True
        assert saved["title"] == "Deterministic Vegetarian Meal Plan"
        assert saved["target_calories"] == 2200
        assert saved["target_protein_g"] == 140
        assert saved["target_carbs_g"] == 250
        assert saved["target_fat_g"] == 65
        assert saved["plan_data"]["achieved_calories"] == 2185
        assert "created_at" in saved
        assert "id" in saved


def test_fetch_active_meal_plan():
    """MealPlanRepository.get_active_meal_plan returns the active plan or None."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True):

        assert MealPlanRepository.get_active_meal_plan(TEST_USER_ID) is None

        plan_data = _sample_meal_plan()
        saved = MealPlanRepository.save_meal_plan(TEST_USER_ID, plan_data)

        fetched = MealPlanRepository.get_active_meal_plan(TEST_USER_ID)
        assert fetched is not None
        assert fetched["id"] == saved["id"]
        assert fetched["user_id"] == TEST_USER_ID
        assert fetched["is_active"] is True

        # User isolation: other user should have None
        assert MealPlanRepository.get_active_meal_plan("other_user_id") is None


def test_saving_new_meal_plan_archives_previous_active_plan():
    """Saving a new meal plan sets previously active plans to is_active=False."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True):

        plan_1 = _sample_meal_plan(target_calories=2000)
        saved_1 = MealPlanRepository.save_meal_plan(TEST_USER_ID, plan_1)
        assert saved_1["is_active"] is True

        plan_2 = _sample_meal_plan(target_calories=2300)
        saved_2 = MealPlanRepository.save_meal_plan(TEST_USER_ID, plan_2)
        assert saved_2["is_active"] is True

        # Check DB records
        records = list(db_mod._OFFLINE_TEST_DB["user_meal_plans"].values())
        assert len(records) == 2

        old_plan = next(r for r in records if r["id"] == saved_1["id"])
        new_plan = next(r for r in records if r["id"] == saved_2["id"])

        assert old_plan["is_active"] is False
        assert new_plan["is_active"] is True

        active = MealPlanRepository.get_active_meal_plan(TEST_USER_ID)
        assert active["id"] == saved_2["id"]
        assert active["target_calories"] == 2300


def test_save_active_workout_plan():
    """WorkoutPlanRepository.save_workout_plan correctly sets is_active=True and stores all schema fields."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_workout_plans"], {}, clear=True):

        plan_data = _sample_workout_plan()
        saved = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, plan_data)

        assert saved["user_id"] == TEST_USER_ID
        assert saved["is_active"] is True
        assert saved["title"] == "Upper / Lower Frequency Split"
        assert saved["split_type"] == "UPPER_LOWER"
        assert saved["days_per_week"] == 4
        assert saved["routine_data"]["experience_level"] == "Intermediate"
        assert "created_at" in saved
        assert "id" in saved


def test_fetch_active_workout_plan():
    """WorkoutPlanRepository.get_active_workout_plan returns the active plan or None."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_workout_plans"], {}, clear=True):

        assert WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID) is None

        plan_data = _sample_workout_plan()
        saved = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, plan_data)

        fetched = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
        assert fetched is not None
        assert fetched["id"] == saved["id"]
        assert fetched["user_id"] == TEST_USER_ID
        assert fetched["is_active"] is True

        # User isolation: other user should have None
        assert WorkoutPlanRepository.get_active_workout_plan("other_user_id") is None


def test_saving_new_workout_plan_archives_previous_active_plan():
    """Saving a new workout plan sets previously active plans to is_active=False."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_workout_plans"], {}, clear=True):

        plan_1 = _sample_workout_plan(days_per_week=3, split_type="FULL_BODY")
        saved_1 = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, plan_1)
        assert saved_1["is_active"] is True

        plan_2 = _sample_workout_plan(days_per_week=5, split_type="PPL")
        saved_2 = WorkoutPlanRepository.save_workout_plan(TEST_USER_ID, plan_2)
        assert saved_2["is_active"] is True

        records = list(db_mod._OFFLINE_TEST_DB["user_workout_plans"].values())
        assert len(records) == 2

        old_plan = next(r for r in records if r["id"] == saved_1["id"])
        new_plan = next(r for r in records if r["id"] == saved_2["id"])

        assert old_plan["is_active"] is False
        assert new_plan["is_active"] is True

        active = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
        assert active["id"] == saved_2["id"]
        assert active["split_type"] == "PPL"
        assert active["days_per_week"] == 5


# ==============================================================================
# 2. LIVE SUPABASE REPOSITORY TESTS (MOCK CLIENT)
# ==============================================================================

def test_live_supabase_meal_plan_repository_save_and_fetch():
    """Verifies live Supabase query shapes, RLS token forwarding, update & insert calls."""
    client_mock = MagicMock()
    # Mock update chain: client.table("user_meal_plans").update(...).eq(...).eq(...).execute()
    update_chain = client_mock.table.return_value.update.return_value.eq.return_value.eq.return_value.execute
    update_chain.return_value.data = []

    # Mock insert chain: client.table("user_meal_plans").insert(...).execute()
    saved_row = {"id": "uuid-123", "user_id": TEST_USER_ID, "is_active": True}
    client_mock.table.return_value.insert.return_value.execute.return_value.data = [saved_row]

    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client_mock):

        res = MealPlanRepository.save_meal_plan(
            TEST_USER_ID,
            _sample_meal_plan(),
            user_token=LIVE_TOKEN,
        )

        client_mock.postgrest.auth.assert_called_with(LIVE_TOKEN)
        client_mock.table.assert_called_with("user_meal_plans")
        table = client_mock.table.return_value
        table.update.assert_called_with({"is_active": False})
        assert res["id"] == "uuid-123"

        # Mock select chain: client.table("user_meal_plans").select("*").eq(...).eq(...).order(...).limit(...).execute()
        select_chain = (
            table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute
        )
        select_chain.return_value.data = [saved_row]

        fetched = MealPlanRepository.get_active_meal_plan(TEST_USER_ID, user_token=LIVE_TOKEN)
        assert fetched["id"] == "uuid-123"
        table.select.assert_called_with("*")


def test_live_supabase_workout_plan_repository_save_and_fetch():
    """Verifies live Supabase query shapes, RLS token forwarding, update & insert calls for workout plans."""
    client_mock = MagicMock()
    update_chain = client_mock.table.return_value.update.return_value.eq.return_value.eq.return_value.execute
    update_chain.return_value.data = []

    saved_row = {"id": "uuid-456", "user_id": TEST_USER_ID, "is_active": True}
    client_mock.table.return_value.insert.return_value.execute.return_value.data = [saved_row]

    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client_mock):

        res = WorkoutPlanRepository.save_workout_plan(
            TEST_USER_ID,
            _sample_workout_plan(),
            user_token=LIVE_TOKEN,
        )

        client_mock.postgrest.auth.assert_called_with(LIVE_TOKEN)
        client_mock.table.assert_called_with("user_workout_plans")
        table = client_mock.table.return_value
        table.update.assert_called_with({"is_active": False})
        assert res["id"] == "uuid-456"

        select_chain = (
            table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute
        )
        select_chain.return_value.data = [saved_row]

        fetched = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID, user_token=LIVE_TOKEN)
        assert fetched["id"] == "uuid-456"
        table.select.assert_called_with("*")


# ==============================================================================
# 3. API INTEGRATION TESTS (POST & GET ENDPOINTS)
# ==============================================================================

def test_meal_plan_api_persists_generated_plan():
    """POST /api/v1/planning/meal-plan persists the generated active plan to database."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True):

        payload = {
            "target_calories": 2200,
            "target_protein_g": 150.0,
            "target_carbs_g": 250.0,
            "target_fat_g": 65.0,
            "dietary_preference": "anything",
            "apply_adaptation": False,
        }
        res = client.post("/api/v1/planning/meal-plan", json=payload, headers=AUTH_HEADER)
        assert res.status_code == 200
        plan = res.json()
        assert plan["target_calories"] == 2200

        # Verify plan was persisted in repository
        persisted = MealPlanRepository.get_active_meal_plan(TEST_USER_ID)
        assert persisted is not None
        assert persisted["user_id"] == TEST_USER_ID
        assert persisted["is_active"] is True
        assert persisted["target_calories"] == 2200
        assert persisted["target_protein_g"] == 150
        assert persisted["plan_data"]["achieved_calories"] == plan["achieved_calories"]

        # Verify GET /api/v1/planning/active-meal-plan returns it
        get_res = client.get("/api/v1/planning/active-meal-plan", headers=AUTH_HEADER)
        assert get_res.status_code == 200
        active_api_plan = get_res.json()
        assert active_api_plan["id"] == persisted["id"]
        assert active_api_plan["is_active"] is True


def test_workout_plan_api_persists_generated_plan():
    """POST /api/v1/planning/workout-plan persists the generated active plan to database."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_workout_plans"], {}, clear=True):

        payload = {
            "goal_type": "fat_loss",
            "workout_days_per_week": 4,
            "experience_level": "intermediate",
            "apply_adaptation": False,
        }
        res = client.post("/api/v1/planning/workout-plan", json=payload, headers=AUTH_HEADER)
        assert res.status_code == 200
        plan = res.json()
        assert plan["split_type"] == "UPPER_LOWER"

        # Verify plan was persisted in repository
        persisted = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
        assert persisted is not None
        assert persisted["user_id"] == TEST_USER_ID
        assert persisted["is_active"] is True
        assert persisted["split_type"] == "UPPER_LOWER"
        assert persisted["days_per_week"] == 4
        assert persisted["routine_data"]["experience_level"] == "Intermediate"

        # Verify GET /api/v1/planning/active-workout-plan returns it
        get_res = client.get("/api/v1/planning/active-workout-plan", headers=AUTH_HEADER)
        assert get_res.status_code == 200
        active_api_plan = get_res.json()
        assert active_api_plan["id"] == persisted["id"]
        assert active_api_plan["is_active"] is True


def test_meal_plan_api_apply_adaptation_false_persists_baseline():
    """apply_adaptation=False generates and persists the unadjusted baseline plan."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True):

        payload = {
            "target_calories": 2500,
            "target_protein_g": 160.0,
            "target_carbs_g": 300.0,
            "target_fat_g": 70.0,
            "dietary_preference": "vegetarian",
            "apply_adaptation": False,
        }
        res = client.post("/api/v1/planning/meal-plan", json=payload, headers=AUTH_HEADER)
        assert res.status_code == 200
        plan = res.json()
        assert plan["target_calories"] == 2500

        persisted = MealPlanRepository.get_active_meal_plan(TEST_USER_ID)
        assert persisted is not None
        assert persisted["target_calories"] == 2500
        assert persisted["plan_data"]["target_calories"] == 2500


def test_workout_plan_api_apply_adaptation_false_persists_baseline():
    """apply_adaptation=False generates and persists the unadjusted baseline workout plan."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_workout_plans"], {}, clear=True):

        payload = {
            "goal_type": "muscle_gain",
            "workout_days_per_week": 5,
            "experience_level": "intermediate",
            "apply_adaptation": False,
        }
        res = client.post("/api/v1/planning/workout-plan", json=payload, headers=AUTH_HEADER)
        assert res.status_code == 200
        plan = res.json()
        assert plan["split_type"] == "PPL"
        assert plan["days_per_week"] == 5

        persisted = WorkoutPlanRepository.get_active_workout_plan(TEST_USER_ID)
        assert persisted is not None
        assert persisted["split_type"] == "PPL"
        assert persisted["days_per_week"] == 5
        assert persisted["routine_data"]["deload_active"] is False


def test_consecutive_api_calls_archive_previous_plans():
    """Generating a second plan via API automatically deactivates/archives the first."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_workout_plans"], {}, clear=True):

        # First meal plan
        res1 = client.post("/api/v1/planning/meal-plan", json={
            "target_calories": 2000, "target_protein_g": 120.0, "target_carbs_g": 220.0,
            "target_fat_g": 60.0, "dietary_preference": "anything"
        }, headers=AUTH_HEADER)
        assert res1.status_code == 200

        # Second meal plan
        res2 = client.post("/api/v1/planning/meal-plan", json={
            "target_calories": 2400, "target_protein_g": 150.0, "target_carbs_g": 260.0,
            "target_fat_g": 70.0, "dietary_preference": "anything"
        }, headers=AUTH_HEADER)
        assert res2.status_code == 200

        all_meals = list(db_mod._OFFLINE_TEST_DB["user_meal_plans"].values())
        assert len(all_meals) == 2
        active_meals = [m for m in all_meals if m["is_active"] is True]
        archived_meals = [m for m in all_meals if m["is_active"] is False]
        assert len(active_meals) == 1
        assert len(archived_meals) == 1
        assert active_meals[0]["target_calories"] == 2400
        assert archived_meals[0]["target_calories"] == 2000

        # First workout plan
        w_res1 = client.post("/api/v1/planning/workout-plan", json={
            "goal_type": "fat_loss", "workout_days_per_week": 3, "experience_level": "beginner"
        }, headers=AUTH_HEADER)
        assert w_res1.status_code == 200

        # Second workout plan
        w_res2 = client.post("/api/v1/planning/workout-plan", json={
            "goal_type": "muscle_gain", "workout_days_per_week": 4, "experience_level": "intermediate"
        }, headers=AUTH_HEADER)
        assert w_res2.status_code == 200

        all_workouts = list(db_mod._OFFLINE_TEST_DB["user_workout_plans"].values())
        assert len(all_workouts) == 2
        active_workouts = [w for w in all_workouts if w["is_active"] is True]
        archived_workouts = [w for w in all_workouts if w["is_active"] is False]
        assert len(active_workouts) == 1
        assert len(archived_workouts) == 1
        assert active_workouts[0]["split_type"] == "UPPER_LOWER"
        assert archived_workouts[0]["split_type"] == "FULL_BODY"
