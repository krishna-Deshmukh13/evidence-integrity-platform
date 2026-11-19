#!/usr/bin/env python3
"""D1: Research and Evaluation Benchmark Framework.

Runs platform forensic analyzers on labelled datasets (genuine and manipulated subfolders per media type),
outputs results.csv, calculates Precision, Recall, F1, ROC-AUC, FPR, and Confusion Matrix (overall and per-check),
and saves evaluation plots as PNG.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import numpy as np
from sklearn import metrics

# Ensure backend root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import scoring
from app.analyzers import audio, document, image, video

DATASET_LAYOUT_GUIDE = """
================================================================================
EVIDENCE INTEGRITY PLATFORM — BENCHMARK DATASET FOLDER LAYOUT
================================================================================
To evaluate this platform on standard academic and forensic benchmark datasets,
organize your files into genuine/ and manipulated/ subfolders per media type:

<data_dir>/
├── image/
│   ├── genuine/
│   │   ├── CASIA v2.0: Authentic uncompressed camera originals (Au_*.jpg / .tif)
│   │   └── Columbia Image Splicing: Pristine uncompressed camera captures
│   └── manipulated/
│       ├── CASIA v2.0: Spliced and copy-move forged images (Sp_*.jpg / .tif)
│       └── FaceForensics++: Extracted manipulated video frames (c23 compression)
├── audio/
│   ├── genuine/
│   │   └── ASVspoof 2019 / 2021: Bonafide genuine human speech recordings (.wav)
│   └── manipulated/
│       └── ASVspoof 2019 / 2021: Neural TTS and voice conversion spoof attacks (.wav)
├── video/
│   ├── genuine/
│   │   └── FaceForensics++: Original pristine sequence videos (.mp4 / .avi)
│   └── manipulated/
│       └── FaceForensics++: Deepfakes, Face2Face, FaceSwap, NeuralTextures (.mp4)
└── document/
    ├── genuine/
    │   └── Authentic digital invoices, contracts, legal filings (.pdf / .docx)
    └── manipulated/
        └── Modified text overlays, altered metadata/dates, forged PDF forms

HOW TO RUN:
  python scripts/evaluate.py --data-dir /path/to/dataset --out-dir ./eval_results
  python scripts/evaluate.py --demo   # Runs instantly on built-in synthetic benchmark
================================================================================
"""


def detect_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"):
        return "image"
    if ext in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
        return "audio"
    if ext in (".mp4", ".avi", ".mov", ".mkv"):
        return "video"
    if ext in (".pdf", ".docx"):
        return "document"
    return "image"


def run_analyzer_on_file(path: Path, media_type: str, artifacts_dir: Path):
    """Run real platform analyzer on file and compute score and findings."""
    try:
        if media_type == "image":
            findings, details = image.analyze(path, artifacts_dir)
        elif media_type == "audio":
            findings, details = audio.analyze(path, artifacts_dir)
        elif media_type == "video":
            findings, details = video.analyze(path, artifacts_dir)
        elif media_type == "document":
            findings, details = document.analyze(path, artifacts_dir)
        else:
            findings, details = [], {}
    except Exception as e:
        print(f"Warning: Analyzer error on {path.name}: {e}")
        findings = []

    score, breakdown, verdict = scoring.compute(findings)
    return findings, score, verdict, breakdown


def build_demo_dataset(target_dir: Path):
    """Create sample genuine and manipulated files for instant demonstration."""
    from scripts import make_samples, make_samples2
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_s = target_dir / "_temp"
    temp_s.mkdir(parents=True, exist_ok=True)

    make_samples.make(temp_s)
    make_samples2.make(temp_s)

    # Image
    im_gen = target_dir / "image" / "genuine"
    im_man = target_dir / "image" / "manipulated"
    im_gen.mkdir(parents=True, exist_ok=True)
    im_man.mkdir(parents=True, exist_ok=True)
    if (temp_s / "photo_original.jpg").exists():
        (im_gen / "photo_original.jpg").write_bytes((temp_s / "photo_original.jpg").read_bytes())
    if (temp_s / "photo_tampered.jpg").exists():
        (im_man / "photo_tampered.jpg").write_bytes((temp_s / "photo_tampered.jpg").read_bytes())
    if (temp_s / "photo_stripped.jpg").exists():
        (im_man / "photo_stripped.jpg").write_bytes((temp_s / "photo_stripped.jpg").read_bytes())

    # Audio
    au_gen = target_dir / "audio" / "genuine"
    au_man = target_dir / "audio" / "manipulated"
    au_gen.mkdir(parents=True, exist_ok=True)
    au_man.mkdir(parents=True, exist_ok=True)
    if (temp_s / "voice_human.wav").exists():
        (au_gen / "voice_human.wav").write_bytes((temp_s / "voice_human.wav").read_bytes())
    elif (temp_s / "voice_original.wav").exists():
        (au_gen / "voice_original.wav").write_bytes((temp_s / "voice_original.wav").read_bytes())
    if (temp_s / "voice_synthetic.wav").exists():
        (au_man / "voice_synthetic.wav").write_bytes((temp_s / "voice_synthetic.wav").read_bytes())
    elif (temp_s / "voice_tts.wav").exists():
        (au_man / "voice_tts.wav").write_bytes((temp_s / "voice_tts.wav").read_bytes())

    # Document
    doc_gen = target_dir / "document" / "genuine"
    doc_man = target_dir / "document" / "manipulated"
    doc_gen.mkdir(parents=True, exist_ok=True)
    doc_man.mkdir(parents=True, exist_ok=True)
    if (temp_s / "invoice_original.pdf").exists():
        (doc_gen / "invoice_original.pdf").write_bytes((temp_s / "invoice_original.pdf").read_bytes())
    if (temp_s / "invoice_tampered.pdf").exists():
        (doc_man / "invoice_tampered.pdf").write_bytes((temp_s / "invoice_tampered.pdf").read_bytes())
    if (temp_s / "memo_clean.docx").exists():
        (doc_gen / "memo_clean.docx").write_bytes((temp_s / "memo_clean.docx").read_bytes())
    if (temp_s / "memo_tampered.docx").exists():
        (doc_man / "memo_tampered.docx").write_bytes((temp_s / "memo_tampered.docx").read_bytes())

    # Video
    vid_gen = target_dir / "video" / "genuine"
    vid_man = target_dir / "video" / "manipulated"
    vid_gen.mkdir(parents=True, exist_ok=True)
    vid_man.mkdir(parents=True, exist_ok=True)
    if (temp_s / "video_original.mp4").exists():
        (vid_gen / "video_original.mp4").write_bytes((temp_s / "video_original.mp4").read_bytes())
    if (temp_s / "video_edited.mp4").exists():
        (vid_man / "video_edited.mp4").write_bytes((temp_s / "video_edited.mp4").read_bytes())


def evaluate_dataset(data_dir: Path, out_dir: Path, is_demo: bool = False):
    """Run full benchmark evaluation across genuine/ and manipulated/ files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    items = []
    # Collect files
    for m_type in ["image", "audio", "video", "document"]:
        m_dir = data_dir / m_type
        if not m_dir.exists():
            continue
        gen_dir = m_dir / "genuine"
        man_dir = m_dir / "manipulated"

        if gen_dir.exists():
            for f in sorted(gen_dir.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    items.append((f, m_type, 0))  # 0 = genuine
        if man_dir.exists():
            for f in sorted(man_dir.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    items.append((f, m_type, 1))  # 1 = manipulated

    if not items:
        print(f"Error: No benchmark files found in {data_dir}.")
        print("Run with --demo to evaluate against project demo files or use --layout to see required structure.")
        return None

    print(f"Loaded {len(items)} labelled items for evaluation ({sum(1 for x in items if x[2]==0)} genuine, {sum(1 for x in items if x[2]==1)} manipulated).")

    all_checks = set()
    records = []

    for idx, (path, m_type, label) in enumerate(items, 1):
        print(f"[{idx}/{len(items)}] Analyzing {m_type}: {path.name} (ground truth: {'manipulated' if label==1 else 'genuine'})...")
        file_art_dir = artifacts_dir / f"item_{idx}"
        file_art_dir.mkdir(parents=True, exist_ok=True)
        findings, score, verdict, breakdown = run_analyzer_on_file(path, m_type, file_art_dir)

        # File is flagged if verdict is Likely manipulated or Needs review (or score < 80)
        predicted = 1 if verdict in ("Likely manipulated", "Needs review") else 0
        manipulation_prob = (100.0 - float(score)) / 100.0

        rec = {
            "file": str(path.relative_to(data_dir)),
            "filename": path.name,
            "media_type": m_type,
            "ground_truth": label,
            "score": score,
            "verdict": verdict,
            "predicted": predicted,
            "manipulation_prob": manipulation_prob,
            "findings_count": len(findings),
            "checks_triggered": {},
            "findings_detail": [f.check for f in findings],
        }
        for f in findings:
            all_checks.add(f.check)
            rec["checks_triggered"][f.check] = rec["checks_triggered"].get(f.check, 0) + 1

        records.append(rec)

    # ---------------------------------------------------------------------------
    # Write results.csv
    # ---------------------------------------------------------------------------
    sorted_checks = sorted(list(all_checks))
    csv_path = out_dir / "results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["file", "filename", "media_type", "ground_truth", "score", "verdict", "predicted", "manipulation_prob", "findings_count"] + [f"check_{c}" for c in sorted_checks]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = {
                "file": r["file"],
                "filename": r["filename"],
                "media_type": r["media_type"],
                "ground_truth": r["ground_truth"],
                "score": r["score"],
                "verdict": r["verdict"],
                "predicted": r["predicted"],
                "manipulation_prob": f"{r['manipulation_prob']:.4f}",
                "findings_count": r["findings_count"],
            }
            for c in sorted_checks:
                row[f"check_{c}"] = 1 if c in r["checks_triggered"] else 0
            writer.writerow(row)

    # ---------------------------------------------------------------------------
    # Compute Metrics
    # ---------------------------------------------------------------------------
    y_true = np.array([r["ground_truth"] for r in records])
    y_pred = np.array([r["predicted"] for r in records])
    y_scores = np.array([r["manipulation_prob"] for r in records])

    # Confusion matrix
    # [ [TN, FP], [FN, TP] ]
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    try:
        if len(np.unique(y_true)) > 1:
            roc_auc = float(metrics.roc_auc_score(y_true, y_scores))
        else:
            roc_auc = 1.0
    except Exception:
        roc_auc = 0.5

    # Per-check metrics
    per_check = {}
    for c in sorted_checks:
        c_trig = np.array([1 if c in r["checks_triggered"] else 0 for r in records])
        c_tp = int(np.sum((y_true == 1) & (c_trig == 1)))
        c_fp = int(np.sum((y_true == 0) & (c_trig == 1)))
        c_fn = int(np.sum((y_true == 1) & (c_trig == 0)))
        c_tn = int(np.sum((y_true == 0) & (c_trig == 0)))
        sens = float(c_tp / (c_tp + c_fn)) if (c_tp + c_fn) > 0 else 0.0
        c_fpr = float(c_fp / (c_fp + c_tn)) if (c_fp + c_tn) > 0 else 0.0
        per_check[c] = {
            "total_triggers": int(np.sum(c_trig)),
            "tp": c_tp,
            "fp": c_fp,
            "sensitivity": round(sens, 4),
            "false_positive_rate": round(c_fpr, 4),
        }

    summary = {
        "dataset_mode": "Demonstration" if is_demo else "Real Benchmark",
        "total_files": len(records),
        "genuine_count": int(np.sum(y_true == 0)),
        "manipulated_count": int(np.sum(y_true == 1)),
        "confusion_matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
        },
        "overall_metrics": {
            "accuracy": round(float((tp + tn) / len(records)), 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "specificity": round(specificity, 4),
            "false_positive_rate": round(fpr, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
        },
        "per_check_metrics": per_check,
    }

    summary_json_path = out_dir / "summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # ---------------------------------------------------------------------------
    # Generate Plots (PNG)
    # ---------------------------------------------------------------------------
    # 1. Confusion Matrix Plot
    plt.figure(figsize=(5, 4.5))
    cm_matrix = np.array([[tn, fp], [fn, tp]])
    plt.imshow(cm_matrix, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix (Verdict vs Ground Truth)", fontsize=11, fontweight="bold")
    plt.colorbar()
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ["Genuine (0)", "Manipulated (1)"])
    plt.yticks(tick_marks, ["Genuine (0)", "Manipulated (1)"])
    for i in range(2):
        for j in range(2):
            count = cm_matrix[i, j]
            col = "white" if count > (cm_matrix.max() / 2) else "black"
            plt.text(j, i, f"{count}", ha="center", va="center", color=col, fontsize=14, fontweight="bold")
    plt.ylabel("True Class")
    plt.xlabel("Predicted Class")
    plt.tight_layout()
    plt.savefig(out_dir / "confusion_matrix.png", dpi=200)
    plt.close()

    # 2. ROC Curve Plot
    plt.figure(figsize=(6, 5))
    if len(np.unique(y_true)) > 1:
        fpr_arr, tpr_arr, _ = metrics.roc_curve(y_true, y_scores)
        plt.plot(fpr_arr, tpr_arr, color="#2563eb", lw=2.5, label=f"ROC Curve (AUC = {roc_auc:.3f})")
    else:
        plt.plot([0, 1], [1, 1], color="#2563eb", lw=2.5, label="ROC Curve (Single Class)")
    plt.plot([0, 1], [0, 1], color="#9ca3af", lw=1.5, linestyle="--", label="Random Chance (AUC = 0.500)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate (1 - Specificity)")
    plt.ylabel("True Positive Rate (Recall / Sensitivity)")
    plt.title("Receiver Operating Characteristic (ROC)", fontsize=11, fontweight="bold")
    plt.legend(loc="lower right")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(out_dir / "roc_curve.png", dpi=200)
    plt.close()

    # 3. Per-Check Detection Rate Bar Chart
    if per_check:
        plt.figure(figsize=(8, max(4, len(per_check) * 0.45)))
        check_names = list(per_check.keys())
        sens_vals = [per_check[c]["sensitivity"] * 100 for c in check_names]
        fpr_vals = [per_check[c]["false_positive_rate"] * 100 for c in check_names]

        y_pos = np.arange(len(check_names))
        height = 0.35

        plt.barh(y_pos - height/2, sens_vals, height, label="Recall / Detection Rate (%)", color="#10b981")
        plt.barh(y_pos + height/2, fpr_vals, height, label="False Alarm Rate (%)", color="#ef4444")

        plt.yticks(y_pos, check_names)
        plt.xlabel("Percentage (%)")
        plt.title("Per-Check Detection vs False Alarm Rates", fontsize=11, fontweight="bold")
        plt.legend(loc="lower right")
        plt.grid(axis="x", linestyle=":", alpha=0.6)
        plt.tight_layout()
        plt.savefig(out_dir / "per_check_metrics.png", dpi=200)
        plt.close()

    # Print summary table to stdout
    print("\n" + "=" * 60)
    print(f"BENCHMARK EVALUATION SUMMARY ({'DEMO DATASET' if is_demo else 'BENCHMARK'})")
    print("=" * 60)
    print(f"Total Evaluated Files:  {len(records)}")
    print(f"Accuracy:               {summary['overall_metrics']['accuracy'] * 100:.1f}%")
    print(f"Precision:              {precision * 100:.1f}%")
    print(f"Recall (Sensitivity):   {recall * 100:.1f}%")
    print(f"Specificity:            {specificity * 100:.1f}%")
    print(f"False Positive Rate:    {fpr * 100:.1f}%")
    print(f"F1 Score:               {f1:.3f}")
    print(f"ROC-AUC:                {roc_auc:.3f}")
    print(f"Confusion Matrix:       TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print("-" * 60)
    print(f"Saved results to:       {csv_path}")
    print(f"Saved metrics to:       {summary_json_path}")
    print(f"Saved plots to:         {out_dir / 'confusion_matrix.png'}")
    print(f"                        {out_dir / 'roc_curve.png'}")
    print(f"                        {out_dir / 'per_check_metrics.png'}")
    print("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate forensic analyzers on labelled datasets.")
    parser.add_argument("--data-dir", type=str, default=None, help="Root folder containing genuine/ and manipulated/ folders")
    parser.add_argument("--out-dir", type=str, default="evaluation_results", help="Directory to save results.csv and plots")
    parser.add_argument("--demo", action="store_true", help="Generate and run evaluation on synthetic benchmark dataset")
    parser.add_argument("--layout", action="store_true", help="Print expected folder layout for academic datasets and exit")

    args = parser.parse_args()

    if args.layout:
        print(DATASET_LAYOUT_GUIDE)
        return

    out_dir = Path(args.out_dir).resolve()

    if args.demo or not args.data_dir:
        print("Using synthetic demo benchmark dataset...")
        demo_dir = Path(tempfile.gettempdir()) / "eip_eval_demo"
        build_demo_dataset(demo_dir)
        evaluate_dataset(demo_dir, out_dir, is_demo=True)
    else:
        d_path = Path(args.data_dir).resolve()
        if not d_path.exists():
            print(f"Error: Data directory {d_path} does not exist.")
            print(DATASET_LAYOUT_GUIDE)
            sys.exit(1)
        evaluate_dataset(d_path, out_dir, is_demo=False)


if __name__ == "__main__":
    main()
