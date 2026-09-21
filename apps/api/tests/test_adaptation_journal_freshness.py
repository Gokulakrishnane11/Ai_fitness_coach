"""
Unit and regression tests for journal freshness windowing in adaptation and coaching.

Verifies:
- is_journal_fresh() helper accurately identifies fresh vs stale timestamps across boundaries
- Exact boundary (ref - max_age_days) is classified as fresh
- 1 microsecond past boundary is classified as stale
- Timezone offsets (+05:30, -04:00, Z) and naive datetimes are handled safely
- aggregate_journal_entries() with max_age_days hides stale summary & sentiment while preserving journal_count
- Newer fresh entry is preferred over older stale entry
- All-stale entries return None for summary/sentiment but keep total count
- prepare_adaptation_input() applies DEFAULT_JOURNAL_FRESHNESS_DAYS (7 days) by default
- compute_adaptation() produces no stale journal recommendations when entries exceed the freshness window
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict

import pytest

from app.engine.adaptation import (
    DEFAULT_JOURNAL_FRESHNESS_DAYS,
    AdaptationInput,
    aggregate_journal_entries,
    build_adaptation_context,
    compute_adaptation,
    is_journal_fresh,
    prepare_adaptation_input,
)

# Reference timestamp for deterministic testing
REF_TIME = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


def _entry(entry_id: str, created_at: Any, sentiment: str, summary: str) -> Dict[str, Any]:
    return {
        "id": entry_id,
        "user_id": "user_freshness",
        "entry_text": f"Journal entry text for {entry_id}",
        "sentiment_tag": sentiment,
        "ai_feedback": {
            "summary": summary,
            "sentiment_tag": sentiment,
            "actionable_tips": ["Rest well."],
            "encouragement_quote": "Keep it up!",
        },
        "created_at": created_at,
    }


def _profile(**overrides) -> Dict[str, Any]:
    base = {
        "id": "user_freshness",
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


def _logs(count: int = 4) -> list[Dict[str, Any]]:
    return [
        {
            "log_date": f"2026-09-{20 - i:02d}",
            "weight_kg": 82.0,
            "calories_consumed": 2000,
            "workout_completed": True,
            "energy_rating": 7,
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# 1. is_journal_fresh helper unit tests
# ---------------------------------------------------------------------------

class TestIsJournalFreshHelper:
    """Verifies boundary math, timezone handling, and invalid values for is_journal_fresh."""

    def test_unparseable_or_none_returns_false(self):
        assert is_journal_fresh(None, reference_time=REF_TIME) is False
        assert is_journal_fresh("", reference_time=REF_TIME) is False
        assert is_journal_fresh("   ", reference_time=REF_TIME) is False
        assert is_journal_fresh("garbage-date", reference_time=REF_TIME) is False
        assert is_journal_fresh(12345, reference_time=REF_TIME) is False  # type: ignore[arg-type]

    def test_fresh_entry_within_window(self):
        one_hour_ago = REF_TIME - timedelta(hours=1)
        three_days_ago = REF_TIME - timedelta(days=3)
        six_days_ago = REF_TIME - timedelta(days=6)
        assert is_journal_fresh(one_hour_ago, reference_time=REF_TIME) is True
        assert is_journal_fresh(three_days_ago, reference_time=REF_TIME) is True
        assert is_journal_fresh(six_days_ago, reference_time=REF_TIME) is True

    def test_exact_boundary_is_fresh(self):
        # Exactly 7 days 0 seconds ago matches cutoff (dt >= cutoff)
        exact_7d = REF_TIME - timedelta(days=7)
        assert is_journal_fresh(exact_7d, max_age_days=7, reference_time=REF_TIME) is True

    def test_just_past_boundary_is_stale(self):
        # 1 microsecond older than 7 days is stale
        stale_by_1us = REF_TIME - timedelta(days=7, microseconds=1)
        assert is_journal_fresh(stale_by_1us, max_age_days=7, reference_time=REF_TIME) is False

    def test_stale_entries(self):
        eight_days_ago = REF_TIME - timedelta(days=8)
        two_weeks_ago = REF_TIME - timedelta(days=14)
        six_months_ago = REF_TIME - timedelta(days=180)
        assert is_journal_fresh(eight_days_ago, reference_time=REF_TIME) is False
        assert is_journal_fresh(two_weeks_ago, reference_time=REF_TIME) is False
        assert is_journal_fresh(six_months_ago, reference_time=REF_TIME) is False

    def test_future_timestamp_is_fresh(self):
        # Clock skew or near-future timestamps are not expired
        one_hour_future = REF_TIME + timedelta(hours=1)
        assert is_journal_fresh(one_hour_future, reference_time=REF_TIME) is True

    def test_custom_max_age_days(self):
        four_days_ago = REF_TIME - timedelta(days=4)
        # Fresh under 7-day window, but stale under 3-day window
        assert is_journal_fresh(four_days_ago, max_age_days=7, reference_time=REF_TIME) is True
        assert is_journal_fresh(four_days_ago, max_age_days=3, reference_time=REF_TIME) is False

    def test_timezone_aware_and_offsets(self):
        # 2026-09-21 17:30:00+05:30 is 12:00:00 UTC (identical moment to REF_TIME)
        same_moment_ist = "2026-09-21T17:30:00+05:30"
        assert is_journal_fresh(same_moment_ist, reference_time=REF_TIME) is True

        # 8 days before REF_TIME with EDT offset (-04:00)
        stale_edt = "2026-09-13T08:00:00-04:00"
        assert is_journal_fresh(stale_edt, reference_time=REF_TIME) is False

    def test_naive_timestamps_treated_as_utc(self):
        naive_fresh = datetime(2026, 9, 19, 12, 0, 0)
        naive_stale = datetime(2026, 9, 10, 12, 0, 0)
        naive_ref = datetime(2026, 9, 21, 12, 0, 0)
        assert is_journal_fresh(naive_fresh, reference_time=naive_ref) is True
        assert is_journal_fresh(naive_stale, reference_time=naive_ref) is False


# ---------------------------------------------------------------------------
# 2. aggregate_journal_entries with freshness windowing
# ---------------------------------------------------------------------------

class TestAggregateJournalEntriesFreshness:
    """Verifies that aggregate_journal_entries hides stale values while preserving counts."""

    def test_single_fresh_entry_returned(self):
        fresh_ts = (REF_TIME - timedelta(days=2)).isoformat()
        entry = _entry("j1", fresh_ts, "motivated", "Great workout.")
        res = aggregate_journal_entries([entry], max_age_days=7, reference_time=REF_TIME)
        assert res["journal_count"] == 1
        assert res["latest_journal_summary"] == "Great workout."
        assert res["latest_journal_sentiment"] == "motivated"

    def test_single_stale_entry_hides_summary_and_sentiment_but_preserves_count(self):
        stale_ts = (REF_TIME - timedelta(days=10)).isoformat()
        entry = _entry("j1", stale_ts, "fatigued", "Tired from deadlifts.")
        res = aggregate_journal_entries([entry], max_age_days=7, reference_time=REF_TIME)
        assert res["journal_count"] == 1
        assert res["latest_journal_summary"] is None
        assert res["latest_journal_sentiment"] is None

    def test_newer_fresh_entry_preferred_over_older_stale_entry(self):
        stale_ts = (REF_TIME - timedelta(days=14)).isoformat()
        fresh_ts = (REF_TIME - timedelta(days=1)).isoformat()
        older_stale = _entry("old", stale_ts, "fatigued", "Old fatigue.")
        newer_fresh = _entry("new", fresh_ts, "motivated", "New motivation.")

        res = aggregate_journal_entries([older_stale, newer_fresh], max_age_days=7, reference_time=REF_TIME)
        assert res["journal_count"] == 2
        assert res["latest_journal_summary"] == "New motivation."
        assert res["latest_journal_sentiment"] == "motivated"

    def test_all_stale_entries_preserves_total_count_but_returns_none(self):
        stale_1 = _entry("j1", (REF_TIME - timedelta(days=20)).isoformat(), "fatigued", "Old 1")
        stale_2 = _entry("j2", (REF_TIME - timedelta(days=10)).isoformat(), "motivated", "Old 2")

        res = aggregate_journal_entries([stale_1, stale_2], max_age_days=7, reference_time=REF_TIME)
        assert res["journal_count"] == 2
        assert res["latest_journal_summary"] is None
        assert res["latest_journal_sentiment"] is None

    def test_max_age_days_none_skips_freshness_filtering(self):
        very_old_ts = (REF_TIME - timedelta(days=100)).isoformat()
        old_entry = _entry("j1", very_old_ts, "consistent", "Ancient entry.")
        res = aggregate_journal_entries([old_entry], max_age_days=None, reference_time=REF_TIME)
        assert res["journal_count"] == 1
        assert res["latest_journal_summary"] == "Ancient entry."
        assert res["latest_journal_sentiment"] == "consistent"

    def test_same_day_ordering_preserved_when_both_fresh(self):
        morning_ts = (REF_TIME - timedelta(days=1, hours=4)).isoformat()
        evening_ts = (REF_TIME - timedelta(days=1)).isoformat()
        morning = _entry("m", morning_ts, "fatigued", "Morning tired")
        evening = _entry("e", evening_ts, "motivated", "Evening energized")

        res = aggregate_journal_entries([morning, evening], max_age_days=7, reference_time=REF_TIME)
        assert res["latest_journal_summary"] == "Evening energized"
        assert res["latest_journal_sentiment"] == "motivated"


# ---------------------------------------------------------------------------
# 3. prepare_adaptation_input integration
# ---------------------------------------------------------------------------

class TestPrepareAdaptationInputFreshness:
    """Verifies that prepare_adaptation_input correctly propagates freshness windowing."""

    def test_stale_fatigue_journal_becomes_none_sentiment(self):
        stale_ts = (REF_TIME - timedelta(days=12)).isoformat()
        journals = [_entry("j1", stale_ts, "fatigued", "Stale fatigue summary")]
        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            journals,
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        assert input_data.latest_journal_summary is None
        assert input_data.latest_journal_sentiment is None

    def test_fresh_fatigue_journal_passes_through(self):
        fresh_ts = (REF_TIME - timedelta(days=2)).isoformat()
        journals = [_entry("j1", fresh_ts, "fatigued", "Fresh fatigue summary")]
        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            journals,
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        assert input_data.latest_journal_summary == "Fresh fatigue summary"
        assert input_data.latest_journal_sentiment == "fatigued"

    def test_fresh_motivated_journal_passes_through(self):
        fresh_ts = (REF_TIME - timedelta(hours=12)).isoformat()
        journals = [_entry("j1", fresh_ts, "motivated", "Hit PR")]
        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            journals,
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        assert input_data.latest_journal_summary == "Hit PR"
        assert input_data.latest_journal_sentiment == "motivated"

    def test_empty_journal_list_remains_safe(self):
        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            [],
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        assert input_data.latest_journal_summary is None
        assert input_data.latest_journal_sentiment is None


# ---------------------------------------------------------------------------
# 4. compute_adaptation end-to-end coaching advice impact
# ---------------------------------------------------------------------------

class TestComputeAdaptationWithFreshness:
    """Verifies that stale journal entries do NOT generate coaching recommendations."""

    FATIGUE_REC = "Recent journal reflects fatigue. Prioritize recovery and sleep."
    MOTIVATION_REC = "High motivation noted in recent journal. Channel energy into structured training."

    def test_stale_fatigued_journal_produces_no_journal_recommendations(self):
        stale_ts = (REF_TIME - timedelta(days=30)).isoformat()
        journals = [_entry("j1", stale_ts, "fatigued", "Exhausted after long session")]

        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            journals,
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        decision = compute_adaptation(input_data)

        assert self.FATIGUE_REC not in decision.actionable_recommendations
        assert self.MOTIVATION_REC not in decision.actionable_recommendations

    def test_fresh_fatigued_journal_produces_fatigue_recommendation(self):
        fresh_ts = (REF_TIME - timedelta(days=1)).isoformat()
        journals = [_entry("j1", fresh_ts, "fatigued", "Very tired today")]

        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            journals,
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        decision = compute_adaptation(input_data)

        assert self.FATIGUE_REC in decision.actionable_recommendations

    def test_stale_motivated_journal_produces_no_journal_recommendations(self):
        stale_ts = (REF_TIME - timedelta(days=15)).isoformat()
        journals = [_entry("j1", stale_ts, "motivated", "Hit a new bench PR")]

        input_data = prepare_adaptation_input(
            _profile(),
            _logs(),
            journals,
            journal_max_age_days=7,
            reference_time=REF_TIME,
        )
        decision = compute_adaptation(input_data)

        assert self.MOTIVATION_REC not in decision.actionable_recommendations
