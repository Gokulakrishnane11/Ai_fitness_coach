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
