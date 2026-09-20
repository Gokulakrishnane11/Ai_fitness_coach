"""
Unit tests for the centralized adaptation engine feature-extraction layer.

Tests pure functions in apps.api.app.engine.adaptation:
- calculate_weight_change
- calculate_weight_change_percent
- calculate_adherence_percent
- calculate_plateau_probability
- build_progress_features
"""

import pytest
from pydantic import ValidationError
from app.engine.adaptation import (
    calculate_weight_change,
    calculate_weight_change_percent,
    calculate_adherence_percent,
    calculate_plateau_probability,
    build_progress_features,
    build_adaptation_input,
    AdaptationInput,
)


# ---------------------------------------------------------------------------
# calculate_weight_change tests
# ---------------------------------------------------------------------------

def test_calculate_weight_change_positive():
    """Verify weight gain produces a positive delta."""
    assert calculate_weight_change(70.0, 72.5) == 2.5


def test_calculate_weight_change_negative():
    """Verify weight loss produces a negative delta."""
    assert calculate_weight_change(85.0, 83.2) == -1.8


def test_calculate_weight_change_zero():
    """Verify stable weight produces zero delta."""
    assert calculate_weight_change(75.0, 75.0) == 0.0


def test_calculate_weight_change_missing_inputs():
    """Verify missing inputs return None."""
    assert calculate_weight_change(None, 70.0) is None
    assert calculate_weight_change(70.0, None) is None
    assert calculate_weight_change(None, None) is None


# ---------------------------------------------------------------------------
# calculate_weight_change_percent tests
# ---------------------------------------------------------------------------

def test_calculate_weight_change_percent_positive():
    """Verify positive percentage change calculation."""
    assert calculate_weight_change_percent(100.0, 105.0) == 5.0
    assert calculate_weight_change_percent(80.0, 82.0) == 2.5


def test_calculate_weight_change_percent_negative():
    """Verify negative percentage change calculation."""
    assert calculate_weight_change_percent(100.0, 95.0) == -5.0
    assert calculate_weight_change_percent(80.0, 76.0) == -5.0


def test_calculate_weight_change_percent_zero():
    """Verify zero percentage change calculation."""
    assert calculate_weight_change_percent(80.0, 80.0) == 0.0


def test_calculate_weight_change_percent_missing_inputs():
    """Verify missing inputs return None."""
    assert calculate_weight_change_percent(None, 80.0) is None
    assert calculate_weight_change_percent(80.0, None) is None
    assert calculate_weight_change_percent(None, None) is None


def test_calculate_weight_change_percent_invalid_start_weight():
    """Verify start weight <= 0 returns None to avoid ZeroDivision / invalid physics."""
    assert calculate_weight_change_percent(0.0, 5.0) is None
    assert calculate_weight_change_percent(-70.0, -68.0) is None


# ---------------------------------------------------------------------------
# calculate_adherence_percent tests
# ---------------------------------------------------------------------------

def test_calculate_adherence_percent_full_adherence():
    """Verify 100% adherence across workout and nutrition data."""
    result = calculate_adherence_percent(
        completed_workouts=4,
        planned_workouts=4,
        days_with_calorie_data=7,
        days_with_target_calories=7,
    )
    assert result == 100.0


def test_calculate_adherence_percent_partial_adherence():
    """Verify arithmetic mean of both categories."""
    # Workout = 3/4 = 75.0%, Nutrition = 5/7 = 71.42857%
    # Mean = (75.0 + 71.42857) / 2 = 73.21428% -> 73.21%
    result = calculate_adherence_percent(
        completed_workouts=3,
        planned_workouts=4,
        days_with_calorie_data=5,
        days_with_target_calories=7,
    )
    assert result == 73.21

    # Workout = 2/4 = 50.0%, Nutrition = 7/7 = 100.0% -> 75.0%
    result2 = calculate_adherence_percent(
        completed_workouts=2,
        planned_workouts=4,
        days_with_calorie_data=7,
        days_with_target_calories=7,
    )
    assert result2 == 75.0


def test_calculate_adherence_percent_only_workout_data():
    """Verify return when only workout data is available."""
    result = calculate_adherence_percent(
        completed_workouts=3,
        planned_workouts=4,
        days_with_calorie_data=None,
        days_with_target_calories=None,
    )
    assert result == 75.0

    # 0% workout adherence
    result_zero = calculate_adherence_percent(
        completed_workouts=0,
        planned_workouts=4,
        days_with_calorie_data=None,
        days_with_target_calories=None,
    )
    assert result_zero == 0.0

    # Overachievement clamped to 100%
    result_over = calculate_adherence_percent(
        completed_workouts=6,
        planned_workouts=4,
        days_with_calorie_data=None,
        days_with_target_calories=None,
    )
    assert result_over == 100.0


def test_calculate_adherence_percent_only_nutrition_data():
    """Verify return when only nutrition data is available."""
    # 6/7 = 85.714% -> 85.71%
    result = calculate_adherence_percent(
        completed_workouts=None,
        planned_workouts=None,
        days_with_calorie_data=6,
        days_with_target_calories=7,
    )
    assert result == 85.71

    # 0% nutrition adherence
    result_zero = calculate_adherence_percent(
        completed_workouts=None,
        planned_workouts=None,
        days_with_calorie_data=0,
        days_with_target_calories=7,
    )
    assert result_zero == 0.0

    # Overachievement clamped to 100%
    result_over = calculate_adherence_percent(
        completed_workouts=None,
        planned_workouts=None,
        days_with_calorie_data=10,
        days_with_target_calories=7,
    )
    assert result_over == 100.0


def test_calculate_adherence_percent_no_adherence_data():
    """Verify None returned when neither category has sufficient data."""
    assert calculate_adherence_percent(None, None, None, None) is None
    # Missing targets / denominator <= 0
    assert calculate_adherence_percent(3, 0, 5, 0) is None
    assert calculate_adherence_percent(3, None, 5, None) is None
    assert calculate_adherence_percent(None, 4, None, 7) is None


# ---------------------------------------------------------------------------
# calculate_plateau_probability tests
# ---------------------------------------------------------------------------

def test_calculate_plateau_probability_fat_loss_plateau():
    """Verify fat_loss returns 80 when |14d| < 0.2 and |28d| < 0.4."""
    # Flat / minimal changes
    assert calculate_plateau_probability(0.1, 0.3, "fat_loss") == 80.0
    assert calculate_plateau_probability(-0.15, -0.35, "fat_loss") == 80.0
    assert calculate_plateau_probability(0.0, 0.0, "fat_loss") == 80.0
    # Case insensitivity
    assert calculate_plateau_probability(0.1, 0.2, "FAT_LOSS") == 80.0


def test_calculate_plateau_probability_fat_loss_active_progress():
    """Verify fat_loss returns 0 when progress exceeds plateau thresholds."""
    # Active weight loss
    assert calculate_plateau_probability(-0.5, -1.2, "fat_loss") == 0.0
    # 14d flat but 28d moving
    assert calculate_plateau_probability(0.1, -0.8, "fat_loss") == 0.0
    # 28d flat but 14d moving
    assert calculate_plateau_probability(-0.4, 0.2, "fat_loss") == 0.0
    # Boundary tests (< 0.2, < 0.4)
    assert calculate_plateau_probability(0.2, 0.3, "fat_loss") == 0.0
    assert calculate_plateau_probability(0.1, 0.4, "fat_loss") == 0.0


def test_calculate_plateau_probability_muscle_gain_and_weight_gain():
    """Verify weight_gain and muscle_gain return 80 when |14d| < 0.1 and |28d| < 0.2."""
    for goal in ["muscle_gain", "weight_gain", "MUSCLE_GAIN", "WEIGHT_GAIN"]:
        # Stalled gain
        assert calculate_plateau_probability(0.05, 0.15, goal) == 80.0
        assert calculate_plateau_probability(-0.08, 0.10, goal) == 80.0
        assert calculate_plateau_probability(0.0, 0.0, goal) == 80.0

        # Active gain (> threshold)
        assert calculate_plateau_probability(0.3, 0.8, goal) == 0.0
        assert calculate_plateau_probability(0.1, 0.15, goal) == 0.0
        assert calculate_plateau_probability(0.05, 0.2, goal) == 0.0


def test_calculate_plateau_probability_recomposition():
    """Verify recomposition always returns None (weight alone is insufficient)."""
    assert calculate_plateau_probability(0.0, 0.0, "recomposition") is None
    assert calculate_plateau_probability(0.1, 0.2, "recomposition") is None
    assert calculate_plateau_probability(1.5, 3.0, "recomposition") is None
    assert calculate_plateau_probability(0.0, 0.0, "RECOMPOSITION") is None


def test_calculate_plateau_probability_insufficient_history():
    """Verify None returned when either 14d or 28d metric is missing."""
    assert calculate_plateau_probability(None, 0.2, "fat_loss") is None
    assert calculate_plateau_probability(0.1, None, "fat_loss") is None
    assert calculate_plateau_probability(None, None, "fat_loss") is None
    # Unknown goal
    assert calculate_plateau_probability(0.0, 0.0, "unknown_goal") is None


# ---------------------------------------------------------------------------
# build_progress_features tests
# ---------------------------------------------------------------------------

def test_build_progress_features_structure_and_values():
    """Verify dictionary keys and calculated plateau_probability."""
    features = build_progress_features(
        weight_change_7d_kg=-0.2,
        weight_change_14d_kg=-0.1,
        weight_change_28d_kg=-0.3,
        goal_type="fat_loss",
    )

    assert set(features.keys()) == {
        "weight_change_kg_7d",
        "weight_change_kg_14d",
        "weight_change_kg_28d",
        "plateau_probability",
    }
    assert features["weight_change_kg_7d"] == -0.2
    assert features["weight_change_kg_14d"] == -0.1
    assert features["weight_change_kg_28d"] == -0.3
    assert features["plateau_probability"] == 80.0


def test_build_progress_features_missing_history():
    """Verify build_progress_features handles missing inputs safely."""
    features = build_progress_features(
        weight_change_7d_kg=-0.2,
        weight_change_14d_kg=None,
        weight_change_28d_kg=None,
        goal_type="fat_loss",
    )
    assert features["weight_change_kg_7d"] == -0.2
    assert features["weight_change_kg_14d"] is None
    assert features["weight_change_kg_28d"] is None
    assert features["plateau_probability"] is None


# ---------------------------------------------------------------------------
# Deterministic repeated calls test
# ---------------------------------------------------------------------------

def test_deterministic_repeated_calls():
    """Verify pure functions return identical results on consecutive invocations."""
    for _ in range(5):
        assert calculate_weight_change(80.5, 79.2) == -1.3
        assert calculate_weight_change_percent(80.0, 78.0) == -2.5
        assert calculate_adherence_percent(4, 4, 6, 7) == 92.86
        assert calculate_plateau_probability(0.05, 0.1, "muscle_gain") == 80.0
        assert build_progress_features(-0.5, -1.0, -2.0, "fat_loss") == {
            "weight_change_kg_7d": -0.5,
            "weight_change_kg_14d": -1.0,
            "weight_change_kg_28d": -2.0,
            "plateau_probability": 0.0,
        }


# ---------------------------------------------------------------------------
# build_adaptation_input tests
# ---------------------------------------------------------------------------

def test_build_adaptation_input_valid_creation():
    """Verify build_adaptation_input produces a valid AdaptationInput instance."""
    input_data = build_adaptation_input(
        current_weight_kg=80.0,
        target_weight_kg=72.0,
        goal_type="fat_loss",
        target_calories=2000.0,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=65.0,
        workout_days_per_week=4,
        experience_level="intermediate",
        log_count=14,
        adherence_percent=85.0,
        recovery_score=80.0,
        stress_score=30.0,
        sleep_quality=75.0,
        injury_risk=10.0,
        weight_change_kg_7d=-0.3,
        weight_change_kg_14d=-0.6,
        weight_change_kg_28d=-1.5,
        latest_journal_summary="Energy was consistent all week.",
        latest_journal_sentiment="consistent",
    )
    assert isinstance(input_data, AdaptationInput)
    assert input_data.current_weight_kg == 80.0
    assert input_data.target_weight_kg == 72.0
    assert input_data.goal_type == "fat_loss"
    assert input_data.target_calories == 2000.0
    assert input_data.workout_days_per_week == 4
    assert input_data.experience_level == "intermediate"
    assert input_data.log_count == 14
    assert input_data.adherence_percent == 85.0
    assert input_data.recovery_score == 80.0
    assert input_data.stress_score == 30.0
    assert input_data.sleep_quality == 75.0
    assert input_data.injury_risk == 10.0
    assert input_data.weight_change_kg_7d == -0.3
    assert input_data.weight_change_kg_14d == -0.6
    assert input_data.weight_change_kg_28d == -1.5
    assert input_data.latest_journal_summary == "Energy was consistent all week."
    assert input_data.latest_journal_sentiment == "consistent"
    # Plateaus: -0.6 (abs >= 0.2), so plateau_probability is derived as 0.0
    assert input_data.plateau_probability == 0.0


def test_build_adaptation_input_fat_loss_plateau_populated():
    """Verify fat-loss plateau probability is automatically derived and populated."""
    # Stalled (< 0.2 and < 0.4)
    stalled = build_adaptation_input(
        current_weight_kg=85.0,
        target_weight_kg=75.0,
        goal_type="fat_loss",
        target_calories=2000.0,
        target_protein_g=160.0,
        target_carbs_g=180.0,
        target_fat_g=60.0,
        workout_days_per_week=4,
        experience_level="intermediate",
        log_count=28,
        weight_change_kg_14d=-0.1,
        weight_change_kg_28d=-0.2,
    )
    assert stalled.plateau_probability == 80.0

    # Progressing (abs(14d) >= 0.2 or abs(28d) >= 0.4)
    progressing = build_adaptation_input(
        current_weight_kg=85.0,
        target_weight_kg=75.0,
        goal_type="fat_loss",
        target_calories=2000.0,
        target_protein_g=160.0,
        target_carbs_g=180.0,
        target_fat_g=60.0,
        workout_days_per_week=4,
        experience_level="intermediate",
        log_count=28,
        weight_change_kg_14d=-0.5,
        weight_change_kg_28d=-1.2,
    )
    assert progressing.plateau_probability == 0.0


def test_build_adaptation_input_muscle_and_weight_gain_plateau():
    """Verify muscle_gain and weight_gain plateau probabilities are automatically populated."""
    for goal in ["muscle_gain", "weight_gain"]:
        stalled = build_adaptation_input(
            current_weight_kg=70.0,
            target_weight_kg=78.0,
            goal_type=goal,
            target_calories=2800.0,
            target_protein_g=170.0,
            target_carbs_g=350.0,
            target_fat_g=80.0,
            workout_days_per_week=5,
            experience_level="advanced",
            log_count=30,
            weight_change_kg_14d=0.05,
            weight_change_kg_28d=0.15,
        )
        assert stalled.plateau_probability == 80.0

        progressing = build_adaptation_input(
            current_weight_kg=70.0,
            target_weight_kg=78.0,
            goal_type=goal,
            target_calories=2800.0,
            target_protein_g=170.0,
            target_carbs_g=350.0,
            target_fat_g=80.0,
            workout_days_per_week=5,
            experience_level="advanced",
            log_count=30,
            weight_change_kg_14d=0.25,
            weight_change_kg_28d=0.60,
        )
        assert progressing.plateau_probability == 0.0


def test_build_adaptation_input_recomposition_plateau_remains_none():
    """Verify recomposition plateau probability remains None regardless of weight trajectory."""
    result = build_adaptation_input(
        current_weight_kg=75.0,
        target_weight_kg=75.0,
        goal_type="recomposition",
        target_calories=2200.0,
        target_protein_g=160.0,
        target_carbs_g=220.0,
        target_fat_g=70.0,
        workout_days_per_week=4,
        experience_level="intermediate",
        log_count=28,
        weight_change_kg_14d=0.0,
        weight_change_kg_28d=0.0,
    )
    assert result.plateau_probability is None


def test_build_adaptation_input_insufficient_progress_history_plateau_none():
    """Verify insufficient progress history keeps plateau_probability as None."""
    base_kwargs = {
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_calories": 2000.0,
        "target_protein_g": 150.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 3,
        "experience_level": "beginner",
        "log_count": 5,
    }
    # Both 14d and 28d missing
    res1 = build_adaptation_input(**base_kwargs)
    assert res1.plateau_probability is None

    # Only 14d present
    res2 = build_adaptation_input(**base_kwargs, weight_change_kg_14d=0.1)
    assert res2.plateau_probability is None

    # Only 28d present
    res3 = build_adaptation_input(**base_kwargs, weight_change_kg_28d=0.2)
    assert res3.plateau_probability is None


def test_build_adaptation_input_optional_journal_fields():
    """Verify optional journal fields remain intact when provided and default to None when omitted."""
    base_kwargs = {
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_calories": 2000.0,
        "target_protein_g": 150.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 3,
        "experience_level": "beginner",
        "log_count": 5,
    }
    # Omitted
    res_none = build_adaptation_input(**base_kwargs)
    assert res_none.latest_journal_summary is None
    assert res_none.latest_journal_sentiment is None

    # Provided
    res_provided = build_adaptation_input(
        **base_kwargs,
        latest_journal_summary="Fatigue accumulating.",
        latest_journal_sentiment="fatigued",
    )
    assert res_provided.latest_journal_summary == "Fatigue accumulating."
    assert res_provided.latest_journal_sentiment == "fatigued"


def test_build_adaptation_input_optional_behavioral_scores():
    """Verify optional behavioral scores remain intact when provided and default to None when omitted."""
    base_kwargs = {
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_calories": 2000.0,
        "target_protein_g": 150.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 3,
        "experience_level": "beginner",
        "log_count": 5,
    }
    res_none = build_adaptation_input(**base_kwargs)
    assert res_none.adherence_percent is None
    assert res_none.recovery_score is None
    assert res_none.stress_score is None
    assert res_none.sleep_quality is None
    assert res_none.injury_risk is None

    res_scores = build_adaptation_input(
        **base_kwargs,
        adherence_percent=92.5,
        recovery_score=85.0,
        stress_score=25.0,
        sleep_quality=90.0,
        injury_risk=15.0,
    )
    assert res_scores.adherence_percent == 92.5
    assert res_scores.recovery_score == 85.0
    assert res_scores.stress_score == 25.0
    assert res_scores.sleep_quality == 90.0
    assert res_scores.injury_risk == 15.0


def test_build_adaptation_input_invalid_profile_rejected():
    """Verify invalid profile values are rejected by AdaptationInput validation."""
    valid_kwargs = {
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_calories": 2000.0,
        "target_protein_g": 150.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 3,
        "experience_level": "beginner",
        "log_count": 5,
    }

    # Invalid weight <= 0
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "current_weight_kg": 0.0})

    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "current_weight_kg": -10.0})

    # Invalid target weight <= 0
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "target_weight_kg": -5.0})

    # Invalid goal type
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "goal_type": "marathon_training"})

    # Invalid calories <= 0
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "target_calories": 0.0})

    # Invalid workout days (< 1 or > 7)
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "workout_days_per_week": 0})

    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "workout_days_per_week": 8})

    # Invalid experience level
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "experience_level": "expert"})

    # Invalid log count (< 0)
    with pytest.raises(ValidationError):
        build_adaptation_input(**{**valid_kwargs, "log_count": -1})


def test_build_adaptation_input_deterministic_repeated_calls():
    """Verify repeated calls with identical inputs produce identical validated models."""
    kwargs = {
        "current_weight_kg": 78.0,
        "target_weight_kg": 72.0,
        "goal_type": "fat_loss",
        "target_calories": 1950.0,
        "target_protein_g": 155.0,
        "target_carbs_g": 190.0,
        "target_fat_g": 55.0,
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "log_count": 14,
        "weight_change_kg_14d": -0.1,
        "weight_change_kg_28d": -0.3,
    }
    first = build_adaptation_input(**kwargs)
    for _ in range(5):
        subsequent = build_adaptation_input(**kwargs)
        assert subsequent.model_dump() == first.model_dump()

