"""
Tests for the adaptation pipeline:
collect_adaptation_data -> ensure_target_metrics -> prepare_adaptation_input -> compute_adaptation

Repositories are mocked with database-shaped rows (the shape Supabase returns): profile rows
have NO target_metrics (it is not a stored column) and journal rows carry full created_at
timestamps. These tests deliberately do not assert on coaching_summary text.
"""

import copy
import inspect
from unittest.mock import MagicMock, patch

import pytest

import app.engine.adaptation as adaptation_mod
from app.db import supabase as db_mod
from app.db.supabase import DailyLogRepository, JournalRepository, ProfileRepository
from app.engine.adaptation import (
    AdaptationDecision,
    compute_adaptation_for_user,
    ensure_target_metrics,
)
from app.engine.bmr_tdee import calculate_target_metrics

USER = "user_pipeline"
FATIGUE_REC = "Recent journal reflects fatigue. Prioritize recovery and sleep."
MOTIVATION_REC = "High motivation noted in recent journal. Channel energy into structured training."
REQUIRED_PROFILE_FIELDS = [
    "weight_kg",
    "height_cm",
    "age",
    "gender",
    "activity_level",
    "goal_type",
]


def _db_profile(**overrides):
    row = {
        "id": USER,
        "first_name": "Alex",
        "gender": "male",
        "age": 25,
        "height_cm": 178.0,
        "weight_kg": 82.5,
        "target_weight_kg": 75.0,
        "body_fat_pct": None,
        "activity_level": "moderately_active",
        "goal_type": "fat_loss",
        "dietary_preference": "anything",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
        "created_at": "2026-09-01T08:00:00+00:00",
        "updated_at": "2026-09-01T08:00:00+00:00",
    }
    row.update(overrides)
    return row


def _db_logs(count=4):
    return [
        {
            "id": f"log_{i}",
            "user_id": USER,
            "log_date": f"2026-09-{18 - i:02d}",
            "weight_kg": round(82.2 - 0.1 * i, 1),
            "calories_consumed": 1900 - 10 * i,
            "protein_consumed_g": 150,
            "carbs_consumed_g": 180,
            "fat_consumed_g": 55,
            "water_liters": 2.5,
            "workout_completed": i % 2 == 0,
            "energy_rating": 7,
            "notes": None,
            "created_at": f"2026-09-{18 - i:02d}T20:00:00+00:00",
        }
        for i in range(count)
    ]


def _journal_row(entry_id, created_at, sentiment):
    return {
        "id": entry_id,
        "user_id": USER,
        "entry_text": "text",
        "sentiment_tag": sentiment,
        "ai_feedback": {"summary": f"summary {entry_id}"},
        "created_at": created_at,
    }


EVENING_MOTIVATED = _journal_row("evening", "2026-09-15T18:00:00.123456+00:00", "motivated")
MORNING_FATIGUED = _journal_row("morning", "2026-09-15T09:00:00.654321+00:00", "fatigued")


def _repos(profile=None, logs=None, journal=None):
    profile_repo = MagicMock()
    log_repo = MagicMock()
    journal_repo = MagicMock()
    profile_repo.get_profile.return_value = _db_profile() if profile is None else profile
    log_repo.get_logs.return_value = _db_logs() if logs is None else logs
    journal_repo.get_entries.return_value = [] if journal is None else journal
    return profile_repo, log_repo, journal_repo


def _run(profile_repo, log_repo, journal_repo, user_token=None):
    return compute_adaptation_for_user(
        USER,
        user_token=user_token,
        profile_repository=profile_repo,
        daily_log_repository=log_repo,
        journal_repository=journal_repo,
    )


def _direct_targets(profile, body_fat=None):
    return calculate_target_metrics(
        weight_kg=float(profile["weight_kg"]),
        height_cm=float(profile["height_cm"]),
        age=int(profile["age"]),
        gender=str(profile["gender"]),
        activity_level=str(profile["activity_level"]),
        goal_type=str(profile["goal_type"]),
        body_fat_pct=body_fat,
    )


# ---------------------------------------------------------------------------
# ensure_target_metrics
# ---------------------------------------------------------------------------

def test_ensure_target_metrics_computes_when_missing():
    profile = _db_profile()
    snapshot = copy.deepcopy(profile)

    result = ensure_target_metrics(profile)

    assert result["target_metrics"] == _direct_targets(profile)
    for key in ("target_calories", "protein_g", "carbs_g", "fat_g"):
        assert result["target_metrics"][key] > 0
    assert profile == snapshot
    assert "target_metrics" not in profile
    assert result is not profile


def test_ensure_target_metrics_keeps_existing_values():
    stored = {"target_calories": 1900.0, "protein_g": 150.0, "carbs_g": 190.0, "fat_g": 55.0}
    profile = _db_profile(target_metrics=stored)

    result = ensure_target_metrics(profile)

    assert result["target_metrics"] == stored
    assert result is not profile


def test_ensure_target_metrics_recomputes_when_empty_dict():
    profile = _db_profile(target_metrics={})

    result = ensure_target_metrics(profile)

    assert result["target_metrics"] == _direct_targets(profile)


@pytest.mark.parametrize("field", REQUIRED_PROFILE_FIELDS)
def test_ensure_target_metrics_raises_when_required_field_missing(field):
    profile = _db_profile(**{field: None})
    with pytest.raises(ValueError, match=field):
        ensure_target_metrics(profile)


def test_ensure_target_metrics_lists_every_missing_field():
    profile = _db_profile(height_cm=None, age=None)
    with pytest.raises(ValueError) as exc_info:
        ensure_target_metrics(profile)
    assert "height_cm" in str(exc_info.value)
    assert "age" in str(exc_info.value)


def test_ensure_target_metrics_passes_body_fat_when_present():
    profile = _db_profile(body_fat_pct=18.5)

    result = ensure_target_metrics(profile)

    assert result["target_metrics"] == _direct_targets(profile, body_fat=18.5)


# ---------------------------------------------------------------------------
# compute_adaptation_for_user
# ---------------------------------------------------------------------------

def test_pipeline_runs_on_database_shaped_profile_without_target_metrics():
    decision = _run(*_repos())
    assert isinstance(decision, AdaptationDecision)


def test_pipeline_latest_fatigued_journal_adds_fatigue_recommendation():
    decision = _run(*_repos(journal=[MORNING_FATIGUED]))
    assert FATIGUE_REC in decision.actionable_recommendations
    assert MOTIVATION_REC not in decision.actionable_recommendations


def test_pipeline_same_day_latest_entry_wins_regardless_of_repository_order():
    for order in (
        [EVENING_MOTIVATED, MORNING_FATIGUED],
        [MORNING_FATIGUED, EVENING_MOTIVATED],
    ):
        decision = _run(*_repos(journal=list(order)))
        assert MOTIVATION_REC in decision.actionable_recommendations
        assert FATIGUE_REC not in decision.actionable_recommendations


def test_pipeline_fewer_than_three_logs_ignores_journal():
    decision = _run(*_repos(logs=_db_logs(2), journal=[MORNING_FATIGUED]))
    assert decision.actionable_recommendations == []
    assert decision.readiness_factor == 1.0


def test_pipeline_without_journal_entries_adds_no_journal_recommendation():
    decision = _run(*_repos(journal=[]))
    assert FATIGUE_REC not in decision.actionable_recommendations
    assert MOTIVATION_REC not in decision.actionable_recommendations


def test_pipeline_passes_resolved_target_metrics_to_prepare():
    profile_row = _db_profile()
    repos = _repos(profile=profile_row)
    with patch.object(
        adaptation_mod,
        "prepare_adaptation_input",
        wraps=adaptation_mod.prepare_adaptation_input,
    ) as spy:
        _run(*repos)

    assert spy.call_count == 1
    passed_profile = spy.call_args[0][0]
    assert passed_profile["target_metrics"] == _direct_targets(profile_row)
    assert "target_metrics" not in profile_row


def test_pipeline_missing_profile_raises_value_error():
    profile_repo, log_repo, journal_repo = _repos()
    profile_repo.get_profile.return_value = None
    with pytest.raises(ValueError, match="Profile not found"):
        _run(profile_repo, log_repo, journal_repo)
    journal_repo.get_entries.assert_not_called()


def test_pipeline_incomplete_profile_raises_value_error():
    repos = _repos(profile=_db_profile(height_cm=None))
    with pytest.raises(ValueError, match="height_cm"):
        _run(*repos)


def test_pipeline_forwards_token_to_all_repositories():
    profile_repo, log_repo, journal_repo = _repos()
    _run(profile_repo, log_repo, journal_repo, user_token="jwt_abc")
    profile_repo.get_profile.assert_called_once_with(USER, user_token="jwt_abc")
    log_repo.get_logs.assert_called_once_with(USER, user_token="jwt_abc")
    journal_repo.get_entries.assert_called_once_with(USER, user_token="jwt_abc")


def test_pipeline_does_not_mutate_repository_data():
    profile_row = _db_profile()
    logs = _db_logs()
    journal = [copy.deepcopy(EVENING_MOTIVATED), copy.deepcopy(MORNING_FATIGUED)]
    snapshots = (copy.deepcopy(profile_row), copy.deepcopy(logs), copy.deepcopy(journal))

    _run(*_repos(profile=profile_row, logs=logs, journal=journal))

    assert (profile_row, logs, journal) == snapshots


def test_pipeline_journal_repository_error_propagates():
    profile_repo, log_repo, journal_repo = _repos()
    journal_repo.get_entries.side_effect = RuntimeError("Supabase RLS Permission Denied")
    with pytest.raises(RuntimeError, match="RLS Permission Denied"):
        _run(profile_repo, log_repo, journal_repo)


def test_pipeline_is_read_only():
    profile_repo, log_repo, journal_repo = _repos(journal=[EVENING_MOTIVATED])
    _run(profile_repo, log_repo, journal_repo)
    assert profile_repo.upsert_profile.call_count == 0
    assert log_repo.add_log.call_count == 0
    assert journal_repo.add_entry.call_count == 0


def test_pipeline_end_to_end_with_real_repositories_in_offline_store():
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["profiles"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["daily_logs"], {}, clear=True), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):
        profile = _db_profile()
        profile.pop("id")
        # No target_metrics: same shape as a row stored in the database
        ProfileRepository.upsert_profile(USER, profile)
        for log in _db_logs():
            DailyLogRepository.add_log(
                USER, {k: v for k, v in log.items() if k not in ("id", "user_id")}
            )
        db_mod._OFFLINE_TEST_DB["journal_entries"]["j_evening"] = dict(EVENING_MOTIVATED)
        db_mod._OFFLINE_TEST_DB["journal_entries"]["j_morning"] = dict(MORNING_FATIGUED)

        decision = compute_adaptation_for_user(USER)

    assert isinstance(decision, AdaptationDecision)
    assert MOTIVATION_REC in decision.actionable_recommendations
    assert FATIGUE_REC not in decision.actionable_recommendations


def test_compute_adaptation_for_user_signature_and_default_repositories():
    params = inspect.signature(compute_adaptation_for_user).parameters
    assert list(params) == [
        "user_id",
        "user_token",
        "profile_repository",
        "daily_log_repository",
        "journal_repository",
    ]
    assert params["user_token"].default is None
    assert params["profile_repository"].default is ProfileRepository
    assert params["daily_log_repository"].default is DailyLogRepository
    assert params["journal_repository"].default is JournalRepository
