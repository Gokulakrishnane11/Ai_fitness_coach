"""
MediaPipe & OpenCV Body Analysis Engine (Phase 5B).

Provides observational, non-medical computer vision analysis for user progress photos.
Calculates visual pose geometry: shoulder tilt, hip tilt, bilateral symmetry,
torso-to-leg ratio, and shoulder-to-hip ratio using MediaPipe Pose Landmarker.

IMPORTANT SCIENTIFIC & ETHICAL CONSTRAINTS:
- Observational ONLY: does NOT diagnose medical conditions or injuries.
- Does NOT calculate body fat percentage, muscle mass, or exact centimetre measurements.
- Coordinates are image-normalised [0.0, 1.0], not real-world units.
- Metrics are calculated ONLY when relevant landmarks meet minimum visibility thresholds.
- If no usable pose is detected, returns status='failed' with a clear non-medical explanation;
  does NOT fabricate measurements.
"""

from __future__ import annotations

import io
import math
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Constants & Thresholds
# ---------------------------------------------------------------------------
ANALYSIS_VERSION = "v1"

# Minimum landmark visibility confidence (0.0 to 1.0)
VISIBILITY_THRESHOLD = 0.5

# MediaPipe Pose Landmark Indices (33 landmarks)
NOSE = 0
LEFT_EYE_INNER = 1
LEFT_EYE = 2
LEFT_EYE_OUTER = 3
RIGHT_EYE_INNER = 4
RIGHT_EYE = 5
RIGHT_EYE_OUTER = 6
LEFT_EAR = 7
RIGHT_EAR = 8
MOUTH_LEFT = 9
MOUTH_RIGHT = 10
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_PINKY = 17
RIGHT_PINKY = 18
LEFT_INDEX = 19
RIGHT_INDEX = 20
LEFT_THUMB = 21
RIGHT_THUMB = 22
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_HEEL = 29
RIGHT_HEEL = 30
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32

# Key anatomical landmarks required for core proportions
CORE_LANDMARKS = [
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
]

# Non-medical disclaimer
DISCLAIMER_TEXT = (
    "These are visual pose observations only. "
    "They do not constitute medical measurements, diagnoses, or body composition assessments. "
    "Values represent pixel-relative proportions and are not equivalent to clinical measurements."
)

# Model bundle search locations
_MODEL_FILENAME = "pose_landmarker_lite.task"
_POSSIBLE_MODEL_PATHS = [
    os.path.join(os.path.dirname(__file__), "models", _MODEL_FILENAME),
    os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "models")), _MODEL_FILENAME),
    os.path.join(os.getcwd(), "assets", "models", _MODEL_FILENAME),
]


# ---------------------------------------------------------------------------
# Structured Results Data Class
# ---------------------------------------------------------------------------
@dataclass
class BodyAnalysisResult:
    """Observational pose analysis result."""

    analysis_version: str = ANALYSIS_VERSION
    status: str = "pending"  # "completed" | "failed"
    pose_detected: bool = False
    pose_confidence: Optional[float] = None
    landmarks_visible: Optional[int] = None
    pose_quality: Optional[str] = None  # "good" | "acceptable" | "poor" | "failed"

    # Geometric proportion metrics (null if quality < acceptable or landmarks missing)
    shoulder_tilt_deg: Optional[float] = None
    hip_tilt_deg: Optional[float] = None
    symmetry_score: Optional[float] = None
    torso_to_leg_ratio: Optional[float] = None
    shoulder_to_hip_ratio: Optional[float] = None

    # Full landmark metadata
    raw_landmarks: Optional[List[Dict[str, float]]] = None

    # Operational metrics
    processing_ms: int = 0
    error_message: Optional[str] = None
    disclaimer_accepted: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to a dictionary suitable for DB persistence / JSON response."""
        data = asdict(self)
        return data


# ---------------------------------------------------------------------------
# Pure Geometric Calculation Functions
# ---------------------------------------------------------------------------

def calculate_tilt_deg(
    pt_left: Dict[str, float],
    pt_right: Dict[str, float],
) -> Optional[float]:
    """
    Calculates the angular deviation from the horizontal in degrees.

    Returns:
        float: Tilt in degrees in range [-90.0, 90.0], where 0.0 is level.
               Positive if the subject's right side is lower in image coordinates (higher y),
               negative if subject's right side is higher in image coordinates.
        None: If coordinates are invalid or points coincide.
    """
    dy = pt_right["y"] - pt_left["y"]
    dx = pt_right["x"] - pt_left["x"]

    # Horizontal span check
    if abs(dx) < 1e-6:
        # Near vertical line
        return 90.0 if dy > 0 else -90.0

    # Deviation angle relative to horizontal span
    angle_rad = math.atan2(dy, abs(dx))
    return round(math.degrees(angle_rad), 2)


def calculate_euclidean_distance_2d(
    pt1: Dict[str, float],
    pt2: Dict[str, float],
) -> float:
    """Calculates 2D Euclidean distance in normalised coordinate space."""
    return math.hypot(pt2["x"] - pt1["x"], pt2["y"] - pt1["y"])


def calculate_symmetry_score(
    landmarks: List[Dict[str, float]],
    vis_threshold: float = VISIBILITY_THRESHOLD,
) -> Optional[float]:
    """
    Computes a bilateral symmetry score [0.0, 1.0], where 1.0 indicates perfect symmetry.

    Compares corresponding left and right segment lengths (torso and optionally legs).
    Returns None if required shoulders or hips are not visible.
    """
    if len(landmarks) < 25:
        return None

    l_sh = landmarks[LEFT_SHOULDER]
    r_sh = landmarks[RIGHT_SHOULDER]
    l_hip = landmarks[LEFT_HIP]
    r_hip = landmarks[RIGHT_HIP]

    # Required landmarks check
    if (
        l_sh.get("visibility", 0) < vis_threshold
        or r_sh.get("visibility", 0) < vis_threshold
        or l_hip.get("visibility", 0) < vis_threshold
        or r_hip.get("visibility", 0) < vis_threshold
    ):
        return None

    # Torso segment length comparison (left vs right)
    dist_l_torso = calculate_euclidean_distance_2d(l_sh, l_hip)
    dist_r_torso = calculate_euclidean_distance_2d(r_sh, r_hip)

    max_torso = max(dist_l_torso, dist_r_torso)
    if max_torso < 1e-4:
        return None

    torso_symmetry = min(dist_l_torso, dist_r_torso) / max_torso

    # Leg segment comparison if legs are visible
    scores = [torso_symmetry]

    if len(landmarks) >= 29:
        l_knee = landmarks[LEFT_KNEE]
        r_knee = landmarks[RIGHT_KNEE]
        l_ank = landmarks[LEFT_ANKLE]
        r_ank = landmarks[RIGHT_ANKLE]

        legs_visible = (
            l_knee.get("visibility", 0) >= vis_threshold
            and r_knee.get("visibility", 0) >= vis_threshold
            and l_ank.get("visibility", 0) >= vis_threshold
            and r_ank.get("visibility", 0) >= vis_threshold
        )
        if legs_visible:
            dist_l_leg = calculate_euclidean_distance_2d(l_hip, l_knee) + calculate_euclidean_distance_2d(l_knee, l_ank)
            dist_r_leg = calculate_euclidean_distance_2d(r_hip, r_knee) + calculate_euclidean_distance_2d(r_knee, r_ank)
            max_leg = max(dist_l_leg, dist_r_leg)
            if max_leg > 1e-4:
                leg_symmetry = min(dist_l_leg, dist_r_leg) / max_leg
                scores.append(leg_symmetry)

    avg_symmetry = sum(scores) / len(scores)
    return round(float(np.clip(avg_symmetry, 0.0, 1.0)), 4)


def calculate_torso_to_leg_ratio(
    landmarks: List[Dict[str, float]],
    vis_threshold: float = VISIBILITY_THRESHOLD,
) -> Optional[float]:
    """
    Computes approximate ratio of torso height to leg length.

    Requires shoulders, hips, and ankles to be visible.
    Returns None if required landmarks are missing or leg length is too small.
    """
    if len(landmarks) < 29:
        return None

    l_sh = landmarks[LEFT_SHOULDER]
    r_sh = landmarks[RIGHT_SHOULDER]
    l_hip = landmarks[LEFT_HIP]
    r_hip = landmarks[RIGHT_HIP]
    l_ank = landmarks[LEFT_ANKLE]
    r_ank = landmarks[RIGHT_ANKLE]

    if (
        l_sh.get("visibility", 0) < vis_threshold
        or r_sh.get("visibility", 0) < vis_threshold
        or l_hip.get("visibility", 0) < vis_threshold
        or r_hip.get("visibility", 0) < vis_threshold
        or l_ank.get("visibility", 0) < vis_threshold
        or r_ank.get("visibility", 0) < vis_threshold
    ):
        return None

    # Midpoints
    mid_shoulder_y = (l_sh["y"] + r_sh["y"]) / 2.0
    mid_hip_y = (l_hip["y"] + r_hip["y"]) / 2.0
    mid_ankle_y = (l_ank["y"] + r_ank["y"]) / 2.0

    torso_height = abs(mid_hip_y - mid_shoulder_y)
    leg_height = abs(mid_ankle_y - mid_hip_y)

    if leg_height < 0.01:
        return None

    ratio = torso_height / leg_height
    return round(float(ratio), 3)


def calculate_shoulder_to_hip_ratio(
    landmarks: List[Dict[str, float]],
    vis_threshold: float = VISIBILITY_THRESHOLD,
) -> Optional[float]:
    """
    Computes ratio of shoulder width to hip width.

    Requires left/right shoulders and left/right hips to be visible.
    Returns None if landmarks are missing or hip width is too small.
    """
    if len(landmarks) < 25:
        return None

    l_sh = landmarks[LEFT_SHOULDER]
    r_sh = landmarks[RIGHT_SHOULDER]
    l_hip = landmarks[LEFT_HIP]
    r_hip = landmarks[RIGHT_HIP]

    if (
        l_sh.get("visibility", 0) < vis_threshold
        or r_sh.get("visibility", 0) < vis_threshold
        or l_hip.get("visibility", 0) < vis_threshold
        or r_hip.get("visibility", 0) < vis_threshold
    ):
        return None

    shoulder_width = calculate_euclidean_distance_2d(l_sh, r_sh)
    hip_width = calculate_euclidean_distance_2d(l_hip, r_hip)

    if hip_width < 0.01:
        return None

    ratio = shoulder_width / hip_width
    return round(float(ratio), 3)


def evaluate_pose_quality(
    landmarks_visible: int,
    avg_confidence: float,
) -> str:
    """
    Classifies pose quality conservatively:
    - 'good': >= 25 landmarks visible with high confidence
    - 'acceptable': >= 18 landmarks visible with acceptable confidence
    - 'poor': 10 to 17 landmarks visible
    - 'failed': < 10 landmarks visible
    """
    if landmarks_visible < 10 or avg_confidence < 0.3:
        return "failed"
    if landmarks_visible < 18 or avg_confidence < 0.45:
        return "poor"
    if landmarks_visible < 25 or avg_confidence < 0.6:
        return "acceptable"
    return "good"


# ---------------------------------------------------------------------------
# Image Preprocessing Helper
# ---------------------------------------------------------------------------

def decode_image_to_rgb(image_bytes: bytes) -> np.ndarray:
    """
    Decodes image bytes safely into an RGB NumPy array.
    Normalises EXIF orientation using Pillow before converting to array.

    Raises:
        ValueError: If bytes cannot be decoded or image is empty.
    """
    if not image_bytes:
        raise ValueError("Image bytes are empty.")

    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img.verify()
        # Re-open after verify
        pil_img = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Corrupt or unreadable image bytes: {exc}") from exc

    # Apply EXIF transpose (handles rotation from camera sensors)
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    rgb_array = np.array(pil_img, dtype=np.uint8)
    if rgb_array.size == 0:
        raise ValueError("Decoded image is empty.")

    return rgb_array


# ---------------------------------------------------------------------------
# Analyzer Abstraction & MediaPipe Lifecycle
# ---------------------------------------------------------------------------

class PoseAnalyzerProtocol(Protocol):
    """Protocol for pluggable pose analyzers (production vs test mocks)."""

    def analyze_rgb(self, rgb_array: np.ndarray) -> Optional[List[Dict[str, float]]]:
        """Returns list of 33 normalised landmark dicts or None if no pose detected."""
        ...


class MediaPipePoseAnalyzer:
    """
    Production MediaPipe Pose Landmarker implementation.
    Loads task bundle once and executes CPU-friendly inference.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._resolve_model_path()
        self._landmarker = None

    @staticmethod
    def _resolve_model_path() -> str:
        for path in _POSSIBLE_MODEL_PATHS:
            if os.path.exists(path):
                return path
        raise FileNotFoundError(
            f"MediaPipe pose task model not found. Searched locations: {_POSSIBLE_MODEL_PATHS}"
        )

    def _get_landmarker(self):
        if self._landmarker is None:
            import mediapipe as mp
            from mediapipe.tasks.python.vision import PoseLandmarker

            self._landmarker = PoseLandmarker.create_from_model_path(self.model_path)
        return self._landmarker

    def analyze_rgb(self, rgb_array: np.ndarray) -> Optional[List[Dict[str, float]]]:
        """
        Runs MediaPipe Pose Landmarker on an RGB NumPy array.
        Returns 33 landmark dictionaries with x, y, z, visibility.
        """
        import mediapipe as mp

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_array)
        landmarker = self._get_landmarker()
        detection_result = landmarker.detect(mp_image)

        if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
            return None

        # Take the first detected person
        person_landmarks = detection_result.pose_landmarks[0]
        result: List[Dict[str, float]] = []

        for idx, lm in enumerate(person_landmarks):
            vis = float(getattr(lm, "visibility", 0.0) or 0.0)
            result.append({
                "index": idx,
                "x": round(float(lm.x), 5),
                "y": round(float(lm.y), 5),
                "z": round(float(lm.z), 5),
                "visibility": round(vis, 4),
            })

        return result

    def close(self):
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None


# ---------------------------------------------------------------------------
# Global Registry / Dependency Injection for Testing
# ---------------------------------------------------------------------------
_active_analyzer: Optional[PoseAnalyzerProtocol] = None


def get_pose_analyzer() -> PoseAnalyzerProtocol:
    """Returns the active pose analyzer (or instantiates the default MediaPipe analyzer)."""
    global _active_analyzer
    if _active_analyzer is None:
        _active_analyzer = MediaPipePoseAnalyzer()
    return _active_analyzer


def set_pose_analyzer(analyzer: Optional[PoseAnalyzerProtocol]) -> None:
    """Injects a custom pose analyzer for unit testing or resets to default."""
    global _active_analyzer
    _active_analyzer = analyzer


# ---------------------------------------------------------------------------
# Main Public Entrypoint
# ---------------------------------------------------------------------------

def analyze_body_photo(image_bytes: bytes) -> BodyAnalysisResult:
    """
    Main analysis pipeline for uploaded progress photos.

    Steps:
    1. Records execution start time.
    2. Decodes image bytes to RGB with orientation normalisation.
    3. Runs pose detection.
    4. Evaluates landmark visibility and pose quality.
    5. Computes geometric proportions (tilts, symmetry, ratios) only if quality is adequate.
    6. Returns structured BodyAnalysisResult (never raises an unhandled exception).
    """
    start_time = time.perf_counter()

    try:
        # Step 1: Decode & normalise image
        rgb_array = decode_image_to_rgb(image_bytes)

        # Step 2: Run pose analysis
        analyzer = get_pose_analyzer()
        landmarks = analyzer.analyze_rgb(rgb_array)

        elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        # Handle case: No pose detected
        if landmarks is None or len(landmarks) == 0:
            return BodyAnalysisResult(
                analysis_version=ANALYSIS_VERSION,
                status="failed",
                pose_detected=False,
                pose_confidence=0.0,
                landmarks_visible=0,
                pose_quality="failed",
                processing_ms=elapsed_ms,
                error_message="No human pose detected in the photo. Please ensure a clear, well-lit, full-body view.",
            )

        # Step 3: Visibility and confidence metrics
        visibilities = [lm.get("visibility", 0.0) for lm in landmarks]
        landmarks_visible = sum(1 for v in visibilities if v >= VISIBILITY_THRESHOLD)
        avg_confidence = round(float(np.mean(visibilities)), 3) if visibilities else 0.0

        # Step 4: Pose quality assessment
        pose_quality = evaluate_pose_quality(landmarks_visible, avg_confidence)

        # If quality is failed, record failure without fabricating measurements
        if pose_quality == "failed":
            return BodyAnalysisResult(
                analysis_version=ANALYSIS_VERSION,
                status="failed",
                pose_detected=False,
                pose_confidence=avg_confidence,
                landmarks_visible=landmarks_visible,
                pose_quality="failed",
                raw_landmarks=landmarks,
                processing_ms=elapsed_ms,
                error_message="Insufficient pose visibility to perform geometric observations.",
            )

        # Step 5: Geometric proportion metrics (observational only)
        shoulder_tilt = None
        hip_tilt = None
        symmetry_score = None
        torso_to_leg_ratio = None
        shoulder_to_hip_ratio = None

        # Metrics are only populated when pose quality is acceptable or good
        if pose_quality in ("good", "acceptable"):
            l_sh = landmarks[LEFT_SHOULDER]
            r_sh = landmarks[RIGHT_SHOULDER]
            if l_sh.get("visibility", 0) >= VISIBILITY_THRESHOLD and r_sh.get("visibility", 0) >= VISIBILITY_THRESHOLD:
                shoulder_tilt = calculate_tilt_deg(l_sh, r_sh)

            l_hip = landmarks[LEFT_HIP]
            r_hip = landmarks[RIGHT_HIP]
            if l_hip.get("visibility", 0) >= VISIBILITY_THRESHOLD and r_hip.get("visibility", 0) >= VISIBILITY_THRESHOLD:
                hip_tilt = calculate_tilt_deg(l_hip, r_hip)

            symmetry_score = calculate_symmetry_score(landmarks, VISIBILITY_THRESHOLD)
            torso_to_leg_ratio = calculate_torso_to_leg_ratio(landmarks, VISIBILITY_THRESHOLD)
            shoulder_to_hip_ratio = calculate_shoulder_to_hip_ratio(landmarks, VISIBILITY_THRESHOLD)

        return BodyAnalysisResult(
            analysis_version=ANALYSIS_VERSION,
            status="completed",
            pose_detected=True,
            pose_confidence=avg_confidence,
            landmarks_visible=landmarks_visible,
            pose_quality=pose_quality,
            shoulder_tilt_deg=shoulder_tilt,
            hip_tilt_deg=hip_tilt,
            symmetry_score=symmetry_score,
            torso_to_leg_ratio=torso_to_leg_ratio,
            shoulder_to_hip_ratio=shoulder_to_hip_ratio,
            raw_landmarks=landmarks,
            processing_ms=elapsed_ms,
            error_message=None,
        )

    except ValueError as exc:
        # Invalid image bytes, decoding failure
        elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        return BodyAnalysisResult(
            analysis_version=ANALYSIS_VERSION,
            status="failed",
            pose_detected=False,
            processing_ms=elapsed_ms,
            error_message=f"Image decoding error: {exc}",
        )
    except Exception as exc:
        # Catch-all: API must never crash due to analysis failures
        elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        return BodyAnalysisResult(
            analysis_version=ANALYSIS_VERSION,
            status="failed",
            pose_detected=False,
            processing_ms=elapsed_ms,
            error_message=f"Analysis pipeline error: {exc}",
        )
