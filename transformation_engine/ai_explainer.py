"""
transformation_engine.ai_explainer
─────────────────────────────────
Builds human-readable insight strings from prediction results.

Per Doc #1 / Doc #2: the AI must NOT generate prediction numbers. It should
only interpret and explain the outputs from the Transformation Engine. This
module provides the static, deterministic explanation text that was previously
hardcoded inside the monolith's show_simulation_page.

The insights are pure functions of the prediction outputs — no LLM calls.
"""

from __future__ import annotations


def build_goal_insight(goal: str, cal_delta: float, protein_g: float,
                       adherence_label: str, total_primary: float,
                       total_muscle: float, weeks: int) -> str:
    """
    Generate a goal-specific insight paragraph for the simulation summary.

    Extracted from the hardcoded dict at the bottom of the original monolith's
    show_simulation_page (lines 964–981). The text is deterministic and
    parameterised by the actual prediction values.
    """
    adh_cfg_label = adherence_label.split("(")[-1].rstrip(")") if "(" in adherence_label else adherence_label

    if goal == "Fat Loss":
        return (
            f"Based on your **{abs(cal_delta):.0f} kcal/day deficit** and "
            f"**{protein_g}g protein**, at {adh_cfg_label} adherence you're "
            f"projected to lose **{total_primary:.2f} kg** of fat in {weeks} "
            f"weeks. Keeping protein high preserves muscle during the deficit."
        )
    if goal == "Muscle Gain":
        return (
            f"Based on your **{cal_delta:.0f} kcal/day surplus** and "
            f"**{protein_g}g protein**, at {adh_cfg_label} adherence you "
            f"could gain **{total_primary:.2f} kg** in {weeks} weeks. "
            f"Progressive overload is the key driver — eat and lift consistently."
        )
    if goal == "Weight Gain":
        return (
            f"Based on your **{cal_delta:.0f} kcal/day surplus**, at "
            f"{adh_cfg_label} adherence you could gain **{total_primary:.2f} kg** "
            f"in {weeks} weeks. Liquid calories and calorie-dense foods make "
            f"hitting your target easier."
        )
    if goal == "Body Recomposition":
        return (
            f"Based on your near-maintenance calories and **{protein_g}g "
            f"protein**, at {adh_cfg_label} adherence you could lose "
            f"**{total_primary:.2f} kg fat** while gaining **{total_muscle:.2f} "
            f"kg muscle** in {weeks} weeks. Recomp is slow but permanent — "
            f"trust the process."
        )
    return "Stay consistent to achieve your transformation goal."
