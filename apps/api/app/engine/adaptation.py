"""
Centralized AI Adaptation Engine Models & Pure Scoring Layer (Phase 8).
Defines strictly typed Pydantic models, zero-data neutrality helpers,
and stateless empirical scoring functions for behavioral adaptation decisions.
"""

from typing import List, Literal, Optional, Union, Any, Dict
from datetime import date, datetime, timedelta, timezone
from pydantic import BaseModel, Field
from app.db.supabase import (
    ProfileRepository,
    DailyLogRepository,
    JournalRepository,
    MealPlanRepository,
    WorkoutPlanRepository,
)
from app.engine.bmr_tdee import calculate_target_metrics



# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DietAdjustment(BaseModel):
    calorie_delta: int = Field(0, ge=-300, le=300, description="Caloric adjustment delta relative to baseline")
    protein_delta_g: float = Field(0.0, ge=-30.0, le=30.0, description="Protein adjustment in grams")
    carb_delta_g: float = Field(0.0, ge=-60.0, le=60.0, description="Carbohydrate adjustment in grams")
    fat_delta_g: float = Field(0.0, ge=-20.0, le=20.0, description="Fat adjustment in grams")


class WorkoutAdjustment(BaseModel):
    intensity: Literal["reduce", "maintain", "increase"] = Field("maintain", description="Training intensity adjustment")
    volume: Literal["low", "medium", "high"] = Field("medium", description="Training volume adjustment")
    recovery_days: int = Field(0, ge=0, le=7, description="Number of additional recovery days to inject")
    cardio_minutes: int = Field(0, ge=0, le=120, description="Cardio minutes recommendation")
    deload_recommended: bool = Field(False, description="Flag indicating if a deload week is recommended")


class AdaptationDecision(BaseModel):
    adherence_score: int = Field(..., ge=0, le=100, description="Calculated adherence score (0-100)")
    recovery_score: int = Field(..., ge=0, le=100, description="Calculated recovery score (0-100)")
    stress_score: int = Field(..., ge=0, le=100, description="Calculated stress score (0-100)")
    sleep_quality: int = Field(..., ge=0, le=100, description="Calculated sleep quality (0-100)")
    plateau_probability: int = Field(..., ge=0, le=100, description="Calculated plateau probability (0-100)")
    injury_risk: int = Field(..., ge=0, le=100, description="Calculated injury risk (0-100)")
    readiness_factor: float = Field(..., ge=0.45, le=1.12, description="Calculated readiness multiplier (0.45-1.12)")

    plateau_detected: bool = Field(False, description="Flag indicating whether a weight/performance plateau is detected")
    high_fatigue_flag: bool = Field(False, description="Flag indicating systemic or acute fatigue")

    diet_adjustment: DietAdjustment = Field(default_factory=DietAdjustment, description="Dietary adjustments")
    workout_adjustment: WorkoutAdjustment = Field(default_factory=WorkoutAdjustment, description="Workout adjustments")

    actionable_recommendations: List[str] = Field(default_factory=list, description="Specific actionable recommendations")
    coaching_summary: str = Field("", description="High-level coaching summary text")
    objective_data_available: bool = Field(
        False,
        description=(
            "True only if at least one objective signal (adherence, recovery, stress, sleep, "
            "injury risk, plateau probability) was provided and evaluated. When False, the numeric "
            "score fields are neutral defaults, not measurements."
        ),
    )


class AdaptationInput(BaseModel):
    # Profile
    current_weight_kg: float = Field(..., gt=0.0, description="Current user body weight in kg")
    target_weight_kg: float = Field(..., gt=0.0, description="Target user body weight in kg")
    goal_type: Literal["fat_loss", "muscle_gain", "weight_gain", "recomposition"] = Field(
        ..., description="User fitness goal type"
    )
    target_calories: float = Field(..., gt=0.0, description="Baseline daily target calories")
    target_protein_g: float = Field(..., ge=0.0, description="Baseline daily target protein in grams")
    target_carbs_g: float = Field(..., ge=0.0, description="Baseline daily target carbohydrates in grams")
    target_fat_g: float = Field(..., ge=0.0, description="Baseline daily target fat in grams")
    workout_days_per_week: int = Field(..., ge=1, le=7, description="Number of workout days scheduled per week")
    experience_level: Literal["beginner", "intermediate", "advanced"] = Field(
        ..., description="User training experience level"
    )

    # Aggregated recent behavior
    log_count: int = Field(..., ge=0, description="Count of daily logs in the evaluation window")
    adherence_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical adherence percentage")
    recovery_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical recovery score")
    stress_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical stress score")
    sleep_quality: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical sleep quality score")
    injury_risk: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical injury risk score")
    plateau_probability: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical plateau probability score")
    nutrition_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical nutrition adherence score")
    training_quality: Optional[float] = Field(None, ge=0.0, le=100.0, description="Recent empirical training quality score")

    # Progress
    weight_change_kg_7d: Optional[float] = Field(None, description="Weight change over past 7 days in kg")
    weight_change_kg_14d: Optional[float] = Field(None, description="Weight change over past 14 days in kg")
    weight_change_kg_28d: Optional[float] = Field(None, description="Weight change over past 28 days in kg")

    # Journal context
    latest_journal_summary: Optional[str] = Field(None, description="Summary of latest journal entry if present")
    latest_journal_sentiment: Optional[Literal["fatigued", "motivated", "consistent"]] = Field(
        None, description="Sentiment detected in latest journal"
    )


# ---------------------------------------------------------------------------
# Zero-Data Neutrality & Pure Empirical Scoring Utilities
# ---------------------------------------------------------------------------

def clamp(value: Any, low: int = 0, high: int = 100) -> int:
    """Clamps a numeric value between low and high (inclusive)."""
    try:
        return max(low, min(high, int(round(float(value)))))
    except Exception:
        return low


def _safe_float(val: Any) -> Optional[float]:
    """Safely casts a value to float, returning None on failure or if val is None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def has_sufficient_adaptation_data(log_count: int, minimum_logs: int = 3) -> bool:
    """
    Determines whether sufficient daily logs exist to evaluate empirical adaptations.
    Returns True only when log_count >= minimum_logs (default 3).
    Prevents applying premature readiness penalties to new users with no behavioral history.
    """
    try:
        return int(log_count) >= int(minimum_logs)
    except Exception:
        return False


def score_adherence(
    adherence_input: Optional[Union[int, float]] = None,
) -> Optional[int]:
    """
    Evaluates empirical user adherence percentage (0-100).
    Returns None if no measurable adherence input exists.
    """
    if adherence_input is None:
        return None
    return clamp(adherence_input, low=0, high=100)


def score_recovery(
    recovery_input: Optional[Union[int, float]] = None,
) -> Optional[int]:
    """
    Evaluates empirical user recovery score (0-100).
    Returns None if no measurable recovery input exists.
    """
    if recovery_input is None:
        return None
    return clamp(recovery_input, low=0, high=100)


def score_plateau_probability(
    plateau_input: Optional[Union[int, float]] = None,
) -> Optional[int]:
    """
    Evaluates empirical plateau probability (0-100).
    Returns None if there is insufficient weight-history information.
    """
    if plateau_input is None:
        return None
    return clamp(plateau_input, low=0, high=100)


def score_stress(
    stress_input: Optional[Union[int, float]] = None,
) -> Optional[int]:
    """
    Clamps and validates empirical stress score (0-100).
    Returns None if no stress input exists.
    """
    if stress_input is None:
        return None
    return clamp(stress_input, low=0, high=100)


def score_sleep_quality(
    sleep_input: Optional[Union[int, float]] = None,
) -> Optional[int]:
    """
    Clamps and validates empirical sleep quality score (0-100).
    Returns None if no sleep quality input exists.
    """
    if sleep_input is None:
        return None
    return clamp(sleep_input, low=0, high=100)


def score_injury_risk(
    risk_input: Optional[Union[int, float]] = None,
) -> Optional[int]:
    """
    Clamps and validates empirical injury risk score (0-100).
    Returns None if no injury risk input exists.
    """
    if risk_input is None:
        return None
    return clamp(risk_input, low=0, high=100)


DEFAULT_NUTRITION_WEIGHT_CALORIES = 0.40
DEFAULT_NUTRITION_WEIGHT_PROTEIN = 0.30
DEFAULT_NUTRITION_WEIGHT_CARBS = 0.15
DEFAULT_NUTRITION_WEIGHT_FAT = 0.15


def score_nutrition(
    *,
    actual_calories: Optional[Union[int, float]] = None,
    target_calories: Optional[Union[int, float]] = None,
    actual_protein_g: Optional[Union[int, float]] = None,
    target_protein_g: Optional[Union[int, float]] = None,
    actual_carbs_g: Optional[Union[int, float]] = None,
    target_carbs_g: Optional[Union[int, float]] = None,
    actual_fat_g: Optional[Union[int, float]] = None,
    target_fat_g: Optional[Union[int, float]] = None,
) -> Optional[float]:
    """
    Evaluates empirical nutrition adherence score (0.0 to 100.0).

    Compares logged average intake against target nutrition values.
    Uses available data only; missing macros are NOT treated as zero intake.
    If no valid nutrition data exists, returns None.

    Weighting:
        calories: 0.40
        protein:  0.30
        carbs:    0.15
        fat:      0.15
    When a subset of metrics is present, the weights are re-normalized across
    the available components.

    Sub-score formula for each component:
        accuracy = max(0.0, min(100.0, 100.0 - (abs(actual - target) / target) * 100.0))
    """
    components = [
        (actual_calories, target_calories, DEFAULT_NUTRITION_WEIGHT_CALORIES),
        (actual_protein_g, target_protein_g, DEFAULT_NUTRITION_WEIGHT_PROTEIN),
        (actual_carbs_g, target_carbs_g, DEFAULT_NUTRITION_WEIGHT_CARBS),
        (actual_fat_g, target_fat_g, DEFAULT_NUTRITION_WEIGHT_FAT),
    ]

    weighted_score_sum = 0.0
    active_weight_sum = 0.0

    for act_raw, tgt_raw, weight in components:
        act = _safe_float(act_raw)
        tgt = _safe_float(tgt_raw)
        if act is not None and tgt is not None and tgt > 0:
            act_clamped = max(0.0, act)
            error_ratio = abs(act_clamped - tgt) / tgt
            sub_score = max(0.0, min(100.0, 100.0 - (error_ratio * 100.0)))
            weighted_score_sum += sub_score * weight
            active_weight_sum += weight

    if active_weight_sum <= 0.0:
        return None

    final_score = weighted_score_sum / active_weight_sum
    return round(max(0.0, min(100.0, final_score)), 2)


DEFAULT_TRAINING_WEIGHT_ADHERENCE = 0.60
DEFAULT_TRAINING_WEIGHT_ENERGY = 0.40


def score_training_quality(
    *,
    workout_adherence: Optional[Union[int, float]] = None,
    average_energy_rating: Optional[Union[int, float]] = None,
    completed_workouts: Optional[int] = None,
    planned_workouts: Optional[int] = None,
    planned_workouts_per_week: Optional[int] = None,
    window_days: Optional[Union[int, float]] = None,
) -> Optional[float]:
    """
    Evaluates empirical training quality score (0.0 to 100.0).

    Combines workout adherence and energy rating:
        workout adherence: 0.60
        energy rating:     0.40 (energy rating 1-10 scaled to 0-100)

    If only one signal is available, it is re-normalized to 1.0.
    If no training data exists, returns None.

    When window_days is provided (> 0), expected workouts are normalized:
        expected_workouts = planned_workouts * (window_days / 7.0)
    If window_days is None, planned_workouts is treated as the expected count directly.
    """
    adh_val = _safe_float(workout_adherence)
    if adh_val is None:
        cw = _safe_float(completed_workouts)
        pw = _safe_float(planned_workouts if planned_workouts is not None else planned_workouts_per_week)
        w_days = _safe_float(window_days)
        if cw is not None and pw is not None and pw > 0:
            if w_days is not None:
                if w_days > 0:
                    expected = pw * (w_days / 7.0)
                    if expected > 0:
                        adh_val = (cw / expected) * 100.0
                else:
                    adh_val = None
            else:
                adh_val = (cw / pw) * 100.0

    adh_score: Optional[float] = None
    if adh_val is not None:
        adh_score = max(0.0, min(100.0, adh_val))

    nrg_val = _safe_float(average_energy_rating)
    nrg_score: Optional[float] = None
    if nrg_val is not None:
        # Scale 1-10 rating to 0-100 (e.g. 7.5 -> 75.0)
        nrg_score = max(0.0, min(100.0, nrg_val * 10.0))

    if adh_score is not None and nrg_score is not None:
        combined = (
            (adh_score * DEFAULT_TRAINING_WEIGHT_ADHERENCE)
            + (nrg_score * DEFAULT_TRAINING_WEIGHT_ENERGY)
        )
        return round(max(0.0, min(100.0, combined)), 2)
    elif adh_score is not None:
        return round(max(0.0, min(100.0, adh_score)), 2)
    elif nrg_score is not None:
        return round(max(0.0, min(100.0, nrg_score)), 2)
    else:
        return None


def calculate_readiness_factor(
    adherence_score: Union[int, float],
    recovery_score: Union[int, float],
    stress_score: Union[int, float],
    sleep_quality: Union[int, float],
    plateau_probability: Union[int, float],
    injury_risk: Union[int, float],
    *,
    nutrition_score: Union[int, float] = 80.0,
    training_quality: Union[int, float] = 80.0,
    motivation_score: Union[int, float] = 80.0,
) -> float:
    """
    Computes composite readiness factor bounded strictly to [0.45, 1.12].
    Accepts explicit numeric scores only. Dict, AdaptationDecision, and arbitrary
    polymorphic inputs are strictly rejected.

    Readiness weights:
        adherence: 0.30
        recovery: 0.20
        nutrition: 0.20
        training: 0.15
        motivation: 0.10
        sleep: 0.05
    Risk weights:
        stress: 0.10
        plateau: 0.12
        injury: 0.12
    """
    inputs = {
        "adherence_score": adherence_score,
        "recovery_score": recovery_score,
        "stress_score": stress_score,
        "sleep_quality": sleep_quality,
        "plateau_probability": plateau_probability,
        "injury_risk": injury_risk,
        "nutrition_score": nutrition_score,
        "training_quality": training_quality,
        "motivation_score": motivation_score,
    }

    for name, val in inputs.items():
        if isinstance(val, (dict, BaseModel)) or type(val) not in (int, float):
            raise TypeError(
                f"calculate_readiness_factor accepts explicit numeric scores only. "
                f"Received unsupported type '{type(val).__name__}' for parameter '{name}'."
            )

    adh = clamp(adherence_score, low=0, high=100)
    rec = clamp(recovery_score, low=0, high=100)
    nut = clamp(nutrition_score, low=0, high=100)
    trn = clamp(training_quality, low=0, high=100)
    mot = clamp(motivation_score, low=0, high=100)
    slp = clamp(sleep_quality, low=0, high=100)

    str_val = clamp(stress_score, low=0, high=100)
    plt = clamp(plateau_probability, low=0, high=100)
    inj = clamp(injury_risk, low=0, high=100)

    readiness = (
        (adh * 0.30)
        + (rec * 0.20)
        + (nut * 0.20)
        + (trn * 0.15)
        + (mot * 0.10)
        + (slp * 0.05)
    ) / 100.0

    risk_penalty = (
        (str_val * 0.10)
        + (plt * 0.12)
        + (inj * 0.12)
    ) / 100.0

    raw_factor = readiness * (1.0 - risk_penalty)
    return round(max(0.45, min(1.12, raw_factor)), 4)


# ---------------------------------------------------------------------------
# Feature Extraction Layer
# ---------------------------------------------------------------------------

def calculate_weight_change(
    start_weight_kg: Optional[float],
    end_weight_kg: Optional[float],
) -> Optional[float]:
    """
    Computes absolute weight change in kg: (end_weight - start_weight).
    Returns None if either input is missing.
    """
    if start_weight_kg is None or end_weight_kg is None:
        return None
    return round(float(end_weight_kg) - float(start_weight_kg), 2)


def calculate_weight_change_percent(
    start_weight_kg: Optional[float],
    end_weight_kg: Optional[float],
) -> Optional[float]:
    """
    Computes percentage weight change relative to start weight:
        ((end_weight - start_weight) / start_weight) * 100.
    Returns None when inputs are missing or start_weight <= 0.
    """
    if start_weight_kg is None or end_weight_kg is None:
        return None
    try:
        start = float(start_weight_kg)
        end = float(end_weight_kg)
        if start <= 0.0:
            return None
        return round(((end - start) / start) * 100.0, 2)
    except Exception:
        return None


def calculate_adherence_percent(
    completed_workouts: Optional[int],
    planned_workouts: Optional[Union[int, float]],
    days_with_calorie_data: Optional[int],
    days_with_target_calories: Optional[Union[int, float]],
) -> Optional[float]:
    """
    Calculates overall adherence percentage (0-100).
    If both workout and nutrition data exist, returns their arithmetic mean.
    If only one category exists, returns that category.
    If neither exists, returns None.
    Clamps the result to [0.0, 100.0].
    """
    workout_adh: Optional[float] = None
    if (
        completed_workouts is not None
        and planned_workouts is not None
        and planned_workouts > 0
    ):
        workout_adh = max(0.0, min(100.0, (completed_workouts / planned_workouts) * 100.0))

    nutrition_adh: Optional[float] = None
    if (
        days_with_calorie_data is not None
        and days_with_target_calories is not None
        and days_with_target_calories > 0
    ):
        nutrition_adh = max(0.0, min(100.0, (days_with_calorie_data / days_with_target_calories) * 100.0))

    if workout_adh is not None and nutrition_adh is not None:
        mean_adh = (workout_adh + nutrition_adh) / 2.0
        return round(max(0.0, min(100.0, mean_adh)), 2)
    elif workout_adh is not None:
        return round(workout_adh, 2)
    elif nutrition_adh is not None:
        return round(nutrition_adh, 2)
    else:
        return None


def calculate_plateau_probability(
    weight_change_14d_kg: Optional[float],
    weight_change_28d_kg: Optional[float],
    goal_type: str,
) -> Optional[float]:
    """
    Transparent rule-based plateau probability estimator (0-100).
    Not a medical diagnosis; identifies flat progress windows over 14-28 days.
    """
    if weight_change_14d_kg is None or weight_change_28d_kg is None:
        return None

    goal = (goal_type or "").lower().strip()
    abs_14d = abs(float(weight_change_14d_kg))
    abs_28d = abs(float(weight_change_28d_kg))

    if goal == "fat_loss":
        if abs_14d < 0.2 and abs_28d < 0.4:
            return 80.0
        return 0.0

    if goal in ("weight_gain", "muscle_gain"):
        if abs_14d < 0.1 and abs_28d < 0.2:
            return 80.0
        return 0.0

    if goal == "recomposition":
        # Weight alone is insufficient to identify recomposition plateau
        return None

    return None


def build_progress_features(
    weight_change_7d_kg: Optional[float],
    weight_change_14d_kg: Optional[float],
    weight_change_28d_kg: Optional[float],
    goal_type: str,
) -> dict:
    """
    Constructs an aggregated progress feature dictionary.
    Returns:
        - weight_change_kg_7d
        - weight_change_kg_14d
        - weight_change_kg_28d
        - plateau_probability
    """
    plateau_prob = calculate_plateau_probability(
        weight_change_14d_kg=weight_change_14d_kg,
        weight_change_28d_kg=weight_change_28d_kg,
        goal_type=goal_type,
    )
    return {
        "weight_change_kg_7d": weight_change_7d_kg,
        "weight_change_kg_14d": weight_change_14d_kg,
        "weight_change_kg_28d": weight_change_28d_kg,
        "plateau_probability": plateau_prob,
    }


def build_adaptation_input(
    *,
    current_weight_kg: float,
    target_weight_kg: float,
    goal_type: str,
    target_calories: float,
    target_protein_g: float,
    target_carbs_g: float,
    target_fat_g: float,
    workout_days_per_week: int,
    experience_level: str,
    log_count: int,
    adherence_percent: Optional[float] = None,
    recovery_score: Optional[float] = None,
    stress_score: Optional[float] = None,
    sleep_quality: Optional[float] = None,
    injury_risk: Optional[float] = None,
    nutrition_score: Optional[float] = None,
    training_quality: Optional[float] = None,
    weight_change_kg_7d: Optional[float] = None,
    weight_change_kg_14d: Optional[float] = None,
    weight_change_kg_28d: Optional[float] = None,
    latest_journal_summary: Optional[str] = None,
    latest_journal_sentiment: Optional[str] = None,
) -> AdaptationInput:
    """
    Pure builder function that produces a validated AdaptationInput instance.

    Automatically derives plateau_probability using calculate_plateau_probability()
    based on the provided 14-day and 28-day weight trajectories and goal type.
    """
    plateau_prob = calculate_plateau_probability(
        weight_change_14d_kg=weight_change_kg_14d,
        weight_change_28d_kg=weight_change_kg_28d,
        goal_type=goal_type,
    )

    return AdaptationInput(
        current_weight_kg=current_weight_kg,
        target_weight_kg=target_weight_kg,
        goal_type=goal_type,  # type: ignore[arg-type]
        target_calories=target_calories,
        target_protein_g=target_protein_g,
        target_carbs_g=target_carbs_g,
        target_fat_g=target_fat_g,
        workout_days_per_week=workout_days_per_week,
        experience_level=experience_level,  # type: ignore[arg-type]
        log_count=log_count,
        adherence_percent=adherence_percent,
        recovery_score=recovery_score,
        stress_score=stress_score,
        sleep_quality=sleep_quality,
        injury_risk=injury_risk,
        plateau_probability=plateau_prob,
        nutrition_score=nutrition_score,
        training_quality=training_quality,
        weight_change_kg_7d=weight_change_kg_7d,
        weight_change_kg_14d=weight_change_kg_14d,
        weight_change_kg_28d=weight_change_kg_28d,
        latest_journal_summary=latest_journal_summary,
        latest_journal_sentiment=latest_journal_sentiment,  # type: ignore[arg-type]
    )



def calculate_workout_adjustment(
    readiness_factor: float,
    plateau_detected: bool,
    high_fatigue_flag: bool,
    goal_type: str,
    recovery_score: Optional[float] = None,
) -> WorkoutAdjustment:
    """
    Computes deterministic WorkoutAdjustment based on physiological and progress signals.

    Rules evaluated in priority order:
    1. High fatigue:
       high_fatigue_flag == True OR readiness_factor < 0.65
       -> intensity="reduce", volume="low", recovery_days=2, cardio_minutes=0, deload_recommended=True
    2. Low readiness:
       0.65 <= readiness_factor < 0.80
       -> intensity="reduce", volume="low", recovery_days=1, cardio_minutes=0, deload_recommended=False
    3. Plateau:
       plateau_detected == True AND readiness_factor >= 0.80
       -> for fat_loss: intensity="maintain", volume="medium", recovery_days=0, cardio_minutes=30, deload_recommended=False
       -> for muscle_gain / weight_gain / recomposition / others:
          intensity="maintain", volume="medium", recovery_days=0, cardio_minutes=0, deload_recommended=False
    4. High readiness:
       readiness_factor >= 1.00 AND plateau_detected == False:
       - Requires recovery_score is not None to escalate training:
         -> intensity="increase", volume="high", recovery_days=0, cardio_minutes=0, deload_recommended=False
       - If recovery_score is None, caps at safe baseline progression:
         -> intensity="maintain", volume="medium", recovery_days=0, cardio_minutes=0, deload_recommended=False
    5. Otherwise:
       -> intensity="maintain", volume="medium", recovery_days=0, cardio_minutes=0, deload_recommended=False
    """
    if high_fatigue_flag or readiness_factor < 0.65:
        return WorkoutAdjustment(
            intensity="reduce",
            volume="low",
            recovery_days=2,
            cardio_minutes=0,
            deload_recommended=True,
        )

    if 0.65 <= readiness_factor < 0.80:
        return WorkoutAdjustment(
            intensity="reduce",
            volume="low",
            recovery_days=1,
            cardio_minutes=0,
            deload_recommended=False,
        )

    if plateau_detected and readiness_factor >= 0.80:
        goal = (goal_type or "").lower().strip()
        cardio = 30 if goal == "fat_loss" else 0
        return WorkoutAdjustment(
            intensity="maintain",
            volume="medium",
            recovery_days=0,
            cardio_minutes=cardio,
            deload_recommended=False,
        )

    if readiness_factor >= 1.00 and not plateau_detected:
        if recovery_score is not None:
            return WorkoutAdjustment(
                intensity="increase",
                volume="high",
                recovery_days=0,
                cardio_minutes=0,
                deload_recommended=False,
            )
        return WorkoutAdjustment(
            intensity="maintain",
            volume="medium",
            recovery_days=0,
            cardio_minutes=0,
            deload_recommended=False,
        )

    return WorkoutAdjustment(
        intensity="maintain",
        volume="medium",
        recovery_days=0,
        cardio_minutes=0,
        deload_recommended=False,
    )


def clamp_negative_calorie_adjustment(
    calorie_delta: int,
    target_calories: Optional[float],
) -> int:
    """
    Enforces the project's internal baseline configuration bound of 1200 kcal
    for any negative calorie adjustment.

    If target_calories <= 1200:
        calorie_delta = 0
    else:
        max_cut = max(0, int(target_calories - 1200))
        calorie_delta = -min(abs(calorie_delta), max_cut)
    """
    if calorie_delta >= 0:
        return calorie_delta
    if target_calories is None or target_calories <= 1200.0:
        return 0
    max_cut = max(0, int(target_calories - 1200.0))
    return -min(abs(calorie_delta), max_cut)


def calculate_diet_adjustment(
    readiness_factor: float,
    plateau_detected: bool,
    high_fatigue_flag: bool,
    goal_type: str,
    adherence_percent: Optional[float] = None,
    nutrition_score: Optional[float] = None,
    target_calories: Optional[float] = None,
) -> DietAdjustment:
    """
    Computes deterministic DietAdjustment based on empirical signals and goals.

    Priority order:
    1. Behavioral adherence gate:
       adherence_percent is None OR adherence_percent < 70.0 -> neutral
    2. Nutritional alignment gate:
       nutrition_score is not None AND nutrition_score < 60.0 -> neutral
    3. Fatigue/readiness gate:
       high_fatigue_flag is True OR readiness_factor < 0.80 -> neutral
    4. Verified plateau:
       If plateau_detected is True:
       - muscle_gain: +150 kcal, 0.0g protein, +25.0g carbs, +5.5g fat
       - weight_gain: +150 kcal, 0.0g protein, +25.0g carbs, +5.5g fat
       - fat_loss: neutral (Task 12-1 handles via cardio_minutes=30)
       - recomposition: neutral
    5. No plateau: -> neutral
    6. Fallback: -> neutral
    """
    # 1. Behavioral adherence gate
    if adherence_percent is None or adherence_percent < 70.0:
        return DietAdjustment(
            calorie_delta=0,
            protein_delta_g=0.0,
            carb_delta_g=0.0,
            fat_delta_g=0.0,
        )

    # 2. Nutritional alignment gate
    if nutrition_score is not None and nutrition_score < 60.0:
        return DietAdjustment(
            calorie_delta=0,
            protein_delta_g=0.0,
            carb_delta_g=0.0,
            fat_delta_g=0.0,
        )

    # 3. Fatigue/readiness gate
    if high_fatigue_flag or readiness_factor < 0.80:
        return DietAdjustment(
            calorie_delta=0,
            protein_delta_g=0.0,
            carb_delta_g=0.0,
            fat_delta_g=0.0,
        )

    # 4. Verified plateau
    if plateau_detected:
        goal = (goal_type or "").lower().strip()
        if goal in ("muscle_gain", "weight_gain"):
            return DietAdjustment(
                calorie_delta=150,
                protein_delta_g=0.0,
                carb_delta_g=25.0,
                fat_delta_g=5.5,
            )
        elif goal == "fat_loss":
            # Task 12-1 already handles fat-loss plateau through cardio_minutes = 30.
            # Do NOT simultaneously reduce calories.
            return DietAdjustment(
                calorie_delta=0,
                protein_delta_g=0.0,
                carb_delta_g=0.0,
                fat_delta_g=0.0,
            )
        elif goal == "recomposition":
            return DietAdjustment(
                calorie_delta=0,
                protein_delta_g=0.0,
                carb_delta_g=0.0,
                fat_delta_g=0.0,
            )

    # 5. No plateau / Fallback
    return DietAdjustment(
        calorie_delta=0,
        protein_delta_g=0.0,
        carb_delta_g=0.0,
        fat_delta_g=0.0,
    )


# ---------------------------------------------------------------------------
# Centralized Adaptation Decision Engine
# ---------------------------------------------------------------------------

def compute_adaptation(input_data: AdaptationInput) -> AdaptationDecision:
    """
    Computes a deterministic, centralized AdaptationDecision from an AdaptationInput payload.

    Architecture:
        AdaptationInput -> compute_adaptation() -> AdaptationDecision

    Safety Guarantees:
        1. Zero-Data Neutrality: If log_count < 3, returns a completely neutral decision
           (readiness_factor = 1.0, zero calorie/macro deltas, baseline maintain workout).
        2. Conservative Adjustments: Zero diet/workout modifications in this v1 phase.
        3. Factual Signal Reflection: Fatigue and plateau flags are derived strictly from empirical
           inputs (recovery < 50, plateau >= 70) without simulation drift or LLM hallucination.
        4. Honest Unmeasured State: If no objective signal was provided, objective_data_available
           is False and coaching_summary says readiness could not be assessed. The numeric score
           defaults are neutral placeholders, not measurements.
    """
    # 1. Zero-Data Safety Guard
    if not has_sufficient_adaptation_data(input_data.log_count, minimum_logs=3):
        return AdaptationDecision(
            adherence_score=100,
            recovery_score=100,
            stress_score=0,
            sleep_quality=100,
            plateau_probability=0,
            injury_risk=0,
            readiness_factor=1.0,
            plateau_detected=False,
            high_fatigue_flag=False,
            diet_adjustment=DietAdjustment(
                calorie_delta=0,
                protein_delta_g=0.0,
                carb_delta_g=0.0,
                fat_delta_g=0.0,
            ),
            workout_adjustment=WorkoutAdjustment(
                intensity="maintain",
                volume="medium",
                recovery_days=0,
                cardio_minutes=0,
                deload_recommended=False,
            ),
            actionable_recommendations=[],
            coaching_summary="Baseline targets active. Maintain consistent logging to enable personalized adaptations.",
        )

    # 2. Evaluate Empirical Scores (using unimpaired neutral fallbacks for missing signals)
    eval_adherence = score_adherence(input_data.adherence_percent)
    eval_recovery = score_recovery(input_data.recovery_score)
    eval_stress = score_stress(input_data.stress_score)
    eval_sleep = score_sleep_quality(input_data.sleep_quality)
    eval_plateau = score_plateau_probability(input_data.plateau_probability)
    eval_injury = score_injury_risk(input_data.injury_risk)

    # Resolve scores for Decision model (unimpaired baseline for missing metrics)
    decision_adherence = eval_adherence if eval_adherence is not None else 100
    decision_recovery = eval_recovery if eval_recovery is not None else 100
    decision_stress = eval_stress if eval_stress is not None else 0
    decision_sleep = eval_sleep if eval_sleep is not None else 100
    decision_plateau = eval_plateau if eval_plateau is not None else 0
    decision_injury = eval_injury if eval_injury is not None else 0

    objective_data_available = any(
        score is not None
        for score in (
            eval_adherence,
            eval_recovery,
            eval_stress,
            eval_sleep,
            eval_plateau,
            eval_injury,
        )
    )

    # 3. Derive Operational Flags
    high_fatigue_flag = bool(
        input_data.recovery_score is not None and eval_recovery is not None and eval_recovery < 50
    )
    plateau_detected = bool(
        input_data.plateau_probability is not None and eval_plateau is not None and eval_plateau >= 70
    )

    # 4. Calculate Readiness Factor
    # NOTE: When empirical nutrition_score or training_quality signals are available on
    # input_data, they are passed directly into calculate_readiness_factor. Unmeasured
    # secondary scores fall back to neutral 100.0 computational stand-ins so that missing
    # dimensions do NOT impose an artificial penalty on the user's readiness.
    effective_nutrition_score = (
        input_data.nutrition_score
        if input_data.nutrition_score is not None
        else 100.0
    )
    effective_training_quality = (
        input_data.training_quality
        if input_data.training_quality is not None
        else 100.0
    )

    readiness_factor = calculate_readiness_factor(
        adherence_score=decision_adherence,
        recovery_score=decision_recovery,
        stress_score=decision_stress,
        sleep_quality=decision_sleep,
        plateau_probability=decision_plateau,
        injury_risk=decision_injury,
        nutrition_score=effective_nutrition_score,
        training_quality=effective_training_quality,
        motivation_score=100.0,
    )

    # 5. Factual Actionable Recommendations
    recommendations: List[str] = []
    if input_data.recovery_score is not None and eval_recovery is not None and eval_recovery < 50:
        recommendations.append("Recovery score is low.")
    if input_data.stress_score is not None and eval_stress is not None and eval_stress >= 60:
        recommendations.append("Stress score is elevated.")
    if input_data.sleep_quality is not None and eval_sleep is not None and eval_sleep < 60:
        recommendations.append("Sleep quality is low.")
    if plateau_detected:
        recommendations.append("Recent progress may indicate a plateau.")
    if input_data.injury_risk is not None and eval_injury is not None and eval_injury >= 50:
        recommendations.append("Injury risk score is elevated.")

    if input_data.adherence_percent is not None and eval_adherence is not None and eval_adherence < 60:
        recommendations.append(
            "Adherence score is low. Prioritize consistent workout completion and logging."
        )
    if input_data.nutrition_score is not None and input_data.nutrition_score < 60:
        recommendations.append(
            "Nutrition target alignment is low. Focus on meeting daily calorie and macro targets."
        )
    if input_data.training_quality is not None and input_data.training_quality < 60:
        recommendations.append(
            "Training quality is low. Review workout completion and session energy."
        )

    has_objective_recommendations = bool(recommendations)

    # Contextual Journal Recommendations
    if input_data.latest_journal_sentiment == "fatigued" and not high_fatigue_flag:
        recommendations.append("Recent journal reflects fatigue. Prioritize recovery and sleep.")
    elif input_data.latest_journal_sentiment == "motivated":
        recommendations.append("High motivation noted in recent journal. Channel energy into structured training.")

    # 6. Deterministic Coaching Summary
    if high_fatigue_flag and plateau_detected:
        coaching_summary = "High fatigue and potential plateau detected. Focus on recovery and baseline consistency."
    elif high_fatigue_flag:
        coaching_summary = "Elevated fatigue detected. Prioritize recovery and sleep quality."
    elif plateau_detected:
        coaching_summary = "Potential plateau detected. Continue tracking weight and adherence closely."
    elif has_objective_recommendations:
        coaching_summary = "Elevated physiological strain observed across recent logs. Maintain steady baseline habits."
    elif not objective_data_available:
        coaching_summary = (
            "Not enough objective data (recovery, stress, sleep, adherence, injury or plateau signals) "
            "has been recorded to assess readiness."
        )
    else:
        coaching_summary = "Consistent progress and healthy readiness metrics observed across recent logs."

    # 7. Dynamic Workout & Diet Adjustments
    if not objective_data_available:
        workout_adjustment = WorkoutAdjustment(
            intensity="maintain",
            volume="medium",
            recovery_days=0,
            cardio_minutes=0,
            deload_recommended=False,
        )
        diet_adjustment = DietAdjustment(
            calorie_delta=0,
            protein_delta_g=0.0,
            carb_delta_g=0.0,
            fat_delta_g=0.0,
        )
    else:
        workout_adjustment = calculate_workout_adjustment(
            readiness_factor=readiness_factor,
            plateau_detected=plateau_detected,
            high_fatigue_flag=high_fatigue_flag,
            goal_type=input_data.goal_type,
            recovery_score=input_data.recovery_score,
        )
        diet_adjustment = calculate_diet_adjustment(
            readiness_factor=readiness_factor,
            plateau_detected=plateau_detected,
            high_fatigue_flag=high_fatigue_flag,
            goal_type=input_data.goal_type,
            adherence_percent=input_data.adherence_percent,
            nutrition_score=input_data.nutrition_score,
            target_calories=input_data.target_calories,
        )

    return AdaptationDecision(
        adherence_score=decision_adherence,
        recovery_score=decision_recovery,
        stress_score=decision_stress,
        sleep_quality=decision_sleep,
        plateau_probability=decision_plateau,
        injury_risk=decision_injury,
        readiness_factor=readiness_factor,
        plateau_detected=plateau_detected,
        high_fatigue_flag=high_fatigue_flag,
        diet_adjustment=diet_adjustment,
        workout_adjustment=workout_adjustment,
        actionable_recommendations=recommendations,
        coaching_summary=coaching_summary,
        objective_data_available=objective_data_available,
    )


# ---------------------------------------------------------------------------
# Read-Only Adaptation Data Collector Layer
# ---------------------------------------------------------------------------

def collect_adaptation_data(
    user_id: str,
    profile_repository: Any = ProfileRepository,
    daily_log_repository: Any = DailyLogRepository,
    user_token: Optional[str] = None,
    journal_repository: Any = JournalRepository,
) -> Dict[str, Any]:
    """
    Read-only data collector that retrieves raw profile, daily tracking logs and
    journal entries for a specific authenticated user.

    Requirements:
    - Pure orchestration layer: reads raw data only.
    - Reuses existing repository methods (ProfileRepository.get_profile,
      DailyLogRepository.get_logs, JournalRepository.get_entries).
    - Read-only: does not create, update, or delete records.
    - Explicitly handles missing profile by raising ValueError (does not invent fake profiles).
    - Propagates any database/repository errors up to caller (including journal errors).
    - Does not reorder, filter, or interpret journal entries.
    - Returns raw dict: {"profile": <profile>, "daily_logs": <logs>, "journal_entries": <entries>}.
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    # 1. Fetch Profile
    if user_token is not None:
        profile = profile_repository.get_profile(user_id, user_token=user_token)
    else:
        profile = profile_repository.get_profile(user_id)

    if profile is None:
        raise ValueError(f"Profile not found for user_id: {user_id}")

    # 2. Fetch Daily Logs
    if user_token is not None:
        daily_logs = daily_log_repository.get_logs(user_id, user_token=user_token)
    else:
        daily_logs = daily_log_repository.get_logs(user_id)

    # 3. Fetch Journal Entries (raw, exactly as returned by the repository)
    if user_token is not None:
        journal_entries = journal_repository.get_entries(user_id, user_token=user_token)
    else:
        journal_entries = journal_repository.get_entries(user_id)

    return {
        "profile": profile,
        "daily_logs": daily_logs if daily_logs is not None else [],
        "journal_entries": journal_entries if journal_entries is not None else [],
    }


# ---------------------------------------------------------------------------
# Pure Daily-Log Aggregation Layer
# ---------------------------------------------------------------------------

def _parse_log_date(val: Any) -> Optional[date]:
    """Safely parses date, datetime, or ISO string to a datetime.date object."""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if len(val) >= 10:
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").date()
            except Exception:
                return None
    return None


def calculate_observed_days(daily_logs: List[Dict[str, Any]]) -> int:
    """
    Computes the observed calendar-day span from daily logs.

    If valid dates exist, computes the calendar span from earliest to latest log:
        (latest_date - earliest_date).days + 1
    ensuring it is at least len(daily_logs).
    If no valid dates exist, falls back to the count of logs (log_count).
    Returns 0 if daily_logs is empty.
    """
    if not daily_logs:
        return 0

    valid_dates: List[date] = []
    for log in daily_logs:
        if isinstance(log, dict):
            d = _parse_log_date(log.get("log_date"))
            if d is not None:
                valid_dates.append(d)

    if valid_dates:
        earliest = min(valid_dates)
        latest = max(valid_dates)
        calendar_span = (latest - earliest).days + 1
        return max(calendar_span, len(daily_logs))

    return len(daily_logs)


def aggregate_daily_logs(
    daily_logs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Pure aggregation function that derives measurable behavioral and progress
    features from a list of raw daily tracking logs.

    Calculates:
        - log_count: total number of log entries provided
        - latest_weight_kg: most recent non-null weight
        - weight_change_kg_7d: 7-day weight change if both window ends exist
        - weight_change_kg_14d: 14-day weight change if both window ends exist
        - weight_change_kg_28d: 28-day weight change if both window ends exist
        - completed_workouts: count of logs where workout_completed == True
        - days_with_calorie_data: count of logs where calories_consumed is not None
        - days_with_target_calories: 0 (DailyLog does not persist target calories)
        - average_energy_rating: arithmetic mean of non-null energy ratings
        - average_calories_consumed: arithmetic mean of non-null calories_consumed
        - average_protein_consumed_g: arithmetic mean of non-null protein_consumed_g
        - average_carbs_consumed_g: arithmetic mean of non-null carbs_consumed_g
        - average_fat_consumed_g: arithmetic mean of non-null fat_consumed_g
    """
    if not daily_logs:
        return {
            "log_count": 0,
            "latest_weight_kg": None,
            "weight_change_kg_7d": None,
            "weight_change_kg_14d": None,
            "weight_change_kg_28d": None,
            "completed_workouts": 0,
            "days_with_calorie_data": 0,
            "days_with_target_calories": 0,
            "average_energy_rating": None,
            "average_calories_consumed": None,
            "average_protein_consumed_g": None,
            "average_carbs_consumed_g": None,
            "average_fat_consumed_g": None,
            # Phase 3C wellness telemetry
            "average_recovery_score": None,
            "average_sleep_quality": None,
            "average_stress_level": None,
            "average_muscle_soreness": None,
        }

    total_logs = len(daily_logs)
    completed_workouts = 0
    days_with_calorie_data = 0
    energy_ratings: List[float] = []
    calories_list: List[float] = []
    protein_list: List[float] = []
    carbs_list: List[float] = []
    fat_list: List[float] = []
    # Phase 3C wellness telemetry lists
    recovery_scores: List[float] = []
    sleep_quality_scores: List[float] = []
    stress_levels: List[float] = []
    muscle_soreness_scores: List[float] = []

    # Valid dated logs sorted chronologically without mutating input
    valid_dated_logs: List[tuple[date, Dict[str, Any]]] = []

    for log in daily_logs:
        if not isinstance(log, dict):
            continue

        # Workout completion
        if log.get("workout_completed") is True:
            completed_workouts += 1

        # Calorie logging
        if log.get("calories_consumed") is not None:
            days_with_calorie_data += 1

        # Energy rating
        energy_val = _safe_float(log.get("energy_rating"))
        if energy_val is not None:
            energy_ratings.append(energy_val)

        # Nutrition macro aggregation
        cal_val = _safe_float(log.get("calories_consumed"))
        if cal_val is not None and cal_val >= 0:
            calories_list.append(cal_val)

        pro_val = _safe_float(log.get("protein_consumed_g"))
        if pro_val is not None and pro_val >= 0:
            protein_list.append(pro_val)

        carb_val = _safe_float(log.get("carbs_consumed_g"))
        if carb_val is not None and carb_val >= 0:
            carbs_list.append(carb_val)

        fat_val = _safe_float(log.get("fat_consumed_g"))
        if fat_val is not None and fat_val >= 0:
            fat_list.append(fat_val)

        # Phase 3C wellness telemetry extraction
        # recovery_score: higher = better (0=exhausted, 100=fully recovered)
        rec_val = _safe_float(log.get("recovery_score"))
        if rec_val is not None and 0.0 <= rec_val <= 100.0:
            recovery_scores.append(rec_val)

        # sleep_quality: higher = better (0=very poor, 100=excellent)
        slp_val = _safe_float(log.get("sleep_quality"))
        if slp_val is not None and 0.0 <= slp_val <= 100.0:
            sleep_quality_scores.append(slp_val)

        # stress_level: higher = worse (0=none, 100=extreme) → maps to AdaptationInput.stress_score
        str_val = _safe_float(log.get("stress_level"))
        if str_val is not None and 0.0 <= str_val <= 100.0:
            stress_levels.append(str_val)

        # muscle_soreness: higher = worse (0=none, 100=extreme) → maps to AdaptationInput.injury_risk
        sor_val = _safe_float(log.get("muscle_soreness"))
        if sor_val is not None and 0.0 <= sor_val <= 100.0:
            muscle_soreness_scores.append(sor_val)

        # Date parsing for time-based trends
        parsed_date = _parse_log_date(log.get("log_date"))
        if parsed_date is not None:
            valid_dated_logs.append((parsed_date, log))

    # DailyLog currently does not persist the user's target calories.
    # Target-calorie adherence requires profile target data and will be combined later.
    days_with_target_calories = 0

    average_energy_rating = (
        round(sum(energy_ratings) / len(energy_ratings), 2)
        if energy_ratings
        else None
    )
    average_calories_consumed = (
        round(sum(calories_list) / len(calories_list), 2)
        if calories_list
        else None
    )
    average_protein_consumed_g = (
        round(sum(protein_list) / len(protein_list), 2)
        if protein_list
        else None
    )
    average_carbs_consumed_g = (
        round(sum(carbs_list) / len(carbs_list), 2)
        if carbs_list
        else None
    )
    average_fat_consumed_g = (
        round(sum(fat_list) / len(fat_list), 2)
        if fat_list
        else None
    )

    # Sort dated logs chronologically before calculating time-based trends
    valid_dated_logs.sort(key=lambda item: item[0])

    dated_weight_entries: Dict[date, float] = {}
    for log_date, log in valid_dated_logs:
        weight_val = _safe_float(log.get("weight_kg"))
        if weight_val is not None and weight_val > 0:
            dated_weight_entries[log_date] = weight_val

    latest_weight_kg: Optional[float] = None
    weight_change_kg_7d: Optional[float] = None
    weight_change_kg_14d: Optional[float] = None
    weight_change_kg_28d: Optional[float] = None

    if dated_weight_entries:
        latest_date = max(dated_weight_entries.keys())
        latest_weight_kg = dated_weight_entries[latest_date]

        # 7-day weight change (requires weight data on both sides of the 7-day window)
        date_7d = latest_date - timedelta(days=7)
        if date_7d in dated_weight_entries:
            weight_change_kg_7d = calculate_weight_change(
                dated_weight_entries[date_7d], latest_weight_kg
            )

        # 14-day weight change (requires weight data on both sides of the 14-day window)
        date_14d = latest_date - timedelta(days=14)
        if date_14d in dated_weight_entries:
            weight_change_kg_14d = calculate_weight_change(
                dated_weight_entries[date_14d], latest_weight_kg
            )

        # 28-day weight change (requires weight data on both sides of the 28-day window)
        date_28d = latest_date - timedelta(days=28)
        if date_28d in dated_weight_entries:
            weight_change_kg_28d = calculate_weight_change(
                dated_weight_entries[date_28d], latest_weight_kg
            )

    # Phase 3C wellness telemetry averages (None when no valid observations)
    average_recovery_score = (
        round(sum(recovery_scores) / len(recovery_scores), 2)
        if recovery_scores
        else None
    )
    average_sleep_quality = (
        round(sum(sleep_quality_scores) / len(sleep_quality_scores), 2)
        if sleep_quality_scores
        else None
    )
    average_stress_level = (
        round(sum(stress_levels) / len(stress_levels), 2)
        if stress_levels
        else None
    )
    average_muscle_soreness = (
        round(sum(muscle_soreness_scores) / len(muscle_soreness_scores), 2)
        if muscle_soreness_scores
        else None
    )

    return {
        "log_count": total_logs,
        "latest_weight_kg": latest_weight_kg,
        "weight_change_kg_7d": weight_change_kg_7d,
        "weight_change_kg_14d": weight_change_kg_14d,
        "weight_change_kg_28d": weight_change_kg_28d,
        "completed_workouts": completed_workouts,
        "days_with_calorie_data": days_with_calorie_data,
        "days_with_target_calories": days_with_target_calories,
        "average_energy_rating": average_energy_rating,
        "average_calories_consumed": average_calories_consumed,
        "average_protein_consumed_g": average_protein_consumed_g,
        "average_carbs_consumed_g": average_carbs_consumed_g,
        "average_fat_consumed_g": average_fat_consumed_g,
        # Phase 3C wellness telemetry
        "average_recovery_score": average_recovery_score,
        "average_sleep_quality": average_sleep_quality,
        "average_stress_level": average_stress_level,
        "average_muscle_soreness": average_muscle_soreness,
    }


# ---------------------------------------------------------------------------
DEFAULT_JOURNAL_FRESHNESS_DAYS = 7
MINIMUM_ADHERENCE_LOGS = 7
MINIMUM_ADHERENCE_DAYS = 7


def has_sufficient_adherence_data(
    log_count: int,
    observed_days: int,
    minimum_logs: int = MINIMUM_ADHERENCE_LOGS,
    minimum_days: int = MINIMUM_ADHERENCE_DAYS,
) -> bool:
    """
    Determines whether sufficient daily logs and observation window exist to
    evaluate empirical weekly adherence.
    Requires at least 7 logs and at least 7 calendar days of observation.
    """
    try:
        return int(log_count) >= int(minimum_logs) and int(observed_days) >= int(minimum_days)
    except Exception:
        return False


def prepare_adaptation_input(
    profile: Dict[str, Any],
    daily_logs: List[Dict[str, Any]],
    journal_entries: Optional[List[Dict[str, Any]]] = None,
    *,
    active_meal_plan: Optional[Dict[str, Any]] = None,
    active_workout_plan: Optional[Dict[str, Any]] = None,
    journal_max_age_days: Optional[int] = DEFAULT_JOURNAL_FRESHNESS_DAYS,
    reference_time: Optional[datetime] = None,
) -> AdaptationInput:
    """
    Pure function that bridges raw profile, daily-log, journal, and active plan data
    into a validated AdaptationInput instance.

    Steps:
        1. Delegates to build_adaptation_context() for aggregation with freshness windowing.
        2. Reads progress values from context["progress"].
        3. Reads journal values from context["journal"].
        4. Extracts required profile fields (goal_type, target metrics, etc.).
        5. Uses the aggregated latest_weight_kg when available; otherwise falls
           back to the profile's weight_kg.
        6. Passes through 7/14/28-day weight-change fields from aggregation.
        7. Passes latest_journal_summary into AdaptationInput.
        8. Passes latest_journal_sentiment through normalize_journal_sentiment() before
           creating AdaptationInput.
        9. Resolves effective nutrition and workout targets: prefers active persisted plans
           when valid; falls back to static profile targets when active plans are missing,
           zero, negative, or malformed.
        10. Computes empirical nutrition_score and training_quality from progress and effective targets.
        11. Computes empirical adherence_percent when sufficient logging history exists (>= 7 logs and >= 7 days).
        12. Does NOT compute readiness, adjustments, recommendations, or call
            compute_adaptation().

    If a required profile field is missing, Pydantic validation will raise
    rather than silently inventing a default value.
    """
    context = build_adaptation_context(
        profile,
        daily_logs,
        journal_entries or [],
        journal_max_age_days=journal_max_age_days,
        reference_time=reference_time,
    )
    progress = context["progress"]
    journal = context["journal"]

    # Resolve current weight: prefer latest logged weight, fall back to profile
    current_weight = progress.get("latest_weight_kg")
    if current_weight is None:
        current_weight = profile.get("weight_kg")

    # Extract target metrics from profile (nested dict computed at onboarding)
    target_metrics = profile.get("target_metrics") or {}

    # Resolve active nutrition targets with fallback to profile target_metrics
    effective_target_calories: Optional[int] = None
    effective_protein_g: Optional[float] = None
    effective_carbs_g: Optional[float] = None
    effective_fat_g: Optional[float] = None

    if isinstance(active_meal_plan, dict):
        act_cals = _safe_float(active_meal_plan.get("target_calories"))
        if act_cals is not None and act_cals > 0:
            effective_target_calories = int(round(act_cals))

        act_p = _safe_float(active_meal_plan.get("target_protein_g"))
        if act_p is not None and act_p > 0:
            effective_protein_g = float(act_p)

        act_c = _safe_float(active_meal_plan.get("target_carbs_g"))
        if act_c is not None and act_c > 0:
            effective_carbs_g = float(act_c)

        act_f = _safe_float(active_meal_plan.get("target_fat_g"))
        if act_f is not None and act_f > 0:
            effective_fat_g = float(act_f)

    if effective_target_calories is None:
        effective_target_calories = target_metrics.get("target_calories")
    if effective_protein_g is None:
        effective_protein_g = target_metrics.get("protein_g")
    if effective_carbs_g is None:
        effective_carbs_g = target_metrics.get("carbs_g")
    if effective_fat_g is None:
        effective_fat_g = target_metrics.get("fat_g")

    # Resolve active workout frequency with fallback to profile workout_days_per_week
    effective_workout_days: Optional[int] = None
    if isinstance(active_workout_plan, dict):
        act_days = _safe_float(active_workout_plan.get("days_per_week"))
        if act_days is not None and act_days > 0:
            effective_workout_days = int(round(act_days))

    if effective_workout_days is None:
        effective_workout_days = profile.get("workout_days_per_week")

    # Extract journal context
    raw_sentiment = journal.get("latest_journal_sentiment")
    normalized_sentiment = normalize_journal_sentiment(raw_sentiment)

    # Compute empirical nutrition, training, and adherence signals
    calculated_nutrition_score: Optional[float] = None
    calculated_training_quality: Optional[float] = None
    calculated_adherence_percent: Optional[float] = None

    if progress.get("log_count", 0) > 0:
        calculated_nutrition_score = score_nutrition(
            actual_calories=progress.get("average_calories_consumed"),
            target_calories=effective_target_calories,
            actual_protein_g=progress.get("average_protein_consumed_g"),
            target_protein_g=effective_protein_g,
            actual_carbs_g=progress.get("average_carbs_consumed_g"),
            target_carbs_g=effective_carbs_g,
            actual_fat_g=progress.get("average_fat_consumed_g"),
            target_fat_g=effective_fat_g,
        )

        has_workout_data = any(
            isinstance(log, dict) and "workout_completed" in log and log.get("workout_completed") is not None
            for log in daily_logs
        )
        planned_workouts = effective_workout_days
        completed_workouts = progress.get("completed_workouts") if has_workout_data else None
        energy_rating = progress.get("average_energy_rating")

        observed_days = calculate_observed_days(daily_logs)
        calculated_training_quality = score_training_quality(
            completed_workouts=completed_workouts,
            planned_workouts=planned_workouts,
            average_energy_rating=energy_rating,
            window_days=observed_days,
        )

        # Adherence calculation: requires sufficient data window (at least 7 logs and 7 calendar days)
        if has_sufficient_adherence_data(progress.get("log_count", 0), observed_days):
            has_calorie_data = any(
                isinstance(log, dict) and log.get("calories_consumed") is not None
                for log in daily_logs
            )

            planned_workouts_adh: Optional[float] = None
            completed_workouts_adh: Optional[int] = None
            pw = _safe_float(effective_workout_days)
            if has_workout_data and pw is not None and pw > 0:
                completed_workouts_adh = progress.get("completed_workouts", 0)
                planned_workouts_adh = pw * (float(observed_days) / 7.0)

            days_with_calorie_data_adh: Optional[int] = None
            days_with_target_calories_adh: Optional[Union[int, float]] = None
            target_cals = _safe_float(
                effective_target_calories or profile.get("target_calories")
            )
            if has_calorie_data and target_cals is not None and target_cals > 0:
                days_with_calorie_data_adh = progress.get("days_with_calorie_data", 0)
                days_with_target_calories_adh = observed_days

            calculated_adherence_percent = calculate_adherence_percent(
                completed_workouts=completed_workouts_adh,
                planned_workouts=planned_workouts_adh,
                days_with_calorie_data=days_with_calorie_data_adh,
                days_with_target_calories=days_with_target_calories_adh,
            )

    calculated_plateau_probability = calculate_plateau_probability(
        weight_change_14d_kg=progress.get("weight_change_kg_14d"),
        weight_change_28d_kg=progress.get("weight_change_kg_28d"),
        goal_type=profile.get("goal_type", ""),
    )

    # Phase 3C: resolve wellness telemetry from aggregated daily logs.
    # Semantic mapping (direction preserved — no inversion applied):
    #   progress["average_recovery_score"]  → AdaptationInput.recovery_score  (higher = better)
    #   progress["average_sleep_quality"]   → AdaptationInput.sleep_quality   (higher = better)
    #   progress["average_stress_level"]    → AdaptationInput.stress_score    (higher = worse, risk penalty)
    #   progress["average_muscle_soreness"] → AdaptationInput.injury_risk     (higher = worse, risk penalty)
    # All four remain None when absent from logs; no neutral value is invented.
    empirical_recovery_score: Optional[float] = progress.get("average_recovery_score")
    empirical_sleep_quality: Optional[float] = progress.get("average_sleep_quality")
    empirical_stress_score: Optional[float] = progress.get("average_stress_level")
    empirical_injury_risk: Optional[float] = progress.get("average_muscle_soreness")

    return AdaptationInput(
        current_weight_kg=current_weight,  # type: ignore[arg-type]
        target_weight_kg=profile.get("target_weight_kg"),  # type: ignore[arg-type]
        goal_type=profile.get("goal_type"),  # type: ignore[arg-type]
        target_calories=effective_target_calories,  # type: ignore[arg-type]
        target_protein_g=effective_protein_g,  # type: ignore[arg-type]
        target_carbs_g=effective_carbs_g,  # type: ignore[arg-type]
        target_fat_g=effective_fat_g,  # type: ignore[arg-type]
        workout_days_per_week=effective_workout_days,  # type: ignore[arg-type]
        experience_level=profile.get("experience_level"),  # type: ignore[arg-type]
        log_count=progress["log_count"],
        adherence_percent=calculated_adherence_percent,
        nutrition_score=calculated_nutrition_score,
        training_quality=calculated_training_quality,
        plateau_probability=calculated_plateau_probability,
        # Phase 3C wellness telemetry (None when not present in logs)
        recovery_score=empirical_recovery_score,
        sleep_quality=empirical_sleep_quality,
        stress_score=empirical_stress_score,
        injury_risk=empirical_injury_risk,
        weight_change_kg_7d=progress.get("weight_change_kg_7d"),
        weight_change_kg_14d=progress.get("weight_change_kg_14d"),
        weight_change_kg_28d=progress.get("weight_change_kg_28d"),
        latest_journal_summary=journal.get("latest_journal_summary"),
        latest_journal_sentiment=normalized_sentiment,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Pure Journal Aggregation Layer
# ---------------------------------------------------------------------------

def _parse_journal_date(val: Any) -> Optional[date]:
    """Parse a journal entry's created_at timestamp or date string to a date.

    Handles:
        - datetime.date objects (returned as-is)
        - datetime.datetime objects (converted to date)
        - ISO-8601 timestamp strings from Supabase (e.g. "2026-09-15T10:30:00+00:00")
        - YYYY-MM-DD date strings
    Returns None on malformed or missing values.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if len(val) >= 10:
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").date()
            except Exception:
                return None
    return None


def _parse_journal_timestamp(val: Any) -> Optional[datetime]:
    """Parse a journal created_at value to a timezone-aware UTC datetime for ordering.

    Handles datetime/date objects, ISO-8601 strings (with or without offset or a trailing
    "Z"), and YYYY-MM-DD strings. Naive values are treated as UTC. Returns None for
    missing or malformed values.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, date):
        dt = datetime(val.year, val.month, val.day)
    elif isinstance(val, str):
        s = val.strip()
        if len(s) < 10:
            return None
        if s[-1] in ("Z", "z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.strptime(s[:10], "%Y-%m-%d")
            except ValueError:
                return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_journal_fresh(
    entry_time: Any,
    max_age_days: int = DEFAULT_JOURNAL_FRESHNESS_DAYS,
    reference_time: Optional[datetime] = None,
) -> bool:
    """
    Checks whether a journal timestamp or datetime is within the freshness window.

    Rules:
        - Parses entry_time using _parse_journal_timestamp (returns False if unparseable/missing).
        - Normalizes reference_time to timezone-aware UTC (defaults to datetime.now(timezone.utc) if None).
        - Returns True if parsed entry_timestamp >= cutoff (ref - timedelta(days=max_age_days)).
        - Returns False if parsed entry_timestamp < cutoff.
    """
    dt = _parse_journal_timestamp(entry_time)
    if dt is None:
        return False

    if reference_time is None:
        ref = datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        ref = reference_time.replace(tzinfo=timezone.utc)
    else:
        ref = reference_time.astimezone(timezone.utc)

    cutoff = ref - timedelta(days=max_age_days)
    return dt >= cutoff


_ALLOWED_JOURNAL_SENTIMENTS = frozenset({"fatigued", "motivated", "consistent"})


def normalize_journal_sentiment(value: Optional[str]) -> Optional[str]:
    """
    Normalizes a raw journal sentiment tag to match AdaptationInput's allowed literal values.

    Rules:
        - None -> None
        - Empty or whitespace-only string -> None
        - Strips surrounding whitespace and converts to lowercase
        - Preserves only: "fatigued", "motivated", "consistent"
        - Any other value, including "stressed", "unknown", or arbitrary text -> None
        - Does NOT invent mappings (e.g. does not map "stressed" to "fatigued")
        - Pure function with no side effects
    """
    if value is None or not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    if cleaned in _ALLOWED_JOURNAL_SENTIMENTS:
        return cleaned
    return None


def aggregate_journal_entries(
    journal_entries: List[Dict[str, Any]],
    *,
    max_age_days: Optional[int] = None,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Pure aggregation function that derives journal context from a list of
    raw journal entry records.

    Returns:
        - journal_count: total number of journal entries provided
        - latest_journal_summary: summary text from the most recent entry (or None)
        - latest_journal_sentiment: sentiment_tag from the most recent entry (or None)

    Rules:
        - Selects the most recent entry by full created_at timestamp (normalized to UTC),
          so multiple entries on the same day are ordered by time of day.
        - The result does not depend on the order of the input list. Exact timestamp
          ties are resolved by entry id.
        - Does not mutate the input.
        - Does NOT invent summary or sentiment; returns None when absent.
        - Entries without a parseable created_at are counted but excluded
          from latest-entry selection.
        - If max_age_days is provided, verifies that the latest entry is within the freshness
          window (latest_dt >= reference_time - max_age_days). If stale, returns None for
          summary and sentiment while preserving journal_count.
    """
    if not journal_entries:
        return {
            "journal_count": 0,
            "latest_journal_summary": None,
            "latest_journal_sentiment": None,
        }

    dated_entries: List[tuple[datetime, Dict[str, Any]]] = []

    for entry in journal_entries:
        if not isinstance(entry, dict):
            continue
        parsed = _parse_journal_timestamp(entry.get("created_at"))
        if parsed is not None:
            dated_entries.append((parsed, entry))

    journal_count = len(journal_entries)

    if not dated_entries:
        # All entries lack parseable timestamps: count them but can't pick latest
        return {
            "journal_count": journal_count,
            "latest_journal_summary": None,
            "latest_journal_sentiment": None,
        }

    # Most recent by full UTC timestamp; exact ties resolve by id so the result
    # never depends on input order
    latest_dt, latest_entry = max(
        dated_entries,
        key=lambda t: (t[0], str(t[1].get("id") or "")),
    )

    # Freshness evaluation if max_age_days is specified
    if max_age_days is not None:
        if not is_journal_fresh(latest_dt, max_age_days=max_age_days, reference_time=reference_time):
            return {
                "journal_count": journal_count,
                "latest_journal_summary": None,
                "latest_journal_sentiment": None,
            }

    # Extract summary: stored inside ai_feedback dict, or as top-level fallback
    ai_feedback = latest_entry.get("ai_feedback")
    if isinstance(ai_feedback, dict):
        summary = ai_feedback.get("summary") or None
    else:
        summary = latest_entry.get("summary") or None

    # Extract sentiment: stored as top-level sentiment_tag
    sentiment = latest_entry.get("sentiment_tag") or None

    return {
        "journal_count": journal_count,
        "latest_journal_summary": summary,
        "latest_journal_sentiment": sentiment,
    }


# ---------------------------------------------------------------------------
# Combined Adaptation-Data Preparation Layer
# ---------------------------------------------------------------------------

def build_adaptation_context(
    profile: Dict[str, Any],
    daily_logs: List[Dict[str, Any]],
    journal_entries: List[Dict[str, Any]],
    *,
    journal_max_age_days: Optional[int] = None,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Pure function that combines daily-log and journal aggregation into a
    single adaptation context dict.

    Args:
        profile: User profile dict. Accepted for future compatibility but
                 not used for calculations in this version.
        daily_logs: Raw daily tracking log records.
        journal_entries: Raw journal entry records.
        journal_max_age_days: Optional maximum age in days for journal freshness.
        reference_time: Optional reference datetime for freshness evaluation.

    Returns:
        {
            "progress": <output of aggregate_daily_logs>,
            "journal": <output of aggregate_journal_entries>,
        }

    Does NOT modify inputs, call repositories/APIs/LLMs, duplicate
    aggregation logic, or add any inferred metrics beyond what the
    existing aggregation functions already produce.
    """
    return {
        "progress": aggregate_daily_logs(daily_logs),
        "journal": aggregate_journal_entries(
            journal_entries,
            max_age_days=journal_max_age_days,
            reference_time=reference_time,
        ),
    }


_TARGET_METRICS_REQUIRED_PROFILE_FIELDS = (
    "weight_kg",
    "height_cm",
    "age",
    "gender",
    "activity_level",
    "goal_type",
)


def ensure_target_metrics(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a shallow copy of a profile row that is guaranteed to carry target_metrics.

    Supabase does not persist target_metrics (it is not a profiles column), so a profile
    loaded from the database has none. When it is missing or empty, it is recomputed with the
    same deterministic engine call that GET /profile uses (calculate_target_metrics).
    Existing non-empty target_metrics are kept as-is.

    Raises ValueError naming every required profile field that is missing. Never invents
    defaults. Does not mutate the input.
    """
    resolved = dict(profile)
    if resolved.get("target_metrics"):
        return resolved

    missing = [
        f for f in _TARGET_METRICS_REQUIRED_PROFILE_FIELDS if resolved.get(f) is None
    ]
    if missing:
        raise ValueError(
            "Cannot compute target metrics; profile is missing: " + ", ".join(missing)
        )

    body_fat = resolved.get("body_fat_pct")
    resolved["target_metrics"] = calculate_target_metrics(
        weight_kg=float(resolved["weight_kg"]),
        height_cm=float(resolved["height_cm"]),
        age=int(resolved["age"]),
        gender=str(resolved["gender"]),
        activity_level=str(resolved["activity_level"]),
        goal_type=str(resolved["goal_type"]),
        body_fat_pct=float(body_fat) if body_fat is not None else None,
    )
    return resolved


def compute_adaptation_for_user(
    user_id: str,
    user_token: Optional[str] = None,
    profile_repository: Any = ProfileRepository,
    daily_log_repository: Any = DailyLogRepository,
    journal_repository: Any = JournalRepository,
    meal_plan_repository: Any = MealPlanRepository,
    workout_plan_repository: Any = WorkoutPlanRepository,
) -> AdaptationDecision:
    """
    Read-only pipeline: collect_adaptation_data -> ensure_target_metrics ->
    resolve active plans -> prepare_adaptation_input -> compute_adaptation.

    Persists nothing. Raises ValueError for a missing profile or a profile too incomplete
    to derive targets. Repository errors propagate to the caller.
    """
    data = collect_adaptation_data(
        user_id=user_id,
        profile_repository=profile_repository,
        daily_log_repository=daily_log_repository,
        user_token=user_token,
        journal_repository=journal_repository,
    )
    profile = ensure_target_metrics(data["profile"])

    active_meal_plan = None
    if meal_plan_repository and hasattr(meal_plan_repository, "get_active_meal_plan"):
        active_meal_plan = meal_plan_repository.get_active_meal_plan(
            user_id=user_id, user_token=user_token
        )

    active_workout_plan = None
    if workout_plan_repository and hasattr(workout_plan_repository, "get_active_workout_plan"):
        active_workout_plan = workout_plan_repository.get_active_workout_plan(
            user_id=user_id, user_token=user_token
        )

    adaptation_input = prepare_adaptation_input(
        profile,
        data["daily_logs"],
        data["journal_entries"],
        active_meal_plan=active_meal_plan,
        active_workout_plan=active_workout_plan,
    )
    return compute_adaptation(adaptation_input)
