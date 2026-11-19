"""Score -> finding thresholds from the guide, audio helpers, heatmap overlay (no torch needed)."""
import numpy as np

from app import ml_core, scoring


def _sev(f):
    return f.severity, f.penalty


def test_ai_image_thresholds():
    assert _sev(ml_core.ai_image_finding(0.97)) == ("high", 52)
    assert _sev(ml_core.ai_image_finding(0.90)) == ("high", 34)
    assert _sev(ml_core.ai_image_finding(0.70)) == ("medium", 18)
    assert ml_core.ai_image_finding(0.55).severity == "low"
    f = ml_core.ai_image_finding(0.01)
    assert f.severity == "info" and "natural camera content (1%)" in f.title


def test_face_thresholds():
    assert _sev(ml_core.face_finding(0.9, 2)) == ("high", 30)
    assert _sev(ml_core.face_finding(0.7, 1)) == ("medium", 16)
    assert ml_core.face_finding(0.5, 1).severity == "info"
    assert ml_core.face_finding(0.0, 0).severity == "info"


def test_voice_thresholds():
    assert _sev(ml_core.voice_finding([0.95, 0.93])[0]) == ("high", 52)
    assert _sev(ml_core.voice_finding([0.8, 0.8])[0]) == ("high", 36)
    assert _sev(ml_core.voice_finding([0.6, 0.55, 0.9, 0.1, 0.52, 0.9, 0.95, 0.6, 0.2, 0.1])[0])[0] in ("high", "medium")
    assert _sev(ml_core.voice_finding([0.1, 0.55, 0.9, 0.1, 0.1, 0.1])[0]) == ("low", 6)       # 33% of windows < 35%, peak 90%
    assert _sev(ml_core.voice_finding([0.6, 0.6, 0.1, 0.1, 0.1])[0]) == ("medium", 20)         # 40% of windows
    assert _sev(ml_core.voice_finding([0.75, 0.0, 0.0, 0.0, 0.0])[0]) == ("low", 6)           # one window 70%+
    f, _ = ml_core.voice_finding([0.02, 0.01, 0.03])
    assert f.severity == "info"
    assert ml_core.voice_finding([])[0].severity == "info"


def test_ai_penalty_respects_cap():
    f = [ml_core.ai_image_finding(0.99), ml_core.face_finding(0.99, 1)]
    score, bd, verdict = scoring.compute([{"category": x.category, "severity": x.severity, "penalty": x.penalty} for x in f])
    assert bd["ai"] == 55 and score == 45 and verdict == "Likely manipulated"   # 52 + 30 capped at 55


def test_fft_resample_keeps_frequency():
    sr = 44100
    t = np.arange(sr * 2) / sr
    y = ml_core.fft_resample(np.sin(2 * np.pi * 440 * t).astype(np.float32), sr, 16000)
    assert len(y) == 32000
    peak = np.fft.rfftfreq(len(y), 1 / 16000)[np.abs(np.fft.rfft(y)).argmax()]
    assert abs(peak - 440) < 2
    assert ml_core.fft_resample(y, 16000, 16000) is not None


def test_windows():
    x = np.zeros(int(44100 * 10.5), np.float32)
    w = ml_core.windows(x, 44100)
    assert [round(a) for a, _, _ in w] == [0, 4, 8] and round(w[-1][1], 1) == 10.5
    assert len(ml_core.windows(np.zeros(44100 * 400, np.float32), 44100)) == 60
    assert ml_core.windows(np.zeros(1000, np.float32), 44100) == []


def test_heat_overlay_shape():
    img = np.full((60, 80, 3), 120, np.uint8)
    out = ml_core.heat_overlay(img, np.random.rand(7, 7))
    assert out.shape == img.shape and out.dtype == np.uint8
