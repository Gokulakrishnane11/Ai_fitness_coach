# Project History - Smart Body Transformation AI Coach

Chronological development log. Generated 2026-07-12 from code analysis and project journal.

---

## Project Overview

Name: Smart Body Transformation AI Coach
Developer: Gokul (B.Tech AI & DS, 2nd Year, Tamil Nadu, India)
Purpose: PPG College Hackathon - Topic 1: AI-Driven Sentiment Analysis & Actionable Insight Generation
Context: Self-taught frontend developer, Python & ML enthusiast

---

## Phase 1 - Initial Build

### What was built:
- Basic Streamlit UI with dark theme (CSS custom styling, Poppins font)
- Nutrition calculation engine: BMR (Mifflin-St Jeor), TDEE, macros, micronutrients
- dataset_generator.py: 1200-row synthetic fat-loss dataset using physiological formulas
- train_model.py: Trained Linear Regression and Random Forest on the dataset
  - Selected RF as best performer by R2 score
  - Saved as fat_loss_model.pkl (12.9MB)
  - Generated visualization plots: correlation heatmap, weight vs fat loss, feature importance
- nutrition.py: food database (20 items), intake estimation, compare_intake()
- Initial rule-based pages for diet, workout recommendations

### Key decisions:
- Chose Streamlit over React for rapid ML app development
- Used Mifflin-St Jeor formula (most validated BMR equation)
- Used 7700 kcal/kg rule for fat loss estimation
- Created synthetic data to avoid privacy/regulatory concerns

---

## Phase 2 - AI Integration

### What was added:
- ai_food.py: Content-based filtering using cosine similarity on nutrient vectors
  - 32-food FOOD_DATABASE with full macro/micro profiles
  - Goal-specific GOAL_NUTRIENT_WEIGHTS
  - MICRO_DEFICIT_BOOST for specific nutrient deficiencies
- ai_diet.py: Multi-objective meal plan generator
  - 55-meal MEAL_DB with Indian + universal meals, goal tags
  - Scoring function: goal_score, protein_score, variety, calorie proximity, fiber, prep time
  - Daily and 7-day weekly plan generation
- ai_workout.py: Decision Tree workout classifier
  - 24 training examples covering all goal/experience/state combinations
  - 10+ named WORKOUT_TEMPLATES (full schedules)
  - FALLBACK_MAP for missing templates
- sentiment_page.py (later renamed AI_analyser_page.py): Google Gemini AI journal analysis
  - Free-text journal entry input
  - Gemini API for sentiment, issues, recommendations
  - Journal history with mood trend chart
- Initial integration of journal feedback with workout adjustments

### Problems encountered:
- Gemini API had inconsistent JSON output formatting
- Structured output reliability was lower than needed for the validation layer
- This eventually led to the switch to NVIDIA NIM

---

## Phase 3 - Refactoring & Cleanup (2026-04-24 per journal)

### What was done:
- Full codebase analysis: reviewed all 15 Python files
- Identified redundant rule-based files:
  - diet_plan.py (old rule-based) - DELETED (replaced by ai_diet.py)
  - feedback.py (old rule-based) - DELETED (replaced by AI feedback)
  - workout.py (old rule-based) - DELETED (replaced by ai_workout.py)
- Fixed broken test.py that called non-existent app.load_model() function - DELETED
- Renamed sentiment_page.py to AI_analyser_page.py for clarity
- Set up PROJECT_JOURNAL.md to track future progress
- Confirmed end-to-end transition from rule-based to AI modules was clean

### Decision recorded in journal:
"Transitioning from strict rule-based logic to ML/AI-driven logic (TF-IDF + Logistic Regression,
Gemini AI) provides much more dynamic and personalized user experiences."

### Milestones completed by this point:
[x] Initial UI setup with Streamlit
[x] Dataset generation (dataset_generator.py)
[x] Train baseline Fat Loss ML Model (train_model.py)
[x] Integrate Gemini AI for Fitness Journal / Mood Analysis
[x] Implement Multi-Objective Diet Generation (ai_diet.py)
[x] Implement AI Workout Decision Tree (ai_workout.py)

---

## Phase 4 - Fitness Intelligence System

### Major architectural change:
Created fitness_intelligence.py as the central shared state module.
This became the "nervous system" connecting all modules.

### What was built:
- fitness_intelligence.py: Shared FI state module
  - DEFAULT_FITNESS_INTELLIGENCE: default values for all 9 scores
  - normalize_fitness_intelligence(): clamp, validate, deepcopy, return safe dict
  - get_session_intelligence(): get FI from session state
  - store_session_intelligence(): write FI to session state (sets fitness_intelligence, feedback_issues, fitness_scores)
  - adherence_factor_from_intelligence(): convert FI to [0.35, 1.0] float
  - prediction_behavior_factor(): compute [0.45, 1.12] behavior multiplier from all 9 scores
  - adjusted_diet_targets(): modify calorie/macro targets based on FI adjustments
  - evolve_weekly_intelligence(): simulate week-by-week FI drift for simulation page

- ai_engine.py: AIEngine class
  - update_profile(): store user profile
  - update_feedback(): call analyze_journal(), update feedback_state
  - get_food_recommendations(), get_meal_plan(), get_workout()
  - get_full_recommendations(): single call for all recs
  - get_adaptive_summary(): text summary of AI adaptations shown in sidebar

### Switch from Gemini to NVIDIA NIM:
- Changed AI_analyser_page.py to use OpenAI Python SDK
- Pointed at NVIDIA NIM base URL: https://integrate.api.nvidia.com/v1
- Model: nvidia/llama-3.3-nemotron-super-49b-v1
- Reason: Better structured JSON instruction following, more powerful model
- API key stored in NVIDIA_API_KEY.env, loaded via python-dotenv

### Updated all pages to use FI:
- Prediction page: get_session_intelligence() -> adherence_factor_from_intelligence()
- Diet page: adjusted_diet_targets(tc, mac, fitness_intelligence)
- Workout page: get_ai_workout(..., fitness_intelligence)
- Simulation page: prediction_behavior_factor(), evolve_weekly_intelligence()

### Validation layer hardened:
- validate_fitness_intelligence() in AI_analyser_page.py
- normalize_fitness_intelligence() in fitness_intelligence.py
- Both layers applied in sequence for defense-in-depth
- Handles: malformed JSON, out-of-range values, missing keys, JSON decode errors

---

## Phase 5 - transformation_engine Package Refactor

### Problem being solved:
transformation_prediction.py had grown to ~1000 lines mixing:
- Streamlit imports and UI code
- ML model loading
- Physics/physiology math
- Goal-specific formulas
- Simulation loop
This made it impossible to unit test.

### Solution implemented:
Created transformation_engine/ package with 13 modules:

Module responsibilities:
  model_loader.py:        joblib.load(), global UNIFIED_MODELS singleton
  feature_processor.py:  preprocess_inputs(), make_feature_row() -> pd.DataFrame
  physiology_engine.py:  pure physics: BMR, TDEE, sub-scores (protein_adequacy, etc.)
  goal_logic.py:         pure math per goal: _fat_loss(), _muscle_gain(), _weight_gain(), _recomposition()
                         Returns uniform dict: {scientific_fat_loss, scientific_muscle_gain, scientific_weight_change, ...}
  prediction_engine.py:  orchestrates: physiology -> goal_logic -> ml_model -> blend
                         predict_fat_loss(), predict_muscle_gain(), predict_weight_change(), predict_recomposition()
  behavior_adjuster.py:  applies ai_factor from prediction_behavior_factor()
  simulation_engine.py:  run_simulation(), simulate_weeks() - week-by-week loop
  simulation_page.py:    ONLY file with Streamlit import in the package - full UI page
  context.py:            PredictionContext dataclass - clean input passing
  validator.py:          validates all inputs, raises ValueError with messages
  ai_explainer.py:       generate human-readable explanations for predictions
  utils.py:              RATE_CAPS, FEATURE_ORDER, shared_constants()
  __init__.py:           full public API, backward compatible with all app.py imports

### Backward compatibility:
app.py still imports from transformation_prediction (not from transformation_engine/).
transformation_prediction.py now acts as a thin proxy forwarding to transformation_engine/.
No changes needed in app.py.

### Parity testing:
Created tests/ directory:
  _capture_baseline.py: runs monolith functions, saves outputs to tests/fixtures/baseline_predictions.json
  test_parity_engine.py: runs new package functions, compares to baseline, asserts numerical parity

### Also trained unified models:
train_model.py: train_unified_models() added
Trains 4 goal-specific RF models on 2500 rows each
Saves as transformation_models.pkl (14.8MB)
Features: age, weight, height, bmi, gender, experience, workout_days, adherence, protein_g, calorie_delta, sleep_hrs, steps

---

## Open Items as of 2026-07-12

### Done:
- Core app fully functional across all 8 pages
- Fitness Intelligence system connected to all modules
- transformation_engine/ package created and integrated
- NVIDIA NIM API integration working
- Parity tests written

### Pending:
- prediction.py: empty file, should be deleted
- Parity tests: written but final full run not verified
- generate_weekly_variation() bug: used_history not properly propagated across 7 days
- End-to-end testing across all pages not done
- Hackathon final polish and demo preparation

---

## Key Problem-Solution Log

| Problem | Root Cause | Solution | Date |
|---|---|---|---|
| Gemini inconsistent JSON | LLM not following strict format | Switched to NVIDIA NIM (better instruction following) | Phase 4 |
| LLM returns out-of-range scores | Model uncertainty | validate_fitness_intelligence() + normalize_fitness_intelligence() | Phase 4 |
| test.py calling app.load_model() | Non-existent function | Deleted broken test, rewrote as test_parity_engine.py | Phase 3 |
| 1000-line untestable monolith | Poor separation of concerns | transformation_engine/ package refactor | Phase 5 |
| Redundant rule-based files | Legacy code not cleaned up | Deleted diet_plan.py, feedback.py, workout.py | Phase 3 |
| FI state potentially undefined | Streamlit session re-run | normalize_fitness_intelligence() at startup guarantees safe defaults | Phase 4 |
| Weekly meal repetition | used_history not propagated | BUG - still open, fix in next sprint | Phase 5 |

---

## Architecture Decisions Log

| Decision | Alternative | Reason Chosen |
|---|---|---|
| Streamlit | React/Next.js | Faster for ML apps, less boilerplate, single-codebase |
| NVIDIA NIM API | Gemini, OpenAI, Ollama | Better JSON compliance, OpenAI-compatible, powerful model |
| Cosine similarity food recommender | Collaborative filtering, GPT | No user-to-user data; content-based is natural; deterministic |
| Decision Tree workout classifier | Rule-based if/else, LLM | Generalizes to unseen combos; explainable; no API calls |
| Multi-objective scoring for meals | LLM meal generation | No hallucinated macros; precise control; fast |
| Synthetic ML training data | Real clinical data | No privacy concerns; reproducible; no data collection needed |
| All state in session_state | SQLite, Firebase | Hackathon scope; simplest working solution |
| Indian food focus | Universal/generic | Cultural relevance for developer and target audience |
| 7700 kcal/kg fat loss rule | Complex thermodynamic model | Industry standard; accurate enough for estimates |
| Mifflin-St Jeor BMR formula | Harris-Benedict, Katch-McArdle | Most validated formula for general population |
