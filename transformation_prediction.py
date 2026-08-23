"""
transformation_prediction.py — backward-compatibility shim.

The real implementation now lives in the modular `transformation_engine/` package
(Doc #1 architecture). This thin shim re-exports the public API symbols that
existing callers (app.py) import, so the refactor is transparent.

Real source of truth: transformation_engine/
"""

from transformation_engine.model_loader import load_fat_loss_model
from transformation_engine.prediction_engine import (
    predict_fat_loss,
    predict_muscle_gain,
    predict_weight_change,
    predict_recomposition,
    weeks_to_goal,
    generate_milestones,
)
from transformation_engine.simulation_page import show_simulation_page

__all__ = [
    "load_fat_loss_model",
    "predict_fat_loss",
    "predict_muscle_gain",
    "predict_weight_change",
    "predict_recomposition",
    "weeks_to_goal",
    "generate_milestones",
    "show_simulation_page",
]
