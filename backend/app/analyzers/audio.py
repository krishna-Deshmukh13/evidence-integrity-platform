"""Audio forensics: digital silence, bandwidth, tool tags, spectrogram (+ synthetic voice from Stage 3)."""
import re
from pathlib import Path

import cv2
import numpy as np

from . import media
from .common import F, noop_progress

TTS = re.compile(r"eleven ?labs|text.to.speech|\btts\b|polly|wavenet|coqui|vall-?e|resemble|murf|speechify|"
                 r"play\.?ht|respeecher|bark|tortoise|piper|neural voice|voice clon|synthes", re.I)
EDITORS = re.compile(r"audacity|audition|premiere|garageband|reaper|ocenaudio|wavepad|sound forge|"
                     r"logic pro|ableton|fl studio|capcut|filmora", re.I)
MIN_SILENCE_S = 0.15


def _runs(mask):
    """Start/end indices of True runs."""
    if not mask.any():
        return []
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def spectrogram_png(x, sr, out: Path):
    n, hop = 1024, 512
    if len(x) < n * 2:
        return
    win = np.hanning(n).astype(np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    mag = np.abs(np.fft.rfft(frames * win, axis=1)).T
    db = 20 * np.log10(mag + 1e-6)
    db = np.clip((db - (db.max() - 90)) / 90, 0, 1)
    img = (np.flipud(db) * 255).astype(np.uint8)
    img = cv2.resize(img, (min(1600, img.shape[1]), 320), interpolation=cv2.INTER_AREA)
    cv2.imencode(".png", cv2.applyColorMap(img, cv2.COLORMAP_INFERNO))[1].tofile(str(out))


def analyze(path: Path, art_dir: Path, progress=noop_progress, prefix: str = ""):
    art_dir.mkdir(parents=True, exist_ok=True)
    if not media.have_ffmpeg():
        raise RuntimeError("ffmpeg / ffprobe not found on PATH. Install ffmpeg and restart the server.")
    findings, details = [], {}
    progress("Reading tags", 5)
    info = media.probe(path)
    tags = media.all_tags(info)
    details["tags"] = tags
    tagtext = " ".join(f"{k}={v}" for k, v in tags.items())
    bad = False
    if TTS.search(tagtext):
        findings.append(F("audio", "tool_tags", "high", "Text-to-speech or voice-cloning tool named in metadata",
                          f"Metadata mentions: {TTS.search(tagtext).group(0)}.", penalty=30,
                          location={"kind": "field", "name": "audio tags"}))
        bad = True
    elif EDITORS.search(tagtext):
        findings.append(F("audio", "tool_tags", "medium", f"Audio editor named in metadata ({EDITORS.search(tagtext).group(0)})",
                          "The file was saved by an editing application.",
                          location={"kind": "field", "name": "audio tags"}))
        bad = True
    if not bad:
        findings.append(F("audio", "tool_tags", "info", "No synthesis or editing tool named in metadata"))

    progress("Decoding audio", 20)
    x, sr = media.decode_mono(path)
    if x is None or len(x) == 0:
        return findings + [F("audio", "decode", "low", "No audio could be decoded")], details
    dur = len(x) / sr
    details.update({"duration": round(dur, 2), "sample_rate": sr})
    # waveform peaks for the viewer
    nb = 500
    edges = np.linspace(0, len(x), nb + 1).astype(int)
    details["waveform"] = [round(float(np.abs(x[a:b]).max()), 3) if b > a else 0.0
                           for a, b in zip(edges[:-1], edges[1:])]

    progress("Digital silence", 40)
    eps = 0.5 / 32768
    runs = [(a, b) for a, b in _runs(np.abs(x) <= eps)
            if (b - a) / sr >= MIN_SILENCE_S and a > 0 and b < len(x)]  # ignore padding at the edges
    details["silences"] = [{"start": round(a / sr, 2), "end": round(b / sr, 2)} for a, b in runs]
    if runs:
        a, b = runs[0]
        findings.append(F("audio", "digital_silence", "medium" if len(runs) < 3 else "high",
                          f"Digital silence: {len(runs)} stretch(es) of exact zero samples",
                          "A real microphone always records some room noise; exact-zero stretches usually mark "
                          "a cut or a generated voice. First at " + f"{a / sr:.2f}s to {b / sr:.2f}s.",
                          penalty=14 if len(runs) < 3 else 26,
                          location={"kind": "time", "start": a / sr, "end": b / sr, "all": details["silences"]}))
    else:
        findings.append(F("audio", "digital_silence", "info", "No digital silence inside the recording"))

    progress("Bandwidth", 55)
    if sr >= 32000 and dur >= 1.0:
        n = 4096
        seg = x[: (len(x) // n) * n].reshape(-1, n) * np.hanning(n).astype(np.float32)
        psd = (np.abs(np.fft.rfft(seg, axis=1)) ** 2).mean(axis=0)
        freqs = np.fft.rfftfreq(n, 1 / sr)
        above = np.where(psd > psd.max() * 1e-8)[0]
        cutoff = float(freqs[above.max()]) if len(above) else 0.0
        details["cutoff_hz"] = round(cutoff)
        if sr >= 40000 and 0 < cutoff < 9000:
            findings.append(F("audio", "bandwidth", "medium", f"Bandwidth limited to about {cutoff / 1000:.1f} kHz",
                              f"The file is stored at {sr / 1000:.1f} kHz but has no content above "
                              f"{cutoff / 1000:.1f} kHz: it was upsampled from a phone call or speech engine.",
                              location={"kind": "field", "name": "audio spectrum"}))
        else:
            findings.append(F("audio", "bandwidth", "info", "Bandwidth is consistent with the sample rate"))
    progress("Spectrogram", 70)
    spectrogram_png(x, sr, art_dir / f"{prefix}spectrogram.png")
    details["layers"] = ["spectrogram"]

    progress("Synthetic voice check", 85)
    try:
        from .. import ml  # Stage 3 adds app/ml.py: check_audio(x, sr) -> (findings, {"windows": [...]})
        fs, extra = ml.check_audio(x, sr)
        findings += fs
        details.update(extra)
    except ImportError:
        findings.append(F("audio", "synthetic_voice", "info", "Synthetic-voice detector not installed",
                          "Install the Stage 3 requirements to enable the AI voice check."))
    return findings, details
