"""
Unit tests for prepare_adaptation_input — the pure function that bridges
raw profile + daily-log data into a validated AdaptationInput instance.
"""

import copy
import pytest
from pydantic import ValidationError
from app.engine.adaptation import prepare_adaptation_input, AdaptationInput


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

    result = prepare_adaptation_input(profile, logs, journals)

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
        result = prepare_adaptation_input(profile, logs, journals)
        assert result.latest_journal_sentiment == expected


def test_invalid_sentiment_becomes_none():
    """Verify that unrecognized sentiments (including 'stressed') normalize to None."""
    profile = _make_profile()
    logs = _make_logs_with_weight_trend()

    for invalid in ["stressed", "unknown", "happy", "", "   "]:
        journals = [_make_journal_entry(sentiment_tag=invalid)]
        result = prepare_adaptation_input(profile, logs, journals)
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

    baseline = prepare_adaptation_input(profile, logs)
    with_journals = prepare_adaptation_input(profile, logs, journals)

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

    prepare_adaptation_input(profile, logs, journals)

    assert profile == profile_copy
    assert logs == logs_copy
    assert journals == journals_copy
    assert journals[0]["created_at"] == journals_copy[0]["created_at"]

