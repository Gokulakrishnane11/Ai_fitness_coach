"""
transformation_engine — Unified AI Transformation Engine
════════════════════════════════════════════════════════
Single source of truth for all body transformation predictions in the
application. Every feature (static prediction, predictive simulation, AI
coach explanations) calls through this package.

The engine:
  • Uses only user inputs when predicting (never touches the raw dataset).
  • Learns from historical data through pre-trained ML models (model_loader).
  • Enhances predictions with scientifically validated fitness calculations
    (physiology_engine + goal_logic).
  • Supports multiple goals through a unified architecture (goal_logic).
  • Applies AI-derived behavioral adjustments through a single chokepoint
    (behavior_adjuster) — the AI refines, never replaces.
  • Validates all inputs before processing (validator).
  • Uses PredictionContext to keep the engine Streamlit-free and testable.

Importing `transformation_engine` itself is safe and lightweight — it does NOT
pull in streamlit. Only simulation_page.py imports streamlit.
"""

# ── Public API (backward-compatible with app.py imports) ─────────────────────
from .model_loader import load_fat_loss_model                # noqa: F401
from .prediction_engine import (                             # noqa: F401
    predict_fat_loss,
    predict_muscle_gain,
    predict_weight_change,
    predict_recomposition,
    weeks_to_goal,
    generate_milestones,
)
from .simulation_page import show_simulation_page             # noqa: F401

# ── Extended public API (used by simulation, future features) ─────────────────
from .prediction_engine import (                             # noqa: F401
    calculate_weekly_rates,
    calculate_metrics,
    predict_static,
)
from .simulation_engine import (                            # noqa: F401
    run_simulation,
    simulate_weeks,
)
from .model_loader import (                                 # noqa: F401
    load_models,
    load_transformation_models,
)
from .feature_processor import (                           # noqa: F401
    preprocess_inputs,
    make_feature_row,
)

# ── New architectural types ────────────────────────────────────────────────
from .context import PredictionContext                       # noqa: F401

# ── Constants bundle (convenience) ───────────────────────────────────────────
from .utils import shared_constants                         # noqa: F401

__all__ = [
    # Backward-compat (8 names app.py imports)
    "load_fat_loss_model",
    "predict_fat_loss",
    "predict_muscle_gain",
    "predict_weight_change",
    "predict_recomposition",
    "weeks_to_goal",
    "generate_milestones",
    "show_simulation_page",
    # Extended API
    "calculate_weekly_rates",
    "calculate_metrics",
    "predict_static",
    "run_simulation",
    "simulate_weeks",
    "load_models",
    "load_transformation_models",
    "preprocess_inputs",
    "make_feature_row",
    # New types
    "PredictionContext",
    "shared_constants",
]
