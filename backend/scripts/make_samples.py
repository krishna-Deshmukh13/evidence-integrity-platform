"""Generate synthetic demo images (original / tampered / stripped). Used by tests and the demo seed."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 1200, 800


def _scene(seed=7):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = 90 + 60 * np.sin(xx / 170.0) + 40 * np.cos(yy / 120.0)
    img = np.stack([base + 20, base, base - 20], axis=2)
    for _ in range(260):  # textured blobs so keypoints exist
        cx, cy, r = rng.integers(0, W), rng.integers(0, H), rng.integers(6, 40)
        col = rng.integers(20, 235, 3)
        m = (xx - cx) ** 2 + (yy - cy) ** 2 < r * r
        img[m] = col
    for _ in range(120):
        x0, y0 = rng.integers(0, W - 60), rng.integers(0, H - 60)
        img[y0:y0 + rng.integers(2, 6), x0:x0 + rng.integers(20, 60)] = rng.integers(0, 255, 3)
    img += rng.normal(0, 5.0, img.shape)  # even sensor noise
    return np.clip(img, 0, 255).astype(np.uint8)


def _exif(software=None, dt="2026:10:10 09:15:00", dt_mod=None):
    e = Image.Exif()
    e[0x010F], e[0x0110] = "Canon", "EOS 200D"
    if software:
        e[0x0131] = software
    e[0x0132] = dt_mod or dt
    sub = e.get_ifd(0x8769)
    sub[0x9003] = dt
    return e


def make(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    arr = _scene()
    Image.fromarray(arr).save(out_dir / "photo_original.jpg", quality=92, exif=_exif())
    t = arr.copy()
    t[560:700, 100:260] = t[100:240, 700:860]            # copy-move
    t[420:560, 800:960] = (t[420:560, 800:960] * 0.2 + 120).astype(np.uint8)  # smoothed patch (no noise)
    Image.fromarray(t).save(out_dir / "photo_tampered.jpg", quality=90,
                            exif=_exif("Adobe Photoshop 25.4 (Windows)", dt_mod="2026:10:13 08:47:00"))
    Image.fromarray(arr).save(out_dir / "photo_stripped.jpg", quality=85)  # no EXIF
    return out_dir


if __name__ == "__main__":
    print(make(Path(sys.argv[1] if len(sys.argv) > 1 else "samples")))
