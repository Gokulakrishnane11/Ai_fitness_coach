"""
Unit & Integration Tests for Adaptation Explainability (Phase 4C).
Covers:
1. AdaptationDecision includes structured reasons list.
2. Low recovery produces the expected recovery reason (negative, < 50).
3. Poor sleep produces the expected sleep reason (negative, < 60).
4. High stress produces the expected stress reason (negative, >= 60).
5. High injury risk/soreness produces the expected injury-risk reason (negative, >= 50).
6. Healthy telemetry produces appropriate positive reasons (recovery >= 80, sleep >= 80, stress <= 30, soreness <= 25, adherence >= 80).
7. Baseline / no-objective-data produces a neutral reason.
8. Reasons are persisted in adaptation history (input_snapshot["reasons"]).
9. GET /api/v1/adaptation/history returns reasons.
10. Legacy history records without reasons or malformed reasons safely deserialize with reasons=[].
11. User isolation remains intact (User A cannot access User B's reasons).
12. Existing adaptation outputs remain unchanged apart from the new metadata.
13. Duplicate history protection still works when reasons are present.
"""

import sys
import os
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.engine.adaptation import (
    AdaptationInput,
    AdaptationDecision,
    AdaptationReason,
    DietAdjustment,
    WorkoutAdjustment,
    compute_adaptation,
)
from app.modules.adaptation import (
    AdaptationHistoryRecord,
    persist_adaptation_snapshot,
)

client = TestClient(app)

USER_A = "user_explainability_a"
USER_B = "user_explainability_b"
AUTH_A = {"Authorization": f"Bearer test_token_{USER_A}"}
AUTH_B = {"Authorization": f"Bearer test_token_{USER_B}"}


def _make_input(**overrides) -> AdaptationInput:
    base = {
        "user_id": USER_A,
        "current_weight_kg": 75.0,
        "target_weight_kg": 70.0,
        "goal_type": "fat_loss",
        "target_calories": 2200,
        "target_protein_g": 160.0,
        "target_carbs_g": 220.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "log_count": 7,
        "adherence_percent": 85.0,
        "recovery_score": 75,
        "sleep_quality": 75,
        "stress_score": 40,
        "injury_risk": 20,
        "plateau_probability": 10,
        "nutrition_score": 85.0,
        "training_quality": 80.0,
        "weight_change_kg_7d": -0.3,
        "weight_change_kg_14d": -0.6,
        "weight_change_kg_28d": -1.2,
        "latest_journal_summary": "Feeling steady",
        "latest_journal_sentiment": "consistent",
    }
    base.update(overrides)
    return AdaptationInput(**base)


def _sample_profile(user_id: str = USER_A, **overrides) -> Dict[str, Any]:
    base = {
        "id": user_id,
        "first_name": "Test",
        "gender": "male",
        "age": 28,
        "height_cm": 178.0,
        "weight_kg": 75.0,
        "current_weight_kg": 75.0,
        "target_weight_kg": 70.0,
        "activity_level": "moderate",
        "goal_type": "fat_loss",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "target_calories": 2200,
        "target_protein_g": 160.0,
        "target_carbs_g": 220.0,
        "target_fat_g": 60.0,
        "target_metrics": {
            "target_calories": 2200,
            "protein_g": 160.0,
            "carbs_g": 220.0,
            "fat_g": 60.0,
        },
    }
    base.update(overrides)
    return base


# ===========================================================================
# 1. AdaptationDecision includes reasons
# ===========================================================================
def test_adaptation_decision_includes_reasons():
    inp = _make_input()
    decision = compute_adaptation(inp)
    assert hasattr(decision, "reasons")
    assert isinstance(decision.reasons, list)
    for r in decision.reasons:
        assert isinstance(r, AdaptationReason)
        assert r.signal != ""
        assert r.effect in ("positive", "neutral", "negative")
        assert len(r.message) > 0


# ===========================================================================
# 2. Low recovery produces expected recovery reason (< 50)
# ===========================================================================
def test_low_recovery_produces_expected_reason():
    inp = _make_input(recovery_score=30)
    decision = compute_adaptation(inp)
    rec_reasons = [r for r in decision.reasons if r.signal == "recovery_score"]
    assert len(rec_reasons) == 1
    reason = rec_reasons[0]
    assert reason.value == 30
    assert reason.effect == "negative"
    assert "Low recovery capacity detected" in reason.message
    assert decision.high_fatigue_flag is True


# ===========================================================================
# 3. Poor sleep produces expected sleep reason (< 60)
# ===========================================================================
def test_poor_sleep_produces_expected_reason():
    inp = _make_input(sleep_quality=40)
    decision = compute_adaptation(inp)
    sleep_reasons = [r for r in decision.reasons if r.signal == "sleep_quality"]
    assert len(sleep_reasons) == 1
    reason = sleep_reasons[0]
    assert reason.value == 40
    assert reason.effect == "negative"
    assert "Poor sleep quality reported" in reason.message


# ===========================================================================
# 4. High stress produces expected stress reason (>= 60)
# ===========================================================================
def test_high_stress_produces_expected_reason():
    inp = _make_input(stress_score=80)
    decision = compute_adaptation(inp)
    stress_reasons = [r for r in decision.reasons if r.signal == "stress_score"]
    assert len(stress_reasons) == 1
    reason = stress_reasons[0]
    assert reason.value == 80
    assert reason.effect == "negative"
    assert "Elevated stress detected" in reason.message


# ===========================================================================
# 5. High injury risk / muscle soreness produces expected reason (>= 50)
# ===========================================================================
def test_high_injury_risk_produces_expected_reason():
    inp = _make_input(injury_risk=75)
    decision = compute_adaptation(inp)
    injury_reasons = [r for r in decision.reasons if r.signal == "injury_risk"]
    assert len(injury_reasons) == 1
    reason = injury_reasons[0]
    assert reason.value == 75
    assert reason.effect == "negative"
    assert "Elevated muscle soreness detected" in reason.message


# ===========================================================================
# 6. Healthy telemetry produces appropriate positive reasons
# ===========================================================================
def test_healthy_telemetry_produces_positive_reasons():
    inp = _make_input(
        recovery_score=85,
        sleep_quality=90,
        stress_score=20,
        injury_risk=15,
        adherence_percent=95.0,
    )
    decision = compute_adaptation(inp)
    reasons_by_signal = {r.signal: r for r in decision.reasons}

    # Recovery (>= 80)
    assert "recovery_score" in reasons_by_signal
    assert reasons_by_signal["recovery_score"].effect == "positive"
    assert reasons_by_signal["recovery_score"].value == 85
    assert "Optimal physiological recovery" in reasons_by_signal["recovery_score"].message

    # Sleep (>= 80)
    assert "sleep_quality" in reasons_by_signal
    assert reasons_by_signal["sleep_quality"].effect == "positive"
    assert reasons_by_signal["sleep_quality"].value == 90
    assert "High sleep quality" in reasons_by_signal["sleep_quality"].message

    # Stress (<= 30)
    assert "stress_score" in reasons_by_signal
    assert reasons_by_signal["stress_score"].effect == "positive"
    assert reasons_by_signal["stress_score"].value == 20
    assert "Low systemic stress" in reasons_by_signal["stress_score"].message

    # Soreness (<= 25)
    assert "injury_risk" in reasons_by_signal
    assert reasons_by_signal["injury_risk"].effect == "positive"
    assert reasons_by_signal["injury_risk"].value == 15
    assert "Minimal muscle soreness" in reasons_by_signal["injury_risk"].message

    # Adherence (>= 80)
    assert "adherence" in reasons_by_signal
    assert reasons_by_signal["adherence"].effect == "positive"
    assert reasons_by_signal["adherence"].value == 95.0
    assert "Strong consistency" in reasons_by_signal["adherence"].message


# ===========================================================================
# 7. Baseline / no-objective-data produces a neutral reason
# ===========================================================================
def test_zero_logs_produces_neutral_baseline_reason():
    inp = _make_input(log_count=0)
    decision = compute_adaptation(inp)
    assert len(decision.reasons) == 1
    reason = decision.reasons[0]
    assert reason.signal == "baseline"
    assert reason.effect == "neutral"
    assert reason.value == 0
    assert "Baseline targets active" in reason.message


def test_no_objective_telemetry_produces_neutral_baseline_reason():
    inp = _make_input(
        log_count=5,
        adherence_percent=None,
        recovery_score=None,
        sleep_quality=None,
        stress_score=None,
        injury_risk=None,
        plateau_probability=None,
    )
    decision = compute_adaptation(inp)
    assert decision.objective_data_available is False
    assert len(decision.reasons) == 1
    reason = decision.reasons[0]
    assert reason.signal == "baseline"
    assert reason.effect == "neutral"
    assert "Insufficient objective telemetry" in reason.message


# ===========================================================================
# 8. Reasons are persisted in adaptation history input_snapshot
# ===========================================================================
def test_reasons_persisted_in_adaptation_history():
    inp = _make_input(recovery_score=35, sleep_quality=45)
    decision = compute_adaptation(inp)
    assert len(decision.reasons) >= 2

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_profile.return_value = _sample_profile(user_id=USER_A)
    mock_daily_repo = MagicMock()
    mock_daily_repo.get_user_logs.return_value = []
    mock_journal_repo = MagicMock()
    mock_journal_repo.get_recent_entries.return_value = []
    mock_meal_repo = MagicMock()
    mock_meal_repo.get_active_meal_plan.return_value = None
    mock_workout_repo = MagicMock()
    mock_workout_repo.get_active_workout_plan.return_value = None
    mock_hist_repo = MagicMock()
    mock_hist_repo.get_latest_history.return_value = None

    saved_payload = {}
    def fake_save(user_id, record_data, user_token=None):
        saved_payload.update(record_data)
        saved_payload["id"] = "hist_rec_123"
        saved_payload["user_id"] = user_id
        return saved_payload

    mock_hist_repo.save_history.side_effect = fake_save

    res = persist_adaptation_snapshot(
        user_id=USER_A,
        decision=decision,
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_daily_repo,
        journal_repository=mock_journal_repo,
        meal_plan_repository=mock_meal_repo,
        workout_plan_repository=mock_workout_repo,
        adaptation_history_repository=mock_hist_repo,
    )

    assert res is not None
    assert "input_snapshot" in res
    assert "reasons" in res["input_snapshot"]
    persisted_reasons = res["input_snapshot"]["reasons"]
    assert isinstance(persisted_reasons, list)
    assert len(persisted_reasons) == len(decision.reasons)
    assert persisted_reasons[0]["signal"] == decision.reasons[0].signal
    assert persisted_reasons[0]["effect"] == decision.reasons[0].effect


# ===========================================================================
# 9. GET /api/v1/adaptation/history returns reasons
# ===========================================================================
def test_get_adaptation_history_returns_reasons():
    sample_reasons = [
        {"signal": "recovery_score", "value": 30, "effect": "negative", "message": "Low recovery capacity detected"},
        {"signal": "sleep_quality", "value": 45, "effect": "negative", "message": "Poor sleep quality reported"},
    ]
    mock_record = {
        "id": "rec_with_reasons_1",
        "user_id": USER_A,
        "created_at": "2026-10-02T10:00:00Z",
        "readiness_factor": 0.72,
        "high_fatigue_flag": True,
        "plateau_detected": False,
        "adherence_score": 90,
        "recovery_score": 30,
        "stress_score": 40,
        "sleep_quality": 45,
        "injury_risk": 20,
        "plateau_probability": 10,
        "diet_adjustment": {"calorie_delta": 0, "protein_delta_g": 0.0, "carb_delta_g": 0.0, "fat_delta_g": 0.0},
        "workout_adjustment": {"intensity": "reduce", "volume": "low", "recovery_days": 1, "cardio_minutes": 0, "deload_recommended": False},
        "actionable_recommendations": ["Recovery score is low."],
        "coaching_summary": "Elevated fatigue detected.",
        "objective_data_available": True,
        "active_meal_plan_id": None,
        "active_workout_plan_id": None,
        "input_snapshot": {
            "recovery_score": 30,
            "sleep_quality": 45,
            "reasons": sample_reasons,
        },
    }

    with patch("app.modules.adaptation.AdaptationHistoryRepository.get_history") as mock_get_hist:
        mock_get_hist.return_value = [mock_record]
        resp = client.get("/api/v1/adaptation/history", headers=AUTH_A)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        history_item = data["history"][0]
        assert "reasons" in history_item
        assert len(history_item["reasons"]) == 2
        assert history_item["reasons"][0]["signal"] == "recovery_score"
        assert history_item["reasons"][0]["effect"] == "negative"
        assert history_item["reasons"][0]["message"] == "Low recovery capacity detected"


# ===========================================================================
# 10. Legacy history records without reasons return reasons=[]
# ===========================================================================
def test_legacy_history_records_without_reasons_return_empty_list():
    legacy_row = {
        "id": "rec_legacy_1",
        "user_id": USER_A,
        "created_at": "2026-09-01T10:00:00Z",
        "readiness_factor": 1.0,
        "high_fatigue_flag": False,
        "plateau_detected": False,
        "adherence_score": 100,
        "recovery_score": 100,
        "stress_score": 0,
        "sleep_quality": 100,
        "injury_risk": 0,
        "plateau_probability": 0,
        "diet_adjustment": {},
        "workout_adjustment": {},
        "actionable_recommendations": [],
        "coaching_summary": "Legacy record",
        "objective_data_available": False,
        "input_snapshot": {"some_old_field": 123},  # no reasons field
    }

    record = AdaptationHistoryRecord.from_db_row(legacy_row)
    assert record.reasons == []

    # Also test when input_snapshot is empty or reasons is null or malformed
    legacy_row_null = dict(legacy_row, input_snapshot={"reasons": None})
    assert AdaptationHistoryRecord.from_db_row(legacy_row_null).reasons == []

    legacy_row_malformed = dict(legacy_row, input_snapshot={"reasons": ["invalid_string", 42, None]})
    assert AdaptationHistoryRecord.from_db_row(legacy_row_malformed).reasons == []

    # Verify over HTTP GET /api/v1/adaptation/history
    with patch("app.modules.adaptation.AdaptationHistoryRepository.get_history") as mock_get_hist:
        mock_get_hist.return_value = [legacy_row]
        resp = client.get("/api/v1/adaptation/history", headers=AUTH_A)
        assert resp.status_code == 200
        assert resp.json()["history"][0]["reasons"] == []


# ===========================================================================
# 11. User isolation remains intact
# ===========================================================================
def test_user_isolation_history_access():
    with patch("app.modules.adaptation.AdaptationHistoryRepository.get_history") as mock_get_hist:
        mock_get_hist.return_value = []
        # User A makes request
        client.get("/api/v1/adaptation/history", headers=AUTH_A)
        assert mock_get_hist.call_args[1]["user_id"] == USER_A

        # User B makes request
        client.get("/api/v1/adaptation/history", headers=AUTH_B)
        assert mock_get_hist.call_args[1]["user_id"] == USER_B

    # Unauthenticated request returns 401
    resp_unauth = client.get("/api/v1/adaptation/history")
    assert resp_unauth.status_code in (401, 403)


# ===========================================================================
# 12. Existing adaptation outputs remain unchanged apart from new metadata
# ===========================================================================
def test_existing_adaptation_outputs_remain_unchanged():
    # Healthy case
    inp_healthy = _make_input(
        recovery_score=85,
        sleep_quality=85,
        stress_score=20,
        injury_risk=10,
        adherence_percent=90.0,
    )
    dec_healthy = compute_adaptation(inp_healthy)
    assert dec_healthy.readiness_factor > 0.80
    assert dec_healthy.high_fatigue_flag is False
    assert dec_healthy.plateau_detected is False
    assert dec_healthy.workout_adjustment.deload_recommended is False
    assert dec_healthy.diet_adjustment.calorie_delta == 0
    assert len(dec_healthy.reasons) > 0

    # Poor fatigue case
    inp_fatigue = _make_input(
        recovery_score=25,
        sleep_quality=30,
        stress_score=85,
        injury_risk=60,
    )
    dec_fatigue = compute_adaptation(inp_fatigue)
    assert dec_fatigue.high_fatigue_flag is True
    assert dec_fatigue.readiness_factor < 0.80
    assert dec_fatigue.workout_adjustment.intensity == "reduce"
    assert len(dec_fatigue.reasons) >= 3


# ===========================================================================
# 13. Duplicate history protection still works with reasons
# ===========================================================================
def test_duplicate_history_protection_with_reasons():
    inp = _make_input(recovery_score=35)
    decision = compute_adaptation(inp)

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_profile.return_value = _sample_profile(user_id=USER_A)
    mock_daily_repo = MagicMock()
    mock_daily_repo.get_user_logs.return_value = []
    mock_journal_repo = MagicMock()
    mock_journal_repo.get_recent_entries.return_value = []
    mock_meal_repo = MagicMock()
    mock_meal_repo.get_active_meal_plan.return_value = None
    mock_workout_repo = MagicMock()
    mock_workout_repo.get_active_workout_plan.return_value = None

    # First call: no previous record
    mock_hist_repo = MagicMock()
    mock_hist_repo.get_latest_history.return_value = None

    saved_record = None
    def fake_save(user_id, record_data, user_token=None):
        nonlocal saved_record
        saved_record = dict(record_data)
        saved_record["id"] = "hist_rec_dedup_1"
        saved_record["user_id"] = user_id
        return saved_record

    mock_hist_repo.save_history.side_effect = fake_save

    res1 = persist_adaptation_snapshot(
        user_id=USER_A,
        decision=decision,
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_daily_repo,
        journal_repository=mock_journal_repo,
        meal_plan_repository=mock_meal_repo,
        workout_plan_repository=mock_workout_repo,
        adaptation_history_repository=mock_hist_repo,
    )
    assert mock_hist_repo.save_history.call_count == 1

    # Second call: mock_hist_repo returns the newly saved record
    mock_hist_repo.get_latest_history.return_value = saved_record
    res2 = persist_adaptation_snapshot(
        user_id=USER_A,
        decision=decision,
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_daily_repo,
        journal_repository=mock_journal_repo,
        meal_plan_repository=mock_meal_repo,
        workout_plan_repository=mock_workout_repo,
        adaptation_history_repository=mock_hist_repo,
    )

    # Must NOT call save_history again!
    assert mock_hist_repo.save_history.call_count == 1
    assert res2["id"] == "hist_rec_dedup_1"
