"""Pretrained detectors (CPU): AI-generated image (SwinV2), face deepfake (ViT), synthetic voice (wav2vec2).
Importing this module raises ImportError if torch / transformers are not installed; the analyzers catch that
and record "detector not installed". If a model cannot be loaded (e.g. first run without internet) the check
records an info finding instead of failing the whole analysis."""
import re
import threading
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import (AutoFeatureExtractor, AutoImageProcessor, AutoModelForAudioClassification,
                          AutoModelForImageClassification)

from . import ml_core
from .analyzers.common import F

MODELS = {
    "image": "haywoodsloan/ai-image-detector-deploy",        # SwinV2
    "face": "prithivMLmods/Deep-Fake-Detector-v2-Model",     # ViT
    "audio": "mo-thecreator/Deepfake-audio-detection",       # wav2vec2
}
FAKE = re.compile(r"\b(ai|artificial|fake|deepfake|synthetic|spoof|generated)\b")
REAL = re.compile(r"\b(real|realism|human|natural|authentic|bonafide|genuine)\b")
_cache, _lock = {}, threading.RLock()
torch.set_num_threads(max(1, min(8, (torch.get_num_threads() or 4))))


def _fake_index(model) -> int:
    labels = {int(i): str(l).lower() for i, l in model.config.id2label.items()}
    for i, l in labels.items():
        if FAKE.search(l):
            return i
    for i, l in labels.items():
        if REAL.search(l) and len(labels) == 2:
            return [j for j in labels if j != i][0]
    return max(labels)


def _load(kind: str):
    with _lock:
        if kind not in _cache:
            name = MODELS[kind]
            if kind == "audio":
                proc = AutoFeatureExtractor.from_pretrained(name)
                model = AutoModelForAudioClassification.from_pretrained(name)
            else:
                proc = AutoImageProcessor.from_pretrained(name)
                model = AutoModelForImageClassification.from_pretrained(name)
            model.eval()
            _cache[kind] = (proc, model, _fake_index(model))
        return _cache[kind]


def _pil(bgr):
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def p_fake(kind: str, bgr) -> float:
    proc, model, fi = _load(kind)
    with _lock, torch.no_grad():
        logits = model(**proc(images=_pil(bgr), return_tensors="pt")).logits
    return float(torch.softmax(logits, -1)[0, fi])


def _target_layer(model):
    for get in (lambda m: m.swinv2.encoder.layers[-1].blocks[-1].layernorm_before,
                lambda m: m.swin.encoder.layers[-1].blocks[-1].layernorm_before,
                lambda m: m.vit.encoder.layer[-1].layernorm_before):
        try:
            return get(model)
        except (AttributeError, IndexError):
            continue
    return None


def heatmap(kind: str, bgr, out: Path) -> bool:
    """Grad-CAM: how strongly each region of the last feature layer pushed the answer toward 'generated'."""
    proc, model, fi = _load(kind)
    layer = _target_layer(model)
    if layer is None:
        return False
    store = {}

    def fwd(_m, _i, o):
        o = o[0] if isinstance(o, tuple) else o
        store["act"] = o
        o.register_hook(lambda g: store.__setitem__("grad", g))

    h = layer.register_forward_hook(fwd)
    try:
        with _lock, torch.enable_grad():
            model.zero_grad()
            logits = model(**proc(images=_pil(bgr), return_tensors="pt")).logits
            logits[0, fi].backward()
        act, grad = store["act"], store["grad"]                  # (1, tokens, channels)
        cam = torch.relu((grad.mean(dim=1, keepdim=True) * act).sum(-1))[0].detach().numpy()
        s = int(round(cam.size ** 0.5))
        if s * s != cam.size:                                    # ViT: drop the class token
            cam = cam[1:]
            s = int(round(cam.size ** 0.5))
        if s * s != cam.size:
            return False
        cv2.imencode(".png", ml_core.heat_overlay(bgr, cam.reshape(s, s)))[1].tofile(str(out))
        return True
    except Exception:
        return False
    finally:
        h.remove()


# ---------------------------------------------------------------- faces
_cascade = None


def _faces(bgr):
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return [tuple(int(v) for v in b) for b in _cascade.detectMultiScale(g, 1.1, 5, minSize=(48, 48))]


def _worst_face(bgr):
    """-> (worst probability, number of faces, bbox of worst)."""
    boxes = _faces(bgr)
    worst, wbox = 0.0, None
    for (x, y, w, h) in boxes[:6]:
        m = int(0.15 * max(w, h))
        crop = bgr[max(0, y - m): y + h + m, max(0, x - m): x + w + m]
        p = p_fake("face", crop)
        if p >= worst:
            worst, wbox = p, (x, y, w, h)
    return worst, len(boxes), wbox


def _unavailable(check, what, exc):
    return F("ai" if check != "synthetic_voice" else "audio", check, "info", f"{what} unavailable",
             f"{type(exc).__name__}: {exc}. If this is the first run, connect to the internet once and run "
             "scripts/download_models.py.")


# ---------------------------------------------------------------- entry points used by the analyzers
def check_image(bgr, art_dir: Path, scale: float = 1.0):
    out = []
    try:
        p = p_fake("image", bgr)
        out.append(ml_core.ai_image_finding(p))
        if p >= 0.30:
            heatmap("image", bgr, art_dir / "ai_heatmap.png")
    except Exception as exc:
        return [_unavailable("ai_image", "AI-image detector", exc)]
    try:
        wp, n, box = _worst_face(bgr)
        loc = None
        if box:
            x, y, w, h = box
            loc = {"kind": "region", "x0": int(x / scale), "y0": int(y / scale),
                   "x1": int((x + w) / scale), "y1": int((y + h) / scale)}
        out.append(ml_core.face_finding(wp, n, loc))
    except Exception as exc:
        out.append(_unavailable("face_deepfake", "Face deepfake detector", exc))
    return out


def check_frames(frames, times, art_dir: Path):
    """Up to 20 frames. The upper quartile of scores is used so a short synthetic insert is not averaged away."""
    if not frames:
        return [], []
    try:
        scores = [p_fake("image", f) for f in frames]
    except Exception as exc:
        return [_unavailable("ai_video", "AI-image detector", exc)], [None] * len(frames)
    agg = float(np.percentile(scores, 75))
    worst = int(np.argmax(scores))
    fnd = ml_core.ai_image_finding(agg, check="ai_video", prefix="Video frames: ", where="footage")
    if fnd.severity != "info":
        fnd.location = {"kind": "time", "start": times[worst], "end": times[worst]}
        fnd.detail += f" Worst frame at {times[worst]:.1f}s ({round(scores[worst] * 100)}%)."
    out = [fnd]
    if scores[worst] >= 0.30:
        heatmap("image", frames[worst], art_dir / "ai_heatmap.png")
    try:
        fp = []
        for f in frames:
            p, n, _ = _worst_face(f)
            if n:
                fp.append(p)
        if fp:
            out.append(ml_core.face_finding(float(np.percentile(fp, 75)), len(fp), prefix="Video frames: "))
        else:
            out.append(ml_core.face_finding(0, 0, prefix="Video frames: "))
    except Exception as exc:
        out.append(_unavailable("face_deepfake", "Face deepfake detector", exc))
    return out, [round(float(s), 3) for s in scores]


def check_audio(x, sr):
    """Score every 4-second window with wav2vec2. -> (findings, extra details for the viewer)."""
    try:
        proc, model, fi = _load("audio")
        wins = ml_core.windows(x, sr)
        scores = []
        for i in range(0, len(wins), 8):
            batch = [ml_core.fft_resample(w[2], sr, 16000) for w in wins[i:i + 8]]
            inp = proc(batch, sampling_rate=16000, return_tensors="pt", padding=True)
            with _lock, torch.no_grad():
                logits = model(**inp).logits
            scores += [float(v) for v in torch.softmax(logits, -1)[:, fi]]
        finding, summ = ml_core.voice_finding(scores)
        if finding.severity != "info":
            first = next((w for w, s in zip(wins, scores) if s >= 0.5), wins[0])
            finding.location = {"kind": "time", "start": first[0], "end": first[1]}
        summ["windows"] = [{"start": round(w[0], 2), "end": round(w[1], 2), "score": round(s, 3)}
                           for w, s in zip(wins, scores)]
        return [finding], summ
    except Exception as exc:
        return [_unavailable("synthetic_voice", "Synthetic-voice detector", exc)], {}
