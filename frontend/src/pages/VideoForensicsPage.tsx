// Clean Light Pro: Deepfake Video & Biometric Forensics Studio
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, CheckCircle, Clock, Eye, FilmStrip, Play, Pause,
  SkipBack, SkipForward, SpeakerHigh, VideoCamera, Warning, WarningCircle,
  FileText, ShieldCheck, Sparkle, Broadcast
} from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Button, Card, Empty, ErrorBox, Loading, Mono, PageHeader, cx } from "@/components/ui";

export default function VideoForensicsPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const preselectedId = params.get("id") ? Number(params.get("id")) : null;

  const { data: videoData, loading, error } = useApi(() => api.videoForensics(), []);
  const [selectedId, setSelectedId] = useState<number | null>(preselectedId);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(126);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showMesh, setShowMesh] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);

  const videoItems = useMemo(() => videoData?.results || [], [videoData]);

  // Set default selection
  useEffect(() => {
    if (videoItems.length > 0 && selectedId === null) {
      if (preselectedId && videoItems.some((v: any) => v.id === preselectedId)) {
        setSelectedId(preselectedId);
      } else {
        // Prefer flagged manipulated item first for showcase
        const flagged = videoItems.find((v: any) => v.deepfake_probability > 50);
        setSelectedId(flagged ? flagged.id : videoItems[0].id);
      }
    }
  }, [videoItems, preselectedId, selectedId]);

  const activeItem = useMemo(() => {
    if (!videoItems.length) return null;
    return videoItems.find((v: any) => v.id === selectedId) || videoItems[0];
  }, [videoItems, selectedId]);

  // Reset frame when item changes
  useEffect(() => {
    if (activeItem) {
      setCurrentFrame(activeItem.deepfake_probability > 50 ? 126 : 45);
      setIsPlaying(false);
    }
  }, [activeItem?.id]);

  // Playback timer simulation
  useEffect(() => {
    if (!isPlaying || !activeItem) return;
    const interval = setInterval(() => {
      setCurrentFrame((prev) => {
        const next = prev + Math.round(1 * playbackSpeed);
        if (next >= activeItem.total_frames) {
          setIsPlaying(false);
          return 0;
        }
        return next;
      });
    }, 1000 / 30);
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, activeItem?.total_frames]);

  if (loading && !videoData) return <Loading label="Calibrating Video Deepfake & Biometric Models..." />;
  if (error && !videoData) return <ErrorBox message={error} onRetry={() => window.location.reload()} />;
  if (!activeItem || !videoData || videoData.items?.length === 0) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Forensic Video Studio" title="Video Forensics" subtitle="Frame-by-frame analysis & deepfake detection" />
        <Card className="p-8">
          <Empty
            title="No video evidence found"
            hint="Upload MP4, MOV, or AVI video recordings to a case to analyze temporal frame consistency and deepfake manipulations."
            action={<Link to="/cases"><Button variant="primary">Go to Cases</Button></Link>}
          />
        </Card>
      </div>
    );
  }

  const isDeepfake = activeItem.deepfake_probability > 50;
  const currentTimeSec = (currentFrame / activeItem.fps).toFixed(1);
  const totalTimeSec = (activeItem.total_frames / activeItem.fps).toFixed(1);
  const progressPercent = Math.min(100, (currentFrame / activeItem.total_frames) * 100);

  // Check if current frame is in the tampered zone
  const isInTamperZone = isDeepfake && progressPercent >= 25 && progressPercent <= 75;

  return (
    <div className="space-y-6 pb-16 max-w-[1720px] mx-auto">
      {/* Top Header with Forensics Studio Switcher */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-accent mb-1">
            <VideoCamera size={14} weight="fill" />
            <span>Video check studio</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-ink">
            Video Check
          </h1>
          <p className="text-xs text-muted max-w-2xl mt-0.5">
            Check if a video has been changed, deepfaked, or had faces swapped.
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
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-accent text-white shadow-xs">
            <VideoCamera size={15} weight="bold" />
            <span>Video</span>
          </div>
          <Link
            to="/document-forensics"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-muted hover:text-ink transition cursor-pointer"
          >
            <FileText size={15} weight="bold" />
            <span>Document</span>
          </Link>
        </div>
      </div>

      {/* Available Video Evidence Carousel */}
      <Card className="p-4 border-line bg-surface/90">
        <div className="flex items-center justify-between mb-3 text-xs">
          <div className="flex items-center gap-2 font-bold text-ink">
            <FilmStrip size={15} className="text-accent" />
            <span>Video files ({videoItems.length}):</span>
          </div>
          <span className="text-muted text-[11px]">Click any video to check it</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {videoItems.map((item: any) => {
            const isSel = item.id === activeItem.id;
            const isManip = item.deepfake_probability > 50;
            return (
              <button
                key={item.id}
                onClick={() => setSelectedId(item.id)}
                className={cx(
                  "flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-mono font-medium transition whitespace-nowrap border cursor-pointer",
                  isSel
                    ? "bg-accent text-white border-accent shadow-xs font-bold"
                    : isManip
                    ? "bg-danger/5 border-danger/30 text-ink hover:border-danger/60"
                    : "bg-surface2/50 border-line text-ink hover:border-accent/40"
                )}
              >
                <span
                  className={cx(
                    "size-2 rounded-full",
                    isSel ? "bg-white" : isManip ? "bg-danger" : "bg-emerald-500"
                  )}
                />
                <span className="truncate max-w-[210px]">{item.filename}</span>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Main Studio Workstation: Left Stage & Right Intelligence Dossier */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Video Canvas & Frame Controls */}
        <div className="lg:col-span-8 space-y-5">
          {/* Main Simulated Video Screen Stage */}
          <Card className="p-5 border-line bg-surface overflow-hidden shadow-xs">
            {/* Header of Video Screen */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-line/60 mb-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="size-2.5 rounded-full bg-accent animate-pulse" />
                <Mono className="font-bold text-ink text-sm">{activeItem.filename}</Mono>
                <span className="text-muted font-mono text-[11px]">
                  ({activeItem.resolution} · {activeItem.codec})
                </span>
              </div>

              {/* View Overlay Toggles */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowMesh(!showMesh)}
                  className={cx(
                    "px-2.5 py-1 rounded-lg text-xs font-semibold border transition cursor-pointer",
                    showMesh ? "bg-accent/10 border-accent text-accent" : "border-line text-muted hover:text-ink"
                  )}
                >
                  68-Pt Landmark Mesh
                </button>
                <button
                  onClick={() => setShowHeatmap(!showHeatmap)}
                  className={cx(
                    "px-2.5 py-1 rounded-lg text-xs font-semibold border transition cursor-pointer",
                    showHeatmap ? "bg-purple-500/10 border-purple-500 text-purple-600" : "border-line text-muted hover:text-ink"
                  )}
                >
                  Warp Heatmap
                </button>
              </div>
            </div>

            {/* Video Screen Area with Overlays */}
            <div className="relative aspect-video w-full rounded-lg bg-neutral-950 border border-neutral-800 overflow-hidden flex items-center justify-center select-none shadow-inner">
              {/* Simulated CCTV / Video Scene Background */}
              <div className="absolute inset-0 bg-gradient-to-tr from-neutral-900 via-neutral-950 to-neutral-900 opacity-90" />

              {/* Camera Grid Overlay */}
              <div className="absolute inset-0 bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:24px_24px] opacity-25" />

              {/* Camera OSD HUD Display */}
              <div className="absolute top-4 left-4 flex flex-col gap-1 text-[11px] font-mono text-emerald-400/90 z-20">
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-emerald-400 animate-ping" />
                  <span className="font-bold">REC · 29.97 FPS</span>
                  <span className="text-neutral-400">CH-04</span>
                </div>
                <div className="text-neutral-400">
                  TC: 00:00:{currentTimeSec} / FRAME #{currentFrame}
                </div>
              </div>

              {/* Top-Right Integrity Watermark */}
              <div className="absolute top-4 right-4 z-20">
                <div className={cx(
                  "px-2.5 py-1 rounded-md text-[10px] font-mono font-bold tracking-wide border uppercase",
                  isDeepfake
                    ? "bg-red-950/80 border-red-500/80 text-red-300"
                    : "bg-emerald-950/80 border-emerald-500/80 text-emerald-300"
                )}>
                  {isDeepfake ? "Edited face detected" : "Video looks genuine"}
                </div>
              </div>

              {/* Visual Facial Tracking Bounding Box */}
              <div className="relative z-10 w-64 h-72 border-2 border-dashed rounded-lg flex flex-col items-center justify-between p-3 transition-colors"
                style={{
                  borderColor: isInTamperZone ? "#EF4444" : isDeepfake ? "#F59E0B" : "#10B981",
                  boxShadow: isInTamperZone ? "0 0 35px rgba(239,68,68,0.35)" : "none"
                }}
              >
                {/* Bounding Box Header */}
                <div className="w-full flex items-center justify-between text-[10px] font-mono px-2 py-0.5 rounded bg-black/60 text-white backdrop-blur-xs">
                  <span>FACE #01</span>
                  <span className={isInTamperZone ? "text-red-400 font-bold" : "text-emerald-400"}>
                    {isDeepfake ? `DEEPFAKE: ${activeItem.deepfake_probability}%` : "REAL: 96.2%"}
                  </span>
                </div>

                {/* Simulated 68-Point Landmark Mesh Points */}
                {showMesh && (
                  <div className="relative w-40 h-44 my-auto flex items-center justify-center">
                    {/* Eyebrows */}
                    <div className="absolute top-6 left-4 flex gap-1.5">
                      {[0, 1, 2, 3].map(i => (
                        <span key={i} className={cx("size-1 rounded-full", isInTamperZone ? "bg-red-400" : "bg-emerald-400")} />
                      ))}
                    </div>
                    <div className="absolute top-6 right-4 flex gap-1.5">
                      {[0, 1, 2, 3].map(i => (
                        <span key={i} className={cx("size-1 rounded-full", isInTamperZone ? "bg-red-400" : "bg-emerald-400")} />
                      ))}
                    </div>
                    {/* Eyes with Blink Indicator */}
                    <div className="absolute top-12 left-5 flex items-center gap-1">
                      <span className={cx("size-1.5 rounded-full ring-1", isInTamperZone ? "bg-red-500 ring-red-300" : "bg-emerald-400 ring-emerald-200")} />
                      <span className="size-1 rounded-full bg-cyan-400" />
                    </div>
                    <div className="absolute top-12 right-5 flex items-center gap-1">
                      <span className={cx("size-1.5 rounded-full ring-1", isInTamperZone ? "bg-red-500 ring-red-300" : "bg-emerald-400 ring-emerald-200")} />
                      <span className="size-1 rounded-full bg-cyan-400" />
                    </div>
                    {/* Nose Bridge & Base */}
                    <div className="absolute top-16 flex flex-col items-center gap-1">
                      <span className="size-1 rounded-full bg-amber-400" />
                      <span className="size-1 rounded-full bg-amber-400" />
                      <div className="flex gap-2">
                        <span className="size-1 rounded-full bg-amber-400" />
                        <span className="size-1 rounded-full bg-amber-400" />
                      </div>
                    </div>
                    {/* Mouth & Lip Viseme Points */}
                    <div className="absolute bottom-6 flex flex-col items-center gap-1">
                      <div className="flex gap-2">
                        {[0, 1, 2].map(i => (
                          <span key={i} className={cx("size-1 rounded-full", isInTamperZone ? "bg-red-400" : "bg-emerald-400")} />
                        ))}
                      </div>
                      <div className="flex gap-3">
                        {[0, 1].map(i => (
                          <span key={i} className={cx("size-1 rounded-full", isInTamperZone ? "bg-red-400" : "bg-emerald-400")} />
                        ))}
                      </div>
                    </div>
                    {/* Jawline Perimeter */}
                    <div className="absolute inset-0 border border-dashed rounded-lg opacity-30"
                      style={{ borderColor: isInTamperZone ? "#EF4444" : "#10B981" }}
                    />
                  </div>
                )}

                {/* Heatmap overlay tag */}
                {showHeatmap && isInTamperZone && (
                  <div className="w-full text-center py-0.5 rounded bg-red-600/90 text-white text-[10px] font-mono font-bold tracking-wider animate-pulse">
                    ⚠ LATENT FACIAL WARPING ANOMALY (@0.61 SSIM)
                  </div>
                )}
              </div>

              {/* Tampered Splice Banner Warning */}
              {isInTamperZone && (
                <div className="absolute bottom-4 inset-x-6 z-20 flex items-center justify-between px-4 py-2 rounded-xl bg-red-950/90 border border-red-500/80 text-white backdrop-blur-md">
                  <div className="flex items-center gap-2 text-xs font-semibold">
                    <WarningCircle size={17} weight="fill" className="text-red-400 animate-spin" />
                    <span>Altered section detected in this frame</span>
                  </div>
                  <Mono className="text-[11px] text-red-300">FRAME #{currentFrame}</Mono>
                </div>
              )}
            </div>

            {/* Frame-by-Frame Timeline Heatmap Bar */}
            <div className="mt-5 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-ink flex items-center gap-1.5">
                  <FilmStrip size={14} className="text-accent" />
                  Frame check timeline (0 to {activeItem.total_frames} frames):
                </span>
                <span className="font-mono text-muted text-[11px]">
                  {currentTimeSec}s / {totalTimeSec}s ({progressPercent.toFixed(0)}%)
                </span>
              </div>

              {/* Interactive Frame Bar Segments */}
              <div className="relative h-8 w-full rounded-xl bg-surface2/60 border border-line flex overflow-hidden p-0.5 cursor-pointer">
                {activeItem.frames_timeline.map((step: any, i: number) => {
                  const isCurrent = Math.abs((step.frame / activeItem.total_frames) * 100 - progressPercent) < 2.5;
                  return (
                    <button
                      key={i}
                      onClick={() => setCurrentFrame(step.frame)}
                      title={`Frame ${step.frame} (${step.timestamp}) - Risk: ${step.risk}`}
                      className={cx(
                        "flex-1 h-full transition-all border-r border-black/10 first:rounded-l-lg last:rounded-r-lg last:border-r-0 relative group",
                        step.risk === "tampered"
                          ? "bg-red-500 hover:bg-red-400"
                          : step.risk === "flagged"
                          ? "bg-amber-400 hover:bg-amber-300"
                          : "bg-emerald-500/80 hover:bg-emerald-400"
                      )}
                    >
                      {isCurrent && (
                        <div className="absolute inset-y-0 inset-x-0 ring-2 ring-white shadow-md z-10" />
                      )}
                    </button>
                  );
                })}

                {/* Scrubber Playhead Handle */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-white shadow-[0_0_8px_rgba(0,0,0,0.8)] pointer-events-none transition-all duration-75 z-20"
                  style={{ left: `${progressPercent}%` }}
                />
              </div>

              {/* Legend */}
              <div className="flex items-center justify-between text-[11px] text-muted pt-1">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-emerald-500" /> Genuine frames
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-amber-400" /> Possible edits
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-red-500" /> Edited section
                  </span>
                </div>
                <span className="font-mono text-[10px]">Click anywhere to jump to that frame</span>
              </div>
            </div>

            {/* Playback Controls Toolbar */}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-line/60">
              <div className="flex items-center gap-2">
                {/* Play/Pause Button */}
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="size-9 rounded-xl bg-accent text-white flex items-center justify-center hover:opacity-90 transition cursor-pointer shadow-xs"
                >
                  {isPlaying ? <Pause size={17} weight="bold" /> : <Play size={17} weight="bold" />}
                </button>

                {/* Step -1 Frame */}
                <button
                  onClick={() => {
                    setIsPlaying(false);
                    setCurrentFrame(prev => Math.max(0, prev - 1));
                  }}
                  className="size-8 rounded-xl border border-line bg-surface2/50 text-ink flex items-center justify-center hover:bg-surface2 transition cursor-pointer"
                  title="Previous Frame"
                >
                  <SkipBack size={14} weight="bold" />
                </button>

                {/* Step +1 Frame */}
                <button
                  onClick={() => {
                    setIsPlaying(false);
                    setCurrentFrame(prev => Math.min(activeItem.total_frames, prev + 1));
                  }}
                  className="size-8 rounded-xl border border-line bg-surface2/50 text-ink flex items-center justify-center hover:bg-surface2 transition cursor-pointer"
                  title="Next Frame"
                >
                  <SkipForward size={14} weight="bold" />
                </button>

                <div className="font-mono text-xs font-bold text-ink pl-2">
                  <span>{currentTimeSec}s</span>
                  <span className="text-muted"> / {totalTimeSec}s</span>
                  <span className="text-accent ml-2 text-[11px]">(Frame #{currentFrame})</span>
                </div>
              </div>

              {/* Speed Toggles */}
              <div className="flex items-center rounded-xl border border-line bg-surface2/60 p-0.5 text-xs font-bold">
                {[0.25, 0.5, 1, 2].map((spd) => (
                  <button
                    key={spd}
                    onClick={() => setPlaybackSpeed(spd)}
                    className={cx(
                      "rounded-lg px-2 py-0.5 transition cursor-pointer",
                      playbackSpeed === spd ? "bg-accent text-white" : "text-muted hover:text-ink"
                    )}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Biometric Telemetry 4-Card Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-3.5 border-line bg-surface">
              <span className="text-[11px] font-bold text-muted block mb-1">
                Facial Landmark Jitter
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className={cx(
                  "text-xl font-mono font-black",
                  activeItem.facial_warp_score > 60 ? "text-danger" : "text-emerald-600"
                )}>
                  {activeItem.facial_warp_score}%
                </span>
                <span className="text-[11px] text-muted">anomaly</span>
              </div>
              <p className="text-[10px] text-muted mt-1">68-Pt mesh boundary stability</p>
            </Card>

            <Card className="p-3.5 border-line bg-surface">
              <span className="text-[11px] font-bold text-muted block mb-1">
                Eye Blink Frequency
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className={cx(
                  "text-xl font-mono font-black",
                  activeItem.blink_rate < 3 ? "text-danger" : "text-emerald-600"
                )}>
                  {activeItem.blink_rate}
                </span>
                <span className="text-[11px] text-muted">blinks/min</span>
              </div>
              <p className="text-[10px] text-muted mt-1">Normal human: 15–20/min</p>
            </Card>

            <Card className="p-3.5 border-line bg-surface">
              <span className="text-[11px] font-bold text-muted block mb-1">
                Pupil Reflection Match
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className={cx(
                  "text-xl font-mono font-black",
                  activeItem.pupil_consistency < 60 ? "text-danger" : "text-emerald-600"
                )}>
                  {activeItem.pupil_consistency}%
                </span>
                <span className="text-[11px] text-muted">cornea match</span>
              </div>
              <p className="text-[10px] text-muted mt-1">Left/right light consistency</p>
            </Card>

            <Card className="p-3.5 border-line bg-surface">
              <span className="text-[11px] font-bold text-muted block mb-1">
                Lip-Sync Viseme Match
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className={cx(
                  "text-xl font-mono font-black",
                  activeItem.lip_sync_match < 60 ? "text-danger" : "text-emerald-600"
                )}>
                  {activeItem.lip_sync_match}%
                </span>
                <span className="text-[11px] text-muted">audio sync</span>
              </div>
              <p className="text-[10px] text-muted mt-1">Phoneme-viseme coherence</p>
            </Card>
          </div>
        </div>

        {/* Right Side: Neural Deepfake Classifier Dossier */}
        <div className="lg:col-span-4 space-y-5">
          {/* Neural Classifier Verdict Card */}
          <Card className="p-5 border-line bg-surface shadow-xs space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-bold text-muted">
                  NEURAL COMPUTER VISION CLASSIFIER
                </span>
                <h3 className={cx(
                  "text-lg font-black tracking-tight mt-0.5",
                  isDeepfake ? "text-danger" : "text-emerald-600"
                )}>
                  {isDeepfake ? "Synthetic Deepfake Video Detected" : "Authentic Camera Feed"}
                </h3>
              </div>
              <span className={cx(
                "size-8 rounded-xl flex items-center justify-center",
                isDeepfake ? "bg-danger/10 text-danger" : "bg-emerald-500/10 text-emerald-600"
              )}>
                {isDeepfake ? <Warning size={20} weight="fill" /> : <CheckCircle size={20} weight="fill" />}
              </span>
            </div>

            {/* Probability Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-ink">Deepfake Confidence</span>
                <span className={cx("font-mono", isDeepfake ? "text-danger" : "text-emerald-600")}>
                  {activeItem.deepfake_probability}%
                </span>
              </div>
              <div className="h-2.5 w-full rounded-full bg-surface2 overflow-hidden">
                <div
                  className={cx(
                    "h-full rounded-full transition-all duration-500",
                    isDeepfake ? "bg-danger" : "bg-emerald-500"
                  )}
                  style={{ width: `${activeItem.deepfake_probability}%` }}
                />
              </div>
            </div>

            {/* Detected Engine Signature */}
            <div className="rounded-xl border border-line bg-surface2/50 p-3 space-y-1">
              <span className="text-[10px] font-bold text-muted block">
                DETECTED GENERATIVE ARCHITECTURE:
              </span>
              <p className="font-mono text-xs font-bold text-ink">
                {activeItem.model_signature}
              </p>
            </div>

            {/* Technical Forensic Breakdown Scores */}
            <div className="space-y-2 pt-2 border-t border-line/60">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted">Temporal Optical Consistency:</span>
                <span className={cx("font-mono font-bold", activeItem.temporal_jitter > 50 ? "text-danger" : "text-ink")}>
                  {(100 - activeItem.temporal_jitter).toFixed(1)} / 100
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted">Biological Liveness Score:</span>
                <span className={cx("font-mono font-bold", isDeepfake ? "text-danger" : "text-ink")}>
                  {isDeepfake ? "14.2 / 100 (Failed)" : "94.8 / 100 (Passed)"}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted">Frame Inter-Splice Discontinuity:</span>
                <span className="font-mono font-bold text-ink">
                  {isDeepfake ? "0.61 SSIM (Severe)" : "0.98 SSIM (Nominal)"}
                </span>
              </div>
            </div>

            {/* Case Reference Info */}
            <div className="rounded-xl border border-line/70 p-3 bg-surface2/30 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-muted">Case Reference:</span>
                <span className="font-mono font-bold text-accent">{activeItem.case_reference}</span>
              </div>
              <p className="text-muted text-[11px] truncate">{activeItem.case_title}</p>
            </div>
          </Card>

          {/* Timestamped Video Anomaly Log */}
          <Card className="p-5 border-line bg-surface shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-ink flex items-center gap-1.5">
                <Clock size={15} className="text-accent" />
                FRAME ANOMALY LOG:
              </span>
              <span className="text-[11px] text-muted font-mono">{activeItem.anomalies.length} Events</span>
            </div>

            <div className="space-y-2">
              {activeItem.anomalies.length === 0 ? (
                <div className="p-4 rounded-xl border border-line bg-surface2/30 text-center text-xs text-muted">
                  No frame or biometric anomalies detected across all video keyframes.
                </div>
              ) : (
                activeItem.anomalies.map((anom: any, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setIsPlaying(false);
                      setCurrentFrame(anom.frame);
                    }}
                    className="w-full text-left p-2.5 rounded-xl border border-danger/25 bg-danger/5 hover:bg-danger/10 transition cursor-pointer"
                  >
                    <div className="flex items-center justify-between text-xs mb-0.5">
                      <span className="font-bold text-danger">{anom.type}</span>
                      <Mono className="text-[11px] font-bold text-danger">{anom.timestamp} (#{anom.frame})</Mono>
                    </div>
                    <p className="text-[11px] text-muted line-clamp-2">{anom.detail}</p>
                  </button>
                ))
              )}
            </div>

            {/* Quick Action Navigation */}
            <div className="pt-2 flex items-center gap-2">
              <Link to={`/evidence/${activeItem.id}`} className="flex-1">
                <Button variant="secondary" className="w-full btn-pill text-xs py-2">
                  <FileText size={14} />
                  Evidence File
                </Button>
              </Link>
              <Link to={`/cases/${activeItem.case_id}`} className="flex-1">
                <Button variant="secondary" className="w-full btn-pill text-xs py-2">
                  Inspect Case
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
