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
  title: string;
  target_calories: number;
  achieved_calories: number;
  achieved_protein_g: number;
  achieved_carbs_g: number;
  achieved_fat_g: number;
  meals: MealPlanMeal[];
}

export interface WorkoutPlanRequest {
  goal_type: string;
  workout_days_per_week: number;
  experience_level: string;
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
  title: string;
  split_type: string;
  days_per_week: number;
  experience_level: string;
  description: string;
  routine: WorkoutDayRoutine[];
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
  return res.json();
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
  return res.json();
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
 * Status code handling:
 * - 401: Unauthenticated request (user not logged in or invalid token)
 * - 404: Profile not found (user has not completed onboarding)
 * - 422: Incomplete profile or missing target metrics required for adaptation
 * - Other non-success HTTP codes: Meaningful error message
 */
export async function fetchAdaptationDecision(token?: string): Promise<AdaptationDecision> {
  const authToken = await getAuthToken(token);
  const res = await fetch(`${API_BASE_URL}/adaptation`, {
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


