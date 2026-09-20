"""
Unit Test Suite for Read-Only Adaptation Data Collector Layer.

Verifies:
- Profile found + logs found returns expected dict
- Profile found + no logs returns expected dict with empty logs list
- Missing profile raises ValueError explicitly (no fake/default profile)
- Database/repository exceptions propagate to caller
- Correct user_id is passed to both repositories
- No repository write methods are called (strictly read-only)
- JWT token forwarding when supplied
"""

import pytest
from unittest.mock import MagicMock
from app.engine.adaptation import collect_adaptation_data


def test_collect_adaptation_data_profile_found_and_logs_found():
    """Verify raw profile and daily logs are returned when both exist."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    sample_profile = {
        "id": "user_001",
        "first_name": "Alex",
        "weight_kg": 82.5,
        "target_weight_kg": 75.0,
        "goal_type": "fat_loss",
        "target_metrics": {"tdee": 2400, "target_calories": 1900},
    }
    sample_logs = [
        {
            "id": "user_001_2026-09-18",
            "user_id": "user_001",
            "log_date": "2026-09-18",
            "weight_kg": 82.2,
            "calories_consumed": 1880,
            "workout_completed": True,
        },
        {
            "id": "user_001_2026-09-17",
            "user_id": "user_001",
            "log_date": "2026-09-17",
            "weight_kg": 82.5,
            "calories_consumed": 1920,
            "workout_completed": True,
        },
    ]

    mock_profile_repo.get_profile.return_value = sample_profile
    mock_log_repo.get_logs.return_value = sample_logs

    data = collect_adaptation_data(
        user_id="user_001",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
    )

    assert set(data.keys()) == {"profile", "daily_logs"}
    assert data["profile"] == sample_profile
    assert data["daily_logs"] == sample_logs
    assert len(data["daily_logs"]) == 2


def test_collect_adaptation_data_profile_found_and_no_logs():
    """Verify empty list is returned for daily_logs when user has no logged days."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    sample_profile = {
        "id": "user_new",
        "first_name": "Jordan",
        "weight_kg": 70.0,
        "goal_type": "muscle_gain",
    }
    mock_profile_repo.get_profile.return_value = sample_profile
    mock_log_repo.get_logs.return_value = []

    data = collect_adaptation_data(
        user_id="user_new",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
    )

    assert data["profile"] == sample_profile
    assert data["daily_logs"] == []


def test_collect_adaptation_data_profile_missing():
    """Verify missing profile explicitly raises ValueError and does not invent fake data."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = None

    with pytest.raises(ValueError, match="Profile not found for user_id: user_missing"):
        collect_adaptation_data(
            user_id="user_missing",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
        )

    mock_profile_repo.get_profile.assert_called_once_with("user_missing")
    # Should fail-fast before attempting daily logs query
    mock_log_repo.get_logs.assert_not_called()


def test_collect_adaptation_data_profile_repo_error_propagation():
    """Verify database exceptions during profile fetch propagate to caller."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    mock_profile_repo.get_profile.side_effect = RuntimeError("Supabase connection timeout")

    with pytest.raises(RuntimeError, match="Supabase connection timeout"):
        collect_adaptation_data(
            user_id="user_err",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
        )


def test_collect_adaptation_data_daily_log_repo_error_propagation():
    """Verify database exceptions during daily log fetch propagate to caller."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_err_logs"}
    mock_log_repo.get_logs.side_effect = ConnectionError("Database network failure")

    with pytest.raises(ConnectionError, match="Database network failure"):
        collect_adaptation_data(
            user_id="user_err_logs",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
        )


def test_collect_adaptation_data_correct_user_id_passed():
    """Verify the exact user_id is passed to both profile and daily log repositories."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "specific_user_789"}
    mock_log_repo.get_logs.return_value = []

    collect_adaptation_data(
        user_id="specific_user_789",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
    )

    mock_profile_repo.get_profile.assert_called_once_with("specific_user_789")
    mock_log_repo.get_logs.assert_called_once_with("specific_user_789")


def test_collect_adaptation_data_no_repository_write_methods_called():
    """Verify that collector is strictly read-only and calls no mutation methods."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_readonly"}
    mock_log_repo.get_logs.return_value = []

    collect_adaptation_data(
        user_id="user_readonly",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
    )

    # Verify write methods are never called
    assert not hasattr(mock_profile_repo, "upsert_profile") or mock_profile_repo.upsert_profile.call_count == 0
    assert not hasattr(mock_log_repo, "add_log") or mock_log_repo.add_log.call_count == 0


def test_collect_adaptation_data_with_token_forwarding():
    """Verify JWT access token is forwarded to repositories for Supabase RLS policies."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_rls"}
    mock_log_repo.get_logs.return_value = []

    collect_adaptation_data(
        user_id="user_rls",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        user_token="bearer_jwt_token_xyz",
    )

    mock_profile_repo.get_profile.assert_called_once_with("user_rls", user_token="bearer_jwt_token_xyz")
    mock_log_repo.get_logs.assert_called_once_with("user_rls", user_token="bearer_jwt_token_xyz")


def test_collect_adaptation_data_empty_user_id_rejected():
    """Verify missing or empty user_id raises ValueError."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()

    with pytest.raises(ValueError, match="user_id must be provided"):
        collect_adaptation_data(
            user_id="",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
        )
