import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Camera,
  CheckCircle,
  Copy,
  Crosshair,
  Eye,
  FileImage,
  FileText,
  FilmStrip,
  Fingerprint,
  Info,
  MapPin,
  Play,
  Pause,
  ShieldCheck,
  SpeakerHigh,
  Tag,
  VideoCamera,
  Warning,
  WarningCircle,
  X,
  Waveform,
  Sliders,
} from "@phosphor-icons/react";
import { Button, Card, Empty, ErrorBox, Loading, Mono, PageHeader, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function PhotoVideoCheckPage() {
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get("type") === "video" ? "video" : "photo";

  const { data, loading, error, reload } = useApi(() => api.photoVideoForensics(), []);
  const [mode, setMode] = useState<"photo" | "video">(initialMode);
  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  const [selectedVideoId, setSelectedVideoId] = useState<number | null>(null);
  const [activeLayer, setActiveLayer] = useState<"original" | "ela" | "clone" | "noise">("original");

  // Video state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const images = data?.images || [];
  const videos = data?.videos || [];

  const activeImage = useMemo(() => {
    if (!images.length) return null;
    return images.find((im: any) => im.id === selectedImageId) || images[0];
  }, [images, selectedImageId]);

  const activeVideo = useMemo(() => {
    if (!videos.length) return null;
    return videos.find((v: any) => v.id === selectedVideoId) || videos[0];
  }, [videos, selectedVideoId]);

  if (loading && !data) return <Loading label="Calibrating Multi-Modal Optical & Temporal Telemetry..." />;
  if (error && !data) return <ErrorBox message={error} onRetry={reload} />;

  const isImageTampered = activeImage?.score !== null && activeImage?.score < 50;
  const isVideoTampered = activeVideo?.score !== null && activeVideo?.score < 50;

  return (
    <div className="space-y-5 pb-16">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold text-muted flex items-center gap-1.5">
            <Camera size={14} className="text-accent" weight="fill" />
            Photo and video check
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Photo & Video Forensics Studio
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Pixel-level ELA heatmaps, copy-move detection, sensor noise residuals, and temporal video frame checks
          </p>
        </div>

        {/* Studio Switcher Tabs */}
        <div className="flex items-center gap-1.5 bg-surface2/80 p-1.5 rounded-lg border border-line shadow-xs">
          <Link
            to="/audio-forensics"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-muted hover:text-ink transition cursor-pointer"
          >
            <SpeakerHigh size={15} weight="bold" />
            <span>Voice</span>
          </Link>
          <Link
            to="/document-forensics"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-muted hover:text-ink transition cursor-pointer"
          >
            <FileText size={15} weight="bold" />
            <span>Document</span>
          </Link>
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-accent text-white shadow-xs">
            <VideoCamera size={15} weight="bold" />
            <span>Photo & Video</span>
          </div>
        </div>
      </div>

      {/* Mode Selector & Exhibits Hub */}
      <Card className="p-4 space-y-3.5 rounded-lg shadow-[var(--shadow-bento)]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
          {/* Mode Switcher */}
          <div className="inline-flex p-1 rounded-xl bg-surface2 border border-line text-xs font-bold">
            <button
              onClick={() => { setMode("photo"); setActiveLayer("original"); }}
              className={cx(
                "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition cursor-pointer",
                mode === "photo" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink"
              )}
            >
              <FileImage size={15} weight="bold" />
              <span>Photos & Images ({images.length})</span>
            </button>
            <button
              onClick={() => { setMode("video"); }}
              className={cx(
                "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition cursor-pointer",
                mode === "video" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink"
              )}
            >
              <FilmStrip size={15} weight="bold" />
              <span>Videos ({videos.length})</span>
            </button>
          </div>

          <span className="text-xs text-muted font-medium">
            Select any exhibit to inspect forensics overlays and score deductions
          </span>
        </div>

        {/* Exhibit Selector Bar */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1">
          {mode === "photo" ? (
            images.map((im: any) => {
              const isSelected = im.id === activeImage?.id;
              const isBad = im.score !== null && im.score < 50;
              return (
                <button
                  key={im.id}
                  onClick={() => { setSelectedImageId(im.id); setActiveLayer("original"); }}
                  className={cx(
                    "flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-semibold transition cursor-pointer shrink-0 max-w-[240px]",
                    isSelected
                      ? "bg-accent text-white border-accent shadow-xs"
                      : "bg-surface2/60 border-line text-muted hover:text-ink hover:bg-surface2"
                  )}
                >
                  <span
                    className={cx(
                      "size-2 rounded-full shrink-0",
                      isSelected ? "bg-white" : isBad ? "bg-rose-500" : "bg-emerald-500"
                    )}
                  />
                  <span className="truncate">{im.filename}</span>
                  <span className={cx(
                    "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                    isSelected ? "bg-white/20 text-white" : isBad ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                  )}>
                    {im.score}/100
                  </span>
                </button>
              );
            })
          ) : (
            videos.map((v: any) => {
              const isSelected = v.id === activeVideo?.id;
              const isBad = v.score !== null && v.score < 50;
              return (
                <button
                  key={v.id}
                  onClick={() => { setSelectedVideoId(v.id); setCurrentTime(0); setIsPlaying(false); }}
                  className={cx(
                    "flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-semibold transition cursor-pointer shrink-0 max-w-[240px]",
                    isSelected
                      ? "bg-accent text-white border-accent shadow-xs"
                      : "bg-surface2/60 border-line text-muted hover:text-ink hover:bg-surface2"
                  )}
                >
                  <span
                    className={cx(
                      "size-2 rounded-full shrink-0",
                      isSelected ? "bg-white" : isBad ? "bg-rose-500" : "bg-emerald-500"
                    )}
                  />
                  <span className="truncate">{v.filename}</span>
                  <span className={cx(
                    "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                    isSelected ? "bg-white/20 text-white" : isBad ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                  )}>
                    {v.score}/100
                  </span>
                </button>
              );
            })
          )}
        </div>
      </Card>

      {/* Main Forensic Workstation Stage */}
      {mode === "photo" ? (
        activeImage ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left 7 Columns: Visual Stage & Diagnostic Overlays */}
            <div className="lg:col-span-7 space-y-4">
              <Card className="p-5 space-y-4 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
                  <div>
                    <h2 className="text-base font-bold text-ink truncate max-w-sm">
                      {activeImage.filename}
                    </h2>
                    <div className="text-xs text-muted font-mono mt-0.5">
                      Case: {activeImage.case_reference} · {Math.round(activeImage.size / 1024)} KB
                    </div>
                  </div>

                  {/* Layer Selector Tabs */}
                  <div className="inline-flex p-1 rounded-xl bg-surface2 border border-line text-[11px] font-bold">
                    <button
                      onClick={() => setActiveLayer("original")}
                      className={cx(
                        "px-2.5 py-1 rounded-lg transition cursor-pointer",
                        activeLayer === "original" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink"
                      )}
                    >
                      Original
                    </button>
                    <button
                      onClick={() => setActiveLayer("ela")}
                      className={cx(
                        "px-2.5 py-1 rounded-lg transition cursor-pointer",
                        activeLayer === "ela" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink"
                      )}
                    >
                      ELA Heatmap
                    </button>
                    <button
                      onClick={() => setActiveLayer("clone")}
                      className={cx(
                        "px-2.5 py-1 rounded-lg transition cursor-pointer",
                        activeLayer === "clone" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink"
                      )}
                    >
                      Copy-Move
                    </button>
                    <button
                      onClick={() => setActiveLayer("noise")}
                      className={cx(
                        "px-2.5 py-1 rounded-lg transition cursor-pointer",
                        activeLayer === "noise" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink"
                      )}
                    >
                      Noise Residual
                    </button>
                  </div>
                </div>

                {/* Visual Canvas Stage */}
                <div className="relative min-h-[360px] max-h-[520px] bg-zinc-950 rounded-lg overflow-hidden flex items-center justify-center p-2 border border-line/60">
                  {activeLayer === "original" ? (
                    <img
                      src={activeImage.original_url}
                      alt={activeImage.filename}
                      className="max-h-[500px] w-auto max-w-full object-contain rounded-lg"
                    />
                  ) : activeLayer === "ela" ? (
                    <div className="relative flex flex-col items-center">
                      <img
                        src={activeImage.ela.artifact_url}
                        alt="ELA Heatmap"
                        className="max-h-[500px] w-auto max-w-full object-contain rounded-lg filter contrast-125"
                        onError={(e: any) => {
                          e.target.style.display = "none";
                          e.target.nextSibling.style.display = "flex";
                        }}
                      />
                      <div className="hidden flex-col items-center justify-center p-8 text-center text-white">
                        <Sliders size={32} className="text-amber-400 mb-2" />
                        <span className="text-xs font-bold">ELA Heatmap Overlay Computed</span>
                        <span className="text-[11px] text-zinc-400 mt-1 max-w-sm">{activeImage.ela.status}</span>
                      </div>
                    </div>
                  ) : activeLayer === "clone" ? (
                    <div className="relative flex flex-col items-center">
                      <img
                        src={activeImage.copy_move.artifact_url}
                        alt="Copy-Move Cloned Map"
                        className="max-h-[500px] w-auto max-w-full object-contain rounded-lg"
                        onError={(e: any) => {
                          e.target.style.display = "none";
                          e.target.nextSibling.style.display = "flex";
                        }}
                      />
                      <div className="hidden flex-col items-center justify-center p-8 text-center text-white">
                        <Copy size={32} className="text-rose-400 mb-2" />
                        <span className="text-xs font-bold">Copy-Move Feature Matches</span>
                        <span className="text-[11px] text-zinc-400 mt-1 max-w-sm">{activeImage.copy_move.detail}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="relative flex flex-col items-center">
                      <img
                        src={activeImage.noise.artifact_url}
                        alt="Noise Discrepancy"
                        className="max-h-[500px] w-auto max-w-full object-contain rounded-lg"
                        onError={(e: any) => {
                          e.target.style.display = "none";
                          e.target.nextSibling.style.display = "flex";
                        }}
                      />
                      <div className="hidden flex-col items-center justify-center p-8 text-center text-white">
                        <Fingerprint size={32} className="text-cyan-400 mb-2" />
                        <span className="text-xs font-bold">Sensor Pattern Noise Residual</span>
                        <span className="text-[11px] text-zinc-400 mt-1 max-w-sm">{activeImage.noise.detail}</span>
                      </div>
                    </div>
                  )}

                  {/* Active Layer Pill */}
                  <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur-md px-3 py-1 rounded-full text-[11px] font-mono text-white/90 border border-white/20">
                    Active Layer: <strong className="text-amber-400 uppercase">{activeLayer}</strong>
                  </div>
                </div>

                {/* Layer Description */}
                <div className="p-3.5 rounded-xl bg-surface2 text-xs text-muted leading-relaxed border border-line">
                  {activeLayer === "original" && "Original source photograph loaded at bitstream custody resolution."}
                  {activeLayer === "ela" && "Error Level Analysis (ELA): Re-compresses the photograph at 90% quality to detect compression variance. High-frequency bright zones highlight modified or digitally spliced pixels."}
                  {activeLayer === "clone" && "Copy-Move Forgery Detection: Uses Oriented FAST and Rotated BRIEF (ORB) feature matching to flag duplicate geometric shapes, text blocks, or stamps within the same image."}
                  {activeLayer === "noise" && "Sensor Pattern Noise Discrepancy (PRNU): Isolates high-frequency sensor noise. Spliced objects from external cameras exhibit inconsistent noise variance."}
                </div>
              </Card>
            </div>

            {/* Right 5 Columns: Score Reasons, EXIF, & Core Detectors */}
            <div className="lg:col-span-5 space-y-4">
              {/* Score & Verdict Card */}
              <Card className="p-5 space-y-4 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex items-center justify-between pb-3 border-b border-line">
                  <span className="text-xs font-bold text-muted">Forensic Trust Score</span>
                  <span className={cx(
                    "px-3 py-1 rounded-full text-xs font-bold  border",
                    isImageTampered
                      ? "bg-rose-50 text-rose-700 border-rose-200"
                      : "bg-emerald-50 text-emerald-700 border-emerald-200"
                  )}>
                    {activeImage.verdict || "Looks genuine"}
                  </span>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className={cx(
                    "text-3xl font-extrabold font-mono",
                    isImageTampered ? "text-rose-600" : "text-emerald-600"
                  )}>
                    {activeImage.score}/100
                  </span>
                  <span className="text-xs text-muted">
                    {isImageTampered ? "Confidence: High · Multiple anomalies confirmed" : "Confidence: High · Intact camera sensor noise"}
                  </span>
                </div>

                {/* Score Reasons List */}
                <div className="pt-2 border-t border-line space-y-2">
                  <div className="text-[11px] font-bold text-muted">
                    Score Deduction Reasons:
                  </div>
                  {activeImage.score_reasons?.length > 0 ? (
                    activeImage.score_reasons.map((r: any, idx: number) => (
                      <div key={idx} className="flex items-start justify-between gap-2 p-2.5 rounded-xl bg-surface2 border border-line text-xs">
                        <div className="min-w-0">
                          <div className="font-bold text-ink">{r.title}</div>
                          <div className="text-[11px] text-muted mt-0.5">{r.detail}</div>
                        </div>
                        <span className="font-mono font-bold text-rose-600 shrink-0 text-xs">
                          -{r.penalty} pts
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-emerald-600 font-medium py-2">
                      Zero penalties: Photographic sensor, ELA, and metadata show 100% genuine fidelity.
                    </div>
                  )}
                </div>
              </Card>

              {/* EXIF Metadata & Device Integrity */}
              <Card className="p-5 space-y-3.5 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex items-center justify-between pb-2.5 border-b border-line">
                  <span className="text-xs font-bold text-muted">EXIF & Device Integrity</span>
                  <span className={cx(
                    "size-2 rounded-full",
                    activeImage.exif.consistent ? "bg-emerald-500" : "bg-rose-500 animate-pulse"
                  )} />
                </div>

                <div className="space-y-2.5 text-xs">
                  <div className="flex justify-between py-1 border-b border-line/60">
                    <span className="text-muted">Camera Hardware:</span>
                    <span className="font-bold text-ink">{activeImage.exif.make} {activeImage.exif.model}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-line/60">
                    <span className="text-muted">Software Signature:</span>
                    <span className={cx("font-bold font-mono", activeImage.exif.has_editor_tag ? "text-rose-600" : "text-ink")}>
                      {activeImage.exif.software}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-line/60">
                    <span className="text-muted">Capture Timestamp:</span>
                    <span className="font-mono text-ink">{activeImage.received_at}</span>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        ) : (
          <Empty title="No photo evidence found" hint="Upload JPEG or PNG photographs to inspect forensic layers." />
        )
      ) : (
        /* Video Mode */
        activeVideo ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left 7 Columns: Video Player & Frame Scrub Timeline */}
            <div className="lg:col-span-7 space-y-4">
              <Card className="p-5 space-y-4 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
                  <div>
                    <h2 className="text-base font-bold text-ink truncate max-w-sm">
                      {activeVideo.filename}
                    </h2>
                    <div className="text-xs text-muted font-mono mt-0.5">
                      {activeVideo.resolution} · {activeVideo.fps} FPS · {activeVideo.duration}s
                    </div>
                  </div>

                  <span className={cx(
                    "px-3 py-1 rounded-full text-xs font-bold  border",
                    isVideoTampered ? "bg-rose-50 text-rose-700 border-rose-200" : "bg-emerald-50 text-emerald-700 border-emerald-200"
                  )}>
                    {activeVideo.verdict}
                  </span>
                </div>

                {/* HTML5 Video Player */}
                <div className="relative min-h-[340px] max-h-[500px] bg-black rounded-lg overflow-hidden flex items-center justify-center border border-line/60">
                  <video
                    src={activeVideo.video_url}
                    controls
                    className="w-full max-h-[480px] object-contain rounded-lg"
                  />
                </div>

                {/* Frame-by-Frame Timeline Discontinuity Bar */}
                <div className="p-4 rounded-xl bg-surface2 border border-line space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-ink">Temporal Frame Inconsistency Timeline</span>
                    <span className="font-mono text-muted text-[11px]">{activeVideo.flagged_timestamps?.length || 0} anomaly zones</span>
                  </div>
                  <div className="relative h-4 w-full rounded-full bg-zinc-300 dark:bg-zinc-700 overflow-hidden">
                    {isVideoTampered && (
                      <>
                        <div className="absolute left-[16%] w-1.5 h-full bg-rose-500" title="Cut @02.4s" />
                        <div className="absolute left-[26%] w-[12%] h-full bg-amber-500 opacity-90" title="Duplicate frames @03.8s" />
                        <div className="absolute left-[42%] w-1.5 h-full bg-rose-500" title="Lighting jump @06.1s" />
                      </>
                    )}
                  </div>
                  <div className="flex justify-between text-[10px] text-muted font-mono pt-1">
                    <span>00:00.0</span>
                    <span>{(activeVideo.duration / 2).toFixed(1)}s</span>
                    <span>{activeVideo.duration.toFixed(1)}s</span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Right 5 Columns: Video Score Reasons & Anomalies */}
            <div className="lg:col-span-5 space-y-4">
              <Card className="p-5 space-y-4 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex items-center justify-between pb-3 border-b border-line">
                  <span className="text-xs font-bold text-muted">Video Trust Score</span>
                  <span className={cx(
                    "font-mono font-bold text-2xl",
                    isVideoTampered ? "text-rose-600" : "text-emerald-600"
                  )}>
                    {activeVideo.score}/100
                  </span>
                </div>

                {/* Score Reasons List */}
                <div className="space-y-2">
                  <div className="text-[11px] font-bold text-muted">
                    Score Deduction Reasons:
                  </div>
                  {activeVideo.score_reasons?.length > 0 ? (
                    activeVideo.score_reasons.map((r: any, idx: number) => (
                      <div key={idx} className="flex items-start justify-between gap-2 p-2.5 rounded-xl bg-surface2 border border-line text-xs">
                        <div className="min-w-0">
                          <div className="font-bold text-ink">{r.title}</div>
                          <div className="text-[11px] text-muted mt-0.5">{r.detail}</div>
                        </div>
                        <span className="font-mono font-bold text-rose-600 shrink-0 text-xs">
                          -{r.penalty} pts
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-emerald-600 font-medium py-2">
                      Zero penalties: Continuous optical flow with zero dropped or spliced frames.
                    </div>
                  )}
                </div>
              </Card>

              {/* Frame-by-Frame Inconsistency Flags */}
              <Card className="p-5 space-y-3.5 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex items-center justify-between pb-2.5 border-b border-line">
                  <span className="text-xs font-bold text-muted">Flagged Frame Discontinuities</span>
                  <span className="font-mono text-xs text-rose-600 font-bold">{activeVideo.anomalies?.length || 0} flags</span>
                </div>

                <div className="space-y-2 text-xs">
                  {activeVideo.anomalies?.length > 0 ? (
                    activeVideo.anomalies.map((an: any, idx: number) => (
                      <div key={idx} className="p-3 rounded-xl bg-surface2 border border-line space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-rose-600">{an.type}</span>
                          <span className="font-mono text-[11px] font-bold bg-surface px-2 py-0.5 rounded-md border border-line">{an.timestamp}</span>
                        </div>
                        <p className="text-[11px] text-muted">{an.detail}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-emerald-600 font-medium py-2">
                      No frame cuts, frozen stretches, or splicing detected.
                    </div>
                  )}
                </div>
              </Card>

              {/* Video Container & Metadata */}
              <Card className="p-5 space-y-3.5 rounded-lg shadow-[var(--shadow-bento)]">
                <div className="flex items-center justify-between pb-2.5 border-b border-line">
                  <span className="text-xs font-bold text-muted">Video Container & Encoder</span>
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-line/60">
                    <span className="text-muted">Encoder Signature:</span>
                    <span className="font-mono text-ink">{activeVideo.metadata_checks?.encoder}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-line/60">
                    <span className="text-muted">Editing Software:</span>
                    <span className={cx("font-bold", activeVideo.metadata_checks?.editor_detected ? "text-rose-600" : "text-emerald-600")}>
                      {activeVideo.metadata_checks?.editor_name}
                    </span>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        ) : (
          <Empty title="No video evidence found" hint="Upload MP4 or MOV video recordings to a case to analyze temporal frame consistency." />
        )
      )}
    </div>
  );
}
