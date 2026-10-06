/**
 * Typed API Client for FastAPI Backend.
 * Handles profile management, meal/workout planning, predictive simulations,
 * daily progress logs, and AI coaching feedback using real Supabase Bearer JWTs.
 */

import { createClient } from "./supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export interface UserProfile {
  id?: string;
  first_name: string;
  gender: "male" | "female" | "other";
  age: number;
  height_cm: number;
  weight_kg: number;
  target_weight_kg: number;
  body_fat_pct?: number;
  activity_level: "sedentary" | "lightly_active" | "moderately_active" | "very_active" | "extra_active";
  goal_type: "fat_loss" | "muscle_gain" | "weight_gain" | "recomposition";
  dietary_preference: "anything" | "vegetarian" | "vegan" | "keto" | "paleo";
  workout_days_per_week: number;
  experience_level: "beginner" | "intermediate" | "advanced";
  target_metrics?: {
    bmr: number;
    tdee: number;
    target_calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    fiber_g: number;
    water_liters: number;
  };
}

export interface SimulationRequest {
  start_weight_kg: number;
  target_weight_kg: number;
  height_cm: number;
  age: number;
  gender: string;
  activity_level: string;
  daily_caloric_deficit_surplus: number;
  adherence_pct: number;
  duration_weeks: number;
  body_fat_pct?: number;
}

export interface WeeklySeriesPoint {
  week: number;
  weight_kg: number;
  fat_mass_kg: number;
  lean_mass_kg: number;
  body_fat_pct: number;
  bmr: number;
  tdee: number;
}

export interface MealPlanRequest {
  target_calories: number;
  target_protein_g: number;
  target_carbs_g: number;
  target_fat_g: number;
  dietary_preference: string;
  apply_adaptation?: boolean;
}

export interface MealPlanItem {
  food: string;
  portion_g: number;
}

export interface MealPlanMeal {
  meal_name: string;
  target_calories: number;
  actual_calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  items: MealPlanItem[];
}

export interface MealPlanResponse {
  id?: string;
  user_id?: string;
  is_active?: boolean;
  created_at?: string;
  title: string;
  target_calories: number;
  target_protein_g?: number;
  target_carbs_g?: number;
  target_fat_g?: number;
  achieved_calories: number;
  achieved_protein_g: number;
  achieved_carbs_g: number;
  achieved_fat_g: number;
  meals: MealPlanMeal[];
  plan_data?: any;
}

export interface WorkoutPlanRequest {
  goal_type: string;
  workout_days_per_week: number;
  experience_level: string;
  apply_adaptation?: boolean;
}

export interface ExerciseItem {
  name: string;
  sets: number;
  reps: string;
  rest_sec: number;
}

export interface WorkoutDayRoutine {
  day: string;
  focus: string;
  exercises: ExerciseItem[];
}

export interface WorkoutPlanResponse {
  id?: string;
  user_id?: string;
  is_active?: boolean;
  created_at?: string;
  title: string;
  split_type: string;
  days_per_week: number;
  experience_level: string;
  description: string;
  routine: WorkoutDayRoutine[];
  intensity_target?: string;
  deload_active?: boolean;
  cardio_minutes?: number;
  recovery_days?: number;
  routine_data?: any;
}

export interface DailyLog {
  id: string;
  user_id: string;
  log_date: string;
  weight_kg: number | null;
  calories_consumed: number | null;
  protein_consumed_g: number | null;
  carbs_consumed_g: number | null;
  fat_consumed_g: number | null;
  water_liters: number | null;
  workout_completed: boolean;
  energy_rating: number | null;
  notes: string | null;
  recovery_score?: number | null;
  sleep_quality?: number | null;
  stress_level?: number | null;
  muscle_soreness?: number | null;
  created_at: string;
}

export interface DailyLogCreateRequest {
  log_date: string;
  weight_kg?: number | null;
  calories_consumed?: number | null;
  protein_consumed_g?: number | null;
  carbs_consumed_g?: number | null;
  fat_consumed_g?: number | null;
  water_liters?: number | null;
  workout_completed?: boolean;
  energy_rating?: number | null;
  notes?: string | null;
  recovery_score?: number | null;
  sleep_quality?: number | null;
  stress_level?: number | null;
  muscle_soreness?: number | null;
}

export interface DailyLogsResponse {
  logs: DailyLog[];
  count: number;
}

export interface DietAdjustment {
  calorie_delta: number;
  protein_delta_g: number;
  carb_delta_g: number;
  fat_delta_g: number;
}

export interface WorkoutAdjustment {
  intensity: "reduce" | "maintain" | "increase";
  volume: "low" | "medium" | "high";
  recovery_days: number;
  cardio_minutes: number;
  deload_recommended: boolean;
}

export interface AdaptationReason {
  signal: string;
  value?: number | string | boolean | null;
  effect: "positive" | "neutral" | "negative";
  message: string;
}

export interface AdaptationFeedbackOutcome {
  trajectory: "improving" | "stable" | "declining" | "insufficient_data";
  recovery_delta?: number | null;
  stress_delta?: number | null;
  soreness_delta?: number | null;
  adherence_delta?: number | null;
  previous_history_id?: string | null;
  days_since_previous?: number | null;
}

export interface AdaptationDecision {
  adherence_score: number;
  recovery_score: number;
  stress_score: number;
  sleep_quality: number;
  plateau_probability: number;
  injury_risk: number;
  readiness_factor: number;
  plateau_detected: boolean;
  high_fatigue_flag: boolean;
  diet_adjustment: DietAdjustment;
  workout_adjustment: WorkoutAdjustment;
  actionable_recommendations: string[];
  coaching_summary: string;
  objective_data_available: boolean;
  reasons?: AdaptationReason[];
  feedback_outcome?: AdaptationFeedbackOutcome | null;
}

export interface AdaptationHistoryRecord {
  id: string;
  user_id: string;
  created_at: string;
  readiness_factor: number;
  high_fatigue_flag: boolean;
  plateau_detected: boolean;
  adherence_score: number;
  recovery_score: number;
  stress_score: number;
  sleep_quality: number;
  injury_risk: number;
  plateau_probability: number;
  diet_adjustment: DietAdjustment;
  workout_adjustment: WorkoutAdjustment;
  actionable_recommendations: string[];
  coaching_summary: string;
  objective_data_available: boolean;
  active_meal_plan_id?: string | null;
  active_workout_plan_id?: string | null;
  input_snapshot: Record<string, any>;
  reasons?: AdaptationReason[];
  feedback_outcome?: AdaptationFeedbackOutcome | null;
}

export interface AdaptationHistoryResponse {
  history: AdaptationHistoryRecord[];
  count: number;
}

export class AdaptationApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "AdaptationApiError";
    this.status = status;
    this.detail = detail;
    Object.setPrototypeOf(this, AdaptationApiError.prototype);
  }
}

/**
 * Helper to obtain the real authenticated Supabase access token.
 * Throws an authentication error if no active session exists (never sends fake/test tokens).
 */
export async function getAuthToken(overrideToken?: string): Promise<string> {
  // If an explicit valid non-mock token is passed, use it directly
  if (overrideToken && !overrideToken.startsWith("test_token_")) {
    return overrideToken;
  }

  const supabase = createClient();
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error || !session?.access_token) {
    throw new Error("Authentication required. No active Supabase session found.");
  }

  return session.access_token;
}

export async function fetchProfile(token?: string): Promise<UserProfile> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/profile`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  if (!res.ok) throw new Error("Failed to fetch user profile");
  return res.json();
}

export async function saveProfile(
  profileOrToken: UserProfile | string,
  maybeProfile?: UserProfile
): Promise<UserProfile> {
  const profile = typeof profileOrToken === "string" ? maybeProfile! : profileOrToken;
  const explicitToken = typeof profileOrToken === "string" ? profileOrToken : undefined;
  const authToken = await getAuthToken(explicitToken);

  const res = await fetch(`${API_BASE_URL}/profile`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error("Failed to save user profile");
  return res.json();
}

export async function runSimulation(
  reqOrToken: SimulationRequest | string,
  maybeReq?: SimulationRequest
) {
  const req = typeof reqOrToken === "string" ? maybeReq! : reqOrToken;
  const explicitToken = typeof reqOrToken === "string" ? reqOrToken : undefined;
  const authToken = await getAuthToken(explicitToken);

  const res = await fetch(`${API_BASE_URL}/simulation/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to run predictive simulation");
  return res.json();
}

export async function submitJournal(textOrToken: string, maybeText?: string) {
  const text = maybeText !== undefined ? maybeText : textOrToken;
  const explicitToken = maybeText !== undefined ? textOrToken : undefined;
  const authToken = await getAuthToken(explicitToken);

  const res = await fetch(`${API_BASE_URL}/coaching/journal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ entry_text: text }),
  });
  if (!res.ok) throw new Error("Failed to submit journal entry");
  return res.json();
}

export async function generateMealPlan(
  req: MealPlanRequest,
  token?: string
): Promise<MealPlanResponse>;
export async function generateMealPlan(
  token: string,
  req: MealPlanRequest
): Promise<MealPlanResponse>;
export async function generateMealPlan(
  reqOrToken: MealPlanRequest | string,
  maybeReqOrToken?: MealPlanRequest | string
): Promise<MealPlanResponse> {
  const req = (typeof reqOrToken === "string" ? maybeReqOrToken : reqOrToken) as MealPlanRequest;
  const explicitToken = typeof reqOrToken === "string" ? reqOrToken : (maybeReqOrToken as string | undefined);
  const authToken = await getAuthToken(explicitToken);

  const res = await fetch(`${API_BASE_URL}/planning/meal-plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to generate meal plan");
  const data = await res.json();
  const normalized = normalizeMealPlan(data);
  return normalized || data;
}

export async function generateWorkoutPlan(
  req: WorkoutPlanRequest,
  token?: string
): Promise<WorkoutPlanResponse>;
export async function generateWorkoutPlan(
  token: string,
  req: WorkoutPlanRequest
): Promise<WorkoutPlanResponse>;
export async function generateWorkoutPlan(
  reqOrToken: WorkoutPlanRequest | string,
  maybeReqOrToken?: WorkoutPlanRequest | string
): Promise<WorkoutPlanResponse> {
  const req = (typeof reqOrToken === "string" ? maybeReqOrToken : reqOrToken) as WorkoutPlanRequest;
  const explicitToken = typeof reqOrToken === "string" ? reqOrToken : (maybeReqOrToken as string | undefined);
  const authToken = await getAuthToken(explicitToken);

  const res = await fetch(`${API_BASE_URL}/planning/workout-plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to generate workout plan");
  const data = await res.json();
  const normalized = normalizeWorkoutPlan(data);
  return normalized || data;
}

export async function submitDailyLog(
  req: DailyLogCreateRequest,
  token?: string
): Promise<DailyLog>;
export async function submitDailyLog(
  token: string,
  req: DailyLogCreateRequest
): Promise<DailyLog>;
export async function submitDailyLog(
  reqOrToken: DailyLogCreateRequest | string,
  maybeReqOrToken?: DailyLogCreateRequest | string
): Promise<DailyLog> {
  const req = (typeof reqOrToken === "string" ? maybeReqOrToken : reqOrToken) as DailyLogCreateRequest;
  const explicitToken = typeof reqOrToken === "string" ? reqOrToken : (maybeReqOrToken as string | undefined);
  const authToken = await getAuthToken(explicitToken);

  const res = await fetch(`${API_BASE_URL}/progress/logs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to submit daily log");
  return res.json();
}

export async function fetchDailyLogs(token?: string): Promise<DailyLogsResponse> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/progress/logs`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  if (!res.ok) throw new Error("Failed to fetch daily logs");
  return res.json();
}

/**
 * Fetches the computed AI adaptation decision for the authenticated user.
 * Reuses the existing authentication token handling and API base URL conventions.
 *
 * Supports both /adaptation (default, backward-compatible) and explicit /adaptation/current.
 *
 * Status code handling:
 * - 401: Unauthenticated request (user not logged in or invalid token)
 * - 404: Profile not found (user has not completed onboarding)
 * - 422: Incomplete profile or missing target metrics required for adaptation
 * - Other non-success HTTP codes: Meaningful error message
 */
export async function fetchAdaptationDecision(
  tokenOrOptions?: string | { useCurrentEndpoint?: boolean; token?: string }
): Promise<AdaptationDecision> {
  const options =
    typeof tokenOrOptions === "object" && tokenOrOptions !== null
      ? tokenOrOptions
      : { token: typeof tokenOrOptions === "string" ? tokenOrOptions : undefined };

  const authToken = await getAuthToken(options.token);
  const endpoint = options.useCurrentEndpoint ? "/adaptation/current" : "/adaptation";
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response body
    }

    if (res.status === 401) {
      throw new AdaptationApiError(
        401,
        errorDetail || "Authentication required. Please log in to view adaptation insights.",
        errorDetail
      );
    }
    if (res.status === 404) {
      throw new AdaptationApiError(
        404,
        errorDetail || "User profile not found. Please complete profile setup.",
        errorDetail
      );
    }
    if (res.status === 422) {
      throw new AdaptationApiError(
        422,
        errorDetail || "Incomplete profile. Required biometric fields are missing for adaptation.",
        errorDetail
      );
    }
    throw new AdaptationApiError(
      res.status,
      errorDetail || `Failed to fetch adaptation decision (HTTP ${res.status})`,
      errorDetail
    );
  }

  return res.json();
}

/**
 * Semantic helper to fetch the current adaptation decision via /adaptation/current.
 */
export async function fetchCurrentAdaptation(token?: string): Promise<AdaptationDecision> {
  return fetchAdaptationDecision({ useCurrentEndpoint: true, token });
}

/**
 * Fetches the historical adaptation decisions and audit trail for the authenticated user.
 */
export async function fetchAdaptationHistory(
  limit: number = 30,
  token?: string
): Promise<AdaptationHistoryResponse> {
  const authToken = await getAuthToken(token);
  const clampedLimit = Math.max(1, Math.min(100, limit));
  const res = await fetch(`${API_BASE_URL}/adaptation/history?limit=${clampedLimit}`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response body
    }
    throw new AdaptationApiError(
      res.status,
      errorDetail || `Failed to fetch adaptation history (HTTP ${res.status})`,
      errorDetail
    );
  }

  return res.json();
}

/**
 * Normalizes any meal plan response (raw DB row, wrapped plan_data, stringified JSON, or flat schema)
 * into a guaranteed valid MealPlanResponse with safe arrays and numbers.
 */
export function normalizeMealPlan(data: any): MealPlanResponse | null {
  if (!data || typeof data !== "object") return null;

  let base: any = { ...data };
  if (data.plan_data) {
    if (typeof data.plan_data === "string") {
      try {
        base = { ...JSON.parse(data.plan_data), ...base };
      } catch {
        // fallback
      }
    } else if (typeof data.plan_data === "object") {
      base = { ...data.plan_data, ...base };
    }
  }

  const rawMeals = Array.isArray(base.meals) ? base.meals : [];
  const meals: MealPlanMeal[] = rawMeals.map((m: any) => ({
    meal_name: String(m.meal_name || m.name || "Meal"),
    target_calories: Number(m.target_calories) || 0,
    actual_calories: Number(m.actual_calories ?? m.calories ?? m.target_calories) || 0,
    protein_g: Number(m.protein_g) || 0,
    carbs_g: Number(m.carbs_g) || 0,
    fat_g: Number(m.fat_g) || 0,
    items: Array.isArray(m.items) ? m.items : [],
  }));

  const target_calories = Number(base.target_calories) || 2000;
  const target_protein_g = Number(base.target_protein_g ?? base.achieved_protein_g) || 150;
  const target_carbs_g = Number(base.target_carbs_g ?? base.achieved_carbs_g) || 200;
  const target_fat_g = Number(base.target_fat_g ?? base.achieved_fat_g) || 60;

  return {
    ...base,
    id: base.id ? String(base.id) : undefined,
    user_id: base.user_id ? String(base.user_id) : undefined,
    is_active: base.is_active !== undefined ? Boolean(base.is_active) : true,
    created_at: base.created_at ? String(base.created_at) : undefined,
    title: String(base.title || "Daily Meal Plan"),
    target_calories,
    target_protein_g,
    target_carbs_g,
    target_fat_g,
    achieved_calories: Number(base.achieved_calories ?? target_calories) || target_calories,
    achieved_protein_g: Number(base.achieved_protein_g ?? target_protein_g) || target_protein_g,
    achieved_carbs_g: Number(base.achieved_carbs_g ?? target_carbs_g) || target_carbs_g,
    achieved_fat_g: Number(base.achieved_fat_g ?? target_fat_g) || target_fat_g,
    meals,
  };
}

/**
 * Normalizes any workout plan response (raw DB row, wrapped routine_data, stringified JSON, or flat schema)
 * into a guaranteed valid WorkoutPlanResponse with safe arrays.
 */
export function normalizeWorkoutPlan(data: any): WorkoutPlanResponse | null {
  if (!data || typeof data !== "object") return null;

  let base: any = { ...data };
  if (data.routine_data) {
    if (typeof data.routine_data === "string") {
      try {
        base = { ...JSON.parse(data.routine_data), ...base };
      } catch {
        // fallback
      }
    } else if (typeof data.routine_data === "object") {
      base = { ...data.routine_data, ...base };
    }
  }

  const rawRoutine = Array.isArray(base.routine) ? base.routine : [];
  const routine: WorkoutDayRoutine[] = rawRoutine.map((r: any) => ({
    day: String(r.day || "Day"),
    focus: String(r.focus || "Training Session"),
    exercises: Array.isArray(r.exercises)
      ? r.exercises.map((e: any) => ({
          name: String(e.name || "Exercise"),
          sets: Number(e.sets) || 3,
          reps: String(e.reps || "10"),
          rest_sec: Number(e.rest_sec) || 60,
        }))
      : [],
  }));

  return {
    ...base,
    id: base.id ? String(base.id) : undefined,
    user_id: base.user_id ? String(base.user_id) : undefined,
    is_active: base.is_active !== undefined ? Boolean(base.is_active) : true,
    created_at: base.created_at ? String(base.created_at) : undefined,
    title: String(base.title || "Workout Routine"),
    split_type: String(base.split_type || "FULL_BODY"),
    days_per_week: Number(base.days_per_week) || 4,
    experience_level: String(base.experience_level || "beginner"),
    description: String(base.description || ""),
    routine,
  };
}

/**
 * Fetches the user's currently active meal plan, or null if none is active.
 */
export async function fetchActiveMealPlan(token?: string): Promise<MealPlanResponse | null> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/planning/active-meal-plan`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch active meal plan (HTTP ${res.status})`);
  }
  const rawData = await res.json();
  console.log("[DEBUG] raw active meal plan response:", rawData);
  const normalized = normalizeMealPlan(rawData);
  console.log("[DEBUG] normalized meal plan response:", normalized);
  return normalized;
}

/**
 * Fetches the user's currently active workout plan, or null if none is active.
 */
export async function fetchActiveWorkoutPlan(token?: string): Promise<WorkoutPlanResponse | null> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/planning/active-workout-plan`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch active workout plan (HTTP ${res.status})`);
  }
  const rawData = await res.json();
  console.log("[DEBUG] raw active workout plan response:", rawData);
  const normalized = normalizeWorkoutPlan(rawData);
  console.log("[DEBUG] normalized workout plan response:", normalized);
  return normalized;
}

export interface ApplyAdaptationResponse {
  status: "applied" | "already_applied";
  applied: boolean;
  message: string;
  decision: AdaptationDecision;
  meal_plan: MealPlanResponse;
  workout_plan: WorkoutPlanResponse;
  active_meal_plan_id?: string | null;
  active_workout_plan_id?: string | null;
}

/**
 * Applies the current adaptation decision to the user's active meal and workout plans.
 * Idempotent: returns already_applied without duplicating plans if already up to date.
 */
export async function applyAdaptationToPlans(
  force: boolean = false,
  token?: string
): Promise<ApplyAdaptationResponse> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/planning/apply-adaptation`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ force_apply: force }),
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && "detail" in errData) {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response body
    }
    throw new AdaptationApiError(
      res.status,
      errorDetail || `Failed to apply adaptation (HTTP ${res.status})`,
      errorDetail
    );
  }

  const data = await res.json();
  if (data && data.meal_plan) {
    data.meal_plan = normalizeMealPlan(data.meal_plan);
  }
  if (data && data.workout_plan) {
    data.workout_plan = normalizeWorkoutPlan(data.workout_plan);
  }
  return data;
}

// ---------------------------------------------------------------------------
// Body Analysis Types & Client Functions (Phase 5)
// ---------------------------------------------------------------------------

export type PhotoType = "front" | "side_left" | "side_right" | "back";

export interface PhotoMetadata {
  id: string;
  photo_type: PhotoType;
  captured_at: string;
  file_size_bytes?: number | null;
  width_px?: number | null;
  height_px?: number | null;
  mime_type?: string | null;
  created_at: string;
  analysis_status?: string | null;
  disclaimer: string;
}

export interface BodyAnalysisResult {
  id: string;
  photo_id: string;
  analysis_version: string;
  status: "completed" | "failed" | "pending";
  pose_detected?: boolean | null;
  pose_confidence?: number | null;
  landmarks_visible?: number | null;
  pose_quality?: "good" | "acceptable" | "poor" | "failed" | null;
  shoulder_tilt_deg?: number | null;
  hip_tilt_deg?: number | null;
  symmetry_score?: number | null;
  torso_to_leg_ratio?: number | null;
  shoulder_to_hip_ratio?: number | null;
  processing_ms?: number | null;
  error_message?: string | null;
  created_at: string;
  disclaimer: string;
}

export interface PhotoDetailResponse {
  photo: PhotoMetadata;
  analysis?: BodyAnalysisResult | null;
  disclaimer: string;
}

export interface PhotoListResponse {
  photos: PhotoMetadata[];
  count: number;
  disclaimer: string;
}

/**
 * Uploads a progress photo for observational MediaPipe pose analysis.
 * Strips EXIF metadata on backend, uploads to private storage, and runs pose analysis synchronously.
 */
export async function uploadProgressPhoto(
  file: File,
  photoType: PhotoType,
  capturedAt: string,
  token?: string
): Promise<PhotoDetailResponse> {
  const authToken = await getAuthToken(token);
  const formData = new FormData();
  formData.append("file", file);
  formData.append("photo_type", photoType);
  formData.append("captured_at", capturedAt);

  const res = await fetch(`${API_BASE_URL}/body-analysis/photos`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
    body: formData,
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail || `Failed to upload progress photo (HTTP ${res.status})`);
  }

  return res.json();
}

/**
 * Lists the authenticated user's progress photos metadata (newest first).
 */
export async function fetchProgressPhotos(
  limit: number = 20,
  token?: string
): Promise<PhotoListResponse> {
  const authToken = await getAuthToken(token);
  const clampedLimit = Math.max(1, Math.min(100, limit));
  const res = await fetch(`${API_BASE_URL}/body-analysis/photos?limit=${clampedLimit}`, {
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail || `Failed to fetch progress photos (HTTP ${res.status})`);
  }

  return res.json();
}

/**
 * Retrieves a single progress photo's metadata and its observational pose analysis result.
 */
export async function fetchProgressPhotoDetail(
  photoId: string,
  token?: string
): Promise<PhotoDetailResponse> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/body-analysis/photos/${photoId}`, {
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail || `Failed to fetch photo details (HTTP ${res.status})`);
  }

  return res.json();
}

/**
 * Soft-deletes a progress photo database record and hard-deletes the private storage asset.
 */
export async function deleteProgressPhoto(
  photoId: string,
  token?: string
): Promise<{ deleted: boolean; photo_id: string; message: string }> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/body-analysis/photos/${photoId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail || `Failed to delete progress photo (HTTP ${res.status})`);
  }

  return res.json();
}
