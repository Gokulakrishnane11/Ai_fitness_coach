# 🔥 AI Fitness Coach Platform

A production-grade, full-stack AI health and fitness coaching application that pairs **metabolic transformation modeling**, **adaptive fitness journaling & sentiment analysis**, and **computer vision pose analysis** into a centralized, closed-loop coaching platform.

The system is built on a decoupled architecture: a **Next.js 14 App Router** frontend paired with a high-performance **FastAPI** backend and **Supabase (PostgreSQL + Auth)**.

---

## 🏗️ System Architecture

```
                                ┌──────────────────────────────────────────────┐
                                │          Next.js 14 Frontend Client          │
                                │   (React 18, TypeScript, Tailwind, Recharts) │
                                └──────────────────────┬───────────────────────┘
                                                       │
                                     HTTP / REST API   │   JWT Bearer Auth
                                     (Port 3000)       ▼   (Supabase SSR)
                                ┌──────────────────────────────────────────────┐
                                │             FastAPI REST Backend             │
                                │       (Python 3.13, Pydantic V2, Uvicorn)    │
                                └──────┬───────────────┬───────────────┬───────┘
                                       │               │               │
            ┌──────────────────────────┘               │               └──────────────────────────┐
            ▼                                          ▼                                          ▼
┌──────────────────────────────┐   ┌───────────────────────────────┐   ┌──────────────────────────────┐
│  Supabase PostgreSQL & Auth  │   │   Central Adaptation Engine   │   │     AI & Vision Services     │
│  • Profiles & Biometrics     │   │   • Readiness Factor (0.45-1.12)  │   │   • MediaPipe Pose Landmarker│
│  • Active Meal Plans         │   │   • Dynamic Calorie Deltas        │   │   • OpenCV EXIF Sanitization │
│  • Active Workout Routines   │   │   • Deload & Volume Adjustments   │   │   • Structured Sentiment NLP │
│  • Daily Telemetry Logs      │   │   • Multi-Score Behavioral Model  │   │   • Groq / NVIDIA NIM LLM    │
│  • Adaptation Audit History  │   │   • Closed-Loop Recalibration     │   │     (Configured / Partial)   │
└──────────────────────────────┘   └───────────────────────────────┘   └──────────────────────────────┘
```

The application functions as a **closed-loop feedback system**:
1. **Baseline Plan Generation**: Based on user biometrics and goals, the engine determines scientific BMR, TDEE, macro splits, and structured workout splits.
2. **Daily Tracking & Journaling**: Users track daily metrics (weight, steps, sleep, nutrition adherence) and submit free-text fitness journal entries.
3. **Sentiment & Stress Extraction**: The coaching module analyzes qualitative journal input to detect sentiment tags, recovery deficits, fatigue levels, and soreness flags.
4. **Centralized Adaptation Engine**: Evaluates adherence, recovery, stress, sleep, injury risk, and plateau indicators to dynamically compute calorie deltas and training volume modifications to prevent burnout and plateaus.

---

## 🚀 Core Features & Implementation Status

| Component | Implementation Status | Technical Details |
|---|---|---|
| **Personalized Nutrition Planning** | **Implemented** | Mifflin-St Jeor BMR, TDEE activity multipliers, goal-specific calorie deltas, deterministic 4-meal daily generation matching macro targets |
| **Workout Planning Engine** | **Implemented** | Clinical deterministic rule matrix (Full Body, Upper/Lower, PPL, Recomp) calibrated by goal, experience, and weekly frequency |
| **Centralized Adaptation Engine** | **Implemented** | Evaluates adherence, recovery, stress, sleep, injury risk, and plateau probability; computes readiness factor (0.45–1.12), diet adjustments, and workout adjustments |
| **Progress & Telemetry Tracking** | **Implemented** | Logs daily weight, calories, macros, water, workout completion, perceived recovery, sleep quality, stress, and muscle soreness |
| **Transformation Simulation** | **Implemented** | Multi-week weight trajectory projection based on human energy-balance dynamics and adherence percentages |
| **Computer Vision Body Analysis** | **Implemented** | EXIF stripping, orientation normalization, private storage upload, and MediaPipe Pose landmark extraction (shoulder tilt, hip tilt, symmetry, proportions) |
| **Structured Fitness Journal NLP** | **Implemented** | Keyword/heuristic sentiment extraction (`fatigued`, `motivated`, `consistent`) outputting structured summaries, actionable tips, and quotes saved to Supabase |
| **Direct Cloud LLM Inference (Groq / NVIDIA NIM)** | **Partial / Configured** | Configured via environment variables (`GROQ_API_KEY`, `NVIDIA_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`) in `app/core/config.py`; direct API calls roadmap-staged |

---

## 🔬 Feature Details

### 1. 🍱 Personalized Nutrition Planning
- **Physics-Based Energy Equations**: Calculates Basal Metabolic Rate (BMR) via the Mifflin-St Jeor formula and Total Daily Energy Expenditure (TDEE) from activity multipliers (`sedentary`, `lightly_active`, `moderately_active`, `very_active`, `extra_active`).
- **Goal-Calibrated Caloric Deltas**: Tailors deficits and surpluses for `fat_loss`, `muscle_gain`, `weight_gain`, and `recomposition`.
- **Macronutrient Optimization**: Gram-precise allocations for protein, carbohydrate, and dietary fat based on lean mass targets and dietary preference (`anything`, `vegetarian`, `vegan`, `keto`, `paleo`).
- **Deterministic Meal Plans**: Generates structured daily meal schedules matching macro targets.

### 2. 💪 Adaptive Workout Planning
- **Deterministic Rule Matrix**: Replaced legacy decision-tree prototyping with transparent, clinical rule matrices in `app/engine/workout_rules.py`. Matches splits (Full Body, Upper/Lower, Push/Pull/Legs) based on goal, training days, and experience.
- **Dynamic Program Adjustments**: Integrates with `WorkoutAdjustment` to scale intensity (`reduce`, `maintain`, `increase`), volume (`low`, `medium`, `high`), inject recovery days, recommend cardio minutes, or trigger deload weeks.

### 3. 🧠 AI Coaching & Fitness Journal
- **Qualitative Journal Processing**: Endpoint accepts daily reflections and parses emotional state, fatigue indicators, and motivation cues.
- **Structured Feedback Output**: Returns structured feedback schemas containing sentiment tags, summaries, 2–3 actionable fitness/nutrition tips, and motivational encouragement.
- **Persistence**: Links coaching feedback and entries to user records via `JournalRepository`.

### 4. 🔄 Centralized Adaptation Engine
- **Multi-Signal Behavioral Scoring**: Pure scoring layer in `app/engine/adaptation.py` evaluating:
  - `adherence_score` (0–100)
  - `recovery_score` (0–100)
  - `stress_score` (0–100)
  - `sleep_quality` (0–100)
  - `plateau_probability` (0–100)
  - `injury_risk` (0–100)
  - `readiness_factor` (0.45 to 1.12 multiplier)
- **Automatic Output Adjustments**:
  - `DietAdjustment`: `calorie_delta` (-300 to +300 kcal), `protein_delta_g`, `carb_delta_g`, `fat_delta_g`.
  - `WorkoutAdjustment`: intensity modifications, volume scaling, recovery days, deload recommendations.
- **Plan Commitment**: `POST /api/v1/planning/apply-adaptation` idempotently commits calculated adjustments to active meal and workout plans while recording audit snapshots.

### 5. 📈 Progress Tracking & Telemetry
- **Daily Telemetry Logs**: Captures body weight, calories, macronutrients, water intake, workout completion status, and energy ratings.
- **Wellness Telemetry**: Captures perceived recovery (0–100), sleep quality (0–100), stress level (0–100), and muscle soreness (0–100) mapping directly into adaptation engine signals.

### 6. 🔮 Transformation Simulation
- **Multi-Week Projections**: Simulates physical transformations across 4 to 52 weeks via `app/engine/transformation.py`.
- **Energy-Balance Dynamics**: Combines Mifflin-St Jeor baseline expenditure, daily caloric delta, and user adherence percentages into realistic weekly milestone series.

### 7. 📸 AI Body Analysis & Vision
- **MediaPipe Pose Landmarker**: Runs 33-point landmark detection using CPU-friendly MediaPipe vision tasks.
- **Pose Geometry Metrics**: Calculates shoulder tilt (degrees), hip tilt (degrees), bilateral symmetry score (0.0–1.0), torso-to-leg ratio, and shoulder-to-hip ratio.
- **Privacy & Sanitization**: Image upload validates file signatures (magic bytes for JPEG, PNG, WebP), enforces size limits (<= 10 MB), strips EXIF/GPS metadata via Pillow, and stores clean files in private Supabase Storage.
- **Observational Only**: Measurements are explicitly flagged as observational pose estimates and do not directly alter clinical metabolic formulas.

---

## 🗺️ Roadmap & Planned Enhancements

- **Direct Cloud LLM Provider Handshake**: Finalize direct streaming chat and deep reasoning through Groq (`llama-3.3-70b-versatile`) and NVIDIA NIM API endpoints using the configured credentials.
- **Computer Vision Trend Comparison**: Longitudinal side-by-side posture progression comparing landmarks across multiple dates.
- **Wearable Device Telemetry Ingestion**: Automated Apple Health and Google Health Connect sync for step counts, resting heart rate, and sleep staging.

---

## 🌐 Frontend Routes (`apps/web`)

| Route | Description |
|---|---|
| `/` | Marketing landing page detailing platform features, architecture, and technology |
| `/login` | Supabase email/password authentication sign-in |
| `/signup` | New user account registration |
| `/onboarding` | Multi-step biometric profile setup (age, gender, height, weight, goal, activity) |
| `/dashboard` | Central hub: daily overview, nutrition cards, workout plan, active adaptations |
| `/coaching` | Daily fitness journal input, sentiment extraction, issue tags, and action nudges |
| `/simulation` | Interactive transformation projection simulator with parameter sliders |
| `/progress` | Longitudinal check-in logs, weight charts, and adherence metrics |
| `/body-analysis` | Body posture analysis photo upload and MediaPipe landmark viewer |

---

## 📡 REST API Reference (`apps/api`)

Base URL: `http://127.0.0.1:8000/api/v1`
Interactive OpenAPI Documentation: `http://127.0.0.1:8000/docs`

| Prefix / Endpoint | Method | Tag | Description |
|---|---|---|---|
| `/health` | `GET` | Health | Service liveness probe and app version |
| `/api/v1/profile` | `GET` | Profile | Retrieve authenticated user biometric profile |
| `/api/v1/profile` | `POST` | Profile | Create or update user biometric profile |
| `/api/v1/planning/meal-plan` | `POST` | Planning | Generate deterministic meal plan matching macro targets |
| `/api/v1/planning/active-meal-plan` | `GET` | Planning | Retrieve currently active meal plan |
| `/api/v1/planning/workout-plan` | `POST` | Planning | Generate deterministic structured workout routine |
| `/api/v1/planning/active-workout-plan` | `GET` | Planning | Retrieve currently active workout plan |
| `/api/v1/planning/apply-adaptation` | `POST` | Planning | Commit current adaptation decisions to active plans |
| `/api/v1/simulation/predict` | `POST` | Simulation | Run multi-week predictive physical transformation simulation |
| `/api/v1/progress/logs` | `GET` | Progress | Retrieve user daily tracking logs |
| `/api/v1/progress/logs` | `POST` | Progress | Submit or update a daily tracking log |
| `/api/v1/coaching/journal` | `POST` | Coaching | Submit daily journal for structured coaching feedback |
| `/api/v1/adaptation` | `GET` | Adaptation | Compute and retrieve personalized adaptation decision |
| `/api/v1/adaptation/current` | `GET` | Adaptation | Semantic route to retrieve current adaptation decision |
| `/api/v1/adaptation/history` | `GET` | Adaptation | Retrieve historical adaptation decision audit trail |
| `/api/v1/body-analysis/photos` | `POST` | Body Analysis | Upload progress photo with EXIF stripping & pose analysis |
| `/api/v1/body-analysis/photos` | `GET` | Body Analysis | List authenticated user progress photos |
| `/api/v1/body-analysis/photos/{photo_id}` | `GET` | Body Analysis | Retrieve single progress photo and analysis result |
| `/api/v1/body-analysis/photos/{photo_id}` | `DELETE` | Body Analysis | Soft-delete photo record and remove from storage |

---

## 📁 Repository Structure

```
.
├── apps/
│   ├── api/                          # FastAPI REST API Backend
│   │   ├── app/
│   │   │   ├── core/                 # Config (settings), security, auth dependencies
│   │   │   ├── db/                   # Supabase client & repository helpers
│   │   │   ├── engine/               # Adaptation, BMR/TDEE, CV, workout & nutrition engines
│   │   │   ├── modules/              # Domain routers (profile, planning, simulation, coaching, etc.)
│   │   │   └── main.py               # FastAPI entry point & CORS configuration
│   │   ├── tests/                    # Backend test suite (829 pytest tests)
│   │   └── requirements.txt          # Backend dependencies
│   │
│   └── web/                          # Next.js 14 App Router Frontend
│       ├── src/
│       │   ├── app/                  # Application routes (dashboard, coaching, simulation, etc.)
│       │   ├── context/              # React context providers (AuthContext)
│       │   └── lib/                  # Supabase clients & API fetch utilities
│       ├── package.json              # Next.js, React, TailwindCSS, Recharts dependencies
│       ├── postcss.config.js         # PostCSS configuration
│       ├── tailwind.config.js        # TailwindCSS design system configuration
│       └── tsconfig.json             # TypeScript compiler configuration
│
├── supabase/
│   └── migrations/                   # PostgreSQL schema migrations (V1 through V4)
│
├── .env                              # Backend environment configuration (git-ignored)
└── README.md                         # Project documentation
```

---

## 🛠️ Windows Development Setup & Running

### Prerequisites
- **Python**: Version 3.10 to 3.13 installed (ensure `python` is available in PowerShell).
- **Node.js**: Version 18.0.0 or higher (v22 recommended).
- **npm**: Version 9.0.0 or higher.
- **Git**: Installed and configured.

---

### Step 1: Environment Variables Setup

#### Backend Environment (`.env` in project root)
Create a `.env` file in the repository root directory:
```env
# Supabase Database & Auth
SUPABASE_URL="https://<your-project-id>.supabase.co"
SUPABASE_ANON_KEY="<your-supabase-anon-key>"
SUPABASE_JWT_SECRET="<your-supabase-jwt-secret-min-32-chars>"

# LLM Coaching Configuration (Groq or NVIDIA NIM)
GROQ_API_KEY="gsk_..."
NVIDIA_API_KEY="nvapi-..."
LLM_BASE_URL="https://api.groq.com/openai/v1"
LLM_MODEL_NAME="llama-3.3-70b-versatile"

# Optional testing flag
TESTING="false"
```

#### Frontend Environment (`apps/web/.env.local`)
Create `apps/web/.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-id>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

> [!CAUTION]
> **Security Warning**: NEVER commit `.env`, `.env.local`, or any file containing API keys, database credentials, or JWT secrets to Git. Always ensure `.env` and `.env.local` are listed in your `.gitignore`.

---

### Step 2: Python Virtual Environment & Backend Setup

From the project root in PowerShell:
```powershell
# Create virtual environment if not already present
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r apps\api\requirements.txt
```

---

### Step 3: Run the Backend Server

With the virtual environment activated, navigate to `apps/api` and start Uvicorn:
```powershell
cd apps\api
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API**: `http://127.0.0.1:8000`
- **Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/health`

---

### Step 4: Frontend Setup & Run

Open a separate PowerShell terminal:
```powershell
cd apps\web

# Install frontend dependencies
npm install

# Start Next.js development server
npm run dev
```
- **Frontend Application**: `http://localhost:3000`

---

## 🧪 Testing & Quality Assurance

### Run Backend Pytest Suite (829 Tests)
From the project root:
```powershell
.\.venv\Scripts\pytest.exe apps\api\tests
```
Or directly from `apps/api`:
```powershell
cd apps\api
..\..\.venv\Scripts\pytest.exe
```
This runs the full test suite verifying:
- Authentication & JWT token verification
- Profile creation and validation
- BMR, TDEE, and macronutrient calculations
- Multi-week predictive simulation logic
- Coaching journal sentiment parsing and fallback handling
- Centralized adaptation engine input preparation, scoring, and repository operations
- MediaPipe pose landmarks and OpenCV photo upload validation

### Run Frontend Build & Typecheck
From `apps/web`:
```powershell
cd apps\web
npm run build
```
Validates TypeScript compilation, route bundling, and Tailwind CSS styles for all application routes.

---

## 🔒 Security & Best Practices

- **Zero Secrets in Source Control**: Keep `.env` and `.env.local` strictly untracked.
- **Row-Level Security (RLS)**: Database tables in Supabase enforce RLS policies tied to user UUIDs authenticated via Supabase Auth.
- **EXIF Sanitization**: User-uploaded progress photos are processed through Pillow and OpenCV to strip geolocation, camera metadata, and device identifiers prior to storage.
- **CORS Configuration**: The FastAPI backend configures CORS explicitly to support secure communication with the frontend client.

---

## ⚖️ Disclaimer

*The nutritional formulas, workout templates, and physiological adaptation suggestions produced by this application are mathematical estimations and AI-assisted insights intended solely for educational and personal wellness purposes. Always consult a certified healthcare professional, registered dietitian, or physician before initiating any vigorous exercise program or extreme dietary modification.*
