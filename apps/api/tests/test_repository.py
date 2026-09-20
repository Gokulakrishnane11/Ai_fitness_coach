"""
Unit Test Suite for Repository Layer (Live Supabase vs Offline Testing Mode).
Verifies RLS token forwarding and confirms NO mid-request error swallowing.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import supabase as db_mod


def test_offline_mode_repository_read_write():
    # Verify that in offline mode (or when patched to False), repository uses offline test store
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False):
        profile = db_mod.ProfileRepository.upsert_profile("test_user_repo", {
            "first_name": "TestUser",
            "gender": "male",
            "age": 25
        })
        assert profile["id"] == "test_user_repo"
        assert profile["first_name"] == "TestUser"

        fetched = db_mod.ProfileRepository.get_profile("test_user_repo")
        assert fetched is not None
        assert fetched["first_name"] == "TestUser"


def test_live_supabase_mode_jwt_token_forwarding_and_error_raising():
    # Verify that when live Supabase is enabled:
    # 1. Authenticated user's JWT token is forwarded to client.postgrest.auth(token) for RLS auth.uid() evaluation
    # 2. Database errors raise to caller (NO mid-request silent fallback to RAM)
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value.execute.side_effect = Exception("Supabase RLS Permission Denied")

    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True):
        with patch("app.db.supabase.create_client", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                db_mod.ProfileRepository.upsert_profile(
                    "live_user_123",
                    {"first_name": "LiveUser"},
                    user_token="valid_user_jwt_token_abc"
                )

            # Confirm PostgREST auth header was set with user's JWT token
            mock_client.postgrest.auth.assert_called_with("valid_user_jwt_token_abc")
            assert "Supabase RLS Permission Denied" in str(exc_info.value)
