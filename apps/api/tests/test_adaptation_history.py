"""
Unit & Integration Tests for Adaptation History & Decision Audit Trail (Phase 4C).
Covers:
1. save and retrieve history
2. newest-first ordering
3. limit=1
4. limit=30
5. limit=100
6. invalid limit rejected (FastAPI 422 on limit < 1 or limit > 100)
7. empty history returns 200 with empty list
8. user isolation (User A cannot access User B records)
9. unauthenticated API returns 401
10. decision fields persisted correctly
11. diet adjustment persisted
12. workout adjustment persisted
13. actionable recommendations persisted
14. coaching summary persisted
15. input_snapshot persisted
16. active meal plan ID persisted
17. active workout plan ID persisted
18. missing active plans handled cleanly as None
19. duplicate identical adaptation evaluation does not create duplicate rows
20. changed telemetry creates new history row
21. changed active plan creates new history row
22. offline repository isolation
23. live Supabase repository query shape
24. RLS token forwarding to PostgREST
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db import supabase as db_mod
from app.db.supabase import (
    AdaptationHistoryRepository,
    ProfileRepository,
    DailyLogRepository,
    MealPlanRepository,
    WorkoutPlanRepository,
)
from app.engine.adaptation import (
    AdaptationDecision,
    DietAdjustment,
    WorkoutAdjustment,
)
from app.modules.adaptation import persist_adaptation_snapshot

client = TestClient(app)

TEST_USER_A = "user_hist_test_a"
TEST_USER_B = "user_hist_test_b"
AUTH_HEADER_A = {"Authorization": f"Bearer test_token_{TEST_USER_A}"}
AUTH_HEADER_B = {"Authorization": f"Bearer test_token_{TEST_USER_B}"}
LIVE_TOKEN = "valid_user_jwt_token_for_adaptation_history_test"


def _sample_decision(**overrides) -> AdaptationDecision:
    base = {
        "adherence_score": 95,
        "recovery_score": 85,
        "stress_score": 20,
        "sleep_quality": 90,
        "plateau_probability": 10,
        "injury_risk": 15,
        "readiness_factor": 0.92,
        "plateau_detected": False,
        "high_fatigue_flag": False,
        "diet_adjustment": DietAdjustment(
            calorie_delta=0,
            protein_delta_g=0.0,
            carb_delta_g=0.0,
            fat_delta_g=0.0,
        ),
        "workout_adjustment": WorkoutAdjustment(
            intensity="maintain",
            volume="medium",
            recovery_days=0,
            cardio_minutes=0,
            deload_recommended=False,
        ),
        "actionable_recommendations": ["Recovery and sleep are optimal."],
        "coaching_summary": "Consistent progress observed across recent logs.",
        "objective_data_available": True,
    }
    base.update(overrides)
    return AdaptationDecision(**base)


def _sample_profile(user_id: str = TEST_USER_A, **overrides):
    base = {
        "id": user_id,
        "first_name": "TestUser",
        "gender": "male",
        "age": 28,
        "height_cm": 178.0,
        "weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "activity_level": "moderately_active",
        "goal_type": "fat_loss",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "dietary_preference": "anything",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Repository Tests (Offline Mode)
# ---------------------------------------------------------------------------

def test_save_and_retrieve_history():
    """Requirement 1, 10, 11, 12, 13, 14, 15: Save and retrieve full adaptation history record."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        rec_data = {
            "readiness_factor": 0.917,
            "high_fatigue_flag": False,
            "plateau_detected": False,
            "adherence_score": 90,
            "recovery_score": 85,
            "stress_score": 20,
            "sleep_quality": 90,
            "injury_risk": 15,
            "plateau_probability": 10,
            "diet_adjustment": {"calorie_delta": 0, "protein_delta_g": 0.0, "carb_delta_g": 0.0, "fat_delta_g": 0.0},
            "workout_adjustment": {"intensity": "maintain", "volume": "medium", "recovery_days": 0, "cardio_minutes": 0, "deload_recommended": False},
            "actionable_recommendations": ["Great recovery today."],
            "coaching_summary": "Maintain steady habits.",
            "objective_data_available": True,
            "active_meal_plan_id": "meal-plan-uuid-1",
            "active_workout_plan_id": "workout-plan-uuid-1",
            "input_snapshot": {"recovery_score": 85.0, "log_count": 7},
        }

        saved = AdaptationHistoryRepository.save_history(TEST_USER_A, rec_data)
        assert saved["id"].startswith("adapt_")
        assert saved["user_id"] == TEST_USER_A
        assert saved["readiness_factor"] == 0.917
        assert saved["active_meal_plan_id"] == "meal-plan-uuid-1"
        assert saved["input_snapshot"]["recovery_score"] == 85.0

        history = AdaptationHistoryRepository.get_history(TEST_USER_A, limit=10)
        assert len(history) == 1
        assert history[0]["id"] == saved["id"]
        assert history[0]["diet_adjustment"]["calorie_delta"] == 0
        assert history[0]["workout_adjustment"]["intensity"] == "maintain"
        assert history[0]["actionable_recommendations"] == ["Great recovery today."]


def test_newest_first_ordering():
    """Requirement 2: Multiple records are returned in descending chronological order (created_at DESC)."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        now = datetime.now(timezone.utc)
        r1 = {"readiness_factor": 0.70, "created_at": (now - timedelta(days=2)).isoformat(), "input_snapshot": {}}
        r2 = {"readiness_factor": 0.85, "created_at": (now - timedelta(days=1)).isoformat(), "input_snapshot": {}}
        r3 = {"readiness_factor": 0.95, "created_at": now.isoformat(), "input_snapshot": {}}

        AdaptationHistoryRepository.save_history(TEST_USER_A, r1)
        AdaptationHistoryRepository.save_history(TEST_USER_A, r2)
        AdaptationHistoryRepository.save_history(TEST_USER_A, r3)

        history = AdaptationHistoryRepository.get_history(TEST_USER_A, limit=10)
        assert len(history) == 3
        # Newest first
        assert history[0]["readiness_factor"] == 0.95
        assert history[1]["readiness_factor"] == 0.85
        assert history[2]["readiness_factor"] == 0.70


def test_history_limit_parameter():
    """Requirement 3, 4, 5, 22: get_history respects limit=1, limit=30, limit=100 and clamps properly."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        for i in range(50):
            AdaptationHistoryRepository.save_history(
                TEST_USER_A,
                {"readiness_factor": 0.50 + i * 0.01, "created_at": f"2026-09-{i+1:02d}T10:00:00Z", "input_snapshot": {}},
            )

        # limit=1
        h1 = AdaptationHistoryRepository.get_history(TEST_USER_A, limit=1)
        assert len(h1) == 1

        # limit=30
        h30 = AdaptationHistoryRepository.get_history(TEST_USER_A, limit=30)
        assert len(h30) == 30

        # limit=100 (returns all 50 available)
        h100 = AdaptationHistoryRepository.get_history(TEST_USER_A, limit=100)
        assert len(h100) == 50


def test_user_isolation_offline():
    """Requirement 8, 22: User A cannot access User B's adaptation records."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        AdaptationHistoryRepository.save_history(TEST_USER_A, {"readiness_factor": 0.90, "input_snapshot": {}})
        AdaptationHistoryRepository.save_history(TEST_USER_B, {"readiness_factor": 0.65, "input_snapshot": {}})

        hist_a = AdaptationHistoryRepository.get_history(TEST_USER_A)
        assert len(hist_a) == 1
        assert hist_a[0]["user_id"] == TEST_USER_A
        assert hist_a[0]["readiness_factor"] == 0.90

        hist_b = AdaptationHistoryRepository.get_history(TEST_USER_B)
        assert len(hist_b) == 1
        assert hist_b[0]["user_id"] == TEST_USER_B
        assert hist_b[0]["readiness_factor"] == 0.65


# ---------------------------------------------------------------------------
# 2. API Endpoint Integration Tests
# ---------------------------------------------------------------------------

def test_api_unauthenticated_returns_401():
    """Requirement 9: Unauthenticated requests to /adaptation/history return HTTP 401."""
    res = client.get("/api/v1/adaptation/history")
    assert res.status_code == 401


def test_api_empty_history_returns_200():
    """Requirement 7: Empty history returns HTTP 200 with empty list."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        res = client.get("/api/v1/adaptation/history", headers=AUTH_HEADER_A)
        assert res.status_code == 200
        data = res.json()
        assert data["history"] == []
        assert data["count"] == 0


def test_api_invalid_limit_rejected():
    """Requirement 6: Query validation rejects limit < 1 or limit > 100 with 422."""
    res_low = client.get("/api/v1/adaptation/history?limit=0", headers=AUTH_HEADER_A)
    assert res_low.status_code == 422

    res_high = client.get("/api/v1/adaptation/history?limit=101", headers=AUTH_HEADER_A)
    assert res_high.status_code == 422


def test_api_get_history_full_schema_and_ordering():
    """Requirement 1, 2, 10, 11, 12, 13, 14, 15, 16, 17: GET /history returns valid schema and newest-first order."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        r1 = {
            "readiness_factor": 0.65,
            "high_fatigue_flag": True,
            "plateau_detected": False,
            "adherence_score": 70,
            "recovery_score": 30,
            "stress_score": 80,
            "sleep_quality": 40,
            "injury_risk": 75,
            "plateau_probability": 0,
            "diet_adjustment": {"calorie_delta": -100, "protein_delta_g": 0.0, "carb_delta_g": -20.0, "fat_delta_g": 0.0},
            "workout_adjustment": {"intensity": "reduce", "volume": "low", "recovery_days": 2, "cardio_minutes": 0, "deload_recommended": True},
            "actionable_recommendations": ["Recovery score is low.", "Stress score is elevated."],
            "coaching_summary": "Elevated fatigue detected. Prioritize recovery.",
            "objective_data_available": True,
            "active_meal_plan_id": "m-plan-1",
            "active_workout_plan_id": "w-plan-1",
            "input_snapshot": {"recovery_score": 30.0, "stress_score": 80.0},
            "created_at": "2026-09-28T10:00:00Z",
        }
        r2 = {
            "readiness_factor": 0.92,
            "high_fatigue_flag": False,
            "plateau_detected": False,
            "adherence_score": 95,
            "recovery_score": 85,
            "stress_score": 20,
            "sleep_quality": 90,
            "injury_risk": 15,
            "plateau_probability": 0,
            "diet_adjustment": {"calorie_delta": 0, "protein_delta_g": 0.0, "carb_delta_g": 0.0, "fat_delta_g": 0.0},
            "workout_adjustment": {"intensity": "maintain", "volume": "medium", "recovery_days": 0, "cardio_minutes": 0, "deload_recommended": False},
            "actionable_recommendations": [],
            "coaching_summary": "Consistent progress and healthy readiness metrics observed.",
            "objective_data_available": True,
            "active_meal_plan_id": "m-plan-2",
            "active_workout_plan_id": "w-plan-2",
            "input_snapshot": {"recovery_score": 85.0, "stress_score": 20.0},
            "created_at": "2026-09-30T10:00:00Z",
        }

        AdaptationHistoryRepository.save_history(TEST_USER_A, r1)
        AdaptationHistoryRepository.save_history(TEST_USER_A, r2)

        res = client.get("/api/v1/adaptation/history?limit=10", headers=AUTH_HEADER_A)
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 2
        items = body["history"]
        assert len(items) == 2

        # Item 0 must be newer (2026-09-30)
        assert items[0]["readiness_factor"] == 0.92
        assert items[0]["high_fatigue_flag"] is False
        assert items[0]["active_meal_plan_id"] == "m-plan-2"
        assert items[0]["workout_adjustment"]["deload_recommended"] is False

        # Item 1 must be older (2026-09-28)
        assert items[1]["readiness_factor"] == 0.65
        assert items[1]["high_fatigue_flag"] is True
        assert items[1]["active_meal_plan_id"] == "m-plan-1"
        assert items[1]["workout_adjustment"]["deload_recommended"] is True


def test_api_user_isolation():
    """Requirement 8: User A cannot see User B's history via the API."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        AdaptationHistoryRepository.save_history(TEST_USER_A, {
            "readiness_factor": 0.95, "coaching_summary": "Summary A", "input_snapshot": {}
        })
        AdaptationHistoryRepository.save_history(TEST_USER_B, {
            "readiness_factor": 0.60, "coaching_summary": "Summary B", "input_snapshot": {}
        })

        res_a = client.get("/api/v1/adaptation/history", headers=AUTH_HEADER_A)
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["count"] == 1
        assert data_a["history"][0]["user_id"] == TEST_USER_A
        assert data_a["history"][0]["coaching_summary"] == "Summary A"

        res_b = client.get("/api/v1/adaptation/history", headers=AUTH_HEADER_B)
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["count"] == 1
        assert data_b["history"][0]["user_id"] == TEST_USER_B
        assert data_b["history"][0]["coaching_summary"] == "Summary B"


# ---------------------------------------------------------------------------
# 3. Deduplication & Snapshot Creation Tests
# ---------------------------------------------------------------------------

def test_deduplication_prevents_duplicate_history_rows():
    """Requirement 19: Repeated GET /adaptation evaluations with identical state do NOT insert duplicate rows."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        # Setup user profile
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_A] = _sample_profile(TEST_USER_A)

        # Call GET /adaptation 3 times
        r1 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r1.status_code == 200

        r2 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r2.status_code == 200

        r3 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r3.status_code == 200

        # Must have exactly 1 history row stored, not 3
        history_rows = list(db_mod._OFFLINE_TEST_DB["adaptation_history"].values())
        user_rows = [r for r in history_rows if r["user_id"] == TEST_USER_A]
        assert len(user_rows) == 1


def test_changed_telemetry_creates_new_history_row():
    """Requirement 20: Submitting new telemetry alters inputs and triggers a new history row on next adaptation."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_A] = _sample_profile(TEST_USER_A)

        # First evaluation
        r1 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r1.status_code == 200
        assert len(db_mod._OFFLINE_TEST_DB["adaptation_history"]) == 1

        # User submits high fatigue telemetry log
        log_payload = {
            "log_date": "2026-09-30",
            "recovery_score": 30,
            "sleep_quality": 40,
            "stress_level": 80,
            "muscle_soreness": 75,
        }
        res_log = client.post("/api/v1/progress/logs", json=log_payload, headers=AUTH_HEADER_A)
        assert res_log.status_code == 201

        # Second evaluation after telemetry change
        r2 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r2.status_code == 200

        # Now there should be 2 distinct history rows
        user_rows = [r for r in db_mod._OFFLINE_TEST_DB["adaptation_history"].values() if r["user_id"] == TEST_USER_A]
        assert len(user_rows) == 2


def test_changed_active_plan_creates_new_history_row():
    """Requirement 16, 17, 18, 21: Changing active meal or workout plan creates a new historical snapshot."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["user_meal_plans"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_A] = _sample_profile(TEST_USER_A)

        # Baseline evaluation without active plans
        r1 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r1.status_code == 200
        user_rows = [r for r in db_mod._OFFLINE_TEST_DB["adaptation_history"].values() if r["user_id"] == TEST_USER_A]
        assert len(user_rows) == 1
        assert user_rows[0]["active_meal_plan_id"] is None

        # User generates a new active meal plan
        meal_plan_data = {
            "title": "Active High Protein Plan",
            "target_calories": 2400,
            "target_protein_g": 160.0,
            "target_carbs_g": 260.0,
            "target_fat_g": 70.0,
        }
        saved_plan = MealPlanRepository.save_meal_plan(TEST_USER_A, meal_plan_data)
        assert saved_plan["id"] is not None

        # Evaluation after active plan creation
        r2 = client.get("/api/v1/adaptation", headers=AUTH_HEADER_A)
        assert r2.status_code == 200

        user_rows_after = [r for r in db_mod._OFFLINE_TEST_DB["adaptation_history"].values() if r["user_id"] == TEST_USER_A]
        assert len(user_rows_after) == 2
        # The latest record must have the active meal plan ID
        latest_rec = AdaptationHistoryRepository.get_latest_history(TEST_USER_A)
        assert latest_rec is not None
        assert latest_rec["active_meal_plan_id"] == saved_plan["id"]


# ---------------------------------------------------------------------------
# 4. Live Supabase Mock & Token Forwarding Tests
# ---------------------------------------------------------------------------

def test_live_supabase_repository_query_shape_and_token_forwarding():
    """Requirement 23, 24: Verifies live Supabase query shapes, RLS token forwarding, and insert calls."""
    client_mock = MagicMock()
    saved_row = {
        "id": "uuid-adapt-999",
        "user_id": TEST_USER_A,
        "readiness_factor": 0.92,
        "created_at": "2026-09-30T10:00:00Z",
    }
    client_mock.table.return_value.insert.return_value.execute.return_value.data = [saved_row]

    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client_mock):

        res = AdaptationHistoryRepository.save_history(
            TEST_USER_A,
            {"readiness_factor": 0.92, "input_snapshot": {}},
            user_token=LIVE_TOKEN,
        )

        client_mock.postgrest.auth.assert_called_with(LIVE_TOKEN)
        client_mock.table.assert_called_with("adaptation_history")
        assert res["id"] == "uuid-adapt-999"

        # Mock select query chain
        select_chain = (
            client_mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute
        )
        select_chain.return_value.data = [saved_row]

        fetched = AdaptationHistoryRepository.get_history(TEST_USER_A, user_token=LIVE_TOKEN, limit=15)
        assert len(fetched) == 1
        assert fetched[0]["id"] == "uuid-adapt-999"
        client_mock.table.return_value.select.assert_called_with("*")
