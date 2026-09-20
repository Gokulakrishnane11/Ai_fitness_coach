"""
Centralized AI Adaptation Engine Models & Pure Scoring Layer (Phase 8).
Defines strictly typed Pydantic models, zero-data neutrality helpers,
and stateless empirical scoring functions for behavioral adaptation decisions.
"""

from typing import List, Literal, Optional, Union, Any, Dict
from datetime import date, datetime, timedelta, timezone
from pydantic import BaseModel, Field
from app.db.supabase import ProfileRepository, DailyLogRepository, JournalRepository
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
    planned_workouts: Optional[int],
    days_with_calorie_data: Optional[int],
    days_with_target_calories: Optional[int],
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
        weight_change_kg_7d=weight_change_kg_7d,
        weight_change_kg_14d=weight_change_kg_14d,
        weight_change_kg_28d=weight_change_kg_28d,
        latest_journal_summary=latest_journal_summary,
        latest_journal_sentiment=latest_journal_sentiment,  # type: ignore[arg-type]
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

    # 3. Derive Operational Flags
    high_fatigue_flag = bool(
        input_data.recovery_score is not None and eval_recovery is not None and eval_recovery < 50
    )
    plateau_detected = bool(
        input_data.plateau_probability is not None and eval_plateau is not None and eval_plateau >= 70
    )

    # 4. Calculate Readiness Factor
    # NOTE: Neutral unmeasured secondary scores (100.0) are used strictly as a computational
    # default in calculate_readiness_factor() so that missing secondary dimensions (nutrition,
    # training quality, motivation) do NOT impose an artificial penalty on the user's readiness.
    # These neutral values are computational stand-ins, not verified user measurements.
    readiness_factor = calculate_readiness_factor(
        adherence_score=decision_adherence,
        recovery_score=decision_recovery,
        stress_score=decision_stress,
        sleep_quality=decision_sleep,
        plateau_probability=decision_plateau,
        injury_risk=decision_injury,
        nutrition_score=100.0,
        training_quality=100.0,
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
    else:
        coaching_summary = "Consistent progress and healthy readiness metrics observed across recent logs."

    # 7. Conservative First-Version Adjustments (Zero modifications)
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
        actionable_recommendations=recommendations,
        coaching_summary=coaching_summary,
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


def _safe_float(val: Any) -> Optional[float]:
    """Safely casts a value to float, returning None on failure or if val is None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


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
        }

    total_logs = len(daily_logs)
    completed_workouts = 0
    days_with_calorie_data = 0
    energy_ratings: List[float] = []

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
    }


# ---------------------------------------------------------------------------
# Pure Adaptation-Input Preparation Layer
# ---------------------------------------------------------------------------

def prepare_adaptation_input(
    profile: Dict[str, Any],
    daily_logs: List[Dict[str, Any]],
    journal_entries: Optional[List[Dict[str, Any]]] = None,
) -> AdaptationInput:
    """
    Pure function that bridges raw profile, daily-log, and journal data into a validated
    AdaptationInput instance.

    Steps:
        1. Delegates to build_adaptation_context() for aggregation.
        2. Reads progress values from context["progress"].
        3. Reads journal values from context["journal"].
        4. Extracts required profile fields (goal_type, target metrics, etc.).
        5. Uses the aggregated latest_weight_kg when available; otherwise falls
           back to the profile's weight_kg.
        6. Passes through 7/14/28-day weight-change fields from aggregation.
        7. Passes latest_journal_summary into AdaptationInput.
        8. Passes latest_journal_sentiment through normalize_journal_sentiment() before
           creating AdaptationInput.
        9. Does NOT compute readiness, adjustments, recommendations, or call
           compute_adaptation().

    If a required profile field is missing, Pydantic validation will raise
    rather than silently inventing a default value.
    """
    context = build_adaptation_context(profile, daily_logs, journal_entries or [])
    progress = context["progress"]
    journal = context["journal"]

    # Resolve current weight: prefer latest logged weight, fall back to profile
    current_weight = progress.get("latest_weight_kg")
    if current_weight is None:
        current_weight = profile.get("weight_kg")

    # Extract target metrics from profile (nested dict computed at onboarding)
    target_metrics = profile.get("target_metrics") or {}

    # Extract journal context
    raw_sentiment = journal.get("latest_journal_sentiment")
    normalized_sentiment = normalize_journal_sentiment(raw_sentiment)

    return AdaptationInput(
        current_weight_kg=current_weight,  # type: ignore[arg-type]
        target_weight_kg=profile.get("target_weight_kg"),  # type: ignore[arg-type]
        goal_type=profile.get("goal_type"),  # type: ignore[arg-type]
        target_calories=target_metrics.get("target_calories"),  # type: ignore[arg-type]
        target_protein_g=target_metrics.get("protein_g"),  # type: ignore[arg-type]
        target_carbs_g=target_metrics.get("carbs_g"),  # type: ignore[arg-type]
        target_fat_g=target_metrics.get("fat_g"),  # type: ignore[arg-type]
        workout_days_per_week=profile.get("workout_days_per_week"),  # type: ignore[arg-type]
        experience_level=profile.get("experience_level"),  # type: ignore[arg-type]
        log_count=progress["log_count"],
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
    _, latest_entry = max(
        dated_entries,
        key=lambda t: (t[0], str(t[1].get("id") or "")),
    )

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
) -> Dict[str, Any]:
    """
    Pure function that combines daily-log and journal aggregation into a
    single adaptation context dict.

    Args:
        profile: User profile dict. Accepted for future compatibility but
                 not used for calculations in this version.
        daily_logs: Raw daily tracking log records.
        journal_entries: Raw journal entry records.

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
        "journal": aggregate_journal_entries(journal_entries),
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
) -> AdaptationDecision:
    """
    Read-only pipeline: collect_adaptation_data -> ensure_target_metrics ->
    prepare_adaptation_input -> compute_adaptation.

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
    adaptation_input = prepare_adaptation_input(
        profile, data["daily_logs"], data["journal_entries"]
    )
    return compute_adaptation(adaptation_input)
