"""
ai_engine.py — Central Adaptive AI Recommendation Engine
Combines user metrics + goal + nutrition + ML predictions + NLP feedback
into one unified recommendation object. Updates on every interaction.
"""

from ai_food     import recommend_foods
from ai_diet     import generate_ai_meal_plan
from ai_workout  import get_ai_workout
# from unwanted.ai_feedback import analyze_ai_feedback
from AI_analyser_page import analyze_journal
from fitness_intelligence import normalize_fitness_intelligence

class AIEngine:
    """
    Central AI orchestrator.
    Holds user state and regenerates recommendations whenever inputs change.
    """
    def __init__(self):
        self.profile        = {}
        self.nutrition      = {}
        self.feedback_state = {"issues": [], "sentiment": "neutral", "score": 50,
                               "fitness_intelligence": normalize_fitness_intelligence({})}
        self.last_recs      = {}

    def update_profile(self, goal, experience, weight_kg, height_cm,
                       age, gender, activity_level, workout_days,
                       preference, target_calories, macros):
        self.profile = {
            "goal": goal, "experience": experience,
            "weight_kg": weight_kg, "height_cm": height_cm,
            "age": age, "gender": gender,
            "activity_level": activity_level,
            "workout_days": workout_days,
            "preference": preference,
        }
        self.nutrition = {
            "target_calories": target_calories,
            "macros": macros,
        }

    def update_feedback(self, text: str):
        result = analyze_journal(text)
        self.feedback_state = {
            "issues":    result["key_issues"],
            "sentiment": result["sentiment"],
            "score":     result["score"],
            "fitness_intelligence": result,
            "fitness_scores": result.get("fitness_scores", {}),
        }
        return result

    def get_food_recommendations(self, deficits: list = None):
        if not self.profile:
            return {}
        return recommend_foods(
            goal       = self.profile["goal"],
            deficits   = deficits or [],
            preference = self.profile["preference"],
        )

    def get_meal_plan(self):
        if not self.profile or not self.nutrition:
            return {}
        return generate_ai_meal_plan(
            goal             = self.profile["goal"],
            target_calories  = self.nutrition["target_calories"],
            macros           = self.nutrition["macros"],
            preference       = self.profile["preference"],
            fitness_intelligence = self.feedback_state.get("fitness_intelligence"),
        )

    def get_workout(self):
        if not self.profile:
            return {}
        return get_ai_workout(
            goal             = self.profile["goal"],
            experience       = self.profile["experience"],
            feedback_issues  = self.feedback_state["issues"],
            workout_days     = self.profile["workout_days"],
            fitness_intelligence = self.feedback_state.get("fitness_intelligence"),
        )

    def get_full_recommendations(self, deficits: list = None) -> dict:
        """Single call → full personalised recommendation bundle."""
        return {
            "food":    self.get_food_recommendations(deficits),
            "meal":    self.get_meal_plan(),
            "workout": self.get_workout(),
            "profile": self.profile,
            "state":   self.feedback_state,
        }

    def get_adaptive_summary(self) -> dict:
        """Generate a text summary of current AI adaptations."""
        intel = normalize_fitness_intelligence(self.feedback_state.get("fitness_intelligence"))
        scores = intel["fitness_scores"]
        issues  = self.feedback_state["issues"]
        sent    = self.feedback_state["sentiment"]
        goal    = self.profile.get("goal", "—")
        summary = []

        if "fatigue" in issues or "overtraining" in issues:
            summary.append("Workout intensity reduced due to detected fatigue")
        if "injury risk" in issues:
            summary.append("Switched to machine-only plan due to injury risk")
        if "low motivation" in issues:
            summary.append("Simplified workout selected for low motivation week")
        if "plateau" in issues:
            summary.append("Nutrition strategy updated to break plateau")
        if "stress" in issues:
            summary.append("Recovery emphasis added due to high stress")
        if sent == "positive":
            summary.append("High readiness detected full intensity plan active")
        summary.append(
            f"Intelligence: adherence {scores['adherence_score']}/100, "
            f"recovery {scores['recovery_score']}/100, nutrition {scores['nutrition_score']}/100"
        )
        if not summary:
            summary.append("All systems nominal standard plan active")

        return {
            "goal":     goal,
            "sentiment": sent,
            "issues":   issues,
            "adaptations": summary,
        }
