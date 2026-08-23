"""
transformation_engine.simulation_engine
────────────────────────────────────────
Week-by-week predictive simulation using the same engine as static prediction.

Every simulated week:
  1. Recalculate BMR/TDEE based on current body weight (via physiology_engine)
  2. Recalculate calorie delta from the (fixed) target calories
  3. Call the unified prediction engine (calculate_weekly_rates)
  4. Evolve the fitness intelligence profile (via fitness_intelligence)
  5. Accumulate totals

This ensures Week 0 of the simulation == static prediction for identical
inputs (Doc #1's consistency requirement), and that no duplicate prediction
logic exists anywhere in the codebase.

No Streamlit imports. Pure logic.
"""

from __future__ import annotations

import pandas as pd

from .behavior_adjuster import resolved_adherence_factor
from .prediction_engine import calculate_weekly_rates
from .physiology_engine import calculate_body_metrics
from .utils import ADHERENCE_CONFIG, _resolve_adherence_config, DEFAULT_ADHERENCE
from .validator import validate_inputs

from fitness_intelligence import (
    adherence_factor_from_intelligence,
    evolve_weekly_intelligence,
    normalize_fitness_intelligence,
)


def run_simulation(profile: dict, goal: str, adherence_label: str,
                   target_calories: float, tdee: float,
                   macros: dict, weeks: int = 20,
                   fitness_intelligence: dict | None = None) -> dict:
    """
    Core ML simulation. All inputs come from the user's profile and nutrition.

    Mirrors the original monolith's run_simulation exactly. The two inlined
    BMR/TDEE calculation blocks have been replaced with a single call to
    physiology_engine.calculate_body_metrics (DRY extraction).
    """
    adherence_label, adh_cfg = _resolve_adherence_config(adherence_label)
    adh_factor = adh_cfg["factor"]
    current_intelligence = normalize_fitness_intelligence(
        fitness_intelligence or profile.get("fitness_intelligence")
    ) if (fitness_intelligence or profile.get("fitness_intelligence")) else None
    if current_intelligence:
        adh_factor = adherence_factor_from_intelligence(current_intelligence, adh_factor)
    protein_g = profile.get("protein_g", macros.get("protein", 120.0))

    cur_weight = float(profile.get("weight_kg", 70.0))
    height = float(profile.get("height_cm", 170.0))
    age = int(profile.get("age", 25))
    gender = profile.get("gender", "Male")
    experience = profile.get("experience", "Beginner")
    workout_days = int(profile.get("workout_days", 3))
    steps = float(profile.get("daily_steps", profile.get("steps", 8000)))
    sleep_hrs = float(profile.get("sleep_hrs", 7.0))
    activity_level = profile.get("activity_level")

    # Initial BMR/TDEE (now via physiology_engine — DRY)
    init_body = calculate_body_metrics(cur_weight, height, age, gender,
                                        workout_days, steps, activity_level)
    init_tdee = init_body["tdee"]
    init_calorie_delta = target_calories - init_tdee

    # Initial weekly rate from the engine
    init_res = calculate_weekly_rates(
        profile, goal, init_calorie_delta, protein_g, adh_factor, current_intelligence,
    )
    if goal in ("Fat Loss", "Body Recomposition"):
        initial_weekly_rate = init_res["weekly_fat_loss"]
    elif goal == "Muscle Gain":
        initial_weekly_rate = init_res["weekly_muscle_gain"]
    else:
        initial_weekly_rate = init_res["weekly_weight_change"]

    recomp_muscle_rate = init_res["weekly_muscle_gain"] if goal == "Body Recomposition" else 0.0

    rows = []
    cum_primary = 0.0
    cum_muscle = 0.0

    # ── Week-by-week loop ────────────────────────────────────────────────────
    for wk in range(1, weeks + 1):
        # Recalculate BMR/TDEE for current weight (via physiology_engine)
        wk_body = calculate_body_metrics(cur_weight, height, age, gender,
                                         workout_days, steps, activity_level)
        wk_tdee = wk_body["tdee"]
        wk_calorie_delta = target_calories - wk_tdee

        # Build a per-week profile with updated weight
        wk_profile = profile.copy()
        wk_profile["weight_kg"] = cur_weight
        wk_profile["fitness_intelligence"] = current_intelligence

        res = calculate_weekly_rates(
            wk_profile, goal, wk_calorie_delta, protein_g, adh_factor,
            current_intelligence,
        )

        fat_loss = res["weekly_fat_loss"]
        muscle_chg = res["weekly_muscle_gain"]
        weight_chg = res["weekly_weight_change"]

        cur_weight += weight_chg
        if goal in ("Fat Loss", "Body Recomposition"):
            cum_primary += fat_loss
        else:
            cum_primary += weight_chg

        cum_muscle += max(0.0, muscle_chg)

        rows.append({
            "week":            wk,
            "weight":          round(cur_weight, 2),
            "weekly_rate":     round(
                fat_loss if goal in ("Fat Loss", "Body Recomposition")
                else (muscle_chg if goal == "Muscle Gain" else weight_chg), 3),
            "cumulative":      round(cum_primary, 2),
            "muscle":          round(cum_muscle, 2),
            "fat_loss_wk":     round(fat_loss, 3),
            "muscle_gain_wk":  round(max(0.0, muscle_chg), 3),
            "adherence_score": round(
                (current_intelligence or {}).get("fitness_scores", {}).get(
                    "adherence_score", adh_factor * 100), 0),
            "recovery_score":  round(
                (current_intelligence or {}).get("fitness_scores", {}).get(
                    "recovery_score", 0), 0),
            "motivation_score": round(
                (current_intelligence or {}).get("fitness_scores", {}).get(
                    "motivation_score", 0), 0),
            "nutrition_score": round(
                (current_intelligence or {}).get("fitness_scores", {}).get(
                    "nutrition_score", 0), 0),
        })

        # Evolve intelligence for next week
        if current_intelligence:
            current_intelligence = evolve_weekly_intelligence(
                current_intelligence, wk, rows[-1])
            adh_factor = adherence_factor_from_intelligence(
                current_intelligence, adh_factor)

    df = pd.DataFrame(rows)

    # ── Adherence-level comparison trajectories ─────────────────────────────
    adh_comparison = {}
    adh_chart_data = {}
    for lbl, cfg in ADHERENCE_CONFIG.items():
        sim_weight = float(profile.get("weight_kg", 70.0))
        sim_cum_primary = 0.0
        sim_weeks_data = []

        for wk in range(1, weeks + 1):
            wk_profile = profile.copy()
            wk_profile["weight_kg"] = sim_weight

            wk_body = calculate_body_metrics(
                sim_weight, height, age, gender, workout_days, steps, activity_level)
            wk_tdee = wk_body["tdee"]
            wk_calorie_delta = target_calories - wk_tdee

            res_adh = calculate_weekly_rates(
                wk_profile, goal, wk_calorie_delta, protein_g,
                cfg["factor"], current_intelligence)

            fat_l = res_adh["weekly_fat_loss"]
            weight_c = res_adh["weekly_weight_change"]

            sim_weight += weight_c
            if goal in ("Fat Loss", "Body Recomposition"):
                sim_cum_primary += fat_l
            else:
                sim_cum_primary += weight_c

            sim_weeks_data.append(round(sim_cum_primary, 2))

        adh_comparison[lbl] = round(sim_cum_primary, 2)
        adh_chart_data[lbl] = sim_weeks_data

    # ── Goal week estimation ───────────────────────────────────────────────
    diff = abs(profile["weight_kg"] - profile["target_weight"])
    goal_week = None
    if initial_weekly_rate > 0:
        goal_week = min(int(diff / initial_weekly_rate), 104)

    return {
        "df":              df,
        "weekly_rate":     round(initial_weekly_rate, 4),
        "goal_week":       goal_week,
        "adh_comparison":  adh_comparison,
        "recomp_muscle":   round(recomp_muscle_rate, 4),
        "calorie_delta":   round(init_calorie_delta, 1),
        "adh_label":       adherence_label,
        "adh_factor":      adh_factor,
        "chart_primary":   pd.DataFrame({
            "Expected":       df["cumulative"].values,
            "Lower (−25%)":   [round(v * 0.75, 2) for v in df["cumulative"]],
            "Upper (+18%)":   [round(v * 1.18, 2) for v in df["cumulative"]],
        }, index=df["week"]),
        "chart_weight":    df[["week", "weight"]].set_index("week"),
        "chart_adherence": pd.DataFrame(adh_chart_data, index=df["week"]),
        "chart_behavior":  df[["week", "adherence_score", "recovery_score",
                                "motivation_score", "nutrition_score"]].set_index("week"),
        "fitness_intelligence": current_intelligence,
        "ai_behavior_factor": init_res.get("ai_behavior_factor", 1.0),
    }


def simulate_weeks(profile: dict, goal: str, adherence_label: str,
                   target_calories: float, tdee: float,
                   macros: dict, weeks: int = 20,
                   fitness_intelligence: dict | None = None) -> dict:
    """Alias for run_simulation. Kept for backward compatibility."""
    return run_simulation(profile, goal, adherence_label, target_calories,
                         tdee, macros, weeks, fitness_intelligence)
