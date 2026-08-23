"""
Daily Tracking & Progress Dashboard API Module (Phase 6).
Handles daily weight, calorie, and workout log logging and history queries.
"""

from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, UserContext
from app.db.supabase import DailyLogRepository

router = APIRouter(prefix="/progress", tags=["Progress"])


class DailyLogCreateSchema(BaseModel):
    log_date: date
    weight_kg: Optional[float] = Field(None, ge=30.0, le=300.0)
    calories_consumed: Optional[int] = Field(None, ge=500, le=8000)
    protein_consumed_g: Optional[int] = Field(None, ge=0, le=400)
    carbs_consumed_g: Optional[int] = Field(None, ge=0, le=800)
    fat_consumed_g: Optional[int] = Field(None, ge=0, le=300)
    water_liters: Optional[float] = Field(None, ge=0.0, le=10.0)
    workout_completed: bool = False
    energy_rating: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=500)


@router.get("/logs")
def get_daily_logs(user_ctx: UserContext = Depends(get_current_user)):
    """Retrieves user daily tracking logs forwarding JWT token for RLS policies."""
    logs = DailyLogRepository.get_logs(user_ctx.user_id, user_ctx.access_token)
    return {"logs": logs, "count": len(logs)}


@router.post("/logs", status_code=status.HTTP_201_CREATED)
def submit_daily_log(
    payload: DailyLogCreateSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Submits or updates a daily tracking log forwarding JWT token for RLS policies."""
    log_dict = payload.model_dump(mode="json")
    saved_log = DailyLogRepository.add_log(user_ctx.user_id, log_dict, user_ctx.access_token)
    return saved_log
