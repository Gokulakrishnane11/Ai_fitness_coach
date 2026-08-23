# AI Handoff Document - Smart Body Transformation AI Coach

Generated: 2026-07-12 | Developer: Gokul (B.Tech AI & DS, 2nd Year, Tamil Nadu, India)
Purpose: Complete context transfer for any AI assistant to continue development.

---

## Project Vision

Smart Body Transformation AI Coach is a Streamlit web application and hackathon
submission for PPG College (Topic 1: AI-Driven Sentiment Analysis & Actionable
Insight Generation applied to a health and fitness coaching context).

Core closed-loop adaptive system:
1. User sets fitness goal and body stats
2. ML models predict scientifically realistic transformation timelines
3. AI generates personalised meal plans, food recommendations, and workout programs
4. User writes journal entries about how they feel
5. NVIDIA NIM LLM analyzes journal, detects mood/issues, dynamically adapts plans

End goal: A self-correcting AI fitness coach that reads your mood, knows the
science, and adjusts your plan accordingly - all in real time.

---

## Tech Stack

- Frontend/UI: Python + Streamlit with custom CSS dark theme (Poppins font)
- Machine Learning: scikit-learn (Random Forest, Decision Tree, cosine_similarity, Pipeline)
- NLP/AI: NVIDIA NIM API (nvidia/llama-3.3-nemotron-super-49b-v1) via OpenAI Python SDK
- Data: Pandas, NumPy, Joblib
- Visualization: Streamlit charts, Matplotlib, Seaborn

---

## Current Development Status

| Layer | Status |
|---|---|
| Core UI (Streamlit, 8 pages) | COMPLETE |
| Nutrition Engine (BMR/TDEE/macros/micros) | COMPLETE |
| fat_loss_model.pkl (12.9MB RF model) | COMPLETE |
| transformation_models.pkl (14.8MB, 4-goal RF) | COMPLETE |
| AI Food Recommender (cosine similarity) | COMPLETE |
| AI Diet Planner (multi-objective scoring) | COMPLETE |
| AI Workout Guide (Decision Tree) | COMPLETE |
| AI Journal / Mood Analyzer (NVIDIA API) | COMPLETE |
| Transformation Prediction (static) | COMPLETE |
| Predictive Simulation (multi-week) | COMPLETE |
| transformation_engine/ package refactor | COMPLETE |
| Fitness Intelligence system | COMPLETE |
| Parity test suite | WRITTEN but not verified |
| prediction.py | EMPTY FILE - orphaned placeholder |
| End-to-end integration testing | NOT DONE |
| Hackathon polish and final presentation | PENDING |

---

## Project Architecture

Root-level files:
  app.py (601 lines)          Main Streamlit entry point, all 8 pages
  AI_analyser_page.py         NVIDIA LLM journal analysis + Streamlit UI (442 lines)
  fitness_intelligence.py     Shared FI state, normalization, behavior adapters (183 lines)
  ai_engine.py                Central AIEngine class (128 lines)
  ai_food.py                  Content-based food recommender (cosine similarity, 32 foods)
  ai_diet.py                  Multi-objective meal plan generator (55 meals)
  ai_workout.py               Decision Tree workout classifier (10+ templates, 321 lines)
  nutrition.py                BMR/TDEE/macros/micros, 20-item food DB, intake compare
  transformation_prediction.py Legacy 1000-line monolith (still used as proxy)
  train_model.py              Full training pipeline (LR + RF, saves pkl, generates plots)
  dataset_generator.py        Synthetic 1200-row fat loss dataset generator
  prediction.py               EMPTY - orphaned placeholder, safe to delete
  fat_loss_dataset.csv        1200-row synthetic training data
  fat_loss_model.pkl          12.9MB Random Forest (fat-loss only)
  transformation_models.pkl   14.8MB Dict of 4 goal-specific RF models
  NVIDIA_API_KEY.env          API key loaded via python-dotenv
  run.bat                     Windows launcher (.venv\Scripts\python.exe)

transformation_engine/ package (13 modules - refactored architecture):
  __init__.py             Public API (backward compatible with app.py imports)
  model_loader.py         Load .pkl files (singleton UNIFIED_MODELS global)
  feature_processor.py    Preprocess user inputs to ML feature DataFrame
  physiology_engine.py    BMR/TDEE/sub-scores calculations
  goal_logic.py           Pure physics: fat loss/muscle/weight/recomp rate formulas
  prediction_engine.py    Orchestrates ML + science blend; predict_fat_loss() etc.
  behavior_adjuster.py    Applies AI behavior factor (0.45-1.12 multiplier)
  simulation_engine.py    Week-by-week simulation loop with FI drift
  simulation_page.py      Streamlit Predictive Simulation page (ONLY Streamlit file)
  context.py              PredictionContext dataclass
  validator.py            Input range validation
  ai_explainer.py         Human-readable AI reasoning explanations
  utils.py                Shared constants (RATE_CAPS, FEATURE_ORDER, etc.)

tests/ directory:
  test_parity_engine.py   Parity tests comparing new engine vs monolith
  _capture_baseline.py    Captures monolith outputs as baseline fixtures
  fixtures/               Baseline JSON snapshots

---

## Adaptive Loop (The Core Innovation)

User Profile → ML Prediction → AI Plans (workout/diet/food)
      |                                           |
      ^                                           v
Plans Updated <- AI Engine <- NVIDIA LLM <- User Journal Entry
                (issues, scores)   (sentiment, fitness_scores)

The fact that a journal entry changes the workout plan on the SAME session
without any user navigation is the key UX differentiator for the hackathon.

---

## All 8 Pages

Page 1 - Goal & Profile Setup:
  4-goal selector (Fat Loss, Muscle Gain, Weight Gain, Body Recomposition)
  Body stats: gender, age, height, weight, target weight, experience, activity, workout days, diet pref
  Saves profile and activates AIEngine in session state

Page 2 - Transformation Prediction:
  BMR (Mifflin-St Jeor), TDEE (activity multiplier), target calories, macros
  Goal-specific weekly/monthly predictions
  Fitness Intelligence adherence adjustment
  Timeline milestones generator

Page 3 - Predictive Simulation:
  Multi-week simulation with sliders (deficit/surplus, protein, cardio, sleep)
  Multiple adherence scenarios (50%, 70%, 90-100%)
  Line charts with weight progression
  Week-by-week FI drift via evolve_weekly_intelligence()

Page 4 - Nutrition Dashboard:
  Daily macro targets with goal-specific calculations (protein/carbs/fat/fiber)
  Micro-nutrient targets with RDA formulas (iron, calcium, vit-D, B12, magnesium, zinc)

Page 5 - Intake vs Requirement:
  Food logging (up to 12 items from 20-item database)
  Comparison with targets: deficit/balanced/excess status

Page 6 - AI Food Recommendations:
  Cosine similarity on 10-feature nutrient vectors (MinMaxScaler normalized)
  Goal-specific nutrient weight vectors
  Micro-deficit boosting (1.4x score multiplier)
  32 foods, veg/non-veg separated

Page 7 - AI Diet Plan:
  Multi-objective scoring: goal_score*2.0 + protein_score*1.8 + variety - cal_diff*1.5 + fiber + prep + noise
  FI adjusts calorie/macro targets before scoring
  Daily plan (breakfast/lunch/dinner/snack) with macro fit score (0-100)
  7-day weekly variation generator
  55 meals: Indian + universal, goal-tagged

Page 8 - AI Workout Guide:
  DecisionTreeClassifier trained on 24 examples at startup
  Features: [goal_enc, exp_enc, fatigue, low_motivation, injury_risk, workout_days, stress]
  10+ named templates: strength_cardio, hypertrophy_split, ppl_split, recomp_balanced,
    strength_bulk, deload, recovery_walk, machine_only, simple_compound
  FALLBACK_MAP for styles without full templates
  FI adjusts intensity/volume/recovery_days post-selection
  Schedule trimmed to available workout days

Page 9 (same nav) - AI Fitness Journal & Mood Analyzer:
  Free-text journal entry with goal-specific quick-prompt buttons
  NVIDIA NIM API call (model: nvidia/llama-3.3-nemotron-super-49b-v1, temp=0.2, max_tokens=1000)
  Returns JSON: sentiment, urgency, key_issues, 9 fitness_scores, confidence_score,
    diet_adjustment, workout_adjustment, 3 recommendations, motivation quote
  Validation layer: clamping 0-100, defaults, JSON decode error handling
  Stores to session_state -> immediately adapts workout guide and diet plan
  Journal history with mood trend line chart, positive streak counter

---

## Key Technical Decisions

### 1. NVIDIA NIM API over Google Gemini
Switched from Google Gemini to NVIDIA NIM API.
Model: nvidia/llama-3.3-nemotron-super-49b-v1
Reason: Better structured JSON instruction following, OpenAI-compatible SDK
Implementation: openai Python client pointing at https://integrate.api.nvidia.com/v1
Config: temperature=0.2, max_tokens=1000

### 2. AI Refines, Never Replaces Scientific Engine
Fitness Intelligence adjusts adherence_factor and behavior_multiplier ONLY.
It never modifies base physiological rates directly.
prediction_behavior_factor() returns value in [0.45, 1.12].
This prevents impossible AI claims like "lose 5kg per week".
Key rule: "The AI estimates behavior, recovery, and readiness.
  Scientific calculators remain responsible for body transformation numbers."
  - from fitness_intelligence.py docstring

### 3. Fitness Intelligence Validation Layer
Every NVIDIA API response passes through:
  validate_fitness_intelligence() - structure validation, clamping, defaults
  normalize_fitness_intelligence() - unified normalization with deepcopy of defaults
Handles: malformed JSON, out-of-range numbers, missing fields, JSON decode failures
Both layers exist for defense-in-depth.

### 4. transformation_engine/ Package Refactor
Refactored 1000-line monolith into 13-module package.
goal_logic.py: pure physics math (no imports from fitness_intelligence or model_loader)
simulation_page.py: ONLY file with Streamlit import in the package
Old transformation_prediction.py kept as backward-compatible proxy.
app.py imports unchanged (from transformation_prediction import ...).
Parity tests verify new package produces identical outputs to monolith.

### 5. Two ML Model Files
fat_loss_model.pkl (12.9MB): Random Forest 200 trees depth 12.
  Trained on 1200 synthetic rows. Features: 9 columns. Target: weekly_fat_loss_kg.
  Used by predict_fat_loss() legacy path.
transformation_models.pkl (14.8MB): Dict of 4 goal-specific RF models.
  Each trained on 2500 synthetic rows. Features: 12 columns.
  Used by all prediction functions via load_models().

### 6. Decision Tree Workout Classifier
sklearn DecisionTreeClassifier, max_depth=5, random_state=42.
24 hand-crafted training examples covering goal x experience x state combinations.
Trained at module import time (fast, no file I/O).
_CLASSIFIER = _train_classifier() called at module level.

### 7. Cosine Similarity Food Recommender
10-feature nutrient vectors: protein, carbs, fat, fiber, iron, calcium, vit_d, b12, magnesium, zinc.
MinMaxScaler normalization. Goal-specific GOAL_NUTRIENT_WEIGHTS bias the need vector.
Micro-deficit foods boosted 1.4x. Affordability and prep-ease get small bonuses.

### 8. All State In-Memory
All user data in st.session_state. No database or file persistence.
Data is lost on page refresh. Acceptable for hackathon scope.

### 9. Indian Food Focus
MEAL_DB and FOOD_DATABASE are primarily Indian foods.
(dal, roti, paneer, poha, rajma, moong, etc. plus universal foods)

---

## Session State Keys

Key session state variables set by the app:
  goal              str: "Fat Loss" | "Muscle Gain" | "Weight Gain" | "Body Recomposition"
  gender            str: "Male" | "Female"
  age               int
  height_cm         int
  weight_kg         int
  target_weight     int
  experience        str: "Beginner" | "Intermediate" | "Advanced"
  workout_days      int
  activity_level    str (one of ACTIVITY_MULTIPLIERS keys)
  preference        str: "Vegetarian" | "Non-Vegetarian"
  profile_set       bool: True once Save & Activate is clicked
  journal_history   list of dicts: [{date, entry, sentiment, score, urgency, fitness_scores}]
  feedback_issues   list of str: issue tags from last journal analysis
  fitness_intelligence dict: normalized FI object (set by store_session_intelligence)
  ai_engine         AIEngine instance
  food_recs         cached food recommendations
  ai_meal_plan      cached daily meal plan
  weekly_plans      cached 7-day meal plans

---

## Data Flow Details

Prediction flow:
  User inputs (Streamlit widgets)
    -> st.session_state
    -> nutrition.py: calculate_bmr(), calculate_tdee(), get_target_calories(), calculate_macros()
    -> get_session_intelligence(st.session_state) - get FI scores
    -> adherence_factor_from_intelligence() - convert FI to adherence factor
    -> predict_fat_loss(deficit*7, weight, workout_days, protein, ml_model, profile=profile_dict)
    -> shown on Prediction page

Journal -> Adaptation flow:
  User journal text
    -> AI_analyser_page.analyze_journal(entry)
    -> NVIDIA NIM API (structured JSON response)
    -> validate_fitness_intelligence(parsed_json)
    -> normalize_fitness_intelligence(validated)
    -> store_session_intelligence(st.session_state, result)
       - sets: st.session_state.fitness_intelligence, feedback_issues, fitness_scores
    -> On Workout page: get_ai_workout(goal, experience, feedback_issues, days, fitness_intelligence)
    -> On Diet page: adjusted_diet_targets(tc, mac, fitness_intelligence)
    -> On Prediction page: adherence_factor_from_intelligence(fitness_intelligence)
    -> On Simulation: prediction_behavior_factor(fitness_intelligence)

---

## Nutrition Calculations

BMR (Mifflin-St Jeor):
  Male:   10*weight + 6.25*height - 5*age + 5
  Female: 10*weight + 6.25*height - 5*age - 161

TDEE = BMR * activity_multiplier
  Sedentary: 1.2 | Lightly Active: 1.375 | Moderately Active: 1.55
  Very Active: 1.725 | Extremely Active: 1.9

Target calories = TDEE + goal_delta
  Fat Loss: -400 | Muscle Gain: +350 | Weight Gain: +650 | Recomp: 0

Protein targets (g/kg bodyweight):
  Fat Loss: 2.2 | Muscle Gain: 2.5 | Weight Gain: 1.8 | Recomp: 2.6

Fat %: 22% of calories (Muscle/Weight Gain) or 27% (Fat Loss/Recomp)
Carbs: remainder after protein and fat calories
Fiber: 14g per 1000 kcal

---

## Physiological Rate Caps

Fat Loss:           max 0.90 kg/week
Muscle Gain:        max 0.35 kg/week
Weight Gain:        max 1.00 kg/week
Body Recomposition: fat_loss max 0.25 kg/week, muscle_gain max 0.15 kg/week

Beginner muscle gain potential: 0.25 kg/week
Intermediate: 0.15 kg/week
Advanced: 0.06 kg/week

Fat loss prediction blend: 0.55 * scientific + 0.45 * ml_rate
Behavior factor range: [0.45, 1.12]

---

## NVIDIA LLM System Prompt (Critical)

The LLM is instructed to:
1. Act as Fitness Intelligence Engine embedded in the app
2. Return ONLY valid JSON - no markdown, no backticks, no explanation
3. NOT estimate physiological outcomes (weight loss kg, BMI changes) - scientific engine handles that
4. Return exactly this structure:
   {
     "sentiment": "positive"|"neutral"|"negative",
     "urgency": "low"|"medium"|"high",
     "key_issues": [list from predefined tags],
     "fitness_scores": {
       "adherence_score": 0-100,
       "recovery_score": 0-100,
       "nutrition_score": 0-100,
       "training_quality": 0-100,
       "motivation_score": 0-100,
       "stress_score": 0-100,
       "sleep_quality": 0-100,
       "plateau_probability": 0-100,
       "injury_risk": 0-100
     },
     "confidence_score": 0-100,
     "diet_adjustment": {protein_delta, calorie_delta, carb_delta, fat_delta},
     "workout_adjustment": {intensity, volume, recovery_days},
     "recommendations": ["...", "...", "..."],  (exactly 3)
     "motivation": "..."  (max 20 words)
   }
5. Vague/short inputs must yield confidence_score < 40

Available key_issue tags:
fatigue, plateau, low motivation, diet struggle, overtraining, sleep issues,
stress, skipped workouts, cravings, feeling strong, progress visible, consistency,
injury risk, emotional eating, dehydration, binge eating, positive momentum,
lack of support, body image concern

---

## Training Data Generation (for fat_loss_dataset.csv)

- 1200 synthetic profiles using numpy RandomState(42)
- Demographics: ages 18-65, male/female 52/48%, height correlated to gender
- Weight correlated to height with noise, range 45-140 kg
- Workout days: 0-7/week, daily steps: 7500 +/- 2500
- Daily calories: 1400-2800 kcal range (fat-loss population)
- Protein: 1.4-2.4 g/kg bodyweight
- Fat loss = (TDEE - daily_calories) * 7 / 7700, clipped to [-0.5, 1.5] kg/week
- Added Gaussian noise (sigma=0.03 kg)

For unified transformation_models.pkl (2500 rows each):
- Fat Loss: deficit*7/7700 * protein_factor * sleep_factor * gender_factor * adherence + exercise_bonus
- Muscle Gain: based on base_monthly by experience * surplus_factor * protein_factor * train_factor * adherence
- Weight Gain: surplus*7/7700 * age_factor * act_factor * adherence
- Recomposition: deficit-equivalent * protein_factor * train_factor * adherence

---

## Known Bugs and Technical Debt

1. prediction.py is empty - orphaned placeholder, safe to delete, nothing imports it
2. Parity tests (tests/test_parity_engine.py) written but not verified to pass
3. generate_weekly_variation() bug: used_history tracking incomplete across 7 days
4. Two prediction paths coexist: transformation_prediction.py + transformation_engine/
5. NVIDIA API key in plain NVIDIA_API_KEY.env - should be in .gitignore
6. Two separate food databases: FOOD_DB in nutrition.py (20 items) vs FOOD_DATABASE in ai_food.py (32 items)
7. analysis.ipynb appears to be a stub (3KB, likely minimal content)
8. No loading states for long operations except journal analysis spinner

---

## Environment Setup

Requirements: Python 3.10+, Windows (run.bat uses .venv\Scripts\)

Install:
  python -m venv .venv
  .venv\Scripts\activate
  pip install streamlit scikit-learn pandas numpy joblib matplotlib seaborn openai python-dotenv

Configure:
  Edit NVIDIA_API_KEY.env:
  NVIDIA_API_KEY = "your_nvapi_key_here"
  Get key at: https://build.nvidia.com

Optional - Regenerate models:
  python dataset_generator.py    (creates fat_loss_dataset.csv)
  python train_model.py          (creates both .pkl files + plots in assets/)

Run:
  streamlit run app.py
  OR: run.bat

---

## Blockers

1. prediction.py is empty - if anything imports from it, it will fail. Currently nothing does.
2. Parity tests not verified - run: python -m pytest tests/
3. NVIDIA free tier API rate limits - mindful usage during hackathon demo

---

## Next Tasks (Priority Order)

IMMEDIATE (Pre-Hackathon):
1. Delete prediction.py (empty orphan causing confusion)
2. Run parity tests: python -m pytest tests/
3. End-to-end smoke test: Fat Loss, Male, 22yo, 75kg->68kg, 4 workout days, Non-Vegetarian
4. Test journal adaptation: submit journal entries with different moods, verify workout adapts
5. Fix generate_weekly_variation() - properly propagate used_groups across all 7 days

POST-HACKATHON:
6. Consolidate transformation_prediction.py and transformation_engine/ (remove monolith after full parity verification)
7. Add persistent storage (SQLite or JSON file) for cross-session user data
8. Expand MEAL_DB and FOOD_DATABASE with more Indian regional meals
9. Add progress tracker page (weekly weigh-in logging, body measurements)
10. Export meal plan to PDF

---

## Important Context

1. This is a hackathon submission - not a production app. Some shortcuts are intentional.
2. The closed-loop journal -> LLM -> plan adaptation is the CORE differentiator - demo this prominently.
3. Gemini was the original LLM, switched to NVIDIA NIM for better reliability.
4. The transformation_engine/ refactor was done for testability, not new features.
5. fitness_intelligence.py is the nervous system connecting all modules.
6. All nutrition math uses validated medical formulas (Mifflin-St Jeor, RDA, 7700 kcal rule).
7. Indian food focus is intentional (developer and target audience context).
