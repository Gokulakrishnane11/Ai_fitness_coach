"""
User Profile API Module.
Handles user onboarding biometrics, profile queries, and updates.
Calculates target metrics automatically upon profile creation/update.
"""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user, UserContext
from app.db.supabase import ProfileRepository
from app.engine.bmr_tdee import calculate_target_metrics

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileCreateUpdateSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    gender: str = Field(..., pattern="^(male|female|other)$")
    age: int = Field(..., ge=13, le=100)
    height_cm: float = Field(..., ge=100.0, le=250.0)
    weight_kg: float = Field(..., ge=30.0, le=300.0)
    target_weight_kg: float = Field(..., ge=30.0, le=300.0)
    body_fat_pct: Optional[float] = Field(None, ge=3.0, le=60.0)
    activity_level: str = Field(
        ..., pattern="^(sedentary|lightly_active|moderately_active|very_active|extra_active)$"
    )
    goal_type: str = Field(
        ..., pattern="^(fat_loss|muscle_gain|weight_gain|recomposition)$"
    )
    dietary_preference: str = Field(
        "anything", pattern="^(anything|vegetarian|vegan|keto|paleo)$"
    )
    workout_days_per_week: int = Field(4, ge=1, le=7)
    experience_level: str = Field(
        "beginner", pattern="^(beginner|intermediate|advanced)$"
    )


class ProfileResponseSchema(ProfileCreateUpdateSchema):
    id: str
    target_metrics: dict


@router.get("", response_model=ProfileResponseSchema)
def get_user_profile(user_ctx: UserContext = Depends(get_current_user)):
    """Fetches authenticated user profile forwarding JWT token for RLS policies."""
    profile = ProfileRepository.get_profile(user_ctx.user_id, user_ctx.access_token)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this user. Please complete onboarding.",
        )
    return profile


@router.post("", response_model=ProfileResponseSchema, status_code=status.HTTP_201_CREATED)
def create_or_update_profile(
    payload: ProfileCreateUpdateSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Creates or updates user profile forwarding JWT token for RLS policies."""
    target_metrics = calculate_target_metrics(
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        age=payload.age,
        gender=payload.gender,
        activity_level=payload.activity_level,
        goal_type=payload.goal_type,
        body_fat_pct=payload.body_fat_pct,
    )

    profile_dict = payload.model_dump()
    profile_dict["target_metrics"] = target_metrics

    saved_profile = ProfileRepository.upsert_profile(user_ctx.user_id, profile_dict, user_ctx.access_token)
    return saved_profile
