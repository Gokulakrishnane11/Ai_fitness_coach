"""
Smart Body Transformation AI Coach — Enhanced with AI Engine
app.py  |  Run: streamlit run app.py
"""

import os, random
import numpy as np
import pandas as pd
import streamlit as st

from nutrition   import (calculate_bmr, calculate_tdee, get_target_calories,
                          calculate_macros, calculate_micronutrients,
                          estimate_intake, compare_intake, FOOD_DB,
                          ACTIVITY_MULTIPLIERS)
from transformation_prediction import (load_fat_loss_model, predict_fat_loss, predict_muscle_gain,
                                       predict_weight_change, predict_recomposition,
                                       weeks_to_goal, generate_milestones,
                                       show_simulation_page)
from ai_food     import recommend_foods, FOOD_DATABASE
from ai_diet     import generate_ai_meal_plan, generate_weekly_variation
from ai_workout  import get_ai_workout
from AI_analyser_page import show_sentiment_page
from ai_engine   import AIEngine
from fitness_intelligence import (
    adjusted_diet_targets,
    adherence_factor_from_intelligence,
    get_session_intelligence,
    normalize_fitness_intelligence,
)

st.set_page_config(page_title="Smart Body Transformation AI Coach",
                   page_icon="💪", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap');
:root{--bg:#0B0D14;--panel:#141720;--border:#252836;--accent:#FF6B35;--green:#00D4AA;
      --purple:#7B5EA7;--blue:#4A90D9;--yellow:#FFB347;--text:#E8EAF0;--muted:#6B7280;}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text)!important;font-family:'Poppins',sans-serif;}
h1,h2,h3{font-family:'Poppins',sans-serif!important;}
.block-container{padding:2rem 3rem!important;max-width:1200px;}
.hero{background:linear-gradient(135deg,#1A1D27 0%,#0F1117 60%,#0d0a1a 100%);border:1px solid var(--border);border-radius:20px;padding:2.5rem 3rem;margin-bottom:2rem;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;top:-60px;right:-60px;width:220px;height:220px;background:radial-gradient(circle,rgba(123,94,167,0.2) 0%,transparent 70%);border-radius:50%;}
.hero-title{font-family:'Poppins',sans-serif;font-size:2.3rem;font-weight:800;margin:0 0 .3rem;background:linear-gradient(90deg,var(--accent) 0%,var(--purple) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.hero-sub{color:var(--muted);font-size:.95rem;margin:0;}
.card{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:1.8rem 2rem;margin-bottom:1.2rem;}
.ctitle{font-family:'Poppins',sans-serif;font-size:.9rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin-bottom:1rem;}
.mrow{display:flex;gap:.7rem;margin-top:.7rem;flex-wrap:wrap;}
.mbox{flex:1;min-width:90px;background:#0B0D14;border:1px solid var(--border);border-radius:12px;padding:1rem .9rem;text-align:center;}
.mbox .lbl{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem;}
.mbox .val{font-family:'Poppins',sans-serif;font-size:1.6rem;font-weight:800;color:var(--accent);}
.mbox .unt{font-size:.76rem;color:var(--muted);}
.mg .val{color:var(--green)!important;} .mp .val{color:var(--purple)!important;}
.mb .val{color:var(--blue)!important;}   .my .val{color:var(--yellow)!important;}
.bar-wrap{background:#1A1D27;border-radius:100px;height:9px;overflow:hidden;margin:.3rem 0;}
.bar-fill{height:100%;border-radius:100px;}
.pill{display:inline-block;padding:3px 11px;border-radius:100px;font-size:.76rem;font-weight:600;margin:2px;}
.tip{background:rgba(0,212,170,.05);border:1px solid rgba(0,212,170,.2);border-radius:10px;padding:.8rem 1rem;margin:.4rem 0;}
.warn{background:rgba(255,71,87,.06);border:1px solid rgba(255,71,87,.25);border-radius:10px;padding:.8rem 1rem;margin:.4rem 0;}
.ai-badge{background:rgba(123,94,167,.15);border:1px solid rgba(123,94,167,.4);color:#A78BCC;border-radius:100px;font-size:.72rem;padding:3px 10px;display:inline-block;margin-bottom:.5rem;}
.food-card{background:#0B0D14;border:1px solid var(--border);border-radius:12px;padding:.9rem 1rem;margin-bottom:.5rem;}
.meal-card{background:#0B0D14;border:1px solid var(--border);border-radius:12px;padding:1rem 1.2rem;margin-bottom:.6rem;}
.stButton>button{background:linear-gradient(135deg,var(--accent),#FF8C5A)!important;color:white!important;font-family:'Poppins',sans-serif!important;font-weight:700!important;border:none!important;border-radius:12px!important;padding:.6rem 1.8rem!important;transition:all .2s!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(255,107,53,.35)!important;}
label,.stSlider label{color:var(--muted)!important;font-size:.86rem!important;}
</style>""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
DEFS = {"goal":"Fat Loss","gender":"Male","age":22,"height_cm":175,"weight_kg":75,
        "target_weight":68,"experience":"Beginner","workout_days":4,
        "activity_level":"Moderately Active (3–5 days/week)",
        "preference":"Non-Vegetarian","profile_set":False,
        "journal_history":[],"feedback_issues":[],
        "fitness_intelligence": normalize_fitness_intelligence({}),
        "ai_engine": AIEngine()}
for k,v in DEFS.items():
    if k not in st.session_state: st.session_state[k] = v

ml_model = load_fat_loss_model()
engine: AIEngine = st.session_state.ai_engine
st.session_state["fitness_intelligence"] = normalize_fitness_intelligence(
    st.session_state.get("fitness_intelligence")
)

GOAL_ICONS = {"Fat Loss":"🔥","Muscle Gain":"💪","Weight Gain":"📈","Body Recomposition":"⚖️"}
GOAL_COLORS = {"Fat Loss":"#FF6B35","Muscle Gain":"#00D4AA","Weight Gain":"#FFB347","Body Recomposition":"#7B5EA7"}

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown(f"""
<div style="padding:.4rem 0 .8rem;">
  <div style="font-family:'Poppins',sans-serif;font-size:1rem;font-weight:800;
    background:linear-gradient(90deg,#FF6B35,#7B5EA7);-webkit-background-clip:text;
    -webkit-text-fill-color:transparent;">💪 Body Transformation AI</div>
  <div class="ai-badge" style="margin-top:.3rem;">AI Engine Active</div>
</div>""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigate",[
    "🎯 Goal & Profile",
    "📊 Transformation Prediction",
    "🔮 Predictive Simulation",
    "🥗 Nutrition Dashboard",
    "📋 Intake vs Requirement",
    "🍱 AI Food Recommendations",
    "🍽️ AI Diet Plan",
    "💪 AI Workout Guide",
    "🧠 AI Feedback Analysis",
], label_visibility="collapsed")

# Adaptive summary in sidebar
if st.session_state.profile_set:
    summary = engine.get_adaptive_summary()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🤖 AI Status**")
    for line in summary["adaptations"]:
        st.sidebar.caption(line)

# ── Helpers ───────────────────────────────────────────────────────────────────
def hero(t,s): st.markdown(f'<div class="hero"><div class="hero-title">{t}</div><p class="hero-sub">{s}</p></div>',unsafe_allow_html=True)
def co(t):     st.markdown(f'<div class="card"><div class="ctitle">{t}</div>',unsafe_allow_html=True)
def cc():      st.markdown('</div>',unsafe_allow_html=True)
def mbox(l,v,u,cls=""): return f'<div class="mbox {cls}"><div class="lbl">{l}</div><div class="val">{v}</div><div class="unt">{u}</div></div>'
def bar(pct,color,label="",val=""):
    st.markdown(f"""<div style="margin:.3rem 0;"><div style="display:flex;justify-content:space-between;font-size:.76rem;color:var(--muted);margin-bottom:3px;"><span>{label}</span><span>{val}</span></div>
    <div class="bar-wrap"><div class="bar-fill" style="width:{min(pct,100)}%;background:{color};"></div></div></div>""",unsafe_allow_html=True)
def ai_badge(text="AI-Powered"):
    st.markdown(f'<div class="ai-badge">🤖 {text}</div>',unsafe_allow_html=True)

def get_profile():
    p = st.session_state
    bmr  = calculate_bmr(p.weight_kg, p.height_cm, p.age, p.gender)
    tdee = calculate_tdee(bmr, p.activity_level)
    tc   = get_target_calories(tdee, p.goal)
    mac  = calculate_macros(tc, p.weight_kg, p.goal)
    mic  = calculate_micronutrients(p.weight_kg, p.age, p.gender, p.goal)
    return bmr, tdee, tc, mac, mic, tdee-tc

def require_profile():
    if not st.session_state.profile_set:
        st.warning("⚠️ Complete **Goal & Profile** first (top of sidebar).")
        st.stop()


# ════════════════════════════════════════════════════════════════
# PAGE 1 — Goal & Profile
# ════════════════════════════════════════════════════════════════
if page == "🎯 Goal & Profile":
    hero("🎯 Goal & Profile Setup","Set your goal and body stats. The AI engine personalises everything automatically.")

    co("🏆 SELECT YOUR GOAL")
    cols = st.columns(4)
    for i, g in enumerate(GOAL_ICONS):
        with cols[i]:
            sel    = st.session_state.goal == g
            border = GOAL_COLORS[g] if sel else "#252836"
            st.markdown(f"""<div style="border:2px solid {border};border-radius:14px;padding:1rem;
            text-align:center;background:#0B0D14;">
            <div style="font-size:1.8rem;">{GOAL_ICONS[g]}</div>
            <div style="font-family:'Syne',sans-serif;font-weight:700;color:{border};margin-top:.3rem;font-size:.9rem;">{g}</div>
            </div>""",unsafe_allow_html=True)
            if st.button("Select",key=f"g_{g}"):
                st.session_state.goal = g; st.rerun()
    cc()

    co("👤 BODY STATS")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.session_state.gender    = st.selectbox("Gender",["Male","Female"])
        st.session_state.age       = st.slider("Age",16,70,st.session_state.age)
        st.session_state.height_cm = st.slider("Height (cm)",145,210,st.session_state.height_cm)
    with c2:
        st.session_state.weight_kg     = st.slider("Current Weight (kg)",35,150,st.session_state.weight_kg)
        st.session_state.target_weight = st.slider("Target Weight (kg)",35,150,st.session_state.target_weight)
        st.session_state.experience    = st.selectbox("Training Experience",["Beginner","Intermediate","Advanced"])
    with c3:
        st.session_state.activity_level = st.selectbox("Activity Level",list(ACTIVITY_MULTIPLIERS.keys()))
        st.session_state.workout_days   = st.slider("Workout Days / Week",0,7,st.session_state.workout_days)
        st.session_state.preference     = st.radio("Diet Preference",["Vegetarian","Non-Vegetarian"])
    cc()

    if st.button("💾  Save & Activate AI Engine"):
        bmr,tdee,tc,mac,_,_ = get_profile()
        engine.update_profile(
            st.session_state.goal, st.session_state.experience,
            st.session_state.weight_kg, st.session_state.height_cm,
            st.session_state.age, st.session_state.gender,
            st.session_state.activity_level, st.session_state.workout_days,
            st.session_state.preference, tc, mac
        )
        st.session_state.profile_set = True
        st.success(f"✅ AI Engine activated! Goal: **{st.session_state.goal}** · {st.session_state.weight_kg}kg → {st.session_state.target_weight}kg")
        st.balloons()


# ════════════════════════════════════════════════════════════════
# PAGE 2 — Transformation Prediction
# ════════════════════════════════════════════════════════════════
elif page == "📊 Transformation Prediction":
    require_profile()
    p = st.session_state
    bmr,tdee,tc,mac,mic,deficit = get_profile()

    hero("📊 Transformation Prediction","Science-backed body transformation estimates.")

    co("⚡ ENERGY BALANCE")
    st.markdown(f"""<div class="mrow">
      {mbox("BMR",f"{bmr:.0f}","kcal/day")}
      {mbox("TDEE",f"{tdee:.0f}","kcal/day","mg")}
      {mbox("Target Cal",f"{tc:.0f}","kcal/day","mp")}
      {mbox("Daily Δ",f"{-deficit:+.0f}","kcal/day","mb")}
    </div>""",unsafe_allow_html=True)
    cc()

    co("🎯 WEEKLY PREDICTION")
    fitness_intelligence = get_session_intelligence(st.session_state)
    ai_adherence = adherence_factor_from_intelligence(fitness_intelligence, 0.92)
    profile_dict = {
        "age":           p.age,
        "weight_kg":     p.weight_kg,
        "height_cm":     p.height_cm,
        "gender":        p.gender,
        "experience":    p.experience,
        "workout_days":  p.workout_days,
        "protein_g":     mac["protein"],
        "daily_steps":   getattr(p, "daily_steps", 8000),
        "sleep_hrs":     fitness_intelligence["fitness_scores"].get("sleep_quality", 70) / 10.0,
        "adherence_factor": ai_adherence,
        "fitness_intelligence": fitness_intelligence,
    }
    scores = fitness_intelligence["fitness_scores"]
    st.markdown(
        f'<div class="tip">Fitness Intelligence applied: adherence '
        f'<strong>{scores["adherence_score"]}/100</strong>, recovery '
        f'<strong>{scores["recovery_score"]}/100</strong>, nutrition '
        f'<strong>{scores["nutrition_score"]}/100</strong>, stress '
        f'<strong>{scores["stress_score"]}/100</strong>, plateau risk '
        f'<strong>{scores["plateau_probability"]}/100</strong>, injury risk '
        f'<strong>{scores["injury_risk"]}/100</strong>.</div>',
        unsafe_allow_html=True
    )

    if p.goal == "Fat Loss":
        wl = predict_fat_loss(max(0,deficit)*7,p.weight_kg,p.workout_days,mac["protein"],ml_model,profile=profile_dict)
        wk = weeks_to_goal(p.weight_kg,p.target_weight,wl)
        st.markdown(f"""<div class="mrow">
          {mbox("Weekly Fat Loss",f"{wl:.3f}","kg/week","my")}
          {mbox("Monthly Fat Loss",f"{wl*4.3:.2f}","kg/month","mg")}
          {mbox("Weeks to Goal",wk or "—","weeks","mp")}
          {mbox("Daily Deficit",f"{deficit:.0f}","kcal/day")}
        </div>""",unsafe_allow_html=True)
        mls = generate_milestones(p.weight_kg,p.target_weight,wl,p.goal)
    elif p.goal == "Muscle Gain":
        s = max(0,-deficit)
        wm = predict_muscle_gain(s,mac["protein"],p.weight_kg,p.experience,p.workout_days,profile=profile_dict)
        ww = predict_weight_change(-deficit,profile=profile_dict,protein_g=mac["protein"])
        wk = weeks_to_goal(p.weight_kg,p.target_weight,ww) if ww>0 else None
        st.markdown(f"""<div class="mrow">
          {mbox("Weekly Muscle",f"{wm:.3f}","kg/week","mg")}
          {mbox("Weekly Weight",f"{ww:.3f}","kg/week","my")}
          {mbox("Yearly Muscle",f"~{wm*4.3*12:.1f}","kg/year","mp")}
          {mbox("Daily Surplus",f"{-deficit:.0f}","kcal/day","mb")}
        </div>""",unsafe_allow_html=True)
        mls = generate_milestones(p.weight_kg,p.target_weight,ww,p.goal)
    elif p.goal == "Weight Gain":
        ww = predict_weight_change(-deficit,profile=profile_dict,protein_g=mac["protein"])
        wk = weeks_to_goal(p.weight_kg,p.target_weight,ww) if ww>0 else None
        st.markdown(f"""<div class="mrow">
          {mbox("Weekly Gain",f"{ww:.3f}","kg/week","my")}
          {mbox("Monthly Gain",f"{ww*4.3:.2f}","kg/month","mg")}
          {mbox("Weeks to Goal",wk or "—","weeks","mp")}
          {mbox("Daily Surplus",f"{-deficit:.0f}","kcal/day","mb")}
        </div>""",unsafe_allow_html=True)
        mls = generate_milestones(p.weight_kg,p.target_weight,ww,p.goal)
    else:
        rc = predict_recomposition(mac["protein"],p.weight_kg,p.workout_days,p.experience,profile=profile_dict)
        st.markdown(f"""<div class="mrow">
          {mbox("Weekly Fat Loss",f"{rc['fat_loss_kg']:.3f}","kg/week","my")}
          {mbox("Weekly Muscle",f"{rc['muscle_gain_kg']:.3f}","kg/week","mg")}
          {mbox("Net Weight Δ",f"{rc['net_weight_kg']:+.3f}","kg/week","mp")}
          {mbox("Calories",f"{tc:.0f}","kcal/day (maint.)","mb")}
        </div>""",unsafe_allow_html=True)
        st.markdown(f'<div class="tip">ℹ️ {rc["note"]}</div>',unsafe_allow_html=True)
        mls = []
    cc()

    if mls:
        co("📅 TRANSFORMATION TIMELINE")
        for m in mls:
            dot = "#00D4AA" if m["reached_goal"] else "#FF6B35"
            lbl = "🎯 <strong>GOAL REACHED</strong>" if m["reached_goal"] else ""
            dir_w = "Lost" if p.goal=="Fat Loss" else "Gained"
            st.markdown(f"""<div style="display:flex;align-items:flex-start;gap:1rem;
              padding:.7rem 0;border-bottom:1px solid var(--border);">
              <div style="width:10px;height:10px;border-radius:50%;background:{dot};
                          margin-top:4px;flex-shrink:0;box-shadow:0 0 8px {dot}88;"></div>
              <div><div style="font-family:'Syne',sans-serif;font-weight:700;color:var(--text);">
              Week {m['week']} {lbl}</div>
              <div style="font-size:.84rem;color:var(--muted);">Weight: <strong style="color:var(--text)">
              {m['weight']}kg</strong> · {dir_w}: <strong style="color:{dot}">{m['change']}kg</strong></div>
              </div></div>""",unsafe_allow_html=True)
        cc()


# ════════════════════════════════════════════════════════════════
# PAGE: Predictive Simulation
# ════════════════════════════════════════════════════════════════
elif page == "🔮 Predictive Simulation":
    show_simulation_page(get_profile, require_profile)


# ════════════════════════════════════════════════════════════════
# PAGE 3 — Nutrition Dashboard
# ════════════════════════════════════════════════════════════════
elif page == "🥗 Nutrition Dashboard":
    require_profile()
    p = st.session_state
    bmr,tdee,tc,mac,mic,_ = get_profile()

    hero("🥗 Nutrition Dashboard","Personalised daily macro & micronutrient targets.")

    co("🔢 DAILY MACRO TARGETS")
    st.markdown(f"""<div class="mrow">
      {mbox("Calories",f"{tc:.0f}","kcal/day","my")}
      {mbox("Protein",mac['protein'],"g/day","mg")}
      {mbox("Carbs",mac['carbs'],"g/day","mb")}
      {mbox("Fat",mac['fat'],"g/day","mp")}
      {mbox("Fiber",mac['fiber'],"g/day")}
    </div>""",unsafe_allow_html=True)
    total_mc = mac["protein"]*4 + mac["carbs"]*4 + mac["fat"]*9
    for name,cal,color in [("Protein",mac["protein"]*4,"#00D4AA"),("Carbs",mac["carbs"]*4,"#4A90D9"),("Fat",mac["fat"]*9,"#7B5EA7")]:
        pct = round(cal/total_mc*100) if total_mc else 0
        bar(pct,color,name,f"{pct}% · {cal} kcal")
    cc()

    co("🔬 MICRONUTRIENT TARGETS")
    micro_data = [("Iron",mic["iron"],"mg","#FF6B35"),("Calcium",mic["calcium"],"mg","#00D4AA"),
                  ("Vitamin D",mic["vitamin_d"],"IU","#FFB347"),("Vitamin B12",mic["vitamin_b12"],"mcg","#7B5EA7"),
                  ("Magnesium",mic["magnesium"],"mg","#4A90D9"),("Zinc",mic["zinc"],"mg","#FF4757")]
    cols = st.columns(3)
    for i,(name,val,unit,color) in enumerate(micro_data):
        with cols[i%3]:
            st.markdown(f"""<div style="background:#0B0D14;border:1px solid #252836;border-radius:12px;
            padding:.85rem;text-align:center;margin-bottom:.5rem;">
            <div style="font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;">{name}</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:{color};">{val}</div>
            <div style="font-size:.74rem;color:var(--muted);">{unit}/day</div></div>""",unsafe_allow_html=True)
    cc()


# ════════════════════════════════════════════════════════════════
# PAGE 4 — Intake vs Requirement
# ════════════════════════════════════════════════════════════════
elif page == "📋 Intake vs Requirement":
    require_profile()
    p = st.session_state
    bmr,tdee,tc,mac,_,_ = get_profile()

    hero("📋 Intake vs Requirement","Log today's food and see exactly where you stand.")

    co("🍽️ LOG YOUR FOOD")
    food_names = list(FOOD_DB.keys())
    n = st.number_input("Number of food items",1,12,5)
    items = []
    cols = st.columns(2)
    for i in range(n):
        with cols[i%2]:
            name = st.selectbox(f"Food {i+1}",food_names,key=f"f{i}")
            qty  = st.number_input(f"Grams/ml for item {i+1}",10,1000,100,key=f"q{i}")
            items.append({"name":name,"qty_g":qty})
    cc()

    if st.button("📊 Analyze My Intake"):
        consumed   = estimate_intake(items)
        comparison = compare_intake(consumed,tc,mac,p.goal)
        co("📊 COMPARISON")
        st.markdown(f"""<div class="mrow">
          {mbox("Calories",consumed['calories'],"kcal")}
          {mbox("Protein",consumed['protein'],"g","mg")}
          {mbox("Carbs",consumed['carbs'],"g","mb")}
          {mbox("Fat",consumed['fat'],"g","mp")}
        </div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        status_colors = {"balanced":"#00D4AA","deficit":"#FFB347","excess":"#FF4757"}
        for nut,data in comparison.items():
            sc = status_colors[data["status"]]
            bar(min(data["pct"],100),sc,nut.title(),f"{data['consumed']}/{data['required']} · {data['pct']}% · {data['status'].upper()}")
            if data["message"]:
                st.markdown(f'<div class="warn" style="font-size:.82rem;">{data["message"]}</div>',unsafe_allow_html=True)
        cc()


# ════════════════════════════════════════════════════════════════
# PAGE 5 — AI Food Recommendations
# ════════════════════════════════════════════════════════════════
elif page == "🍱 AI Food Recommendations":
    require_profile()
    p = st.session_state
    _,_,tc,mac,mic,_ = get_profile()

    hero("🍱 AI Food Recommendations","Content-based filtering ranks foods by your nutrient needs and goal.")
    ai_badge("Cosine Similarity · Nutrient Vector Matching")

    co("🎯 SELECT NUTRIENT DEFICITS TO FIX")
    all_micros = ["iron","calcium","vit_d","b12","magnesium","zinc"]
    sel_deficits = st.multiselect("Which micronutrients are you deficient in? (leave blank for goal-only)",
                                   all_micros,default=[])
    pref_override = st.radio("Show foods for:",["My preference","Vegetarian only","Non-vegetarian only"],horizontal=True)
    pref_map = {"My preference":p.preference,"Vegetarian only":"Vegetarian","Non-vegetarian only":"Non-Vegetarian"}
    pref = pref_map[pref_override]
    cc()

    if st.button("🤖 Generate AI Food Recommendations"):
        recs = recommend_foods(p.goal, sel_deficits, pref, top_n=8)
        st.session_state["food_recs"] = recs

    recs = st.session_state.get("food_recs")
    if not recs:
        recs = recommend_foods(p.goal, [], p.preference, top_n=8)
        st.session_state["food_recs"] = recs

    co(f"🏆 TOP PICKS FOR {p.goal.upper()}")
    display_foods = recs["veg"] if pref=="Vegetarian" else (recs["non_veg"] + recs["veg"])[:8]
    cols = st.columns(2)
    for i, food in enumerate(display_foods[:8]):
        with cols[i%2]:
            score_bar_w = int(food["score"]*100*3)
            veg_badge   = "🌿" if FOOD_DATABASE.get(food["name"],{}).get("veg",True) else "🍗"
            st.markdown(f"""<div class="food-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
              <div>
                <span style="font-size:.88rem;font-weight:600;color:var(--text);">{veg_badge} {food['name']}</span><br>
                <span style="font-size:.74rem;color:var(--muted);">{food['cal']} kcal · {food['protein']}g protein</span>
              </div>
              <span style="font-size:.72rem;color:#7B5EA7;background:rgba(123,94,167,.15);
                           padding:2px 8px;border-radius:100px;">{food['cost']}</span>
            </div>
            <div style="margin:.5rem 0 .3rem;">
              <div class="bar-wrap"><div class="bar-fill" style="width:{min(score_bar_w,100)}%;
              background:linear-gradient(90deg,#7B5EA7,#00D4AA);"></div></div>
            </div>
            <div style="font-size:.72rem;color:var(--muted);">✓ {food['reason']}</div>
            </div>""",unsafe_allow_html=True)
    cc()

    if sel_deficits and recs.get("deficit_picks"):
        co("💊 DEFICIT-SPECIFIC PICKS")
        for deficit, foods in recs["deficit_picks"].items():
            if foods:
                st.markdown(f"**{deficit.replace('_',' ').title()}:** " + " · ".join([f"`{f}`" for f in foods]))
        cc()


# ════════════════════════════════════════════════════════════════
# PAGE 6 — AI Diet Plan
# ════════════════════════════════════════════════════════════════
elif page == "🍽️ AI Diet Plan":
    require_profile()
    p = st.session_state
    _,_,tc,mac,_,_ = get_profile()
    fitness_intelligence = get_session_intelligence(st.session_state)
    adjusted_tc, adjusted_mac = adjusted_diet_targets(tc, mac, fitness_intelligence)

    hero("🍽️ AI Diet Plan Generator","Multi-objective scoring selects meals for maximum macro fit and variety.")
    ai_badge("Multi-Objective Meal Scoring · Variety Engine")

    st.info(f"🎯 Target: **{tc:.0f} kcal** · **{mac['protein']}g protein** · {p.preference} · {p.goal}")

    tab1, tab2 = st.tabs(["📅 Today's Plan","🗓️ Weekly Variation"])

    with tab1:
        if st.button("🔄 Generate New Meal Plan"):
            st.session_state["ai_meal_plan"] = generate_ai_meal_plan(
                p.goal, tc, mac, p.preference, fitness_intelligence=fitness_intelligence
            )

        if "ai_meal_plan" not in st.session_state:
            st.session_state["ai_meal_plan"] = generate_ai_meal_plan(
                p.goal, tc, mac, p.preference, fitness_intelligence=fitness_intelligence
            )

        plan = st.session_state["ai_meal_plan"]
        fit_score = plan.get("macro_fit_score",0)
        st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:.8rem;">
          <span style="font-size:.82rem;color:var(--muted);">Macro Fit Score:</span>
          <div style="flex:1;max-width:200px;"><div class="bar-wrap">
          <div class="bar-fill" style="width:{fit_score}%;background:#00D4AA;"></div></div></div>
          <span style="font-size:.82rem;font-weight:600;color:#00D4AA;">{fit_score}/100</span>
        </div>""",unsafe_allow_html=True)

        meal_icons  = {"breakfast":"🌅","lunch":"☀️","dinner":"🌙","snack":"🍎"}
        meal_colors = {"breakfast":"#FF6B35","lunch":"#00D4AA","dinner":"#7B5EA7","snack":"#FFB347"}
        for mk,icon in meal_icons.items():
            if mk in plan and isinstance(plan[mk],dict):
                m = plan[mk]
                c = meal_colors[mk]
                veg = "🌿" if m.get("veg",True) else "🍗"
                st.markdown(f"""<div class="meal-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px;">
                    <div>
                      <div style="font-size:.72rem;color:{c};text-transform:uppercase;
                                  letter-spacing:.07em;margin-bottom:.2rem;">{icon} {mk.title()}</div>
                      <div style="font-size:.96rem;font-weight:600;color:var(--text);">{veg} {m['name']}</div>
                      <div style="font-size:.76rem;color:var(--muted);margin-top:.2rem;">
                        ⏱ {m['prep_min']} min prep · {m['fiber']}g fiber</div>
                    </div>
                    <div style="display:flex;gap:.4rem;flex-wrap:wrap;">
                      <span class="pill" style="border:1px solid {c};color:{c};">{m['calories']} kcal</span>
                      <span class="pill" style="border:1px solid #00D4AA;color:#00D4AA;">{m['protein']}g protein</span>
                      <span class="pill" style="border:1px solid #4A90D9;color:#4A90D9;">{m['carbs']}g carbs</span>
                    </div>
                  </div>
                </div>""",unsafe_allow_html=True)

        co("📊 DAY TOTALS")
        st.markdown(f"""<div class="mrow">
          {mbox("Total Cal",plan.get('total_calories','—'),"kcal","my")}
          {mbox("Total Protein",plan.get('total_protein','—'),"g","mg")}
          {mbox("Total Carbs",plan.get('total_carbs','—'),"g","mb")}
          {mbox("Total Fat",plan.get('total_fat','—'),"g","mp")}
        </div>""",unsafe_allow_html=True)
        cc()

    with tab2:
        if st.button("🔄 Generate 7-Day Meal Plan"):
            st.session_state["weekly_plans"] = generate_weekly_variation(
                p.goal, tc, mac, p.preference, fitness_intelligence
            )
        if "weekly_plans" not in st.session_state:
            st.session_state["weekly_plans"] = generate_weekly_variation(
                p.goal, tc, mac, p.preference, fitness_intelligence
            )
        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        for day,plan in zip(days,st.session_state["weekly_plans"]):
            with st.expander(f"📅 {day} — {plan.get('total_calories','?')} kcal · {plan.get('total_protein','?')}g protein"):
                for mk in ("breakfast","lunch","dinner","snack"):
                    if mk in plan and isinstance(plan[mk],dict):
                        m = plan[mk]
                        st.markdown(f"**{mk.title()}:** {m['name']} — {m['calories']} kcal · {m['protein']}g protein")


# ════════════════════════════════════════════════════════════════
# PAGE 7 — AI Workout Guide
# ════════════════════════════════════════════════════════════════
elif page == "💪 AI Workout Guide":
    require_profile()
    p = st.session_state

    hero("💪 AI Workout Guide","Decision Tree selects your optimal plan based on goal, experience, and feedback.")
    ai_badge("Decision Tree Classifier · Feedback-Adaptive")

    issues = st.session_state.get("feedback_issues",[])
    fitness_intelligence = get_session_intelligence(st.session_state)
    workout = get_ai_workout(p.goal,p.experience,issues,p.workout_days,fitness_intelligence)

    co("🤖 AI REASONING")
    st.markdown(f'<div class="tip">{workout.get("ai_reasoning","—")}</div>',unsafe_allow_html=True)
    cc()

    co(f"📋 {workout.get('title','Workout Plan').upper()}")
    c1,c2,c3 = st.columns(3)
    c1.markdown(f"**Split:** {workout.get('split','—')}")
    c2.markdown(f"**Intensity:** {workout.get('intensity','—')}")
    c3.markdown(f"**Progression:** {workout.get('progression','—')}")
    cc()

    day_type_colors = {"Strength":"#00D4AA","Light Strength":"#4A90D9",
                       "Cardio":"#FFB347","Active Rest":"#6B7280","Rest":"#3D4155",
                       "Cardio + Core":"#FF6B35","Cardio + Strength":"#FF6B35"}

    for day,(focus,exercises,dtype) in workout.get("schedule",{}).items():
        color = day_type_colors.get(dtype,"#6B7280")
        co(f"📅 {day.upper()} — {focus}")
        st.markdown(f'<span style="border:1px solid {color};color:{color};padding:3px 12px;'
                    f'border-radius:100px;font-size:.74rem;">{dtype}</span><br><br>',unsafe_allow_html=True)
        for ex,sets in exercises:
            st.markdown(f"""<div style="display:flex;justify-content:space-between;
              padding:5px 0;border-bottom:1px solid #1A1D27;font-size:.86rem;">
              <span style="color:var(--text);">{ex}</span>
              <span style="color:{color};font-weight:600;">{sets}</span>
            </div>""",unsafe_allow_html=True)
        cc()

    co("💤 RECOVERY TIPS")
    for tip in workout.get("recovery",["Rest and recover well."]):
        st.markdown(f'<div class="tip" style="margin-bottom:.3rem;">💤 {tip}</div>',unsafe_allow_html=True)
    cc()


# ════════════════════════════════════════════════════════════════
# PAGE 8 — AI Feedback Analysis (Gemini Powered)
# ════════════════════════════════════════════════════════════════
elif page == "🧠 AI Feedback Analysis":
    require_profile()
    show_sentiment_page()

st.markdown("""<hr style="border-color:#252836;margin-top:3rem;">
<p style="text-align:center;color:#3D4155;font-size:.76rem;padding-bottom:1rem;">
Smart Body Transformation AI Coach · ML: scikit-learn · Feedback: Google Gemini AI ·
Results are estimates — consult a professional before major changes.
</p>""",unsafe_allow_html=True)
