"""
Body Analysis API Module (Phase 5A).

Provides photo upload, retrieval, and deletion endpoints for progress photos.
Phase 5A: upload validation + metadata persistence only.
Phase 5B (not yet implemented): adds OpenCV/MediaPipe pose analysis.

IMPORTANT CONSTRAINTS:
- Body analysis results are OBSERVATIONAL ONLY.
- They must NOT modify adaptation formulas, calorie targets, or workout intensity.
- All ownership decisions are made from the authenticated JWT; user_id is NEVER
  accepted from the request body.
"""

import io
import uuid
import re
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user, UserContext
from app.engine.body_analysis import analyze_body_photo
from app.db.supabase import (
    ProgressPhotoRepository,
    BodyAnalysisRepository,
    IS_LIVE_SUPABASE_ENABLED,
    get_authenticated_supabase_client,
)

router = APIRouter(prefix="/body-analysis", tags=["Body Analysis"])

# ---------------------------------------------------------------------------
# Upload validation constants
# ---------------------------------------------------------------------------
ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
# Magic byte signatures (first bytes of the file)
_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",  # RIFF....WEBP - checked further below
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MIN_DIMENSION_PX = 100
MAX_DIMENSION_PX = 8192

VALID_PHOTO_TYPES = frozenset({"front", "side_left", "side_right", "back"})

# Disclaimer text embedded in every response - non-negotiable
_DISCLAIMER = (
    "These are visual pose observations only. "
    "They do not constitute medical measurements, diagnoses, or body composition assessments. "
    "Values represent pixel-relative proportions and are not equivalent to clinical measurements."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_mime_from_bytes(header: bytes) -> Optional[str]:
    """
    Infer MIME type from file magic bytes.
    Returns None if unrecognised.
    """
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if header[:4] == b"\x89PNG":
        return "image/png"
    # WEBP: "RIFF....WEBP"
    if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def _sanitise_storage_path(user_id: str, photo_id: str, mime_type: str) -> str:
    """
    Builds a user-scoped storage path.
    Never derived from client-supplied filenames.
    """
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(mime_type, "jpg")
    # Defensive: ensure user_id and photo_id are UUID-like (alphanumeric + hyphens only)
    safe_uid = re.sub(r"[^a-zA-Z0-9\-]", "", user_id)[:36]
    safe_pid = re.sub(r"[^a-zA-Z0-9\-]", "", photo_id)[:36]
    return f"{safe_uid}/{safe_pid}.{ext}"


def _strip_exif(image_bytes: bytes, mime_type: str) -> tuple[bytes, int, int]:
    """
    Strips EXIF metadata (including GPS) and returns (clean_bytes, width, height).
    Requires Pillow. In Phase 5A, Pillow is available; MediaPipe is not yet required.
    Raises ValueError if the image cannot be parsed.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required for EXIF stripping") from exc

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # raises on corrupt files
        # Re-open after verify (verify leaves file pointer in indeterminate state)
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        # Validate dimensions
        if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
            raise ValueError(
                f"Image too small: {width}x{height} px "
                f"(minimum {MIN_DIMENSION_PX}x{MIN_DIMENSION_PX})"
            )
        if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
            raise ValueError(
                f"Image too large: {width}x{height} px "
                f"(maximum {MAX_DIMENSION_PX}x{MAX_DIMENSION_PX})"
            )

        # Apply EXIF orientation before stripping (prevents rotated images)
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # exif_transpose is best-effort

        # Strip EXIF: re-save without any EXIF data
        output = io.BytesIO()
        save_format = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}.get(
            mime_type, "JPEG"
        )
        # Convert RGBA/P modes to RGB for JPEG compatibility
        if save_format == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(output, format=save_format)
        clean_bytes = output.getvalue()
        return clean_bytes, width, height

    except (OSError, SyntaxError, Exception) as exc:
        # Catches PIL UnidentifiedImageError, corrupt JPEGs, etc.
        raise ValueError(f"Invalid or unreadable image: {exc}") from exc


async def _upload_to_storage(
    storage_path: str,
    image_bytes: bytes,
    mime_type: str,
    user_token: Optional[str],
) -> None:
    """
    Uploads clean (EXIF-stripped) image bytes to the private Supabase Storage bucket.
    Bucket name: 'progress-photos' (must be pre-created as private in Supabase dashboard).
    In offline/test mode, this is a no-op.
    """
    client = get_authenticated_supabase_client(user_token)
    if client is None:
        # Offline test mode - storage upload is skipped
        return
    try:
        client.storage.from_("progress-photos").upload(
            path=storage_path,
            file=image_bytes,
            file_options={"content-type": mime_type, "upsert": "false"},
        )
    except Exception as exc:
        raise RuntimeError(f"Storage upload failed: {exc}") from exc


def _delete_from_storage(storage_path: str, user_token: Optional[str]) -> None:
    """
    Hard-deletes the image from Supabase Storage.
    In offline/test mode, this is a no-op.
    """
    client = get_authenticated_supabase_client(user_token)
    if client is None:
        return
    try:
        client.storage.from_("progress-photos").remove([storage_path])
    except Exception:
        # Log but don't raise - the DB soft-delete is already committed
        pass


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class PhotoMetadataResponse(BaseModel):
    """Safe, client-facing photo metadata. Never contains storage_path or image bytes."""
    id: str
    photo_type: str
    captured_at: str
    file_size_bytes: Optional[int] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: str
    analysis_status: Optional[str] = Field(None, description="Status from body_analysis_results if available")
    disclaimer: str = Field(_DISCLAIMER)


class AnalysisResultResponse(BaseModel):
    """
    Body analysis result for a single photo.
    All metric fields are OBSERVATIONAL ONLY (pose estimates, not medical measurements).
    """
    id: str
    photo_id: str
    analysis_version: str
    status: str

    pose_detected: Optional[bool] = None
    pose_confidence: Optional[float] = None
    landmarks_visible: Optional[int] = None
    pose_quality: Optional[str] = None

    # Body proportion fields (pixel-relative, image-normalised)
    shoulder_tilt_deg: Optional[float] = None
    hip_tilt_deg: Optional[float] = None
    symmetry_score: Optional[float] = None
    torso_to_leg_ratio: Optional[float] = None
    shoulder_to_hip_ratio: Optional[float] = None

    processing_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str

    disclaimer: str = Field(_DISCLAIMER)


class PhotoDetailResponse(BaseModel):
    photo: PhotoMetadataResponse
    analysis: Optional[AnalysisResultResponse] = None
    disclaimer: str = Field(_DISCLAIMER)


class PhotoListResponse(BaseModel):
    photos: List[PhotoMetadataResponse]
    count: int
    disclaimer: str = Field(_DISCLAIMER)


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------

def _build_photo_response(row: Dict[str, Any], analysis: Optional[Dict[str, Any]] = None) -> PhotoMetadataResponse:
    return PhotoMetadataResponse(
        id=str(row["id"]),
        photo_type=row["photo_type"],
        captured_at=str(row["captured_at"]),
        file_size_bytes=row.get("file_size_bytes"),
        width_px=row.get("width_px"),
        height_px=row.get("height_px"),
        mime_type=row.get("mime_type"),
        created_at=str(row.get("created_at", "")),
        analysis_status=analysis.get("status") if analysis else None,
    )


def _build_analysis_response(row: Dict[str, Any]) -> AnalysisResultResponse:
    return AnalysisResultResponse(
        id=str(row["id"]),
        photo_id=str(row["photo_id"]),
        analysis_version=str(row.get("analysis_version", "v1")),
        status=str(row.get("status", "pending")),
        pose_detected=row.get("pose_detected"),
        pose_confidence=row.get("pose_confidence"),
        landmarks_visible=row.get("landmarks_visible"),
        pose_quality=row.get("pose_quality"),
        shoulder_tilt_deg=row.get("shoulder_tilt_deg"),
        hip_tilt_deg=row.get("hip_tilt_deg"),
        symmetry_score=row.get("symmetry_score"),
        torso_to_leg_ratio=row.get("torso_to_leg_ratio"),
        shoulder_to_hip_ratio=row.get("shoulder_to_hip_ratio"),
        processing_ms=row.get("processing_ms"),
        error_message=row.get("error_message"),
        created_at=str(row.get("created_at", "")),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/photos", status_code=status.HTTP_201_CREATED, response_model=PhotoDetailResponse)
async def upload_progress_photo(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, or WebP, max 10 MB)"),
    photo_type: str = Form(..., description="Pose direction: front | side_left | side_right | back"),
    captured_at: str = Form(..., description="Date photo was taken (YYYY-MM-DD)"),
    user_ctx: UserContext = Depends(get_current_user),
):
    """
    Upload a progress photo.

    Phase 5A performs:
    1. File type validation (by magic bytes, not extension).
    2. File size enforcement (<= 10 MB).
    3. Image integrity check.
    4. EXIF metadata stripping (including GPS).
    5. Orientation normalisation.
    6. Dimension validation.
    7. Upload to private Supabase Storage.
    8. Persistence of photo metadata.
    9. Creation of a placeholder analysis record (status=pending).

    Phase 5B will extend step 9 to run MediaPipe Pose synchronously.

    NOTE: Body analysis results are OBSERVATIONAL ONLY and do not affect adaptation plans.
    """
    # --- 1. Validate photo_type ---
    if photo_type not in VALID_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid photo_type. Must be one of: {sorted(VALID_PHOTO_TYPES)}",
        )

    # --- 2. Validate captured_at ---
    try:
        parsed_date = date.fromisoformat(captured_at)
        if parsed_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="captured_at cannot be in the future.",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="captured_at must be a valid date in YYYY-MM-DD format.",
        )

    # --- 3. Read bytes (size-limited) ---
    # Read in chunks to avoid loading the entire file if it's enormous
    MAX_READ = MAX_FILE_SIZE_BYTES + 1  # one extra byte to detect oversize
    raw_bytes = await file.read(MAX_READ)
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.",
        )
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    # --- 4. Detect MIME from magic bytes (never trust Content-Type or filename) ---
    detected_mime = _detect_mime_from_bytes(raw_bytes[:12])
    if detected_mime is None or detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image format. "
                f"Allowed formats: JPEG, PNG, WebP. "
                f"Detected: {detected_mime or 'unknown'}."
            ),
        )

    # --- 5. Strip EXIF, validate dimensions, normalise orientation ---
    try:
        clean_bytes, width_px, height_px = _strip_exif(raw_bytes, detected_mime)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    # --- 6. Generate storage path (never from client filename) ---
    photo_id = str(uuid.uuid4())
    storage_path = _sanitise_storage_path(user_ctx.user_id, photo_id, detected_mime)

    # --- 7. Upload to private Supabase Storage ---
    try:
        await _upload_to_storage(storage_path, clean_bytes, detected_mime, user_ctx.access_token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    # --- 8. Persist photo metadata (storage_path never returned to client) ---
    photo_record = ProgressPhotoRepository.create_photo(
        user_id=user_ctx.user_id,
        photo_data={
            "id": photo_id,  # pass generated ID so offline store and live DB use the same
            "storage_path": storage_path,
            "photo_type": photo_type,
            "captured_at": captured_at,
            "file_size_bytes": len(clean_bytes),
            "width_px": width_px,
            "height_px": height_px,
            "mime_type": detected_mime,
        },
        user_token=user_ctx.access_token,
    )

    # --- 9. Create placeholder analysis record (status=pending) ---
    analysis_record = BodyAnalysisRepository.create_result(
        user_id=user_ctx.user_id,
        photo_id=photo_record["id"],
        result_data={
            "analysis_version": "v1",
            "status": "pending",
            "disclaimer_accepted": True,
        },
        user_token=user_ctx.access_token,
    )

    # --- 10. Run MediaPipe Body Analysis Engine synchronously ---
    analysis_result = analyze_body_photo(clean_bytes)

    # --- 11. Persist analysis result (status becomes completed or failed) ---
    updated_analysis = BodyAnalysisRepository.update_result(
        result_id=analysis_record["id"],
        user_id=user_ctx.user_id,
        update_data={
            "analysis_version": analysis_result.analysis_version,
            "status": analysis_result.status,
            "pose_detected": analysis_result.pose_detected,
            "pose_confidence": analysis_result.pose_confidence,
            "landmarks_visible": analysis_result.landmarks_visible,
            "pose_quality": analysis_result.pose_quality,
            "shoulder_tilt_deg": analysis_result.shoulder_tilt_deg,
            "hip_tilt_deg": analysis_result.hip_tilt_deg,
            "symmetry_score": analysis_result.symmetry_score,
            "torso_to_leg_ratio": analysis_result.torso_to_leg_ratio,
            "shoulder_to_hip_ratio": analysis_result.shoulder_to_hip_ratio,
            "raw_landmarks": analysis_result.raw_landmarks,
            "processing_ms": analysis_result.processing_ms,
            "error_message": analysis_result.error_message,
            "disclaimer_accepted": True,
        },
        user_token=user_ctx.access_token,
    )

    final_analysis = updated_analysis if updated_analysis is not None else analysis_record

    return PhotoDetailResponse(
        photo=_build_photo_response(photo_record, final_analysis),
        analysis=_build_analysis_response(final_analysis),
    )


@router.get("/photos", response_model=PhotoListResponse)
def list_progress_photos(
    limit: int = Query(default=20, ge=1, le=100),
    user_ctx: UserContext = Depends(get_current_user),
):
    """
    Returns the authenticated user's progress photos, newest first.
    Soft-deleted photos are excluded.
    storage_path is never returned to the client.
    """
    photos = ProgressPhotoRepository.get_photos(
        user_id=user_ctx.user_id,
        user_token=user_ctx.access_token,
        include_deleted=False,
    )[:limit]

    # Fetch analysis status for each photo
    responses = []
    for p in photos:
        analysis = BodyAnalysisRepository.get_result_by_photo(
            photo_id=str(p["id"]),
            user_token=user_ctx.access_token,
        )
        responses.append(_build_photo_response(p, analysis))

    return PhotoListResponse(photos=responses, count=len(responses))


@router.get("/photos/{photo_id}", response_model=PhotoDetailResponse)
def get_progress_photo(
    photo_id: str,
    user_ctx: UserContext = Depends(get_current_user),
):
    """
    Returns a single progress photo and its analysis result.
    Returns 404 if not found or soft-deleted.
    Returns 403 if the photo belongs to another user (ownership enforced by RLS + explicit check).
    storage_path is never returned to the client.
    """
    photo = ProgressPhotoRepository.get_photo(
        photo_id=photo_id,
        user_token=user_ctx.access_token,
    )
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")

    # Explicit ownership check (defence-in-depth beyond RLS)
    if str(photo.get("user_id")) != user_ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    analysis = BodyAnalysisRepository.get_result_by_photo(
        photo_id=str(photo["id"]),
        user_token=user_ctx.access_token,
    )

    return PhotoDetailResponse(
        photo=_build_photo_response(photo, analysis),
        analysis=_build_analysis_response(analysis) if analysis else None,
    )


@router.delete("/photos/{photo_id}", status_code=status.HTTP_200_OK)
def delete_progress_photo(
    photo_id: str,
    user_ctx: UserContext = Depends(get_current_user),
):
    """
    Soft-deletes a progress photo (DB row) and hard-deletes the storage object.
    Returns 404 if not found or already deleted.
    Returns 403 if the photo belongs to another user.
    The body_analysis_results row is retained for audit purposes.
    """
    # Retrieve first to get storage_path and verify ownership
    photo = ProgressPhotoRepository.get_photo(
        photo_id=photo_id,
        user_token=user_ctx.access_token,
    )
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")

    # Explicit ownership check
    if str(photo.get("user_id")) != user_ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Soft-delete the DB row
    deleted = ProgressPhotoRepository.soft_delete_photo(
        photo_id=photo_id,
        user_id=user_ctx.user_id,
        user_token=user_ctx.access_token,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found or already deleted.")

    # Hard-delete the storage object (best-effort; DB row is already soft-deleted)
    storage_path = photo.get("storage_path", "")
    if storage_path:
        _delete_from_storage(storage_path, user_ctx.access_token)

    return {"deleted": True, "photo_id": photo_id, "message": "Photo deleted successfully."}
