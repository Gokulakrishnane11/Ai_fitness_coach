-- Supabase V4 Schema Migration: Progress Photos & Body Analysis
-- Migration Name: 20261002000000_v4_progress_photos.sql
--
-- Adds two tables for Phase 5A:
--   progress_photos      - photo metadata (bytes are in Supabase Storage, not here)
--   body_analysis_results - per-photo CV analysis output
--
-- Design principles:
--   - No image bytes are stored in the database.
--   - Storage paths are user-scoped: {user_id}/{photo_uuid} in a PRIVATE bucket.
--   - Body analysis fields are OBSERVATIONAL ONLY and must NOT be used by adaptation formulas.
--   - is_deleted is a soft-delete flag; hard deletion of storage objects is handled in the API.

-- Ensure UUID extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- 12. PROGRESS PHOTOS (metadata only - bytes live in Supabase Storage)
CREATE TABLE IF NOT EXISTS public.progress_photos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,

    -- Storage reference (private bucket path, never a public URL)
    storage_path    TEXT NOT NULL,

    -- Photo context supplied by the user
    photo_type      TEXT NOT NULL CHECK (photo_type IN ('front', 'side_left', 'side_right', 'back')),
    captured_at     DATE NOT NULL,

    -- Basic image metadata recorded at upload time (no EXIF - stripped server-side)
    file_size_bytes INT     CHECK (file_size_bytes > 0),
    width_px        INT     CHECK (width_px > 0),
    height_px       INT     CHECK (height_px > 0),
    mime_type       TEXT    CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp')),

    -- Soft delete: row is kept for audit; storage object is hard-deleted by the API
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 13. BODY ANALYSIS RESULTS (per-photo, observational only)
CREATE TABLE IF NOT EXISTS public.body_analysis_results (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    photo_id              UUID NOT NULL REFERENCES public.progress_photos(id) ON DELETE CASCADE,

    -- Analysis provenance
    analysis_version      TEXT NOT NULL DEFAULT 'v1',
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'completed', 'failed')),

    -- Pose detection output
    pose_detected         BOOLEAN,
    pose_confidence       NUMERIC(4, 3)   CHECK (pose_confidence BETWEEN 0 AND 1),
    landmarks_visible     INT             CHECK (landmarks_visible BETWEEN 0 AND 33),
    pose_quality          TEXT            CHECK (pose_quality IN ('good', 'acceptable', 'poor', 'failed')),

    -- Safe body-proportion metrics (pixel-relative, image-normalised, NOT absolute cm)
    -- Only populated when pose_quality IN ('good','acceptable')
    shoulder_tilt_deg     NUMERIC(6, 2),
    hip_tilt_deg          NUMERIC(6, 2),
    symmetry_score        NUMERIC(5, 4)   CHECK (symmetry_score BETWEEN 0 AND 1),
    torso_to_leg_ratio    NUMERIC(5, 3)   CHECK (torso_to_leg_ratio > 0),
    shoulder_to_hip_ratio NUMERIC(5, 3)  CHECK (shoulder_to_hip_ratio > 0),

    -- Full landmark array for future reprocessing
    raw_landmarks         JSONB,

    -- Processing metadata
    processing_ms         INT             CHECK (processing_ms >= 0),
    error_message         TEXT,

    -- Disclaimer: always TRUE; values are visual/pose estimates only
    disclaimer_accepted   BOOLEAN NOT NULL DEFAULT TRUE,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Indices
CREATE INDEX IF NOT EXISTS idx_progress_photos_user_captured
    ON public.progress_photos (user_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_body_analysis_photo_id
    ON public.body_analysis_results (photo_id);

CREATE INDEX IF NOT EXISTS idx_body_analysis_user_created
    ON public.body_analysis_results (user_id, created_at DESC);


-- Row Level Security
ALTER TABLE public.progress_photos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.body_analysis_results  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users access own progress photos"
    ON public.progress_photos
    FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users access own body analysis results"
    ON public.body_analysis_results
    FOR ALL
    USING (auth.uid() = user_id);
