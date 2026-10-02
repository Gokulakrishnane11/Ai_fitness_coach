from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user, UserContext
from app.db.supabase import (
    ProfileRepository,
    MealPlanRepository,
    WorkoutPlanRepository,
    AdaptationHistoryRepository,
)
from app.engine.adaptation import (
    AdaptationDecision,
    compute_adaptation_for_user,
    ensure_target_metrics,
    DietAdjustment,
    WorkoutAdjustment,
)
from app.engine.nutrition_rules import generate_deterministic_meal_plan
from app.engine.workout_rules import generate_deterministic_workout_plan
from app.modules.adaptation import persist_adaptation_snapshot

router = APIRouter(prefix="/planning", tags=["Planning"])


class MealPlanRequestSchema(BaseModel):
    target_calories: int = Field(..., ge=1000, le=5000)
    target_protein_g: float = Field(..., ge=30.0, le=300.0)
    target_carbs_g: float = Field(..., ge=20.0, le=600.0)
    target_fat_g: float = Field(..., ge=15.0, le=200.0)
    dietary_preference: str = Field("anything", pattern="^(anything|vegetarian|vegan|keto|paleo)$")
    apply_adaptation: bool = Field(True, description="Whether to apply active adaptation adjustments if available")


class WorkoutPlanRequestSchema(BaseModel):
    goal_type: str = Field(..., pattern="^(fat_loss|muscle_gain|weight_gain|recomposition)$")
    workout_days_per_week: int = Field(4, ge=1, le=7)
    experience_level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    apply_adaptation: bool = Field(True, description="Whether to apply active adaptation adjustments if available")


class ApplyAdaptationRequestSchema(BaseModel):
    force_apply: bool = Field(False, description="Whether to force plan regeneration even if already applied")


class ApplyAdaptationResponseSchema(BaseModel):
    status: str = Field(..., description="'applied' or 'already_applied'")
    applied: bool = Field(..., description="True if new plans were generated and persisted, False if already up to date")
    message: str
    decision: AdaptationDecision
    meal_plan: Dict[str, Any]
    workout_plan: Dict[str, Any]
    active_meal_plan_id: Optional[str] = Field(None, description="Active meal plan ID")
    active_workout_plan_id: Optional[str] = Field(None, description="Active workout plan ID")


def _has_diet_adjustment(adj: DietAdjustment) -> bool:
    """Checks whether the adaptation contains any non-zero diet adjustment."""
    return (
        adj.calorie_delta != 0
        or adj.protein_delta_g != 0.0
        or adj.carb_delta_g != 0.0
        or adj.fat_delta_g != 0.0
    )


def _has_workout_adjustment(adj: WorkoutAdjustment) -> bool:
    """Checks whether the adaptation contains any active workout stimulus or schedule change."""
    return (
        adj.intensity != "maintain"
        or adj.volume not in ("medium", "maintain")
        or adj.recovery_days > 0
        or adj.cardio_minutes > 0
        or bool(adj.deload_recommended)
    )


@router.post("/meal-plan")
def create_meal_plan(
    payload: MealPlanRequestSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Generates a deterministic 4-meal daily plan matching macro targets, applying user adaptation if active, and persists as active plan."""
    diet_adjustment: Optional[DietAdjustment] = None
    if payload.apply_adaptation and user_ctx and user_ctx.user_id:
        try:
            profile = ProfileRepository.get_profile(user_ctx.user_id, user_ctx.access_token)
            if profile:
                decision = compute_adaptation_for_user(
                    user_id=user_ctx.user_id,
                    user_token=user_ctx.access_token,
                )
                diet_adjustment = decision.diet_adjustment
        except (ValueError, KeyError):
            diet_adjustment = None

    plan = generate_deterministic_meal_plan(
        target_calories=payload.target_calories,
        target_protein_g=payload.target_protein_g,
        target_carbs_g=payload.target_carbs_g,
        target_fat_g=payload.target_fat_g,
        dietary_preference=payload.dietary_preference,
        diet_adjustment=diet_adjustment,
    )

    if user_ctx and user_ctx.user_id:
        MealPlanRepository.save_meal_plan(
            user_id=user_ctx.user_id,
            plan_data=plan,
            user_token=user_ctx.access_token,
        )

    return plan


@router.get("/active-meal-plan")
def get_active_meal_plan(
    user_ctx: UserContext = Depends(get_current_user),
):
    """Retrieves the user's currently active meal plan, or None if none is active."""
    if not user_ctx or not user_ctx.user_id:
        return None
    return MealPlanRepository.get_active_meal_plan(
        user_id=user_ctx.user_id,
        user_token=user_ctx.access_token,
    )


@router.post("/workout-plan")
def create_workout_plan(
    payload: WorkoutPlanRequestSchema, user_ctx: UserContext = Depends(get_current_user)
):
    """Generates a deterministic structured workout routine based on split rules, applying user adaptation if active, and persists as active plan."""
    workout_adjustment: Optional[WorkoutAdjustment] = None
    if payload.apply_adaptation and user_ctx and user_ctx.user_id:
        try:
            profile = ProfileRepository.get_profile(user_ctx.user_id, user_ctx.access_token)
            if profile:
                decision = compute_adaptation_for_user(
                    user_id=user_ctx.user_id,
                    user_token=user_ctx.access_token,
                )
                workout_adjustment = decision.workout_adjustment
        except (ValueError, KeyError):
            workout_adjustment = None

    plan = generate_deterministic_workout_plan(
        goal_type=payload.goal_type,
        workout_days_per_week=payload.workout_days_per_week,
        experience_level=payload.experience_level,
        workout_adjustment=workout_adjustment,
    )

    if user_ctx and user_ctx.user_id:
        WorkoutPlanRepository.save_workout_plan(
            user_id=user_ctx.user_id,
            plan_data=plan,
            user_token=user_ctx.access_token,
        )

    return plan


@router.get("/active-workout-plan")
def get_active_workout_plan(
    user_ctx: UserContext = Depends(get_current_user),
):
    """Retrieves the user's currently active workout plan, or None if none is active."""
    if not user_ctx or not user_ctx.user_id:
        return None
    return WorkoutPlanRepository.get_active_workout_plan(
        user_id=user_ctx.user_id,
        user_token=user_ctx.access_token,
    )


@router.post("/apply-adaptation", response_model=ApplyAdaptationResponseSchema)
def apply_adaptation_to_plans(
    payload: Optional[ApplyAdaptationRequestSchema] = None,
    user_ctx: UserContext = Depends(get_current_user),
) -> ApplyAdaptationResponseSchema:
    """
    Applies the current adaptation decision to active meal and workout plans idempotently.
    1. Resolves user profile and target metrics (HTTP 404 if missing, 422 if incomplete).
    2. Computes the latest adaptation decision via the deterministic adaptation engine.
    3. Verifies whether active plans are already aligned with this exact decision (idempotency).
    4. If not aligned (or force_apply=True):
       - Generates adapted meal plan via nutrition planning engine + DietAdjustment.
       - Generates adapted workout plan via workout planning engine + WorkoutAdjustment.
       - Persists new meal plan as active and archives previous active meal plans.
       - Persists new workout plan as active and archives previous active workout plans.
       - Persists adaptation decision snapshot linking new active plan IDs to audit history.
    5. Returns status, decision, and newly active plans.
    """
    if not user_ctx or not user_ctx.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    profile = ProfileRepository.get_profile(user_ctx.user_id, user_ctx.access_token)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for user {user_ctx.user_id}",
        )

    try:
        resolved_profile = ensure_target_metrics(profile)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    try:
        decision = compute_adaptation_for_user(
            user_id=user_ctx.user_id,
            user_token=user_ctx.access_token,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    force = payload.force_apply if payload else False

    # Check existing active plans
    active_meal = MealPlanRepository.get_active_meal_plan(user_ctx.user_id, user_ctx.access_token)
    active_workout = WorkoutPlanRepository.get_active_workout_plan(user_ctx.user_id, user_ctx.access_token)
    latest_history = AdaptationHistoryRepository.get_latest_history(user_ctx.user_id, user_ctx.access_token)

    # Idempotency check: verify if the current decision was already applied to active plans
    if not force and active_meal and active_workout and latest_history:
        same_meal_id = str(latest_history.get("active_meal_plan_id") or "") == str(active_meal.get("id") or "")
        same_workout_id = str(latest_history.get("active_workout_plan_id") or "") == str(active_workout.get("id") or "")
        same_diet_adj = (latest_history.get("diet_adjustment") or {}) == decision.diet_adjustment.model_dump(mode="json")
        same_workout_adj = (latest_history.get("workout_adjustment") or {}) == decision.workout_adjustment.model_dump(mode="json")
        same_fatigue = bool(latest_history.get("high_fatigue_flag")) == bool(decision.high_fatigue_flag)
        same_plateau = bool(latest_history.get("plateau_detected")) == bool(decision.plateau_detected)

        if same_meal_id and same_workout_id and same_diet_adj and same_workout_adj and same_fatigue and same_plateau:
            meal_data = active_meal.get("plan_data") if isinstance(active_meal.get("plan_data"), dict) else active_meal
            workout_data = active_workout.get("routine_data") if isinstance(active_workout.get("routine_data"), dict) else active_workout
            return ApplyAdaptationResponseSchema(
                status="already_applied",
                applied=False,
                message="Adaptation decision is already applied to current active plans.",
                decision=decision,
                meal_plan=meal_data,
                workout_plan=workout_data,
                active_meal_plan_id=str(active_meal.get("id")) if active_meal.get("id") else None,
                active_workout_plan_id=str(active_workout.get("id")) if active_workout.get("id") else None,
            )

    has_diet_adj = _has_diet_adjustment(decision.diet_adjustment)
    has_workout_adj = _has_workout_adjustment(decision.workout_adjustment)

    need_meal_gen = force or (active_meal is None) or has_diet_adj
    need_workout_gen = force or (active_workout is None) or has_workout_adj

    # No-op check: if both active plans already exist and neither adjustment is required (and not force)
    if not need_meal_gen and not need_workout_gen:
        meal_data = active_meal.get("plan_data") if isinstance(active_meal.get("plan_data"), dict) else active_meal
        workout_data = active_workout.get("routine_data") if isinstance(active_workout.get("routine_data"), dict) else active_workout
        try:
            persist_adaptation_snapshot(
                user_id=user_ctx.user_id,
                decision=decision,
                user_token=user_ctx.access_token,
            )
        except Exception:
            pass
        return ApplyAdaptationResponseSchema(
            status="already_applied",
            applied=False,
            message="No adaptation adjustments required; active plans maintained.",
            decision=decision,
            meal_plan=meal_data,
            workout_plan=workout_data,
            active_meal_plan_id=str(active_meal.get("id")) if active_meal.get("id") else None,
            active_workout_plan_id=str(active_workout.get("id")) if active_workout.get("id") else None,
        )

    # Meal Plan Generation if needed
    if need_meal_gen:
        tm = resolved_profile.get("target_metrics") or {}
        target_cal = int(round(float(tm.get("target_calories", 2000))))
        target_p = float(tm.get("protein_g", 150.0))
        target_c = float(tm.get("carbs_g", 200.0))
        target_f = float(tm.get("fat_g", 65.0))
        diet_pref = str(profile.get("dietary_preference") or "anything")

        new_meal_plan = generate_deterministic_meal_plan(
            target_calories=target_cal,
            target_protein_g=target_p,
            target_carbs_g=target_c,
            target_fat_g=target_f,
            dietary_preference=diet_pref,
            diet_adjustment=decision.diet_adjustment,
        )
        saved_meal = MealPlanRepository.save_meal_plan(
            user_id=user_ctx.user_id,
            plan_data=new_meal_plan,
            user_token=user_ctx.access_token,
        )
        saved_meal_id = str(saved_meal.get("id")) if saved_meal and saved_meal.get("id") else None
        meal_plan_to_return = new_meal_plan
        if saved_meal_id:
            meal_plan_to_return["id"] = saved_meal_id
    else:
        saved_meal_id = str(active_meal.get("id")) if active_meal and active_meal.get("id") else None
        meal_plan_to_return = active_meal.get("plan_data") if isinstance(active_meal.get("plan_data"), dict) else active_meal

    # Workout Plan Generation if needed
    if need_workout_gen:
        goal_type = str(profile.get("goal_type") or "fat_loss")
        workout_days = int(profile.get("workout_days_per_week") or 4)
        exp_level = str(profile.get("experience_level") or "beginner")

        new_workout_plan = generate_deterministic_workout_plan(
            goal_type=goal_type,
            workout_days_per_week=workout_days,
            experience_level=exp_level,
            workout_adjustment=decision.workout_adjustment,
        )
        saved_workout = WorkoutPlanRepository.save_workout_plan(
            user_id=user_ctx.user_id,
            plan_data=new_workout_plan,
            user_token=user_ctx.access_token,
        )
        saved_workout_id = str(saved_workout.get("id")) if saved_workout and saved_workout.get("id") else None
        workout_plan_to_return = new_workout_plan
        if saved_workout_id:
            workout_plan_to_return["id"] = saved_workout_id
    else:
        saved_workout_id = str(active_workout.get("id")) if active_workout and active_workout.get("id") else None
        workout_plan_to_return = active_workout.get("routine_data") if isinstance(active_workout.get("routine_data"), dict) else active_workout

    # Persist snapshot linking active plan IDs to audit history
    try:
        persist_adaptation_snapshot(
            user_id=user_ctx.user_id,
            decision=decision,
            user_token=user_ctx.access_token,
        )
    except Exception:
        pass

    return ApplyAdaptationResponseSchema(
        status="applied",
        applied=True,
        message="Adaptation successfully applied to active meal and workout plans.",
        decision=decision,
        meal_plan=meal_plan_to_return,
        workout_plan=workout_plan_to_return,
        active_meal_plan_id=saved_meal_id,
        active_workout_plan_id=saved_workout_id,
    )
