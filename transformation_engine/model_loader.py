"""
transformation_engine.model_loader
──────────────────────────────────
Lazy, once-only loading of the pre-trained transformation models.

The engine must NEVER retrain at runtime, never regenerate training data, and
never touch the raw dataset when predicting. This module is the single place
that touches the .pkl bundle: it loads it once into a module-level cache and
hands out models to the prediction/simulation engines.

Moved verbatim from the original monolith.
"""

import os

import pandas as pd

from .utils import FEATURE_ORDER, MODEL_PATH

# Module-level cache. Populated on first load_models() call, reused thereafter.
UNIFIED_MODELS: dict | None = None


def load_models() -> dict:
    """
    Load the trained transformation models once from transformation_models.pkl.

    Returns a dict keyed by goal name ("Fat Loss", "Muscle Gain", ...). On any
    failure (missing file, corrupt pickle) returns an empty dict so callers can
    gracefully fall back to the scientific layer alone.
    """
    global UNIFIED_MODELS
    if UNIFIED_MODELS is None:
        try:
            import joblib
            UNIFIED_MODELS = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else {}
        except Exception:
            UNIFIED_MODELS = {}
    return UNIFIED_MODELS


def load_transformation_models() -> dict:
    """Alias for load_models(). Kept for callers that used the long name."""
    return load_models()


def load_fat_loss_model():
    """Convenience accessor for the Fat Loss pipeline (used by app.py)."""
    return load_models().get("Fat Loss")


def _predict_with_model(goal: str, feature_row: pd.DataFrame, model=None) -> float | None:
    """
    Run a single prediction through a goal's model.

    Returns None if the model is missing or prediction throws — the scientific
    layer in goal_logic / prediction_engine handles the fallback. Never raises.
    """
    active_model = model if model is not None else load_models().get(goal)
    if active_model is None:
        return None
    try:
        return float(active_model.predict(feature_row[FEATURE_ORDER])[0])
    except Exception:
        return None
