"""
transformation_engine.simulation_page
─────────────────────────────────────
The Streamlit UI for the Predictive Simulation feature.

This is the ONLY module in the engine package that imports streamlit.
It builds a PredictionContext from session_state at the boundary, passes it
to the pure-logic simulation_engine.run_simulation, and renders the results.

All HTML/CSS and chart rendering logic is preserved exactly from the original
monolith's show_simulation_page (lines 694–999).
"""

import pandas as pd

from .ai_explainer import build_goal_insight
from .simulation_engine import run_simulation
from .utils import ADHERENCE_COLORS, ADHERENCE_CONFIG, GOAL_METRIC_LABELS


def show_simulation_page(get_profile_fn, require_profile_fn):
    """
    Streamlit page: Predictive Transformation Simulator.

    Signature is identical to the monolith's version so the backward-compat shim
    can re-export it without changes. `get_profile_fn` and `require_profile_fn`
    are the same callables defined in app.py.
    """
    import streamlit as st
    from fitness_intelligence import get_session_intelligence

    require_profile_fn()
    p = st.session_state
    bmr, tdee, tc, mac, _, _ = get_profile_fn()
    goal = p.goal
    fitness_intelligence = get_session_intelligence(st.session_state)

    metric_label, metric_unit, metric_color = GOAL_METRIC_LABELS.get(
        goal, ("Progress", "kg", "#E8EAF0"))

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#141720 0%,#0F1117 55%,#0a1a0a 100%);
        border:1px solid #252836;border-radius:20px;padding:2.5rem 3rem;margin-bottom:1.5rem;
        position:relative;overflow:hidden;">
      <div style="position:absolute;top:-50px;right:-50px;width:200px;height:200px;
        background:radial-gradient(circle,rgba(0,212,170,.12) 0%,transparent 70%);border-radius:50%;"></div>
      <div style="font-family:'Syne',sans-serif;font-size:2.1rem;font-weight:800;margin:0 0 .3rem;
        background:linear-gradient(90deg,#00D4AA 0%,#4A90D9 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        🔮 Predictive Transformation Simulator</div>
      <p style="color:#6B7280;font-size:.95rem;margin:0;">
        ML projections based on YOUR actual profile — weight, calories, protein, workout days.
        Change adherence level to see how consistency affects outcomes.
      </p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<span style="background:rgba(0,212,170,.1);border:1px solid rgba(0,212,170,.3);'
        'color:#00D4AA;border-radius:100px;font-size:.72rem;padding:3px 12px;">'
        '🤖 RandomForest ML · Trained on 2,500 synthetic physiological profiles · '
        'Predictions use your actual saved profile</span>', unsafe_allow_html=True)

    st.warning("⚠️ **Estimates only.** Actual results depend on metabolism, genetics, sleep, "
               "stress, and individual response. Always consult a professional.")

    # ── Show user inputs being used ───────────────────────────────────────────
    st.markdown("### 👤 Your Profile Used for Simulation")
    st.markdown(
        f'<div style="background:#0B0D14;border:1px solid #252836;border-radius:12px;'
        f'padding:.9rem 1.2rem;font-size:.82rem;color:#6B7280;margin-bottom:1rem;">'
        f'<strong style="color:#E8EAF0;">Goal:</strong> {goal} &nbsp;|&nbsp; '
        f'<strong style="color:#E8EAF0;">Weight:</strong> {p.weight_kg} kg &nbsp;|&nbsp; '
        f'<strong style="color:#E8EAF0;">Target:</strong> {p.target_weight} kg &nbsp;|&nbsp; '
        f'<strong style="color:#E8EAF0;">Calories:</strong> {tc:.0f} kcal/day '
        f'(TDEE: {tdee:.0f}) &nbsp;|&nbsp; '
        f'<strong style="color:#E8EAF0;">Protein:</strong> {mac["protein"]}g &nbsp;|&nbsp; '
        f'<strong style="color:#E8EAF0;">Workout Days:</strong> {p.workout_days}/week &nbsp;|&nbsp; '
        f'<strong style="color:#E8EAF0;">Experience:</strong> {p.experience}</div>',
        unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    st.markdown("### ⚙️ Simulation Settings")
    c1, c2, c3 = st.columns(3)
    with c1:
        adherence_label = st.selectbox(
            "Adherence Level",
            list(ADHERENCE_CONFIG.keys()), index=1,
            help="How consistently you follow the diet + workout plan")
    with c2:
        sim_weeks = st.slider("Duration (weeks)", 4, 52, 16, step=4)
    with c3:
        show_ci = st.checkbox("Show confidence range", value=True)

    adh_color = ADHERENCE_COLORS[adherence_label]
    adh_cfg = ADHERENCE_CONFIG[adherence_label]

    # ── Run simulation with user's real profile data ──────────────────────────
    profile = {
        "weight_kg": p.weight_kg,
        "target_weight": p.target_weight,
        "height_cm": p.height_cm,
        "age": p.age,
        "gender": p.gender,
        "experience": p.experience,
        "workout_days": p.workout_days,
        "protein_g": mac["protein"],
        "daily_steps": getattr(p, "daily_steps", 8000),
        "sleep_hrs": fitness_intelligence["fitness_scores"].get("sleep_quality", 70) / 10.0,
        "fitness_intelligence": fitness_intelligence,
    }

    with st.spinner("Running ML prediction on your profile..."):
        result = run_simulation(
            profile=profile, goal=goal,
            adherence_label=adherence_label,
            target_calories=tc, tdee=tdee,
            macros=mac, weeks=sim_weeks,
            fitness_intelligence=fitness_intelligence,
        )

    df = result["df"]
    rate = result["weekly_rate"]
    goal_wk = result["goal_week"]
    adh_comp = result["adh_comparison"]
    cal_delta = result["calorie_delta"]
    total_primary = df["cumulative"].iloc[-1]
    final_weight = df["weight"].iloc[-1]
    total_muscle = df["muscle"].iloc[-1]

    # ── Calorie delta insight ─────────────────────────────────────────────────
    if cal_delta < 0:
        delta_label = f"Deficit: {abs(cal_delta):.0f} kcal/day"
        delta_color = "#00D4AA"
    elif cal_delta > 0:
        delta_label = f"Surplus: {cal_delta:.0f} kcal/day"
        delta_color = "#FFB347"
    else:
        delta_label = "Maintenance calories"
        delta_color = "#6B7280"

    # ── Summary cards ─────────────────────────────────────────────────────────
    st.markdown("### 📊 ML Prediction Summary")
    time_str = (f"{goal_wk} weeks (~{goal_wk//4} months)"
                 if goal_wk and goal_wk <= 104 else f">{sim_weeks}w")
    weight_dir = "↓" if goal == "Fat Loss" else "↑"

    cards_html = f"""
    <div style="display:flex;gap:.65rem;flex-wrap:wrap;margin-bottom:1rem;">
      <div style="flex:1;min-width:110px;background:#0B0D14;border:1px solid #252836;
          border-radius:13px;padding:1rem .9rem;text-align:center;">
        <div style="font-size:.66rem;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;">
          Weekly Rate</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.65rem;font-weight:800;color:{adh_color};">
          {rate:.3f}</div>
        <div style="font-size:.72rem;color:#6B7280;">{metric_unit}/week</div>
      </div>
      <div style="flex:1;min-width:110px;background:#0B0D14;border:1px solid #252836;
          border-radius:13px;padding:1rem .9rem;text-align:center;">
        <div style="font-size:.66rem;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;">
          {metric_label} in {sim_weeks}w</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.65rem;font-weight:800;color:{metric_color};">
          {total_primary:.2f}</div>
        <div style="font-size:.72rem;color:#6B7280;">{metric_unit}</div>
      </div>
      <div style="flex:1;min-width:110px;background:#0B0D14;border:1px solid #252836;
          border-radius:13px;padding:1rem .9rem;text-align:center;">
        <div style="font-size:.66rem;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;">
          Final Weight</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.65rem;font-weight:800;color:#4A90D9;">
          {final_weight:.1f}</div>
        <div style="font-size:.72rem;color:#6B7280;">kg {weight_dir}</div>
      </div>
      <div style="flex:1;min-width:110px;background:#0B0D14;border:1px solid #252836;
          border-radius:13px;padding:1rem .9rem;text-align:center;">
        <div style="font-size:.66rem;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;">
          Goal Timeline</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.0rem;font-weight:800;
            color:#FFB347;margin-top:.3rem;">{time_str}</div>
      </div>
      <div style="flex:1;min-width:110px;background:#0B0D14;border:1px solid #252836;
          border-radius:13px;padding:1rem .9rem;text-align:center;">
        <div style="font-size:.66rem;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;">
          Calorie Balance</div>
        <div style="font-family:'Syne',sans-serif;font-size:.95rem;font-weight:800;
            color:{delta_color};margin-top:.3rem;">{delta_label}</div>
      </div>
      {"" if goal not in ("Muscle Gain","Weight Gain","Body Recomposition") else f'''
      <div style="flex:1;min-width:110px;background:#0B0D14;border:1px solid #252836;
          border-radius:13px;padding:1rem .9rem;text-align:center;">
        <div style="font-size:.66rem;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;">
          Muscle Gained</div>
        <div style="font-family:Syne,sans-serif;font-size:1.65rem;font-weight:800;color:#00D4AA;">
          {total_muscle:.2f}</div>
        <div style="font-size:.72rem;color:#6B7280;">kg muscle</div>
      </div>'''}
    </div>"""
    st.markdown(cards_html, unsafe_allow_html=True)

    # Adherence badge
    adh_desc = {
        "Low (50%)": "Following the plan ~50% of the time — missed sessions, diet slips expected.",
        "Moderate (70%)": "Following the plan ~70% of the time — mostly consistent with some lapses.",
        "High (90–100%)": "Following the plan 90–100% — near-perfect discipline and consistency.",
    }
    adh_icon = "🔴" if "Low" in adherence_label else ("🟡" if "Mod" in adherence_label else "🟢")
    st.markdown(f"""
    <div style="background:rgba(0,0,0,.25);border:1px solid {adh_color};border-radius:11px;
        padding:.75rem 1rem;margin-bottom:1rem;display:flex;align-items:center;gap:10px;">
      <span>{adh_icon}</span>
      <div>
        <span style="font-size:.84rem;font-weight:600;color:{adh_color};">{adherence_label}</span>
        <span style="font-size:.78rem;color:#6B7280;margin-left:8px;">{adh_desc[adherence_label]}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown("### 📈 Visual Projections")
    tab1, tab2, tab3 = st.tabs([
        f"📉 {metric_label} Over Time",
        "⚖️ Weight Trajectory",
        "🔀 Adherence Comparison",
    ])

    with tab1:
        st.caption(f"Cumulative {metric_unit} · week by week · {adh_cfg['label']} adherence")
        if show_ci:
            chart_df = result["chart_primary"].rename(columns={
                "Expected": f"Expected ({adh_cfg['label']})",
                "Lower (−25%)": "Pessimistic",
                "Upper (+18%)": "Optimistic",
            })
        else:
            chart_df = result["chart_primary"][["Expected"]].rename(
                columns={"Expected": f"Expected ({adh_cfg['label']})"})
        st.line_chart(chart_df, height=280)
        if show_ci:
            st.caption("Pessimistic/Optimistic band shows realistic variation. "
                       "Actual results vary by metabolism, sleep, and stress.")

    with tab2:
        st.caption("Projected body weight week by week")
        st.line_chart(result["chart_weight"].rename(columns={"weight": "Weight (kg)"}), height=260)
        goal_line = pd.DataFrame(
            {"Target Weight": [p.target_weight] * sim_weeks}, index=range(1, sim_weeks + 1))
        st.line_chart(goal_line, height=70)
        st.caption(f"Target: **{p.target_weight} kg** · Start: **{p.weight_kg} kg** · "
                   f"Difference: **{abs(p.weight_kg - p.target_weight):.1f} kg**")

    with tab3:
        st.caption("All 3 adherence levels compared on same timeline")
        st.line_chart(result["chart_adherence"], height=280,
                      color=["#FF4757", "#FFB347", "#00D4AA"])
        st.markdown("**Projected totals at end of simulation:**")
        cols = st.columns(3)
        for i, (lbl, val) in enumerate(adh_comp.items()):
            c = ADHERENCE_COLORS[lbl]
            icon = "🔴" if "Low" in lbl else ("🟡" if "Mod" in lbl else "🟢")
            with cols[i]:
                st.markdown(f"""
                <div style="background:#0B0D14;border:1px solid {c};border-radius:12px;
                    padding:.9rem;text-align:center;">
                  <div style="font-size:.72rem;color:{c};">{icon} {lbl}</div>
                  <div style="font-family:'Syne',sans-serif;font-size:1.5rem;
                      font-weight:800;color:{c};margin-top:.2rem;">{val:.2f}</div>
                  <div style="font-size:.72rem;color:#6B7280;">{metric_unit}</div>
                </div>""", unsafe_allow_html=True)

    # ── Recomp split chart ────────────────────────────────────────────────────
    if goal == "Body Recomposition":
        st.markdown("### ⚖️ Recomposition Breakdown")
        rc = pd.DataFrame({
            "Fat Lost (cumulative)": df["cumulative"].values,
            "Muscle Gained (cumulative)": df["muscle"].values,
        }, index=df["week"])
        st.line_chart(rc, height=240, color=["#FF6B35", "#00D4AA"])
        st.caption("Fat loss and muscle gain happening simultaneously — true body recomposition.")

    # ── Milestone table ───────────────────────────────────────────────────────
    st.markdown("### 📅 Weekly Milestones")
    m_weeks = [w for w in [1, 2, 4, 6, 8, 10, 12, 16, 20, 24] if w <= sim_weeks]
    mdf = df[df["week"].isin(m_weeks)].copy()
    mdf["weight"] = mdf["weight"].map(lambda x: f"{x:.1f} kg")
    mdf["cumulative"] = mdf["cumulative"].map(lambda x: f"{x:.2f}")
    mdf["muscle"] = mdf["muscle"].map(lambda x: f"{x:.2f} kg")

    dcols = {"week": "Week", "weight": "Body Weight", "cumulative": metric_label}
    if goal in ("Muscle Gain", "Weight Gain"):
        dcols["muscle"] = "Lean Muscle (kg)"
    elif goal == "Body Recomposition":
        dcols["muscle"] = "Muscle Gained (kg)"

    st.dataframe(
        mdf[list(dcols.keys())].rename(columns=dcols).reset_index(drop=True),
        use_container_width=True, hide_index=True)

    # ── Insight box (now via ai_explainer) ───────────────────────────────────
    st.markdown("---")
    insight_text = build_goal_insight(
        goal, cal_delta, mac["protein"], adherence_label,
        total_primary, total_muscle, sim_weeks,
    )
    st.markdown(f"""
    <div style="background:rgba(0,212,170,.05);border:1px solid rgba(0,212,170,.2);
        border-radius:14px;padding:1.2rem 1.4rem;">
      <div style="font-size:.76rem;color:#00D4AA;text-transform:uppercase;
          letter-spacing:.07em;margin-bottom:.4rem;">🤖 ML Prediction Insight</div>
      <div style="font-size:.9rem;color:#E8EAF0;line-height:1.65;">
        {insight_text}
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(255,71,87,.04);border:1px solid rgba(255,71,87,.2);
        border-radius:10px;padding:.75rem 1rem;margin-top:.7rem;font-size:.76rem;color:#FF4757;">
      ⚠️ Predictions are ML estimates trained on synthetic data. Actual results vary by
      individual metabolism, hormones, sleep quality, stress, and many other factors.
      These are directional projections, not guarantees.
    </div>""", unsafe_allow_html=True)
