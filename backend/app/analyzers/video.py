"""Video forensics: container tags, hard cuts, frozen frames, sampled frames, audio track."""
import re
from pathlib import Path

import cv2
import numpy as np

from . import audio as audio_mod
from . import media
from .common import F, noop_progress

VIDEO_EDITORS = re.compile(r"capcut|premiere|final cut|davinci|vegas|filmora|kdenlive|imovie|camtasia|shotcut|"
                           r"openshot|inshot|vn video|movavi|lightworks|after effects|handbrake", re.I)
MAX_FRAMES = 4000
N_SAMPLES = 20


def _tags(info):
    tags = media.all_tags(info)
    findings = []
    text = " ".join(f"{k}={v}" for k, v in tags.items())
    bad = 0
    m = VIDEO_EDITORS.search(text)
    if m:
        findings.append(F("metadata", "video_editor", "medium", f"Saved by video editing software ({m.group(0)})",
                          "The container tags name an editing application.",
                          location={"kind": "field", "name": "container tags"}))
        bad += 1
    if re.search(r"lavf|ffmpeg|libx264", text, re.I):
        findings.append(F("metadata", "reencoded", "low", "Re-encoded with ffmpeg",
                          "The encoder tag shows the file was re-encoded after recording.",
                          location={"kind": "field", "name": "encoder tag"}))
        bad += 1
    has_time = any("creation_time" in k for k in tags)
    has_device = any(k in tags for k in ("com.apple.quicktime.make", "com.apple.quicktime.model", "make", "model"))
    if not has_time and not has_device:
        findings.append(F("metadata", "no_origin", "low", "No creation time or device information",
                          "Cameras and phones normally record when and on what device the clip was made.",
                          location={"kind": "field", "name": "container tags"}))
        bad += 1
    if not bad:
        findings.append(F("metadata", "container_tags", "info", "Container tags look consistent"))
    return findings, tags


def analyze(path: Path, art_dir: Path, progress=noop_progress):
    art_dir.mkdir(parents=True, exist_ok=True)
    if not media.have_ffmpeg():
        raise RuntimeError("ffmpeg / ffprobe not found on PATH. Install ffmpeg and restart the server.")
    progress("Reading container tags", 5)
    info = media.probe(path)
    findings, tags = _tags(info)
    vs = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    details = {"tags": tags, "has_audio": any(s.get("codec_type") == "audio" for s in info["streams"])}
    if not vs:
        return findings + [F("container", "no_video", "low", "No video stream found")], details
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    details.update({"fps": round(fps, 2), "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})
    progress("Measuring frame changes", 15)
    prev, diffs = None, []
    while len(diffs) < MAX_FRAMES:
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (64, 36), interpolation=cv2.INTER_AREA).astype(np.float32)
        if prev is not None:
            diffs.append(float(np.abs(g - prev).mean()))
        prev = g
    cap.release()
    d = np.array(diffs, np.float32)
    duration = (len(d) + 1) / fps
    details["duration"] = round(max(duration, float(info["format"].get("duration", 0) or 0)), 2)
    cuts, frozen = [], []
    if len(d) >= 10:
        med = float(np.median(d))
        mad = float(np.median(np.abs(d - med))) * 1.4826 + 0.3
        z = (d - med) / mad
        cuts = [int(i) + 1 for i in np.where((z > 12) & (d > 12))[0]]
        min_run = max(2, int(0.5 * fps))
        for a, b in audio_mod._runs(d < 0.05):
            if b - a >= min_run:
                frozen.append((int(a), int(b)))
    details["cuts"] = [round(i / fps, 2) for i in cuts]
    details["frozen"] = [{"start": round(a / fps, 2), "end": round((b + 1) / fps, 2)} for a, b in frozen]
    k = max(1, len(d) // 300)
    details["timeline"] = [round(float(d[i:i + k].max()), 2) for i in range(0, len(d), k)] if len(d) else []
    if cuts:
        t = cuts[0] / fps
        findings.append(F("container", "hard_cuts", "medium", f"Hard cut(s) in the footage ({len(cuts)})",
                          f"The picture changes abruptly at {', '.join(f'{c / fps:.1f}s' for c in cuts[:4])}. "
                          "Normal in an edited film, suspicious in one continuous recording.", penalty=14,
                          location={"kind": "time", "start": t, "end": t, "all": details["cuts"]}))
    else:
        findings.append(F("container", "hard_cuts", "info", "No hard cuts detected"))
    if frozen:
        a, b = frozen[0]
        findings.append(F("container", "frozen_frames", "low", f"Frozen stretch(es) of identical frames ({len(frozen)})",
                          f"Identical frames from {a / fps:.1f}s to {(b + 1) / fps:.1f}s can hide removed footage.",
                          penalty=6, location={"kind": "time", "start": a / fps, "end": (b + 1) / fps,
                                               "all": details["frozen"]}))
    else:
        findings.append(F("container", "frozen_frames", "info", "No frozen frames"))

    progress("Sampling frames", 55)
    cap = cv2.VideoCapture(str(path))
    n_frames = total if total > 0 else len(d) + 1
    idxs = sorted({int(i) for i in np.linspace(0, max(n_frames - 2, 0), min(N_SAMPLES, max(n_frames, 1)))})
    frames, times, thumbs = [], [], []
    for j, i in enumerate(idxs):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        sc = min(1.0, 640 / max(w, h))
        big = cv2.resize(fr, (int(w * sc), int(h * sc))) if sc < 1 else fr
        frames.append(big)
        times.append(i / fps)
        name = f"frame_{j:02d}.jpg"
        tw = 240
        cv2.imwrite(str(art_dir / name), cv2.resize(fr, (tw, max(1, int(h * tw / w)))))
        thumbs.append({"t": round(i / fps, 2), "file": name, "ai": None})
    cap.release()
    details["frames"] = thumbs
    progress("AI and face check per frame", 70)
    try:
        from .. import ml  # Stage 3: check_frames(frames, times, art_dir) -> (findings, [score per frame])
        fs, scores = ml.check_frames(frames, times, art_dir)
        findings += fs
        for t_, s_ in zip(thumbs, scores):
            t_["ai"] = s_
    except ImportError:
        findings.append(F("ai", "ai_video", "info", "AI / deepfake frame check not installed",
                          "Install the Stage 3 requirements to enable it."))
    if details["has_audio"]:
        progress("Audio track", 85)
        wav = art_dir / "_track.wav"
        try:
            if media.extract_audio_wav(path, wav):
                af, ad = audio_mod.analyze(wav, art_dir, prefix="audio_")
                for f in af:
                    f.title = "Audio track: " + f.title
                findings += af
                details["audio"] = ad
        finally:
            wav.unlink(missing_ok=True)
    details["layers"] = ["frames"] + (["heatmap"] if (art_dir / "ai_heatmap.png").exists() else [])
    return findings, details
