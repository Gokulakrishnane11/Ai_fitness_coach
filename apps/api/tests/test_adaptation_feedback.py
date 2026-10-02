"""
Unit & Integration Tests for Phase 4C: Observational Feedback Loop.

Covers:
1. No previous history -> trajectory="insufficient_data"
2. Previous history older than 28 days -> trajectory="insufficient_data"
3. Recovery improvement (higher = better) -> trajectory="improving"
4. Recovery decline (lower = worse) -> trajectory="declining"
5. Stress reduction (lower = better) -> trajectory="improving"
6. Stress increase (higher = worse) -> trajectory="declining"
7. Soreness reduction (lower = better) -> trajectory="improving"
8. Soreness increase (higher = worse) -> trajectory="declining"
9. Adherence improvement (higher = better) -> trajectory="improving"
10. Adherence decline (lower = worse) -> trajectory="declining"
11. Mixed signals -> trajectory="stable" unless clear majority
12. Missing telemetry -> graceful handling without crashing or false evaluations
13. Multi-user isolation -> history lookup uses authenticated user token/id
14. Legacy history without feedback fields -> deserializes cleanly
15. Current adaptation formulas remain unchanged
16. Existing planning endpoints remain unchanged
17. Feedback outcome does NOT alter:
    - readiness_factor
    - calorie_delta
    - workout intensity
    - workout volume
    - deload recommendation
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.engine.adaptation import (
    AdaptationInput,
    AdaptationDecision,
    AdaptationFeedbackOutcome,
    AdaptationReason,
    evaluate_adaptation_feedback,
    compute_adaptation,
    compute_adaptation_for_user,
    FEEDBACK_MEANINGFUL_DELTA_THRESHOLD,
    FEEDBACK_MAX_HISTORY_AGE_DAYS,
)
from app.modules.adaptation import (
    AdaptationHistoryRecord,
    persist_adaptation_snapshot,
)
import app.db.supabase as db_mod

client = TestClient(app)

USER_A = "user_feedback_a"
USER_B = "user_feedback_b"
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
        "adherence_percent": 80.0,
        "recovery_score": 70.0,
        "sleep_quality": 75.0,
        "stress_score": 40.0,
        "injury_risk": 20.0,
        "plateau_probability": 10.0,
        "nutrition_score": 85.0,
        "training_quality": 80.0,
        "weight_change_kg_7d": -0.3,
        "weight_change_kg_14d": -0.6,
        "weight_change_kg_28d": -1.2,
        "latest_journal_summary": "Feeling solid",
        "latest_journal_sentiment": "consistent",
    }
    base.update(overrides)
    return AdaptationInput(**base)


def _make_history_record(
    history_id: str = "hist_prev_1",
    created_at: Optional[str] = None,
    recovery_score: float = 70.0,
    stress_score: float = 40.0,
    injury_risk: float = 20.0,
    adherence_percent: float = 80.0,
    objective_data_available: bool = True,
    **input_snapshot_overrides,
) -> Dict[str, Any]:
    if created_at is None:
        created_at = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    snap = {
        "recovery_score": recovery_score,
        "stress_score": stress_score,
        "injury_risk": injury_risk,
        "adherence_percent": adherence_percent,
        "sleep_quality": 70.0,
        "log_count": 7,
    }
    snap.update(input_snapshot_overrides)

    return {
        "id": history_id,
        "user_id": USER_A,
        "created_at": created_at,
        "recovery_score": int(recovery_score) if recovery_score is not None else 100,
        "stress_score": int(stress_score) if stress_score is not None else 0,
        "injury_risk": int(injury_risk) if injury_risk is not None else 0,
        "adherence_score": int(adherence_percent) if adherence_percent is not None else 100,
        "sleep_quality": 70,
        "readiness_factor": 1.0,
        "high_fatigue_flag": False,
        "plateau_detected": False,
        "objective_data_available": objective_data_available,
        "input_snapshot": snap,
    }


# ===========================================================================
# 1. No previous history -> trajectory="insufficient_data"
# ===========================================================================
def test_feedback_no_previous_history():
    curr = _make_input()
    outcome = evaluate_adaptation_feedback(current_input=curr, previous_history_record=None)
    assert outcome.trajectory == "insufficient_data"
    assert outcome.recovery_delta is None
    assert outcome.stress_delta is None
    assert outcome.previous_history_id is None
    assert outcome.days_since_previous is None


# ===========================================================================
# 2. Previous history older than 28 days -> trajectory="insufficient_data"
# ===========================================================================
def test_feedback_history_older_than_28_days():
    ref_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    old_time = (ref_time - timedelta(days=29)).isoformat()
    hist = _make_history_record(created_at=old_time, recovery_score=60.0)
    curr = _make_input(recovery_score=85.0)

    outcome = evaluate_adaptation_feedback(
        current_input=curr,
        previous_history_record=hist,
        reference_time=ref_time,
    )
    assert outcome.trajectory == "insufficient_data"
    assert outcome.previous_history_id == "hist_prev_1"
    assert outcome.days_since_previous == 29


# ===========================================================================
# 3. Recovery improvement (higher = better) -> trajectory="improving"
# ===========================================================================
def test_feedback_recovery_improvement():
    # previous: 60, current: 80 -> delta = +20 (>= +5 threshold)
    hist = _make_history_record(recovery_score=60.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=80.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "improving"
    assert outcome.recovery_delta == 20.0
    assert outcome.stress_delta == 0.0


# ===========================================================================
# 4. Recovery decline (lower = worse) -> trajectory="declining"
# ===========================================================================
def test_feedback_recovery_decline():
    # previous: 80, current: 60 -> delta = -20 (<= -5 threshold)
    hist = _make_history_record(recovery_score=80.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=60.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "declining"
    assert outcome.recovery_delta == -20.0


# ===========================================================================
# 5. Stress reduction (lower = better) -> trajectory="improving"
# ===========================================================================
def test_feedback_stress_reduction():
    # previous: 70, current: 40 -> delta = -30 (<= -5 threshold means improvement)
    hist = _make_history_record(recovery_score=70.0, stress_score=70.0, injury_risk=20.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "improving"
    assert outcome.stress_delta == -30.0


# ===========================================================================
# 6. Stress increase (higher = worse) -> trajectory="declining"
# ===========================================================================
def test_feedback_stress_increase():
    # previous: 30, current: 65 -> delta = +35 (>= +5 threshold means worsening)
    hist = _make_history_record(recovery_score=70.0, stress_score=30.0, injury_risk=20.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=70.0, stress_score=65.0, injury_risk=20.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "declining"
    assert outcome.stress_delta == 35.0


# ===========================================================================
# 7. Soreness reduction (lower = better) -> trajectory="improving"
# ===========================================================================
def test_feedback_soreness_reduction():
    # previous: 65, current: 20 -> delta = -45 (<= -5 threshold means improvement)
    hist = _make_history_record(recovery_score=70.0, stress_score=40.0, injury_risk=65.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "improving"
    assert outcome.soreness_delta == -45.0


# ===========================================================================
# 8. Soreness increase (higher = worse) -> trajectory="declining"
# ===========================================================================
def test_feedback_soreness_increase():
    # previous: 20, current: 60 -> delta = +40 (>= +5 threshold means worsening)
    hist = _make_history_record(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=70.0, stress_score=40.0, injury_risk=60.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "declining"
    assert outcome.soreness_delta == 40.0


# ===========================================================================
# 9. Adherence improvement (higher = better) -> trajectory="improving"
# ===========================================================================
def test_feedback_adherence_improvement():
    # previous: 60, current: 90 -> delta = +30 (>= +5 threshold means improvement)
    hist = _make_history_record(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=60.0)
    curr = _make_input(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=90.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "improving"
    assert outcome.adherence_delta == 30.0


# ===========================================================================
# 10. Adherence decline (lower = worse) -> trajectory="declining"
# ===========================================================================
def test_feedback_adherence_decline():
    # previous: 90, current: 55 -> delta = -35 (<= -5 threshold means worsening)
    hist = _make_history_record(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=90.0)
    curr = _make_input(recovery_score=70.0, stress_score=40.0, injury_risk=20.0, adherence_percent=55.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "declining"
    assert outcome.adherence_delta == -35.0


# ===========================================================================
# 11. Mixed signals -> trajectory="stable" unless clear majority
# ===========================================================================
def test_feedback_mixed_signals_balanced():
    # 1 improving (recovery +15), 1 declining (stress +20), 2 unchanged -> balanced -> stable
    hist = _make_history_record(recovery_score=60.0, stress_score=30.0, injury_risk=20.0, adherence_percent=80.0)
    curr = _make_input(recovery_score=75.0, stress_score=50.0, injury_risk=20.0, adherence_percent=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "stable"
    assert outcome.recovery_delta == 15.0
    assert outcome.stress_delta == 20.0


def test_feedback_mixed_signals_with_majority_improving():
    # 3 improving (recovery +15, stress -15, adherence +15), 1 declining (soreness +10) -> majority -> improving
    hist = _make_history_record(recovery_score=60.0, stress_score=50.0, injury_risk=20.0, adherence_percent=70.0)
    curr = _make_input(recovery_score=75.0, stress_score=35.0, injury_risk=30.0, adherence_percent=85.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "improving"


# ===========================================================================
# 12. Missing telemetry -> graceful handling
# ===========================================================================
def test_feedback_missing_telemetry_graceful():
    # Only recovery is present in both, other metrics None in current or previous
    hist = _make_history_record(recovery_score=50.0, stress_score=None, injury_risk=None, adherence_percent=None)
    curr = _make_input(recovery_score=75.0, stress_score=None, injury_risk=None, adherence_percent=None)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "improving"
    assert outcome.recovery_delta == 25.0
    assert outcome.stress_delta is None
    assert outcome.soreness_delta is None
    assert outcome.adherence_delta is None


def test_feedback_unmeasured_previous_snapshot():
    # If previous history had objective_data_available = False, cannot compare -> insufficient_data
    hist = _make_history_record(objective_data_available=False)
    curr = _make_input(recovery_score=80.0)

    outcome = evaluate_adaptation_feedback(curr, hist)
    assert outcome.trajectory == "insufficient_data"


# ===========================================================================
# 13. Multi-user isolation
# ===========================================================================
def test_feedback_multi_user_isolation():
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["adaptation_history"], {}, clear=True):

        # User A has previous history
        hist_a = _make_history_record(history_id="hist_a_1", recovery_score=50.0)
        hist_a["user_id"] = USER_A
        db_mod._OFFLINE_TEST_DB["adaptation_history"]["hist_a_1"] = hist_a

        # User B queries latest history
        latest_b = db_mod.AdaptationHistoryRepository.get_latest_history(user_id=USER_B)
        assert latest_b is None

        # User A queries latest history
        latest_a = db_mod.AdaptationHistoryRepository.get_latest_history(user_id=USER_A)
        assert latest_a is not None
        assert latest_a["id"] == "hist_a_1"


# ===========================================================================
# 14. Legacy history without feedback fields
# ===========================================================================
def test_feedback_legacy_history_deserialization():
    legacy_row = {
        "id": "hist_legacy_001",
        "user_id": USER_A,
        "created_at": "2026-05-01T12:00:00Z",
        "readiness_factor": 1.05,
        "high_fatigue_flag": False,
        "plateau_detected": False,
        "adherence_score": 85,
        "recovery_score": 80,
        "stress_score": 25,
        "sleep_quality": 85,
        "injury_risk": 15,
        "plateau_probability": 10,
        "diet_adjustment": {"calorie_delta": 0, "protein_delta_g": 0.0, "carb_delta_g": 0.0, "fat_delta_g": 0.0},
        "workout_adjustment": {"intensity": "maintain", "volume": "medium", "recovery_days": 0, "cardio_minutes": 0, "deload_recommended": False},
        "actionable_recommendations": [],
        "coaching_summary": "Legacy summary",
        "objective_data_available": True,
        "active_meal_plan_id": None,
        "active_workout_plan_id": None,
        "input_snapshot": {
            "recovery_score": 80,
            "reasons": [{"signal": "recovery_score", "effect": "positive", "message": "Good recovery"}],
            # Note: No feedback_outcome key
        },
    }

    record = AdaptationHistoryRecord.from_db_row(legacy_row)
    assert record.feedback_outcome is None
    assert len(record.reasons) == 1
    assert record.reasons[0].signal == "recovery_score"


# ===========================================================================
# 15. Observational explainability reason is generated
# ===========================================================================
def test_feedback_generates_observational_reason():
    curr = _make_input(recovery_score=85.0, stress_score=25.0)
    outcome = AdaptationFeedbackOutcome(
        trajectory="improving",
        recovery_delta=15.0,
        stress_delta=-15.0,
        soreness_delta=0.0,
        adherence_delta=0.0,
        previous_history_id="prev_hist_test",
        days_since_previous=7,
    )

    decision = compute_adaptation(curr, feedback_outcome=outcome)
    assert decision.feedback_outcome == outcome

    outcome_reasons = [r for r in decision.reasons if r.signal == "adaptation_outcome"]
    assert len(outcome_reasons) == 1
    reason = outcome_reasons[0]
    assert reason.effect == "positive"
    assert reason.value == "improving"
    # Strict check: Observational language used, not causal claim
    assert "Recovery improved after the previous adaptation" in reason.message
    assert "Stress decreased after the previous adaptation" in reason.message
    assert "caused" not in reason.message.lower()


# ===========================================================================
# 16. Existing planning endpoints remain unchanged and callable
# ===========================================================================
def test_existing_planning_endpoints_remain_operational():
    # Meal plan generation endpoint accepts payload and returns 200
    res = client.post(
        "/api/v1/planning/meal-plan",
        json={
            "target_calories": 2000,
            "target_protein_g": 150.0,
            "target_carbs_g": 200.0,
            "target_fat_g": 65.0,
            "dietary_preference": "anything",
        },
        headers=AUTH_A,
    )
    assert res.status_code == 200
    data = res.json()
    assert "meals" in data
    assert data["target_calories"] == 2000

    # Workout plan generation endpoint accepts payload and returns 200
    res = client.post(
        "/api/v1/planning/workout-plan",
        json={
            "goal_type": "fat_loss",
            "workout_days_per_week": 4,
            "experience_level": "intermediate",
        },
        headers=AUTH_A,
    )
    assert res.status_code == 200
    data = res.json()
    assert "title" in data
    assert data["days_per_week"] == 4


# ===========================================================================
# 17. Feedback does NOT alter adaptation formulas or decisions
# ===========================================================================
def test_feedback_does_not_alter_adaptation_formulas_or_decisions():
    """
    CRITICAL INVARIANT:
    readiness_factor, calorie_delta, workout intensity, volume, and deload
    must be 100% IDENTICAL whether feedback is improving, declining, or absent.
    """
    inp = _make_input(
        recovery_score=40.0,  # low recovery triggers deload / fatigue
        stress_score=70.0,
        injury_risk=55.0,
        adherence_percent=60.0,
    )

    outcome_improving = AdaptationFeedbackOutcome(
        trajectory="improving",
        recovery_delta=20.0,
        stress_delta=-20.0,
    )
    outcome_declining = AdaptationFeedbackOutcome(
        trajectory="declining",
        recovery_delta=-20.0,
        stress_delta=20.0,
    )

    decision_baseline = compute_adaptation(inp, feedback_outcome=None)
    decision_with_improving = compute_adaptation(inp, feedback_outcome=outcome_improving)
    decision_with_declining = compute_adaptation(inp, feedback_outcome=outcome_declining)

    # 1. Readiness factor must be bit-for-bit identical
    assert decision_baseline.readiness_factor == decision_with_improving.readiness_factor
    assert decision_baseline.readiness_factor == decision_with_declining.readiness_factor

    # 2. Calorie deltas must be identical
    assert decision_baseline.diet_adjustment.calorie_delta == decision_with_improving.diet_adjustment.calorie_delta
    assert decision_baseline.diet_adjustment.calorie_delta == decision_with_declining.diet_adjustment.calorie_delta

    # 3. Macro deltas must be identical
    assert decision_baseline.diet_adjustment.protein_delta_g == decision_with_improving.diet_adjustment.protein_delta_g
    assert decision_baseline.diet_adjustment.carb_delta_g == decision_with_improving.diet_adjustment.carb_delta_g
    assert decision_baseline.diet_adjustment.fat_delta_g == decision_with_improving.diet_adjustment.fat_delta_g

    # 4. Workout adjustments must be identical
    assert decision_baseline.workout_adjustment.intensity == decision_with_improving.workout_adjustment.intensity
    assert decision_baseline.workout_adjustment.volume == decision_with_improving.workout_adjustment.volume
    assert decision_baseline.workout_adjustment.deload_recommended == decision_with_improving.workout_adjustment.deload_recommended
    assert decision_baseline.workout_adjustment.recovery_days == decision_with_improving.workout_adjustment.recovery_days

    # 5. Core flags must be identical
    assert decision_baseline.high_fatigue_flag == decision_with_improving.high_fatigue_flag
    assert decision_baseline.plateau_detected == decision_with_improving.plateau_detected
