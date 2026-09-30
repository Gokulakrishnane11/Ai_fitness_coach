"""
Phase 4C: Frontend Contract & Wellness Telemetry Integration Test Suite.
Verifies the exact payload contract sent by the frontend Daily Progress Tracker:
- Default/optional behavior (no telemetry submitted)
- Full telemetry submission (recovery_score, sleep_quality, stress_level, muscle_soreness)
- Boundary values (0 and 100 accepted)
- Invalid values (< 0, > 100 rejected with HTTP 422)
- Existing fields (weight, calories, macros, water, workout, energy, notes) preserved
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings

client = TestClient(app)

TEST_USER = "user_phase4c_contract_test"
AUTH_HEADER = {"Authorization": f"Bearer test_token_{TEST_USER}"}


@pytest.fixture(autouse=True)
def enable_testing_mode():
    orig_testing = settings.TESTING
    settings.TESTING = True
    yield
    settings.TESTING = orig_testing


def test_optional_behavior_submitting_without_telemetry():
    """Verify daily logs can be submitted without any wellness telemetry (backward compatibility)."""
    payload = {
        "log_date": "2026-10-01",
        "weight_kg": 75.5,
        "calories_consumed": 2100,
        "protein_consumed_g": 160,
        "carbs_consumed_g": 240,
        "fat_consumed_g": 65,
        "water_liters": 3.0,
        "workout_completed": True,
        "energy_rating": 8,
        "notes": "Standard progress entry without telemetry",
    }
    res = client.post("/api/v1/progress/logs", json=payload, headers=AUTH_HEADER)
    assert res.status_code == 201
    data = res.json()
    assert data["log_date"] == "2026-10-01"
    assert data["weight_kg"] == 75.5
    assert data.get("recovery_score") is None
    assert data.get("sleep_quality") is None
    assert data.get("stress_level") is None
    assert data.get("muscle_soreness") is None


def test_telemetry_submission_all_four_fields():
    """Verify submitting all four telemetry fields matches the frontend payload contract."""
    payload = {
        "log_date": "2026-10-02",
        "weight_kg": 75.2,
        "calories_consumed": 2200,
        "protein_consumed_g": 165,
        "carbs_consumed_g": 250,
        "fat_consumed_g": 70,
        "water_liters": 3.2,
        "workout_completed": True,
        "energy_rating": 9,
        "notes": "Great day with full wellness telemetry",
        "recovery_score": 85,
        "sleep_quality": 90,
        "stress_level": 20,
        "muscle_soreness": 15,
    }
    res = client.post("/api/v1/progress/logs", json=payload, headers=AUTH_HEADER)
    assert res.status_code == 201
    data = res.json()
    assert data["recovery_score"] == 85
    assert data["sleep_quality"] == 90
    assert data["stress_level"] == 20
    assert data["muscle_soreness"] == 15


def test_boundary_values_zero_and_hundred():
    """Verify boundary values 0 and 100 are strictly accepted."""
    # Boundary 0
    payload_zero = {
        "log_date": "2026-10-03",
        "recovery_score": 0,
        "sleep_quality": 0,
        "stress_level": 0,
        "muscle_soreness": 0,
    }
    res_zero = client.post("/api/v1/progress/logs", json=payload_zero, headers=AUTH_HEADER)
    assert res_zero.status_code == 201
    data_zero = res_zero.json()
    assert data_zero["recovery_score"] == 0
    assert data_zero["sleep_quality"] == 0
    assert data_zero["stress_level"] == 0
    assert data_zero["muscle_soreness"] == 0

    # Boundary 100
    payload_hundred = {
        "log_date": "2026-10-04",
        "recovery_score": 100,
        "sleep_quality": 100,
        "stress_level": 100,
        "muscle_soreness": 100,
    }
    res_hundred = client.post("/api/v1/progress/logs", json=payload_hundred, headers=AUTH_HEADER)
    assert res_hundred.status_code == 201
    data_hundred = res_hundred.json()
    assert data_hundred["recovery_score"] == 100
    assert data_hundred["sleep_quality"] == 100
    assert data_hundred["stress_level"] == 100
    assert data_hundred["muscle_soreness"] == 100


def test_invalid_values_rejected_with_422():
    """Verify values < 0 or > 100 are rejected with HTTP 422."""
    # Below 0
    res_neg = client.post(
        "/api/v1/progress/logs",
        json={"log_date": "2026-10-05", "recovery_score": -1},
        headers=AUTH_HEADER,
    )
    assert res_neg.status_code == 422

    # Above 100
    res_high = client.post(
        "/api/v1/progress/logs",
        json={"log_date": "2026-10-05", "sleep_quality": 101},
        headers=AUTH_HEADER,
    )
    assert res_high.status_code == 422

    # Stress level > 100
    res_stress = client.post(
        "/api/v1/progress/logs",
        json={"log_date": "2026-10-05", "stress_level": 150},
        headers=AUTH_HEADER,
    )
    assert res_stress.status_code == 422

    # Muscle soreness < 0
    res_soreness = client.post(
        "/api/v1/progress/logs",
        json={"log_date": "2026-10-05", "muscle_soreness": -10},
        headers=AUTH_HEADER,
    )
    assert res_soreness.status_code == 422


def test_retrieval_and_existing_fields_intact():
    """Verify GET /api/v1/progress/logs returns all existing and new telemetry fields intact."""
    get_res = client.get("/api/v1/progress/logs", headers=AUTH_HEADER)
    assert get_res.status_code == 200
    logs = get_res.json()["logs"]
    assert len(logs) >= 3
    # Check that entries have their expected values
    log_map = {l["log_date"]: l for l in logs}
    assert "2026-10-01" in log_map
    assert log_map["2026-10-01"]["weight_kg"] == 75.5
    assert "2026-10-02" in log_map
    assert log_map["2026-10-02"]["recovery_score"] == 85
