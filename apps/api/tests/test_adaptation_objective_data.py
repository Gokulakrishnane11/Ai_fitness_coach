"""
Tests for objective-data availability in compute_adaptation().

When no objective signal (adherence, recovery, stress, sleep, injury risk, plateau probability)
was provided, the engine must say so instead of claiming healthy readiness. Numeric neutral
defaults are unchanged in this task; objective_data_available tells consumers they are not
measurements.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.engine.adaptation import (
    AdaptationDecision,
    AdaptationInput,
    compute_adaptation,
    compute_adaptation_for_user,
)

NO_DATA_SUMMARY = (
    "Not enough objective data (recovery, stress, sleep, adherence, injury or plateau signals) "
    "has been recorded to assess readiness."
)
BASELINE_SUMMARY = "Baseline targets active. Maintain consistent logging to enable personalized adaptations."
FATIGUE_REC = "Recent journal reflects fatigue. Prioritize recovery and sleep."
MOTIVATION_REC = "High motivation noted in recent journal. Channel energy into structured training."

HEALTHY_SIGNALS = {
    "adherence_percent": 90.0,
    "recovery_score": 80.0,
    "stress_score": 20.0,
    "sleep_quality": 85.0,
    "injury_risk": 10.0,
    "plateau_probability": 10.0,
}


def _input(**overrides):
    base = dict(
        current_weight_kg=82.5,
        target_weight_kg=75.0,
        goal_type="fat_loss",
        target_calories=2100,
        target_protein_g=165,
        target_carbs_g=200,
        target_fat_g=60,
        workout_days_per_week=4,
        experience_level="intermediate",
        log_count=10,
    )
    base.update(overrides)
    return AdaptationInput(**base)


def test_no_objective_inputs_reports_unavailable_with_honest_summary():
    decision = compute_adaptation(_input())
    assert isinstance(decision, AdaptationDecision)
    assert decision.objective_data_available is False
    assert decision.coaching_summary == NO_DATA_SUMMARY
    assert "healthy" not in decision.coaching_summary.lower()


@pytest.mark.parametrize("field,value", sorted(HEALTHY_SIGNALS.items()))
def test_any_single_objective_input_marks_data_available(field, value):
    decision = compute_adaptation(_input(**{field: value}))
    assert decision.objective_data_available is True
    assert decision.coaching_summary != NO_DATA_SUMMARY


def test_low_recovery_still_flags_fatigue_and_reports_available():
    decision = compute_adaptation(_input(recovery_score=35.0))
    assert decision.objective_data_available is True
    assert decision.high_fatigue_flag is True
    assert "Recovery score is low." in decision.actionable_recommendations
    assert decision.coaching_summary == "Elevated fatigue detected. Prioritize recovery and sleep quality."


@pytest.mark.parametrize("sentiment", [None, "fatigued", "motivated", "consistent"])
def test_journal_sentiment_never_changes_availability_or_summary(sentiment):
    decision = compute_adaptation(_input(latest_journal_sentiment=sentiment))
    assert decision.objective_data_available is False
    assert decision.coaching_summary == NO_DATA_SUMMARY


def test_journal_recommendations_still_added_without_objective_data():
    fatigued = compute_adaptation(_input(latest_journal_sentiment="fatigued"))
    motivated = compute_adaptation(_input(latest_journal_sentiment="motivated"))
    assert fatigued.actionable_recommendations == [FATIGUE_REC]
    assert motivated.actionable_recommendations == [MOTIVATION_REC]


def test_under_three_logs_reports_unavailable_and_keeps_baseline():
    decision = compute_adaptation(
        _input(log_count=2, latest_journal_sentiment="fatigued", recovery_score=35.0)
    )
    assert decision.objective_data_available is False
    assert decision.coaching_summary == BASELINE_SUMMARY
    assert decision.actionable_recommendations == []
    assert decision.high_fatigue_flag is False


def test_numeric_neutral_defaults_unchanged_without_data():
    d = compute_adaptation(_input())
    assert (
        d.adherence_score,
        d.recovery_score,
        d.stress_score,
        d.sleep_quality,
        d.plateau_probability,
        d.injury_risk,
    ) == (100, 100, 0, 100, 0, 0)
    assert d.readiness_factor == 1.0
    assert d.high_fatigue_flag is False
    assert d.plateau_detected is False


def test_decision_serializes_availability_field_with_false_default():
    dumped = compute_adaptation(_input()).model_dump()
    assert dumped["objective_data_available"] is False
    assert AdaptationDecision.model_fields["objective_data_available"].default is False


def test_production_shaped_pipeline_reports_no_objective_data():
    profile_repo, log_repo, journal_repo = MagicMock(), MagicMock(), MagicMock()
    profile_repo.get_profile.return_value = {
        "id": "u1",
        "gender": "male",
        "age": 25,
        "height_cm": 178.0,
        "weight_kg": 82.5,
        "target_weight_kg": 75.0,
        "body_fat_pct": None,
        "activity_level": "moderately_active",
        "goal_type": "fat_loss",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
    }
    log_repo.get_logs.return_value = [
        {
            "log_date": f"2026-09-{18 - i:02d}",
            "weight_kg": 82.0,
            "calories_consumed": 1900,
            "workout_completed": True,
            "energy_rating": 7,
        }
        for i in range(4)
    ]
    ref_time = datetime.now(timezone.utc)
    fresh_created_at = (ref_time - timedelta(days=1)).isoformat()
    journal_repo.get_entries.return_value = [
        {
            "id": "j1",
            "created_at": fresh_created_at,
            "sentiment_tag": "fatigued",
            "ai_feedback": {"summary": "s"},
        }
    ]

    decision = compute_adaptation_for_user(
        "u1",
        profile_repository=profile_repo,
        daily_log_repository=log_repo,
        journal_repository=journal_repo,
    )

    assert decision.objective_data_available is False
    assert decision.coaching_summary == NO_DATA_SUMMARY
    assert decision.actionable_recommendations == [FATIGUE_REC]


def test_nutrition_and_training_modulate_readiness_while_objective_data_remains_false():
    """
    Verify Task 11A semantics: empirical nutrition_score and training_quality
    modulate the composite readiness_factor even when the 6 primary physiological
    metrics are unmeasured and objective_data_available remains False.
    """
    # Base input with empirical nutrition and training signals, but NO sensor biometrics
    inp = _input(nutrition_score=80.0, training_quality=70.0)
    decision = compute_adaptation(inp)

    # 1. Primary 6 physiological scores remain neutral placeholders
    assert (
        decision.adherence_score,
        decision.recovery_score,
        decision.stress_score,
        decision.sleep_quality,
        decision.plateau_probability,
        decision.injury_risk,
    ) == (100, 100, 0, 100, 0, 0)

    # 2. objective_data_available remains False to protect dashboard baseline mode
    assert decision.objective_data_available is False
    assert decision.coaching_summary == NO_DATA_SUMMARY

    # 3. readiness_factor reflects the empirical lifestyle signals:
    # (100*0.30) + (100*0.20) + (80*0.20) + (70*0.15) + (100*0.10) + (100*0.05)
    # = 30 + 20 + 16 + 10.5 + 10 + 5 = 91.5 / 100.0 = 0.915
    assert decision.readiness_factor == 0.915
