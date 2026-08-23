/**
 * Typed API Client for FastAPI Backend.
 * Handles profile management, meal/workout planning, predictive simulations,
 * daily progress logs, and AI coaching feedback.
 */

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

export async function fetchProfile(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/profile`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch user profile");
  return res.json();
}

export async function saveProfile(token: string, profile: UserProfile): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/profile`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error("Failed to save user profile");
  return res.json();
}

export async function runSimulation(token: string, req: SimulationRequest) {
  const res = await fetch(`${API_BASE_URL}/simulation/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to run predictive simulation");
  return res.json();
}

export async function submitJournal(token: string, text: string) {
  const res = await fetch(`${API_BASE_URL}/coaching/journal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ entry_text: text }),
  });
  if (!res.ok) throw new Error("Failed to submit journal entry");
  return res.json();
}
