"""
Unit & Integration Test Suite for Auth Security & Test-Token Bypass Guard.
Tests:
1. test_token_ is accepted when TESTING=True.
2. test_token_ is rejected with HTTP 401 when TESTING=False.
3. Valid Supabase JWT (ES256 / JWKS) is accepted.
4. Invalid JWT is rejected with HTTP 401.
"""

import sys
import os
import time
import pytest
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import ec
import jwt
from jwt import PyJWKClientError
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core import security
from app.core.config import settings
from app.db import supabase as db_mod

client = TestClient(app)

# Local ephemeral ES256 key pair for offline test verification
TEST_EC_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
TEST_EC_PUBLIC_KEY = TEST_EC_PRIVATE_KEY.public_key()
TEST_WRONG_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
TEST_KID = "test-mock-auth-kid-2026"


class MockSigningKey:
    def __init__(self, key):
        self.key = key


def mock_get_signing_key_from_jwt(token: str):
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        raise PyJWKClientError("Invalid token header")
    if header.get("kid") == TEST_KID:
        return MockSigningKey(TEST_EC_PUBLIC_KEY)
    raise PyJWKClientError(f"No key found for kid {header.get('kid')}")


@pytest.fixture(autouse=True)
def mock_jwks_and_offline_db():
    """Mock JWKS key resolution and enforce offline database mode for deterministic auth tests."""
    with patch.object(security.jwks_client, "get_signing_key_from_jwt", side_effect=mock_get_signing_key_from_jwt):
        with patch.object(db_mod, "IS_LIVE_SUPABASE_ENABLED", False):
            yield


def mint_test_jwt(sub: str, key=TEST_EC_PRIVATE_KEY, expired: bool = False, kid: str = TEST_KID) -> str:
    """Helper to mint an ES256 signed test JWT for verification tests."""
    now = int(time.time())
    exp = now - 60 if expired else now + 3600
    payload = {
        "sub": sub,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": exp,
        "iat": now - 100,
    }
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid})


def test_token_accepted_in_testing_mode():
    """Verify test_token_ is accepted when settings.TESTING is True."""
    settings.TESTING = True
    headers = {"Authorization": "Bearer test_token_user_valid_123"}
    # Call protected endpoint
    response = client.get("/api/v1/profile", headers=headers)
    # Status should not be 401 (it may be 404 if profile not in DB yet, but auth succeeded)
    assert response.status_code != 401
    assert response.status_code in (200, 404)


def test_token_rejected_outside_testing_mode():
    """Verify test_token_ is rejected with HTTP 401 when settings.TESTING is False."""
    settings.TESTING = False
    try:
        headers = {"Authorization": "Bearer test_token_user_hacker_456"}
        response = client.get("/api/v1/profile", headers=headers)
        assert response.status_code == 401
        assert "Test tokens are not allowed in this environment" in response.json()["detail"]
    finally:
        # Restore testing mode for subsequent tests
        settings.TESTING = True


def test_valid_supabase_jwt_accepted():
    """Verify a cryptographically valid Supabase JWT is accepted regardless of testing mode."""
    # Test both with TESTING=False and TESTING=True
    for mode in [False, True]:
        settings.TESTING = mode
        valid_jwt = mint_test_jwt("38d99528-8d99-47df-b915-a0e5b0ec08e8", TEST_EC_PRIVATE_KEY)
        headers = {"Authorization": f"Bearer {valid_jwt}"}
        response = client.get("/api/v1/profile", headers=headers)
        # Authentication must pass (not 401)
        assert response.status_code != 401, f"Failed in mode TESTING={mode}: {response.text}"
        assert response.status_code in (200, 404)


def test_invalid_jwt_rejected():
    """Verify malformed and invalid signature JWTs are rejected with HTTP 401."""
    # 1. Completely malformed token
    headers_malformed = {"Authorization": "Bearer not_a_valid_jwt_token_string"}
    res_malformed = client.get("/api/v1/profile", headers=headers_malformed)
    assert res_malformed.status_code == 401
    assert "Invalid authentication token" in res_malformed.json()["detail"]

    # 2. Token signed with wrong secret key
    tampered_jwt = mint_test_jwt("attacker_uuid", TEST_WRONG_PRIVATE_KEY)
    headers_tampered = {"Authorization": f"Bearer {tampered_jwt}"}
    res_tampered = client.get("/api/v1/profile", headers=headers_tampered)
    assert res_tampered.status_code == 401
    assert "Invalid authentication token" in res_tampered.json()["detail"]

    # 3. Expired token
    expired_jwt = mint_test_jwt("expired_uuid", TEST_EC_PRIVATE_KEY, expired=True)
    headers_expired = {"Authorization": f"Bearer {expired_jwt}"}
    res_expired = client.get("/api/v1/profile", headers=headers_expired)
    assert res_expired.status_code == 401
    assert "Token has expired" in res_expired.json()["detail"]

    # 4. Unknown key ID (kid)
    unknown_kid_jwt = mint_test_jwt("unknown_kid_uuid", TEST_EC_PRIVATE_KEY, kid="unknown-kid")
    headers_unknown = {"Authorization": f"Bearer {unknown_kid_jwt}"}
    res_unknown = client.get("/api/v1/profile", headers=headers_unknown)
    assert res_unknown.status_code == 401
    assert "Invalid authentication token" in res_unknown.json()["detail"]
