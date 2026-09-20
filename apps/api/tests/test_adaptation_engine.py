"""
Unit Tests for Centralized Adaptation Decision Engine (apps/api/app/engine/adaptation.py).
File: apps/api/tests/test_adaptation_engine.py

Verifies:
1. Fewer than 3 logs -> completely neutral decision
2. Exactly 3 logs -> engine evaluates available signals
3. High recovery -> no fatigue flag
4. Recovery < 50 -> high fatigue flag
5. Plateau probability >= 70 -> plateau_detected
6. Missing optional scores do not crash
7. Readiness factor remains bounded to [0.45, 1.12]
8. Conservative adjustments: no diet changes in v1
9. Conservative adjustments: no workout changes in v1
10. Recommendations accurately reflect available signals
11. Deterministic repeated execution yields identical results
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.adaptation import (
    AdaptationInput,
    AdaptationDecision,
    compute_adaptation,
)


def make_base_input(**overrides) -> AdaptationInput:
    """Helper to create a valid base AdaptationInput payload."""
    data = {
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_calories": 2000.0,
        "target_protein_g": 160.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "log_count": 5,
    }
    data.update(overrides)
    return AdaptationInput(**data)


# ---------------------------------------------------------------------------
# 1. Zero-Data Safety (< 3 logs)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("log_count", [0, 1, 2])
def test_fewer_than_three_logs_completely_neutral(log_count):
    inp = make_base_input(
        log_count=log_count,
        adherence_percent=50.0,
        recovery_score=30.0,
        plateau_probability=90.0,
    )
    decision = compute_adaptation(inp)

    assert isinstance(decision, AdaptationDecision)
    assert decision.readiness_factor == 1.0
    assert decision.plateau_detected is False
    assert decision.high_fatigue_flag is False

    # Diet adjustments remain zero
    assert decision.diet_adjustment.calorie_delta == 0
    assert decision.diet_adjustment.protein_delta_g == 0.0
    assert decision.diet_adjustment.carb_delta_g == 0.0
    assert decision.diet_adjustment.fat_delta_g == 0.0

    # Workout adjustments remain neutral
    assert decision.workout_adjustment.intensity == "maintain"
    assert decision.workout_adjustment.volume == "medium"
    assert decision.workout_adjustment.recovery_days == 0
    assert decision.workout_adjustment.cardio_minutes == 0
    assert decision.workout_adjustment.deload_recommended is False

    # No premature recommendations
    assert decision.actionable_recommendations == []
    assert "Baseline targets active" in decision.coaching_summary


# ---------------------------------------------------------------------------
# 2. Exactly 3 Logs Evaluates Signals
# ---------------------------------------------------------------------------

def test_exactly_three_logs_evaluates_signals():
    inp = make_base_input(
        log_count=3,
        adherence_percent=85.0,
        recovery_score=40.0,
        stress_score=70.0,
    )
    decision = compute_adaptation(inp)

    assert decision.adherence_score == 85
    assert decision.recovery_score == 40
    assert decision.stress_score == 70
    assert decision.high_fatigue_flag is True
    assert "Recovery score is low." in decision.actionable_recommendations
    assert "Stress score is elevated." in decision.actionable_recommendations


# ---------------------------------------------------------------------------
# 3. Recovery & Fatigue Flags
# ---------------------------------------------------------------------------

def test_high_recovery_no_fatigue_flag():
    inp = make_base_input(log_count=5, recovery_score=85.0)
    decision = compute_adaptation(inp)

    assert decision.high_fatigue_flag is False
    assert "Recovery score is low." not in decision.actionable_recommendations


def test_low_recovery_triggers_fatigue_flag():
    inp = make_base_input(log_count=5, recovery_score=45.0)
    decision = compute_adaptation(inp)

    assert decision.high_fatigue_flag is True
    assert "Recovery score is low." in decision.actionable_recommendations


# ---------------------------------------------------------------------------
# 4. Plateau Detection Thresholds
# ---------------------------------------------------------------------------

def test_plateau_probability_triggers_flag_at_seventy():
    inp_70 = make_base_input(log_count=4, plateau_probability=70.0)
    decision_70 = compute_adaptation(inp_70)
    assert decision_70.plateau_detected is True
    assert "Recent progress may indicate a plateau." in decision_70.actionable_recommendations

    inp_85 = make_base_input(log_count=4, plateau_probability=85.0)
    decision_85 = compute_adaptation(inp_85)
    assert decision_85.plateau_detected is True


def test_plateau_probability_below_seventy_no_flag():
    inp_69 = make_base_input(log_count=4, plateau_probability=69.0)
    decision_69 = compute_adaptation(inp_69)
    assert decision_69.plateau_detected is False
    assert "Recent progress may indicate a plateau." not in decision_69.actionable_recommendations

    inp_none = make_base_input(log_count=4, plateau_probability=None)
    decision_none = compute_adaptation(inp_none)
    assert decision_none.plateau_detected is False


# ---------------------------------------------------------------------------
# 5. Missing Optional Scores Robustness
# ---------------------------------------------------------------------------

def test_missing_optional_scores_do_not_crash():
    inp = make_base_input(
        log_count=5,
        adherence_percent=None,
        recovery_score=None,
        stress_score=None,
        sleep_quality=None,
        injury_risk=None,
        plateau_probability=None,
        weight_change_kg_7d=None,
        weight_change_kg_14d=None,
        weight_change_kg_28d=None,
        latest_journal_summary=None,
        latest_journal_sentiment=None,
    )
    decision = compute_adaptation(inp)
    assert isinstance(decision, AdaptationDecision)
    assert decision.adherence_score == 100
    assert decision.recovery_score == 100
    assert decision.high_fatigue_flag is False
    assert decision.plateau_detected is False
    assert 0.45 <= decision.readiness_factor <= 1.12


# ---------------------------------------------------------------------------
# 6. Readiness Factor Boundedness [0.45, 1.12]
# ---------------------------------------------------------------------------

def test_readiness_factor_stays_within_bounds():
    worst_inp = make_base_input(
        log_count=10,
        adherence_percent=0.0,
        recovery_score=0.0,
        stress_score=100.0,
        sleep_quality=0.0,
        plateau_probability=100.0,
        injury_risk=100.0,
    )
    worst_decision = compute_adaptation(worst_inp)
    assert worst_decision.readiness_factor == 0.45

    best_inp = make_base_input(
        log_count=10,
        adherence_percent=100.0,
        recovery_score=100.0,
        stress_score=0.0,
        sleep_quality=100.0,
        plateau_probability=0.0,
        injury_risk=0.0,
    )
    best_decision = compute_adaptation(best_inp)
    assert 0.45 <= best_decision.readiness_factor <= 1.12


# ---------------------------------------------------------------------------
# 7. Conservative First-Version Adjustments
# ---------------------------------------------------------------------------

def test_no_diet_changes_made_in_v1():
    inp = make_base_input(log_count=14, recovery_score=30.0, plateau_probability=80.0)
    decision = compute_adaptation(inp)

    assert decision.diet_adjustment.calorie_delta == 0
    assert decision.diet_adjustment.protein_delta_g == 0.0
    assert decision.diet_adjustment.carb_delta_g == 0.0
    assert decision.diet_adjustment.fat_delta_g == 0.0


def test_no_workout_changes_made_in_v1():
    inp = make_base_input(log_count=14, recovery_score=30.0, injury_risk=80.0)
    decision = compute_adaptation(inp)

    assert decision.workout_adjustment.intensity == "maintain"
    assert decision.workout_adjustment.volume == "medium"
    assert decision.workout_adjustment.recovery_days == 0
    assert decision.workout_adjustment.cardio_minutes == 0
    assert decision.workout_adjustment.deload_recommended is False


# ---------------------------------------------------------------------------
# 8. Factual Actionable Recommendations
# ---------------------------------------------------------------------------

def test_recommendations_reflect_available_signals():
    inp = make_base_input(
        log_count=7,
        recovery_score=40.0,
        stress_score=75.0,
        sleep_quality=45.0,
        plateau_probability=80.0,
        injury_risk=65.0,
    )
    decision = compute_adaptation(inp)

    assert "Recovery score is low." in decision.actionable_recommendations
    assert "Stress score is elevated." in decision.actionable_recommendations
    assert "Sleep quality is low." in decision.actionable_recommendations
    assert "Recent progress may indicate a plateau." in decision.actionable_recommendations
    assert "Injury risk score is elevated." in decision.actionable_recommendations


# ---------------------------------------------------------------------------
# 9. Deterministic Repeated Calls
# ---------------------------------------------------------------------------

def test_deterministic_repetition():
    inp = make_base_input(
        log_count=5,
        adherence_percent=80.0,
        recovery_score=60.0,
        stress_score=40.0,
        sleep_quality=70.0,
        plateau_probability=20.0,
        injury_risk=15.0,
    )
    baseline_dump = compute_adaptation(inp).model_dump()
    for _ in range(20):
        assert compute_adaptation(inp).model_dump() == baseline_dump


# ---------------------------------------------------------------------------
# 10. Journal Invariance Regression Test
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("log_count", [2, 5])
def test_journal_fields_do_not_affect_adaptation_decision(log_count):
    """
    Verifies that journal fields preserve neutrality when log_count < 3,
    and preserve core mathematical/adjustment invariance when log_count >= 3.
    """
    journal_variants = [
        {"latest_journal_summary": None, "latest_journal_sentiment": None},
        {"latest_journal_summary": "Feeling tired after training", "latest_journal_sentiment": "fatigued"},
        {"latest_journal_summary": "Feeling energetic today", "latest_journal_sentiment": "motivated"},
        {"latest_journal_summary": "Completed my planned workout", "latest_journal_sentiment": "consistent"},
    ]

    base_kwargs = {
        "log_count": log_count,
        "adherence_percent": 85.0,
        "recovery_score": 45.0,
        "stress_score": 65.0,
        "sleep_quality": 55.0,
        "plateau_probability": 75.0,
        "injury_risk": 50.0,
        "weight_change_kg_7d": -0.4,
        "weight_change_kg_14d": -0.8,
        "weight_change_kg_28d": -1.5,
    }

    decisions = [
        compute_adaptation(make_base_input(**base_kwargs, **variant))
        for variant in journal_variants
    ]

    baseline_decision = decisions[0]
    if log_count < 3:
        # Zero-data safety guard guarantees 100% identical outputs
        for other_decision in decisions[1:]:
            assert other_decision == baseline_decision
            assert other_decision.model_dump() == baseline_decision.model_dump()
    else:
        # Core mathematical outputs, flags, adjustments, and coaching summary remain invariant
        for other_decision in decisions[1:]:
            assert other_decision.readiness_factor == baseline_decision.readiness_factor
            assert other_decision.adherence_score == baseline_decision.adherence_score
            assert other_decision.recovery_score == baseline_decision.recovery_score
            assert other_decision.stress_score == baseline_decision.stress_score
            assert other_decision.sleep_quality == baseline_decision.sleep_quality
            assert other_decision.plateau_probability == baseline_decision.plateau_probability
            assert other_decision.injury_risk == baseline_decision.injury_risk
            assert other_decision.high_fatigue_flag == baseline_decision.high_fatigue_flag
            assert other_decision.plateau_detected == baseline_decision.plateau_detected
            assert other_decision.diet_adjustment == baseline_decision.diet_adjustment
            assert other_decision.workout_adjustment == baseline_decision.workout_adjustment
            assert other_decision.coaching_summary == baseline_decision.coaching_summary


# ---------------------------------------------------------------------------
# 11. Journal-Driven Actionable Recommendations Tests
# ---------------------------------------------------------------------------

def test_fatigued_with_objective_recovery_ge_50_adds_recommendation():
    """fatigued sentiment with recovery >= 50 appends subjective fatigue recommendation."""
    inp = make_base_input(
        log_count=5,
        recovery_score=75.0,
        latest_journal_sentiment="fatigued",
    )
    decision = compute_adaptation(inp)

    expected = "Recent journal reflects fatigue. Prioritize recovery and sleep."
    assert expected in decision.actionable_recommendations
    assert decision.high_fatigue_flag is False


def test_fatigued_with_objective_recovery_lt_50_does_not_duplicate():
    """fatigued sentiment with recovery < 50 does NOT add the subjective recommendation (no duplication)."""
    inp = make_base_input(
        log_count=5,
        recovery_score=35.0,
        latest_journal_sentiment="fatigued",
    )
    decision = compute_adaptation(inp)

    assert decision.high_fatigue_flag is True
    assert "Recovery score is low." in decision.actionable_recommendations
    assert "Recent journal reflects fatigue. Prioritize recovery and sleep." not in decision.actionable_recommendations


def test_motivated_adds_motivation_recommendation():
    """motivated sentiment appends structured training focus recommendation."""
    inp = make_base_input(
        log_count=5,
        recovery_score=80.0,
        latest_journal_sentiment="motivated",
    )
    decision = compute_adaptation(inp)

    expected = "High motivation noted in recent journal. Channel energy into structured training."
    assert expected in decision.actionable_recommendations


def test_consistent_adds_no_journal_recommendation():
    """consistent sentiment does not add any journal recommendation."""
    inp = make_base_input(
        log_count=5,
        recovery_score=80.0,
        latest_journal_sentiment="consistent",
    )
    decision = compute_adaptation(inp)

    assert decision.actionable_recommendations == []


def test_none_sentiment_adds_no_journal_recommendation():
    """None sentiment does not add any journal recommendation."""
    inp = make_base_input(
        log_count=5,
        recovery_score=80.0,
        latest_journal_sentiment=None,
    )
    decision = compute_adaptation(inp)

    assert decision.actionable_recommendations == []


@pytest.mark.parametrize("sentiment", ["fatigued", "motivated", "consistent", None])
@pytest.mark.parametrize("log_count", [0, 1, 2])
def test_log_count_under_three_preserves_neutral_behavior(sentiment, log_count):
    """When log_count < 3, zero-data neutrality is preserved regardless of sentiment."""
    inp = make_base_input(
        log_count=log_count,
        recovery_score=30.0,
        latest_journal_sentiment=sentiment,
    )
    decision = compute_adaptation(inp)

    assert decision.actionable_recommendations == []
    assert decision.readiness_factor == 1.0
    assert decision.high_fatigue_flag is False
    assert decision.coaching_summary == "Baseline targets active. Maintain consistent logging to enable personalized adaptations."


def test_existing_objective_recommendations_remain_present_and_in_order():
    """Objective recommendations appear before contextual journal recommendations in exact order."""
    inp = make_base_input(
        log_count=5,
        recovery_score=75.0,
        stress_score=70.0,
        sleep_quality=45.0,
        plateau_probability=85.0,
        injury_risk=60.0,
        latest_journal_sentiment="motivated",
    )
    decision = compute_adaptation(inp)

    expected_order = [
        "Stress score is elevated.",
        "Sleep quality is low.",
        "Recent progress may indicate a plateau.",
        "Injury risk score is elevated.",
        "High motivation noted in recent journal. Channel energy into structured training.",
    ]
    assert decision.actionable_recommendations == expected_order


