"""
Unit tests for aggregate_journal_entries — the pure function that derives
journal_count, latest_journal_summary, and latest_journal_sentiment from
raw journal entry records.
"""

import copy
from datetime import date, datetime

import pytest
from app.engine.adaptation import aggregate_journal_entries


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_entry(
    created_at="2026-09-15",
    sentiment_tag="consistent",
    summary="Stayed on track today.",
    **extra,
):
    """Build a minimal journal entry dict matching the JournalRepository schema."""
    entry = {
        "id": extra.pop("id", "journal_1"),
        "user_id": extra.pop("user_id", "user_001"),
        "entry_text": extra.pop("entry_text", "Sample journal text"),
        "sentiment_tag": sentiment_tag,
        "ai_feedback": {
            "sentiment_tag": sentiment_tag,
            "summary": summary,
            "actionable_tips": ["Tip 1"],
            "encouragement_quote": "Keep going!",
        },
        "created_at": created_at,
    }
    entry.update(extra)
    return entry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmptyInput:
    def test_empty_list(self):
        result = aggregate_journal_entries([])
        assert result == {
            "journal_count": 0,
            "latest_journal_summary": None,
            "latest_journal_sentiment": None,
        }


class TestSingleEntry:
    def test_single_entry_returns_its_data(self):
        entry = _make_entry(
            created_at="2026-09-15",
            sentiment_tag="motivated",
            summary="Feeling strong after PR.",
        )
        result = aggregate_journal_entries([entry])

        assert result["journal_count"] == 1
        assert result["latest_journal_summary"] == "Feeling strong after PR."
        assert result["latest_journal_sentiment"] == "motivated"


class TestMultipleEntriesOutOfOrder:
    def test_picks_most_recent_by_date(self):
        older = _make_entry(
            created_at="2026-09-10",
            sentiment_tag="fatigued",
            summary="Tired from deadlift session.",
            id="j1",
        )
        newest = _make_entry(
            created_at="2026-09-20",
            sentiment_tag="motivated",
            summary="Crushed upper body day.",
            id="j2",
        )
        middle = _make_entry(
            created_at="2026-09-15",
            sentiment_tag="consistent",
            summary="Steady progress.",
            id="j3",
        )
        # Input order: oldest, newest, middle → should still pick newest
        result = aggregate_journal_entries([older, newest, middle])

        assert result["journal_count"] == 3
        assert result["latest_journal_summary"] == "Crushed upper body day."
        assert result["latest_journal_sentiment"] == "motivated"

    def test_iso_timestamp_strings_parsed(self):
        """Verify ISO-8601 timestamps (from Supabase) are parsed correctly."""
        early = _make_entry(
            created_at="2026-09-10T08:00:00+00:00",
            sentiment_tag="fatigued",
            summary="Morning drag.",
            id="j1",
        )
        late = _make_entry(
            created_at="2026-09-20T22:15:30.123456+05:30",
            sentiment_tag="consistent",
            summary="Late night log.",
            id="j2",
        )
        result = aggregate_journal_entries([early, late])

        assert result["journal_count"] == 2
        assert result["latest_journal_summary"] == "Late night log."
        assert result["latest_journal_sentiment"] == "consistent"


class TestLatestEntrySelection:
    def test_datetime_objects_accepted(self):
        entry = _make_entry(
            created_at=datetime(2026, 9, 18, 10, 30),
            sentiment_tag="motivated",
            summary="Datetime entry.",
        )
        result = aggregate_journal_entries([entry])
        assert result["latest_journal_summary"] == "Datetime entry."

    def test_date_objects_accepted(self):
        entry = _make_entry(
            created_at=date(2026, 9, 18),
            sentiment_tag="consistent",
            summary="Date entry.",
        )
        result = aggregate_journal_entries([entry])
        assert result["latest_journal_summary"] == "Date entry."


class TestNullSummaryOrSentiment:
    def test_null_summary_returns_none(self):
        entry = _make_entry(sentiment_tag="motivated", summary=None)
        result = aggregate_journal_entries([entry])

        assert result["latest_journal_summary"] is None
        assert result["latest_journal_sentiment"] == "motivated"

    def test_null_sentiment_returns_none(self):
        entry = _make_entry(sentiment_tag=None, summary="Got summary.")
        result = aggregate_journal_entries([entry])

        assert result["latest_journal_summary"] == "Got summary."
        assert result["latest_journal_sentiment"] is None

    def test_empty_string_summary_treated_as_none(self):
        entry = _make_entry(sentiment_tag="consistent", summary="")
        result = aggregate_journal_entries([entry])
        assert result["latest_journal_summary"] is None

    def test_empty_string_sentiment_treated_as_none(self):
        entry = _make_entry(sentiment_tag="", summary="Has summary.")
        result = aggregate_journal_entries([entry])
        assert result["latest_journal_sentiment"] is None

    def test_both_null(self):
        entry = _make_entry(sentiment_tag=None, summary=None)
        result = aggregate_journal_entries([entry])

        assert result["journal_count"] == 1
        assert result["latest_journal_summary"] is None
        assert result["latest_journal_sentiment"] is None


class TestMalformedOrMissingDate:
    def test_missing_created_at_skipped_for_latest(self):
        """Entries without created_at are counted but can't be chosen as latest."""
        no_date = _make_entry(
            sentiment_tag="fatigued",
            summary="No date entry.",
            id="j1",
        )
        del no_date["created_at"]

        with_date = _make_entry(
            created_at="2026-09-10",
            sentiment_tag="motivated",
            summary="Dated entry.",
            id="j2",
        )

        result = aggregate_journal_entries([no_date, with_date])
        assert result["journal_count"] == 2
        assert result["latest_journal_summary"] == "Dated entry."
        assert result["latest_journal_sentiment"] == "motivated"

    def test_malformed_date_skipped(self):
        bad = _make_entry(
            created_at="not-a-date",
            sentiment_tag="fatigued",
            summary="Bad date.",
            id="j1",
        )
        good = _make_entry(
            created_at="2026-09-20",
            sentiment_tag="consistent",
            summary="Good date.",
            id="j2",
        )
        result = aggregate_journal_entries([bad, good])
        assert result["journal_count"] == 2
        assert result["latest_journal_summary"] == "Good date."

    def test_all_malformed_dates_returns_none_for_latest(self):
        """If every entry has a malformed date, count is preserved but
        latest fields are None."""
        entries = [
            _make_entry(created_at="garbage", id="j1"),
            _make_entry(created_at=12345, id="j2"),
        ]
        result = aggregate_journal_entries(entries)
        assert result["journal_count"] == 2
        assert result["latest_journal_summary"] is None
        assert result["latest_journal_sentiment"] is None

    def test_none_created_at_skipped(self):
        entry = _make_entry(created_at=None)
        result = aggregate_journal_entries([entry])
        assert result["journal_count"] == 1
        assert result["latest_journal_summary"] is None


class TestInputImmutability:
    def test_input_list_and_dicts_not_mutated(self):
        entries = [
            _make_entry(created_at="2026-09-20", id="j1"),
            _make_entry(created_at="2026-09-10", id="j2"),
        ]
        entries_copy = copy.deepcopy(entries)

        aggregate_journal_entries(entries)

        assert entries == entries_copy
        # Verify list order unchanged
        assert entries[0]["id"] == "j1"
        assert entries[1]["id"] == "j2"


class TestDeterministicRepeatedCalls:
    def test_same_result_on_repeated_calls(self):
        entries = [
            _make_entry(created_at="2026-09-20", sentiment_tag="motivated", summary="A", id="j1"),
            _make_entry(created_at="2026-09-10", sentiment_tag="fatigued", summary="B", id="j2"),
        ]

        result1 = aggregate_journal_entries(entries)
        result2 = aggregate_journal_entries(entries)
        result3 = aggregate_journal_entries(entries)

        assert result1 == result2 == result3
