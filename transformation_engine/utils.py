"""
transformation_engine.utils
───────────────────────────
Shared constants and small config helpers for the Unified Transformation Engine.

These values are the single source of truth for adherence levels, physiological
rate caps, feature ordering, and goal display metadata. Every other engine
module imports from here rather than redefining these constants.

Moved verbatim (no value changes) from the original transformation_prediction.py
monolith so existing predictions are reproduced bit-for-bit.
"""

# ── Adherence config ──────────────────────────────────────────────────────────
ADHERENCE_CONFIG = {
    "Low (50%)":      {"factor": 0.50, "label": "50%"},
    "Moderate (70%)": {"factor": 0.70, "label": "70%"},
    "High (90–100%)": {"factor": 0.92, "label": "90–100%"},
}
ADHERENCE_COLORS = {
    "Low (50%)":      "#FF4757",
    "Moderate (70%)": "#FFB347",
    "High (90–100%)": "#00D4AA",
}

# Physiologically safe ceilings on weekly rates (kg/week). Used by goal_logic
# to clamp every goal branch so predictions never exceed realistic biology.
RATE_CAPS = {
    "Fat Loss":           {"max": 0.90},
    "Muscle Gain":        {"max": 0.35},
    "Weight Gain":        {"max": 1.00},
    "Body Recomposition": {"fat_loss_max": 0.25, "muscle_gain_max": 0.15},
}

# Display metadata per goal: (primary metric label, unit, accent color).
GOAL_METRIC_LABELS = {
    "Fat Loss":           ("Fat Lost",      "kg fat lost", "#FF6B35"),
    "Muscle Gain":        ("Muscle Gained", "kg muscle",   "#00D4AA"),
    "Weight Gain":        ("Weight Gained", "kg gained",   "#FFB347"),
    "Body Recomposition": ("Fat Lost",      "kg fat lost", "#7B5EA7"),
}

# Order of columns the trained ML models expect. Must match train_model.py
# exactly or the pickled pipelines will misalign features.
FEATURE_ORDER = [
    "age", "weight", "height", "bmi", "gender", "experience",
    "workout_days", "adherence", "protein_g", "calorie_delta",
    "sleep_hrs", "steps",
]

DEFAULT_ADHERENCE = 0.92

# Path to the unified multi-goal model bundle produced by train_model.py.
MODEL_PATH = "transformation_models.pkl"

# Protein target (g per kg bodyweight) per goal — used by goal_logic to score
# protein adequacy. Pure physiological constants.
PROTEIN_PER_KG = {
    "Fat Loss":           2.2,
    "Muscle Gain":        2.5,
    "Weight Gain":        1.8,
    "Body Recomposition": 2.6,
}

# Goals the engine knows how to predict. Imported by validator + goal_logic.
SUPPORTED_GOALS = list(RATE_CAPS.keys())


def _resolve_adherence_config(adherence_label: str) -> tuple[str, dict]:
    """
    Resolve a UI adherence label (e.g. 'Moderate (70%)') to its config dict.

    Falls back to High adherence if the label is unrecognised. Tolerant of
    capitalisation and partial matches so callers passing shorthand still work.
    """
    if adherence_label in ADHERENCE_CONFIG:
        return adherence_label, ADHERENCE_CONFIG[adherence_label]
    lowered = adherence_label.lower()
    for label, config in ADHERENCE_CONFIG.items():
        if label.lower().split()[0] in lowered or lowered.split()[0] in label.lower():
            return label, config
    return "High (90-100%)", {"factor": DEFAULT_ADHERENCE, "label": "90-100%"}


def shared_constants() -> dict:
    """
    Bundle of every public constant, exposed for callers (UI, tests) that want
    a single import surface. Kept for backward compatibility with the monolith.
    """
    return {
        "feature_order": FEATURE_ORDER,
        "default_adherence": DEFAULT_ADHERENCE,
        "adherence_config": ADHERENCE_CONFIG,
        "rate_caps": RATE_CAPS,
        "goal_metric_labels": GOAL_METRIC_LABELS,
    }
