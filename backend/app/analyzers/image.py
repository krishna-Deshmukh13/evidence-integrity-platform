"""Image forensics: EXIF, EXIF thumbnail, ELA, noise consistency, clone detection."""
import io
import re
import struct
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .common import F, noop_progress

EDITORS = re.compile(r"photoshop|gimp|lightroom|snapseed|paint\.net|pixlr|canva|affinity|picsart|facetune|"
                     r"capture one|photopea|acdsee|corel|paintshop|luminar|fotor|befunky", re.I)
MAX_WORK = 1600  # longest side used for noise / clone / artifacts


def _parse_dt(s):
    try:
        return datetime.strptime(str(s).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def _exif_thumbnail(raw: bytes):
    """Return thumbnail JPEG bytes from the raw Exif block (IFD1), or None."""
    try:
        if raw[:6] == b"Exif\x00\x00":
            raw = raw[6:]
        end = "<" if raw[:2] == b"II" else ">"
        ifd0 = struct.unpack(end + "I", raw[4:8])[0]
        n = struct.unpack(end + "H", raw[ifd0:ifd0 + 2])[0]
        nxt = struct.unpack(end + "I", raw[ifd0 + 2 + 12 * n: ifd0 + 6 + 12 * n])[0]
        if not nxt:
            return None
        m = struct.unpack(end + "H", raw[nxt:nxt + 2])[0]
        off = ln = None
        for i in range(m):
            tag, _t, _c, val = struct.unpack(end + "HHII", raw[nxt + 2 + 12 * i: nxt + 14 + 12 * i])
            if tag == 0x201:
                off = val
            elif tag == 0x202:
                ln = val
        return raw[off:off + ln] if off and ln else None
    except Exception:
        return None


def check_metadata(img: Image.Image, fmt: str, w: int, h: int):
    out = []
    exif = img.getexif()
    sub = {}
    try:
        sub = exif.get_ifd(0x8769)
    except Exception:
        pass
    software = str(exif.get(0x0131, "") or "")
    make, model = exif.get(0x010F), exif.get(0x0110)
    dt_mod = _parse_dt(exif.get(0x0132))
    dt_orig = _parse_dt(sub.get(0x9003))
    bad = False
    if software and EDITORS.search(software):
        out.append(F("metadata", "software", "medium", f"Saved by image editing software ({software})",
                     f"The EXIF Software tag names an image editor: {software}.",
                     location={"kind": "field", "name": "EXIF: Software"}))
        bad = True
    if dt_mod and dt_orig:
        delta = (dt_mod - dt_orig).total_seconds()
        if delta > 3600:
            days = delta / 86400
            out.append(F("metadata", "modified_after_capture", "medium",
                         f"Modified after capture ({days:.1f} days later)",
                         f"EXIF DateTime ({dt_mod}) is later than DateTimeOriginal ({dt_orig}).",
                         location={"kind": "field", "name": "EXIF: DateTimeOriginal vs DateTime"}))
            bad = True
        elif delta < -60:
            out.append(F("metadata", "dates_out_of_order", "medium", "Dates out of order",
                         f"DateTime ({dt_mod}) is earlier than DateTimeOriginal ({dt_orig}).",
                         location={"kind": "field", "name": "EXIF: DateTimeOriginal vs DateTime"}))
            bad = True
    px, py = sub.get(0xA002), sub.get(0xA003)
    if px and py and {int(px), int(py)} != {w, h} and (int(px), int(py)) != (w, h):
        out.append(F("metadata", "size_mismatch", "low", "Pixel size differs from EXIF",
                     f"EXIF says {px}x{py} but the image is {w}x{h}: it was resized or cropped after capture.",
                     location={"kind": "field", "name": "EXIF: PixelXDimension/PixelYDimension"}))
        bad = True
    if fmt == "JPEG" and not (make or model or dt_orig or software) and not bad:
        out.append(F("metadata", "exif_stripped", "low", "No camera metadata (EXIF stripped or absent)",
                     "A JPEG straight from a camera normally carries make, model and capture time.",
                     location={"kind": "field", "name": "EXIF"}))
        bad = True
    if not bad:
        out.append(F("metadata", "exif", "info", "Metadata consistent",
                     "No editing software, date conflict or size mismatch in the metadata."))
    return out


def check_thumbnail(img: Image.Image, w: int, h: int):
    raw = img.info.get("exif")
    thumb = _exif_thumbnail(raw) if raw else None
    if not thumb:
        return [F("metadata", "exif_thumbnail", "info", "No EXIF thumbnail to compare")]
    try:
        t = Image.open(io.BytesIO(thumb)).convert("L")
    except Exception:
        return [F("metadata", "exif_thumbnail", "info", "EXIF thumbnail unreadable")]
    tw, th = t.size
    ar_main, ar_t = w / h, tw / th
    if abs(ar_main - ar_t) / ar_main > 0.04 and abs(ar_main - 1 / ar_t) / ar_main > 0.04:
        return [F("metadata", "exif_thumbnail", "medium", "EXIF thumbnail has a different shape",
                  f"Thumbnail is {tw}x{th} but the image is {w}x{h}: it was cropped after capture.",
                  location={"kind": "field", "name": "EXIF: thumbnail"})]
    main = img.convert("L").resize((tw, th)) if abs(ar_main - ar_t) / ar_main <= 0.04 else None
    if main is not None:
        diff = float(np.abs(np.asarray(main, np.float32) - np.asarray(t, np.float32)).mean())
        if diff > 40:
            return [F("metadata", "exif_thumbnail", "medium", "EXIF thumbnail shows different content",
                      f"The embedded preview differs from the main image (mean difference {diff:.0f}).",
                      location={"kind": "field", "name": "EXIF: thumbnail"})]
    return [F("metadata", "exif_thumbnail", "info", "EXIF thumbnail matches the image")]


def _components(mask_blocks, min_blocks):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask_blocks.astype(np.uint8))
    comps = [(stats[i][4], stats[i]) for i in range(1, n) if stats[i][4] >= min_blocks]
    comps.sort(key=lambda c: -c[0])
    return comps


def check_ela(pil_rgb: Image.Image, scale_to_orig: float, art_path: Path, size):
    buf = io.BytesIO()
    pil_rgb.save(buf, "JPEG", quality=90)
    buf.seek(0)
    re_img = Image.open(buf).convert("RGB")
    diff = np.abs(np.asarray(pil_rgb, np.int16) - np.asarray(re_img, np.int16)).max(axis=2).astype(np.float32)
    vis = np.clip(diff * (255.0 / max(diff.max(), 1.0)) * 1.5, 0, 255).astype(np.uint8)
    vis = cv2.resize(vis, size, interpolation=cv2.INTER_AREA)
    cv2.imencode(".png", cv2.applyColorMap(vis, cv2.COLORMAP_INFERNO))[1].tofile(str(art_path))
    B = 16
    h, w = diff.shape
    bh, bw = h // B, w // B
    if bh < 8 or bw < 8:
        return [F("pixel", "ela", "info", "Image too small for error level analysis")]
    blocks = cv2.resize(diff, (bw, bh), interpolation=cv2.INTER_AREA)
    med = float(np.median(blocks))
    mad = float(np.median(np.abs(blocks - med))) * 1.4826 + 1e-3
    mask = (blocks > med + 8 * mad) & (blocks > 4.0)
    comps = _components(mask, 10)
    if comps:
        area, st = comps[0]
        x0, y0, x1, y1 = (int(st[0] * B), int(st[1] * B), int((st[0] + st[2]) * B), int((st[1] + st[3]) * B))
        return [F("pixel", "ela", "medium", "Error level analysis: compact region with different compression",
                  f"A block cluster ({area} blocks) recompresses with unusually high error.",
                  location={"kind": "region", "x0": x0, "y0": y0, "x1": x1, "y1": y1})]
    return [F("pixel", "ela", "info", "Error level analysis: uniform")]


def check_noise(gray_u8: np.ndarray, art_path: Path, to_orig: float):
    B = 32
    h, w = gray_u8.shape
    bh, bw = h // B, w // B
    if bh < 4 or bw < 4:
        return [F("pixel", "noise", "info", "Image too small for noise analysis")]
    res = gray_u8.astype(np.float32) - cv2.medianBlur(gray_u8, 3).astype(np.float32)
    gx = cv2.Sobel(gray_u8, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray_u8, cv2.CV_32F, 0, 1)
    grad = np.sqrt(gx * gx + gy * gy)
    sd = np.zeros((bh, bw), np.float32)
    gm = np.zeros((bh, bw), np.float32)
    mean = np.zeros((bh, bw), np.float32)
    for i in range(bh):
        for j in range(bw):
            sl = (slice(i * B, (i + 1) * B), slice(j * B, (j + 1) * B))
            sd[i, j] = res[sl].std()
            gm[i, j] = grad[sl].mean()
            mean[i, j] = gray_u8[sl].mean()
    valid = (gm < np.percentile(gm, 50)) & (mean > 15) & (mean < 240)
    vis = np.clip(sd / max(float(np.percentile(sd, 99)), 1e-3) * 255, 0, 255).astype(np.uint8)
    cv2.imencode(".png", cv2.applyColorMap(cv2.resize(vis, (w, h), interpolation=cv2.INTER_NEAREST),
                                           cv2.COLORMAP_VIRIDIS))[1].tofile(str(art_path))
    if valid.sum() < 12:
        return [F("pixel", "noise", "info", "Noise consistency: not enough flat areas to judge")]
    lv = np.log(sd + 0.05)
    med = float(np.median(lv[valid]))
    mad = float(np.median(np.abs(lv[valid] - med))) * 1.4826 + 0.05
    z = (lv - med) / mad
    mask = valid & (z < -4)
    comps = _components(mask, 6)
    if comps:
        area, st = comps[0]
        x0, y0 = int(st[0] * B / to_orig), int(st[1] * B / to_orig)
        x1, y1 = int((st[0] + st[2]) * B / to_orig), int((st[1] + st[3]) * B / to_orig)
        return [F("pixel", "noise", "medium", "Noise inconsistency: a region is far cleaner than the rest",
                  f"{area} flat blocks have sensor noise far below the image norm (robust z-score < -4); "
                  "typical of pasted or smoothed areas.",
                  location={"kind": "region", "x0": x0, "y0": y0, "x1": x1, "y1": y1})]
    return [F("pixel", "noise", "info", "Noise consistency: even across the image")]


def check_clone(bgr: np.ndarray, art_path: Path, to_orig: float):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=4000, fastThreshold=10)
    kps, des = orb.detectAndCompute(gray, None)
    vis = bgr.copy()
    result = [F("pixel", "copy_move", "info", "Clone detection: no copied region")]
    if des is not None and len(kps) >= 30:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        knn = bf.knnMatch(des, des, k=3)
        pts = np.array([k.pt for k in kps], np.float32)
        pairs = []
        for m in knn:
            if len(m) < 3:
                continue
            a, b, c = m  # a is the point itself
            if b.distance < 0.7 * c.distance and b.distance < 50:
                d = float(np.linalg.norm(pts[b.queryIdx] - pts[b.trainIdx]))
                if d > 40:
                    pairs.append((b.queryIdx, b.trainIdx))
        groups = {}
        for qi, ti in pairs:
            off = pts[ti] - pts[qi]
            if off[0] < 0 or (off[0] == 0 and off[1] < 0):
                off = -off
            groups.setdefault((int(round(off[0] / 8)), int(round(off[1] / 8))), []).append((qi, ti))
        best = max(groups.values(), key=len) if groups else []
        if len(best) >= 10:
            src = np.array([pts[q] for q, _ in best])
            dst = np.array([pts[t] for _, t in best])
            all_pts = np.vstack([src, dst])
            spread = all_pts.max(0) - all_pts.min(0)
            if spread.max() >= 20:
                sa = np.vstack([src]); sb = np.vstack([dst])
                a0, a1 = sa.min(0).astype(int), sa.max(0).astype(int)
                b0, b1 = sb.min(0).astype(int), sb.max(0).astype(int)
                cv2.rectangle(vis, tuple(a0), tuple(a1), (0, 200, 0), 2)
                cv2.rectangle(vis, tuple(b0), tuple(b1), (0, 0, 230), 2)
                for p, q in zip(src, dst):
                    cv2.line(vis, tuple(p.astype(int)), tuple(q.astype(int)), (0, 165, 255), 1)
                allp = np.vstack([a0, a1, b0, b1]) / to_orig
                x0, y0 = allp.min(0).astype(int)
                x1, y1 = allp.max(0).astype(int)
                result = [F("pixel", "copy_move", "high", "Cloned region detected",
                            f"{len(best)} matching features were found copied from one part of the image "
                            "to another along the same offset, a clear sign of copy-paste.",
                            penalty=30,
                            location={"kind": "region", "x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1),
                                      "matches": len(best)})]
    cv2.imencode(".png", vis)[1].tofile(str(art_path))
    return result


def analyze(path: Path, art_dir: Path, progress=noop_progress):
    art_dir.mkdir(parents=True, exist_ok=True)
    findings, details = [], {}
    img = Image.open(path)
    fmt = img.format
    w, h = img.size
    details.update({"format": fmt, "width": w, "height": h})
    progress("Reading metadata", 5)
    exif = img.getexif()
    details["exif"] = {str(k): str(v)[:120] for k, v in exif.items() if k in
                       (0x010F, 0x0110, 0x0131, 0x0132, 0x0112)}
    findings += check_metadata(img, fmt, w, h)
    findings += check_thumbnail(img, w, h)

    rgb = img.convert("RGB")
    s = min(1.0, MAX_WORK / max(w, h))
    work = rgb.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS) if s < 1 else rgb
    bgr = cv2.cvtColor(np.asarray(work), cv2.COLOR_RGB2BGR)
    details["preview_size"] = [bgr.shape[1], bgr.shape[0]]
    cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tofile(str(art_dir / "original.jpg"))

    progress("Error level analysis", 20)
    if fmt == "JPEG":
        findings += check_ela(rgb, s, art_dir / "ela.png", (bgr.shape[1], bgr.shape[0]))
    else:
        findings.append(F("pixel", "ela", "info", "Error level analysis skipped (not a JPEG)"))
    progress("Noise consistency", 40)
    findings += check_noise(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), art_dir / "noise.png", s)
    progress("Clone detection", 60)
    findings += check_clone(bgr, art_dir / "clone.png", s)
    details["layers"] = ["original", "ela", "noise", "clone"]
    progress("AI-generated image check", 85)
    try:
        from .. import ml  # Stage 3 adds app/ml.py
        findings += ml.check_image(bgr, art_dir, s)
        if (art_dir / "ai_heatmap.png").exists():
            details["layers"].append("heatmap")
    except ImportError:
        findings.append(F("ai", "ai_image", "info", "AI-image detector not installed",
                          "Install the Stage 3 requirements to enable the AI-generated image check."))
    return findings, details
