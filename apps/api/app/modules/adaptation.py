"""
AI Adaptation API Module (Phase 8 / Phase 4C).
Exposes read-only adaptation decision and readiness calculation endpoints,
as well as historical decision audit trail retrieval.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import get_current_user, UserContext
from app.engine.adaptation import (
    AdaptationDecision,
    DietAdjustment,
    WorkoutAdjustment,
    compute_adaptation_for_user,
    collect_adaptation_data,
    ensure_target_metrics,
    prepare_adaptation_input,
)
from app.db.supabase import (
    ProfileRepository,
    DailyLogRepository,
    JournalRepository,
    MealPlanRepository,
    WorkoutPlanRepository,
    AdaptationHistoryRepository,
)

router = APIRouter(prefix="/adaptation", tags=["Adaptation"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AdaptationHistoryRecord(BaseModel):
    id: str
    user_id: str
    created_at: str
    readiness_factor: float
    high_fatigue_flag: bool
    plateau_detected: bool
    adherence_score: int
    recovery_score: int
    stress_score: int
    sleep_quality: int
    injury_risk: int
    plateau_probability: int
    diet_adjustment: DietAdjustment
    workout_adjustment: WorkoutAdjustment
    actionable_recommendations: List[str] = Field(default_factory=list)
    coaching_summary: str = ""
    objective_data_available: bool = False
    active_meal_plan_id: Optional[str] = None
    active_workout_plan_id: Optional[str] = None
    input_snapshot: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "AdaptationHistoryRecord":
        c_at = row.get("created_at")
        if isinstance(c_at, datetime):
            c_at = c_at.isoformat()
        return cls(
            id=str(row.get("id")),
            user_id=str(row.get("user_id")),
            created_at=str(c_at or ""),
            readiness_factor=float(row.get("readiness_factor", 1.0)),
            high_fatigue_flag=bool(row.get("high_fatigue_flag")),
            plateau_detected=bool(row.get("plateau_detected")),
            adherence_score=int(row.get("adherence_score", 100)),
            recovery_score=int(row.get("recovery_score", 100)),
            stress_score=int(row.get("stress_score", 0)),
            sleep_quality=int(row.get("sleep_quality", 100)),
            injury_risk=int(row.get("injury_risk", 0)),
            plateau_probability=int(row.get("plateau_probability", 0)),
            diet_adjustment=DietAdjustment.model_validate(row.get("diet_adjustment") or {}),
            workout_adjustment=WorkoutAdjustment.model_validate(row.get("workout_adjustment") or {}),
            actionable_recommendations=list(row.get("actionable_recommendations") or []),
            coaching_summary=str(row.get("coaching_summary") or ""),
            objective_data_available=bool(row.get("objective_data_available")),
            active_meal_plan_id=str(row["active_meal_plan_id"]) if row.get("active_meal_plan_id") else None,
            active_workout_plan_id=str(row["active_workout_plan_id"]) if row.get("active_workout_plan_id") else None,
            input_snapshot=dict(row.get("input_snapshot") or {}),
        )


class AdaptationHistoryListResponse(BaseModel):
    history: List[AdaptationHistoryRecord]
    count: int


# ---------------------------------------------------------------------------
# Persistence & Deduplication Helpers
# ---------------------------------------------------------------------------

def _is_equivalent_record(
    latest: Dict[str, Any],
    decision: AdaptationDecision,
    input_snapshot: Dict[str, Any],
    active_meal_plan_id: Optional[str],
    active_workout_plan_id: Optional[str],
) -> bool:
    """
    Deterministic comparison between a stored record and newly computed decision + inputs.
    Returns True if the state is functionally identical, avoiding duplicate historical rows.
    """
    try:
        # 1. Compare Decision Core Metrics
        if round(float(latest.get("readiness_factor", 0)), 3) != round(float(decision.readiness_factor), 3):
            return False
        if bool(latest.get("high_fatigue_flag")) != bool(decision.high_fatigue_flag):
            return False
        if bool(latest.get("plateau_detected")) != bool(decision.plateau_detected):
            return False
        if int(latest.get("adherence_score", 0)) != int(decision.adherence_score):
            return False
        if int(latest.get("recovery_score", 0)) != int(decision.recovery_score):
            return False
        if int(latest.get("stress_score", 0)) != int(decision.stress_score):
            return False
        if int(latest.get("sleep_quality", 0)) != int(decision.sleep_quality):
            return False
        if int(latest.get("injury_risk", 0)) != int(decision.injury_risk):
            return False
        if int(latest.get("plateau_probability", 0)) != int(decision.plateau_probability):
            return False

        # 2. Compare Adjustments
        latest_diet = latest.get("diet_adjustment") or {}
        dec_diet = decision.diet_adjustment.model_dump(mode="json")
        if latest_diet != dec_diet:
            return False

        latest_workout = latest.get("workout_adjustment") or {}
        dec_workout = decision.workout_adjustment.model_dump(mode="json")
        if latest_workout != dec_workout:
            return False

        # 3. Compare Active Plan IDs
        if str(latest.get("active_meal_plan_id") or "") != str(active_meal_plan_id or ""):
            return False
        if str(latest.get("active_workout_plan_id") or "") != str(active_workout_plan_id or ""):
            return False

        # 4. Compare Input Snapshot Metrics
        latest_snap = latest.get("input_snapshot") or {}
        compare_keys = [
            "log_count",
            "adherence_percent",
            "recovery_score",
            "sleep_quality",
            "stress_score",
            "injury_risk",
            "weight_change_kg_7d",
            "weight_change_kg_14d",
            "weight_change_kg_28d",
            "latest_journal_sentiment",
            "target_calories",
            "current_weight_kg",
        ]
        for k in compare_keys:
            v_old = latest_snap.get(k)
            v_new = input_snapshot.get(k)
            if v_old is None and v_new is None:
                continue
            if v_old is None or v_new is None:
                return False
            if isinstance(v_old, (int, float)) and isinstance(v_new, (int, float)):
                if abs(float(v_old) - float(v_new)) > 1e-4:
                    return False
            elif v_old != v_new:
                return False

        return True
    except Exception:
        return False


def persist_adaptation_snapshot(
    user_id: str,
    decision: AdaptationDecision,
    user_token: Optional[str] = None,
    profile_repository: Any = ProfileRepository,
    daily_log_repository: Any = DailyLogRepository,
    journal_repository: Any = JournalRepository,
    meal_plan_repository: Any = MealPlanRepository,
    workout_plan_repository: Any = WorkoutPlanRepository,
    adaptation_history_repository: Any = AdaptationHistoryRepository,
) -> Optional[Dict[str, Any]]:
    """
    Constructs an input snapshot and saves the adaptation decision to history if it represents
    a new or changed state. Deduplicates identical repeated evaluations.
    """
    data = collect_adaptation_data(
        user_id=user_id,
        profile_repository=profile_repository,
        daily_log_repository=daily_log_repository,
        user_token=user_token,
        journal_repository=journal_repository,
    )
    profile = ensure_target_metrics(data["profile"])

    active_meal_plan = None
    if meal_plan_repository and hasattr(meal_plan_repository, "get_active_meal_plan"):
        active_meal_plan = meal_plan_repository.get_active_meal_plan(
            user_id=user_id, user_token=user_token
        )

    active_workout_plan = None
    if workout_plan_repository and hasattr(workout_plan_repository, "get_active_workout_plan"):
        active_workout_plan = workout_plan_repository.get_active_workout_plan(
            user_id=user_id, user_token=user_token
        )

    adaptation_input = prepare_adaptation_input(
        profile,
        data["daily_logs"],
        data["journal_entries"],
        active_meal_plan=active_meal_plan,
        active_workout_plan=active_workout_plan,
    )

    active_meal_plan_id = (
        str(active_meal_plan["id"]) if active_meal_plan and active_meal_plan.get("id") else None
    )
    active_workout_plan_id = (
        str(active_workout_plan["id"]) if active_workout_plan and active_workout_plan.get("id") else None
    )

    input_snapshot = {
        "current_weight_kg": adaptation_input.current_weight_kg,
        "target_weight_kg": adaptation_input.target_weight_kg,
        "goal_type": adaptation_input.goal_type,
        "target_calories": adaptation_input.target_calories,
        "target_protein_g": adaptation_input.target_protein_g,
        "target_carbs_g": adaptation_input.target_carbs_g,
        "target_fat_g": adaptation_input.target_fat_g,
        "workout_days_per_week": adaptation_input.workout_days_per_week,
        "experience_level": adaptation_input.experience_level,
        "log_count": adaptation_input.log_count,
        "adherence_percent": adaptation_input.adherence_percent,
        "recovery_score": adaptation_input.recovery_score,
        "sleep_quality": adaptation_input.sleep_quality,
        "stress_score": adaptation_input.stress_score,
        "injury_risk": adaptation_input.injury_risk,
        "plateau_probability": adaptation_input.plateau_probability,
        "nutrition_score": adaptation_input.nutrition_score,
        "training_quality": adaptation_input.training_quality,
        "weight_change_kg_7d": adaptation_input.weight_change_kg_7d,
        "weight_change_kg_14d": adaptation_input.weight_change_kg_14d,
        "weight_change_kg_28d": adaptation_input.weight_change_kg_28d,
        "latest_journal_summary": adaptation_input.latest_journal_summary,
        "latest_journal_sentiment": adaptation_input.latest_journal_sentiment,
        "active_meal_plan_id": active_meal_plan_id,
        "active_workout_plan_id": active_workout_plan_id,
    }

    latest = adaptation_history_repository.get_latest_history(user_id=user_id, user_token=user_token)
    if latest and _is_equivalent_record(
        latest, decision, input_snapshot, active_meal_plan_id, active_workout_plan_id
    ):
        return latest

    record_data = {
        "readiness_factor": float(decision.readiness_factor),
        "high_fatigue_flag": bool(decision.high_fatigue_flag),
        "plateau_detected": bool(decision.plateau_detected),
        "adherence_score": int(decision.adherence_score),
        "recovery_score": int(decision.recovery_score),
        "stress_score": int(decision.stress_score),
        "sleep_quality": int(decision.sleep_quality),
        "injury_risk": int(decision.injury_risk),
        "plateau_probability": int(decision.plateau_probability),
        "diet_adjustment": decision.diet_adjustment.model_dump(mode="json"),
        "workout_adjustment": decision.workout_adjustment.model_dump(mode="json"),
        "actionable_recommendations": list(decision.actionable_recommendations),
        "coaching_summary": str(decision.coaching_summary),
        "objective_data_available": bool(decision.objective_data_available),
        "active_meal_plan_id": active_meal_plan_id,
        "active_workout_plan_id": active_workout_plan_id,
        "input_snapshot": input_snapshot,
    }

    return adaptation_history_repository.save_history(
        user_id=user_id,
        record_data=record_data,
        user_token=user_token,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=AdaptationDecision)
def get_user_adaptation(
    user_ctx: UserContext = Depends(get_current_user),
) -> AdaptationDecision:
    """
    Computes and returns the personalized AI adaptation decision for the authenticated user.
    Forwards JWT token for Supabase Row Level Security (RLS) across all repository queries.
    Persists decision snapshot to history if inputs/decisions have changed (deduplicated).
    """
    try:
        decision = compute_adaptation_for_user(
            user_id=user_ctx.user_id,
            user_token=user_ctx.access_token,
        )
    except ValueError as e:
        err_msg = str(e)
        if "Profile not found" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        # Any other ValueError (e.g. "Cannot compute target metrics; profile is missing...")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_msg,
        )

    # Persist decision snapshot in history (deduplicated; non-blocking on persistence failures)
    try:
        persist_adaptation_snapshot(
            user_id=user_ctx.user_id,
            decision=decision,
            user_token=user_ctx.access_token,
        )
    except Exception:
        pass

    return decision


@router.get("/history", response_model=AdaptationHistoryListResponse)
def get_user_adaptation_history(
    limit: int = Query(30, ge=1, le=100, description="Max history records to return"),
    user_ctx: UserContext = Depends(get_current_user),
) -> AdaptationHistoryListResponse:
    """
    Returns the authenticated user's adaptation decision history ordered newest first.
    Forwards Bearer JWT to Supabase for RLS enforcement.
    """
    records = AdaptationHistoryRepository.get_history(
        user_id=user_ctx.user_id,
        user_token=user_ctx.access_token,
        limit=limit,
    )
    return AdaptationHistoryListResponse(
        history=[AdaptationHistoryRecord.from_db_row(r) for r in records],
        count=len(records),
    )
