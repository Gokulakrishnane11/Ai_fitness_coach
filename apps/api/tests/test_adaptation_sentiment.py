"""
Unit tests for normalize_journal_sentiment — the pure function that normalizes
raw journal sentiment tags to match AdaptationInput's allowed literal values.
"""

import pytest
from app.engine.adaptation import normalize_journal_sentiment


class TestNormalizeJournalSentiment:
    """Test suite verifying behavior of normalize_journal_sentiment."""

    @pytest.mark.parametrize("sentiment", ["fatigued", "motivated", "consistent"])
    def test_each_valid_sentiment(self, sentiment: str) -> None:
        """Each allowed sentiment is preserved exactly as-is."""
        assert normalize_journal_sentiment(sentiment) == sentiment

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("FATIGUED", "fatigued"),
            ("MOTIVATED", "motivated"),
            ("CONSISTENT", "consistent"),
            ("MoTiVaTeD", "motivated"),
            ("Fatigued", "fatigued"),
        ],
    )
    def test_uppercase_input(self, raw: str, expected: str) -> None:
        """Uppercase and mixed-case inputs are converted to lowercase."""
        assert normalize_journal_sentiment(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("  fatigued  ", "fatigued"),
            ("\tmotivated\n", "motivated"),
            ("   consistent   ", "consistent"),
            (" \n  FATIGUED \t ", "fatigued"),
        ],
    )
    def test_surrounding_whitespace(self, raw: str, expected: str) -> None:
        """Surrounding whitespace and newlines are stripped."""
        assert normalize_journal_sentiment(raw) == expected

    def test_none_input(self) -> None:
        """None input returns None."""
        assert normalize_journal_sentiment(None) is None

    def test_empty_string(self) -> None:
        """Empty string returns None."""
        assert normalize_journal_sentiment("") is None

    @pytest.mark.parametrize("whitespace", [" ", "   ", "\t", "\n", " \t \n "])
    def test_whitespace_only_string(self, whitespace: str) -> None:
        """Whitespace-only strings return None."""
        assert normalize_journal_sentiment(whitespace) is None

    def test_stressed_returns_none(self) -> None:
        """'stressed' is not mapped to 'fatigued' and returns None."""
        assert normalize_journal_sentiment("stressed") is None
        assert normalize_journal_sentiment("STRESSED") is None
        assert normalize_journal_sentiment("  stressed  ") is None

    @pytest.mark.parametrize(
        "unknown",
        [
            "unknown",
            "happy",
            "sad",
            "neutral",
            "exhausted",
            "energized",
            "random text with motivation",
            "123",
            "!@#$",
        ],
    )
    def test_arbitrary_unknown_value_returns_none(self, unknown: str) -> None:
        """Arbitrary unrecognized values return None."""
        assert normalize_journal_sentiment(unknown) is None

    def test_repeated_calls_are_deterministic(self) -> None:
        """Multiple repeated calls with the same input yield identical results."""
        inputs = ["motivated", "  fatigued  ", "CONSISTENT", "stressed", None, "", "other"]
        for val in inputs:
            res1 = normalize_journal_sentiment(val)
            res2 = normalize_journal_sentiment(val)
            res3 = normalize_journal_sentiment(val)
            assert res1 == res2 == res3

    @pytest.mark.parametrize("non_string", [123, 45.6, True, False, [], {}, object()])
    def test_non_string_types_safely_return_none(self, non_string: object) -> None:
        """Non-string inputs are handled safely without raising exceptions."""
        assert normalize_journal_sentiment(non_string) is None  # type: ignore[arg-type]
