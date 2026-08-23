"""
Transformation Prediction & Predictive Simulation API Module (Phase 5).
Exposes endpoints for deterministic thermodynamics transformation timeline projections
and multi-week simulation series.
"""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, UserContext
from app.engine.transformation import (
    predict_transformation_timeline,
    simulate_multi_week_transformation,
)

router = APIRouter(prefix="/simulation", tags=["Simulation"])


class SimulationRequestSchema(BaseModel):
    start_weight_kg: float = Field(..., ge=30.0, le=300.0)
    target_weight_kg: float = Field(..., ge=30.0, le=300.0)
    height_cm: float = Field(..., ge=100.0, le=250.0)
    age: int = Field(..., ge=13, le=100)
    gender: str = Field(..., pattern="^(male|female|other)$")
    activity_level: str = Field(
        ..., pattern="^(sedentary|lightly_active|moderately_active|very_active|extra_active)$"
    )
    daily_caloric_deficit_surplus: int = Field(..., ge=-1500, le=1500)
    adherence_pct: float = Field(85.0, ge=50.0, le=100.0)
    duration_weeks: int = Field(12, ge=4, le=52)
    body_fat_pct: Optional[float] = Field(None, ge=3.0, le=60.0)


@router.post("/predict")
def run_transformation_simulation(
    payload: SimulationRequestSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Calculates transformation timeline and multi-week weight trajectory series."""
    timeline = predict_transformation_timeline(
        current_weight_kg=payload.start_weight_kg,
        target_weight_kg=payload.target_weight_kg,
        height_cm=payload.height_cm,
        age=payload.age,
        gender=payload.gender,
        activity_level=payload.activity_level,
        daily_caloric_deficit_surplus=payload.daily_caloric_deficit_surplus,
        adherence_pct=payload.adherence_pct,
    )

    simulation_series = simulate_multi_week_transformation(
        start_weight_kg=payload.start_weight_kg,
        height_cm=payload.height_cm,
        age=payload.age,
        gender=payload.gender,
        activity_level=payload.activity_level,
        daily_caloric_deficit_surplus=payload.daily_caloric_deficit_surplus,
        adherence_pct=payload.adherence_pct,
        duration_weeks=payload.duration_weeks,
        body_fat_pct=payload.body_fat_pct,
    )

    return {
        "user_id": user_ctx.user_id,
        "timeline_summary": timeline,
        "weekly_series": simulation_series,
        "methodology": "Validated human energy-balance dynamics (Mifflin-St Jeor & Adaptive Thermogenesis models), bounded by safe biological limits.",
    }
