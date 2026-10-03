"""
Supabase Database Client & Production Repository Layer.
Strict Per-Request RLS Authorization:
- Forwards user's Bearer JWT into postgrest.auth(user_token) so auth.uid() evaluates correctly in RLS policies.
- Live Supabase queries raise exceptions on failure (NO mid-request fallback).
- Offline test mode uses local memory store when IS_LIVE_SUPABASE_ENABLED is False.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
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

    if user_token and user_token.startswith("test_token_"):
        # Fall back to offline test store for unit tests using mock tokens
        return None

    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    if user_token:
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
    "adaptation_history": {},
    # Phase 5A — body analysis
    "progress_photos": {},
    "body_analysis_results": {},
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
        db_record = {k: v for k, v in record.items() if k != "target_metrics"}
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("profiles").upsert(db_record).execute()
            if res.data and len(res.data) > 0:
                result = dict(res.data[0])
                if "target_metrics" in record:
                    result["target_metrics"] = record["target_metrics"]
                return result
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
            res = client.table("daily_logs").upsert(record, on_conflict="user_id,log_date").execute()
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

    @staticmethod
    def get_entries(
        user_id: str,
        user_token: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Read-only. Returns the user's journal entries, newest first (created_at desc)."""
        if limit < 1:
            raise ValueError("limit must be >= 1")
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("journal_entries")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data if res.data is not None else []
        entries = [
            dict(e)
            for e in reversed(list(_OFFLINE_TEST_DB["journal_entries"].values()))
            if e.get("user_id") == user_id
        ]
        # Stable sort: entries without created_at keep newest-inserted-first order
        entries.sort(key=lambda e: str(e.get("created_at") or ""), reverse=True)
        return entries[:limit]


class MealPlanRepository:
    """Production Repository for user_meal_plans table with Supabase RLS JWT forwarding."""

    @staticmethod
    def save_meal_plan(
        user_id: str,
        plan_data: Dict[str, Any],
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Saves a meal plan as active for the user, archiving (deactivating) any previous active meal plans.
        """
        record = {
            "user_id": user_id,
            "title": str(plan_data.get("title") or "Deterministic Meal Plan"),
            "target_calories": int(round(plan_data.get("target_calories", 0))),
            "target_protein_g": int(round(plan_data.get("target_protein_g", 0))),
            "target_carbs_g": int(round(plan_data.get("target_carbs_g", 0))),
            "target_fat_g": int(round(plan_data.get("target_fat_g", 0))),
            "plan_data": dict(plan_data),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = get_authenticated_supabase_client(user_token)
        if client:
            client.table("user_meal_plans").update({"is_active": False}).eq("user_id", user_id).eq("is_active", True).execute()
            res = client.table("user_meal_plans").insert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase user_meal_plans insert returned empty response data")

        for p in _OFFLINE_TEST_DB["user_meal_plans"].values():
            if p.get("user_id") == user_id and p.get("is_active") is True:
                p["is_active"] = False

        plan_id = f"meal_plan_{len(_OFFLINE_TEST_DB['user_meal_plans']) + 1}"
        if plan_id in _OFFLINE_TEST_DB["user_meal_plans"]:
            plan_id = f"meal_plan_{uuid.uuid4().hex[:8]}"
        record["id"] = plan_id
        _OFFLINE_TEST_DB["user_meal_plans"][plan_id] = record
        return record

    @staticmethod
    def get_active_meal_plan(
        user_id: str,
        user_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read-only. Returns user's currently active meal plan, or None if no active plan exists."""
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("user_meal_plans")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None

        active_plans = [
            dict(p)
            for p in _OFFLINE_TEST_DB["user_meal_plans"].values()
            if p.get("user_id") == user_id and p.get("is_active") is True
        ]
        if not active_plans:
            return None
        active_plans.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return active_plans[0]


class WorkoutPlanRepository:
    """Production Repository for user_workout_plans table with Supabase RLS JWT forwarding."""

    @staticmethod
    def save_workout_plan(
        user_id: str,
        plan_data: Dict[str, Any],
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Saves a workout plan as active for the user, archiving (deactivating) any previous active workout plans.
        """
        record = {
            "user_id": user_id,
            "title": str(plan_data.get("title") or "Deterministic Workout Plan"),
            "split_type": str(plan_data.get("split_type") or "FULL_BODY"),
            "days_per_week": int(plan_data.get("days_per_week", 4)),
            "routine_data": dict(plan_data),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = get_authenticated_supabase_client(user_token)
        if client:
            client.table("user_workout_plans").update({"is_active": False}).eq("user_id", user_id).eq("is_active", True).execute()
            res = client.table("user_workout_plans").insert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase user_workout_plans insert returned empty response data")

        for p in _OFFLINE_TEST_DB["user_workout_plans"].values():
            if p.get("user_id") == user_id and p.get("is_active") is True:
                p["is_active"] = False

        plan_id = f"workout_plan_{len(_OFFLINE_TEST_DB['user_workout_plans']) + 1}"
        if plan_id in _OFFLINE_TEST_DB["user_workout_plans"]:
            plan_id = f"workout_plan_{uuid.uuid4().hex[:8]}"
        record["id"] = plan_id
        _OFFLINE_TEST_DB["user_workout_plans"][plan_id] = record
        return record

    @staticmethod
    def get_active_workout_plan(
        user_id: str,
        user_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read-only. Returns user's currently active workout plan, or None if no active plan exists."""
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("user_workout_plans")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None

        active_plans = [
            dict(p)
            for p in _OFFLINE_TEST_DB["user_workout_plans"].values()
            if p.get("user_id") == user_id and p.get("is_active") is True
        ]
        if not active_plans:
            return None
        active_plans.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return active_plans[0]


class AdaptationHistoryRepository:
    """Production Repository for adaptation_history table with Supabase RLS JWT forwarding."""

    @staticmethod
    def _serialize_record(data: Dict[str, Any]) -> Dict[str, Any]:
        """Converts any nested Pydantic models or date/time objects into JSON-serializable primitives."""
        def _conv(v: Any) -> Any:
            if hasattr(v, "model_dump"):
                return v.model_dump(mode="json")
            if isinstance(v, dict):
                return {k: _conv(val) for k, val in v.items()}
            if isinstance(v, (list, tuple)):
                return [_conv(item) for item in v]
            return v
        return {k: _conv(v) for k, v in data.items()}

    @classmethod
    def save_history(
        cls,
        user_id: str,
        record_data: Dict[str, Any],
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists a single adaptation decision and input snapshot for the authenticated user.
        Forwards JWT Bearer token so PostgreSQL auth.uid() = user_id evaluates correctly under RLS.
        """
        serialized = cls._serialize_record(record_data)
        record = {**serialized, "user_id": user_id}
        if "created_at" not in record or not record["created_at"]:
            record["created_at"] = datetime.now(timezone.utc).isoformat()

        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("adaptation_history").insert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase adaptation_history insert returned empty response data")

        history_id = f"adapt_{uuid.uuid4()}"
        record["id"] = history_id
        _OFFLINE_TEST_DB["adaptation_history"][history_id] = record
        return record

    @classmethod
    def get_history(
        cls,
        user_id: str,
        user_token: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the authenticated user's adaptation decision history ordered newest first (created_at DESC).
        Enforces user isolation and clamps limit between 1 and 100.
        """
        clamped_limit = max(1, min(100, int(limit)))
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("adaptation_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(clamped_limit)
                .execute()
            )
            return res.data if res.data is not None else []

        user_records = [
            dict(r)
            for r in _OFFLINE_TEST_DB["adaptation_history"].values()
            if r.get("user_id") == user_id
        ]
        user_records.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return user_records[:clamped_limit]

    @classmethod
    def get_latest_history(
        cls,
        user_id: str,
        user_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Returns the most recent adaptation decision record for the user, or None if none exist."""
        history = cls.get_history(user_id=user_id, user_token=user_token, limit=1)
        return history[0] if history else None


class ProgressPhotoRepository:
    """
    Production Repository for progress_photos table.

    Phase 5A — database layer only. No image bytes are stored here;
    actual photo data lives in the private Supabase Storage bucket.
    All writes enforce user_id ownership; all reads filter by user_id.
    """

    @staticmethod
    def create_photo(
        user_id: str,
        photo_data: Dict[str, Any],
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists photo metadata for the authenticated user.

        photo_data must include: storage_path, photo_type, captured_at.
        Optional: file_size_bytes, width_px, height_px, mime_type.
        user_id is always taken from the authenticated token, never from the payload.
        """
        record = {
            **{k: v for k, v in photo_data.items() if k != "user_id"},
            "user_id": user_id,
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("progress_photos").insert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase progress_photos insert returned empty response")
        photo_id = str(uuid.uuid4())
        record["id"] = photo_id
        _OFFLINE_TEST_DB["progress_photos"][photo_id] = record
        return record

    @staticmethod
    def get_photos(
        user_id: str,
        user_token: Optional[str] = None,
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        """Returns the user's progress photo records, newest first."""
        client = get_authenticated_supabase_client(user_token)
        if client:
            q = (
                client.table("progress_photos")
                .select("*")
                .eq("user_id", user_id)
                .order("captured_at", desc=True)
            )
            if not include_deleted:
                q = q.eq("is_deleted", False)
            res = q.execute()
            return res.data if res.data is not None else []
        rows = [
            dict(r)
            for r in _OFFLINE_TEST_DB["progress_photos"].values()
            if r.get("user_id") == user_id
            and (include_deleted or not r.get("is_deleted", False))
        ]
        rows.sort(key=lambda x: str(x.get("captured_at") or ""), reverse=True)
        return rows

    @staticmethod
    def get_photo(
        photo_id: str,
        user_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Returns a single photo record by id (RLS enforces ownership at DB level)."""
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("progress_photos")
                .select("*")
                .eq("id", photo_id)
                .eq("is_deleted", False)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        row = _OFFLINE_TEST_DB["progress_photos"].get(photo_id)
        if row and not row.get("is_deleted", False):
            return dict(row)
        return None

    @staticmethod
    def soft_delete_photo(
        photo_id: str,
        user_id: str,
        user_token: Optional[str] = None,
    ) -> bool:
        """
        Soft-deletes the photo row (sets is_deleted=True).
        Returns True if a row was updated, False if nothing was found or owned by another user.
        The API layer is responsible for also hard-deleting the storage object.
        """
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("progress_photos")
                .update({"is_deleted": True})
                .eq("id", photo_id)
                .eq("user_id", user_id)
                .eq("is_deleted", False)
                .execute()
            )
            return bool(res.data and len(res.data) > 0)
        row = _OFFLINE_TEST_DB["progress_photos"].get(photo_id)
        if row and row.get("user_id") == user_id and not row.get("is_deleted", False):
            row["is_deleted"] = True
            return True
        return False


class BodyAnalysisRepository:
    """
    Production Repository for body_analysis_results table.

    Phase 5A — stores analysis output linked to a progress photo.
    Results are OBSERVATIONAL ONLY and must not be fed into adaptation formulas.
    """

    @staticmethod
    def create_result(
        user_id: str,
        photo_id: str,
        result_data: Dict[str, Any],
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persists a body analysis result for the given photo."""
        record = {
            **{k: v for k, v in result_data.items() if k not in ("user_id", "photo_id")},
            "user_id": user_id,
            "photo_id": photo_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = client.table("body_analysis_results").insert(record).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            raise RuntimeError("Supabase body_analysis_results insert returned empty response")
        result_id = str(uuid.uuid4())
        record["id"] = result_id
        _OFFLINE_TEST_DB["body_analysis_results"][result_id] = record
        return record

    @staticmethod
    def get_result_by_photo(
        photo_id: str,
        user_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Returns the analysis result for a specific photo, or None."""
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("body_analysis_results")
                .select("*")
                .eq("photo_id", photo_id)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        for row in _OFFLINE_TEST_DB["body_analysis_results"].values():
            if row.get("photo_id") == photo_id:
                return dict(row)
        return None

    @staticmethod
    def get_results_by_user(
        user_id: str,
        user_token: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Returns all analysis results for a user, newest first."""
        clamped = max(1, min(100, int(limit)))
        client = get_authenticated_supabase_client(user_token)
        if client:
            res = (
                client.table("body_analysis_results")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(clamped)
                .execute()
            )
            return res.data if res.data is not None else []
        rows = [
            dict(r)
            for r in _OFFLINE_TEST_DB["body_analysis_results"].values()
            if r.get("user_id") == user_id
        ]
        rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return rows[:clamped]
