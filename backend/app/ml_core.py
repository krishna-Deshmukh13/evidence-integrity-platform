"""Model-independent parts of the AI checks: score -> finding rules, audio windows/resampling, heatmap overlay.
(No torch import here so these rules are fully unit-tested without the models.)"""
import cv2
import numpy as np

from .analyzers.common import F


# ---------------------------------------------------------------- score -> finding (fixed thresholds)
def ai_image_finding(p: float, check: str = "ai_image", prefix: str = "", where: str = "image") -> F:
    pct = round(p * 100)
    if p >= 0.95:
        return F("ai", check, "high", f"{prefix}AI-generated {where} detected ({pct}%)",
                 f"The AI-image classifier rates the {where} {pct}% likely to be machine-generated.", penalty=52)
    if p >= 0.85:
        return F("ai", check, "high", f"{prefix}Likely AI-generated {where} ({pct}%)",
                 f"The AI-image classifier rates the {where} {pct}% likely to be machine-generated.", penalty=34)
    if p >= 0.65:
        return F("ai", check, "medium", f"{prefix}Possible AI-generated {where} ({pct}%)",
                 f"The AI-image classifier gives {pct}%, which is above the review threshold.", penalty=18)
    if p >= 0.50:
        return F("ai", check, "low", f"{prefix}Borderline AI-image score ({pct}%)",
                 "The classifier is close to undecided; treat as a weak indicator only.", penalty=6)
    return F("ai", check, "info", f"{prefix}AI detector: natural camera content ({pct}%)",
             f"The classifier rates the {where} only {pct}% likely to be generated.")


def face_finding(p, n_faces: int, location=None, prefix: str = "") -> F:
    if n_faces == 0:
        return F("ai", "face_deepfake", "info", f"{prefix}Face check: no faces found")
    pct = round(p * 100)
    if p >= 0.85:
        return F("ai", "face_deepfake", "high", f"{prefix}Face deepfake indicator ({pct}%)",
                 f"The deepfake classifier rates at least one of {n_faces} face(s) {pct}% likely to be "
                 "manipulated or generated.", penalty=30, location=location)
    if p >= 0.65:
        return F("ai", "face_deepfake", "medium", f"{prefix}Possible face manipulation ({pct}%)",
                 f"The deepfake classifier gives {pct}% for the worst of {n_faces} face(s).", penalty=16,
                 location=location)
    return F("ai", "face_deepfake", "info", f"{prefix}Face check: {n_faces} face(s), none flagged (worst {pct}%)")


def voice_finding(scores):
    """scores: synthetic-probability per 4 s window. -> (finding, summary)."""
    if not scores:
        return F("audio", "synthetic_voice", "info", "Synthetic-voice check: audio too short"), {}
    a = np.asarray(scores, float)
    avg, peak = float(a.mean()), float(a.max())
    frac = float((a >= 0.5).mean())
    summ = {"synthetic_avg": round(avg, 3), "synthetic_peak": round(peak, 3)}
    a_, p_ = round(avg * 100), round(peak * 100)
    txt = f"Average {a_}% and peak {p_}% over {len(a)} window(s) of 4 s; {round(frac * 100)}% of windows score 50% or more."
    if avg >= 0.90:
        return F("audio", "synthetic_voice", "high", f"Synthetic voice detected ({a_}%)", txt, penalty=52), summ
    if avg >= 0.75 or frac >= 0.70:
        return F("audio", "synthetic_voice", "high", f"Likely synthetic voice ({a_}%)", txt, penalty=36), summ
    if avg >= 0.50 or frac >= 0.35:
        return F("audio", "synthetic_voice", "medium", f"Possible synthetic voice ({a_}%)", txt, penalty=20), summ
    if peak >= 0.70:
        return F("audio", "synthetic_voice", "low", f"One window looks synthetic (peak {p_}%)", txt, penalty=6), summ
    return F("audio", "synthetic_voice", "info", f"Synthetic-voice check: natural speech (average {a_}%)", txt), summ


# ---------------------------------------------------------------- audio helpers
def fft_resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out or len(x) == 0:
        return x.astype(np.float32)
    n_out = max(1, int(round(len(x) * sr_out / sr_in)))
    X = np.fft.rfft(x.astype(np.float64))
    Y = np.zeros(n_out // 2 + 1, dtype=complex)
    m = min(len(X), len(Y))
    Y[:m] = X[:m]
    return (np.fft.irfft(Y, n_out) * (n_out / len(x))).astype(np.float32)


def windows(x: np.ndarray, sr: int, seconds: float = 4.0, max_windows: int = 60, min_seconds: float = 1.0):
    """-> list of (start_s, end_s, samples). Evenly thinned if the file is long."""
    step = int(seconds * sr)
    out = []
    for a in range(0, len(x), step):
        seg = x[a:a + step]
        if len(seg) >= min_seconds * sr:
            out.append((a / sr, (a + len(seg)) / sr, seg))
    if len(out) > max_windows:
        idx = np.linspace(0, len(out) - 1, max_windows).astype(int)
        out = [out[i] for i in idx]
    return out


# ---------------------------------------------------------------- heatmap
def heat_overlay(bgr: np.ndarray, cam: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    cam = np.asarray(cam, np.float32)
    cam = cam - cam.min()
    cam = cam / (cam.max() + 1e-8)
    cam = cv2.resize(cam, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_CUBIC)
    heat = cv2.applyColorMap((np.clip(cam, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.addWeighted(bgr, 1 - alpha, heat, alpha, 0)
