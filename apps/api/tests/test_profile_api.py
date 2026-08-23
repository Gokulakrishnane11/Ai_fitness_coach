"""
FastAPI Integration Test Suite for Auth Middleware and Profile API (Phase 2 Verification).
Tests JWT security guards, onboarding profile creation, and metric computations.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_profile_unauthorized_without_token():
    response = client.get("/api/v1/profile")
    assert response.status_code == 401
    assert "Missing authorization Bearer token" in response.json()["detail"]


def test_profile_unauthorized_invalid_token():
    headers = {"Authorization": "Bearer invalid_token_xyz"}
    response = client.get("/api/v1/profile", headers=headers)
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_create_and_get_profile_success():
    headers = {"Authorization": "Bearer test_token_user_123"}

    profile_data = {
        "first_name": "Gokul",
        "gender": "male",
        "age": 22,
        "height_cm": 178.0,
        "weight_kg": 75.0,
        "target_weight_kg": 70.0,
        "body_fat_pct": 18.0,
        "activity_level": "moderately_active",
        "goal_type": "fat_loss",
        "dietary_preference": "vegetarian",
        "workout_days_per_week": 4,
        "experience_level": "intermediate",
    }

    # Create profile via POST /api/v1/profile
    post_res = client.post("/api/v1/profile", json=profile_data, headers=headers)
    assert post_res.status_code == 201, post_res.text
    created = post_res.json()
    assert created["id"] == "user_123"
    assert created["first_name"] == "Gokul"
    assert "target_metrics" in created
    assert created["target_metrics"]["bmr"] > 1000.0
    assert created["target_metrics"]["target_calories"] > 1200

    # Fetch profile via GET /api/v1/profile
    get_res = client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == "user_123"
    assert fetched["goal_type"] == "fat_loss"
