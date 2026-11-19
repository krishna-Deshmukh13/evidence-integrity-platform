"""ffmpeg / ffprobe helpers shared by the audio and video analyzers."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
                        str(path)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("ffprobe could not read this file")
    return json.loads(r.stdout or "{}")


def all_tags(info: dict) -> dict:
    tags = dict((info.get("format") or {}).get("tags") or {})
    for s in info.get("streams", []):
        for k, v in (s.get("tags") or {}).items():
            tags.setdefault(k, v)
    return {k.lower(): str(v) for k, v in tags.items()}


def decode_mono(path: Path, max_seconds=900):
    """-> (float32 samples in [-1,1], sample_rate) at the file's own rate."""
    info = probe(path)
    st = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    if not st:
        return None, 0
    sr = int(st.get("sample_rate", 44100))
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", str(max_seconds), "-vn", "-ac", "1",
                        "-f", "f32le", "-"], capture_output=True, timeout=600)
    return np.frombuffer(r.stdout, np.float32).copy(), sr


def extract_audio_wav(path: Path, out_wav: Path) -> bool:
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1",
                        "-acodec", "pcm_s16le", str(out_wav)], capture_output=True, timeout=600)
    return r.returncode == 0 and out_wav.exists() and out_wav.stat().st_size > 100
