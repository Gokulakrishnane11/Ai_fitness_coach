import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import supabase as db_mod

USER = "user_a"
TOKEN = "valid_user_jwt_token_abc"


def _live_client(rows=None, side_effect=None):
    client = MagicMock()
    chain = (
        client.table.return_value.select.return_value.eq.return_value
        .order.return_value.limit.return_value.execute
    )
    if side_effect:
        chain.side_effect = side_effect
    else:
        chain.return_value.data = rows
    return client


def test_live_query_shape_and_jwt_forwarding():
    rows = [{
        "id": "1", "user_id": USER, "entry_text": "t", "sentiment_tag": "fatigued",
        "ai_feedback": {"summary": "s"}, "created_at": "2026-09-15T10:30:00.123456+00:00",
    }]
    client = _live_client(rows)
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client):
        result = db_mod.JournalRepository.get_entries(USER, user_token=TOKEN)

    client.postgrest.auth.assert_called_with(TOKEN)
    client.table.assert_called_with("journal_entries")
    table = client.table.return_value
    table.select.assert_called_with("*")
    table.select.return_value.eq.assert_called_with("user_id", USER)
    table.select.return_value.eq.return_value.order.assert_called_with("created_at", desc=True)
    table.select.return_value.eq.return_value.order.return_value.limit.assert_called_with(30)
    assert result == rows
    assert result[0]["created_at"] == "2026-09-15T10:30:00.123456+00:00"
    assert result[0]["ai_feedback"] == {"summary": "s"}


def test_live_custom_limit_is_applied():
    client = _live_client([])
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client):
        db_mod.JournalRepository.get_entries(USER, user_token=TOKEN, limit=5)
    limit_mock = client.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    limit_mock.assert_called_with(5)


def test_live_none_data_returns_empty_list():
    client = _live_client(None)
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client):
        assert db_mod.JournalRepository.get_entries(USER, user_token=TOKEN) == []


def test_live_errors_propagate():
    client = _live_client(side_effect=Exception("Supabase RLS Permission Denied"))
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client):
        with pytest.raises(Exception, match="RLS Permission Denied"):
            db_mod.JournalRepository.get_entries(USER, user_token=TOKEN)


def test_live_is_read_only():
    client = _live_client([])
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", True), \
         patch("app.db.supabase.create_client", return_value=client):
        db_mod.JournalRepository.get_entries(USER, user_token=TOKEN)
    table = client.table.return_value
    for op in ("insert", "upsert", "update", "delete"):
        getattr(table, op).assert_not_called()


@pytest.mark.parametrize("bad", [0, -1])
def test_invalid_limit_raises(bad):
    with pytest.raises(ValueError):
        db_mod.JournalRepository.get_entries(USER, limit=bad)


def test_offline_filters_by_user_newest_first_and_returns_copies():
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):
        db_mod.JournalRepository.add_entry(USER, "first", "fatigued", {"summary": "a"})
        db_mod.JournalRepository.add_entry("user_b", "other", "motivated", {"summary": "x"})
        db_mod.JournalRepository.add_entry(USER, "second", "motivated", {"summary": "b"})

        result = db_mod.JournalRepository.get_entries(USER)
        assert [e["entry_text"] for e in result] == ["second", "first"]
        assert all(e["user_id"] == USER for e in result)
        assert result[0]["sentiment_tag"] == "motivated"
        assert result[0]["ai_feedback"] == {"summary": "b"}

        result[0]["entry_text"] = "mutated"
        again = db_mod.JournalRepository.get_entries(USER)
        assert again[0]["entry_text"] == "second"


def test_offline_orders_by_created_at_when_present():
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {
             "j1": {"id": "j1", "user_id": USER, "created_at": "2026-09-15T18:00:00+00:00"},
             "j2": {"id": "j2", "user_id": USER, "created_at": "2026-09-15T09:00:00+00:00"},
         }, clear=True):
        result = db_mod.JournalRepository.get_entries(USER)
        assert [e["id"] for e in result] == ["j1", "j2"]


def test_offline_respects_limit_and_empty_user():
    with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False), \
         patch.dict(db_mod._OFFLINE_TEST_DB["journal_entries"], {}, clear=True):
        for i in range(3):
            db_mod.JournalRepository.add_entry(USER, f"e{i}", "consistent", {})
        assert len(db_mod.JournalRepository.get_entries(USER, limit=2)) == 2
        assert db_mod.JournalRepository.get_entries("nobody") == []
