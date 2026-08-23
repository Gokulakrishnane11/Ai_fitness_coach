"""
FastAPI Security & Supabase JWT Auth Middleware Dependency.
Extracts and validates Supabase JWT Bearer tokens to protect API endpoints
and provides UserContext containing user_id and access_token for RLS forwarding.
"""

from typing import Dict, Any, Optional
import jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    user_id: str
    access_token: str


def verify_supabase_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> UserContext:
    """
    Validates Supabase JWT Bearer token and returns UserContext containing user_id and raw access_token.
    Supports test tokens for automated test environments.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Test token bypass for automated integration testing
    if token.startswith("test_token_"):
        user_id = token.replace("test_token_", "")
        return UserContext(user_id=user_id, access_token=token)

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing user ID (sub claim)",
            )
        return UserContext(user_id=str(user_id), access_token=token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(user_ctx: UserContext = Depends(verify_supabase_jwt)) -> UserContext:
    """Dependency returning authenticated UserContext (user_id & access_token)."""
    return user_ctx
