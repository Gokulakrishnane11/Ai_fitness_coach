"""
Unit Tests for Empirical Scoring Layer and Zero-Data Neutrality in Adaptation Engine.
File: apps/api/tests/test_adaptation_scoring.py

Verifies:
1. Empirical adherence evaluation (100 remains 100, 75 remains 75, None when missing)
2. Empirical recovery evaluation (100 remains 100, None when missing)
3. Empirical plateau probability (None when missing, clamped when provided)
4. Scalar scorers (stress, sleep, injury)
5. Zero-data neutrality helper (has_sufficient_adaptation_data)
6. Readiness factor:
   - Uses explicit numeric inputs only
   - Rejects dict input with TypeError
   - Rejects AdaptationDecision input with TypeError
   - Strictly bounded between 0.45 and 1.12
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.adaptation import (
    clamp,
    has_sufficient_adaptation_data,
    score_adherence,
    score_recovery,
    score_stress,
    score_sleep_quality,
    score_plateau_probability,
    score_injury_risk,
    score_nutrition,
    score_training_quality,
    calculate_observed_days,
    calculate_readiness_factor,
    AdaptationDecision,
)


# ---------------------------------------------------------------------------
# 1. Empirical Adherence Tests
# ---------------------------------------------------------------------------

def test_empirical_adherence_values():
    assert score_adherence(100) == 100
    assert score_adherence(75) == 75
    assert score_adherence(50) == 50
    assert score_adherence(0) == 0


def test_empirical_adherence_missing():
    assert score_adherence(None) is None
    assert score_adherence() is None


def test_empirical_adherence_clamping():
    assert score_adherence(-15) == 0
    assert score_adherence(125) == 100


# ---------------------------------------------------------------------------
# 2. Empirical Recovery Tests
# ---------------------------------------------------------------------------

def test_empirical_recovery_values():
    assert score_recovery(100) == 100
    assert score_recovery(80) == 80
    assert score_recovery(0) == 0


def test_empirical_recovery_missing():
    assert score_recovery(None) is None
    assert score_recovery() is None


def test_empirical_recovery_clamping():
    assert score_recovery(-20) == 0
    assert score_recovery(150) == 100


# ---------------------------------------------------------------------------
# 3. Empirical Plateau Probability Tests
# ---------------------------------------------------------------------------

def test_empirical_plateau_missing():
    assert score_plateau_probability(None) is None
    assert score_plateau_probability() is None


def test_empirical_plateau_clamping():
    assert score_plateau_probability(15) == 15
    assert score_plateau_probability(-10) == 0
    assert score_plateau_probability(120) == 100


# ---------------------------------------------------------------------------
# 4. Empirical Stress, Sleep, and Injury Scorers
# ---------------------------------------------------------------------------

def test_empirical_stress_score():
    assert score_stress(35) == 35
    assert score_stress(None) is None
    assert score_stress(-5) == 0
    assert score_stress(115) == 100


def test_empirical_sleep_quality_score():
    assert score_sleep_quality(85) == 85
    assert score_sleep_quality(None) is None
    assert score_sleep_quality(-1) == 0
    assert score_sleep_quality(105) == 100


def test_empirical_injury_risk_score():
    assert score_injury_risk(10) == 10
    assert score_injury_risk(None) is None
    assert score_injury_risk(-10) == 0
    assert score_injury_risk(110) == 100


# ---------------------------------------------------------------------------
# 5. Zero-Data Neutrality Helper Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("log_count", [0, 1, 2])
def test_insufficient_adaptation_data(log_count):
    assert has_sufficient_adaptation_data(log_count) is False


@pytest.mark.parametrize("log_count", [3, 7, 14, 30])
def test_sufficient_adaptation_data(log_count):
    assert has_sufficient_adaptation_data(log_count) is True


def test_sufficient_adaptation_data_custom_minimum():
    assert has_sufficient_adaptation_data(4, minimum_logs=5) is False
    assert has_sufficient_adaptation_data(5, minimum_logs=5) is True


# ---------------------------------------------------------------------------
# 6. Readiness Factor Tests: Explicit Numerics & Type Rejections
# ---------------------------------------------------------------------------

def test_readiness_calculation_numeric_inputs():
    factor = calculate_readiness_factor(
        adherence_score=90,
        recovery_score=80,
        stress_score=20,
        sleep_quality=80,
        plateau_probability=5,
        injury_risk=5,
    )
    assert isinstance(factor, float)
    assert 0.80 <= factor <= 0.81


def test_readiness_calculation_rejects_dict_input():
    with pytest.raises(TypeError, match="explicit numeric scores only"):
        calculate_readiness_factor(
            {"adherence_score": 90},  # type: ignore
            80, 20, 80, 5, 5
        )


def test_readiness_calculation_rejects_adaptation_decision_input():
    decision = AdaptationDecision(
        adherence_score=90,
        recovery_score=80,
        stress_score=20,
        sleep_quality=80,
        plateau_probability=5,
        injury_risk=5,
        readiness_factor=0.8034,
    )
    with pytest.raises(TypeError, match="explicit numeric scores only"):
        calculate_readiness_factor(
            decision,  # type: ignore
            80, 20, 80, 5, 5
        )


def test_readiness_calculation_rejects_non_numeric_types():
    with pytest.raises(TypeError):
        calculate_readiness_factor("90", 80, 20, 80, 5, 5)  # type: ignore


# ---------------------------------------------------------------------------
# 7. Readiness Factor Boundedness [0.45, 1.12]
# ---------------------------------------------------------------------------

def test_readiness_lower_bound_clamp():
    # Worst case: 0 for all positive readiness, 100 for all risks
    factor = calculate_readiness_factor(
        adherence_score=0,
        recovery_score=0,
        stress_score=100,
        sleep_quality=0,
        plateau_probability=100,
        injury_risk=100,
        nutrition_score=0,
        training_quality=0,
        motivation_score=0,
    )
    assert factor == 0.45


def test_readiness_upper_bound_clamp():
    # Best case: 100 for all positive readiness, 0 for all risks
    factor = calculate_readiness_factor(
        adherence_score=100,
        recovery_score=100,
        stress_score=0,
        sleep_quality=100,
        plateau_probability=0,
        injury_risk=0,
        nutrition_score=100,
        training_quality=100,
        motivation_score=100,
    )
    assert factor <= 1.12
    assert factor >= 0.45


def test_clamp_utility():
    assert clamp(50, 0, 100) == 50
    assert clamp(-10, 0, 100) == 0
    assert clamp(110, 0, 100) == 100
    assert clamp("invalid", 0, 100) == 0


# ---------------------------------------------------------------------------
# 8. Empirical Nutrition Scoring Tests (Task 11A)
# ---------------------------------------------------------------------------

def test_score_nutrition_calories_only():
    """Verify calories-only input re-normalizes weight to 100%."""
    # Exact target
    assert score_nutrition(actual_calories=2000, target_calories=2000) == 100.0
    # 10% below target -> 90.0
    assert score_nutrition(actual_calories=1800, target_calories=2000) == 90.0
    # 10% above target -> 90.0
    assert score_nutrition(actual_calories=2200, target_calories=2000) == 90.0


def test_score_nutrition_all_four_macros_present():
    """Verify all 4 macros are weighted deterministically (40/30/15/15)."""
    # Exact targets for all: score should be 100.0
    score = score_nutrition(
        actual_calories=2000,
        target_calories=2000,
        actual_protein_g=150,
        target_protein_g=150,
        actual_carbs_g=200,
        target_carbs_g=200,
        actual_fat_g=60,
        target_fat_g=60,
    )
    assert score == 100.0

    # Calories 10% off (sub=90), protein 20% off (sub=80), carbs exact (sub=100), fat exact (sub=100)
    # Expected: (90*0.40) + (80*0.30) + (100*0.15) + (100*0.15) = 36 + 24 + 15 + 15 = 90.0
    score_mixed = score_nutrition(
        actual_calories=1800,  # 10% error -> 90.0
        target_calories=2000,
        actual_protein_g=120,  # 20% error -> 80.0
        target_protein_g=150,
        actual_carbs_g=200,    # exact -> 100.0
        target_carbs_g=200,
        actual_fat_g=60,       # exact -> 100.0
        target_fat_g=60,
    )
    assert score_mixed == 90.0


def test_score_nutrition_missing_individual_macros():
    """Verify missing individual macros are NOT treated as zero intake and weights re-normalize."""
    # Only calories and protein (0.40 and 0.30 weights -> sum 0.70)
    # calories exact (100.0), protein 20% off (80.0)
    # expected: (100.0 * 0.40 + 80.0 * 0.30) / 0.70 = (40 + 24) / 0.70 = 64 / 0.70 = 91.43
    score = score_nutrition(
        actual_calories=2000,
        target_calories=2000,
        actual_protein_g=120,
        target_protein_g=150,
        actual_carbs_g=None,
        target_carbs_g=200,
        actual_fat_g=None,
        target_fat_g=60,
    )
    assert score == 91.43


def test_score_nutrition_no_data_returns_none():
    """Verify no nutrition data returns None rather than claiming a measured score."""
    assert score_nutrition() is None
    assert score_nutrition(actual_calories=None, target_calories=2000) is None
    assert score_nutrition(actual_calories=2000, target_calories=None) is None
    assert score_nutrition(target_calories=2000, target_protein_g=150) is None


def test_score_nutrition_below_near_above_target():
    """Verify nutrition values below, near, and above target produce expected scores."""
    # Near target: 5% off
    assert score_nutrition(actual_calories=2100, target_calories=2000) == 95.0
    # Far above target: 100% off (4000 vs 2000) -> 0.0
    assert score_nutrition(actual_calories=4000, target_calories=2000) == 0.0
    # Extremely above target: 150% off (5000 vs 2000) -> clamped to 0.0
    assert score_nutrition(actual_calories=5000, target_calories=2000) == 0.0


def test_score_nutrition_bounds():
    """Verify score_nutrition is strictly bounded [0.0, 100.0]."""
    score_high = score_nutrition(actual_calories=2000, target_calories=2000)
    assert 0.0 <= score_high <= 100.0

    score_zero = score_nutrition(actual_calories=10000, target_calories=2000)
    assert score_zero == 0.0

    # Negative intake clamped safely to 0
    score_neg = score_nutrition(actual_calories=-500, target_calories=2000)
    assert score_neg == 0.0


# ---------------------------------------------------------------------------
# 9. Empirical Training Quality Scoring Tests (Task 11A)
# ---------------------------------------------------------------------------

def test_score_training_quality_workout_adherence_only():
    """Verify training quality calculation with workout adherence only."""
    assert score_training_quality(workout_adherence=100) == 100.0
    assert score_training_quality(workout_adherence=75) == 75.0
    assert score_training_quality(completed_workouts=3, planned_workouts=4) == 75.0
    assert score_training_quality(completed_workouts=4, planned_workouts=4) == 100.0


def test_score_training_quality_energy_rating_only():
    """Verify training quality calculation with energy rating only (1-10 scaled to 0-100)."""
    assert score_training_quality(average_energy_rating=10) == 100.0
    assert score_training_quality(average_energy_rating=8) == 80.0
    assert score_training_quality(average_energy_rating=5.5) == 55.0


def test_score_training_quality_both_present():
    """Verify weighted combination (60% adherence, 40% energy)."""
    # 80 adherence, 7.0 energy (70.0) -> (80 * 0.60) + (70 * 0.40) = 48 + 28 = 76.0
    score = score_training_quality(workout_adherence=80, average_energy_rating=7.0)
    assert score == 76.0

    # Completed workouts (3/4 = 75%) and energy (8.0 -> 80.0) -> (75 * 0.60) + (80 * 0.40) = 45 + 32 = 77.0
    score_cw = score_training_quality(
        completed_workouts=3, planned_workouts=4, average_energy_rating=8.0
    )
    assert score_cw == 77.0


def test_score_training_quality_missing_data_returns_none():
    """Verify None returned when no training data exists."""
    assert score_training_quality() is None
    assert score_training_quality(workout_adherence=None, average_energy_rating=None) is None
    assert score_training_quality(completed_workouts=None, planned_workouts=None) is None


def test_score_training_quality_bounds():
    """Verify training quality is bounded [0.0, 100.0]."""
    assert score_training_quality(workout_adherence=150) == 100.0
    assert score_training_quality(workout_adherence=-20) == 0.0
    assert score_training_quality(average_energy_rating=15) == 100.0
    assert score_training_quality(average_energy_rating=-2) == 0.0
    assert score_training_quality(completed_workouts=-2, planned_workouts=4, window_days=7) == 0.0
    assert score_training_quality(completed_workouts=50, planned_workouts=4, window_days=7) == 100.0


# 10. Training Adherence Window Normalization Audit Tests
# ---------------------------------------------------------------------------

def test_score_training_quality_exactly_7_calendar_days():
    """1. Exactly 7 calendar days: expected workouts equal planned_workouts directly."""
    # 4 of 4 planned workouts in 7 days -> 100.0%
    assert score_training_quality(
        completed_workouts=4, planned_workouts=4, window_days=7
    ) == 100.0

    # 3 of 4 planned workouts in 7 days -> 3 / 4.0 = 75.0%
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=7
    ) == 75.0

    # 2 of 4 planned workouts in 7 days -> 2 / 4.0 = 50.0%
    assert score_training_quality(
        completed_workouts=2, planned_workouts=4, window_days=7
    ) == 50.0


def test_score_training_quality_fewer_than_7_calendar_days():
    """2. Fewer than 7 calendar days: expected workouts prorated by (days / 7)."""
    # 4 planned per week over 3 days -> expected = 4 * (3 / 7) = 1.7142857
    # 1 completed workout -> 1 / 1.7142857 = 58.333% -> 58.33
    assert score_training_quality(
        completed_workouts=1, planned_workouts=4, window_days=3
    ) == 58.33

    # 4 planned per week over 5 days -> expected = 4 * (5 / 7) = 2.8571428
    # 2 completed workouts -> 2 / 2.8571428 = 70.0%
    assert score_training_quality(
        completed_workouts=2, planned_workouts=4, window_days=5
    ) == 70.0


def test_score_training_quality_more_than_7_calendar_days():
    """3. More than 7 calendar days: expected workouts scaled over the multi-week window."""
    # 4 planned per week over 14 days (2 weeks) -> expected = 4 * (14 / 7) = 8.0
    # 6 completed workouts -> 6 / 8.0 = 75.0%
    assert score_training_quality(
        completed_workouts=6, planned_workouts=4, window_days=14
    ) == 75.0

    # 8 completed workouts -> 8 / 8.0 = 100.0%
    assert score_training_quality(
        completed_workouts=8, planned_workouts=4, window_days=14
    ) == 100.0

    # 3 planned per week over 21 days (3 weeks) -> expected = 3 * (21 / 7) = 9.0
    # 6 completed workouts -> 6 / 9.0 = 66.67%
    assert score_training_quality(
        completed_workouts=6, planned_workouts=3, window_days=21
    ) == 66.67


def test_score_training_quality_gaps_in_logged_dates():
    """4. Gaps in logged dates: window accounts for calendar coverage from earliest to latest date."""
    # 3 daily logs spread over 7 calendar days (e.g. Sept 1, Sept 4, Sept 7)
    logs_7d_span = [
        {"log_date": "2026-09-01", "workout_completed": True},
        {"log_date": "2026-09-04", "workout_completed": True},
        {"log_date": "2026-09-07", "workout_completed": True},
    ]
    observed_days = calculate_observed_days(logs_7d_span)
    assert observed_days == 7  # (09-07 - 09-01) + 1 = 7 days, NOT 3 logs

    # With 4 planned workouts per week across that 7-day span, expected is 4.0
    # 3 workouts completed -> 3 / 4.0 = 75.0% adherence (not 100% as log_count alone would suggest)
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=observed_days
    ) == 75.0

    # 2 logs spread over 11 calendar days (Sept 1 to Sept 11)
    logs_11d_span = [
        {"log_date": "2026-09-01", "workout_completed": True},
        {"log_date": "2026-09-11", "workout_completed": True},
    ]
    assert calculate_observed_days(logs_11d_span) == 11
    # expected = 4 * (11 / 7) = 6.2857 -> 2 / 6.2857 = 31.82%
    assert score_training_quality(
        completed_workouts=2, planned_workouts=4, window_days=11
    ) == 31.82


def test_score_training_quality_zero_completed_workouts():
    """5. Zero completed workouts: yields 0.0% adherence and preserves lower bound."""
    # Exactly 7 days
    assert score_training_quality(
        completed_workouts=0, planned_workouts=4, window_days=7
    ) == 0.0

    # Fewer than 7 days (3 days)
    assert score_training_quality(
        completed_workouts=0, planned_workouts=4, window_days=3
    ) == 0.0

    # More than 7 days (14 days)
    assert score_training_quality(
        completed_workouts=0, planned_workouts=4, window_days=14
    ) == 0.0


def test_score_training_quality_completed_exceeding_expected_clamped():
    """6. Completed workouts exceeding expected workouts: clamped strictly to 100.0."""
    # 3 daily logs in 3 days, 3 completed workouts, 4 planned/week -> expected 1.714 -> raw 175% -> clamped 100.0
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=3
    ) == 100.0

    # 6 workouts in 7 days with 4 planned -> raw 150% -> clamped to 100.0
    assert score_training_quality(
        completed_workouts=6, planned_workouts=4, window_days=7
    ) == 100.0

    # 10 workouts in 14 days with 4 planned/week (8 expected) -> raw 125% -> clamped to 100.0
    assert score_training_quality(
        completed_workouts=10, planned_workouts=4, window_days=14
    ) == 100.0


def test_score_training_quality_missing_workout_completed_data():
    """7. Missing workout_completed data: returns None when no training data exists."""
    # Completed workouts is None
    assert score_training_quality(
        completed_workouts=None, planned_workouts=4, window_days=7
    ) is None

    # Planned workouts is None
    assert score_training_quality(
        completed_workouts=3, planned_workouts=None, window_days=7
    ) is None

    # Both None
    assert score_training_quality(
        completed_workouts=None, planned_workouts=None, window_days=7
    ) is None

    # Missing workouts with energy rating present -> re-normalizes to energy alone
    assert score_training_quality(
        completed_workouts=None, planned_workouts=4, window_days=7, average_energy_rating=7.5
    ) == 75.0

    # Invalid window_days (<= 0) cannot evaluate expected workouts
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=0
    ) is None
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=-3
    ) is None


def test_score_training_quality_energy_only():
    """8. Energy-only training quality: re-normalizes energy weight to 1.0."""
    # Energy rating 10.0 -> 100.0
    assert score_training_quality(average_energy_rating=10.0) == 100.0

    # Energy rating 8.5 -> 85.0
    assert score_training_quality(average_energy_rating=8.5) == 85.0

    # Energy rating 5.0 -> 50.0
    assert score_training_quality(average_energy_rating=5.0) == 50.0

    # Missing completed workouts with energy present
    assert score_training_quality(
        completed_workouts=None, planned_workouts=4, window_days=7, average_energy_rating=8.0
    ) == 80.0


def test_score_training_quality_both_adherence_and_energy():
    """9. Both adherence + energy: weighted 60% adherence, 40% energy rating."""
    # 75.0 adherence (3/4 in 7 days), 8.0 energy (80.0) -> (75.0 * 0.60) + (80.0 * 0.40) = 45.0 + 32.0 = 77.0
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=7, average_energy_rating=8.0
    ) == 77.0

    # 58.333 adherence (1/1.714 in 3 days), 7.0 energy (70.0) -> (58.333 * 0.60) + (70.0 * 0.40) = 35.0 + 28.0 = 63.0
    assert score_training_quality(
        completed_workouts=1, planned_workouts=4, window_days=3, average_energy_rating=7.0
    ) == 63.0

    # 100.0 adherence (3/1.714 in 3 days clamped), 8.0 energy (80.0) -> (100.0 * 0.60) + (80.0 * 0.40) = 60.0 + 32.0 = 92.0
    assert score_training_quality(
        completed_workouts=3, planned_workouts=4, window_days=3, average_energy_rating=8.0
    ) == 92.0

    # 0.0 adherence (0 workouts in 7 days), 8.0 energy (80.0) -> (0.0 * 0.60) + (80.0 * 0.40) = 32.0
    assert score_training_quality(
        completed_workouts=0, planned_workouts=4, window_days=7, average_energy_rating=8.0
    ) == 32.0
