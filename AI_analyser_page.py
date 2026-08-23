"""
AI_analyser.py
─────────────────
Fitness Journal & Mood Analyzer — nvb AI powered
Integrated into Smart Body Transformation AI Coach.
"""

import re
import json
import pandas as pd
import streamlit as st
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI
from fitness_intelligence import normalize_fitness_intelligence, store_session_intelligence
load_dotenv(dotenv_path="./NVIDIA_API_KEY.env")
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY not found in environment variables")

client = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)



SYSTEM_PROMPT = """
You are a Fitness Intelligence Engine embedded inside a Smart Body Transformation AI Coach app.

The user will share a fitness journal entry — how they are feeling, their struggles, wins, energy levels, sleep, nutrition, workouts, etc.

Your job is to deeply analyze this entry and generate structured fitness intelligence. You must return ONLY a valid JSON object.

Do NOT estimate physiological transformation outcomes like weight loss, muscle gain, body fat %, or BMI. Those are calculated by a separate scientific engine. You must only estimate behavioral and recovery metrics based on their written journal entry.

Return exactly this JSON structure:
{
  "sentiment": "positive" or "neutral" or "negative",
  "urgency": "low" or "medium" or "high",
  "key_issues": ["tag1", "tag2"],  // Choose from: fatigue, plateau, low motivation, diet struggle, overtraining, sleep issues, stress, skipped workouts, cravings, feeling strong, progress visible, consistency, injury risk, emotional eating, dehydration, binge eating, positive momentum, lack of support, body image concern.
  
  "fitness_scores": {
    "adherence_score": 0-100, // How well they followed their fitness routine (workouts, nutrition, steps) recently
    "recovery_score": 0-100,  // Recovery status based on soreness, energy, sleep
    "nutrition_score": 0-100, // Quality and consistency of their diet
    "training_quality": 0-100,// Workout intensity, strength, performance mentioned
    "motivation_score": 0-100,// Readiness, enthusiasm, focus level
    "stress_score": 0-100,    // Stress levels (school, work, life)
    "sleep_quality": 0-100,   // Quality and quantity of sleep
    "plateau_probability": 0-100, // Likelihood that progress is stalling
    "injury_risk": 0-100      // Risk of injury based on joint pain, excessive soreness, overtraining
  },
  "confidence_score": 0-100,  // How confident you are in this analysis (0-100). Vague or short entries must yield low confidence (< 40)

  "diet_adjustment": {
    "protein_delta": number, // Adjustment in grams (e.g. 20, -10, 0)
    "calorie_delta": number, // Adjustment in kcal (e.g. -150, 100, 0)
    "carb_delta": number,    // Adjustment in grams (e.g. -20, 10, 0)
    "fat_delta": number      // Adjustment in grams (e.g. -5, 5, 0)
  },

  "workout_adjustment": {
    "intensity": "reduce" or "maintain" or "increase",
    "volume": "low" or "medium" or "high",
    "recovery_days": number // Recommended extra rest days this week (0-7)
  },

  "recommendations": [
    "...", // Exactly 3 short, specific, actionable recommendations. Be specific (e.g. "Add 30g protein to breakfast to curb cravings")
    "...",
    "..."
  ],

  "motivation": "..." // One short personal motivational sentence (max 20 words) addressing their situation.
}

STRICT RULES:
- Return ONLY the JSON object. No explanation, no markdown, no backticks.
- Vague or short inputs (e.g. "Feeling ok") must result in a confidence_score below 40.
- Clamping scores to 0-100 is done by a validation layer, but try to be accurate.
- Maintain empathy and context of their goal in motivation and recommendations.
"""


def validate_fitness_intelligence(raw_json: dict) -> dict:
    """
    Validation Layer:
    - Validates JSON structure.
    - Clamps every score to 0-100.
    - Applies sensible defaults if fields are missing.
    - Rejects malformed values and handles low confidence.
    """
    intel = {
        "sentiment": raw_json.get("sentiment", "neutral"),
        "urgency": raw_json.get("urgency", "low"),
        "key_issues": raw_json.get("key_issues", []),
        "fitness_scores": {},
        "confidence_score": raw_json.get("confidence_score", 85),
        "diet_adjustment": {},
        "workout_adjustment": {},
        "recommendations": raw_json.get("recommendations", raw_json.get("action_nudges", [])),
        "motivation": raw_json.get("motivation", "Stay consistent and keep pushing!")
    }

    if not isinstance(intel["key_issues"], list):
        intel["key_issues"] = []
    if not isinstance(intel["recommendations"], list):
        intel["recommendations"] = []

    try:
        intel["confidence_score"] = max(0, min(100, int(intel["confidence_score"])))
    except Exception:
        intel["confidence_score"] = 85

    # Validate fitness scores (0-100)
    default_scores = {
        "adherence_score": 90,
        "recovery_score": 80,
        "nutrition_score": 80,
        "training_quality": 80,
        "motivation_score": 80,
        "stress_score": 20,
        "sleep_quality": 80,
        "plateau_probability": 5,
        "injury_risk": 5
    }
    raw_scores = raw_json.get("fitness_scores", {})
    if not isinstance(raw_scores, dict):
        raw_scores = {}
    for k, v in default_scores.items():
        try:
            score_val = int(raw_scores.get(k, v))
            intel["fitness_scores"][k] = max(0, min(100, score_val))
        except Exception:
            intel["fitness_scores"][k] = v

    # Validate diet adjustments
    default_diet = {
        "protein_delta": 0,
        "calorie_delta": 0,
        "carb_delta": 0,
        "fat_delta": 0
    }
    raw_diet = raw_json.get("diet_adjustment", {})
    if not isinstance(raw_diet, dict):
        raw_diet = {}
    for k, v in default_diet.items():
        try:
            val_key = k
            # support both exact and raw abbreviations
            val = raw_diet.get(k, raw_diet.get(k.replace("_delta", ""), v))
            intel["diet_adjustment"][k] = max(-2000, min(2000, int(val)))
        except Exception:
            intel["diet_adjustment"][k] = v

    # Validate workout adjustments
    default_workout = {
        "intensity": "maintain",
        "volume": "medium",
        "recovery_days": 0
    }
    raw_workout = raw_json.get("workout_adjustment", {})
    if not isinstance(raw_workout, dict):
        raw_workout = {}

    intensity = str(raw_workout.get("intensity", default_workout["intensity"])).lower()
    if intensity not in ("reduce", "maintain", "increase"):
        intensity = "maintain"
    intel["workout_adjustment"]["intensity"] = intensity

    volume = str(raw_workout.get("volume", default_workout["volume"])).lower()
    if volume not in ("low", "medium", "high"):
        volume = "medium"
    intel["workout_adjustment"]["volume"] = volume

    try:
        rec_days = int(raw_workout.get("recovery_days", default_workout["recovery_days"]))
        intel["workout_adjustment"]["recovery_days"] = max(0, min(7, rec_days))
    except Exception:
        intel["workout_adjustment"]["recovery_days"] = 0

    # Add legacy score field for UI backward compatibility
    intel["score"] = intel["fitness_scores"]["recovery_score"]
    intel["fitness_scores"]["confidence_score"] = intel["confidence_score"]
    intel["action_nudges"] = intel["recommendations"]

    intel = normalize_fitness_intelligence(intel)

    return intel


def analyze_journal(entry: str) -> dict:
    full_prompt = SYSTEM_PROMPT + f"\n\nUser journal entry:\n{entry}"

    response = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1",
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.2,
        max_tokens=1000
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        # Fallback to an empty structure that the validation layer can fix
        parsed = {}
        print(f"Warning: JSON decode failed for response: {raw}. Error: {e}")

    return validate_fitness_intelligence(parsed)


def show_sentiment_page():
    goal = st.session_state.get("goal", "Fat Loss")

    # ── Hero ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#141720 0%,#0F1117 60%,#0a0a1a 100%);
        border:1px solid #252836;border-radius:20px;padding:2.5rem 3rem;margin-bottom:2rem;">
        <div style="font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;
            background:linear-gradient(90deg,#7B5EA7 0%,#A78BCC 100%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            margin-bottom:0.4rem;">🧠 AI Fitness Journal & Mood Analyzer</div>
        <p style="color:#6B7280;font-size:1rem;margin:0;">
            Write how you're feeling. AI detects your mood, identifies issues,
            and gives personalized action nudges. Results also update your workout plan.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<span style="background:rgba(123,94,167,.15);border:1px solid rgba(123,94,167,.4);'
                'color:#A78BCC;border-radius:100px;font-size:.72rem;padding:3px 10px;">'
                '🤖 Powered by NVIDIA AI</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick prompts based on current goal ──────────────────────────────────
    QUICK = {
        "Fat Loss":           ["Feeling tired, skipped 2 workouts", "Crushed my workout today!",
                               "Scale not moving despite eating clean", "Struggling with late night cravings"],
        "Muscle Gain":        ["Hit a new PR on bench press!", "Too sore to train today",
                               "Eating enough but not seeing size", "Motivated and consistent this week"],
        "Weight Gain":        ["Can't eat enough, always full", "Weight went up this week!",
                               "Missing meals due to busy schedule", "Struggling to hit calorie target"],
        "Body Recomposition": ["Looking leaner but weight same", "Feeling good and consistent",
                               "Stressed from exams, no energy", "Seeing muscle definition appear!"],
    }
    st.markdown("**Try a quick prompt:**")
    cols = st.columns(2)
    for i, q in enumerate(QUICK.get(goal, QUICK["Fat Loss"])):
        if cols[i % 2].button(q, key=f"sp_quick_{i}"):
            st.session_state["journal_input"] = q
            st.rerun()

    # ── Journal input ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    entry = st.text_area(
        "What's on your mind today?",
        value=st.session_state.get("journal_input", ""),
        height=130,
        placeholder=(
            "e.g. I've been really tired this week, skipped the gym twice. "
            "Eating okay but the scale hasn't moved in 10 days. "
            "Feeling a bit demotivated..."
        ),
    )

    col_btn, col_clear = st.columns([3, 1])
    analyze_clicked = col_btn.button("🔍 AI Analyze", type="primary")
    if col_clear.button("Clear", key="sp_clear"):
        st.session_state["journal_input"] = ""
        st.rerun()

    # ── Analysis ──────────────────────────────────────────────────────────────
    if analyze_clicked:
        if not entry.strip():
            st.warning("Please write something first!")
        else:
            with st.spinner("AI is analyzing your entry..."):
                try:
                    result = store_session_intelligence(st.session_state, analyze_journal(entry))

                    # ── Save issues to session state for workout page ─────────
                    st.session_state["feedback_issues"] = result.get("key_issues", [])

                    # Also update AI engine if available
                    engine = st.session_state.get("ai_engine")
                    if engine:
                        engine.feedback_state = {
                            "issues":    result.get("key_issues", []),
                            "sentiment": result.get("sentiment", "neutral"),
                            "score":     result.get("score", 50),
                            "fitness_intelligence": result,
                            "fitness_scores": result.get("fitness_scores", {}),
                        }

                    # ── Display result ────────────────────────────────────────
                    sentiment_colors = {
                        "positive": ("#00D4AA", "🟢"),
                        "neutral":  ("#FFB347", "🟡"),
                        "negative": ("#FF4757", "🔴"),
                    }
                    color, icon = sentiment_colors.get(result["sentiment"], ("#E8EAF0", "⚪"))

                    # Result card
                    st.markdown(f"""
                    <div style="background:#141720;border:1px solid #252836;
                        border-radius:16px;padding:1.8rem 2rem;margin:1.5rem 0 1rem;">
                        <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:1.2rem;flex-wrap:wrap;gap:8px;">
                            <span style="font-family:'Syne',sans-serif;font-size:1rem;
                                font-weight:700;color:#E8EAF0;">Fitness Intelligence Result</span>
                            <div style="display:flex;gap:8px;align-items:center;">
                                <span style="background:transparent;border:1px solid {color};
                                    color:{color};padding:4px 14px;border-radius:100px;
                                    font-size:0.82rem;font-weight:600;">
                                    {icon} {result['sentiment'].capitalize()}</span>
                                <span style="background:#1A1D27;border:1px solid #252836;
                                    color:#6B7280;padding:4px 12px;border-radius:100px;
                                    font-size:0.82rem;">{result['urgency'].capitalize()} urgency</span>
                            </div>
                        </div>
                        <div style="font-size:0.8rem;color:#6B7280;margin-bottom:6px;">
                            Recovery score: <strong style="color:#E8EAF0">{result['score']}/100</strong>
                        </div>
                        <div style="background:#1A1D27;border-radius:100px;height:10px;overflow:hidden;">
                            <div style="width:{result['score']}%;height:100%;border-radius:100px;
                                background:linear-gradient(90deg,{color},{color}88);"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Issues
                    st.markdown("**Detected issues:**")
                    tags_html = "".join([
                        f'<span style="background:#1A1D27;border:1px solid #252836;'
                        f'color:#6B7280;padding:4px 12px;border-radius:100px;'
                        f'font-size:0.82rem;margin:3px;display:inline-block;">{issue}</span>'
                        for issue in result["key_issues"]
                    ])
                    st.markdown(f'<div style=" margin-bottom:1.2rem;">{tags_html}</div>',
                                unsafe_allow_html=True)

                    scores = result.get("fitness_scores", {})
                    st.markdown("**Fitness Intelligence Scores:**")
                    score_cols = st.columns(5)
                    score_labels = [
                        ("Adherence", "adherence_score"),
                        ("Recovery", "recovery_score"),
                        ("Nutrition", "nutrition_score"),
                        ("Training", "training_quality"),
                        ("Motivation", "motivation_score"),
                        ("Stress", "stress_score"),
                        ("Sleep", "sleep_quality"),
                        ("Plateau", "plateau_probability"),
                        ("Injury Risk", "injury_risk"),
                        ("Confidence", "confidence_score"),
                    ]
                    for i, (label, key) in enumerate(score_labels):
                        score_cols[i % 5].metric(label, f"{scores.get(key, 0)}/100")

                    # Action nudges
                    st.markdown("---")
                    st.markdown("**💡 Action nudges for you:**")
                    for nudge in result["recommendations"]:
                        st.success(f"→ {nudge}")

                    # Motivation
                    st.markdown("---")
                    st.markdown(
                        f'<div style="border-left:3px solid #7B5EA7;padding:0.8rem 1.2rem;'
                        f'color:#A78BCC;font-style:italic;font-size:0.95rem;margin-top:0.5rem;">'
                        f'"{result["motivation"]}"</div>',
                        unsafe_allow_html=True
                    )

                    # Save to history
                    if "journal_history" not in st.session_state:
                        st.session_state["journal_history"] = []
                    st.session_state["journal_history"].append({
                        "date":      datetime.now().strftime("%d %b, %I:%M %p"),
                        "entry":     entry[:65] + "..." if len(entry) > 65 else entry,
                        "sentiment": result["sentiment"],
                        "score":     result["score"],
                        "urgency":   result["urgency"],
                        "fitness_scores": result.get("fitness_scores", {}),
                    })

                    st.info("🤖 Workout plan on **AI Workout Guide** has been updated based on your feedback!")

                except json.JSONDecodeError:
                    st.error("AI returned unexpected response. Please try again.")
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

    # ── Journal History ───────────────────────────────────────────────────────
    history = st.session_state.get("journal_history", [])
    if history:
        st.markdown("---")
        st.markdown("### 📈 Journal History & Mood Trend")

        pos    = sum(1 for h in history if h["sentiment"] == "positive")
        avg    = round(sum(h["score"] for h in history) / len(history))
        streak = 0
        for h in reversed(history):
            if h["sentiment"] == "positive": streak += 1
            else: break

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Entries",  len(history))
        m2.metric("Positive Days",  pos)
        m3.metric("Avg Mood Score", f"{avg}/100")
        m4.metric("Positive Streak", streak)

        if len(history) > 1:
            df = pd.DataFrame(history)
            st.line_chart(df.set_index("date")["score"], height=180)

        st.markdown("<br>", unsafe_allow_html=True)
        for h in reversed(history):
            dot = {"positive":"#00D4AA","neutral":"#FFB347","negative":"#FF4757"}.get(h["sentiment"],"#6B7280")
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
                background:#141720;border:1px solid #252836;border-radius:12px;margin-bottom:6px;">
                <div style="width:9px;height:9px;border-radius:50%;background:{dot};flex-shrink:0;"></div>
                <div style="flex:1;font-size:0.88rem;color:#6B7280;overflow:hidden;
                    white-space:nowrap;text-overflow:ellipsis;">{h['entry']}</div>
                <span style="font-size:0.78rem;color:{dot};border:1px solid {dot};
                    padding:2px 10px;border-radius:100px;flex-shrink:0;">{h['sentiment']}</span>
                <span style="font-size:0.78rem;color:#3D4155;flex-shrink:0;">{h['date']}</span>
            </div>
            """, unsafe_allow_html=True)
