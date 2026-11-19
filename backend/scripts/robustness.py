#!/usr/bin/env python3
"""D2: Robustness Benchmark Framework.

Applies perturbations to evidence images:
- JPEG recompression (Quality 90, 70, 50)
- Resizing / Downscaling (75%, 50%)
- Screenshot-like re-save (sRGB display gamut, stripped metadata, PNG/lossless roundtrip)
- Additive Gaussian noise (sigma=5, 12)

Re-runs forensic analyzers on each perturbed version and produces:
- robustness_table.csv
- robustness_degradation.png
- robustness_heatmap.png
- Terminal summary table showing how check detection rates and scores degrade under laundering attacks.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure backend root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import scoring
from app.analyzers import image


def apply_perturbations(img_path: Path, work_dir: Path) -> List[Tuple[str, str, Path]]:
    """Generate all perturbed variants of the source image."""
    work_dir.mkdir(parents=True, exist_ok=True)
    orig_img = Image.open(img_path).convert("RGB")
    variants = []

    # 1. Baseline
    base_path = work_dir / f"baseline_{img_path.name}"
    orig_img.save(base_path, quality=95, exif=orig_img.getexif())
    variants.append(("baseline", "Original unperturbed image", base_path))

    # 2. JPEG Recompression (Quality 90, 70, 50)
    for q in [90, 70, 50]:
        p = work_dir / f"jpeg_q{q}_{img_path.stem}.jpg"
        orig_img.save(p, format="JPEG", quality=q)
        variants.append((f"jpeg_q{q}", f"JPEG recompression (quality {q})", p))

    # 3. Resizing (75%, 50%)
    w, h = orig_img.size
    for scale in [75, 50]:
        nw, nh = int(w * (scale / 100.0)), int(h * (scale / 100.0))
        resized = orig_img.resize((nw, nh), Image.Resampling.BILINEAR)
        p = work_dir / f"resize_{scale}pct_{img_path.stem}.jpg"
        resized.save(p, format="JPEG", quality=85)
        variants.append((f"resize_{scale}pct", f"Downscaled to {scale}% dimensions", p))

    # 4. Screenshot-like re-save (lossless RGB PNG, metadata stripped)
    screen_path = work_dir / f"screenshot_{img_path.stem}.png"
    orig_img.save(screen_path, format="PNG")
    variants.append(("screenshot", "Screenshot-like capture (PNG re-save, no EXIF)", screen_path))

    # 5. Gaussian Noise (sigma=5, sigma=12)
    arr = np.array(orig_img).astype(np.float32)
    rng = np.random.default_rng(42)
    for sigma in [5, 12]:
        noisy_arr = arr + rng.normal(0, sigma, arr.shape)
        noisy_arr = np.clip(noisy_arr, 0, 255).astype(np.uint8)
        noisy_img = Image.fromarray(noisy_arr)
        p = work_dir / f"noise_sigma{sigma}_{img_path.stem}.jpg"
        noisy_img.save(p, format="JPEG", quality=88)
        variants.append((f"noise_sigma{sigma}", f"Gaussian noise (sigma={sigma})", p))

    return variants


def evaluate_robustness(img_path: Path, out_dir: Path):
    """Run robustness perturbation suite and output CSV and charts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = out_dir / "perturbed_samples"
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print(f"Applying forensic perturbations to {img_path.name}...")
    variants = apply_perturbations(img_path, work_dir)

    all_checks = set()
    results = []

    for name, desc, v_path in variants:
        print(f"  Evaluating variant '{name}': {desc}...")
        v_art_dir = artifacts_dir / name
        v_art_dir.mkdir(parents=True, exist_ok=True)

        try:
            findings, details = image.analyze(v_path, v_art_dir)
        except Exception as e:
            print(f"    Analyzer error on {name}: {e}")
            findings, details = [], {}

        score, breakdown, verdict = scoring.compute(findings)

        rec = {
            "perturbation": name,
            "description": desc,
            "score": score,
            "verdict": verdict,
            "findings_count": len(findings),
            "checks": {f.check: f.penalty for f in findings},
        }
        for f in findings:
            all_checks.add(f.check)
        results.append(rec)

    sorted_checks = sorted(list(all_checks))

    # Write robustness_table.csv
    csv_path = out_dir / "robustness_table.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["perturbation", "description", "score", "verdict", "findings_count"] + [f"check_{c}" for c in sorted_checks]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = {
                "perturbation": r["perturbation"],
                "description": r["description"],
                "score": r["score"],
                "verdict": r["verdict"],
                "findings_count": r["findings_count"],
            }
            for c in sorted_checks:
                row[f"check_{c}"] = 1 if c in r["checks"] else 0
            writer.writerow(row)

    # ---------------------------------------------------------------------------
    # Plot 1: Score & Findings Degradation Line Chart
    # ---------------------------------------------------------------------------
    names = [r["perturbation"] for r in results]
    scores = [r["score"] for r in results]
    f_counts = [r["findings_count"] for r in results]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    color = "#2563eb"
    ax1.set_xlabel("Perturbation Attack", fontweight="bold", labelpad=8)
    ax1.set_ylabel("Evidence Integrity Score (0-100)", color=color, fontweight="bold")
    ax1.plot(names, scores, color=color, marker="o", lw=2.5, markersize=7, label="Integrity Score")
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.set_ylim(-5, 105)
    ax1.axhline(80, color="#10b981", linestyle="--", alpha=0.6, label="Consistent threshold (80)")
    ax1.axhline(50, color="#f59e0b", linestyle="--", alpha=0.6, label="Needs review threshold (50)")
    plt.xticks(rotation=30, ha="right")

    ax2 = ax1.twinx()
    color2 = "#ef4444"
    ax2.set_ylabel("Total Checks Triggered", color=color2, fontweight="bold")
    ax2.bar(names, f_counts, alpha=0.25, color=color2, width=0.4, label="Detected Checks")
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.set_ylim(0, max(max(f_counts) + 2, 6))

    plt.title(f"Forensic Detection Degradation Across Perturbations ({img_path.name})", fontsize=12, fontweight="bold")
    fig.tight_layout()
    plt.savefig(out_dir / "robustness_degradation.png", dpi=200)
    plt.close()

    # ---------------------------------------------------------------------------
    # Plot 2: Check Survival Heatmap
    # ---------------------------------------------------------------------------
    if sorted_checks:
        matrix = np.zeros((len(sorted_checks), len(names)), dtype=int)
        for j, r in enumerate(results):
            for i, c in enumerate(sorted_checks):
                matrix[i, j] = 1 if c in r["checks"] else 0

        plt.figure(figsize=(10, max(4, len(sorted_checks) * 0.5)))
        plt.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=1)
        plt.title(f"Individual Forensic Check Survival Matrix ({img_path.name})", fontsize=11, fontweight="bold")
        plt.xticks(range(len(names)), names, rotation=35, ha="right")
        plt.yticks(range(len(sorted_checks)), sorted_checks)
        for i in range(len(sorted_checks)):
            for j in range(len(names)):
                text = "Detected" if matrix[i, j] == 1 else "Missed"
                col = "white" if matrix[i, j] == 1 else "#9ca3af"
                plt.text(j, i, text, ha="center", va="center", color=col, fontsize=9, fontweight="bold")
        plt.tight_layout()
        plt.savefig(out_dir / "robustness_heatmap.png", dpi=200)
        plt.close()

    # Terminal Report
    print("\n" + "=" * 76)
    print(f"ROBUSTNESS BENCHMARK RESULTS: {img_path.name}")
    print("=" * 76)
    print(f"{'Perturbation':<18} | {'Score':<5} | {'Verdict':<18} | {'Flags':<5} | Description")
    print("-" * 76)
    for r in results:
        print(f"{r['perturbation']:<18} | {r['score']:<5} | {r['verdict']:<18} | {r['findings_count']:<5} | {r['description']}")
    print("-" * 76)
    print(f"Output table: {csv_path}")
    print(f"Output chart: {out_dir / 'robustness_degradation.png'}")
    print(f"Output heatmap: {out_dir / 'robustness_heatmap.png'}")
    print("=" * 76 + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate forensic robustness against recompression and perturbations.")
    parser.add_argument("--input", type=str, default=None, help="Path to input image file (e.g. photo_tampered.jpg)")
    parser.add_argument("--out-dir", type=str, default="robustness_results", help="Directory to save CSV and charts")
    parser.add_argument("--demo", action="store_true", help="Run on built-in tampered demo image")

    args = parser.parse_args()
    out_dir = Path(args.out_dir).resolve()

    if args.input:
        target = Path(args.input).resolve()
    else:
        # Default or demo mode: generate sample tampered image
        from scripts import make_samples
        demo_tmp = Path(tempfile.gettempdir()) / "eip_robustness_demo"
        make_samples.make(demo_tmp)
        target = demo_tmp / "photo_tampered.jpg"
        print(f"Using demo tampered sample: {target}")

    if not target.exists():
        print(f"Error: Target image {target} not found.")
        sys.exit(1)

    evaluate_robustness(target, out_dir)


if __name__ == "__main__":
    main()
