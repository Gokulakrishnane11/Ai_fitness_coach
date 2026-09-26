"""
Unit tests for build_adaptation_context — the pure combiner that merges
daily-log and journal aggregation into a single adaptation context dict.
"""

import copy

from app.engine.adaptation import (
    aggregate_daily_logs,
    aggregate_journal_entries,
    build_adaptation_context,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_profile(**overrides):
    base = {
        "id": "user_001",
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


def _make_daily_logs():
    return [
        {"log_date": "2026-09-01", "weight_kg": 83.0, "calories_consumed": 2050, "workout_completed": True, "energy_rating": 7},
        {"log_date": "2026-09-15", "weight_kg": 81.5, "calories_consumed": 1980, "workout_completed": False, "energy_rating": 6},
        {"log_date": "2026-09-29", "weight_kg": 80.2, "calories_consumed": 1950, "workout_completed": True, "energy_rating": 9},
    ]


def _make_journal_entries():
    return [
        {
            "id": "j1",
            "user_id": "user_001",
            "entry_text": "Felt great today",
            "sentiment_tag": "motivated",
            "ai_feedback": {"summary": "Strong session.", "sentiment_tag": "motivated", "actionable_tips": [], "encouragement_quote": "Go!"},
            "created_at": "2026-09-10",
        },
        {
            "id": "j2",
            "user_id": "user_001",
            "entry_text": "Tired and sore",
            "sentiment_tag": "fatigued",
            "ai_feedback": {"summary": "Rest needed.", "sentiment_tag": "fatigued", "actionable_tips": [], "encouragement_quote": "Recover!"},
            "created_at": "2026-09-25",
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNormalInput:
    def test_returns_progress_and_journal_keys(self):
        result = build_adaptation_context(
            _make_profile(), _make_daily_logs(), _make_journal_entries()
        )
        assert set(result.keys()) == {"progress", "journal"}

    def test_progress_matches_aggregate_daily_logs(self):
        logs = _make_daily_logs()
        result = build_adaptation_context(_make_profile(), logs, _make_journal_entries())
        expected = aggregate_daily_logs(logs)
        assert result["progress"] == expected

    def test_journal_matches_aggregate_journal_entries(self):
        journals = _make_journal_entries()
        result = build_adaptation_context(_make_profile(), _make_daily_logs(), journals)
        expected = aggregate_journal_entries(journals)
        assert result["journal"] == expected


class TestEmptyLogsAndJournals:
    def test_empty_logs_and_journals(self):
        result = build_adaptation_context(_make_profile(), [], [])

        assert result["progress"]["log_count"] == 0
        assert result["progress"]["latest_weight_kg"] is None
        assert result["journal"]["journal_count"] == 0
        assert result["journal"]["latest_journal_summary"] is None
        assert result["journal"]["latest_journal_sentiment"] is None

    def test_empty_logs_only(self):
        result = build_adaptation_context(_make_profile(), [], _make_journal_entries())
        assert result["progress"]["log_count"] == 0
        assert result["journal"]["journal_count"] == 2

    def test_empty_journals_only(self):
        result = build_adaptation_context(_make_profile(), _make_daily_logs(), [])
        assert result["progress"]["log_count"] == 3
        assert result["journal"]["journal_count"] == 0


class TestAggregationResultsPreserved:
    def test_progress_keys_exact(self):
        result = build_adaptation_context(
            _make_profile(), _make_daily_logs(), _make_journal_entries()
        )
        expected_keys = {
            "log_count", "latest_weight_kg",
            "weight_change_kg_7d", "weight_change_kg_14d", "weight_change_kg_28d",
            "completed_workouts", "days_with_calorie_data",
            "days_with_target_calories", "average_energy_rating",
            "average_calories_consumed", "average_protein_consumed_g",
            "average_carbs_consumed_g", "average_fat_consumed_g",
        }
        assert set(result["progress"].keys()) == expected_keys

    def test_journal_keys_exact(self):
        result = build_adaptation_context(
            _make_profile(), _make_daily_logs(), _make_journal_entries()
        )
        expected_keys = {
            "journal_count", "latest_journal_summary", "latest_journal_sentiment",
        }
        assert set(result["journal"].keys()) == expected_keys

    def test_no_extra_top_level_keys(self):
        result = build_adaptation_context(
            _make_profile(), _make_daily_logs(), _make_journal_entries()
        )
        assert set(result.keys()) == {"progress", "journal"}


class TestProfileNotMutated:
    def test_profile_unchanged(self):
        profile = _make_profile()
        profile_copy = copy.deepcopy(profile)

        build_adaptation_context(profile, _make_daily_logs(), _make_journal_entries())

        assert profile == profile_copy


class TestLogsAndJournalsNotMutated:
    def test_daily_logs_unchanged(self):
        logs = _make_daily_logs()
        logs_copy = copy.deepcopy(logs)

        build_adaptation_context(_make_profile(), logs, _make_journal_entries())

        assert logs == logs_copy

    def test_journal_entries_unchanged(self):
        journals = _make_journal_entries()
        journals_copy = copy.deepcopy(journals)

        build_adaptation_context(_make_profile(), _make_daily_logs(), journals)

        assert journals == journals_copy


class TestDeterministicRepeatedCalls:
    def test_identical_results(self):
        profile = _make_profile()
        logs = _make_daily_logs()
        journals = _make_journal_entries()

        r1 = build_adaptation_context(profile, logs, journals)
        r2 = build_adaptation_context(profile, logs, journals)
        r3 = build_adaptation_context(profile, logs, journals)

        assert r1 == r2 == r3
