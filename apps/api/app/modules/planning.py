"""
Nutrition & Workout Planning API Module (Phase 4).
Exposes deterministic meal planning and workout routine generation endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, UserContext
from app.engine.nutrition_rules import generate_deterministic_meal_plan
from app.engine.workout_rules import generate_deterministic_workout_plan

router = APIRouter(prefix="/planning", tags=["Planning"])


class MealPlanRequestSchema(BaseModel):
    target_calories: int = Field(..., ge=1000, le=5000)
    target_protein_g: float = Field(..., ge=30.0, le=300.0)
    target_carbs_g: float = Field(..., ge=20.0, le=600.0)
    target_fat_g: float = Field(..., ge=15.0, le=200.0)
    dietary_preference: str = Field("anything", pattern="^(anything|vegetarian|vegan|keto|paleo)$")


class WorkoutPlanRequestSchema(BaseModel):
    goal_type: str = Field(..., pattern="^(fat_loss|muscle_gain|weight_gain|recomposition)$")
    workout_days_per_week: int = Field(4, ge=1, le=7)
    experience_level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")


@router.post("/meal-plan")
def create_meal_plan(
    payload: MealPlanRequestSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Generates a deterministic 4-meal daily plan matching macro targets."""
    return generate_deterministic_meal_plan(
        target_calories=payload.target_calories,
        target_protein_g=payload.target_protein_g,
        target_carbs_g=payload.target_carbs_g,
        target_fat_g=payload.target_fat_g,
        dietary_preference=payload.dietary_preference,
    )


@router.post("/workout-plan")
def create_workout_plan(
    payload: WorkoutPlanRequestSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Generates a deterministic structured workout routine based on split rules."""
    return generate_deterministic_workout_plan(
        goal_type=payload.goal_type,
        workout_days_per_week=payload.workout_days_per_week,
        experience_level=payload.experience_level,
    )
