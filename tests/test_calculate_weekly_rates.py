"""
tests/test_calculate_weekly_rates.py
═════════════════════════════════════
Comprehensive unit tests for calculate_weekly_rates in
transformation_engine.prediction_engine.

Covers
──────
1. Normal cases: all 4 goals × Male/Female × Beginner/Intermediate/Advanced
2. Input clamping: weight/height/age/workout_days/sleep/steps/protein
   (only unknown goal and non-positive height raise ValueError)
3. ML fallback: model=None for each goal → blended rate == scientific rate exactly
4. Blend math: alpha=0.20 asserted directly for all 4 goals, including:
     - Fat Loss:            final = (1-α)*sci + α*ml
     - Weight Gain:         final = (1-α)*sci + α*ml
     - Muscle Gain:         nested double-blend (muscle then weight-change)
     - Body Recomposition:  fat blend + 0.55-discounted muscle blend
5. Invariant: muscle_loss_fraction ∈ [0, 0.35] across randomised inputs
6. Rate caps: all outputs respect RATE_CAPS
7. Scientific-vs-ML delta table printed to stdout for every goal

Source reference
────────────────
protein_adequacy is calculated in
    physiology_engine.calculate_readiness_subscores (lines 80-82):

        target_protein = weight * PROTEIN_PER_KG.get(goal, 2.0)
        protein_adequacy = min(1.5, protein_g / max(1.0, target_protein))

    where PROTEIN_PER_KG = {
        "Fat Loss": 2.2, "Muscle Gain": 2.5,
        "Weight Gain": 1.8, "Body Recomposition": 2.6,
    }

    It is capped at 1.5 so over-eating protein can never unlock more than a
    50% bonus relative to the target.

_predict_with_model (model_loader.py line 60-61):
    if active_model is None:
        return None
    So passing model=None (i.e. load_models() returning {}) guarantees an
    immediate None return → scientific fallback path, no randomness.
"""

from __future__ import annotations

import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from transformation_engine.prediction_engine import calculate_weekly_rates
from transformation_engine.utils import PROTEIN_PER_KG, RATE_CAPS

# ── Module-level constants mirrored from source ───────────────────────────────

ALPHA = 0.20  # blend weight (prediction_engine.py line 128)

# max_weekly_muscle_gain per experience tier (goal_logic._muscle_gain line 96)
_MAX_MUSCLE = {"Beginner": 0.25, "Intermediate": 0.15, "Advanced": 0.06}

# optimal training days per tier (physiology_engine line 85)
_OPTIMAL_DAYS = {"Beginner": 3, "Intermediate": 4, "Advanced": 5}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _profile(**overrides) -> dict:
    """Standard valid male-intermediate profile; override any key in a test."""
    return {
        "weight_kg":   80.0,
        "height_cm":  180.0,
        "age":          30,
        "gender":     "Male",
        "experience": "Intermediate",
        "workout_days":  4,
        "sleep_hrs":    8.0,
        "daily_steps": 10_000,
        **overrides,
    }


def _no_ml(monkeypatch):
    """Patch _predict_with_model to always return None (scientific-only mode)."""
    monkeypatch.setattr(
        "transformation_engine.prediction_engine._predict_with_model",
        lambda *args, **kwargs: None,
    )


def _fixed_ml(monkeypatch, value: float):
    """Patch _predict_with_model to always return a fixed scalar."""
    monkeypatch.setattr(
        "transformation_engine.prediction_engine._predict_with_model",
        lambda *args, **kwargs: value,
    )


def _routed_ml(monkeypatch, mapping: dict[str, float]):
    """Patch _predict_with_model to return different values per goal."""
    monkeypatch.setattr(
        "transformation_engine.prediction_engine._predict_with_model",
        lambda goal_name, *a, **kw: mapping.get(goal_name, 0.0),
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. NORMAL CASES – all goals × gender × experience
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("gender", ["Male", "Female"])
@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_normal_fat_loss(gender, experience):
    res = calculate_weekly_rates(
        profile=_profile(gender=gender, experience=experience),
        goal="Fat Loss", calorie_delta=-500.0, protein_g=160.0,
    )
    assert res["weekly_fat_loss"] >= 0.0
    assert res["weekly_fat_loss"] <= RATE_CAPS["Fat Loss"]["max"]
    assert res["bmr"] > 0
    assert res["bmi"] > 0
    assert res["scientific_fat_loss"] >= 0.0


@pytest.mark.parametrize("gender", ["Male", "Female"])
@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_normal_muscle_gain(gender, experience):
    res = calculate_weekly_rates(
        profile=_profile(gender=gender, experience=experience),
        goal="Muscle Gain", calorie_delta=350.0, protein_g=160.0,
    )
    assert res["weekly_muscle_gain"] >= 0.0
    assert res["weekly_muscle_gain"] <= _MAX_MUSCLE[experience]
    assert res["weekly_weight_change"] >= 0.0


@pytest.mark.parametrize("gender", ["Male", "Female"])
@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_normal_weight_gain(gender, experience):
    res = calculate_weekly_rates(
        profile=_profile(gender=gender, experience=experience),
        goal="Weight Gain", calorie_delta=500.0, protein_g=140.0,
    )
    assert res["weekly_weight_change"] >= 0.0
    assert res["weekly_weight_change"] <= RATE_CAPS["Weight Gain"]["max"]


@pytest.mark.parametrize("gender", ["Male", "Female"])
@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_normal_body_recomposition(gender, experience):
    res = calculate_weekly_rates(
        profile=_profile(gender=gender, experience=experience),
        goal="Body Recomposition", calorie_delta=-200.0, protein_g=200.0,
    )
    assert res["weekly_fat_loss"]    >= 0.0
    assert res["weekly_fat_loss"]    <= RATE_CAPS["Body Recomposition"]["fat_loss_max"]
    assert res["weekly_muscle_gain"] >= 0.0
    assert res["weekly_muscle_gain"] <= RATE_CAPS["Body Recomposition"]["muscle_gain_max"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. INPUT CLAMPING
# ══════════════════════════════════════════════════════════════════════════════

def test_clamp_weight_below_minimum():
    """weight_kg < 30 → clamped to 30."""
    res = calculate_weekly_rates(
        profile=_profile(weight_kg=5.0),
        goal="Fat Loss", calorie_delta=-300.0, protein_g=100.0,
    )
    # BMR Male: 10*30 + 6.25*180 - 5*30 + 5 = 300 + 1125 - 150 + 5 = 1280
    assert res["bmr"] == pytest.approx(1280.0)


def test_clamp_weight_above_maximum():
    """weight_kg > 250 → clamped to 250."""
    res = calculate_weekly_rates(
        profile=_profile(weight_kg=400.0),
        goal="Fat Loss", calorie_delta=-300.0, protein_g=100.0,
    )
    # BMR Male: 10*250 + 6.25*180 - 5*30 + 5 = 2500 + 1125 - 150 + 5 = 3480
    assert res["bmr"] == pytest.approx(3480.0)


def test_clamp_height_below_minimum():
    """height_cm < 100 → clamped to 100; BMI and BMR change accordingly."""
    res = calculate_weekly_rates(
        profile=_profile(height_cm=50.0),
        goal="Fat Loss", calorie_delta=-300.0, protein_g=100.0,
    )
    # clamped height = 100 cm → height_m = 1.0
    # BMI = 80 / 1.0^2 = 80.0
    assert res["bmi"] == pytest.approx(80.0)


def test_clamp_age_below_minimum():
    """age < 10 → clamped to 10; BMR changes."""
    res = calculate_weekly_rates(
        profile=_profile(age=3),
        goal="Fat Loss", calorie_delta=-300.0, protein_g=100.0,
    )
    # BMR Male: 10*80 + 6.25*180 - 5*10 + 5 = 800 + 1125 - 50 + 5 = 1880
    assert res["bmr"] == pytest.approx(1880.0)


def test_clamp_age_above_maximum():
    """age > 100 → clamped to 100."""
    res = calculate_weekly_rates(
        profile=_profile(age=150),
        goal="Fat Loss", calorie_delta=-300.0, protein_g=100.0,
    )
    # BMR Male: 10*80 + 6.25*180 - 5*100 + 5 = 800 + 1125 - 500 + 5 = 1430
    assert res["bmr"] == pytest.approx(1430.0)


def test_clamp_workout_days_below_zero():
    """workout_days < 0 → clamped to 0."""
    res = calculate_weekly_rates(
        profile=_profile(workout_days=-5),
        goal="Muscle Gain", calorie_delta=350.0, protein_g=160.0,
    )
    # training_volume_score = min(1.2, 0/4) = 0.0 for Intermediate
    # → scientific_muscle_gain = 0 (training_volume_score == 0)
    assert res["scientific_muscle_gain"] == pytest.approx(0.0)


def test_clamp_workout_days_above_seven():
    """workout_days > 7 → clamped to 7."""
    res = calculate_weekly_rates(
        profile=_profile(workout_days=15),
        goal="Fat Loss", calorie_delta=-400.0, protein_g=160.0,
    )
    # training_volume_score = min(1.2, 7/4) = 1.2 — no exception raised
    assert res["weekly_fat_loss"] >= 0.0


def test_clamp_sleep_hrs_below_zero():
    """sleep_hrs < 0 → clamped to 0; sleep_score = max(0.4, 0/7) = 0.4."""
    res = calculate_weekly_rates(
        profile=_profile(sleep_hrs=-3.0),
        goal="Fat Loss", calorie_delta=-400.0, protein_g=160.0,
    )
    assert res["sleep_score"] == pytest.approx(0.4)


def test_clamp_daily_steps_below_zero():
    """daily_steps < 0 → clamped to 0; step_score = 0."""
    res = calculate_weekly_rates(
        profile=_profile(daily_steps=-1000),
        goal="Fat Loss", calorie_delta=-400.0, protein_g=160.0,
    )
    assert res["step_score"] == pytest.approx(0.0)


def test_clamp_protein_below_zero():
    """protein_g < 0 → clamped to 0; protein_adequacy = 0."""
    res = calculate_weekly_rates(
        profile=_profile(),
        goal="Fat Loss", calorie_delta=-400.0, protein_g=-50.0,
    )
    assert res["protein_adequacy"] == pytest.approx(0.0)


def test_clamp_adherence_factor_below_zero():
    """adherence_factor < 0 → clamped to 0; adherence_score = 0."""
    res = calculate_weekly_rates(
        profile=_profile(),
        goal="Fat Loss", calorie_delta=-400.0, protein_g=160.0,
        adherence_factor=-0.5,
    )
    assert res["adherence_score"] == pytest.approx(0.0)


def test_clamp_adherence_factor_above_one():
    """adherence_factor > 1 → clamped to 1; adherence_score = 1."""
    res = calculate_weekly_rates(
        profile=_profile(),
        goal="Fat Loss", calorie_delta=-400.0, protein_g=160.0,
        adherence_factor=5.0,
    )
    assert res["adherence_score"] == pytest.approx(1.0)


# ── only these two raise ValueError ──────────────────────────────────────────

def test_raises_unknown_goal():
    with pytest.raises(ValueError, match="Unknown goal"):
        calculate_weekly_rates(
            profile={}, goal="Shred", calorie_delta=0.0, protein_g=100.0,
        )


def test_raises_height_zero():
    with pytest.raises(ValueError, match="Height must be positive"):
        calculate_weekly_rates(
            profile={"height_cm": 0.0}, goal="Fat Loss",
            calorie_delta=0.0, protein_g=100.0,
        )


def test_raises_height_negative():
    with pytest.raises(ValueError, match="Height must be positive"):
        calculate_weekly_rates(
            profile={"height_cm": -10.0}, goal="Fat Loss",
            calorie_delta=0.0, protein_g=100.0,
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3. ML FALLBACK  (model=None → _predict_with_model returns None immediately)
# ══════════════════════════════════════════════════════════════════════════════

def test_fallback_fat_loss_with_no_model(monkeypatch):
    """Fat Loss: model=None → weekly_fat_loss == scientific_fat_loss exactly."""
    _no_ml(monkeypatch)
    res = calculate_weekly_rates(
        profile=_profile(), goal="Fat Loss",
        calorie_delta=-500.0, protein_g=160.0,
    )
    assert res["ml_fat_loss"] is None
    assert res["weekly_fat_loss"] == pytest.approx(res["scientific_fat_loss"], abs=1e-9)


def test_fallback_muscle_gain_with_no_model(monkeypatch):
    """Muscle Gain: model=None → weekly_muscle_gain == scientific_muscle_gain exactly."""
    _no_ml(monkeypatch)
    res = calculate_weekly_rates(
        profile=_profile(), goal="Muscle Gain",
        calorie_delta=350.0, protein_g=160.0,
    )
    assert res["ml_muscle_gain"] is None
    assert res["weekly_muscle_gain"] == pytest.approx(res["scientific_muscle_gain"], abs=1e-9)


def test_fallback_weight_gain_with_no_model(monkeypatch):
    """Weight Gain: model=None → weekly_weight_change == scientific_weight_change exactly."""
    _no_ml(monkeypatch)
    res = calculate_weekly_rates(
        profile=_profile(), goal="Weight Gain",
        calorie_delta=500.0, protein_g=140.0,
    )
    assert res["ml_weight_gain"] is None
    assert res["weekly_weight_change"] == pytest.approx(res["scientific_weight_change"], abs=1e-9)


def test_fallback_recomposition_with_no_model(monkeypatch):
    """Body Recomposition: model=None → both blended rates equal scientific rates exactly."""
    _no_ml(monkeypatch)
    res = calculate_weekly_rates(
        profile=_profile(), goal="Body Recomposition",
        calorie_delta=-200.0, protein_g=200.0,
    )
    assert res["ml_recomp_fat_loss"] is None
    assert res["ml_muscle_gain"]     is None
    assert res["weekly_fat_loss"]    == pytest.approx(res["scientific_fat_loss"],    abs=1e-9)
    assert res["weekly_muscle_gain"] == pytest.approx(res["scientific_muscle_gain"], abs=1e-9)


@pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("goal,cal_delta,blended_key,sci_key", [
    ("Fat Loss",          -500.0, "weekly_fat_loss",     "scientific_fat_loss"),
    ("Muscle Gain",        350.0, "weekly_muscle_gain",  "scientific_muscle_gain"),
    ("Weight Gain",        500.0, "weekly_weight_change","scientific_weight_change"),
    ("Body Recomposition",-200.0, "weekly_fat_loss",     "scientific_fat_loss"),
])
def test_fallback_non_finite_ml(monkeypatch, bad_val, goal, cal_delta, blended_key, sci_key):
    """Non-finite ML prediction → isfinite() guard triggers → falls back to scientific rate."""
    monkeypatch.setattr(
        "transformation_engine.prediction_engine._predict_with_model",
        lambda *a, **kw: bad_val,
    )
    res = calculate_weekly_rates(
        profile=_profile(), goal=goal,
        calorie_delta=cal_delta, protein_g=160.0,
    )
    assert res[blended_key] == pytest.approx(res[sci_key], abs=1e-9), (
        f"[{goal}, bad_val={bad_val}] expected fallback: "
        f"{blended_key}={res[blended_key]!r} != {sci_key}={res[sci_key]!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4. BLEND MATH  (alpha = 0.20 asserted directly)
# ══════════════════════════════════════════════════════════════════════════════

def test_blend_fat_loss_alpha_0_20(monkeypatch):
    """
    Fat Loss blend (prediction_engine lines 159-161):
        ml_fat_loss = max(0, ml_val)
        final = (1 - 0.20)*sci + 0.20*ml_fat_loss
        final = min(RATE_CAPS["Fat Loss"]["max"], max(0, final))
    """
    ml_val = 0.60
    _fixed_ml(monkeypatch, ml_val)

    res = calculate_weekly_rates(
        profile=_profile(), goal="Fat Loss",
        calorie_delta=-500.0, protein_g=160.0,
    )
    sci = res["scientific_fat_loss"]
    expected = min(RATE_CAPS["Fat Loss"]["max"], max(0.0,
                   (1 - ALPHA) * sci + ALPHA * max(0.0, ml_val)))

    assert res["weekly_fat_loss"] == pytest.approx(expected, abs=1e-9), (
        f"Fat Loss: expected blend={(1-ALPHA):.2f}×{sci:.5f} + {ALPHA:.2f}×{ml_val:.5f}"
        f" = {expected:.6f}, got {res['weekly_fat_loss']:.6f}"
    )


def test_blend_weight_gain_alpha_0_20(monkeypatch):
    """
    Weight Gain blend (prediction_engine lines 189-194):
        final = (1 - 0.20)*sci + 0.20*ml_weight_gain
        final = min(RATE_CAPS["Weight Gain"]["max"], max(0, final))
    """
    ml_val = 0.70
    _fixed_ml(monkeypatch, ml_val)

    res = calculate_weekly_rates(
        profile=_profile(), goal="Weight Gain",
        calorie_delta=500.0, protein_g=140.0,
    )
    sci = res["scientific_weight_change"]
    expected = min(RATE_CAPS["Weight Gain"]["max"], max(0.0,
                   (1 - ALPHA) * sci + ALPHA * max(0.0, ml_val)))

    assert res["weekly_weight_change"] == pytest.approx(expected, abs=1e-9), (
        f"Weight Gain: expected {expected:.6f}, got {res['weekly_weight_change']:.6f}"
    )


def test_blend_muscle_gain_nested_double_blend(monkeypatch):
    """
    Muscle Gain has a nested (double) blend (prediction_engine lines 167-184):

    Step 1 — muscle:
        ml_muscle clamped to max(0, ml_muscle_val)
        final_muscle = (1-α)*sci_muscle + α*ml_muscle
        final_muscle = min(max_weekly_muscle_gain[experience], max(0, final_muscle))

    Step 2 — weight change:
        sci_fat_gain = total_surplus_weight_gain - sci_muscle  [from goal_logic]
        final_weight = (1-α)*(final_muscle + sci_fat_gain) + α*ml_weight_gain
        final_weight = min(RATE_CAPS["Muscle Gain"]["max"], max(0, final_weight))
    """
    ml_muscle_val = 0.30
    ml_weight_val = 0.50
    experience    = "Intermediate"
    adherence     = 0.92   # DEFAULT_ADHERENCE (no override passed)
    calorie_delta = 350.0

    _routed_ml(monkeypatch, {"Muscle Gain": ml_muscle_val, "Weight Gain": ml_weight_val})

    res = calculate_weekly_rates(
        profile=_profile(experience=experience),
        goal="Muscle Gain", calorie_delta=calorie_delta, protein_g=160.0,
    )

    sci_muscle = res["scientific_muscle_gain"]
    actual_adherence = res["adherence_score"]  # exact value after clamping

    # Step 1 — muscle blend
    expected_muscle = (1 - ALPHA) * sci_muscle + ALPHA * max(0.0, ml_muscle_val)
    expected_muscle = min(_MAX_MUSCLE[experience], max(0.0, expected_muscle))

    assert res["weekly_muscle_gain"] == pytest.approx(expected_muscle, abs=1e-9), (
        f"Muscle Gain — muscle step: expected {expected_muscle:.6f}, "
        f"got {res['weekly_muscle_gain']:.6f}"
    )

    # Step 2 — weight-change double blend
    # sci_fat_gain comes from goal_logic._muscle_gain (formula verbatim):
    #   total_surplus_wg = (surplus * 7 / 7700) * adherence
    #   sci_fat_gain = max(0, total_surplus_wg - sci_muscle)
    total_surplus_wg = (calorie_delta * 7.0 / 7700.0) * actual_adherence
    sci_fat_gain     = max(0.0, total_surplus_wg - sci_muscle)

    expected_weight = (1 - ALPHA) * (expected_muscle + sci_fat_gain) + ALPHA * max(0.0, ml_weight_val)
    expected_weight = min(RATE_CAPS["Muscle Gain"]["max"], max(0.0, expected_weight))

    assert res["weekly_weight_change"] == pytest.approx(expected_weight, abs=1e-9), (
        f"Muscle Gain — weight step: expected {expected_weight:.6f}, "
        f"got {res['weekly_weight_change']:.6f}"
    )


def test_blend_body_recomposition_with_0_55_muscle_discount(monkeypatch):
    """
    Body Recomposition blend (prediction_engine lines 200-215):

    Fat:
        final_fat = (1-α)*sci_fat + α*max(0, ml_recomp_fat)
        final_fat = min(fat_loss_max, max(0, final_fat))

    Muscle (0.55 discount applied to raw ml_muscle BEFORE blending):
        ml_recomp_muscle = max(0, ml_muscle) * 0.55
        final_muscle = (1-α)*sci_muscle + α*ml_recomp_muscle
        final_muscle = min(muscle_gain_max, max(0, final_muscle))

    Weight:
        weekly_weight_change = final_muscle - final_fat
    """
    ml_recomp_fat = 0.15
    ml_muscle     = 0.25

    _routed_ml(monkeypatch, {"Body Recomposition": ml_recomp_fat, "Muscle Gain": ml_muscle})

    res = calculate_weekly_rates(
        profile=_profile(), goal="Body Recomposition",
        calorie_delta=-200.0, protein_g=200.0,
    )

    sci_fat    = res["scientific_fat_loss"]
    sci_muscle = res["scientific_muscle_gain"]

    expected_fat = (1 - ALPHA) * sci_fat + ALPHA * max(0.0, ml_recomp_fat)
    expected_fat = min(RATE_CAPS["Body Recomposition"]["fat_loss_max"], max(0.0, expected_fat))

    ml_recomp_muscle = max(0.0, ml_muscle) * 0.55   # ← the 0.55 discount
    expected_muscle  = (1 - ALPHA) * sci_muscle + ALPHA * ml_recomp_muscle
    expected_muscle  = min(RATE_CAPS["Body Recomposition"]["muscle_gain_max"], max(0.0, expected_muscle))

    assert res["weekly_fat_loss"] == pytest.approx(expected_fat, abs=1e-9), (
        f"Recomp fat: expected {expected_fat:.6f}, got {res['weekly_fat_loss']:.6f}"
    )
    assert res["weekly_muscle_gain"] == pytest.approx(expected_muscle, abs=1e-9), (
        f"Recomp muscle (0.55 discount): expected {expected_muscle:.6f}, "
        f"got {res['weekly_muscle_gain']:.6f}"
    )
    # net weight = muscle - fat  (prediction_engine line 213)
    assert res["weekly_weight_change"] == pytest.approx(expected_muscle - expected_fat, abs=1e-9)


def test_alpha_regression_guard(monkeypatch):
    """
    Regression guard: if someone changes alpha from 0.20 this test fails
    loudly with the back-calculated actual alpha in the message.

    We use ml_val >> sci so the alpha term dominates and is measurable.
    """
    ml_val = 1.0   # saturating value so any alpha change is obvious
    _fixed_ml(monkeypatch, ml_val)

    res = calculate_weekly_rates(
        profile=_profile(), goal="Fat Loss",
        calorie_delta=-500.0, protein_g=160.0,
    )
    sci = res["scientific_fat_loss"]

    # derive what alpha would produce this blended result (before cap)
    blended_uncapped = res["weekly_fat_loss"]  # may be capped — use sci < cap region
    # cross-check: build the expected blended value at alpha=0.20
    expected = min(RATE_CAPS["Fat Loss"]["max"], max(0.0,
                   (1 - ALPHA) * sci + ALPHA * max(0.0, ml_val)))

    assert res["weekly_fat_loss"] == pytest.approx(expected, abs=1e-9), (
        f"alpha does not appear to be {ALPHA}. "
        f"sci={sci:.5f}, ml={ml_val:.5f}, blended={blended_uncapped:.5f}, "
        f"expected_at_alpha_0.20={expected:.5f}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5. INVARIANT:  muscle_loss_fraction ∈ [0, 0.35]
# ══════════════════════════════════════════════════════════════════════════════
# This guards against a future divide-by-zero in the Fat Loss weight-change
# calculation (prediction_engine line 162):
#   weekly_weight_change = -(final_fat_loss / (1.0 - muscle_loss_fraction))
# If muscle_loss_fraction ever hits 1.0 we get ZeroDivisionError.
#
# From goal_logic._fat_loss:
#   muscle_preservation = 0.6*min(1, protein_adequacy) + 0.4*min(1, training_volume_score)
#   muscle_loss_fraction = 0.35 * (1 - muscle_preservation)
#
# Bounds:  muscle_preservation ∈ [0, 1]  → muscle_loss_fraction ∈ [0, 0.35]
# ═════════════════════════════════════════════════════════════════════════════

# Derive muscle_loss_fraction from the returned weekly values, since it is not
# in the public return dict.  From the source:
#   weekly_weight_change = -(final_fat_loss / (1 - muscle_loss_fraction))
# → muscle_loss_fraction = 1 - (-final_fat_loss / weekly_weight_change)
# We use no-ML mode so final_fat_loss == scientific_fat_loss (no blending complication).

def _muscle_loss_fraction_from_result(res: dict) -> float:
    fat  = res["weekly_fat_loss"]
    wt_chg = res["weekly_weight_change"]   # negative for Fat Loss
    if wt_chg == 0.0:
        return 0.0
    return 1.0 - (-fat / wt_chg)


@pytest.mark.parametrize("seed", range(20))
def test_muscle_loss_fraction_invariant(monkeypatch, seed):
    """
    muscle_loss_fraction must stay in [0, 0.35] across 20 random valid profiles.

    Formula (goal_logic._fat_loss lines 74-75):
        muscle_preservation = 0.6*min(1, protein_adequacy) + 0.4*min(1, tvs)
        muscle_loss_fraction = 0.35 * (1 - muscle_preservation)   ← max = 0.35
    """
    _no_ml(monkeypatch)
    rng = random.Random(seed)

    profile = {
        "weight_kg":   rng.uniform(30, 200),
        "height_cm":   rng.uniform(100, 210),
        "age":         rng.randint(10, 80),
        "gender":      rng.choice(["Male", "Female"]),
        "experience":  rng.choice(["Beginner", "Intermediate", "Advanced"]),
        "workout_days": rng.randint(0, 7),
        "sleep_hrs":   rng.uniform(0, 12),
        "daily_steps": rng.uniform(0, 20_000),
    }
    protein_g    = rng.uniform(0, 300)
    calorie_delta = rng.uniform(-900, -50)   # deficit → Fat Loss

    res = calculate_weekly_rates(
        profile=profile, goal="Fat Loss",
        calorie_delta=calorie_delta, protein_g=protein_g,
    )

    mlf = _muscle_loss_fraction_from_result(res)
    assert 0.0 <= mlf <= 0.35 + 1e-9, (
        f"seed={seed}: muscle_loss_fraction={mlf:.6f} out of [0, 0.35]. "
        f"profile={profile}, protein_g={protein_g:.1f}, delta={calorie_delta:.1f}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 6. RATE CAPS — outputs never exceed physiological ceilings
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_rate_cap_fat_loss(monkeypatch, experience):
    """Fat Loss: weekly_fat_loss ≤ RATE_CAPS["Fat Loss"]["max"] = 0.90 kg/week."""
    _fixed_ml(monkeypatch, 9999.0)   # extreme ML value to stress-test capping
    res = calculate_weekly_rates(
        profile=_profile(experience=experience),
        goal="Fat Loss", calorie_delta=-5000.0, protein_g=300.0,
    )
    assert res["weekly_fat_loss"] <= RATE_CAPS["Fat Loss"]["max"] + 1e-9


@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_rate_cap_muscle_gain(monkeypatch, experience):
    """Muscle Gain: weekly_muscle_gain ≤ _MAX_MUSCLE[experience]."""
    _fixed_ml(monkeypatch, 9999.0)
    res = calculate_weekly_rates(
        profile=_profile(experience=experience),
        goal="Muscle Gain", calorie_delta=2000.0, protein_g=400.0,
    )
    assert res["weekly_muscle_gain"] <= _MAX_MUSCLE[experience] + 1e-9


@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_rate_cap_weight_gain(monkeypatch, experience):
    """Weight Gain: weekly_weight_change ≤ RATE_CAPS["Weight Gain"]["max"] = 1.00 kg/week."""
    _fixed_ml(monkeypatch, 9999.0)
    res = calculate_weekly_rates(
        profile=_profile(experience=experience),
        goal="Weight Gain", calorie_delta=3000.0, protein_g=300.0,
    )
    assert res["weekly_weight_change"] <= RATE_CAPS["Weight Gain"]["max"] + 1e-9


@pytest.mark.parametrize("experience", ["Beginner", "Intermediate", "Advanced"])
def test_rate_cap_recomposition(monkeypatch, experience):
    """Body Recomposition: both fat_loss and muscle_gain stay within their caps."""
    _fixed_ml(monkeypatch, 9999.0)
    res = calculate_weekly_rates(
        profile=_profile(experience=experience),
        goal="Body Recomposition", calorie_delta=-200.0, protein_g=300.0,
    )
    assert res["weekly_fat_loss"]    <= RATE_CAPS["Body Recomposition"]["fat_loss_max"]    + 1e-9
    assert res["weekly_muscle_gain"] <= RATE_CAPS["Body Recomposition"]["muscle_gain_max"] + 1e-9


# ══════════════════════════════════════════════════════════════════════════════
# 7. SCIENTIFIC vs ML-BLENDED DELTA TABLE
#    Read the printed numbers — they answer whether the ML models are worth
#    keeping or whether the scientific formula alone would suffice.
# ══════════════════════════════════════════════════════════════════════════════

_DELTA_CASES = [
    ("Fat Loss", _profile(
        weight_kg=85, height_cm=178, age=22,
        gender="Male", experience="Beginner",
        workout_days=4, daily_steps=8000, sleep_hrs=7.0,
    ), -500.0, 180.0),
    ("Fat Loss (Female)", _profile(
        weight_kg=68, height_cm=163, age=27,
        gender="Female", experience="Intermediate",
        workout_days=4, daily_steps=9000, sleep_hrs=7.5,
    ), -400.0, 140.0),
    ("Muscle Gain", _profile(
        weight_kg=60, height_cm=165, age=29,
        gender="Female", experience="Intermediate",
        workout_days=5, daily_steps=10_000, sleep_hrs=7.5,
    ), 350.0, 150.0),
    ("Muscle Gain (Beginner)", _profile(
        weight_kg=75, height_cm=175, age=21,
        gender="Male", experience="Beginner",
        workout_days=3, daily_steps=7000, sleep_hrs=8.0,
    ), 400.0, 160.0),
    ("Weight Gain", _profile(
        weight_kg=78, height_cm=180, age=35,
        gender="Male", experience="Advanced",
        workout_days=5, daily_steps=12_000, sleep_hrs=6.5,
    ), 500.0, 140.0),
    ("Body Recomposition", _profile(
        weight_kg=110, height_cm=182, age=31,
        gender="Male", experience="Intermediate",
        workout_days=6, daily_steps=14_000, sleep_hrs=6.0,
    ), -150.0, 200.0),
    ("Body Recomposition (Advanced)", _profile(
        weight_kg=90, height_cm=177, age=34,
        gender="Female", experience="Advanced",
        workout_days=6, daily_steps=12_000, sleep_hrs=7.0,
    ), -100.0, 240.0),
]


def test_scientific_vs_ml_delta_table():
    """
    Characterisation test — always PASSES.
    Read the printed table to judge whether the ML models add meaningful value
    over the plain scientific formula.

    Key question: if |% Shift| < 5% for every goal, the ML models contribute
    noise, not signal, and the pipeline could be simplified.
    """
    W = 84
    print("\n" + "=" * W)
    print(
        f"{'Label':<28} | {'Metric':<18} | "
        f"{'Sci Rate':>8} | {'ML Blend':>8} | {'Delta kg/wk':>11} | {'% Shift':>8}"
    )
    print("-" * W)

    for label, profile, cal_delta, protein in _DELTA_CASES:
        # goal canonical name = first word(s) until '('
        goal = label.split("(")[0].strip()
        res  = calculate_weekly_rates(
            profile=profile, goal=goal,
            calorie_delta=cal_delta, protein_g=protein,
        )

        if goal == "Fat Loss":
            rows = [("Fat Loss (kg/wk)", res["scientific_fat_loss"], res["weekly_fat_loss"])]
        elif goal == "Muscle Gain":
            rows = [("Muscle Gain (kg/wk)", res["scientific_muscle_gain"], res["weekly_muscle_gain"])]
        elif goal == "Weight Gain":
            rows = [("Weight Chg (kg/wk)", res["scientific_weight_change"], res["weekly_weight_change"])]
        else:  # Body Recomposition
            rows = [
                ("Recomp FL (kg/wk)", res["scientific_fat_loss"],    res["weekly_fat_loss"]),
                ("Recomp MG (kg/wk)", res["scientific_muscle_gain"], res["weekly_muscle_gain"]),
            ]

        first = True
        for metric, sci, blend in rows:
            delta = blend - sci
            pct   = (delta / sci * 100.0) if sci != 0.0 else 0.0
            lbl   = label if first else ""
            first = False
            print(
                f"{lbl:<28} | {metric:<18} | "
                f"{sci:8.5f} | {blend:8.5f} | {delta:+8.5f} | {pct:+7.2f}%"
            )

    print("=" * W)
    print(
        "  >> If |% Shift| < 5% across all goals  -> ML adds noise, not signal.\n"
        "     If |% Shift| > 15% consistently     -> ML is adjusting meaningfully.\n"
        "     Inspect sign: negative means ML is conservative vs the formula."
    )
