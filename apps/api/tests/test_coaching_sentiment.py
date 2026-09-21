"""
Unit and regression tests for journal coaching sentiment keyword matching.

Verifies:
- Partial-word matches like "protein" and "project" do not falsely trigger "motivated"
- Legitimate motivated keywords (including "PR", "great", "strong", etc.) still match
- Fatigue keywords (including "tired", "fatigued", "soreness", etc.) match correctly
- Punctuation, casing, and word boundaries are handled properly
- Neutral entries fall back to "consistent"
"""

import pytest
from app.modules.coaching import (
    generate_fallback_coaching_feedback,
    _contains_keyword,
    FATIGUE_KEYWORDS,
    MOTIVATED_KEYWORDS,
)


class TestSentimentKeywordFalsePositives:
    """Ensure sub-words do not trigger unintended sentiment categories."""

    @pytest.mark.parametrize(
        "text",
        [
            "Hit my protein target today and drank plenty of water.",
            "Ate 150g of protein and stayed within my calorie budget.",
            "Bought some whey protein powder for post-workout shakes.",
            "Working on my coding project all afternoon.",
            "Had a long project meeting before going to the gym.",
            "Making slow progress on my training routine.",
            "Good form practice during warmups.",
            "No problem finishing all scheduled sets.",
            "Prepared my lunch and dinner for tomorrow.",
            "Took pre-workout before my normal session.",
            "Prioritized hydration throughout the workday.",
        ],
    )
    def test_pr_substring_words_do_not_match_motivated(self, text: str):
        feedback = generate_fallback_coaching_feedback(text)
        assert feedback.sentiment_tag == "consistent"

    def test_protein_alone_is_consistent(self):
        feedback = generate_fallback_coaching_feedback("Protein intake was on point today.")
        assert feedback.sentiment_tag == "consistent"

    def test_project_alone_is_consistent(self):
        feedback = generate_fallback_coaching_feedback("Completed my office project today.")
        assert feedback.sentiment_tag == "consistent"


class TestLegitimateMotivatedSentiment:
    """Verify legitimate motivation keywords still match accurately."""

    @pytest.mark.parametrize(
        "text",
        [
            "Hit a new PR on bench press today!",
            "Crushed a new pr on deadlift.",
            "Hit two PRs during my training session.",
            "Had a fantastic workout today, smashed my personal record on squat!",
            "Felt super strong and pushed hard through every set.",
            "Best workout of the entire month.",
            "Today felt easy and smooth.",
            "High energy and feeling motivated to continue.",
            "Strong motivation to keep pushing forward.",
            "Set a new squat record today.",
        ],
    )
    def test_motivated_keywords_detected(self, text: str):
        feedback = generate_fallback_coaching_feedback(text)
        assert feedback.sentiment_tag == "motivated"

    @pytest.mark.parametrize(
        "pr_snippet",
        [
            "Hit a PR!",
            "Hit a PR.",
            "New PR, feeling great",
            "(PR) achieved on bench",
            "Squat PR: 140kg",
            "Bench PR/record broken",
        ],
    )
    def test_pr_with_various_punctuation_matches(self, pr_snippet: str):
        feedback = generate_fallback_coaching_feedback(pr_snippet)
        assert feedback.sentiment_tag == "motivated"


class TestLegitimateFatigueSentiment:
    """Verify fatigue keywords match and take precedence over motivation if present."""

    @pytest.mark.parametrize(
        "text",
        [
            "Feeling very tired after training.",
            "Completely exhausted from lack of sleep.",
            "Suffering from heavy fatigue today.",
            "Felt fatigued during my warmup.",
            "Shoulders are sore from yesterday.",
            "Dealing with intense muscle soreness.",
            "Felt sharp pain in my elbow during bench.",
            "Knee was painful when squatting.",
            "Felt weak on all heavy sets.",
            "Experiencing general body weakness today.",
        ],
    )
    def test_fatigue_keywords_detected(self, text: str):
        feedback = generate_fallback_coaching_feedback(text)
        assert feedback.sentiment_tag == "fatigued"

    def test_fatigue_takes_precedence_over_motivation(self):
        # When both fatigue and motivation keywords are present, fatigue is detected first
        text = "Pushed hard and hit a PR, but now I am exhausted and sore."
        feedback = generate_fallback_coaching_feedback(text)
        assert feedback.sentiment_tag == "fatigued"


class TestConsistentFallback:
    """Verify neutral journal entries default to consistent."""

    @pytest.mark.parametrize(
        "text",
        [
            "Completed my scheduled 45-minute workout.",
            "Followed the meal plan and drank 3 liters of water.",
            "Just a regular day following the routine as planned.",
            "Rest day today, did 20 minutes of light walking.",
        ],
    )
    def test_neutral_text_defaults_to_consistent(self, text: str):
        feedback = generate_fallback_coaching_feedback(text)
        assert feedback.sentiment_tag == "consistent"


class TestKeywordMatcherHelper:
    """Unit tests directly on the _contains_keyword helper."""

    def test_word_boundary_isolation(self):
        assert _contains_keyword("pr", ["pr"]) is True
        assert _contains_keyword("PR", ["pr"]) is True
        assert _contains_keyword("protein", ["pr"]) is False
        assert _contains_keyword("project", ["pr"]) is False
        assert _contains_keyword("spring", ["pr"]) is False

    def test_case_insensitivity(self):
        assert _contains_keyword("TIRED", ["tired"]) is True
        assert _contains_keyword("Motivated", ["motivated"]) is True
        assert _contains_keyword("FaTiGuEd", ["fatigued"]) is True

    def test_multi_word_phrase(self):
        assert _contains_keyword("Hit a personal record", ["personal record"]) is True
        assert _contains_keyword("impersonal recorder", ["personal record"]) is False
