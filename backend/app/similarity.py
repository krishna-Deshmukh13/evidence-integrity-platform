"""Perceptual hash (DCT, 64 bit) and pixel difference."""
import cv2
import numpy as np

PHASH_LIMIT = 16  # bits


def phash_image(path) -> str:
    data = np.fromfile(str(path), np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return ""
    small = cv2.resize(img, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(small)[:8, :8]
    bits = (dct > np.median(dct)).flatten()
    return "".join("1" if b else "0" for b in bits)  # 64 chars of 0/1


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b)) if a and b and len(a) == len(b) else 64


def similarity_pct(a: str, b: str) -> int:
    return round(100 * (1 - hamming(a, b) / 64))


def diff_map(path_a, path_b, out_png=None, threshold=28):
    """Scale B to A, subtract, blur, keep > threshold, join neighbours, box each area."""
    a = cv2.imdecode(np.fromfile(str(path_a), np.uint8), cv2.IMREAD_COLOR)
    b = cv2.imdecode(np.fromfile(str(path_b), np.uint8), cv2.IMREAD_COLOR)
    if a is None or b is None:
        return None
    b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    ga = cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    gb = cv2.GaussianBlur(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    mask = (cv2.absdiff(ga, gb) > threshold).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    boxes = [tuple(int(v) for v in stats[i][:4]) for i in range(1, n) if stats[i][4] >= 100]
    pct = round(100.0 * float((mask > 0).sum()) / mask.size, 1)
    if out_png:
        vis = cv2.cvtColor(ga, cv2.COLOR_GRAY2BGR)
        vis[mask > 0] = (0, 40, 240)
        for x, y, w, h in boxes:
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 200), 2)
        cv2.imencode(".png", vis)[1].tofile(str(out_png))
    return {"pixels_changed_pct": pct, "boxes": [{"x": x, "y": y, "w": w, "h": h} for x, y, w, h in boxes]}
