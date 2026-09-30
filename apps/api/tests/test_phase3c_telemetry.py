"""
Phase 3C Test Suite — Recovery / Sleep / Stress / Injury Telemetry.

Covers:
A.  Daily-log schema accepts all four telemetry fields.
B.  Minimum value 0 is accepted.
C.  Maximum value 100 is accepted.
D.  Values below 0 are rejected by the schema.
E.  Values above 100 are rejected by the schema.
F.  Missing/null values remain valid.
G.  Aggregation calculates the expected value from multiple daily logs.
H.  Partial telemetry: each signal in isolation and arbitrary combinations.
I.  No telemetry preserves previous adaptation behavior.
J.  Correct semantic direction (higher recovery = better; higher stress/soreness = worse).
K.  End-to-end adaptation test with realistic telemetry values.
L.  Existing Phase 3B active-plan adherence behavior still passes.
M.  Existing diet/workout adjustment behavior still passes.
"""

import pytest
from pydantic import ValidationError
from app.modules.progress import DailyLogCreateSchema
from app.engine.adaptation import (
    aggregate_daily_logs,
    prepare_adaptation_input,
    compute_adaptation,
    AdaptationInput,
)
from datetime import date


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_full_profile(
    *,
    goal_type: str = "fat_loss",
    workout_days_per_week: int = 4,
    experience_level: str = "intermediate",
) -> dict:
    return {
        "weight_kg": 80.0,
        "target_weight_kg": 72.0,
        "goal_type": goal_type,
        "target_metrics": {
            "target_calories": 2100,
            "protein_g": 160.0,
            "carbs_g": 220.0,
            "fat_g": 65.0,
        },
        "workout_days_per_week": workout_days_per_week,
        "experience_level": experience_level,
    }


def _make_log(log_date: str, **kwargs) -> dict:
    """Helper to produce a minimal daily log dict."""
    return {"log_date": log_date, **kwargs}


def _make_base_adaptation_input(
    log_count: int = 10,
    **kwargs,
) -> AdaptationInput:
    """Constructs a minimal valid AdaptationInput for engine tests."""
    defaults = dict(
        current_weight_kg=80.0,
        target_weight_kg=72.0,
        goal_type="fat_loss",
        target_calories=2100.0,
        target_protein_g=160.0,
        target_carbs_g=220.0,
        target_fat_g=65.0,
        workout_days_per_week=4,
        experience_level="intermediate",
        log_count=log_count,
        adherence_percent=85.0,
    )
    defaults.update(kwargs)
    return AdaptationInput(**defaults)


# ===========================================================================
# A. Schema accepts all four fields
# ===========================================================================

class TestSchemaAcceptsTelemetryFields:
    def test_all_four_fields_accepted(self):
        """A. Schema accepts all four telemetry fields simultaneously."""
        log = DailyLogCreateSchema(
            log_date=date(2026, 9, 28),
            recovery_score=80,
            sleep_quality=75,
            stress_level=30,
            muscle_soreness=20,
        )
        assert log.recovery_score == 80
        assert log.sleep_quality == 75
        assert log.stress_level == 30
        assert log.muscle_soreness == 20

    # B. Minimum value 0 is accepted
    def test_minimum_value_zero_accepted(self):
        """B. Minimum value 0 is accepted for all four fields."""
        log = DailyLogCreateSchema(
            log_date=date(2026, 9, 28),
            recovery_score=0,
            sleep_quality=0,
            stress_level=0,
            muscle_soreness=0,
        )
        assert log.recovery_score == 0
        assert log.sleep_quality == 0
        assert log.stress_level == 0
        assert log.muscle_soreness == 0

    # C. Maximum value 100 is accepted
    def test_maximum_value_100_accepted(self):
        """C. Maximum value 100 is accepted for all four fields."""
        log = DailyLogCreateSchema(
            log_date=date(2026, 9, 28),
            recovery_score=100,
            sleep_quality=100,
            stress_level=100,
            muscle_soreness=100,
        )
        assert log.recovery_score == 100
        assert log.sleep_quality == 100
        assert log.stress_level == 100
        assert log.muscle_soreness == 100


# ===========================================================================
# D. Values below 0 are rejected
# ===========================================================================

class TestSchemaBelowMinRejected:
    @pytest.mark.parametrize("field", [
        "recovery_score", "sleep_quality", "stress_level", "muscle_soreness"
    ])
    def test_value_below_zero_rejected(self, field):
        """D. Values below 0 are rejected by the schema."""
        with pytest.raises(ValidationError):
            DailyLogCreateSchema(log_date=date(2026, 9, 28), **{field: -1})


# ===========================================================================
# E. Values above 100 are rejected
# ===========================================================================

class TestSchemaAboveMaxRejected:
    @pytest.mark.parametrize("field", [
        "recovery_score", "sleep_quality", "stress_level", "muscle_soreness"
    ])
    def test_value_above_100_rejected(self, field):
        """E. Values above 100 are rejected by the schema."""
        with pytest.raises(ValidationError):
            DailyLogCreateSchema(log_date=date(2026, 9, 28), **{field: 101})


# ===========================================================================
# F. Missing / null values remain valid
# ===========================================================================

class TestSchemaNullValuesValid:
    def test_all_telemetry_fields_missing_produces_none(self):
        """F. Omitting all four fields produces None defaults (not an error)."""
        log = DailyLogCreateSchema(log_date=date(2026, 9, 28))
        assert log.recovery_score is None
        assert log.sleep_quality is None
        assert log.stress_level is None
        assert log.muscle_soreness is None

    def test_explicit_none_values_accepted(self):
        """F. Explicit None values are accepted."""
        log = DailyLogCreateSchema(
            log_date=date(2026, 9, 28),
            recovery_score=None,
            sleep_quality=None,
            stress_level=None,
            muscle_soreness=None,
        )
        assert log.recovery_score is None
        assert log.sleep_quality is None
        assert log.stress_level is None
        assert log.muscle_soreness is None

    def test_existing_fields_still_work_without_telemetry(self):
        """F. Existing fields (weight, calories, workout) still work when telemetry absent."""
        log = DailyLogCreateSchema(
            log_date=date(2026, 9, 28),
            weight_kg=80.5,
            calories_consumed=2100,
            workout_completed=True,
            energy_rating=8,
        )
        assert log.weight_kg == 80.5
        assert log.recovery_score is None
        assert log.muscle_soreness is None


# ===========================================================================
# G. Aggregation produces correct averages
# ===========================================================================

class TestAggregationCorrectAverages:
    def test_recovery_score_average(self):
        """G. recovery_score averages correctly across multiple logs."""
        logs = [
            _make_log("2026-09-01", recovery_score=60),
            _make_log("2026-09-02", recovery_score=80),
            _make_log("2026-09-03", recovery_score=70),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_recovery_score"] == 70.0

    def test_sleep_quality_average(self):
        """G. sleep_quality averages correctly across multiple logs."""
        logs = [
            _make_log("2026-09-01", sleep_quality=50),
            _make_log("2026-09-02", sleep_quality=90),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_sleep_quality"] == 70.0

    def test_stress_level_average(self):
        """G. stress_level averages correctly across multiple logs."""
        logs = [
            _make_log("2026-09-01", stress_level=30),
            _make_log("2026-09-02", stress_level=70),
            _make_log("2026-09-03", stress_level=50),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_stress_level"] == 50.0

    def test_muscle_soreness_average(self):
        """G. muscle_soreness averages correctly across multiple logs."""
        logs = [
            _make_log("2026-09-01", muscle_soreness=20),
            _make_log("2026-09-02", muscle_soreness=80),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_muscle_soreness"] == 50.0

    def test_rounding_to_two_decimal_places(self):
        """G. Averages are rounded to 2 decimal places."""
        logs = [
            _make_log("2026-09-01", recovery_score=70),
            _make_log("2026-09-02", recovery_score=80),
            _make_log("2026-09-03", recovery_score=75),
        ]
        result = aggregate_daily_logs(logs)
        # (70 + 80 + 75) / 3 = 75.0
        assert result["average_recovery_score"] == 75.0

    def test_fractional_average_rounded(self):
        """G. Fractional averages are rounded to 2 decimal places."""
        logs = [
            _make_log("2026-09-01", stress_level=33),
            _make_log("2026-09-02", stress_level=34),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_stress_level"] == 33.5

    def test_empty_logs_all_telemetry_none(self):
        """G. Empty log list returns None for all telemetry keys."""
        result = aggregate_daily_logs([])
        assert result["average_recovery_score"] is None
        assert result["average_sleep_quality"] is None
        assert result["average_stress_level"] is None
        assert result["average_muscle_soreness"] is None


# ===========================================================================
# H. Partial telemetry — each signal in isolation and combinations
# ===========================================================================

class TestPartialTelemetry:
    def test_only_recovery_present(self):
        """H. Only recovery_score; others remain None."""
        logs = [
            _make_log("2026-09-01", recovery_score=75),
            _make_log("2026-09-02", recovery_score=85),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_recovery_score"] == 80.0
        assert result["average_sleep_quality"] is None
        assert result["average_stress_level"] is None
        assert result["average_muscle_soreness"] is None

    def test_only_sleep_present(self):
        """H. Only sleep_quality; others remain None."""
        logs = [
            _make_log("2026-09-01", sleep_quality=60),
            _make_log("2026-09-02", sleep_quality=80),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_sleep_quality"] == 70.0
        assert result["average_recovery_score"] is None
        assert result["average_stress_level"] is None
        assert result["average_muscle_soreness"] is None

    def test_only_stress_present(self):
        """H. Only stress_level; others remain None."""
        logs = [_make_log("2026-09-01", stress_level=55)]
        result = aggregate_daily_logs(logs)
        assert result["average_stress_level"] == 55.0
        assert result["average_recovery_score"] is None
        assert result["average_sleep_quality"] is None
        assert result["average_muscle_soreness"] is None

    def test_only_soreness_present(self):
        """H. Only muscle_soreness; others remain None."""
        logs = [_make_log("2026-09-01", muscle_soreness=40)]
        result = aggregate_daily_logs(logs)
        assert result["average_muscle_soreness"] == 40.0
        assert result["average_recovery_score"] is None
        assert result["average_sleep_quality"] is None
        assert result["average_stress_level"] is None

    def test_recovery_and_stress_only(self):
        """H. Recovery and stress present; sleep and soreness None."""
        logs = [
            _make_log("2026-09-01", recovery_score=70, stress_level=40),
            _make_log("2026-09-02", recovery_score=90, stress_level=20),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_recovery_score"] == 80.0
        assert result["average_stress_level"] == 30.0
        assert result["average_sleep_quality"] is None
        assert result["average_muscle_soreness"] is None

    def test_sleep_and_soreness_only(self):
        """H. Sleep and soreness present; recovery and stress None."""
        logs = [
            _make_log("2026-09-01", sleep_quality=70, muscle_soreness=30),
            _make_log("2026-09-02", sleep_quality=90, muscle_soreness=50),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_sleep_quality"] == 80.0
        assert result["average_muscle_soreness"] == 40.0
        assert result["average_recovery_score"] is None
        assert result["average_stress_level"] is None

    def test_null_values_excluded_from_average(self):
        """H. Null telemetry values on some logs are excluded from the average."""
        logs = [
            _make_log("2026-09-01", recovery_score=60),
            _make_log("2026-09-02", recovery_score=None),  # excluded
            _make_log("2026-09-03"),                        # missing key, excluded
            _make_log("2026-09-04", recovery_score=80),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_recovery_score"] == 70.0  # (60 + 80) / 2


# ===========================================================================
# I. No telemetry preserves previous behavior
# ===========================================================================

class TestNoTelemetryPreservesBehavior:
    def test_aggregation_without_telemetry_unchanged(self):
        """I. Logs without any telemetry fields produce identical output keys as before."""
        logs = [
            _make_log("2026-09-01", weight_kg=80.0, calories_consumed=2100, workout_completed=True, energy_rating=8),
            _make_log("2026-09-08", weight_kg=79.5, calories_consumed=2050, workout_completed=False, energy_rating=7),
        ]
        result = aggregate_daily_logs(logs)
        # Core fields still present
        assert result["log_count"] == 2
        assert result["latest_weight_kg"] == 79.5
        assert result["average_energy_rating"] == 7.5
        assert result["completed_workouts"] == 1
        # New telemetry keys exist but are None
        assert result["average_recovery_score"] is None
        assert result["average_sleep_quality"] is None
        assert result["average_stress_level"] is None
        assert result["average_muscle_soreness"] is None

    def test_prepare_adaptation_input_without_telemetry_no_new_signals(self):
        """I. prepare_adaptation_input without telemetry keeps recovery/sleep/stress/injury as None."""
        profile = _make_full_profile()
        logs = [
            _make_log("2026-09-01", weight_kg=80.0, calories_consumed=2100, workout_completed=True),
        ]
        result = prepare_adaptation_input(profile, logs)
        # All telemetry signals remain None — no invented values
        assert result.recovery_score is None
        assert result.sleep_quality is None
        assert result.stress_score is None
        assert result.injury_risk is None

    def test_compute_adaptation_without_telemetry_neutral_outcome(self):
        """I. compute_adaptation without telemetry keeps high_fatigue_flag=False."""
        inp = _make_base_adaptation_input(
            log_count=10,
            recovery_score=None,
            sleep_quality=None,
            stress_score=None,
            injury_risk=None,
        )
        decision = compute_adaptation(inp)
        # Without physiological signals, fatigue flag must be False
        assert decision.high_fatigue_flag is False
        # Default neutral values used
        assert decision.recovery_score == 100
        assert decision.stress_score == 0
        assert decision.sleep_quality == 100
        assert decision.injury_risk == 0


# ===========================================================================
# J. Correct semantic direction
# ===========================================================================

class TestSemanticDirection:
    def test_higher_recovery_score_improves_decision_recovery_score(self):
        """J. Higher recovery_score results in higher decision recovery_score (better)."""
        low_rec = _make_base_adaptation_input(log_count=10, recovery_score=30.0)
        high_rec = _make_base_adaptation_input(log_count=10, recovery_score=90.0)
        d_low = compute_adaptation(low_rec)
        d_high = compute_adaptation(high_rec)
        assert d_high.recovery_score > d_low.recovery_score

    def test_higher_recovery_produces_higher_readiness(self):
        """J. Higher recovery_score produces higher readiness_factor."""
        low_rec = _make_base_adaptation_input(log_count=10, recovery_score=30.0)
        high_rec = _make_base_adaptation_input(log_count=10, recovery_score=90.0)
        d_low = compute_adaptation(low_rec)
        d_high = compute_adaptation(high_rec)
        assert d_high.readiness_factor > d_low.readiness_factor

    def test_high_stress_does_not_improve_readiness(self):
        """J. Higher stress_score does NOT improve readiness (it is a risk penalty)."""
        low_stress = _make_base_adaptation_input(log_count=10, stress_score=10.0)
        high_stress = _make_base_adaptation_input(log_count=10, stress_score=90.0)
        d_low = compute_adaptation(low_stress)
        d_high = compute_adaptation(high_stress)
        # Higher stress = more risk penalty = lower readiness factor
        assert d_high.readiness_factor < d_low.readiness_factor

    def test_high_soreness_as_injury_risk_does_not_improve_readiness(self):
        """J. Higher muscle_soreness (injury_risk) does NOT improve readiness."""
        low_sor = _make_base_adaptation_input(log_count=10, injury_risk=5.0)
        high_sor = _make_base_adaptation_input(log_count=10, injury_risk=90.0)
        d_low = compute_adaptation(low_sor)
        d_high = compute_adaptation(high_sor)
        assert d_high.readiness_factor < d_low.readiness_factor

    def test_higher_sleep_quality_improves_readiness(self):
        """J. Higher sleep_quality contributes positively to readiness_factor."""
        low_slp = _make_base_adaptation_input(log_count=10, sleep_quality=20.0)
        high_slp = _make_base_adaptation_input(log_count=10, sleep_quality=95.0)
        d_low = compute_adaptation(low_slp)
        d_high = compute_adaptation(high_slp)
        assert d_high.readiness_factor > d_low.readiness_factor

    def test_low_recovery_triggers_high_fatigue_flag(self):
        """J. recovery_score < 50 triggers high_fatigue_flag = True."""
        inp = _make_base_adaptation_input(log_count=10, recovery_score=35.0)
        decision = compute_adaptation(inp)
        assert decision.high_fatigue_flag is True

    def test_high_recovery_does_not_trigger_fatigue(self):
        """J. recovery_score >= 50 does NOT trigger high_fatigue_flag."""
        inp = _make_base_adaptation_input(log_count=10, recovery_score=80.0)
        decision = compute_adaptation(inp)
        assert decision.high_fatigue_flag is False

    def test_stress_level_mapped_to_stress_score_correctly(self):
        """J. stress_level in daily logs maps to AdaptationInput.stress_score (same direction)."""
        logs = [
            _make_log("2026-09-01", stress_level=70),
            _make_log("2026-09-02", stress_level=90),
        ]
        result = aggregate_daily_logs(logs)
        # stress_level averages to 80 and maps to AdaptationInput.stress_score via prepare_adaptation_input
        assert result["average_stress_level"] == 80.0

        profile = _make_full_profile()
        adaptation_input = prepare_adaptation_input(profile, logs)
        # stress_score receives the same numeric value (no inversion)
        assert adaptation_input.stress_score == 80.0

    def test_muscle_soreness_mapped_to_injury_risk_correctly(self):
        """J. muscle_soreness in daily logs maps to AdaptationInput.injury_risk (same direction)."""
        logs = [
            _make_log("2026-09-01", muscle_soreness=60),
            _make_log("2026-09-02", muscle_soreness=80),
        ]
        result = aggregate_daily_logs(logs)
        assert result["average_muscle_soreness"] == 70.0

        profile = _make_full_profile()
        adaptation_input = prepare_adaptation_input(profile, logs)
        assert adaptation_input.injury_risk == 70.0

    def test_recovery_score_mapped_directly(self):
        """J. recovery_score in daily logs maps directly to AdaptationInput.recovery_score."""
        logs = [
            _make_log("2026-09-01", recovery_score=65),
            _make_log("2026-09-02", recovery_score=75),
        ]
        profile = _make_full_profile()
        adaptation_input = prepare_adaptation_input(profile, logs)
        assert adaptation_input.recovery_score == 70.0

    def test_sleep_quality_mapped_directly(self):
        """J. sleep_quality in daily logs maps directly to AdaptationInput.sleep_quality."""
        logs = [
            _make_log("2026-09-01", sleep_quality=50),
            _make_log("2026-09-02", sleep_quality=70),
        ]
        profile = _make_full_profile()
        adaptation_input = prepare_adaptation_input(profile, logs)
        assert adaptation_input.sleep_quality == 60.0


# ===========================================================================
# K. End-to-end adaptation with realistic telemetry
# ===========================================================================

class TestEndToEndWithTelemetry:
    def test_full_telemetry_end_to_end(self):
        """K. Realistic telemetry flows correctly from daily logs to AdaptationDecision."""
        profile = _make_full_profile(goal_type="fat_loss")
        # 10 days of logs with full telemetry
        logs = []
        base = date(2026, 9, 1)
        for i in range(10):
            d = date(2026, 9, 1 + i)
            logs.append(_make_log(
                str(d),
                weight_kg=80.0 - i * 0.1,
                calories_consumed=2050,
                protein_consumed_g=155,
                carbs_consumed_g=215,
                fat_consumed_g=63,
                workout_completed=(i % 2 == 0),
                energy_rating=7,
                recovery_score=75,
                sleep_quality=80,
                stress_level=25,
                muscle_soreness=20,
            ))

        adaptation_input = prepare_adaptation_input(profile, logs)

        # Telemetry is wired in
        assert adaptation_input.recovery_score == 75.0
        assert adaptation_input.sleep_quality == 80.0
        assert adaptation_input.stress_score == 25.0
        assert adaptation_input.injury_risk == 20.0

        decision = compute_adaptation(adaptation_input)

        # With moderate recovery (75) no fatigue flag
        assert decision.high_fatigue_flag is False
        # With sufficient data, objective data should be available
        assert decision.objective_data_available is True

    def test_extreme_fatigue_telemetry_triggers_deload(self):
        """K. Very low recovery_score (< 50) in daily logs causes deload_recommended=True."""
        profile = _make_full_profile()
        logs = [
            _make_log(f"2026-09-{i+1:02d}", recovery_score=30, stress_level=80, muscle_soreness=70)
            for i in range(10)
        ]
        adaptation_input = prepare_adaptation_input(profile, logs)
        assert adaptation_input.recovery_score == 30.0
        decision = compute_adaptation(adaptation_input)
        assert decision.high_fatigue_flag is True
        assert decision.workout_adjustment.deload_recommended is True
        assert decision.workout_adjustment.intensity == "reduce"

    def test_excellent_wellness_allows_increase_when_recovery_confirmed(self):
        """K. Excellent recovery enables training intensity escalation (readiness_factor >= 1.0)."""
        # To reach readiness_factor >= 1.0 with no plateau/deload, we need very high
        # adherence, recovery, nutrition, training, sleep, and low stress/injury/plateau.
        # readiness = (adh*0.30 + rec*0.20 + nut*0.20 + trn*0.15 + mot*0.10 + slp*0.05) / 100
        # risk_penalty = (stress*0.10 + plateau*0.12 + injury*0.12) / 100
        # raw = readiness * (1 - risk_penalty)
        # With all positive at 100 and all risks at 0: readiness=1.0, penalty=0.0 → factor=1.0
        inp = _make_base_adaptation_input(
            log_count=14,
            adherence_percent=100.0,
            recovery_score=100.0,
            sleep_quality=100.0,
            stress_score=0.0,
            injury_risk=0.0,
            nutrition_score=100.0,
            training_quality=100.0,
            plateau_probability=0.0,
        )
        decision = compute_adaptation(inp)
        assert decision.high_fatigue_flag is False
        # With recovery_score provided and readiness_factor >= 1.0, intensity should escalate
        assert decision.readiness_factor >= 1.0
        assert decision.workout_adjustment.intensity == "increase"
        assert decision.workout_adjustment.volume == "high"


# ===========================================================================
# L. Existing Phase 3B active-plan adherence behavior still passes
# ===========================================================================

class TestPhase3BCompatibility:
    def test_active_meal_plan_still_overrides_profile_targets(self):
        """L. Active meal plan still overrides profile nutrition targets (Phase 3B)."""
        profile = _make_full_profile()
        logs = [_make_log("2026-09-01", calories_consumed=1800, protein_consumed_g=140)]
        active_meal_plan = {
            "target_calories": 1900,
            "target_protein_g": 145,
            "target_carbs_g": 200,
            "target_fat_g": 60,
        }
        adaptation_input = prepare_adaptation_input(
            profile, logs, active_meal_plan=active_meal_plan
        )
        # Active plan takes precedence over profile target_metrics
        assert adaptation_input.target_calories == 1900
        assert adaptation_input.target_protein_g == 145.0

    def test_active_workout_plan_still_overrides_profile_days(self):
        """L. Active workout plan still overrides profile workout_days_per_week (Phase 3B)."""
        profile = _make_full_profile(workout_days_per_week=4)
        logs = [_make_log("2026-09-01", workout_completed=True)]
        active_workout_plan = {"days_per_week": 5}
        adaptation_input = prepare_adaptation_input(
            profile, logs, active_workout_plan=active_workout_plan
        )
        assert adaptation_input.workout_days_per_week == 5

    def test_phase3b_and_phase3c_together(self):
        """L. Phase 3B plan adherence and Phase 3C telemetry coexist without conflict."""
        profile = _make_full_profile()
        logs = [
            _make_log("2026-09-01",
                      calories_consumed=1950, protein_consumed_g=148,
                      carbs_consumed_g=205, fat_consumed_g=62,
                      workout_completed=True,
                      recovery_score=70, sleep_quality=75, stress_level=30, muscle_soreness=25),
        ]
        active_meal_plan = {"target_calories": 2000, "target_protein_g": 150, "target_carbs_g": 210, "target_fat_g": 65}
        active_workout_plan = {"days_per_week": 4}

        adaptation_input = prepare_adaptation_input(
            profile, logs,
            active_meal_plan=active_meal_plan,
            active_workout_plan=active_workout_plan,
        )
        # Phase 3B: plan targets used
        assert adaptation_input.target_calories == 2000
        assert adaptation_input.workout_days_per_week == 4
        # Phase 3C: telemetry wired in
        assert adaptation_input.recovery_score == 70.0
        assert adaptation_input.sleep_quality == 75.0
        assert adaptation_input.stress_score == 30.0
        assert adaptation_input.injury_risk == 25.0


# ===========================================================================
# M. Existing diet/workout adjustment behavior still passes
# ===========================================================================

class TestDietWorkoutAdjustmentsUnchanged:
    def test_low_adherence_still_produces_neutral_diet_adjustment(self):
        """M. Low adherence still blocks diet adjustment (existing rule unchanged)."""
        inp = _make_base_adaptation_input(
            log_count=14,
            adherence_percent=50.0,  # below 70 threshold
            recovery_score=85.0,
        )
        decision = compute_adaptation(inp)
        assert decision.diet_adjustment.calorie_delta == 0
        assert decision.diet_adjustment.protein_delta_g == 0.0

    def test_high_fatigue_still_forces_reduce_intensity(self):
        """M. Fatigue from low recovery still forces intensity=reduce (existing rule)."""
        inp = _make_base_adaptation_input(
            log_count=10,
            adherence_percent=90.0,
            recovery_score=30.0,  # triggers fatigue
        )
        decision = compute_adaptation(inp)
        assert decision.workout_adjustment.intensity == "reduce"
        assert decision.workout_adjustment.deload_recommended is True

    def test_plateau_with_fat_loss_still_adds_cardio(self):
        """M. Plateau detection for fat_loss still recommends cardio (existing rule).

        The plateau+cardio rule requires readiness_factor >= 0.80 AND plateau_detected.
        Low stress (0) and low injury (0) with high adherence pushes readiness above 0.80.
        """
        inp = _make_base_adaptation_input(
            log_count=14,
            adherence_percent=90.0,
            nutrition_score=85.0,
            training_quality=85.0,
            recovery_score=90.0,
            sleep_quality=90.0,
            stress_score=0.0,
            injury_risk=0.0,
            weight_change_kg_7d=0.0,
            weight_change_kg_14d=0.05,
            weight_change_kg_28d=0.1,
            plateau_probability=80.0,
            goal_type="fat_loss",
        )
        decision = compute_adaptation(inp)
        assert decision.plateau_detected is True
        # readiness_factor must be >= 0.80 for plateau rule to fire (not low-readiness gate)
        assert decision.readiness_factor >= 0.80
        assert decision.workout_adjustment.cardio_minutes == 30

    def test_deload_flag_unchanged_for_very_low_readiness(self):
        """M. readiness_factor < 0.65 still forces deload (existing rule)."""
        inp = _make_base_adaptation_input(
            log_count=10,
            adherence_percent=20.0,
            recovery_score=10.0,
        )
        decision = compute_adaptation(inp)
        assert decision.readiness_factor < 0.65 or decision.high_fatigue_flag
        assert decision.workout_adjustment.deload_recommended is True
