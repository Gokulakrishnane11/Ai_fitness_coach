"""
Unit Tests for Centralized Adaptation Engine Models (apps/api/app/engine/adaptation.py).
Tests:
- Valid default initialization
- Pydantic validation rejecting out-of-range values
- Valid enum / Literal validation
"""

import sys
import os
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.adaptation import (
    DietAdjustment,
    WorkoutAdjustment,
    AdaptationDecision,
    AdaptationInput,
)


# 1. Valid Defaults Tests
def test_diet_adjustment_defaults():
    adj = DietAdjustment()
    assert adj.calorie_delta == 0
    assert adj.protein_delta_g == 0.0
    assert adj.carb_delta_g == 0.0
    assert adj.fat_delta_g == 0.0


def test_workout_adjustment_defaults():
    adj = WorkoutAdjustment()
    assert adj.intensity == "maintain"
    assert adj.volume == "medium"
    assert adj.recovery_days == 0
    assert adj.cardio_minutes == 0
    assert adj.deload_recommended is False


def test_adaptation_decision_defaults():
    decision = AdaptationDecision(
        adherence_score=90,
        recovery_score=80,
        stress_score=20,
        sleep_quality=80,
        plateau_probability=10,
        injury_risk=5,
        readiness_factor=0.95,
    )
    assert decision.adherence_score == 90
    assert decision.recovery_score == 80
    assert decision.stress_score == 20
    assert decision.sleep_quality == 80
    assert decision.plateau_probability == 10
    assert decision.injury_risk == 5
    assert decision.readiness_factor == 0.95
    assert decision.plateau_detected is False
    assert decision.high_fatigue_flag is False
    assert isinstance(decision.diet_adjustment, DietAdjustment)
    assert decision.diet_adjustment.calorie_delta == 0
    assert isinstance(decision.workout_adjustment, WorkoutAdjustment)
    assert decision.workout_adjustment.intensity == "maintain"
    assert decision.actionable_recommendations == []
    assert decision.coaching_summary == ""


# 2. Pydantic Range Validation Tests - DietAdjustment
def test_diet_adjustment_valid_ranges():
    adj = DietAdjustment(
        calorie_delta=-300,
        protein_delta_g=30.0,
        carb_delta_g=-60.0,
        fat_delta_g=20.0,
    )
    assert adj.calorie_delta == -300
    assert adj.protein_delta_g == 30.0
    assert adj.carb_delta_g == -60.0
    assert adj.fat_delta_g == 20.0


@pytest.mark.parametrize(
    "field,invalid_val",
    [
        ("calorie_delta", 301),
        ("calorie_delta", -301),
        ("protein_delta_g", 30.1),
        ("protein_delta_g", -30.1),
        ("carb_delta_g", 60.1),
        ("carb_delta_g", -60.1),
        ("fat_delta_g", 20.1),
        ("fat_delta_g", -20.1),
    ],
)
def test_diet_adjustment_out_of_range_rejected(field, invalid_val):
    with pytest.raises(ValidationError):
        DietAdjustment(**{field: invalid_val})


# 3. Pydantic Range & Enum Validation Tests - WorkoutAdjustment
@pytest.mark.parametrize("intensity", ["reduce", "maintain", "increase"])
def test_workout_adjustment_valid_intensity(intensity):
    adj = WorkoutAdjustment(intensity=intensity)
    assert adj.intensity == intensity


@pytest.mark.parametrize("intensity", ["extreme", "max", "invalid", ""])
def test_workout_adjustment_invalid_intensity_rejected(intensity):
    with pytest.raises(ValidationError):
        WorkoutAdjustment(intensity=intensity)


@pytest.mark.parametrize("volume", ["low", "medium", "high"])
def test_workout_adjustment_valid_volume(volume):
    adj = WorkoutAdjustment(volume=volume)
    assert adj.volume == volume


@pytest.mark.parametrize("volume", ["ultra", "none", "heavy", ""])
def test_workout_adjustment_invalid_volume_rejected(volume):
    with pytest.raises(ValidationError):
        WorkoutAdjustment(volume=volume)


@pytest.mark.parametrize(
    "field,invalid_val",
    [
        ("recovery_days", -1),
        ("recovery_days", 8),
        ("cardio_minutes", -1),
        ("cardio_minutes", 121),
    ],
)
def test_workout_adjustment_out_of_range_rejected(field, invalid_val):
    with pytest.raises(ValidationError):
        WorkoutAdjustment(**{field: invalid_val})


# 4. Pydantic Range Validation Tests - AdaptationDecision
def test_adaptation_decision_valid_boundary_scores():
    decision_min = AdaptationDecision(
        adherence_score=0,
        recovery_score=0,
        stress_score=0,
        sleep_quality=0,
        plateau_probability=0,
        injury_risk=0,
        readiness_factor=0.45,
    )
    assert decision_min.adherence_score == 0
    assert decision_min.readiness_factor == 0.45

    decision_max = AdaptationDecision(
        adherence_score=100,
        recovery_score=100,
        stress_score=100,
        sleep_quality=100,
        plateau_probability=100,
        injury_risk=100,
        readiness_factor=1.12,
    )
    assert decision_max.adherence_score == 100
    assert decision_max.readiness_factor == 1.12


@pytest.mark.parametrize(
    "field,invalid_val",
    [
        ("adherence_score", -1),
        ("adherence_score", 101),
        ("recovery_score", -1),
        ("recovery_score", 101),
        ("stress_score", -1),
        ("stress_score", 101),
        ("sleep_quality", -1),
        ("sleep_quality", 101),
        ("plateau_probability", -1),
        ("plateau_probability", 101),
        ("injury_risk", -1),
        ("injury_risk", 101),
        ("readiness_factor", 0.44),
        ("readiness_factor", 1.13),
    ],
)
def test_adaptation_decision_out_of_range_rejected(field, invalid_val):
    base_kwargs = {
        "adherence_score": 90,
        "recovery_score": 80,
        "stress_score": 20,
        "sleep_quality": 80,
        "plateau_probability": 10,
        "injury_risk": 5,
        "readiness_factor": 1.0,
    }
    base_kwargs[field] = invalid_val
    with pytest.raises(ValidationError):
        AdaptationDecision(**base_kwargs)


# ---------------------------------------------------------------------------
# 5. AdaptationInput Model Tests
# ---------------------------------------------------------------------------

def test_adaptation_input_valid_construction():
    payload = {
        "current_weight_kg": 82.5,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_calories": 2100.0,
        "target_protein_g": 160.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 65.0,
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "log_count": 7,
        "adherence_percent": 85.0,
        "recovery_score": 75.0,
        "stress_score": 30.0,
        "sleep_quality": 80.0,
        "injury_risk": 10.0,
        "weight_change_kg_7d": -0.6,
        "weight_change_kg_14d": -1.2,
        "weight_change_kg_28d": -2.4,
        "latest_journal_summary": "Felt good energy during workouts.",
        "latest_journal_sentiment": "motivated",
    }
    input_data = AdaptationInput(**payload)
    assert input_data.current_weight_kg == 82.5
    assert input_data.target_weight_kg == 75.0
    assert input_data.goal_type == "fat_loss"
    assert input_data.target_calories == 2100.0
    assert input_data.workout_days_per_week == 4
    assert input_data.experience_level == "intermediate"
    assert input_data.log_count == 7
    assert input_data.weight_change_kg_7d == -0.6
    assert input_data.latest_journal_sentiment == "motivated"


@pytest.mark.parametrize(
    "missing_field",
    [
        "current_weight_kg",
        "target_weight_kg",
        "goal_type",
        "target_calories",
        "target_protein_g",
        "target_carbs_g",
        "target_fat_g",
        "workout_days_per_week",
        "experience_level",
        "log_count",
    ],
)
def test_adaptation_input_required_fields(missing_field):
    base_kwargs = {
        "current_weight_kg": 80.0,
        "target_weight_kg": 75.0,
        "goal_type": "recomposition",
        "target_calories": 2000.0,
        "target_protein_g": 150.0,
        "target_carbs_g": 200.0,
        "target_fat_g": 60.0,
        "workout_days_per_week": 3,
        "experience_level": "beginner",
        "log_count": 0,
    }
    del base_kwargs[missing_field]
    with pytest.raises(ValidationError):
        AdaptationInput(**base_kwargs)


def test_adaptation_input_optional_fields_accept_none():
    minimal = AdaptationInput(
        current_weight_kg=80.0,
        target_weight_kg=75.0,
        goal_type="recomposition",
        target_calories=2000.0,
        target_protein_g=150.0,
        target_carbs_g=200.0,
        target_fat_g=60.0,
        workout_days_per_week=3,
        experience_level="beginner",
        log_count=0,
    )
    assert minimal.adherence_percent is None
    assert minimal.recovery_score is None
    assert minimal.stress_score is None
    assert minimal.sleep_quality is None
    assert minimal.injury_risk is None
    assert minimal.weight_change_kg_7d is None
    assert minimal.weight_change_kg_14d is None
    assert minimal.weight_change_kg_28d is None
    assert minimal.latest_journal_summary is None
    assert minimal.latest_journal_sentiment is None
    assert minimal.nutrition_score is None
    assert minimal.training_quality is None


@pytest.mark.parametrize("goal", ["fat_loss", "muscle_gain", "weight_gain", "recomposition"])
def test_adaptation_input_valid_goals(goal):
    inp = AdaptationInput(
        current_weight_kg=70.0,
        target_weight_kg=65.0,
        goal_type=goal,
        target_calories=1800.0,
        target_protein_g=140.0,
        target_carbs_g=180.0,
        target_fat_g=50.0,
        workout_days_per_week=3,
        experience_level="beginner",
        log_count=0,
    )
    assert inp.goal_type == goal


@pytest.mark.parametrize("invalid_goal", ["cut", "bulk", "tone", "invalid", ""])
def test_adaptation_input_invalid_goal_rejected(invalid_goal):
    with pytest.raises(ValidationError):
        AdaptationInput(
            current_weight_kg=70.0,
            target_weight_kg=65.0,
            goal_type=invalid_goal,
            target_calories=1800.0,
            target_protein_g=140.0,
            target_carbs_g=180.0,
            target_fat_g=50.0,
            workout_days_per_week=3,
            experience_level="beginner",
            log_count=0,
        )


@pytest.mark.parametrize("exp", ["beginner", "intermediate", "advanced"])
def test_adaptation_input_valid_experience_levels(exp):
    inp = AdaptationInput(
        current_weight_kg=70.0,
        target_weight_kg=65.0,
        goal_type="fat_loss",
        target_calories=1800.0,
        target_protein_g=140.0,
        target_carbs_g=180.0,
        target_fat_g=50.0,
        workout_days_per_week=3,
        experience_level=exp,
        log_count=0,
    )
    assert inp.experience_level == exp


@pytest.mark.parametrize("invalid_exp", ["novice", "pro", "elite", "invalid", ""])
def test_adaptation_input_invalid_experience_level_rejected(invalid_exp):
    with pytest.raises(ValidationError):
        AdaptationInput(
            current_weight_kg=70.0,
            target_weight_kg=65.0,
            goal_type="fat_loss",
            target_calories=1800.0,
            target_protein_g=140.0,
            target_carbs_g=180.0,
            target_fat_g=50.0,
            workout_days_per_week=3,
            experience_level=invalid_exp,
            log_count=0,
        )


@pytest.mark.parametrize("days", [1, 2, 4, 7])
def test_adaptation_input_valid_workout_days(days):
    inp = AdaptationInput(
        current_weight_kg=70.0,
        target_weight_kg=65.0,
        goal_type="fat_loss",
        target_calories=1800.0,
        target_protein_g=140.0,
        target_carbs_g=180.0,
        target_fat_g=50.0,
        workout_days_per_week=days,
        experience_level="beginner",
        log_count=0,
    )
    assert inp.workout_days_per_week == days


@pytest.mark.parametrize("invalid_days", [0, -1, 8, 14])
def test_adaptation_input_invalid_workout_days_rejected(invalid_days):
    with pytest.raises(ValidationError):
        AdaptationInput(
            current_weight_kg=70.0,
            target_weight_kg=65.0,
            goal_type="fat_loss",
            target_calories=1800.0,
            target_protein_g=140.0,
            target_carbs_g=180.0,
            target_fat_g=50.0,
            workout_days_per_week=invalid_days,
            experience_level="beginner",
            log_count=0,
        )


@pytest.mark.parametrize(
    "field,invalid_val",
    [
        ("current_weight_kg", 0.0),
        ("current_weight_kg", -5.0),
        ("target_weight_kg", 0.0),
        ("target_weight_kg", -10.0),
        ("target_calories", 0.0),
        ("target_calories", -500.0),
        ("target_protein_g", -1.0),
        ("target_carbs_g", -1.0),
        ("target_fat_g", -1.0),
    ],
)
def test_adaptation_input_negative_or_zero_values_rejected(field, invalid_val):
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
        "log_count": 0,
    }
    base_kwargs[field] = invalid_val
    with pytest.raises(ValidationError):
        AdaptationInput(**base_kwargs)


def test_adaptation_input_negative_log_count_rejected():
    with pytest.raises(ValidationError):
        AdaptationInput(
            current_weight_kg=80.0,
            target_weight_kg=75.0,
            goal_type="fat_loss",
            target_calories=2000.0,
            target_protein_g=150.0,
            target_carbs_g=200.0,
            target_fat_g=60.0,
            workout_days_per_week=3,
            experience_level="beginner",
            log_count=-1,
        )


@pytest.mark.parametrize("invalid_score", [-5.0, 105.0])
def test_adaptation_input_nutrition_score_bounds_rejected(invalid_score):
    with pytest.raises(ValidationError):
        AdaptationInput(
            current_weight_kg=80.0,
            target_weight_kg=75.0,
            goal_type="fat_loss",
            target_calories=2000.0,
            target_protein_g=150.0,
            target_carbs_g=200.0,
            target_fat_g=60.0,
            workout_days_per_week=3,
            experience_level="beginner",
            log_count=5,
            nutrition_score=invalid_score,
        )


@pytest.mark.parametrize("invalid_score", [-5.0, 105.0])
def test_adaptation_input_training_quality_bounds_rejected(invalid_score):
    with pytest.raises(ValidationError):
        AdaptationInput(
            current_weight_kg=80.0,
            target_weight_kg=75.0,
            goal_type="fat_loss",
            target_calories=2000.0,
            target_protein_g=150.0,
            target_carbs_g=200.0,
            target_fat_g=60.0,
            workout_days_per_week=3,
            experience_level="beginner",
            log_count=5,
            training_quality=invalid_score,
        )

