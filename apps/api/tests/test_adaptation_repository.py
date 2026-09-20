"""
Unit Test Suite for Read-Only Adaptation Data Collector Layer.

Verifies:
- Profile found + logs found returns expected dict
- Profile found + no logs returns expected dict with empty logs list
- Missing profile raises ValueError explicitly (no fake/default profile)
- Database/repository exceptions propagate to caller
- Correct user_id is passed to all repositories
- No repository write methods are called (strictly read-only)
- JWT token forwarding when supplied
- Journal entries are collected raw (no reordering, filtering, or interpretation)
"""

import inspect

import pytest
from unittest.mock import MagicMock
from app.db.supabase import JournalRepository
from app.engine.adaptation import collect_adaptation_data


def test_collect_adaptation_data_profile_found_and_logs_found():
    """Verify raw profile, daily logs and journal entries are returned when all exist."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

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
    sample_journal = [
        {
            "id": "j1",
            "user_id": "user_001",
            "entry_text": "Felt strong today",
            "sentiment_tag": "motivated",
            "ai_feedback": {"summary": "Logged journal update regarding current training state."},
            "created_at": "2026-09-18T18:00:00.123456+00:00",
        },
    ]

    mock_profile_repo.get_profile.return_value = sample_profile
    mock_log_repo.get_logs.return_value = sample_logs
    mock_journal_repo.get_entries.return_value = sample_journal

    data = collect_adaptation_data(
        user_id="user_001",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    assert set(data.keys()) == {"profile", "daily_logs", "journal_entries"}
    assert data["profile"] == sample_profile
    assert data["daily_logs"] == sample_logs
    assert data["journal_entries"] == sample_journal
    assert len(data["daily_logs"]) == 2


def test_collect_adaptation_data_profile_found_and_no_logs():
    """Verify empty list is returned for daily_logs when user has no logged days."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    sample_profile = {
        "id": "user_new",
        "first_name": "Jordan",
        "weight_kg": 70.0,
        "goal_type": "muscle_gain",
    }
    mock_profile_repo.get_profile.return_value = sample_profile
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = []

    data = collect_adaptation_data(
        user_id="user_new",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    assert data["profile"] == sample_profile
    assert data["daily_logs"] == []
    assert data["journal_entries"] == []


def test_collect_adaptation_data_profile_missing():
    """Verify missing profile explicitly raises ValueError and does not invent fake data."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = None

    with pytest.raises(ValueError, match="Profile not found for user_id: user_missing"):
        collect_adaptation_data(
            user_id="user_missing",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
            journal_repository=mock_journal_repo,
        )

    mock_profile_repo.get_profile.assert_called_once_with("user_missing")
    # Should fail-fast before attempting daily logs or journal queries
    mock_log_repo.get_logs.assert_not_called()
    mock_journal_repo.get_entries.assert_not_called()


def test_collect_adaptation_data_profile_repo_error_propagation():
    """Verify database exceptions during profile fetch propagate to caller."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.side_effect = RuntimeError("Supabase connection timeout")

    with pytest.raises(RuntimeError, match="Supabase connection timeout"):
        collect_adaptation_data(
            user_id="user_err",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
            journal_repository=mock_journal_repo,
        )

    mock_journal_repo.get_entries.assert_not_called()


def test_collect_adaptation_data_daily_log_repo_error_propagation():
    """Verify database exceptions during daily log fetch propagate to caller."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_err_logs"}
    mock_log_repo.get_logs.side_effect = ConnectionError("Database network failure")

    with pytest.raises(ConnectionError, match="Database network failure"):
        collect_adaptation_data(
            user_id="user_err_logs",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
            journal_repository=mock_journal_repo,
        )

    mock_journal_repo.get_entries.assert_not_called()


def test_collect_adaptation_data_correct_user_id_passed():
    """Verify the exact user_id is passed to profile, daily log and journal repositories."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "specific_user_789"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = []

    collect_adaptation_data(
        user_id="specific_user_789",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    mock_profile_repo.get_profile.assert_called_once_with("specific_user_789")
    mock_log_repo.get_logs.assert_called_once_with("specific_user_789")
    mock_journal_repo.get_entries.assert_called_once_with("specific_user_789")


def test_collect_adaptation_data_no_repository_write_methods_called():
    """Verify that collector is strictly read-only and calls no mutation methods."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_readonly"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = []

    collect_adaptation_data(
        user_id="user_readonly",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    # Verify write methods are never called
    assert not hasattr(mock_profile_repo, "upsert_profile") or mock_profile_repo.upsert_profile.call_count == 0
    assert not hasattr(mock_log_repo, "add_log") or mock_log_repo.add_log.call_count == 0
    assert mock_journal_repo.add_entry.call_count == 0


def test_collect_adaptation_data_with_token_forwarding():
    """Verify JWT access token is forwarded to all repositories for Supabase RLS policies."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_rls"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = []

    collect_adaptation_data(
        user_id="user_rls",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        user_token="bearer_jwt_token_xyz",
        journal_repository=mock_journal_repo,
    )

    mock_profile_repo.get_profile.assert_called_once_with("user_rls", user_token="bearer_jwt_token_xyz")
    mock_log_repo.get_logs.assert_called_once_with("user_rls", user_token="bearer_jwt_token_xyz")
    mock_journal_repo.get_entries.assert_called_once_with("user_rls", user_token="bearer_jwt_token_xyz")


def test_collect_adaptation_data_empty_user_id_rejected():
    """Verify missing or empty user_id raises ValueError."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    with pytest.raises(ValueError, match="user_id must be provided"):
        collect_adaptation_data(
            user_id="",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
            journal_repository=mock_journal_repo,
        )

    mock_journal_repo.get_entries.assert_not_called()


def test_collect_adaptation_data_journal_entries_passed_through_unmodified():
    """Collector must not reorder, filter, truncate, or interpret journal entries."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    same_day_entries = [
        {
            "id": "j_evening",
            "created_at": "2026-09-15T18:00:00+00:00",
            "sentiment_tag": "motivated",
            "ai_feedback": {"summary": "evening"},
        },
        {
            "id": "j_morning",
            "created_at": "2026-09-15T09:00:00+00:00",
            "sentiment_tag": "fatigued",
            "ai_feedback": {"summary": "morning"},
        },
        {
            "id": "j_unknown_tag",
            "created_at": "2026-09-14T09:00:00+00:00",
            "sentiment_tag": "stressed",
            "summary": "top-level summary",
        },
    ]
    mock_profile_repo.get_profile.return_value = {"id": "user_j"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = same_day_entries

    data = collect_adaptation_data(
        user_id="user_j",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    assert data["journal_entries"] == same_day_entries
    assert [e["id"] for e in data["journal_entries"]] == ["j_evening", "j_morning", "j_unknown_tag"]
    assert data["journal_entries"][0]["created_at"] == "2026-09-15T18:00:00+00:00"
    assert data["journal_entries"][2]["sentiment_tag"] == "stressed"


def test_collect_adaptation_data_no_journal_entries_returns_empty_list():
    """A user with no journals gets an empty list, not a missing key."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_nj"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = []

    data = collect_adaptation_data(
        user_id="user_nj",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    assert "journal_entries" in data
    assert data["journal_entries"] == []


def test_collect_adaptation_data_none_journal_entries_becomes_empty_list():
    """Defensive: a repository returning None is normalized to an empty list."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_none"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.return_value = None

    data = collect_adaptation_data(
        user_id="user_none",
        profile_repository=mock_profile_repo,
        daily_log_repository=mock_log_repo,
        journal_repository=mock_journal_repo,
    )

    assert data["journal_entries"] == []


def test_collect_adaptation_data_journal_repo_error_propagation():
    """Journal fetch failures must propagate, not be swallowed into an empty list."""
    mock_profile_repo = MagicMock()
    mock_log_repo = MagicMock()
    mock_journal_repo = MagicMock()

    mock_profile_repo.get_profile.return_value = {"id": "user_jerr"}
    mock_log_repo.get_logs.return_value = []
    mock_journal_repo.get_entries.side_effect = RuntimeError("Supabase RLS Permission Denied")

    with pytest.raises(RuntimeError, match="RLS Permission Denied"):
        collect_adaptation_data(
            user_id="user_jerr",
            profile_repository=mock_profile_repo,
            daily_log_repository=mock_log_repo,
            journal_repository=mock_journal_repo,
        )


def test_collect_adaptation_data_signature_and_default_journal_repository():
    """journal_repository is the LAST parameter (existing callers unaffected) and defaults to the real repository."""
    params = inspect.signature(collect_adaptation_data).parameters
    assert list(params) == [
        "user_id",
        "profile_repository",
        "daily_log_repository",
        "user_token",
        "journal_repository",
    ]
    assert params["journal_repository"].default is JournalRepository
