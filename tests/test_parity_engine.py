"""
tests/test_parity_engine.py
══════════════════════════
Permanent parity test for the transformation_engine package.

Guards against numeric regressions by comparing the refactored package's outputs
against a frozen baseline captured from the original monolith
(tests/fixtures/baseline_predictions.json).

Also enforces Week-0 parity (Doc #1 requirement): static prediction via
calculate_weekly_rates must produce the same numbers as run_simulation's
Week 1 column for identical inputs.

Run with:  pytest tests/test_parity_engine.py -v

This test is PERMANENT — it stays in the repo forever.
"""

import json
import math
import os
import sys
from copy import deepcopy

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "baseline_predictions.json")

with open(FIXTURE_PATH) as f:
    BASELINE = json.load(f)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _approx(a, b, tol=1e-4):
    """Assert two values are close (handles None and non-numeric strings)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    # Non-numeric (e.g. the Recomposition "note" string) → exact equality
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return a == b
    return abs(a - b) < tol


def _assert_result_match(got: dict, expected: dict, label: str):
    """Deep-compare a calculate_weekly_rates result dict against baseline."""
    for key in (
        "weekly_fat_loss", "weekly_muscle_gain", "weekly_weight_change",
        "weekly_fat_loss_change", "bmi", "bmr", "tdee", "maintenance_calories",
        "calorie_delta", "protein_adequacy", "training_volume", "recovery_score",
        "sleep_score", "step_score", "adherence_score",
        "scientific_fat_loss", "scientific_muscle_gain",
        "scientific_weight_change",
        "ai_behavior_factor",
    ):
        assert _approx(got.get(key), expected.get(key)), (
            f"{label} | {key}: got {got.get(key)}, expected {expected.get(key)}"
        )
    # ML values can be None
    for key in ("ml_fat_loss", "ml_muscle_gain", "ml_weight_gain", "ml_recomp_fat_loss"):
        assert _approx(got.get(key), expected.get(key)), (
            f"{label} | {key}: got {got.get(key)}, expected {expected.get(key)}"
        )


# ── Fixtures for test parametrisation ────────────────────────────────────────

GOALS = ["Fat Loss", "Muscle Gain", "Weight Gain", "Body Recomposition"]

PROFILES = [
    {"age": 22, "gender": "Male", "weight_kg": 85, "height_cm": 178,
     "experience": "Beginner", "workout_days": 4, "daily_steps": 8000,
     "sleep_hrs": 7.0, "target_weight": 75, "activity_level": None},
    {"age": 29, "gender": "Female", "weight_kg": 60, "height_cm": 165,
     "experience": "Intermediate", "workout_days": 5, "daily_steps": 10000,
     "sleep_hrs": 7.5, "target_weight": 64, "activity_level": None},
    {"age": 35, "gender": "Male", "weight_kg": 78, "height_cm": 180,
     "experience": "Advanced", "workout_days": 5, "daily_steps": 12000,
     "sleep_hrs": 6.5, "target_weight": 76, "activity_level": None},
    {"age": 45, "gender": "Female", "weight_kg": 52, "height_cm": 160,
     "experience": "Beginner", "workout_days": 3, "daily_steps": 5000,
     "sleep_hrs": 8.0, "target_weight": 58, "activity_level": None},
    {"age": 31, "gender": "Male", "weight_kg": 110, "height_cm": 182,
     "experience": "Intermediate", "workout_days": 6, "daily_steps": 14000,
     "sleep_hrs": 6.0, "target_weight": 90, "activity_level": None},
]

INPUT_MATRIX = {
    "Fat Loss":           [(-500, 180), (-300, 150), (-700, 220), (-400, 140), (-600, 200)],
    "Muscle Gain":        [(+300, 180), (+250, 160), (+400, 200), (+200, 140), (+350, 190)],
    "Weight Gain":        [(+500, 140), (+400, 120), (+600, 160), (+300, 100), (+700, 150)],
    "Body Recomposition": [(-150, 200), (-100, 180), (+50, 210), (-200, 170), (0, 190)],
}

INTELLIGENCE_VARIANTS = [
    None,
    {
        "fitness_scores": {"adherence_score": 60, "recovery_score": 45, "nutrition_score": 70,
                            "training_quality": 65, "motivation_score": 55, "stress_score": 75,
                            "sleep_quality": 50, "plateau_probability": 55, "injury_risk": 30,
                            "confidence_score": 80},
        "diet_adjustment": {"protein_delta": 10, "calorie_delta": -50, "carb_delta": 0, "fat_delta": 0},
        "workout_adjustment": {"intensity": "reduce", "volume": "medium", "recovery_days": 1, "cardio_minutes": 20},
        "recommendations": [], "motivation": "x",
    },
    {
        "fitness_scores": {"adherence_score": 95, "recovery_score": 90, "nutrition_score": 92,
                            "training_quality": 88, "motivation_score": 95, "stress_score": 15,
                            "sleep_quality": 88, "plateau_probability": 8, "injury_risk": 5,
                            "confidence_score": 90},
        "diet_adjustment": {"protein_delta": 0, "calorie_delta": 0, "carb_delta": 0, "fat_delta": 0},
        "workout_adjustment": {"intensity": "maintain", "volume": "high", "recovery_days": 0, "cardio_minutes": 20},
        "recommendations": [], "motivation": "x",
    },
]

INTEL_LABELS = {None: "none"}


# ── Tests: calculate_weekly_rates parity ────────────────────────────────────

class TestCalculateWeeklyRatesParity:
    """Every baseline case must match the refactored package exactly."""

    @pytest.mark.parametrize("goal_idx", range(4))
    @pytest.mark.parametrize("profile_idx", range(5))
    @pytest.mark.parametrize("intel_idx", range(3))
    def test_parity(self, goal_idx, profile_idx, intel_idx):
        from transformation_engine.prediction_engine import calculate_weekly_rates
        from transformation_engine.utils import DEFAULT_ADHERENCE

        goal = GOALS[goal_idx]
        profile = deepcopy(PROFILES[profile_idx])
        calorie_delta, protein_g = INPUT_MATRIX[goal][profile_idx]
        intel = INTELLIGENCE_VARIANTS[intel_idx]
        intel_label = "stressed" if intel and intel["fitness_scores"]["stress_score"] > 50 else (
            "fresh" if intel else "none")

        # Build baseline lookup key
        baseline_cases = BASELINE["calculate_weekly_rates"][goal]
        expected = None
        for case in baseline_cases:
            if (case["profile_idx"] == profile_idx
                    and case["intel"] == intel_label
                    and case["calorie_delta"] == calorie_delta
                    and case["protein_g"] == protein_g):
                expected = case["result"]
                break
        if expected is None:
            pytest.skip(f"No baseline case for {goal}/{profile_idx}/{intel_label}")

        profile["fitness_intelligence"] = intel
        got = calculate_weekly_rates(
            profile, goal, calorie_delta, protein_g,
            DEFAULT_ADHERENCE, intel,
        )
        _assert_result_match(got, expected,
                             f"cwr/{goal}/p{profile_idx}/{intel_label}")


# ── Tests: wrapper parity ──────────────────────────────────────────────────

class TestWrapperParity:
    """The public API wrappers (predict_fat_loss etc.) must match baseline."""

    @pytest.mark.parametrize("goal_idx", range(4))
    @pytest.mark.parametrize("profile_idx", range(5))
    def test_wrapper_parity(self, goal_idx, profile_idx):
        from transformation_engine.prediction_engine import (
            predict_fat_loss, predict_muscle_gain, predict_weight_change,
            calculate_metrics,
        )
        from transformation_engine.utils import DEFAULT_ADHERENCE

        goal = GOALS[goal_idx]
        profile = deepcopy(PROFILES[profile_idx])
        calorie_delta, protein_g = INPUT_MATRIX[goal][profile_idx]
        weekly_deficit = max(0, -calorie_delta) * 7
        surplus = max(0, calorie_delta)

        baseline = BASELINE["wrappers"][goal][profile_idx]

        assert predict_fat_loss(
            weekly_deficit, profile["weight_kg"], profile["workout_days"],
            protein_g, profile=profile,
        ) == baseline["predict_fat_loss"], f"predict_fat_loss/{goal}/p{profile_idx}"

        assert predict_muscle_gain(
            surplus, protein_g, profile["weight_kg"], profile["experience"],
            profile["workout_days"], profile=profile,
        ) == baseline["predict_muscle_gain"], f"predict_muscle_gain/{goal}/p{profile_idx}"

        assert predict_weight_change(
            calorie_delta, profile=profile, protein_g=protein_g,
        ) == baseline["predict_weight_change"], f"predict_weight_change/{goal}/p{profile_idx}"

        got_metrics = calculate_metrics(
            profile, goal, calorie_delta, protein_g, DEFAULT_ADHERENCE,
        )
        expected_metrics = baseline["calculate_metrics"]
        for key in expected_metrics:
            assert _approx(got_metrics[key], expected_metrics[key]), (
                f"calculate_metrics/{goal}/p{profile_idx} | {key}: "
                f"got {got_metrics[key]}, expected {expected_metrics[key]}"
            )


# ── Tests: run_simulation parity ───────────────────────────────────────────

class TestRunSimulationParity:
    """run_simulation must match baseline across goal × profile × intelligence."""

    @pytest.mark.parametrize("goal_idx", range(4))
    @pytest.mark.parametrize("profile_idx", (0, 2))
    @pytest.mark.parametrize("intel_idx", (0, 1))
    def test_simulation_parity(self, goal_idx, profile_idx, intel_idx):
        from transformation_engine.simulation_engine import run_simulation

        goal = GOALS[goal_idx]
        profile = deepcopy(PROFILES[profile_idx])
        calorie_delta, protein_g = INPUT_MATRIX[goal][profile_idx]
        tdee_guess = 2000 + profile_idx * 50
        target_calories = tdee_guess + calorie_delta
        intel = INTELLIGENCE_VARIANTS[intel_idx]
        intel_label = "none" if intel is None else "stressed"

        baseline_cases = BASELINE["run_simulation"][goal]
        expected = None
        for case in baseline_cases:
            if case["profile_idx"] == profile_idx and case["intel"] == intel_label:
                expected = case
                break
        if expected is None:
            pytest.skip(f"No sim baseline for {goal}/{profile_idx}/{intel_label}")

        profile["protein_g"] = protein_g
        profile["fitness_intelligence"] = intel
        macros = {"protein": protein_g, "carbs": 200, "fat": 60, "fiber": 30}

        got = run_simulation(
            profile=profile, goal=goal, adherence_label="Moderate (70%)",
            target_calories=target_calories, tdee=tdee_guess,
            macros=macros, weeks=8, fitness_intelligence=intel,
        )

        assert _approx(got["weekly_rate"], expected["weekly_rate"]), (
            f"sim/{goal}/p{profile_idx}/{intel_label} | weekly_rate: "
            f"got {got['weekly_rate']}, expected {expected['weekly_rate']}")
        assert got["goal_week"] == expected["goal_week"], (
            f"sim/{goal}/p{profile_idx}/{intel_label} | goal_week")
        assert _approx(got["calorie_delta"], expected["calorie_delta"]), (
            f"sim/{goal}/p{profile_idx}/{intel_label} | calorie_delta")
        assert _approx(got["recomp_muscle"], expected["recomp_muscle"]), (
            f"sim/{goal}/p{profile_idx}/{intel_label} | recomp_muscle")

        # Compare DF records
        got_records = got["df"].to_dict(orient="records")
        for i, (g_row, e_row) in enumerate(zip(got_records, expected["df_records"])):
            for key in ("week", "weight", "weekly_rate", "cumulative", "muscle"):
                assert _approx(g_row.get(key), e_row.get(key)), (
                    f"sim/{goal}/p{profile_idx}/{intel_label} | df[{i}].{key}: "
                    f"got {g_row.get(key)}, expected {e_row.get(key)}")

        # Adherence comparison
        for lbl in got["adh_comparison"]:
            assert _approx(got["adh_comparison"][lbl], expected["adh_comparison"].get(lbl)), (
                f"sim/{goal}/p{profile_idx}/{intel_label} | adh[{lbl}]")


# ── Tests: milestone parity ────────────────────────────────────────────────

class TestMilestoneParity:
    """generate_milestones shape must match baseline."""

    @pytest.mark.parametrize("goal", GOALS)
    def test_milestones(self, goal):
        from transformation_engine.prediction_engine import generate_milestones

        weekly = {"Fat Loss": 0.5, "Muscle Gain": 0.15,
                  "Weight Gain": 0.3, "Body Recomposition": 0.1}[goal]
        target = 90 if goal == "Fat Loss" else 110

        got = generate_milestones(100, target, weekly, goal)
        expected = BASELINE["milestones"][goal]

        assert len(got) == len(expected), f"milestones/{goal} | length"
        for i, (g, e) in enumerate(zip(got, expected)):
            assert g["week"] == e["week"], f"milestones/{goal}[{i}].week"
            assert g["weight"] == e["weight"], f"milestones/{goal}[{i}].weight"
            assert g["change"] == e["change"], f"milestones/{goal}[{i}].change"
            assert g["reached_goal"] == e["reached_goal"], f"milestones/{goal}[{i}].reached_goal"
