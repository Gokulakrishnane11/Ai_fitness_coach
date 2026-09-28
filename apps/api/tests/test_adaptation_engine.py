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
    WorkoutAdjustment,
    calculate_workout_adjustment,
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

    # In Task 12-1, recovery_score=30.0 (< 50) triggers high_fatigue_flag -> deload
    assert decision.workout_adjustment.intensity == "reduce"
    assert decision.workout_adjustment.volume == "low"
    assert decision.workout_adjustment.recovery_days == 2
    assert decision.workout_adjustment.cardio_minutes == 0
    assert decision.workout_adjustment.deload_recommended is True


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


# ---------------------------------------------------------------------------
# 10. Empirical Recommendations Tests (Task 11B-3)
# ---------------------------------------------------------------------------

ADH_REC = "Adherence score is low. Prioritize consistent workout completion and logging."
NUT_REC = "Nutrition target alignment is low. Focus on meeting daily calorie and macro targets."
TRN_REC = "Training quality is low. Review workout completion and session energy."


def test_low_adherence_percent_adds_recommendation():
    """1. adherence_percent=40 (< 60) appends adherence recommendation."""
    inp = make_base_input(adherence_percent=40.0)
    decision = compute_adaptation(inp)
    assert ADH_REC in decision.actionable_recommendations


def test_high_adherence_percent_adds_no_recommendation():
    """2. adherence_percent=90 (>= 60) does not append adherence recommendation."""
    inp = make_base_input(adherence_percent=90.0)
    decision = compute_adaptation(inp)
    assert ADH_REC not in decision.actionable_recommendations


def test_none_adherence_percent_adds_no_recommendation():
    """3. adherence_percent=None does not append adherence recommendation."""
    inp = make_base_input(adherence_percent=None)
    decision = compute_adaptation(inp)
    assert ADH_REC not in decision.actionable_recommendations


def test_low_nutrition_score_adds_recommendation():
    """4. nutrition_score=45 (< 60) appends nutrition alignment recommendation."""
    inp = make_base_input(nutrition_score=45.0)
    decision = compute_adaptation(inp)
    assert NUT_REC in decision.actionable_recommendations


def test_high_nutrition_score_adds_no_recommendation():
    """5. nutrition_score=90 (>= 60) does not append nutrition recommendation."""
    inp = make_base_input(nutrition_score=90.0)
    decision = compute_adaptation(inp)
    assert NUT_REC not in decision.actionable_recommendations


def test_none_nutrition_score_adds_no_recommendation():
    """6. nutrition_score=None does not append nutrition recommendation."""
    inp = make_base_input(nutrition_score=None)
    decision = compute_adaptation(inp)
    assert NUT_REC not in decision.actionable_recommendations


def test_low_training_quality_adds_recommendation():
    """7. training_quality=40 (< 60) appends training quality recommendation."""
    inp = make_base_input(training_quality=40.0)
    decision = compute_adaptation(inp)
    assert TRN_REC in decision.actionable_recommendations


def test_high_training_quality_adds_no_recommendation():
    """8. training_quality=85 (>= 60) does not append training recommendation."""
    inp = make_base_input(training_quality=85.0)
    decision = compute_adaptation(inp)
    assert TRN_REC not in decision.actionable_recommendations


def test_none_training_quality_adds_no_recommendation():
    """9. training_quality=None does not append training recommendation."""
    inp = make_base_input(training_quality=None)
    decision = compute_adaptation(inp)
    assert TRN_REC not in decision.actionable_recommendations


def test_multiple_low_empirical_signals_coexist():
    """10. Multiple low empirical signals coexist cleanly without duplicate text."""
    inp = make_base_input(
        adherence_percent=45.0,
        nutrition_score=50.0,
        training_quality=40.0,
    )
    decision = compute_adaptation(inp)
    assert ADH_REC in decision.actionable_recommendations
    assert NUT_REC in decision.actionable_recommendations
    assert TRN_REC in decision.actionable_recommendations
    assert len(decision.actionable_recommendations) == 3


def test_empirical_recommendations_maintain_ordering_with_physiological_and_journal():
    """11 & 12. Ordering: Physiological -> Empirical -> Journal recommendations."""
    inp = make_base_input(
        recovery_score=75.0,
        stress_score=70.0,
        sleep_quality=45.0,
        plateau_probability=85.0,
        injury_risk=60.0,
        adherence_percent=40.0,
        nutrition_score=50.0,
        training_quality=45.0,
        latest_journal_sentiment="motivated",
    )
    decision = compute_adaptation(inp)

    expected_order = [
        "Stress score is elevated.",
        "Sleep quality is low.",
        "Recent progress may indicate a plateau.",
        "Injury risk score is elevated.",
        ADH_REC,
        NUT_REC,
        TRN_REC,
        "High motivation noted in recent journal. Channel energy into structured training.",
    ]
    assert decision.actionable_recommendations == expected_order


# ---------------------------------------------------------------------------
# 11. Dynamic Workout Adjustments Tests (Task 12-1)
# ---------------------------------------------------------------------------

def test_workout_adj_rule1_high_fatigue_flag_triggers_deload():
    """1. high fatigue -> deload (intensity=reduce, volume=low, recovery_days=2, cardio=0, deload=True)."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.90,
        plateau_detected=False,
        high_fatigue_flag=True,
        goal_type="fat_loss",
    )
    assert adj.intensity == "reduce"
    assert adj.volume == "low"
    assert adj.recovery_days == 2
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is True


def test_workout_adj_rule1_rf_under_65_triggers_deload():
    """2. RF < 0.65 -> deload."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.64,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "reduce"
    assert adj.volume == "low"
    assert adj.recovery_days == 2
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is True


def test_workout_adj_rule2_rf_65_boundary_low_readiness():
    """3. RF 0.65 -> low readiness (intensity=reduce, volume=low, recovery_days=1, cardio=0, deload=False)."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.65,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "reduce"
    assert adj.volume == "low"
    assert adj.recovery_days == 1
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule2_rf_79_boundary_low_readiness():
    """4. RF 0.79 -> low readiness."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.79,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "reduce"
    assert adj.volume == "low"
    assert adj.recovery_days == 1
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule5_rf_80_moderate_boundary():
    """5. RF 0.80 -> moderate/plateau boundary (neutral if not plateau)."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.80,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule5_rf_99_moderate():
    """6. RF 0.99 -> moderate."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.99,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule4_rf_ge_100_recovery_none_caps_at_maintain():
    """7a. RF >= 1.00 + recovery=None -> maintain/medium (safe baseline progression)."""
    adj = calculate_workout_adjustment(
        readiness_factor=1.00,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
        recovery_score=None,
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule4_rf_112_recovery_none_caps_at_maintain():
    """7b. RF 1.12 + recovery=None -> maintain/medium."""
    adj = calculate_workout_adjustment(
        readiness_factor=1.12,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
        recovery_score=None,
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule4_rf_ge_100_with_recovery_triggers_increase():
    """8a. RF >= 1.00 + recovery=85 -> increase/high (escalation with measured clearance)."""
    adj = calculate_workout_adjustment(
        readiness_factor=1.00,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
        recovery_score=85.0,
    )
    assert adj.intensity == "increase"
    assert adj.volume == "high"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule4_rf_112_with_recovery_triggers_increase():
    """8b. RF 1.12 + recovery=90 -> increase/high."""
    adj = calculate_workout_adjustment(
        readiness_factor=1.12,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
        recovery_score=90.0,
    )
    assert adj.intensity == "increase"
    assert adj.volume == "high"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_compute_adaptation_rf_ge_100_without_recovery_caps_at_maintain():
    """Integration: High adherence and logging without recovery score caps at maintain/medium."""
    inp = make_base_input(
        log_count=10,
        adherence_percent=100.0,
        recovery_score=None,
        plateau_probability=0.0,
    )
    decision = compute_adaptation(inp)
    assert decision.readiness_factor >= 1.00
    assert decision.workout_adjustment.intensity == "maintain"
    assert decision.workout_adjustment.volume == "medium"
    assert decision.workout_adjustment.deload_recommended is False


def test_compute_adaptation_rf_ge_100_with_recovery_triggers_increase():
    """Integration: High adherence + recovery score = 100.0 triggers increase/high."""
    inp = make_base_input(
        log_count=10,
        adherence_percent=100.0,
        recovery_score=100.0,
        plateau_probability=0.0,
    )
    decision = compute_adaptation(inp)
    assert decision.readiness_factor >= 1.00
    assert decision.workout_adjustment.intensity == "increase"
    assert decision.workout_adjustment.volume == "high"
    assert decision.workout_adjustment.deload_recommended is False


def test_workout_adj_rule3_fat_loss_plateau_adds_cardio():
    """9. fat-loss plateau with good readiness -> +30 cardio."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.85,
        plateau_detected=True,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 30
    assert adj.deload_recommended is False


def test_workout_adj_rule3_muscle_gain_plateau_no_cardio():
    """10. muscle-gain plateau -> no cardio."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.85,
        plateau_detected=True,
        high_fatigue_flag=False,
        goal_type="muscle_gain",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule3_weight_gain_plateau_no_cardio():
    """11. weight-gain plateau -> no cardio."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.85,
        plateau_detected=True,
        high_fatigue_flag=False,
        goal_type="weight_gain",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_rule3_recomposition_plateau_no_cardio():
    """12. recomposition plateau -> no cardio."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.85,
        plateau_detected=True,
        high_fatigue_flag=False,
        goal_type="recomposition",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_high_fatigue_priority_over_plateau():
    """13. high fatigue + plateau -> fatigue/deload takes priority."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.85,
        plateau_detected=True,
        high_fatigue_flag=True,
        goal_type="fat_loss",
    )
    assert adj.intensity == "reduce"
    assert adj.volume == "low"
    assert adj.recovery_days == 2
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is True


def test_workout_adj_low_readiness_priority_over_plateau():
    """14. low readiness + plateau -> low-readiness rule takes priority (no cardio)."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.72,
        plateau_detected=True,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "reduce"
    assert adj.volume == "low"
    assert adj.recovery_days == 1
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_workout_adj_neutral_state():
    """15. neutral state -> maintain/medium."""
    adj = calculate_workout_adjustment(
        readiness_factor=0.90,
        plateau_detected=False,
        high_fatigue_flag=False,
        goal_type="fat_loss",
    )
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_compute_adaptation_zero_data_guard_remains_neutral():
    """16. zero-data guard remains neutral."""
    inp = make_base_input(log_count=2, recovery_score=20.0, plateau_probability=90.0)
    decision = compute_adaptation(inp)
    assert decision.workout_adjustment.intensity == "maintain"
    assert decision.workout_adjustment.volume == "medium"
    assert decision.workout_adjustment.recovery_days == 0
    assert decision.workout_adjustment.cardio_minutes == 0
    assert decision.workout_adjustment.deload_recommended is False


def test_compute_adaptation_baseline_unmeasured_objective_data_remains_neutral():
    """17. baseline/unmeasured objective data remains neutral."""
    inp = make_base_input(
        log_count=5,
        adherence_percent=None,
        recovery_score=None,
        stress_score=None,
        sleep_quality=None,
        plateau_probability=None,
        injury_risk=None,
    )
    decision = compute_adaptation(inp)
    assert decision.objective_data_available is False
    assert decision.workout_adjustment.intensity == "maintain"
    assert decision.workout_adjustment.volume == "medium"
    assert decision.workout_adjustment.recovery_days == 0
    assert decision.workout_adjustment.cardio_minutes == 0
    assert decision.workout_adjustment.deload_recommended is False


def test_compute_adaptation_journal_changes_do_not_affect_workout_adjustment():
    """18. journal changes do not affect workout adjustment."""
    base_inp = make_base_input(
        log_count=5,
        adherence_percent=85.0,
        recovery_score=80.0,
        plateau_probability=20.0,
    )
    decision_base = compute_adaptation(base_inp)

    for sentiment in ["fatigued", "motivated", "consistent", None]:
        inp = make_base_input(
            log_count=5,
            adherence_percent=85.0,
            recovery_score=80.0,
            plateau_probability=20.0,
            latest_journal_sentiment=sentiment,
        )
        decision = compute_adaptation(inp)
        assert decision.workout_adjustment == decision_base.workout_adjustment
