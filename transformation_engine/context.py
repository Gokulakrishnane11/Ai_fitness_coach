"""
transformation_engine.context
─────────────────────────────
PredictionContext — the single object threaded through the engine.

Replaces the long parameter lists (profile, goal, calorie_delta, protein_g,
adherence_factor, fitness_intelligence, weeks) that the monolith passed around.
Constructing one object makes the engine trivially testable and keeps the
Streamlit boundary (the only place that reads st.session_state) clearly
separated from the pure engine functions.

The engine never imports streamlit and never reads session state directly.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from .utils import DEFAULT_ADHERENCE


@dataclass
class PredictionContext:
    """
    Everything the engine needs to compute one prediction or simulation.

    Attributes mirror the parameters of the legacy calculate_weekly_rates /
    run_simulation functions so behavior is preserved exactly.
    """
    profile: dict
    goal: str
    calorie_delta: float = 0.0
    protein_g: float = 120.0
    adherence_factor: float = DEFAULT_ADHERENCE
    fitness_intelligence: dict | None = None
    weeks: int = 20
    # Simulation-only inputs (ignored by static prediction):
    target_calories: float | None = None
    tdee: float | None = None
    macros: dict = field(default_factory=dict)
    adherence_label: str = "High (90–100%)"

    # ── Factories ────────────────────────────────────────────────────────────
    @classmethod
    def from_profile(cls, profile: dict, goal: str, calorie_delta: float = 0.0,
                     protein_g: float = 120.0,
                     adherence_factor: float = DEFAULT_ADHERENCE,
                     fitness_intelligence: dict | None = None) -> "PredictionContext":
        """Build a context for a static prediction (no simulation)."""
        return cls(
            profile=deepcopy(profile),
            goal=goal,
            calorie_delta=calorie_delta,
            protein_g=protein_g,
            adherence_factor=adherence_factor,
            fitness_intelligence=deepcopy(fitness_intelligence)
            if fitness_intelligence else None,
        )

    @classmethod
    def from_session_state(cls, session_state, goal: str | None = None,
                           target_calories: float | None = None,
                           tdee: float | None = None,
                           macros: dict | None = None) -> "PredictionContext":
        """
        Build a context from a Streamlit session state.

        This is the ONE place the engine layer is allowed to read session state.
        All downstream code receives a clean PredictionContext instead.
        `session_state` is treated as a Mapping — tests can pass a plain dict.
        """
        from .utils import DEFAULT_ADHERENCE as _DA  # local to avoid cycle surprises

        goal = goal or session_state.get("goal", "Fat Loss")
        macros = macros or {}
        protein_g = macros.get("protein", session_state.get("protein_g", 120.0))
        sleep_quality = 70
        # If a fitness_intelligence blob is already in session, pull sleep from it
        intel = session_state.get("fitness_intelligence")
        if intel and isinstance(intel, dict):
            sleep_quality = intel.get("fitness_scores", {}).get("sleep_quality", 70)

        profile = {
            "age":           session_state.get("age", 25),
            "weight_kg":     session_state.get("weight_kg", 70.0),
            "target_weight": session_state.get("target_weight", session_state.get("weight_kg", 70.0)),
            "height_cm":     session_state.get("height_cm", 170.0),
            "gender":        session_state.get("gender", "Male"),
            "experience":    session_state.get("experience", "Beginner"),
            "workout_days":  session_state.get("workout_days", 3),
            "activity_level": session_state.get("activity_level"),
            "protein_g":     protein_g,
            "daily_steps":   getattr(session_state, "daily_steps",
                                     session_state.get("daily_steps", 8000)),
            "sleep_hrs":     sleep_quality / 10.0,
            "fitness_intelligence": intel,
        }
        return cls(
            profile=profile,
            goal=goal,
            protein_g=protein_g,
            adherence_factor=_DA,
            fitness_intelligence=intel,
            target_calories=target_calories,
            tdee=tdee,
            macros=macros,
        )

    # ── Convenience views ────────────────────────────────────────────────────
    def with_updates(self, **changes) -> "PredictionContext":
        """Return a shallow copy with the given fields replaced."""
        new = PredictionContext(
            profile=self.profile,
            goal=self.goal,
            calorie_delta=self.calorie_delta,
            protein_g=self.protein_g,
            adherence_factor=self.adherence_factor,
            fitness_intelligence=self.fitness_intelligence,
            weeks=self.weeks,
            target_calories=self.target_calories,
            tdee=self.tdee,
            macros=self.macros,
            adherence_label=self.adherence_label,
        )
        for k, v in changes.items():
            setattr(new, k, v)
        return new
