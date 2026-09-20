"""
FastAPI Security & Supabase JWT Auth Middleware Dependency.
Extracts and validates Supabase JWT Bearer tokens to protect API endpoints
and provides UserContext containing user_id and access_token for RLS forwarding.
"""

from typing import Dict, Any, Optional
import jwt
from jwt import PyJWKClient, PyJWKError, PyJWKClientError
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)

jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url)


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

    # Test token bypass for automated integration testing (ONLY allowed when TESTING=True)
    if token.startswith("test_token_"):
        if not settings.TESTING:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Test tokens are not allowed in this environment",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = token.replace("test_token_", "")
        return UserContext(user_id=user_id, access_token=token)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
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
    except (jwt.InvalidTokenError, PyJWKError, PyJWKClientError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(user_ctx: UserContext = Depends(verify_supabase_jwt)) -> UserContext:
    """Dependency returning authenticated UserContext (user_id & access_token)."""
    return user_ctx
