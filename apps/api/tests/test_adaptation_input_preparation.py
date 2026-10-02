"""
Unit tests for prepare_adaptation_input — the pure function that bridges
raw profile + daily-log data into a validated AdaptationInput instance.
"""

import copy
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.engine.adaptation import (
    prepare_adaptation_input,
    AdaptationInput,
    compute_adaptation,
)

# Reference time anchored to the test dataset so journal entries dated
# in September 2026 are always within the DEFAULT_JOURNAL_FRESHNESS_DAYS
# window, regardless of when the suite is executed.
_JOURNAL_REF_TIME = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_profile(**overrides):
    base = {
        "id": "user_001",
        "first_name": "Alex",
        "weight_kg": 82.5,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "target_metrics": {
            "target_calories": 2100,
            "protein_g": 165.0,
            "carbs_g": 200.0,
            "fat_g": 60.0,
        },
    }
    base.update(overrides)
    return base


def _make_logs_with_weight_trend():
    """28 days of logs with weight entries on key boundary dates."""
    return [
        {"log_date": "2026-09-01", "weight_kg": 83.0, "calories_consumed": 2050, "workout_completed": True, "energy_rating": 7},
        {"log_date": "2026-09-08", "weight_kg": 82.3, "calories_consumed": 2000, "workout_completed": True, "energy_rating": 8},
        {"log_date": "2026-09-15", "weight_kg": 81.5, "calories_consumed": 1980, "workout_completed": False, "energy_rating": 6},
        {"log_date": "2026-09-22", "weight_kg": 81.0, "calories_consumed": 2020, "workout_completed": True, "energy_rating": 7},
        {"log_date": "2026-09-29", "weight_kg": 80.2, "calories_consumed": 1950, "workout_completed": True, "energy_rating": 9},
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_normal_profile_and_logs():
    """Verify prepare_adaptation_input produces a valid AdaptationInput with
    profile fields and aggregated log metrics."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    result = prepare_adaptation_input(profile, logs)

    assert isinstance(result, AdaptationInput)
    assert result.goal_type == "fat_loss"
    assert result.target_weight_kg == 75.0
    assert result.target_calories == 2100
    assert result.target_protein_g == 165.0
    assert result.target_carbs_g == 200.0
    assert result.target_fat_g == 60.0
    assert result.workout_days_per_week == 4
    assert result.experience_level == "intermediate"
    assert result.log_count == 5


def test_latest_logged_weight_overrides_profile():
    """Verify the most recent logged weight is used as current_weight_kg,
    not the profile's static weight_kg."""
    profile = _make_profile(weight_kg=82.5)
    logs = [
        {"log_date": "2026-09-28", "weight_kg": 80.0},
        {"log_date": "2026-09-29", "weight_kg": 79.5},
    ]

    result = prepare_adaptation_input(profile, logs)

    assert result.current_weight_kg == 79.5  # latest log, not 82.5


def test_no_logs_falls_back_to_profile_weight():
    """Verify profile weight_kg is used when there are no daily logs."""
    profile = _make_profile(weight_kg=82.5)

    result = prepare_adaptation_input(profile, [])

    assert result.current_weight_kg == 82.5
    assert result.log_count == 0
    assert result.weight_change_kg_7d is None
    assert result.weight_change_kg_14d is None
    assert result.weight_change_kg_28d is None


def test_weight_trend_fields_passed_through():
    """Verify 7/14/28-day weight-change values flow from aggregation into AdaptationInput."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    result = prepare_adaptation_input(profile, logs)

    # latest is 2026-09-29 = 80.2
    # 7d ago  = 2026-09-22 = 81.0  → 80.2 - 81.0 = -0.8
    # 14d ago = 2026-09-15 = 81.5  → 80.2 - 81.5 = -1.3
    # 28d ago = 2026-09-01 = 83.0  → 80.2 - 83.0 = -2.8
    assert result.weight_change_kg_7d == -0.8
    assert result.weight_change_kg_14d == -1.3
    assert result.weight_change_kg_28d == -2.8


def test_profile_target_metrics_passed_through():
    """Verify target_metrics fields (calories, protein, carbs, fat) are
    extracted from the nested profile dict and passed into AdaptationInput."""
    profile = _make_profile(target_metrics={
        "target_calories": 2800,
        "protein_g": 190.0,
        "carbs_g": 300.0,
        "fat_g": 75.0,
    })

    result = prepare_adaptation_input(profile, [])

    assert result.target_calories == 2800
    assert result.target_protein_g == 190.0
    assert result.target_carbs_g == 300.0
    assert result.target_fat_g == 75.0


def test_missing_required_profile_data_fails_validation():
    """Verify that missing required profile fields cause Pydantic
    ValidationError rather than producing a silently broken result."""
    base = _make_profile()

    # Missing goal_type
    bad_profile = {k: v for k, v in base.items() if k != "goal_type"}
    with pytest.raises(ValidationError):
        prepare_adaptation_input(bad_profile, [])

    # Missing target_metrics entirely
    bad_profile2 = {k: v for k, v in base.items() if k != "target_metrics"}
    with pytest.raises(ValidationError):
        prepare_adaptation_input(bad_profile2, [])

    # Missing weight_kg with no logs (no fallback available)
    bad_profile3 = {k: v for k, v in base.items() if k != "weight_kg"}
    with pytest.raises(ValidationError):
        prepare_adaptation_input(bad_profile3, [])


def test_input_dicts_and_lists_not_mutated():
    """Verify prepare_adaptation_input does not mutate the input profile
    dict or the daily_logs list."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    profile_copy = copy.deepcopy(profile)
    logs_copy = copy.deepcopy(logs)

    prepare_adaptation_input(profile, logs)

    assert profile == profile_copy
    assert logs == logs_copy
    # Verify list order is preserved
    assert logs[0]["log_date"] == logs_copy[0]["log_date"]


def test_delegates_through_build_adaptation_context():
    """Verify prepare_adaptation_input delegates to build_adaptation_context
    rather than calling aggregate_daily_logs directly."""
    from unittest.mock import patch

    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    with patch(
        "app.engine.adaptation.build_adaptation_context", wraps=__import__(
            "app.engine.adaptation", fromlist=["build_adaptation_context"]
        ).build_adaptation_context,
    ) as mock_ctx:
        result = prepare_adaptation_input(profile, logs)

        mock_ctx.assert_called_once()
        call_args = mock_ctx.call_args
        # First positional arg is profile, second is daily_logs, third is []
        assert call_args[0][0] is profile
        assert call_args[0][1] is logs
        assert call_args[0][2] == []

    # Output must still be a valid AdaptationInput
    assert isinstance(result, AdaptationInput)
    assert result.log_count == 5


# ---------------------------------------------------------------------------
# Journal context integration tests
# ---------------------------------------------------------------------------

def _make_journal_entry(
    created_at: str = "2026-09-25T10:00:00+00:00",
    sentiment_tag: str = "motivated",
    summary: str = "Felt strong today during deadlifts.",
):
    return {
        "id": "j_01",
        "created_at": created_at,
        "sentiment_tag": sentiment_tag,
        "ai_feedback": {
            "summary": summary,
            "sentiment_tag": sentiment_tag,
            "actionable_tips": ["Rest well."],
            "encouragement_quote": "Keep it up!",
        },
    }


def test_journal_summary_reaches_adaptation_input():
    """Verify that the latest journal entry summary reaches AdaptationInput."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()
    journals = [
        _make_journal_entry(created_at="2026-09-10", summary="Older summary", sentiment_tag="consistent"),
        _make_journal_entry(created_at="2026-09-28", summary="Newest summary", sentiment_tag="motivated"),
    ]

    result = prepare_adaptation_input(profile, logs, journals, reference_time=_JOURNAL_REF_TIME)

    assert result.latest_journal_summary == "Newest summary"


def test_valid_sentiment_reaches_adaptation_input():
    """Verify that allowed sentiments reach AdaptationInput and are normalized."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    for raw, expected in [
        ("motivated", "motivated"),
        ("fatigued", "fatigued"),
        ("consistent", "consistent"),
        ("  MOTIVATED  ", "motivated"),
        ("Fatigued", "fatigued"),
    ]:
        journals = [_make_journal_entry(sentiment_tag=raw)]
        result = prepare_adaptation_input(profile, logs, journals, reference_time=_JOURNAL_REF_TIME)
        assert result.latest_journal_sentiment == expected


def test_invalid_sentiment_becomes_none():
    """Verify that unrecognized sentiments (including 'stressed') normalize to None."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    for invalid in ["stressed", "unknown", "happy", "", "   "]:
        journals = [_make_journal_entry(sentiment_tag=invalid)]
        result = prepare_adaptation_input(profile, logs, journals, reference_time=_JOURNAL_REF_TIME)
        assert result.latest_journal_sentiment is None


def test_no_journal_entries_preserves_current_behavior():
    """Verify that omitting journal_entries, passing None, or passing [] preserves default None fields."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    res_omitted = prepare_adaptation_input(profile, logs)
    res_none = prepare_adaptation_input(profile, logs, None)
    res_empty = prepare_adaptation_input(profile, logs, [])

    for res in (res_omitted, res_none, res_empty):
        assert res.latest_journal_summary is None
        assert res.latest_journal_sentiment is None
        assert res.log_count == 5


def test_existing_progress_fields_remain_unchanged():
    """Verify progress and profile fields are identical whether journals are provided or omitted."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()
    journals = [_make_journal_entry()]

    baseline = prepare_adaptation_input(profile, logs, reference_time=_JOURNAL_REF_TIME)
    with_journals = prepare_adaptation_input(profile, logs, journals, reference_time=_JOURNAL_REF_TIME)

    assert with_journals.current_weight_kg == baseline.current_weight_kg
    assert with_journals.target_weight_kg == baseline.target_weight_kg
    assert with_journals.goal_type == baseline.goal_type
    assert with_journals.target_calories == baseline.target_calories
    assert with_journals.target_protein_g == baseline.target_protein_g
    assert with_journals.target_carbs_g == baseline.target_carbs_g
    assert with_journals.target_fat_g == baseline.target_fat_g
    assert with_journals.workout_days_per_week == baseline.workout_days_per_week
    assert with_journals.experience_level == baseline.experience_level
    assert with_journals.log_count == baseline.log_count
    assert with_journals.weight_change_kg_7d == baseline.weight_change_kg_7d
    assert with_journals.weight_change_kg_14d == baseline.weight_change_kg_14d
    assert with_journals.weight_change_kg_28d == baseline.weight_change_kg_28d


def test_inputs_remain_unmodified_including_journals():
    """Verify prepare_adaptation_input mutates neither profile, logs, nor journals."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()
    journals = [
        _make_journal_entry(created_at="2026-09-20", sentiment_tag="motivated"),
        _make_journal_entry(created_at="2026-09-10", sentiment_tag="fatigued"),
    ]

    profile_copy = copy.deepcopy(profile)
    logs_copy = copy.deepcopy(logs)
    journals_copy = copy.deepcopy(journals)

    prepare_adaptation_input(profile, logs, journals, reference_time=_JOURNAL_REF_TIME)

    assert profile == profile_copy
    assert logs == logs_copy
    assert journals == journals_copy
    assert journals[0]["created_at"] == journals_copy[0]["created_at"]


def test_adaptation_input_propagation_with_nutrition_and_training():
    """Verify nutrition_score and training_quality are calculated and propagated to AdaptationInput."""
    profile = _make_profile(workout_days_per_week=4)
    logs = [
        {
            "log_date": "2026-09-01",
            "weight_kg": 82.0,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        },
        {
            "log_date": "2026-09-02",
            "weight_kg": 81.8,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        },
        {
            "log_date": "2026-09-03",
            "weight_kg": 81.7,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        },
    ]

    result = prepare_adaptation_input(profile, logs)
    # Exact targets met -> nutrition_score 100.0
    assert result.nutrition_score == 100.0
    # Over 3 days, expected workouts = 4 * (3 / 7) = 1.714
    # 3 completed workouts >= 1.714 -> workout adherence is 100.0% (clamped)
    # Energy rating 8 -> 80.0
    # Training quality = (100.0 * 0.60) + (80.0 * 0.40) = 60.0 + 32.0 = 92.0
    assert result.training_quality == 92.0


def test_adaptation_input_propagation_with_7day_window():
    """Verify training quality calculation with a standard 7-day window."""
    profile = _make_profile(workout_days_per_week=4)
    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "weight_kg": 82.0,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": (i in (1, 3, 5)),  # 3 completed workouts out of 7 days
            "energy_rating": 8,
        }
        for i in range(1, 8)
    ]

    result = prepare_adaptation_input(profile, logs)
    assert result.log_count == 7
    # 3 of 4 expected workouts in 7 days -> 75.0% adherence
    # (75.0 * 0.60) + (80.0 * 0.40) = 45.0 + 32.0 = 77.0
    assert result.training_quality == 77.0


def test_adaptation_input_propagation_with_missing_nutrition_and_training():
    """Verify nutrition_score and training_quality remain None when underlying data is absent."""
    profile = _make_profile()
    # Weight-only logs with no nutrition or training data
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 82.0},
        {"log_date": "2026-09-02", "weight_kg": 81.8},
        {"log_date": "2026-09-03", "weight_kg": 81.6},
    ]

    result = prepare_adaptation_input(profile, logs)
    assert result.nutrition_score is None
    assert result.training_quality is None


def test_adaptation_input_propagation_with_date_gaps():
    """Verify logs with date gaps span the calendar days rather than log_count alone."""
    profile = _make_profile(workout_days_per_week=4)
    # 3 logs spanning 7 calendar days (Sept 1 to Sept 7)
    logs = [
        {
            "log_date": "2026-09-01",
            "weight_kg": 82.0,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        },
        {
            "log_date": "2026-09-04",
            "weight_kg": 81.8,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        },
        {
            "log_date": "2026-09-07",
            "weight_kg": 81.6,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        },
    ]

    result = prepare_adaptation_input(profile, logs)
    # log_count is 3, but calendar span is 7 days
    assert result.log_count == 3
    # Over 7 calendar days, expected workouts = 4 * (7 / 7) = 4.0
    # 3 completed workouts -> 3 / 4.0 = 75.0% adherence
    # Training quality = (75.0 * 0.60) + (80.0 * 0.40) = 45.0 + 32.0 = 77.0
    assert result.training_quality == 77.0


# ---------------------------------------------------------------------------
# Plateau Probability Integration Tests (Task 11B-1)
# ---------------------------------------------------------------------------

def test_prepare_adaptation_input_fat_loss_plateau():
    """Verify fat-loss plateau is detected when 14d and 28d weight trends stall (|14d| < 0.2 and |28d| < 0.4)."""
    profile = _make_profile(goal_type="fat_loss")
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 80.0, "calories_consumed": 2000, "workout_completed": True},
        {"log_date": "2026-09-15", "weight_kg": 80.1, "calories_consumed": 2000, "workout_completed": True},
        {"log_date": "2026-09-29", "weight_kg": 80.2, "calories_consumed": 2000, "workout_completed": True},
    ]

    result = prepare_adaptation_input(profile, logs)
    # 14d change = 80.2 - 80.1 = 0.1
    # 28d change = 80.2 - 80.0 = 0.2
    assert result.plateau_probability == 80.0

    decision = compute_adaptation(result)
    assert decision.plateau_detected is True
    assert decision.plateau_probability == 80
    assert decision.objective_data_available is True
    assert "Recent progress may indicate a plateau." in decision.actionable_recommendations
    assert "Potential plateau detected" in decision.coaching_summary


def test_prepare_adaptation_input_fat_loss_non_plateau():
    """Verify fat-loss non-plateau evaluates to 0.0 when weight is actively changing."""
    profile = _make_profile(goal_type="fat_loss")
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 83.0, "calories_consumed": 1900, "workout_completed": True},
        {"log_date": "2026-09-15", "weight_kg": 81.5, "calories_consumed": 1900, "workout_completed": True},
        {"log_date": "2026-09-29", "weight_kg": 80.0, "calories_consumed": 1900, "workout_completed": True},
    ]

    result = prepare_adaptation_input(profile, logs)
    # 14d change = 80.0 - 81.5 = -1.5
    # 28d change = 80.0 - 83.0 = -3.0
    assert result.plateau_probability == 0.0

    decision = compute_adaptation(result)
    assert decision.plateau_detected is False
    assert decision.plateau_probability == 0
    # Evaluated objective data is present (0.0 is an objective measurement)
    assert decision.objective_data_available is True
    assert "Recent progress may indicate a plateau." not in decision.actionable_recommendations


def test_prepare_adaptation_input_insufficient_weight_history():
    """Verify plateau_probability is None when weight history is insufficient (< 28 days or missing boundary dates)."""
    profile = _make_profile(goal_type="fat_loss")
    # Only 7 days of logs
    logs_7d = [
        {"log_date": "2026-09-01", "weight_kg": 80.0, "calories_consumed": 2000, "workout_completed": True},
        {"log_date": "2026-09-07", "weight_kg": 79.8, "calories_consumed": 2000, "workout_completed": True},
    ]

    result = prepare_adaptation_input(profile, logs_7d)
    assert result.plateau_probability is None

    decision = compute_adaptation(result)
    assert decision.plateau_detected is False
    assert decision.plateau_probability == 0  # neutral placeholder
    # No other primary objective signals provided -> objective_data_available is False
    assert decision.objective_data_available is False


def test_prepare_adaptation_input_muscle_and_weight_gain():
    """Verify muscle_gain and weight_gain goals evaluate plateau thresholds (|14d| < 0.1 and |28d| < 0.2)."""
    # Stalled muscle gain -> plateau
    profile_stalled = _make_profile(goal_type="muscle_gain")
    logs_stalled = [
        {"log_date": "2026-09-01", "weight_kg": 70.0, "calories_consumed": 2500, "workout_completed": True},
        {"log_date": "2026-09-15", "weight_kg": 70.05, "calories_consumed": 2500, "workout_completed": True},
        {"log_date": "2026-09-29", "weight_kg": 70.08, "calories_consumed": 2500, "workout_completed": True},
    ]
    res_stalled = prepare_adaptation_input(profile_stalled, logs_stalled)
    assert res_stalled.plateau_probability == 80.0
    dec_stalled = compute_adaptation(res_stalled)
    assert dec_stalled.plateau_detected is True
    assert dec_stalled.objective_data_available is True

    # Active weight gain -> non-plateau
    profile_gain = _make_profile(goal_type="weight_gain")
    logs_gain = [
        {"log_date": "2026-09-01", "weight_kg": 70.0, "calories_consumed": 2700, "workout_completed": True},
        {"log_date": "2026-09-15", "weight_kg": 70.5, "calories_consumed": 2700, "workout_completed": True},
        {"log_date": "2026-09-29", "weight_kg": 71.0, "calories_consumed": 2700, "workout_completed": True},
    ]
    res_gain = prepare_adaptation_input(profile_gain, logs_gain)
    assert res_gain.plateau_probability == 0.0
    dec_gain = compute_adaptation(res_gain)
    assert dec_gain.plateau_detected is False
    assert dec_gain.objective_data_available is True


def test_prepare_adaptation_input_recomposition():
    """Verify recomposition preserves None for plateau_probability (weight alone cannot determine recomposition plateau)."""
    profile = _make_profile(goal_type="recomposition")
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 75.0, "calories_consumed": 2200, "workout_completed": True},
        {"log_date": "2026-09-15", "weight_kg": 75.0, "calories_consumed": 2200, "workout_completed": True},
        {"log_date": "2026-09-29", "weight_kg": 75.0, "calories_consumed": 2200, "workout_completed": True},
    ]

    result = prepare_adaptation_input(profile, logs)
    assert result.plateau_probability is None

    decision = compute_adaptation(result)
    assert decision.plateau_detected is False
    assert decision.plateau_probability == 0
    assert decision.objective_data_available is False


def test_objective_data_available_flips_true_on_plateau_evaluation():
    """Verify objective_data_available flips to True strictly when plateau is evaluated as a primary objective signal."""
    profile = _make_profile(goal_type="fat_loss")
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 80.0},
        {"log_date": "2026-09-15", "weight_kg": 80.0},
        {"log_date": "2026-09-29", "weight_kg": 80.0},
    ]
    result = prepare_adaptation_input(profile, logs)
    assert result.plateau_probability == 80.0
    decision = compute_adaptation(result)
    assert decision.objective_data_available is True


def test_existing_objective_data_regression_behavior_intact():
    """Verify that when weight history is insufficient for plateau (< 14d/28d),
    objective_data_available remains False even if empirical nutrition and training scores are present."""
    profile = _make_profile(goal_type="fat_loss")
    # 4 days of logs: nutrition and training exist, but plateau cannot be computed
    logs = [
        {
            "log_date": f"2026-09-{18 - i:02d}",
            "weight_kg": 82.0,
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
            "workout_completed": True,
            "energy_rating": 8,
        }
        for i in range(4)
    ]
    result = prepare_adaptation_input(profile, logs)
    assert result.nutrition_score is not None
    assert result.training_quality is not None
    assert result.plateau_probability is None

    decision = compute_adaptation(result)
    # objective_data_available strictly tracks primary physiological signals; remains False here
    assert decision.objective_data_available is False
    assert decision.plateau_probability == 0
    assert decision.plateau_detected is False


# ---------------------------------------------------------------------------
# Adherence Integration Tests (Task 11B-2)
# ---------------------------------------------------------------------------

def test_prepare_adaptation_input_no_adherence_data_under_seven_logs():
    """Verify adherence_percent is None when log_count < 7, preserving neutral decision defaults."""
    profile = _make_profile(workout_days_per_week=4)
    logs_4d = [
        {
            "log_date": f"2026-09-{i:02d}",
            "calories_consumed": 2100,
            "workout_completed": True,
        }
        for i in range(1, 5)
    ]
    result = prepare_adaptation_input(profile, logs_4d)
    assert result.adherence_percent is None

    decision = compute_adaptation(result)
    assert decision.adherence_score == 100
    assert decision.objective_data_available is False


def test_prepare_adaptation_input_no_adherence_data_seven_logs_weight_only():
    """Verify adherence_percent is None when 7 logs contain no workout or nutrition data."""
    profile = _make_profile()
    logs_weight_only = [
        {"log_date": f"2026-09-{i:02d}", "weight_kg": 80.0}
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs_weight_only)
    assert result.adherence_percent is None

    decision = compute_adaptation(result)
    assert decision.adherence_score == 100
    assert decision.objective_data_available is False


def test_prepare_adaptation_input_workout_only_adherence():
    """Verify workout-only logging evaluates workout adherence without penalizing missing nutrition."""
    profile = _make_profile(workout_days_per_week=4)
    # 7 days, 3 completed workouts, no calorie data in any log
    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": i in (1, 3, 5),  # 3 completed
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs)
    # 3 / 4.0 = 75.0%
    assert result.adherence_percent == 75.0

    decision = compute_adaptation(result)
    assert decision.adherence_score == 75
    assert decision.objective_data_available is True


def test_prepare_adaptation_input_nutrition_only_adherence():
    """Verify nutrition-only logging evaluates nutrition adherence without penalizing missing workouts."""
    profile = _make_profile(workout_days_per_week=4)
    # 7 days, 6 days with calories logged, workout_completed never logged
    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "calories_consumed": 2100 if i <= 6 else None,
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs)
    # 6 / 7 = 85.714% -> 85.71%
    assert result.adherence_percent == 85.71

    decision = compute_adaptation(result)
    assert decision.adherence_score == 86
    assert decision.objective_data_available is True


def test_prepare_adaptation_input_both_workout_and_nutrition_adherence():
    """Verify both categories are averaged via arithmetic mean."""
    profile = _make_profile(workout_days_per_week=4)
    # 7 days, 3 workouts (75.0%), 5 calorie days (5/7 = 71.42857%)
    # mean = (75.0 + 71.42857) / 2 = 73.214% -> 73.21%
    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": i in (1, 3, 5),
            "calories_consumed": 2100 if i <= 5 else None,
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs)
    assert result.adherence_percent == 73.21

    decision = compute_adaptation(result)
    assert decision.adherence_score == 73
    assert decision.objective_data_available is True


def test_prepare_adaptation_input_partial_missing_values():
    """Verify partial or missing data handling across daily logs."""
    profile = _make_profile(workout_days_per_week=4)

    # Some days have None for workout_completed (e.g. only 4 days have workout status, 2 completed)
    logs_partial_workouts = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": True if i in (1, 2) else (False if i in (3, 4) else None),
            "calories_consumed": 2100 if i <= 5 else None,
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs_partial_workouts)
    # completed workouts = 2 / 4 = 50.0%
    # calories logged = 5 / 7 = 71.43%
    # mean = (50.0 + 71.42857) / 2 = 60.71%
    assert result.adherence_percent == 60.71

    # Nutrition only partially logged (3 of 7 days), workouts entirely omitted
    logs_partial_nut = [
        {
            "log_date": f"2026-09-{i:02d}",
            "calories_consumed": 2100 if i <= 3 else None,
        }
        for i in range(1, 8)
    ]
    res_nut = prepare_adaptation_input(profile, logs_partial_nut)
    # 3 / 7 = 42.857% -> 42.86%
    assert res_nut.adherence_percent == 42.86


def test_prepare_adaptation_input_zero_completed_workouts():
    """Verify 0 completed workouts yields 0.0% workout adherence."""
    profile = _make_profile(workout_days_per_week=4)
    logs_zero_workouts = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": False,
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs_zero_workouts)
    assert result.adherence_percent == 0.0

    decision = compute_adaptation(result)
    assert decision.adherence_score == 0
    assert decision.objective_data_available is True


def test_prepare_adaptation_input_poor_adherence():
    """Verify poor adherence in workouts and nutrition produces proportionally low score."""
    profile = _make_profile(workout_days_per_week=4)
    # 1/4 workouts completed = 25.0%, 2/7 calorie days logged = 28.5714%
    # Mean = (25.0 + 28.5714) / 2 = 26.7857% -> 26.79%
    logs_poor = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": (i == 1),
            "calories_consumed": 2100 if i <= 2 else None,
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs_poor)
    assert result.adherence_percent == 26.79

    decision = compute_adaptation(result)
    assert decision.adherence_score == 27
    assert decision.objective_data_available is True


def test_prepare_adaptation_input_full_adherence():
    """Verify full adherence in workouts and nutrition produces 100.0%."""
    profile = _make_profile(workout_days_per_week=4)
    logs_full = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": (i <= 4),  # exactly 4 completed
            "calories_consumed": 2100,      # 7/7
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs_full)
    assert result.adherence_percent == 100.0

    decision = compute_adaptation(result)
    assert decision.adherence_score == 100
    assert decision.objective_data_available is True


def test_prepare_adaptation_input_boundary_and_clamping_behavior():
    """Verify completed workouts exceeding planned are clamped strictly to 100.0%."""
    profile = _make_profile(workout_days_per_week=4)
    logs_over = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": True,  # 7 workouts completed > 4 planned
            "calories_consumed": 2100,  # 7/7
        }
        for i in range(1, 8)
    ]
    result = prepare_adaptation_input(profile, logs_over)
    # Workout 7/4 = 175% clamped to 100.0%, Nutrition 7/7 = 100.0% -> 100.0%
    assert result.adherence_percent == 100.0

    decision = compute_adaptation(result)
    assert decision.adherence_score == 100


def test_prepare_adaptation_input_propagation_into_decision_and_readiness():
    """Verify adherence score modulates the mathematical readiness_factor calculation."""
    profile = _make_profile(workout_days_per_week=4)

    # 1. Full adherence (100%)
    logs_full = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": (i <= 4),
            "calories_consumed": 2100,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 200.0,
            "fat_consumed_g": 60.0,
        }
        for i in range(1, 8)
    ]
    inp_full = prepare_adaptation_input(profile, logs_full)
    dec_full = compute_adaptation(inp_full)

    # 2. Poor adherence (1 workout = 25.0%, 1 calorie log = 1/7 = 14.29% -> mean = 19.64%)
    logs_poor = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": (i == 1),
            "calories_consumed": 2100 if i == 1 else None,
            "protein_consumed_g": 165.0 if i == 1 else None,
            "carbs_consumed_g": 200.0 if i == 1 else None,
            "fat_consumed_g": 60.0 if i == 1 else None,
        }
        for i in range(1, 8)
    ]
    inp_poor = prepare_adaptation_input(profile, logs_poor)
    dec_poor = compute_adaptation(inp_poor)

    assert inp_full.adherence_percent == 100.0
    assert dec_full.adherence_score == 100

    assert inp_poor.adherence_percent < inp_full.adherence_percent
    assert dec_poor.adherence_score < dec_full.adherence_score
    # Adherence score accounts for 30% of positive readiness: lower adherence directly lowers readiness_factor
    assert dec_poor.readiness_factor < dec_full.readiness_factor


# ---------------------------------------------------------------------------
# Phase 3B: Active Plan -> Adherence Integration Tests
# ---------------------------------------------------------------------------

def test_prepare_adaptation_input_active_meal_plan_overrides_calories():
    """Verify active meal plan target_calories overrides static profile target_calories."""
    profile = _make_profile()
    active_meal_plan = {"target_calories": 2500}
    result = prepare_adaptation_input(profile, [], active_meal_plan=active_meal_plan)
    assert result.target_calories == 2500


def test_prepare_adaptation_input_active_meal_plan_overrides_all_macros():
    """Verify active meal plan targets override protein, carbs, and fat."""
    profile = _make_profile()
    active_meal_plan = {
        "target_calories": 2400,
        "target_protein_g": 180.0,
        "target_carbs_g": 260.0,
        "target_fat_g": 70.0,
    }
    result = prepare_adaptation_input(profile, [], active_meal_plan=active_meal_plan)
    assert result.target_calories == 2400
    assert result.target_protein_g == 180.0
    assert result.target_carbs_g == 260.0
    assert result.target_fat_g == 70.0


def test_prepare_adaptation_input_active_workout_plan_overrides_frequency():
    """Verify active workout plan days_per_week overrides profile workout_days_per_week."""
    profile = _make_profile(workout_days_per_week=4)
    active_workout_plan = {"days_per_week": 3}
    result = prepare_adaptation_input(profile, [], active_workout_plan=active_workout_plan)
    assert result.workout_days_per_week == 3


def test_prepare_adaptation_input_missing_active_plans_fall_back_to_profile():
    """Verify omitting active plans or passing None falls back to profile values."""
    profile = _make_profile(workout_days_per_week=4)
    res_none = prepare_adaptation_input(profile, [], active_meal_plan=None, active_workout_plan=None)
    assert res_none.target_calories == 2100
    assert res_none.target_protein_g == 165.0
    assert res_none.target_carbs_g == 200.0
    assert res_none.target_fat_g == 60.0
    assert res_none.workout_days_per_week == 4


def test_prepare_adaptation_input_invalid_active_meal_plan_falls_back_safely():
    """Verify None, 0, negative values, and non-dict active meal plans fall back safely."""
    profile = _make_profile()
    # Case 1: non-dict
    res_str = prepare_adaptation_input(profile, [], active_meal_plan="invalid")  # type: ignore
    assert res_str.target_calories == 2100

    # Case 2: zero values
    res_zero = prepare_adaptation_input(
        profile,
        [],
        active_meal_plan={"target_calories": 0, "target_protein_g": 0, "target_carbs_g": 0, "target_fat_g": 0},
    )
    assert res_zero.target_calories == 2100
    assert res_zero.target_protein_g == 165.0
    assert res_zero.target_carbs_g == 200.0
    assert res_zero.target_fat_g == 60.0

    # Case 3: negative values
    res_neg = prepare_adaptation_input(
        profile,
        [],
        active_meal_plan={"target_calories": -2000, "target_protein_g": -50.0},
    )
    assert res_neg.target_calories == 2100
    assert res_neg.target_protein_g == 165.0

    # Case 4: None values in dict
    res_nones = prepare_adaptation_input(
        profile,
        [],
        active_meal_plan={"target_calories": None, "target_protein_g": None},
    )
    assert res_nones.target_calories == 2100
    assert res_nones.target_protein_g == 165.0


def test_prepare_adaptation_input_invalid_active_workout_plan_falls_back_safely():
    """Verify None, 0, negative values, and non-dict active workout plans fall back safely."""
    profile = _make_profile(workout_days_per_week=4)

    # Non-dict
    res_str = prepare_adaptation_input(profile, [], active_workout_plan="malformed")  # type: ignore
    assert res_str.workout_days_per_week == 4

    # Zero
    res_zero = prepare_adaptation_input(profile, [], active_workout_plan={"days_per_week": 0})
    assert res_zero.workout_days_per_week == 4

    # Negative
    res_neg = prepare_adaptation_input(profile, [], active_workout_plan={"days_per_week": -3})
    assert res_neg.workout_days_per_week == 4

    # None
    res_none = prepare_adaptation_input(profile, [], active_workout_plan={"days_per_week": None})
    assert res_none.workout_days_per_week == 4


def test_prepare_adaptation_input_adapted_nutrition_alignment_example():
    """
    Example from requirements:
    Original target = 3155 kcal, Adapted active plan = 3305 kcal, User logs = 3305 kcal.
    The nutrition score should evaluate against 3305 (producing 100.0), not 3155.
    """
    profile = _make_profile(
        target_metrics={
            "target_calories": 3155,
            "protein_g": 165.0,
            "carbs_g": 415.0,
            "fat_g": 93.0,
        }
    )
    active_meal_plan = {
        "target_calories": 3305,
        "target_protein_g": 165.0,
        "target_carbs_g": 452.0,
        "target_fat_g": 94.0,
    }

    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "calories_consumed": 3305,
            "protein_consumed_g": 165.0,
            "carbs_consumed_g": 452.0,
            "fat_consumed_g": 94.0,
        }
        for i in range(1, 8)
    ]

    # With active meal plan: evaluates against 3305 -> 100.0% nutrition score
    result_adapted = prepare_adaptation_input(profile, logs, active_meal_plan=active_meal_plan)
    assert result_adapted.nutrition_score == 100.0

    # Without active meal plan: evaluates against 3155 -> sub-100% nutrition score
    result_baseline = prepare_adaptation_input(profile, logs)
    assert result_baseline.nutrition_score < 100.0


def test_prepare_adaptation_input_adapted_workout_recovery_alignment_example():
    """
    Example from requirements:
    Original workout target = 4 days, Active recovery plan = 3 days, User completes 3 workouts.
    Workout adherence should evaluate against 3 (producing 100%), not 4 (87.5%).
    """
    profile = _make_profile(workout_days_per_week=4)
    active_workout_plan = {"days_per_week": 3}

    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": (i in (1, 3, 5)),  # exactly 3 workouts in 7 days
            "calories_consumed": 2100,
        }
        for i in range(1, 8)
    ]

    # With active 3-day recovery plan: 3 completed / 3 expected = 100.0%
    result_adapted = prepare_adaptation_input(profile, logs, active_workout_plan=active_workout_plan)
    assert result_adapted.adherence_percent == 100.0

    # Without active plan (profile 4 days): 3 completed / 4 expected = 75.0% workout adh,
    # combined with 7/7 calories (100%) -> (75.0 + 100.0) / 2 = 87.5%
    result_baseline = prepare_adaptation_input(profile, logs)
    assert result_baseline.adherence_percent == 87.5


def test_prepare_adaptation_input_apply_adaptation_false_baseline_behavior():
    """
    When a baseline plan is generated with apply_adaptation=False, its target_calories
    and days_per_week match the profile. Passing this plan behaves naturally like the profile.
    """
    profile = _make_profile(workout_days_per_week=4)
    baseline_plan = {
        "target_calories": 2100,
        "target_protein_g": 165.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
    }
    baseline_workout = {"days_per_week": 4}

    logs = [
        {
            "log_date": f"2026-09-{i:02d}",
            "workout_completed": (i in (1, 3, 5)),
            "calories_consumed": 2100,
        }
        for i in range(1, 8)
    ]

    res_adapted_baseline = prepare_adaptation_input(
        profile, logs, active_meal_plan=baseline_plan, active_workout_plan=baseline_workout
    )
    res_no_plan = prepare_adaptation_input(profile, logs)

    assert res_adapted_baseline.target_calories == res_no_plan.target_calories
    assert res_adapted_baseline.target_protein_g == res_no_plan.target_protein_g
    assert res_adapted_baseline.workout_days_per_week == res_no_plan.workout_days_per_week
    assert res_adapted_baseline.nutrition_score == res_no_plan.nutrition_score
    assert res_adapted_baseline.adherence_percent == res_no_plan.adherence_percent


def test_prepare_adaptation_input_does_not_mutate_active_plans():
    """Verify prepare_adaptation_input does not mutate active plan input dicts."""
    profile = _make_profile()
    meal_plan = {"target_calories": 2500, "target_protein_g": 180.0}
    workout_plan = {"days_per_week": 3}
    meal_snapshot = copy.deepcopy(meal_plan)
    workout_snapshot = copy.deepcopy(workout_plan)

    prepare_adaptation_input(
        profile,
        [],
        active_meal_plan=meal_plan,
        active_workout_plan=workout_plan,
    )

    assert meal_plan == meal_snapshot
    assert workout_plan == workout_snapshot
