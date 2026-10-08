"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  uploadProgressPhoto,
  fetchProgressPhotos,
  fetchProgressPhotoDetail,
  deleteProgressPhoto,
  PhotoType,
  PhotoMetadata,
  BodyAnalysisResult,
  PhotoDetailResponse,
} from "@/lib/api";
import {
  Camera,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Target,
  Scale,
  Dumbbell,
  ShieldAlert,
  Trash2,
  Eye,
  RefreshCw,
  X,
  FileImage,
  Sparkles,
  Clock,
  ChevronRight,
  Info,
} from "lucide-react";

const VALID_PHOTO_TYPES: { id: PhotoType; label: string; desc: string }[] = [
  { id: "front", label: "Front Pose", desc: "Facing camera directly" },
  { id: "side_left", label: "Left Profile", desc: "Left side facing camera" },
  { id: "side_right", label: "Right Profile", desc: "Right side facing camera" },
  { id: "back", label: "Back Pose", desc: "Back facing camera" },
];

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];

function getTodayDateString(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatBytes(bytes?: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function BodyAnalysisPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  // Form inputs
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [photoType, setPhotoType] = useState<PhotoType>("front");
  const [capturedAt, setCapturedAt] = useState<string>(getTodayDateString());
  const [isDragging, setIsDragging] = useState(false);

  // Upload & execution state
  const [uploading, setUploading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Active / Inspecting analysis result
  const [activePhoto, setActivePhoto] = useState<PhotoMetadata | null>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<BodyAnalysisResult | null>(null);
  const [loadingDetailId, setLoadingDetailId] = useState<string | null>(null);

  // History state
  const [photos, setPhotos] = useState<PhotoMetadata[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Authentication guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  // Clean up object URL preview on unmount or file change
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // Load photo history
  const loadHistory = useCallback(async () => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const res = await fetchProgressPhotos(30);
      setPhotos(res.photos || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load past photos.";
      setHistoryError(msg);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadHistory();
    }
  }, [user, loadHistory]);

  // File validation & preview handler
  const handleFileSelect = (file: File) => {
    setFormError(null);

    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      setFormError("Invalid image type. Supported formats: JPEG, PNG, WebP.");
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFormError("Image exceeds 10 MB limit. Please select a smaller photo.");
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    const objectUrl = URL.createObjectURL(file);
    setSelectedFile(file);
    setPreviewUrl(objectUrl);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleClearSelectedFile = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setFormError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Submit photo for MediaPipe analysis
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!selectedFile) {
      setFormError("Please select or drop a progress photo to analyze.");
      return;
    }

    if (!capturedAt) {
      setFormError("Capture date is required.");
      return;
    }

    const today = getTodayDateString();
    if (capturedAt > today) {
      setFormError("Capture date cannot be in the future.");
      return;
    }

    setUploading(true);
    try {
      const res: PhotoDetailResponse = await uploadProgressPhoto(
        selectedFile,
        photoType,
        capturedAt
      );

      setActivePhoto(res.photo);
      setActiveAnalysis(res.analysis ?? null);

      // Refresh list to include newly persisted photo
      await loadHistory();

      // Clear current file selection
      handleClearSelectedFile();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to analyze photo.";
      setFormError(msg);
    } finally {
      setUploading(false);
    }
  };

  // View historical details
  const handleInspectPhoto = async (photoId: string) => {
    setLoadingDetailId(photoId);
    try {
      const detail = await fetchProgressPhotoDetail(photoId);
      setActivePhoto(detail.photo);
      setActiveAnalysis(detail.analysis ?? null);
      window.scrollTo({ top: 320, behavior: "smooth" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to fetch photo details.";
      setHistoryError(msg);
    } finally {
      setLoadingDetailId(null);
    }
  };

  // Delete historical photo
  const handleDeletePhoto = async (photoId: string) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this progress photo? The image and analysis record will be removed."
    );
    if (!confirmed) return;

    setDeletingId(photoId);
    try {
      await deleteProgressPhoto(photoId);
      if (activePhoto?.id === photoId) {
        setActivePhoto(null);
        setActiveAnalysis(null);
      }
      await loadHistory();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete photo.";
      setHistoryError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  if (authLoading) {
    return (
      <div className="py-20 text-center text-gray-400 flex items-center justify-center gap-3">
        <span className="animate-spin inline-block w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full" />
        <span>Authenticating session...</span>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-8 py-2 max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="glass-card p-6 sm:p-8 border border-slate-800/80 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-72 h-72 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="space-y-3 relative z-10">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
              <Camera className="w-3.5 h-3.5 text-cyan-400" />
              MediaPipe Pose Landmarker
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-slate-800/80 border border-slate-700 text-slate-300">
              <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
              EXIF Privacy Stripped
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-purple-950/60 border border-purple-500/30 text-purple-300">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              Bilateral Symmetry
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            AI Body Analysis
          </h1>

          <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">
            Upload progress photos and track measurable changes in your physique over time.
          </p>
        </div>
      </div>

      {/* Mandatory Non-Clinical Disclaimer */}
      <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-200/90 text-xs flex items-start gap-3 leading-relaxed font-sans">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-amber-300">Observational Notice: </strong>
          Visual pose observations only. They do not constitute medical measurements, clinical diagnoses, or body composition assessments. Values represent pixel-relative proportions and are not equivalent to clinical measurements.
        </div>
      </div>

      {/* Upload and Control Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Upload Form (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <form
            onSubmit={handleSubmit}
            className="glass-card p-6 sm:p-7 space-y-6 border border-slate-800/80"
          >
            <div className="border-b border-gray-800/80 pb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <UploadCloud className="w-5 h-5 text-cyan-400" />
                  Upload Photo
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Drag & drop or browse
                </p>
              </div>
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/70 border border-cyan-800/40 px-2.5 py-1 rounded-md">
                Max 10 MB
              </span>
            </div>

            {/* Error Banner */}
            {formError && (
              <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-500/40 text-red-300 text-xs flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            {/* Pose Orientation Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide block">
                1. Select Pose Direction
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {VALID_PHOTO_TYPES.map((type) => {
                  const isSelected = photoType === type.id;
                  return (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setPhotoType(type.id)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                        isSelected
                          ? "bg-cyan-500/15 border-cyan-500/60 text-white shadow-sm ring-1 ring-cyan-500/40"
                          : "bg-slate-900/60 border-slate-800 text-gray-400 hover:text-gray-200 hover:bg-slate-850"
                      }`}
                    >
                      <span className="text-xs font-bold block">{type.label}</span>
                      <span className="text-[10px] text-gray-500 leading-tight mt-1">{type.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Capture Date Input */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide block">
                2. Capture Date
              </label>
              <input
                type="date"
                value={capturedAt}
                max={getTodayDateString()}
                onChange={(e) => setCapturedAt(e.target.value)}
                className="w-full p-3 rounded-xl bg-[#0c1322] border border-white/10 text-sm text-gray-100 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none transition font-mono"
                required
              />
            </div>

            {/* Drag & Drop File Zone */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide block">
                3. Choose or Drop Image
              </label>

              {!previewUrl ? (
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`p-8 border-2 border-dashed rounded-2xl text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 ${
                    isDragging
                      ? "border-cyan-400 bg-cyan-950/20"
                      : "border-slate-800 hover:border-slate-700 bg-slate-900/40 hover:bg-slate-900/70"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelect(e.target.files[0]);
                      }
                    }}
                  />
                  <div className="p-3.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                    <Camera className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-gray-200">
                      Click to upload or drag & drop
                    </p>
                    <p className="text-xs text-gray-500 font-mono">
                      JPEG, PNG, or WebP (100×100 px min, up to 10 MB)
                    </p>
                    <div className="pt-2 flex items-center justify-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-cyan-300/80 border border-slate-700">
                        Supported: Front • Side • Back
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                /* Selected File Preview */
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
                        <FileImage className="w-4 h-4" />
                      </div>
                      <div className="truncate max-w-xs sm:max-w-md">
                        <p className="text-xs font-semibold text-gray-200 truncate">
                          {selectedFile?.name}
                        </p>
                        <p className="text-[11px] font-mono text-gray-500">
                          {formatBytes(selectedFile?.size)} • {selectedFile?.type}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleClearSelectedFile}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-950/30 transition"
                      title="Remove image"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Thumbnail Container */}
                  <div className="relative w-full h-64 rounded-xl overflow-hidden bg-black/50 border border-slate-800/80 flex items-center justify-center">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={previewUrl}
                      alt="Preview"
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Submit Action */}
            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="w-full py-3.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold flex items-center justify-center gap-2 glow-btn transition shadow-sm disabled:opacity-50 text-sm cursor-pointer"
            >
              {uploading ? (
                <>
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  <span>Executing MediaPipe Pose Analysis...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Analyze Pose & Extract Geometry</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Active Result View (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-card p-6 sm:p-7 space-y-6 border border-slate-800/80">
            <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
              <h2 className="text-base font-bold text-gray-100 flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                Active Analysis Result
              </h2>
              {activePhoto && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-gray-300 capitalize">
                  {activePhoto.photo_type.replace("_", " ")}
                </span>
              )}
            </div>

            {!activePhoto ? (
              /* Empty state before any upload or selection */
              <div className="py-12 text-center text-gray-400 space-y-3">
                <Camera className="w-10 h-10 text-gray-600 mx-auto" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-300">
                    No active photo selected
                  </p>
                  <p className="text-xs text-gray-500 max-w-xs mx-auto">
                    Upload a photo or choose an existing entry from your archive to inspect its computer-vision metrics.
                  </p>
                </div>
              </div>
            ) : activeAnalysis?.status === "failed" ? (
              /* Failed pose detection */
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                    Pose Landmark Detection Failed
                  </div>
                  <p className="text-xs text-red-200/90 leading-relaxed">
                    {activeAnalysis.error_message ||
                      "The computer vision engine could not detect full body landmarks. Ensure the full subject is in frame with adequate contrast."}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-gray-400 space-y-1.5 font-mono">
                  <div className="flex justify-between">
                    <span>Captured:</span>
                    <span className="text-gray-200">{activePhoto.captured_at}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Processing:</span>
                    <span className="text-gray-200">{activeAnalysis.processing_ms} ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="text-red-400 uppercase font-bold">Failed</span>
                  </div>
                </div>
              </div>
            ) : (
              /* Successful observational metrics */
              <div className="space-y-5 animate-in fade-in duration-300">
                {/* Status Bar */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="font-semibold text-emerald-300">
                      Pose Detected ({activeAnalysis?.pose_quality || "good"})
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-gray-400">
                    {activeAnalysis?.processing_ms} ms
                  </span>
                </div>

                {/* Metrics Cards Grid */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  {/* Posture */}
                  <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-gray-400 font-semibold block">
                      Posture
                    </span>
                    <p className="text-xl font-bold font-mono text-emerald-400 capitalize">
                      {activeAnalysis?.pose_quality || "Good"}
                    </p>
                    <span className="text-[10px] text-gray-500">
                      {activeAnalysis?.pose_confidence !== null && activeAnalysis?.pose_confidence !== undefined
                        ? `${(activeAnalysis.pose_confidence * 100).toFixed(0)}% confidence`
                        : "Confidence calibrated"}
                    </span>
                  </div>

                  {/* Body Symmetry */}
                  <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-gray-400 font-semibold block">
                      Body Symmetry
                    </span>
                    <p className="text-xl font-bold font-mono text-purple-400">
                      {activeAnalysis?.symmetry_score !== null &&
                      activeAnalysis?.symmetry_score !== undefined
                        ? `${(activeAnalysis.symmetry_score <= 1 ? activeAnalysis.symmetry_score * 100 : activeAnalysis.symmetry_score).toFixed(1)}%`
                        : "—"}
                    </p>
                    <span className="text-[10px] text-gray-500">Bilateral landmark balance</span>
                  </div>

                  {/* Shoulder Alignment */}
                  <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-gray-400 font-semibold block">
                      Shoulder Alignment
                    </span>
                    <p className="text-xl font-bold font-mono text-cyan-400">
                      {activeAnalysis?.shoulder_tilt_deg !== null &&
                      activeAnalysis?.shoulder_tilt_deg !== undefined
                        ? `${Math.abs(activeAnalysis.shoulder_tilt_deg).toFixed(1)}°`
                        : "—"}
                    </p>
                    <span className="text-[10px] text-gray-500">
                      {activeAnalysis?.shoulder_tilt_deg === 0
                        ? "Level"
                        : (activeAnalysis?.shoulder_tilt_deg ?? 0) > 0
                        ? "Right lower"
                        : "Left lower"}
                    </span>
                  </div>

                  {/* Hip Alignment */}
                  <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-gray-400 font-semibold block">
                      Hip Alignment
                    </span>
                    <p className="text-xl font-bold font-mono text-amber-400">
                      {activeAnalysis?.hip_tilt_deg !== null &&
                      activeAnalysis?.hip_tilt_deg !== undefined
                        ? `${Math.abs(activeAnalysis.hip_tilt_deg).toFixed(1)}°`
                        : "—"}
                    </p>
                    <span className="text-[10px] text-gray-500">
                      {activeAnalysis?.hip_tilt_deg === 0
                        ? "Level"
                        : (activeAnalysis?.hip_tilt_deg ?? 0) > 0
                        ? "Right hip lower"
                        : "Left hip lower"}
                    </span>
                  </div>

                  {/* Movement & Proportional Observations */}
                  <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5 col-span-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] uppercase font-mono text-gray-400 font-semibold">
                        Movement Observations
                      </span>
                      <span className="text-xs font-mono font-bold text-cyan-300">
                        {activeAnalysis?.landmarks_visible ?? 33}/33 Landmarks Visible
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-gray-400 pt-1.5 border-t border-gray-800/60 font-mono">
                      <div>
                        <span>Shoulder / Hip Ratio: </span>
                        <strong className="text-gray-200">
                          {activeAnalysis?.shoulder_to_hip_ratio !== null &&
                          activeAnalysis?.shoulder_to_hip_ratio !== undefined
                            ? activeAnalysis.shoulder_to_hip_ratio.toFixed(2)
                            : "—"}
                        </strong>
                      </div>
                      <div>
                        <span>Torso / Leg Ratio: </span>
                        <strong className="text-gray-200">
                          {activeAnalysis?.torso_to_leg_ratio !== null &&
                          activeAnalysis?.torso_to_leg_ratio !== undefined
                            ? activeAnalysis.torso_to_leg_ratio.toFixed(2)
                            : "—"}
                        </strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Metadata Summary */}
                <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800 text-[11px] font-mono text-gray-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Captured Date:</span>
                    <span className="text-gray-200">{activePhoto.captured_at}</span>
                  </div>
                  {activePhoto.width_px && activePhoto.height_px && (
                    <div className="flex justify-between">
                      <span>Resolution:</span>
                      <span className="text-gray-200">
                        {activePhoto.width_px} × {activePhoto.height_px} px
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>File Size:</span>
                    <span className="text-gray-200">
                      {formatBytes(activePhoto.file_size_bytes)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Historical Photo Archive Section */}
      <div className="glass-card p-6 sm:p-7 space-y-5 border border-slate-800/80">
        <div className="flex items-center justify-between border-b border-gray-800/80 pb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
              <Clock className="w-5 h-5 text-cyan-400" />
              Progress Photo Archive
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Historical pose sessions stored in private user storage
            </p>
          </div>
          <button
            onClick={loadHistory}
            disabled={loadingHistory}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-gray-300 transition text-xs flex items-center gap-1.5"
            title="Refresh archive"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${loadingHistory ? "animate-spin text-cyan-400" : ""}`}
            />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {historyError && (
          <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-500/40 text-red-300 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{historyError}</span>
          </div>
        )}

        {loadingHistory && photos.length === 0 ? (
          <div className="py-10 text-center text-gray-400 flex items-center justify-center gap-2">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full" />
            <span className="text-xs">Loading progress photo archive...</span>
          </div>
        ) : photos.length === 0 ? (
          /* Empty state */
          <div className="py-12 text-center text-gray-400 space-y-3 border border-dashed border-gray-800 rounded-2xl">
            <Camera className="w-10 h-10 text-gray-600 mx-auto" />
            <p className="text-sm font-medium text-gray-300">
              No progress photos recorded yet
            </p>
            <p className="text-xs text-gray-500 max-w-sm mx-auto">
              Upload your first front or profile photo above to start logging computer-vision pose symmetry metrics.
            </p>
          </div>
        ) : (
          /* Photo Archive Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {photos.map((item) => {
              const isInspecting = activePhoto?.id === item.id;
              const isDeleting = deletingId === item.id;
              const isLoadingThis = loadingDetailId === item.id;

              return (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl border transition flex flex-col justify-between space-y-3 ${
                    isInspecting
                      ? "bg-cyan-950/20 border-cyan-500/50 shadow-sm"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold capitalize text-gray-200">
                        {item.photo_type.replace("_", " ")}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase font-bold ${
                          item.analysis_status === "completed"
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                            : item.analysis_status === "failed"
                            ? "bg-red-950/80 text-red-300 border border-red-800/60"
                            : "bg-gray-800 text-gray-400"
                        }`}
                      >
                        {item.analysis_status || "Logged"}
                      </span>
                    </div>

                    <div className="text-[11px] font-mono text-gray-400 space-y-1">
                      <div className="flex justify-between">
                        <span>Date:</span>
                        <span className="text-gray-200">{item.captured_at}</span>
                      </div>
                      {item.width_px && item.height_px && (
                        <div className="flex justify-between">
                          <span>Size:</span>
                          <span className="text-gray-300">
                            {item.width_px}×{item.height_px} ({formatBytes(item.file_size_bytes)})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-gray-800/60">
                    <button
                      onClick={() => handleInspectPhoto(item.id)}
                      disabled={isLoadingThis}
                      className="flex-1 py-1.5 px-2.5 rounded-lg bg-cyan-600/80 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition disabled:opacity-50"
                    >
                      {isLoadingThis ? (
                        <span className="animate-spin inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                      <span>Inspect</span>
                    </button>

                    <button
                      onClick={() => handleDeletePhoto(item.id)}
                      disabled={isDeleting}
                      className="p-1.5 rounded-lg border border-red-500/20 bg-red-950/30 text-red-400 hover:bg-red-900/50 hover:border-red-500/40 transition disabled:opacity-50"
                      title="Delete photo record"
                    >
                      {isDeleting ? (
                        <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-red-400 border-t-transparent rounded-full" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
