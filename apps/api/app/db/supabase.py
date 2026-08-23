"""
Supabase Database Client & Production Repository Layer.
Strict Per-Request RLS Authorization:
- Forwards user's Bearer JWT into postgrest.auth(user_token) so auth.uid() evaluates correctly in RLS policies.
- Live Supabase queries raise exceptions on failure (NO mid-request fallback).
- Offline test mode uses local memory store when IS_LIVE_SUPABASE_ENABLED is False.
"""

from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from app.core.config import settings

# Startup-Time Check: Determine whether live Supabase is enabled
IS_LIVE_SUPABASE_ENABLED: bool = bool(
    settings.SUPABASE_URL
    and "xyzcompany" not in settings.SUPABASE_URL
    and settings.SUPABASE_ANON_KEY
    and "dummy" not in settings.SUPABASE_ANON_KEY
)


def get_authenticated_supabase_client(user_token: Optional[str] = None) -> Optional[Client]:
    """
    Creates a Supabase client and forwards user's JWT token to PostgREST headers,
    ensuring PostgreSQL auth.uid() evaluates to the authenticated user ID for RLS policies.
    """
    if not IS_LIVE_SUPABASE_ENABLED:
        return None

    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    if user_token and not user_token.startswith("test_token_"):
        # Forward authenticated user's JWT to PostgREST for RLS auth.uid() evaluation
        client.postgrest.auth(user_token)
    return client


# In-memory database store used ONLY when IS_LIVE_SUPABASE_ENABLED is False
_OFFLINE_TEST_DB: Dict[str, Dict[str, Any]] = {
    "profiles": {},
    "user_meal_plans": {},
    "user_workout_plans": {},
    "daily_logs": {},
    "simulations": {},
    "journal_entries": {},
}


class ProfileRepository:
    """Production Repository for profiles table with Supabase RLS JWT forwarding."""

    @staticmethod
    def get_profile(user_id: str, user_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("profiles").select("*").eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        return _OFFLINE_TEST_DB["profiles"].get(user_id)

    @staticmethod
    def upsert_profile(user_id: str, profile_data: Dict[str, Any], user_token: Optional[str] = None) -> Dict[str, Any]:
        record = {**profile_data, "id": user_id}
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("profiles").upsert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase profile upsert returned empty response data")
        _OFFLINE_TEST_DB["profiles"][user_id] = record
        return record


class DailyLogRepository:
    """Production Repository for daily_logs table with Supabase RLS JWT forwarding."""

    @staticmethod
    def get_logs(user_id: str, user_token: Optional[str] = None) -> List[Dict[str, Any]]:
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("daily_logs")
                .select("*")
                .eq("user_id", user_id)
                .order("log_date", desc=True)
                .execute()
            )
            return res.data if res.data is not None else []
        logs = [log for log in _OFFLINE_TEST_DB["daily_logs"].values() if log.get("user_id") == user_id]
        return sorted(logs, key=lambda x: str(x.get("log_date", "")), reverse=True)

    @staticmethod
    def add_log(user_id: str, log_data: Dict[str, Any], user_token: Optional[str] = None) -> Dict[str, Any]:
        record = {**log_data, "user_id": user_id}
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("daily_logs").upsert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase log upsert returned empty response data")
        log_id = f"{user_id}_{log_data.get('log_date')}"
        record["id"] = log_id
        _OFFLINE_TEST_DB["daily_logs"][log_id] = record
        return record


class JournalRepository:
    """Production Repository for journal_entries table with Supabase RLS JWT forwarding."""

    @staticmethod
    def add_entry(
        user_id: str,
        entry_text: str,
        sentiment: str,
        ai_feedback: Dict[str, Any],
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = {
            "user_id": user_id,
            "entry_text": entry_text,
            "sentiment_tag": sentiment,
            "ai_feedback": ai_feedback,
        }
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("journal_entries").insert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase journal insert returned empty response data")
        entry_id = f"journal_{len(_OFFLINE_TEST_DB['journal_entries']) + 1}"
        record["id"] = entry_id
        _OFFLINE_TEST_DB["journal_entries"][entry_id] = record
        return record
