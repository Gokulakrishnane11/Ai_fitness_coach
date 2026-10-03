"""
Engine Unit Tests for MediaPipe & OpenCV Body Analysis (Phase 5B).

Tests pure geometric calculations, image preprocessing, orientation handling,
pose quality evaluation, landmark visibility filtering, and pipeline error resilience.
All tests run offline without external internet access.
"""

import io
import math
import pytest
import numpy as np
from PIL import Image, ImageOps

from app.engine.body_analysis import (
    ANALYSIS_VERSION,
    CORE_LANDMARKS,
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    VISIBILITY_THRESHOLD,
    BodyAnalysisResult,
    analyze_body_photo,
    calculate_euclidean_distance_2d,
    calculate_shoulder_to_hip_ratio,
    calculate_symmetry_score,
    calculate_tilt_deg,
    calculate_torso_to_leg_ratio,
    decode_image_to_rgb,
    evaluate_pose_quality,
    get_pose_analyzer,
    set_pose_analyzer,
)


# ---------------------------------------------------------------------------
# Test Helpers & Mock Analyzer
# ---------------------------------------------------------------------------

def _build_33_landmarks(
    default_vis: float = 0.9,
    overrides: dict = None,
) -> list:
    """Builds a complete list of 33 normalised landmarks for deterministic testing."""
    landmarks = []
    for i in range(33):
        landmarks.append({
            "index": i,
            "x": 0.5,
            "y": 0.5,
            "z": 0.0,
            "visibility": default_vis,
        })
    if overrides:
        for idx, values in overrides.items():
            landmarks[idx].update(values)
    return landmarks


class MockPoseAnalyzer:
    """Mock analyzer for deterministic unit testing of the pipeline."""

    def __init__(self, landmarks: list = None):
        self.landmarks = landmarks

    def analyze_rgb(self, rgb_array: np.ndarray):
        return self.landmarks


def _make_pillow_image(width: int = 300, height: int = 400, color=(150, 150, 150)) -> bytes:
    """Generates a clean in-memory JPEG byte string."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _reset_analyzer():
    """Ensure each test starts with a clean state and restores the default analyzer."""
    yield
    set_pose_analyzer(None)


# ---------------------------------------------------------------------------
# Pure Calculation Tests: Tilt (Shoulder / Hip)
# ---------------------------------------------------------------------------

class TestTiltCalculations:
    def test_level_shoulders_zero_tilt(self):
        """Points at the same y-coordinate produce 0.0 degree tilt."""
        pt_l = {"x": 0.4, "y": 0.3}
        pt_r = {"x": 0.6, "y": 0.3}
        tilt = calculate_tilt_deg(pt_l, pt_r)
        assert tilt == 0.0

    def test_right_shoulder_lower_positive_tilt(self):
        """If right shoulder is lower in image (larger y), tilt is positive."""
        pt_l = {"x": 0.4, "y": 0.3}
        pt_r = {"x": 0.6, "y": 0.35}
        tilt = calculate_tilt_deg(pt_l, pt_r)
        assert tilt is not None
        assert tilt > 0.0
        # arctan(0.05 / 0.2) in degrees ~ 14.04 deg
        expected = round(math.degrees(math.atan2(0.05, 0.2)), 2)
        assert tilt == expected

    def test_right_shoulder_higher_negative_tilt(self):
        """If right shoulder is higher in image (smaller y), tilt is negative."""
        pt_l = {"x": 0.4, "y": 0.35}
        pt_r = {"x": 0.6, "y": 0.3}
        tilt = calculate_tilt_deg(pt_l, pt_r)
        assert tilt is not None
        assert tilt < 0.0

    def test_coinciding_x_produces_vertical_tilt(self):
        """Points with identical x coordinates produce 90 or -90 degrees without ZeroDivisionError."""
        pt_l = {"x": 0.5, "y": 0.3}
        pt_r = {"x": 0.5, "y": 0.4}
        tilt = calculate_tilt_deg(pt_l, pt_r)
        assert tilt == 90.0


# ---------------------------------------------------------------------------
# Pure Calculation Tests: Symmetry Score
# ---------------------------------------------------------------------------

class TestSymmetryCalculations:
    def test_perfect_symmetry_returns_one(self):
        """Symmetric torso and leg segment lengths yield symmetry_score == 1.0."""
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                LEFT_SHOULDER: {"x": 0.35, "y": 0.3, "visibility": 0.9},
                RIGHT_SHOULDER: {"x": 0.65, "y": 0.3, "visibility": 0.9},
                LEFT_HIP: {"x": 0.4, "y": 0.55, "visibility": 0.9},
                RIGHT_HIP: {"x": 0.6, "y": 0.55, "visibility": 0.9},
                LEFT_KNEE: {"x": 0.4, "y": 0.75, "visibility": 0.9},
                RIGHT_KNEE: {"x": 0.6, "y": 0.75, "visibility": 0.9},
                LEFT_ANKLE: {"x": 0.4, "y": 0.95, "visibility": 0.9},
                RIGHT_ANKLE: {"x": 0.6, "y": 0.95, "visibility": 0.9},
            },
        )
        score = calculate_symmetry_score(landmarks)
        assert score is not None
        assert score == 1.0

    def test_asymmetric_torso_reduces_symmetry(self):
        """Asymmetric side lengths yield symmetry_score < 1.0."""
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                LEFT_SHOULDER: {"x": 0.35, "y": 0.3, "visibility": 0.9},
                RIGHT_SHOULDER: {"x": 0.65, "y": 0.3, "visibility": 0.9},
                LEFT_HIP: {"x": 0.4, "y": 0.50, "visibility": 0.9},  # shorter torso
                RIGHT_HIP: {"x": 0.6, "y": 0.60, "visibility": 0.9}, # longer torso
                LEFT_KNEE: {"x": 0.4, "y": 0.75, "visibility": 0.9},
                RIGHT_KNEE: {"x": 0.6, "y": 0.75, "visibility": 0.9},
                LEFT_ANKLE: {"x": 0.4, "y": 0.95, "visibility": 0.9},
                RIGHT_ANKLE: {"x": 0.6, "y": 0.95, "visibility": 0.9},
            },
        )
        score = calculate_symmetry_score(landmarks)
        assert score is not None
        assert 0.0 < score < 1.0

    def test_insufficient_visibility_returns_none(self):
        """If shoulder visibility is below threshold, symmetry returns None."""
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                LEFT_SHOULDER: {"x": 0.35, "y": 0.3, "visibility": 0.2},  # low vis
                RIGHT_SHOULDER: {"x": 0.65, "y": 0.3, "visibility": 0.9},
                LEFT_HIP: {"x": 0.4, "y": 0.55, "visibility": 0.9},
                RIGHT_HIP: {"x": 0.6, "y": 0.55, "visibility": 0.9},
            },
        )
        score = calculate_symmetry_score(landmarks)
        assert score is None


# ---------------------------------------------------------------------------
# Pure Calculation Tests: Torso-to-Leg & Shoulder-to-Hip Ratios
# ---------------------------------------------------------------------------

class TestRatioCalculations:
    def test_torso_to_leg_ratio_calculation(self):
        """Verifies ratio calculation with known vertical heights."""
        # Torso height = |0.5 - 0.2| = 0.30
        # Leg height   = |0.9 - 0.5| = 0.40
        # Ratio        = 0.30 / 0.40 = 0.75
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                LEFT_SHOULDER: {"x": 0.4, "y": 0.2, "visibility": 0.9},
                RIGHT_SHOULDER: {"x": 0.6, "y": 0.2, "visibility": 0.9},
                LEFT_HIP: {"x": 0.45, "y": 0.5, "visibility": 0.9},
                RIGHT_HIP: {"x": 0.55, "y": 0.5, "visibility": 0.9},
                LEFT_ANKLE: {"x": 0.45, "y": 0.9, "visibility": 0.9},
                RIGHT_ANKLE: {"x": 0.55, "y": 0.9, "visibility": 0.9},
            },
        )
        ratio = calculate_torso_to_leg_ratio(landmarks)
        assert ratio is not None
        assert ratio == 0.75

    def test_torso_to_leg_ratio_low_visibility_returns_none(self):
        """Missing ankle visibility causes torso-to-leg ratio to be None."""
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                LEFT_ANKLE: {"x": 0.45, "y": 0.9, "visibility": 0.3},
            },
        )
        ratio = calculate_torso_to_leg_ratio(landmarks)
        assert ratio is None

    def test_shoulder_to_hip_ratio_calculation(self):
        """Verifies shoulder to hip width ratio."""
        # Shoulder width = |0.7 - 0.3| = 0.40
        # Hip width      = |0.6 - 0.4| = 0.20
        # Ratio          = 0.40 / 0.20 = 2.0
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                LEFT_SHOULDER: {"x": 0.3, "y": 0.3, "visibility": 0.9},
                RIGHT_SHOULDER: {"x": 0.7, "y": 0.3, "visibility": 0.9},
                LEFT_HIP: {"x": 0.4, "y": 0.6, "visibility": 0.9},
                RIGHT_HIP: {"x": 0.6, "y": 0.6, "visibility": 0.9},
            },
        )
        ratio = calculate_shoulder_to_hip_ratio(landmarks)
        assert ratio is not None
        assert ratio == 2.0

    def test_shoulder_to_hip_ratio_low_hip_visibility_returns_none(self):
        landmarks = _build_33_landmarks(
            default_vis=0.9,
            overrides={
                RIGHT_HIP: {"x": 0.6, "y": 0.6, "visibility": 0.1},
            },
        )
        ratio = calculate_shoulder_to_hip_ratio(landmarks)
        assert ratio is None


# ---------------------------------------------------------------------------
# Pose Quality Evaluation Tests
# ---------------------------------------------------------------------------

class TestPoseQualityEvaluation:
    def test_good_quality(self):
        assert evaluate_pose_quality(landmarks_visible=30, avg_confidence=0.85) == "good"

    def test_acceptable_quality(self):
        assert evaluate_pose_quality(landmarks_visible=20, avg_confidence=0.7) == "acceptable"

    def test_poor_quality(self):
        assert evaluate_pose_quality(landmarks_visible=14, avg_confidence=0.5) == "poor"

    def test_failed_quality_few_landmarks(self):
        assert evaluate_pose_quality(landmarks_visible=6, avg_confidence=0.8) == "failed"

    def test_failed_quality_low_confidence(self):
        assert evaluate_pose_quality(landmarks_visible=25, avg_confidence=0.25) == "failed"


# ---------------------------------------------------------------------------
# Image Preprocessing & Orientation Tests
# ---------------------------------------------------------------------------

class TestImagePreprocessing:
    def test_valid_image_decoded_to_rgb(self):
        img_bytes = _make_pillow_image(200, 300)
        rgb_arr = decode_image_to_rgb(img_bytes)
        assert isinstance(rgb_arr, np.ndarray)
        assert rgb_arr.shape == (300, 200, 3)

    def test_empty_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            decode_image_to_rgb(b"")

    def test_corrupt_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            decode_image_to_rgb(b"not an image at all")

    def test_exif_orientation_normalised(self):
        """EXIF orientation tag 6 (rotate 90 CW) is transposed before analysis."""
        img = Image.new("RGB", (200, 100), color=(100, 150, 200))
        exif = img.getexif()
        exif[0x0112] = 6  # Orientation: Rotate 90 CW
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)

        rgb_arr = decode_image_to_rgb(buf.getvalue())
        # Transposed 90 degrees rotates 200x100 into 100x200
        assert rgb_arr.shape[0] == 200
        assert rgb_arr.shape[1] == 100


# ---------------------------------------------------------------------------
# Full Pipeline Tests (analyze_body_photo)
# ---------------------------------------------------------------------------

class TestAnalyzeBodyPhotoPipeline:
    def test_pipeline_with_detected_pose(self):
        """Pipeline returns completed status and observational metrics when pose is detected."""
        landmarks = _build_33_landmarks(
            default_vis=0.85,
            overrides={
                LEFT_SHOULDER: {"x": 0.35, "y": 0.25, "visibility": 0.9},
                RIGHT_SHOULDER: {"x": 0.65, "y": 0.25, "visibility": 0.9},
                LEFT_HIP: {"x": 0.40, "y": 0.50, "visibility": 0.9},
                RIGHT_HIP: {"x": 0.60, "y": 0.50, "visibility": 0.9},
                LEFT_KNEE: {"x": 0.40, "y": 0.70, "visibility": 0.9},
                RIGHT_KNEE: {"x": 0.60, "y": 0.70, "visibility": 0.9},
                LEFT_ANKLE: {"x": 0.40, "y": 0.90, "visibility": 0.9},
                RIGHT_ANKLE: {"x": 0.60, "y": 0.90, "visibility": 0.9},
            },
        )
        set_pose_analyzer(MockPoseAnalyzer(landmarks))

        img_bytes = _make_pillow_image()
        result = analyze_body_photo(img_bytes)

        assert isinstance(result, BodyAnalysisResult)
        assert result.status == "completed"
        assert result.pose_detected is True
        assert result.pose_quality == "good"
        assert result.shoulder_tilt_deg == 0.0
        assert result.hip_tilt_deg == 0.0
        assert result.symmetry_score == 1.0
        assert result.torso_to_leg_ratio is not None
        assert result.shoulder_to_hip_ratio is not None
        assert result.raw_landmarks is not None
        assert len(result.raw_landmarks) == 33
        assert result.processing_ms >= 0
        assert result.error_message is None
        assert result.analysis_version == ANALYSIS_VERSION

    def test_pipeline_when_no_pose_detected(self):
        """Pipeline returns failed status and no fabricated metrics when no pose found."""
        set_pose_analyzer(MockPoseAnalyzer(None))

        img_bytes = _make_pillow_image()
        result = analyze_body_photo(img_bytes)

        assert result.status == "failed"
        assert result.pose_detected is False
        assert result.pose_quality == "failed"
        assert result.shoulder_tilt_deg is None
        assert result.hip_tilt_deg is None
        assert result.symmetry_score is None
        assert result.torso_to_leg_ratio is None
        assert result.shoulder_to_hip_ratio is None
        assert result.processing_ms >= 0
        assert "No human pose detected" in (result.error_message or "")

    def test_pipeline_when_pose_quality_failed(self):
        """Pipeline returns failed status when fewer than 10 landmarks are visible."""
        # 5 visible landmarks only
        landmarks = _build_33_landmarks(default_vis=0.1)
        for i in range(5):
            landmarks[i]["visibility"] = 0.9

        set_pose_analyzer(MockPoseAnalyzer(landmarks))

        img_bytes = _make_pillow_image()
        result = analyze_body_photo(img_bytes)

        assert result.status == "failed"
        assert result.pose_detected is False
        assert result.pose_quality == "failed"
        assert result.shoulder_tilt_deg is None
        assert result.symmetry_score is None

    def test_pipeline_with_corrupt_image_bytes(self):
        """Pipeline safely handles corrupt image bytes without raising."""
        result = analyze_body_photo(b"corrupt non-image garbage bytes")
        assert result.status == "failed"
        assert result.pose_detected is False
        assert result.processing_ms >= 0
        assert "Image decoding error" in (result.error_message or "")

    def test_result_to_dict_keys(self):
        """to_dict produces expected keys for database persistence."""
        res = BodyAnalysisResult(
            status="completed",
            pose_detected=True,
            shoulder_tilt_deg=1.5,
            processing_ms=12,
        )
        d = res.to_dict()
        assert d["status"] == "completed"
        assert d["pose_detected"] is True
        assert d["shoulder_tilt_deg"] == 1.5
        assert d["processing_ms"] == 12
        assert d["analysis_version"] == "v1"
        assert d["disclaimer_accepted"] is True
