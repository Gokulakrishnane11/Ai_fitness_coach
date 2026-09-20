"""
Unit Test Suite for Pure Daily-Log Aggregation Layer.

Tests aggregate_daily_logs in apps.api.app.engine.adaptation:
- empty logs
- single log
- multiple logs out of chronological order
- latest weight selection
- 7-day weight change
- 14-day weight change
- 28-day weight change
- insufficient weight history returns None
- null weights ignored
- workout completion counting
- calorie-data counting
- target-calorie count remains 0
- energy average
- missing energy values
- input list is not mutated
- malformed/missing log_date handling
- deterministic repeated calls
"""

import copy
import pytest
from app.engine.adaptation import aggregate_daily_logs


def test_aggregate_daily_logs_empty_logs():
    """Verify safe empty dictionary returned for empty input."""
    result = aggregate_daily_logs([])
    assert result == {
        "log_count": 0,
        "latest_weight_kg": None,
        "weight_change_kg_7d": None,
        "weight_change_kg_14d": None,
        "weight_change_kg_28d": None,
        "completed_workouts": 0,
        "days_with_calorie_data": 0,
        "days_with_target_calories": 0,
        "average_energy_rating": None,
    }


def test_aggregate_daily_logs_single_log():
    """Verify aggregation on a single daily log."""
    logs = [
        {
            "log_date": "2026-09-01",
            "weight_kg": 80.5,
            "calories_consumed": 2100,
            "workout_completed": True,
            "energy_rating": 8,
        }
    ]
    result = aggregate_daily_logs(logs)
    assert result["log_count"] == 1
    assert result["latest_weight_kg"] == 80.5
    assert result["weight_change_kg_7d"] is None
    assert result["weight_change_kg_14d"] is None
    assert result["weight_change_kg_28d"] is None
    assert result["completed_workouts"] == 1
    assert result["days_with_calorie_data"] == 1
    assert result["days_with_target_calories"] == 0
    assert result["average_energy_rating"] == 8.0


def test_aggregate_daily_logs_multiple_logs_out_of_chronological_order():
    """Verify logs are sorted chronologically before calculating trends."""
    logs = [
        {"log_date": "2026-09-08", "weight_kg": 79.2},
        {"log_date": "2026-09-01", "weight_kg": 80.0},
    ]
    result = aggregate_daily_logs(logs)
    assert result["latest_weight_kg"] == 79.2
    assert result["weight_change_kg_7d"] == -0.8


def test_aggregate_daily_logs_latest_weight_selection():
    """Verify latest_weight_kg reflects the most recent non-null weight."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 81.0},
        {"log_date": "2026-09-05", "weight_kg": 80.2},
        {"log_date": "2026-09-06", "weight_kg": None, "workout_completed": True},
    ]
    result = aggregate_daily_logs(logs)
    assert result["latest_weight_kg"] == 80.2


def test_aggregate_daily_logs_7d_weight_change():
    """Verify 7-day weight change when weight exists on both sides of 7d window."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 80.0},
        {"log_date": "2026-09-04", "weight_kg": 79.6},
        {"log_date": "2026-09-08", "weight_kg": 79.3},
    ]
    result = aggregate_daily_logs(logs)
    assert result["latest_weight_kg"] == 79.3
    # 7 days before 2026-09-08 is 2026-09-01: 79.3 - 80.0 = -0.7
    assert result["weight_change_kg_7d"] == -0.7
    assert result["weight_change_kg_14d"] is None
    assert result["weight_change_kg_28d"] is None


def test_aggregate_daily_logs_14d_weight_change():
    """Verify 14-day weight change when weight exists on both sides of 14d window."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 80.0},
        {"log_date": "2026-09-08", "weight_kg": 79.0},
        {"log_date": "2026-09-15", "weight_kg": 78.4},
    ]
    result = aggregate_daily_logs(logs)
    assert result["latest_weight_kg"] == 78.4
    # 7 days before 2026-09-15 is 2026-09-08: 78.4 - 79.0 = -0.6
    assert result["weight_change_kg_7d"] == -0.6
    # 14 days before 2026-09-15 is 2026-09-01: 78.4 - 80.0 = -1.6
    assert result["weight_change_kg_14d"] == -1.6
    assert result["weight_change_kg_28d"] is None


def test_aggregate_daily_logs_28d_weight_change():
    """Verify 28-day weight change when weight exists on both sides of 28d window."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 85.0},
        {"log_date": "2026-09-15", "weight_kg": 83.5},
        {"log_date": "2026-09-29", "weight_kg": 82.0},
    ]
    result = aggregate_daily_logs(logs)
    assert result["latest_weight_kg"] == 82.0
    # 14 days before 2026-09-29 is 2026-09-15: 82.0 - 83.5 = -1.5
    assert result["weight_change_kg_14d"] == -1.5
    # 28 days before 2026-09-29 is 2026-09-01: 82.0 - 85.0 = -3.0
    assert result["weight_change_kg_28d"] == -3.0
    # No log on 2026-09-22 (7d prior)
    assert result["weight_change_kg_7d"] is None


def test_aggregate_daily_logs_insufficient_weight_history_returns_none():
    """Verify None returned when time span is shorter than window or missing boundary."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 80.0},
        {"log_date": "2026-09-04", "weight_kg": 79.8},
        {"log_date": "2026-09-05", "weight_kg": 79.5},
    ]
    result = aggregate_daily_logs(logs)
    assert result["weight_change_kg_7d"] is None
    assert result["weight_change_kg_14d"] is None
    assert result["weight_change_kg_28d"] is None


def test_aggregate_daily_logs_null_weights_ignored():
    """Verify logs with None weight do not cause errors and are ignored for weight metrics."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": None, "calories_consumed": 2000},
        {"log_date": "2026-09-02", "weight_kg": None, "workout_completed": True},
    ]
    result = aggregate_daily_logs(logs)
    assert result["latest_weight_kg"] is None
    assert result["weight_change_kg_7d"] is None
    assert result["weight_change_kg_14d"] is None
    assert result["weight_change_kg_28d"] is None
    assert result["completed_workouts"] == 1
    assert result["days_with_calorie_data"] == 1


def test_aggregate_daily_logs_workout_completion_counting():
    """Verify workout_completed == True is counted accurately."""
    logs = [
        {"log_date": "2026-09-01", "workout_completed": True},
        {"log_date": "2026-09-02", "workout_completed": False},
        {"log_date": "2026-09-03", "workout_completed": True},
        {"log_date": "2026-09-04"},  # missing key
        {"log_date": "2026-09-05", "workout_completed": True},
    ]
    result = aggregate_daily_logs(logs)
    assert result["completed_workouts"] == 3


def test_aggregate_daily_logs_calorie_data_counting():
    """Verify count of logs where calories_consumed is not None."""
    logs = [
        {"log_date": "2026-09-01", "calories_consumed": 2200},
        {"log_date": "2026-09-02", "calories_consumed": None},
        {"log_date": "2026-09-03", "calories_consumed": 1850},
        {"log_date": "2026-09-04"},  # missing key
    ]
    result = aggregate_daily_logs(logs)
    assert result["days_with_calorie_data"] == 2


def test_aggregate_daily_logs_target_calorie_count_remains_zero():
    """Verify days_with_target_calories is 0 since DailyLog does not persist target calories."""
    logs = [
        {"log_date": "2026-09-01", "calories_consumed": 2000},
        {"log_date": "2026-09-02", "calories_consumed": 2200},
        {"log_date": "2026-09-03", "calories_consumed": 1900},
    ]
    result = aggregate_daily_logs(logs)
    assert result["days_with_target_calories"] == 0


def test_aggregate_daily_logs_energy_average():
    """Verify arithmetic mean of non-null energy_rating values."""
    logs = [
        {"log_date": "2026-09-01", "energy_rating": 6},
        {"log_date": "2026-09-02", "energy_rating": 8},
        {"log_date": "2026-09-03", "energy_rating": 7},
    ]
    result = aggregate_daily_logs(logs)
    assert result["average_energy_rating"] == 7.0

    # Rounded to 2 decimals (7.67)
    logs2 = [
        {"log_date": "2026-09-01", "energy_rating": 7},
        {"log_date": "2026-09-02", "energy_rating": 8},
        {"log_date": "2026-09-03", "energy_rating": 8},
    ]
    result2 = aggregate_daily_logs(logs2)
    assert result2["average_energy_rating"] == 7.67


def test_aggregate_daily_logs_missing_energy_values():
    """Verify energy average ignores None values and returns None if all missing."""
    logs = [
        {"log_date": "2026-09-01", "energy_rating": 9},
        {"log_date": "2026-09-02", "energy_rating": None},
        {"log_date": "2026-09-03"},
    ]
    result = aggregate_daily_logs(logs)
    assert result["average_energy_rating"] == 9.0

    logs_none = [
        {"log_date": "2026-09-01", "energy_rating": None},
        {"log_date": "2026-09-02"},
    ]
    result_none = aggregate_daily_logs(logs_none)
    assert result_none["average_energy_rating"] is None


def test_aggregate_daily_logs_input_list_not_mutated():
    """Verify the original input list and inner dictionaries are not mutated."""
    original_logs = [
        {"log_date": "2026-09-08", "weight_kg": 78.5, "workout_completed": True},
        {"log_date": "2026-09-01", "weight_kg": 80.0, "workout_completed": False},
    ]
    frozen_copy = copy.deepcopy(original_logs)

    aggregate_daily_logs(original_logs)

    assert original_logs == frozen_copy
    # Verify first element is still the 09-08 log (not reordered in-place)
    assert original_logs[0]["log_date"] == "2026-09-08"


def test_aggregate_daily_logs_malformed_missing_log_date_handling():
    """Verify malformed records without log_date are ignored for trends and do not cause crashes."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 80.0},
        {"weight_kg": 85.0, "notes": "No date provided"},  # missing log_date
        {"log_date": "malformed-date", "weight_kg": 90.0},  # invalid date string
        {"log_date": None, "weight_kg": 88.0},  # None date
        {"log_date": "2026-09-08", "weight_kg": 79.0},
    ]
    result = aggregate_daily_logs(logs)
    # Trends should be calculated between valid dates 2026-09-01 and 2026-09-08
    assert result["latest_weight_kg"] == 79.0
    assert result["weight_change_kg_7d"] == -1.0
    assert result["log_count"] == 5


def test_aggregate_daily_logs_deterministic_repeated_calls():
    """Verify repeated invocations on the same dataset return identical outputs."""
    logs = [
        {"log_date": "2026-09-01", "weight_kg": 82.0, "calories_consumed": 2000, "workout_completed": True, "energy_rating": 7},
        {"log_date": "2026-09-08", "weight_kg": 81.2, "calories_consumed": 1950, "workout_completed": False, "energy_rating": 8},
        {"log_date": "2026-09-15", "weight_kg": 80.5, "calories_consumed": 2100, "workout_completed": True, "energy_rating": 9},
    ]
    first = aggregate_daily_logs(logs)
    for _ in range(5):
        subsequent = aggregate_daily_logs(logs)
        assert subsequent == first
