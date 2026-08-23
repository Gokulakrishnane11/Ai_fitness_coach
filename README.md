# 🔥 Smart Body Transformation AI Coach
### PPG College Hackathon — Problem Statement: Topic 1
> AI-Driven Sentiment Analysis & Actionable Insight Generation

---

## 📌 Project Overview

**Smart Body Transformation AI Coach** is a comprehensive, AI-powered web application that combines machine learning-based physical transformation prediction with an intelligent, feedback-adaptive coaching system. It dynamically personalizes diet, workouts, and food recommendations based on real-time sentiment analysis and user progress.

The project directly addresses **Topic 1 — AI-Driven Sentiment Analysis & Actionable Insight Generation from Survey Responses**, applied in a health and fitness coaching context. Instead of analyzing generic surveys, the system analyzes users' personal fitness journal entries to detect mood, identify issues (e.g., fatigue, plateau, stress), and generate targeted action nudges — bridging the gap between how a user *feels* and what they should *do next*. The coaching engine then physically adapts the workout and diet plans in real-time based on this emotional and physiological feedback.

---

## 🧠 How Topic 1 Is Implemented

| Topic 1 Requirement | Our Implementation |
|---|---|
| Analyze qualitative responses | User fitness journal entries (free-text) |
| Classify sentiment | Google Gemini AI classifies each journal entry (positive/neutral/negative) |
| Identify key issues and urgency | Detects tags: fatigue, plateau, cravings, stress, injury risk, etc. |
| Convert insights into action nudges | 3 personalized, specific recommendations per entry |
| Adaptive AI Engine | Feedback dynamically alters Workout Plans (e.g., reducing intensity if fatigued) |
| Longitudinal trend analysis | Mood trend chart across all journal entries |

---

## 🚀 Key Features

### 1. 📊 Transformation Prediction (ML Core)
- Predicts weekly and monthly changes for **Fat Loss**, **Muscle Gain**, **Weight Gain**, and **Body Recomposition**.
- Inputs: age, gender, height, weight, workout days, activity level, etc.
- Calculates BMR, TDEE, and daily macro/micronutrient targets.
- Powered by a custom ML model trained on 1,200 physiologically realistic profiles.

### 2. 🔮 Predictive Simulation
- Simulates how varying your calorie deficit/surplus, protein intake, and workout frequency will impact your goals over time.

### 3. 🍱 AI Food & Diet Recommendations
- **AI Food Recommender:** Uses content-based filtering (cosine similarity) to suggest the best foods based on your specific goal and detected micronutrient deficits.
- **AI Diet Plan Generator:** Uses multi-objective scoring (macro fit, calorie proximity, variety) to dynamically assemble daily and weekly meal plans.

### 4. 💪 Adaptive AI Workout Guide
- Uses a **Decision Tree Classifier** to select the optimal workout split (10+ templates) based on goal and experience level.
- **Feedback-Adaptive:** Automatically scales down intensity, adjusts volume, or suggests mobility work if the AI Journal detects high stress, fatigue, or injury risk.

### 5. 🧠 Fitness Journal & Mood Analyzer (Topic 1 Core)
- Users write free-text journal entries about their fitness day.
- Gemini AI deeply analyzes the text, identifies struggles, and generates targeted action nudges.
- Acts as the sensory input for the central **AI Engine**, driving the adaptive behavior of the entire app.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend & UI | Python, Streamlit (Custom CSS) |
| Machine Learning | Scikit-learn (Random Forest, Decision Trees, Logistic Regression) |
| Sentiment & NLP | Google Gemini 2.5 Flash API, TF-IDF |
| Data Processing | Pandas, NumPy |
| Model Persistence | Joblib |
| Visualization | Streamlit Charts, Matplotlib, Seaborn |

---

## 📁 Project Structure

```
smart-body-ai-coach/
│
├── app.py                  # Main Streamlit application
├── ai_engine.py            # Central state and adaptation engine
├── ai_diet.py              # Multi-objective meal plan generator
├── ai_food.py              # Cosine-similarity food recommender
├── ai_workout.py           # Decision Tree workout classifier
├── ai_feedback.py          # TF-IDF fallback sentiment analyzer
├── sentiment_page.py       # Topic 1 — Gemini AI Fitness Journal
├── transformation_prediction.py # Unified prediction and simulation engine
├── nutrition.py            # Core BMR/TDEE/Macro calculators
├── train_model.py          # Script to train fat_loss_model.pkl
├── dataset_generator.py    # Generates synthetic training dataset
├── PROJECT_JOURNAL.md      # Development log
└── fat_loss_model.pkl      # Trained ML model
```

---

## ⚙️ Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/your-username/smart-body-ai-coach.git
cd smart-body-ai-coach
```

### 2. Install dependencies
```bash
pip install streamlit scikit-learn pandas numpy joblib google-generativeai matplotlib seaborn
```

### 3. Add your Gemini API key
Open `sentiment_page.py` and replace line 18:
```python
GEMINI_API_KEY = "your_gemini_api_key_here"
```
*(Get a free key at: https://aistudio.google.com/apikey)*

### 4. Run the app
```bash
streamlit run app.py
```

---

## 🔗 The Adaptive Loop (How it all connects)

Unlike standard fitness trackers, this app features a **closed-loop feedback system**:
1. The **ML Models** set the baseline path (macros, calories, expected weight change).
2. The **AI Workout & Diet** generators create the initial program.
3. The user logs their experience in the **Fitness Journal**.
4. The **Sentiment AI (Gemini)** analyzes the entry, detecting hidden issues (e.g., *Fatigue* or *Overtraining*).
5. The **AI Engine** receives these issues and *dynamically modifies* the active Workout Guide (e.g., dropping volume by 20% or switching to an active recovery template) to prevent burnout.

---

## 👨‍💻 Built By

**Gokul** — B.Tech AI & Data Science, 2nd Year  
Self-taught frontend developer | Python & ML enthusiast  
Tamil Nadu, India

---

## 📝 Notes for Judges

- The Gemini API free tier is used (1,500 requests/day).
- A robust Scikit-learn TF-IDF model (`ai_feedback.py`) is included as a conceptual fallback for NLP.
- The physical ML model was trained on 1,200 synthetic, physiologically accurate data points (`dataset_generator.py`).
- The entire application runs smoothly locally with in-memory state management.

---

*Built with Python, Scikit-learn & Streamlit · Predictions are estimates — always consult a healthcare professional.*
