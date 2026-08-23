"""
FastAPI Complete V1 API Integration Test Suite.
Tests Planning, Simulation, Progress Tracking, and AI Coaching endpoints.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)
auth_headers = {"Authorization": "Bearer test_token_user_full_123"}


def test_meal_plan_api():
    payload = {
        "target_calories": 2100,
        "target_protein_g": 160.0,
        "target_carbs_g": 210.0,
        "target_fat_g": 60.0,
        "dietary_preference": "vegetarian"
    }
    res = client.post("/api/v1/planning/meal-plan", json=payload, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["target_calories"] == 2100
    assert len(body["meals"]) == 4


def test_workout_plan_api():
    payload = {
        "goal_type": "fat_loss",
        "workout_days_per_week": 4,
        "experience_level": "intermediate"
    }
    res = client.post("/api/v1/planning/workout-plan", json=payload, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["split_type"] == "UPPER_LOWER"
    assert len(body["routine"]) == 2


def test_simulation_predict_api():
    payload = {
        "start_weight_kg": 82.0,
        "target_weight_kg": 74.0,
        "height_cm": 176.0,
        "age": 24,
        "gender": "male",
        "activity_level": "moderately_active",
        "daily_caloric_deficit_surplus": -500,
        "adherence_pct": 90.0,
        "duration_weeks": 12
    }
    res = client.post("/api/v1/simulation/predict", json=payload, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == "user_full_123"
    assert len(body["weekly_series"]) == 13
    assert body["weekly_series"][12]["weight_kg"] < 82.0


def test_daily_logs_api():
    log_data = {
        "log_date": "2026-08-10",
        "weight_kg": 81.5,
        "calories_consumed": 2050,
        "protein_consumed_g": 155,
        "workout_completed": True,
        "energy_rating": 8
    }
    # Submit log
    post_res = client.post("/api/v1/progress/logs", json=log_data, headers=auth_headers)
    assert post_res.status_code == 201

    # Fetch logs
    get_res = client.get("/api/v1/progress/logs", headers=auth_headers)
    assert get_res.status_code == 200
    logs_body = get_res.json()
    assert logs_body["count"] > 0
    assert logs_body["logs"][0]["weight_kg"] == 81.5


def test_coaching_journal_api():
    payload = {
        "entry_text": "Had a fantastic workout today, smashed my personal record on squat!"
    }
    res = client.post("/api/v1/coaching/journal", json=payload, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["feedback"]["sentiment_tag"] == "motivated"
    assert len(body["feedback"]["actionable_tips"]) > 0
