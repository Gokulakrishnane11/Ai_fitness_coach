import copy
import itertools
from datetime import date, datetime, timezone

import pytest

from app.engine.adaptation import aggregate_journal_entries, _parse_journal_timestamp


def _entry(entry_id, created_at, sentiment, summary):
    return {
        "id": entry_id,
        "created_at": created_at,
        "sentiment_tag": sentiment,
        "ai_feedback": {"summary": summary},
    }


EVENING = _entry("evening", "2026-09-15T18:00:00+00:00", "motivated", "evening")
MORNING = _entry("morning", "2026-09-15T09:00:00+00:00", "fatigued", "morning")


def test_same_day_latest_is_evening_when_input_newest_first():
    result = aggregate_journal_entries([EVENING, MORNING])
    assert result["latest_journal_summary"] == "evening"
    assert result["latest_journal_sentiment"] == "motivated"
    assert result["journal_count"] == 2


def test_same_day_latest_is_evening_when_input_oldest_first():
    result = aggregate_journal_entries([MORNING, EVENING])
    assert result["latest_journal_summary"] == "evening"
    assert result["latest_journal_sentiment"] == "motivated"


def test_result_independent_of_input_order():
    entries = [
        _entry("a", "2026-09-14T22:00:00+00:00", "consistent", "a"),
        MORNING,
        EVENING,
        _entry("z", "2026-09-13T08:00:00+00:00", "fatigued", "z"),
    ]
    results = {
        tuple(sorted(aggregate_journal_entries(list(p)).items()))
        for p in itertools.permutations(entries)
    }
    assert len(results) == 1
    assert dict(next(iter(results)))["latest_journal_summary"] == "evening"


def test_microsecond_precision_orders_correctly():
    a = _entry("a", "2026-09-15T10:30:00.123456+00:00", "fatigued", "earlier")
    b = _entry("b", "2026-09-15T10:30:00.123457+00:00", "motivated", "later")
    assert aggregate_journal_entries([b, a])["latest_journal_summary"] == "later"
    assert aggregate_journal_entries([a, b])["latest_journal_summary"] == "later"


def test_different_utc_offsets_compared_as_absolute_time():
    # 20:00+05:30 is 14:30 UTC, which is EARLIER than 15:00 UTC even though 20 > 15
    ist = _entry("ist", "2026-09-15T20:00:00+05:30", "fatigued", "ist")
    utc = _entry("utc", "2026-09-15T15:00:00+00:00", "motivated", "utc")
    assert aggregate_journal_entries([ist, utc])["latest_journal_summary"] == "utc"
    assert aggregate_journal_entries([utc, ist])["latest_journal_summary"] == "utc"


def test_mixed_naive_and_aware_timestamps_do_not_raise():
    naive = _entry("naive", "2026-09-15T09:00:00", "fatigued", "naive")
    aware = _entry("aware", "2026-09-15T18:00:00+00:00", "motivated", "aware")
    assert aggregate_journal_entries([naive, aware])["latest_journal_summary"] == "aware"
    assert aggregate_journal_entries([aware, naive])["latest_journal_summary"] == "aware"


def test_fractional_seconds_with_fewer_than_six_digits():
    a = _entry("a", "2026-09-15T10:30:00.12+00:00", "fatigued", "a")
    b = _entry("b", "2026-09-15T10:31:00.5+00:00", "motivated", "b")
    assert aggregate_journal_entries([a, b])["latest_journal_summary"] == "b"
    assert aggregate_journal_entries([b, a])["latest_journal_summary"] == "b"


def test_date_only_and_timestamp_strings_both_supported():
    date_only = _entry("d", "2026-09-14", "fatigued", "date_only")
    stamped = _entry("t", "2026-09-15T00:00:01+00:00", "motivated", "stamped")
    assert aggregate_journal_entries([date_only, stamped])["latest_journal_summary"] == "stamped"


def test_entries_without_parseable_timestamp_are_counted_but_never_latest():
    bad = _entry("bad", "not-a-date", "motivated", "bad")
    missing = {"id": "m", "sentiment_tag": "motivated", "ai_feedback": {"summary": "missing"}}
    good = _entry("good", "2026-09-15T09:00:00+00:00", "fatigued", "good")
    result = aggregate_journal_entries([bad, missing, good])
    assert result["journal_count"] == 3
    assert result["latest_journal_summary"] == "good"
    assert result["latest_journal_sentiment"] == "fatigued"


def test_exact_timestamp_tie_is_deterministic_by_id():
    t = "2026-09-15T09:00:00+00:00"
    a = _entry("a", t, "fatigued", "a")
    b = _entry("b", t, "motivated", "b")
    assert aggregate_journal_entries([a, b]) == aggregate_journal_entries([b, a])
    assert aggregate_journal_entries([a, b])["latest_journal_summary"] == "b"


def test_input_list_is_not_mutated_or_reordered():
    entries = [EVENING, MORNING]
    snapshot = copy.deepcopy(entries)
    aggregate_journal_entries(entries)
    assert entries == snapshot


@pytest.mark.parametrize("value", [None, "", "2026", "garbage", 12345, ["2026-09-15"]])
def test_parse_journal_timestamp_returns_none_for_unusable_values(value):
    assert _parse_journal_timestamp(value) is None


def test_parse_journal_timestamp_normalizes_to_utc():
    parsed = _parse_journal_timestamp("2026-09-15T20:00:00+05:30")
    assert parsed == datetime(2026, 9, 15, 14, 30, tzinfo=timezone.utc)
    assert parsed.utcoffset().total_seconds() == 0
    assert _parse_journal_timestamp("2026-09-15T09:00:00") == datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc)
    assert _parse_journal_timestamp("2026-09-15") == datetime(2026, 9, 15, tzinfo=timezone.utc)
    assert _parse_journal_timestamp("2026-09-15T09:00:00Z") == datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc)
    assert _parse_journal_timestamp(date(2026, 9, 15)) == datetime(2026, 9, 15, tzinfo=timezone.utc)
    assert _parse_journal_timestamp(datetime(2026, 9, 15, 9, 0)) == datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc)
