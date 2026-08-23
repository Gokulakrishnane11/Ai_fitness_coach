"""
Smart Fat Loss AI Coach
=======================
dataset_generator.py

Generates a synthetic dataset of 1200 realistic user fitness profiles.
Uses the Mifflin-St Jeor formula for BMR and activity multipliers for TDEE.
Fat loss is computed from caloric deficit using the 7700 kcal/kg rule.
"""

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────
# Seed for reproducibility
# ─────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
N_SAMPLES   = 1200

# ─────────────────────────────────────────────
# Activity multiplier map (workout days → factor)
# ─────────────────────────────────────────────
ACTIVITY_MULTIPLIERS = {
    0: 1.2,   # Sedentary
    1: 1.375, # Lightly active
    2: 1.375,
    3: 1.55,  # Moderately active
    4: 1.55,
    5: 1.725, # Very active
    6: 1.725,
    7: 1.9,   # Extra active
}

def calculate_bmr(weight_kg: float, height_cm: float,
                  age: int, gender: str) -> float:
    """
    Mifflin-St Jeor BMR formula.

    Male:   BMR = 10 × weight + 6.25 × height − 5 × age + 5
    Female: BMR = 10 × weight + 6.25 × height − 5 × age − 161
    """
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "male" else base - 161


def calculate_tdee(bmr: float, workout_days: int) -> float:
    """TDEE = BMR × activity multiplier (capped to 0–7 workout days)."""
    multiplier = ACTIVITY_MULTIPLIERS.get(min(workout_days, 7), 1.2)
    return bmr * multiplier


def calculate_weekly_fat_loss(tdee: float, daily_calories: float) -> float:
    """
    Estimate weekly fat loss from caloric deficit.

    weekly_fat_loss (kg) = (TDEE − daily_calories) × 7 / 7700

    Negative values indicate fat gain; capped to realistic bounds.
    """
    deficit = tdee - daily_calories
    fat_loss = (deficit * 7) / 7700
    # Realistic physiological bounds: −0.5 kg/week gain to +1.5 kg/week loss
    return float(np.clip(fat_loss, -0.5, 1.5))


def generate_dataset(n_samples: int = N_SAMPLES) -> pd.DataFrame:
    """
    Build a synthetic but physiologically realistic fitness dataset.

    Returns
    -------
    pd.DataFrame with columns:
        age, gender, height_cm, weight_kg, workout_days_per_week,
        daily_calories, protein_intake_g, daily_steps, bmr, tdee,
        weekly_fat_loss_kg
    """
    # ── Demographics ──────────────────────────────────────────────────────────
    ages    = np.random.randint(18, 65, n_samples)
    genders = np.random.choice(["male", "female"], n_samples, p=[0.52, 0.48])

    # Height: males 165–190 cm, females 150–175 cm
    heights = np.where(
        genders == "male",
        np.random.normal(177, 7, n_samples),
        np.random.normal(163, 6, n_samples),
    ).clip(145, 200)

    # Weight correlated with height ± noise
    weights = (heights * 0.45 + np.random.normal(0, 8, n_samples)).clip(45, 140)

    # ── Activity ──────────────────────────────────────────────────────────────
    workout_days = np.random.randint(0, 8, n_samples)          # 0–7 days/week
    daily_steps  = np.random.normal(7500, 2500, n_samples).clip(1000, 20000).astype(int)

    # ── Nutrition ─────────────────────────────────────────────────────────────
    # People on a fat-loss programme tend to eat 1400–2800 kcal
    daily_calories = np.random.normal(2000, 350, n_samples).clip(1200, 3500)

    # Protein target: 1.6–2.2 g / kg bodyweight for active individuals
    protein_ratio  = np.random.uniform(1.4, 2.4, n_samples)
    protein_intake = (weights * protein_ratio).clip(80, 300)

    # ── Derived fields ────────────────────────────────────────────────────────
    bmr_values  = np.array([calculate_bmr(w, h, a, g)
                             for w, h, a, g in zip(weights, heights, ages, genders)])
    tdee_values = np.array([calculate_tdee(b, d)
                             for b, d in zip(bmr_values, workout_days)])

    # Steps contribution: +50 kcal per 1000 steps above 5000 baseline
    step_bonus  = np.maximum(0, (daily_steps - 5000) / 1000 * 50)
    tdee_values = tdee_values + step_bonus

    fat_loss_values = np.array([calculate_weekly_fat_loss(t, c)
                                 for t, c in zip(tdee_values, daily_calories)])

    # ── Add small realistic noise ─────────────────────────────────────────────
    fat_loss_values += np.random.normal(0, 0.03, n_samples)
    fat_loss_values  = np.clip(fat_loss_values, -0.5, 1.5)

    df = pd.DataFrame({
        "age":                   ages,
        "gender":                genders,
        "height_cm":             heights.round(1),
        "weight_kg":             weights.round(1),
        "workout_days_per_week": workout_days,
        "daily_calories":        daily_calories.round(0).astype(int),
        "protein_intake_g":      protein_intake.round(1),
        "daily_steps":           daily_steps,
        "bmr":                   bmr_values.round(2),
        "tdee":                  tdee_values.round(2),
        "weekly_fat_loss_kg":    fat_loss_values.round(4),
    })

    return df


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🔧  Generating dataset …")
    df = generate_dataset()
    out_path = "fat_loss_dataset.csv"
    df.to_csv(out_path, index=False)
    print(f"✅  Saved {len(df):,} rows → {out_path}")
    print(f"\nPreview:\n{df.head(3).to_string()}")
    print(f"\nTarget stats:\n{df['weekly_fat_loss_kg'].describe().round(4)}")
