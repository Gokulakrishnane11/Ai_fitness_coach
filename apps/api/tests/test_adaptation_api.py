"""
FastAPI Integration Tests for Adaptation API Endpoint (Task 8).
Tests GET /api/v1/adaptation:
- 401 on unauthenticated / invalid token requests
- 404 on missing profile
- 422 on incomplete profile / target metrics calculation failure
- 200 on valid authenticated request with full AdaptationDecision schema validation
- Verified user_id from token is used (never query/body)
- Verified user_token (Supabase access_token) forwarded to pipeline & repositories
- Stale journal (>7d) does not produce journal advice
- Fresh journal (<=7d) produces journal-based advice
- Propagation of unexpected server errors (500)
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
from app.db.supabase import DailyLogRepository, ProfileRepository
from app.engine.adaptation import (
    AdaptationDecision,
    DEFAULT_JOURNAL_FRESHNESS_DAYS,
)
import app.modules.adaptation as adaptation_module

client = TestClient(app)

TEST_USER_ID = "user_adaptation_test"
AUTH_HEADER = {"Authorization": f"Bearer test_token_{TEST_USER_ID}"}

MOTIVATION_REC = "High motivation noted in recent journal. Channel energy into structured training."
FATIGUE_REC = "Recent journal reflects fatigue. Prioritize recovery and sleep."


def _valid_db_profile(**overrides):
    """Database-shaped profile row (no target_metrics, as stored in Supabase)."""
    row = {
        "id": TEST_USER_ID,
        "first_name": "Gokul",
        "gender": "male",
        "age": 25,
        "height_cm": 178.0,
        "weight_kg": 82.5,
        "target_weight_kg": 75.0,
        "body_fat_pct": None,
        "activity_level": "moderately_active",
        "goal_type": "fat_loss",
        "dietary_preference": "vegetarian",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "created_at": "2026-09-01T08:00:00+00:00",
        "updated_at": "2026-09-01T08:00:00+00:00",
    }
    row.update(overrides)
    return row


def _valid_db_logs(count=4):
    """List of valid daily log records."""
    return [
        {
            "id": f"log_{i}",
            "user_id": TEST_USER_ID,
            "log_date": f"2026-09-{20 - i:02d}",
            "weight_kg": round(82.5 - 0.1 * i, 1),
            "calories_consumed": 2100 - 20 * i,
            "protein_consumed_g": 160,
            "carbs_consumed_g": 200,
            "fat_consumed_g": 60,
            "water_liters": 3.0,
            "workout_completed": i % 2 == 0,
            "energy_rating": 8,
            "notes": "Good energy",
            "created_at": f"2026-09-{20 - i:02d}T20:00:00+00:00",
        }
        for i in range(count)
    ]


def _valid_journal_entry(created_at: str, sentiment: str, summary: str = "Training update"):
    return {
        "id": f"journal_{sentiment}",
        "user_id": TEST_USER_ID,
        "entry_text": f"Feeling {sentiment} today",
        "sentiment_tag": sentiment,
        "ai_feedback": {"summary": summary},
        "created_at": created_at,
    }


# ---------------------------------------------------------------------------
# 1. Authentication & Security Tests
# ---------------------------------------------------------------------------

def test_adaptation_unauthorized_without_token():
    """Unauthenticated request must return 401."""
    res = client.get("/api/v1/adaptation")
    assert res.status_code == 401
    assert "Missing authorization Bearer token" in res.json()["detail"]


def test_adaptation_unauthorized_invalid_token():
    """Request with invalid/malformed token must return 401."""
    headers = {"Authorization": "Bearer invalid_token_xyz"}
    res = client.get("/api/v1/adaptation", headers=headers)
    assert res.status_code == 401
    assert "Invalid authentication token" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Missing & Incomplete Profile Error Handling Tests
# ---------------------------------------------------------------------------

def test_adaptation_missing_profile_returns_404():
    """When user has no profile row in the database, returns 404."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True):
        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 404
        body = res.json()
        assert "Profile not found" in body["detail"]


def test_adaptation_incomplete_profile_missing_field_returns_422():
    """When profile is missing required metrics fields (e.g. height_cm), returns 422."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True):
        bad_profile = _valid_db_profile(height_cm=None)
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = bad_profile

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 422
        body = res.json()
        assert "height_cm" in body["detail"]


def test_adaptation_incomplete_profile_missing_goal_type_returns_422():
    """When profile is missing goal_type, returns 422."""
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True):
        bad_profile = _valid_db_profile(goal_type=None)
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = bad_profile

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 422
        body = res.json()
        assert "goal_type" in body["detail"]


# ---------------------------------------------------------------------------
# 3. User Identification & Token Forwarding Verification
# ---------------------------------------------------------------------------

def test_adaptation_user_id_from_context_and_token_forwarded():
    """
    Verifies that the endpoint extracts user_id strictly from UserContext (not query/body)
    and forwards both user_id and access_token to compute_adaptation_for_user.
    """
    custom_user = "user_isolated_jwt_999"
    custom_token = f"test_token_{custom_user}"
    custom_headers = {"Authorization": f"Bearer {custom_token}"}

    with patch.object(
        adaptation_module,
        "compute_adaptation_for_user",
        wraps=adaptation_module.compute_adaptation_for_user,
    ) as spy_compute, \
         patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile(id=custom_user)
        db_mod._OFFLINE_TEST_DB["profiles"][custom_user] = profile

        # Attempt to pass an injection in query string (must be ignored)
        res = client.get(
            "/api/v1/adaptation?user_id=attacker_user",
            headers=custom_headers,
        )
        assert res.status_code == 200

        spy_compute.assert_called_once_with(
            user_id=custom_user,
            user_token=custom_token,
        )


# ---------------------------------------------------------------------------
# 4. Valid Request & Schema Validation Tests
# ---------------------------------------------------------------------------

def test_adaptation_valid_authenticated_request_returns_200_and_validates_schema():
    """
    Valid authenticated request returns 200 and a complete response
    that strictly satisfies the AdaptationDecision Pydantic schema.
    """
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile()
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile
        for log in _valid_db_logs(4):
            db_mod._OFFLINE_TEST_DB["daily_logs"][log["id"]] = dict(log)

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()

        # Validate with AdaptationDecision model
        decision = AdaptationDecision.model_validate(data)
        assert isinstance(decision, AdaptationDecision)
        assert decision.adherence_score >= 0
        assert decision.recovery_score >= 0
        assert decision.readiness_factor >= 0.45
        assert decision.readiness_factor <= 1.12
        assert decision.diet_adjustment.calorie_delta == 0
        assert decision.workout_adjustment.intensity == "maintain"
        # Without empirical sensor scores (recovery, stress, etc.), honest state is False
        assert decision.objective_data_available is False
        assert "Not enough objective data" in decision.coaching_summary


def test_adaptation_with_objective_signals_reports_available():
    """
    When objective data is available (e.g. recovery_score or adherence signals present),
    the endpoint returns 200 with objective_data_available=True.
    """
    mock_decision = AdaptationDecision(
        adherence_score=95,
        recovery_score=85,
        stress_score=20,
        sleep_quality=80,
        plateau_probability=5,
        injury_risk=5,
        readiness_factor=1.05,
        plateau_detected=False,
        high_fatigue_flag=False,
        coaching_summary="Consistent progress and healthy readiness metrics observed across recent logs.",
        objective_data_available=True,
    )
    with patch.object(
        adaptation_module,
        "compute_adaptation_for_user",
        return_value=mock_decision,
    ):
        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()
        assert data["objective_data_available"] is True
        assert "Consistent progress" in data["coaching_summary"]


# ---------------------------------------------------------------------------
# 5. Fresh vs Stale Journal Freshness Tests
# ---------------------------------------------------------------------------

def test_adaptation_fresh_journal_produces_coaching_advice():
    """
    A fresh journal entry (logged within the 7-day freshness window)
    influences actionable recommendations.
    """
    now_utc = datetime.now(timezone.utc)
    fresh_timestamp = (now_utc - timedelta(days=1)).isoformat()

    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile()
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile
        for log in _valid_db_logs(4):
            db_mod._OFFLINE_TEST_DB["daily_logs"][log["id"]] = dict(log)

        fresh_entry = _valid_journal_entry(fresh_timestamp, "motivated")
        db_mod._OFFLINE_TEST_DB["journal_entries"]["j_fresh"] = fresh_entry

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()
        assert MOTIVATION_REC in data["actionable_recommendations"]


def test_adaptation_stale_journal_does_not_produce_coaching_advice():
    """
    A stale journal entry (logged 10 days ago, >7-day freshness window)
    is filtered out and does not influence recommendations.
    """
    now_utc = datetime.now(timezone.utc)
    stale_timestamp = (now_utc - timedelta(days=10)).isoformat()

    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile()
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile
        for log in _valid_db_logs(4):
            db_mod._OFFLINE_TEST_DB["daily_logs"][log["id"]] = dict(log)

        stale_entry = _valid_journal_entry(stale_timestamp, "motivated")
        db_mod._OFFLINE_TEST_DB["journal_entries"]["j_stale"] = stale_entry

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()
        assert MOTIVATION_REC not in data["actionable_recommendations"]


# ---------------------------------------------------------------------------
# 6. Objective Data Availability & Neutral Fallback Tests
# ---------------------------------------------------------------------------

def test_adaptation_under_three_logs_reports_baseline_summary():
    """
    When the user has a profile but fewer than 3 daily logs (e.g. 0 logs),
    returns 200 with objective_data_available=False, neutral readiness 1.0,
    and the baseline logging prompt summary.
    """
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile()
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()
        assert data["objective_data_available"] is False
        assert data["coaching_summary"] == "Baseline targets active. Maintain consistent logging to enable personalized adaptations."
        assert data["readiness_factor"] == 1.0


def test_adaptation_sufficient_logs_without_sensors_reports_honest_summary():
    """
    When user has >=3 daily logs but no sensor scores (recovery, stress, etc.),
    returns 200 with objective_data_available=False and honest no-data summary.
    """
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile()
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile
        for log in _valid_db_logs(4):
            db_mod._OFFLINE_TEST_DB["daily_logs"][log["id"]] = dict(log)

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()
        assert data["objective_data_available"] is False
        assert "Not enough objective data" in data["coaching_summary"]


# ---------------------------------------------------------------------------
# 7. Unhandled Server Error Propagation (500)
# ---------------------------------------------------------------------------

def test_adaptation_unexpected_exception_propagates_as_500():
    """
    Unexpected exceptions (e.g. database network collapse, unhandled RuntimeError)
    must not be swallowed or converted into 404/422.
    """
    with patch.object(
        adaptation_module,
        "compute_adaptation_for_user",
        side_effect=RuntimeError("Supabase connection reset by peer"),
    ):
        with pytest.raises(RuntimeError, match="connection reset"):
            client.get("/api/v1/adaptation", headers=AUTH_HEADER)


# ---------------------------------------------------------------------------
# 8. Live Dynamic Output Integration Tests (Task 13-1)
# ---------------------------------------------------------------------------

def _plateau_logs_28d(
    weight_kg: float = 82.5,
    count: int = 29,
    calories: float = 3155.0,
    protein_g: float = 165.0,
    carbs_g: float = 427.0,
    fat_g: float = 88.0,
):
    """
    Creates 29 daily logs spanning 28 full calendar days with invariant weight,
    consistent workouts, and aligned nutrition to trigger empirical adherence and plateau.
    """
    from datetime import date
    base = date(2026, 8, 1)
    logs = []
    for i in range(count):
        d = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        logs.append({
            "id": f"plateau_log_{i}",
            "user_id": TEST_USER_ID,
            "log_date": d,
            "weight_kg": weight_kg,
            "calories_consumed": calories,
            "protein_consumed_g": protein_g,
            "carbs_consumed_g": carbs_g,
            "fat_consumed_g": fat_g,
            "water_liters": 3.0,
            "workout_completed": True,
            "energy_rating": 8,
            "notes": "Plateau integration test log",
            "created_at": f"{d}T12:00:00+00:00",
        })
    return logs


def test_adaptation_api_live_muscle_gain_plateau_produces_dynamic_diet_surplus():
    """
    Live integration test: Seeds offline DB with 29 daily logs representing a
    weight plateau under muscle_gain with high adherence.
    Calls GET /api/v1/adaptation through TestClient.
    Verifies that real HTTP JSON response returns:
      diet_adjustment.calorie_delta == 150
      carb_delta_g == 25.0
      fat_delta_g == 5.5
      protein_delta_g == 0.0
    and workout adjustment remains baseline maintain/medium.
    """
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile(goal_type="muscle_gain", target_weight_kg=85.0)
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile

        # For male 82.5kg, 178cm, 25yo, moderately_active, muscle_gain:
        # target_calories is 3155, protein 165g, carbs 426.7g, fat 87.6g
        for log in _plateau_logs_28d(calories=3155, protein_g=165, carbs_g=427, fat_g=88):
            db_mod._OFFLINE_TEST_DB["daily_logs"][log["id"]] = dict(log)

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()

        # Schema validation
        decision = AdaptationDecision.model_validate(data)
        assert decision.plateau_detected is True
        assert decision.objective_data_available is True

        # Dynamic diet adjustment values in JSON response
        assert data["diet_adjustment"]["calorie_delta"] == 150
        assert data["diet_adjustment"]["carb_delta_g"] == 25.0
        assert data["diet_adjustment"]["fat_delta_g"] == 5.5
        assert data["diet_adjustment"]["protein_delta_g"] == 0.0

        # Workout adjustment remains neutral baseline for muscle_gain plateau
        assert data["workout_adjustment"]["intensity"] == "maintain"
        assert data["workout_adjustment"]["volume"] == "medium"
        assert data["workout_adjustment"]["cardio_minutes"] == 0
        assert data["workout_adjustment"]["deload_recommended"] is False


def test_adaptation_api_live_fat_loss_plateau_produces_cardio_without_diet_cut():
    """
    Live integration test: Seeds offline DB with 29 daily logs representing a
    weight plateau under fat_loss with high adherence.
    Calls GET /api/v1/adaptation through TestClient.
    Verifies that single-intervention rule survives the API boundary:
      workout_adjustment.cardio_minutes == 30
      diet_adjustment.calorie_delta == 0
    """
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):

        profile = _valid_db_profile(goal_type="fat_loss", target_weight_kg=75.0)
        db_mod._OFFLINE_TEST_DB["profiles"][TEST_USER_ID] = profile

        # For male 82.5kg, 178cm, 25yo, moderately_active, fat_loss:
        # target_calories is 2254, protein 181.5g, carbs 233.4g, fat 66.0g
        for log in _plateau_logs_28d(calories=2254, protein_g=181.5, carbs_g=233.4, fat_g=66.0):
            db_mod._OFFLINE_TEST_DB["daily_logs"][log["id"]] = dict(log)

        res = client.get("/api/v1/adaptation", headers=AUTH_HEADER)
        assert res.status_code == 200
        data = res.json()

        # Schema validation
        decision = AdaptationDecision.model_validate(data)
        assert decision.plateau_detected is True
        assert decision.objective_data_available is True

        # Workout adjustment introduces cardio intervention
        assert data["workout_adjustment"]["cardio_minutes"] == 30
        assert data["workout_adjustment"]["intensity"] == "maintain"
        assert data["workout_adjustment"]["volume"] == "medium"
        assert data["workout_adjustment"]["deload_recommended"] is False

        # Diet adjustment remains neutral (no simultaneous deficit)
        assert data["diet_adjustment"]["calorie_delta"] == 0
        assert data["diet_adjustment"]["protein_delta_g"] == 0.0
        assert data["diet_adjustment"]["carb_delta_g"] == 0.0
        assert data["diet_adjustment"]["fat_delta_g"] == 0.0
