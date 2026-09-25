"""
AI Adaptation API Module (Phase 8).
Exposes read-only adaptation decision and readiness calculation endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user, UserContext
from app.engine.adaptation import (
    AdaptationDecision,
    compute_adaptation_for_user,
)

router = APIRouter(prefix="/adaptation", tags=["Adaptation"])


@router.get("", response_model=AdaptationDecision)
def get_user_adaptation(
    user_ctx: UserContext = Depends(get_current_user),
) -> AdaptationDecision:
    """
    Computes and returns the personalized AI adaptation decision for the authenticated user.
    Forwards JWT token for Supabase Row Level Security (RLS) across all repository queries.
    """
    try:
        return compute_adaptation_for_user(
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
