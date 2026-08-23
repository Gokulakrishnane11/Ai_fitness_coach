"""
Smart Fat Loss AI Coach
=======================
train_model.py

Trains Linear Regression and Random Forest models on the generated dataset.
Evaluates both on MAE and R², then saves the best performer as fat_loss_model.pkl.
Also generates all visualisation plots into the assets/ folder.
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")               # non-interactive backend for servers
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

from sklearn.model_selection   import train_test_split, cross_val_score
from sklearn.linear_model      import LinearRegression
from sklearn.ensemble          import RandomForestRegressor
from sklearn.preprocessing     import StandardScaler
from sklearn.pipeline          import Pipeline
from sklearn.metrics           import mean_absolute_error, r2_score

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
DATA_PATH  = "fat_loss_dataset.csv"
MODEL_PATH = "fat_loss_model.pkl"
ASSETS_DIR = "assets"
TEST_SIZE  = 0.20
RANDOM_STATE = 42

FEATURE_COLS = [
    "age", "height_cm", "weight_kg",
    "workout_days_per_week", "daily_calories",
    "protein_intake_g", "daily_steps", "tdee",
]
TARGET_COL = "weekly_fat_loss_kg"

# ─────────────────────────────────────────────
# Plotting style
# ─────────────────────────────────────────────
PALETTE = {
    "bg":       "#0F1117",
    "panel":    "#1A1D27",
    "accent1":  "#FF6B35",
    "accent2":  "#00D4AA",
    "accent3":  "#7B5EA7",
    "text":     "#E8EAF0",
    "muted":    "#6B7280",
}

def set_style():
    plt.rcParams.update({
        "figure.facecolor":  PALETTE["bg"],
        "axes.facecolor":    PALETTE["panel"],
        "axes.edgecolor":    PALETTE["muted"],
        "axes.labelcolor":   PALETTE["text"],
        "xtick.color":       PALETTE["muted"],
        "ytick.color":       PALETTE["muted"],
        "text.color":        PALETTE["text"],
        "grid.color":        "#2A2D3A",
        "grid.linewidth":    0.6,
        "font.family":       "DejaVu Sans",
        "font.size":         11,
    })

# ─────────────────────────────────────────────
# Helper: save figure
# ─────────────────────────────────────────────
def save_fig(name: str):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    path = os.path.join(ASSETS_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=PALETTE["bg"])
    plt.close()
    print(f"   📊  Saved → {path}")


# ═══════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════
def load_data(path: str = DATA_PATH) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    df = pd.read_csv(path)

    # One-hot encode gender (male=1, female=0)
    df["is_male"] = (df["gender"] == "male").astype(int)

    X = df[FEATURE_COLS + ["is_male"]]
    y = df[TARGET_COL]
    print(f"📂  Loaded {len(df):,} rows | Features: {X.shape[1]} | Target: {TARGET_COL}")
    return X, y, df


# ═══════════════════════════════════════════════════════════
# 2. TRAIN MODELS
# ═══════════════════════════════════════════════════════════
def build_pipelines() -> dict:
    return {
        "Linear Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model",  LinearRegression()),
        ]),
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("model",  RandomForestRegressor(
                n_estimators=200,
                max_depth=12,
                min_samples_split=4,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )),
        ]),
    }


def evaluate(pipe, X_train, X_test, y_train, y_test, name: str) -> dict:
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    cv_scores = cross_val_score(pipe, X_train, y_train, cv=5,
                                scoring="r2", n_jobs=-1)

    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)
    print(f"\n  [{name}]")
    print(f"    MAE  : {mae:.4f} kg")
    print(f"    R²   : {r2:.4f}")
    print(f"    CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    return {"pipe": pipe, "y_pred": y_pred, "mae": mae, "r2": r2, "name": name}


# ═══════════════════════════════════════════════════════════
# 3. PLOTS
# ═══════════════════════════════════════════════════════════
def plot_correlation_heatmap(df: pd.DataFrame):
    set_style()
    numeric_df = df[FEATURE_COLS + ["weekly_fat_loss_kg"]].copy()
    corr = numeric_df.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(220, 20, as_cmap=True)
    sns.heatmap(corr, mask=mask, cmap=cmap, center=0, vmin=-1, vmax=1,
                annot=True, fmt=".2f", linewidths=0.5,
                linecolor=PALETTE["bg"], ax=ax,
                annot_kws={"size": 9, "color": PALETTE["text"]},
                cbar_kws={"shrink": 0.8})

    ax.set_title("Feature Correlation Heatmap", fontsize=15,
                 fontweight="bold", pad=15, color=PALETTE["text"])
    plt.tight_layout()
    save_fig("01_correlation_heatmap.png")


def plot_weight_vs_fat_loss(df: pd.DataFrame):
    set_style()
    fig, ax = plt.subplots(figsize=(9, 6))

    sc = ax.scatter(
        df["weight_kg"], df["weekly_fat_loss_kg"],
        c=df["tdee"], cmap="plasma",
        alpha=0.6, s=25, linewidths=0,
    )
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("TDEE (kcal)", color=PALETTE["text"])
    cbar.ax.yaxis.set_tick_params(color=PALETTE["muted"])

    ax.set_xlabel("Body Weight (kg)")
    ax.set_ylabel("Weekly Fat Loss (kg)")
    ax.set_title("Body Weight vs Weekly Fat Loss",
                 fontsize=14, fontweight="bold", pad=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    save_fig("02_weight_vs_fat_loss.png")


def plot_protein_vs_fat_loss(df: pd.DataFrame):
    set_style()
    fig, ax = plt.subplots(figsize=(9, 6))

    colors = np.where(df["gender"] == "male",
                      PALETTE["accent1"], PALETTE["accent2"])
    ax.scatter(df["protein_intake_g"], df["weekly_fat_loss_kg"],
               c=colors, alpha=0.55, s=22, linewidths=0)

    # Legend proxies
    import matplotlib.patches as mpatches
    ax.legend(handles=[
        mpatches.Patch(color=PALETTE["accent1"], label="Male"),
        mpatches.Patch(color=PALETTE["accent2"], label="Female"),
    ], framealpha=0.2)

    ax.set_xlabel("Daily Protein Intake (g)")
    ax.set_ylabel("Weekly Fat Loss (kg)")
    ax.set_title("Protein Intake vs Weekly Fat Loss",
                 fontsize=14, fontweight="bold", pad=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    save_fig("03_protein_vs_fat_loss.png")


def plot_feature_importance(rf_pipe, feature_names: list):
    set_style()
    rf_model    = rf_pipe.named_steps["model"]
    importances = rf_model.feature_importances_
    idx         = np.argsort(importances)

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(
        [feature_names[i] for i in idx],
        importances[idx],
        color=[PALETTE["accent1"] if v > np.median(importances)
               else PALETTE["accent3"] for v in importances[idx]],
        edgecolor="none", height=0.65,
    )

    # Value labels
    for bar, val in zip(bars, importances[idx]):
        ax.text(val + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9, color=PALETTE["muted"])

    ax.set_xlabel("Importance Score")
    ax.set_title("Random Forest — Feature Importance",
                 fontsize=14, fontweight="bold", pad=12)
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    save_fig("04_feature_importance.png")


def plot_model_comparison(results: list):
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    names = [r["name"] for r in results]
    maes  = [r["mae"]  for r in results]
    r2s   = [r["r2"]   for r in results]

    colors = [PALETTE["accent1"], PALETTE["accent2"]]

    # MAE bar
    axes[0].bar(names, maes, color=colors, width=0.45, edgecolor="none")
    axes[0].set_title("Mean Absolute Error (lower = better)",
                      fontweight="bold", pad=10)
    axes[0].set_ylabel("MAE (kg)")
    axes[0].grid(True, axis="y", alpha=0.3)
    for i, v in enumerate(maes):
        axes[0].text(i, v + 0.001, f"{v:.4f}", ha="center",
                     fontsize=10, color=PALETTE["text"])

    # R² bar
    axes[1].bar(names, r2s, color=colors, width=0.45, edgecolor="none")
    axes[1].set_title("R² Score (higher = better)",
                      fontweight="bold", pad=10)
    axes[1].set_ylabel("R²")
    axes[1].grid(True, axis="y", alpha=0.3)
    for i, v in enumerate(r2s):
        axes[1].text(i, v + 0.005, f"{v:.4f}", ha="center",
                     fontsize=10, color=PALETTE["text"])

    plt.suptitle("Model Comparison", fontsize=15,
                 fontweight="bold", y=1.02, color=PALETTE["text"])
    plt.tight_layout()
    save_fig("05_model_comparison.png")


def plot_actual_vs_predicted(y_test, y_pred_best, best_name: str):
    set_style()
    fig, ax = plt.subplots(figsize=(8, 7))

    ax.scatter(y_test, y_pred_best, alpha=0.5, s=20,
               color=PALETTE["accent1"], linewidths=0)

    lims = [min(y_test.min(), y_pred_best.min()) - 0.05,
            max(y_test.max(), y_pred_best.max()) + 0.05]
    ax.plot(lims, lims, "--", color=PALETTE["accent2"], lw=1.5, label="Perfect fit")

    ax.set_xlabel("Actual Weekly Fat Loss (kg)")
    ax.set_ylabel("Predicted Weekly Fat Loss (kg)")
    ax.set_title(f"Actual vs Predicted — {best_name}",
                 fontsize=14, fontweight="bold", pad=12)
    ax.legend(framealpha=0.2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    save_fig("06_actual_vs_predicted.png")


def train_unified_models(path="transformation_models.pkl"):
    print("\n🏋️  Training Unified Multi-Goal Transformation Models ...")
    
    RATE_CAPS = {
        "Fat Loss":           {"max": 0.90},
        "Muscle Gain":        {"max": 0.35},
        "Weight Gain":        {"max": 1.00},
        "Body Recomposition": {"fat_loss_max": 0.25, "muscle_gain_max": 0.15},
    }
    
    def generate_goal_data(n=2500, goal="Fat Loss"):
        rng           = np.random.RandomState(42)
        age           = rng.randint(18, 55, n)
        weight        = rng.uniform(50, 130, n)
        height        = rng.uniform(155, 195, n)
        bmi           = weight / (height / 100) ** 2
        gender        = rng.randint(0, 2, n)
        experience    = rng.randint(0, 3, n)
        workout_days  = rng.randint(2, 7, n)
        adherence     = rng.uniform(0.3, 1.0, n)
        protein_g     = rng.uniform(80, 280, n)
        calorie_delta = rng.uniform(-800, 800, n)   # negative = deficit
        sleep_hrs     = rng.uniform(5, 9, n)
        steps         = rng.randint(3000, 15000, n)

        if goal == "Fat Loss":
            base           = np.clip(-calorie_delta, 0, 800) / 7700
            protein_factor = np.clip(protein_g / weight / 2.2, 0.5, 1.1)
            sleep_factor   = np.clip(sleep_hrs / 8.0, 0.7, 1.05)
            exercise_bonus = workout_days * 0.008
            gender_factor  = 1.05 * gender + 0.97 * (1 - gender)
            exp_factor     = 1.0 + experience * 0.03
            weekly         = (base * protein_factor * sleep_factor
                              * gender_factor * exp_factor * adherence + exercise_bonus)
            target         = np.clip(weekly + rng.normal(0, 0.02, n), 0, RATE_CAPS["Fat Loss"]["max"])

        elif goal == "Muscle Gain":
            base_monthly   = np.where(experience==0, 1.1, np.where(experience==1, 0.7, 0.35))
            surplus_factor = np.clip(np.maximum(calorie_delta, 0) / 350, 0.3, 1.0)
            protein_factor = np.clip(protein_g / weight / 2.2, 0.5, 1.05)
            train_factor   = np.clip(workout_days / 5, 0.5, 1.0)
            weekly         = (base_monthly/4.3) * surplus_factor * protein_factor * train_factor * adherence
            target         = np.clip(weekly + rng.normal(0, 0.01, n), 0, RATE_CAPS["Muscle Gain"]["max"])

        elif goal == "Weight Gain":
            surplus        = np.clip(calorie_delta, 0, 1000)
            base           = surplus / 7700
            age_factor     = np.clip(1.0 - (age - 25) * 0.005, 0.80, 1.05)
            act_factor     = np.clip(workout_days / 4, 0.8, 1.1)
            weekly         = base * age_factor * act_factor * adherence
            target         = np.clip(weekly + rng.normal(0, 0.03, n), 0, RATE_CAPS["Weight Gain"]["max"])

        else:  # Recomposition
            deficit_equiv  = np.clip(-calorie_delta * 0.3, 0, 300) / 7700
            protein_factor = np.clip(protein_g / weight / 2.5, 0.4, 1.0)
            train_factor   = np.clip(workout_days / 4, 0.5, 1.0)
            weekly         = deficit_equiv * protein_factor * train_factor * adherence
            target         = np.clip(weekly + rng.normal(0, 0.01, n),
                                     0, RATE_CAPS["Body Recomposition"]["fat_loss_max"])

        return pd.DataFrame({
            "age": age, "weight": weight, "height": height, "bmi": bmi,
            "gender": gender, "experience": experience, "workout_days": workout_days,
            "adherence": adherence, "protein_g": protein_g,
            "calorie_delta": calorie_delta, "sleep_hrs": sleep_hrs, "steps": steps,
            "target": target,
        })

    models = {}
    features = ["age", "weight", "height", "bmi", "gender", "experience",
                "workout_days", "adherence", "protein_g", "calorie_delta", "sleep_hrs", "steps"]
    
    for goal in ["Fat Loss", "Muscle Gain", "Weight Gain", "Body Recomposition"]:
        df = generate_goal_data(2500, goal)
        X, y = df[features], df["target"]
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("rf",     RandomForestRegressor(
                n_estimators=150, max_depth=9,
                min_samples_leaf=4, random_state=42, n_jobs=-1)),
        ])
        pipe.fit(X, y)
        models[goal] = pipe
        print(f"   ✓ Trained model for: {goal}")
        
    joblib.dump(models, path)
    print(f"💾  Unified models saved → {path}")


# ═══════════════════════════════════════════════════════════
# 4. MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("\n" + "═" * 55)
    print("  Smart Fat Loss AI Coach — Model Training")
    print("═" * 55)

    # Load
    X, y, df = load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    feature_names = list(X.columns)

    # Train & evaluate
    print("\n🏋️  Training models …")
    pipes   = build_pipelines()
    results = []
    for name, pipe in pipes.items():
        res = evaluate(pipe, X_train, X_test, y_train, y_test, name)
        results.append(res)

    # Select best by R²
    best = max(results, key=lambda r: r["r2"])
    print(f"\n🏆  Best model: {best['name']}  (R² = {best['r2']:.4f})")

    # Save model
    joblib.dump(best["pipe"], MODEL_PATH)
    print(f"💾  Model saved → {MODEL_PATH}")

    # ── Plots ─────────────────────────────────────────────────────────────────
    print("\n🎨  Generating plots …")
    set_style()
    plot_correlation_heatmap(df)
    plot_weight_vs_fat_loss(df)
    plot_protein_vs_fat_loss(df)
    plot_feature_importance(best["pipe"] if best["name"] == "Random Forest"
                            else results[1]["pipe"],
                            feature_names)
    plot_model_comparison(results)
    plot_actual_vs_predicted(y_test, best["y_pred"], best["name"])

    # Train the unified simulation models
    train_unified_models()

    print("\n✅  Training complete!")
    print(f"   Model : {MODEL_PATH}")
    print(f"   Plots : {ASSETS_DIR}/")


if __name__ == "__main__":
    main()
