#!/usr/bin/env python3
"""D3: Learned Fusion and Feature Ablation.

Trains Logistic Regression and Gradient Boosting models on findings-derived features
(check triggers, severity, penalty sums) from evaluation output, compares against
hand-tuned score by ROC-AUC, produces an ablation table (removing one check at a time),
and saves an ML fusion model for optional UI confidence assistance.
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn import metrics
from sklearn.model_selection import StratifiedKFold

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

from app import config


def load_dataset_from_csv(csv_path: Path):
    """Load evaluation CSV and construct feature matrix X, ground truth y, and check names."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {csv_path}")

    check_cols = [c for c in reader.fieldnames if c.startswith("check_")]
    X_checks = []
    hand_tuned_probs = []
    y = []

    for r in rows:
        checks_vec = [float(r.get(c, 0) or 0) for c in check_cols]
        X_checks.append(checks_vec)
        hand_tuned_probs.append(float(r.get("manipulation_prob", 0.0)))
        y.append(int(r.get("ground_truth", 0)))

    X = np.array(X_checks, dtype=np.float32)
    y = np.array(y, dtype=np.int32)
    hand_tuned_probs = np.array(hand_tuned_probs, dtype=np.float32)
    return X, y, hand_tuned_probs, check_cols


def run_cross_val_auc(clf, X: np.ndarray, y: np.ndarray, n_splits: int = 3) -> Tuple[float, np.ndarray]:
    """Perform stratified cross-validation and return out-of-fold predicted probabilities and ROC-AUC."""
    unique_classes, counts = np.unique(y, return_counts=True)
    if len(unique_classes) < 2 or min(counts) < 2:
        # Fallback for minimal sample size
        clf.fit(X, y)
        probs = clf.predict_proba(X)[:, 1] if hasattr(clf, "predict_proba") else clf.predict(X)
        try:
            auc = float(metrics.roc_auc_score(y, probs))
        except Exception:
            auc = 0.5
        return auc, probs

    n_splits = min(n_splits, min(counts))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    oof_probs = np.zeros(len(y), dtype=np.float32)

    for train_idx, val_idx in skf.split(X, y):
        X_tr, y_tr = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]
        clf.fit(X_tr, y_tr)
        oof_probs[val_idx] = clf.predict_proba(X_val)[:, 1]

    try:
        auc = float(metrics.roc_auc_score(y, oof_probs))
    except Exception:
        auc = 0.5
    return auc, oof_probs


def train_learned_fusion(csv_path: Path, out_dir: Path, is_demo: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    X, y, hand_tuned_probs, check_cols = load_dataset_from_csv(csv_path)

    print(f"Loaded {len(y)} samples ({np.sum(y==0)} genuine, {np.sum(y==1)} manipulated) with {len(check_cols)} check features.")

    # 1. Baseline: Hand-tuned score AUC
    try:
        if len(np.unique(y)) > 1:
            hand_tuned_auc = float(metrics.roc_auc_score(y, hand_tuned_probs))
        else:
            hand_tuned_auc = 1.0
    except Exception:
        hand_tuned_auc = 0.5

    # 2. Logistic Regression Fusion
    lr = LogisticRegression(C=1.0, max_iter=500, random_state=42)
    lr_auc, lr_probs = run_cross_val_auc(lr, X, y)

    # 3. Gradient Boosting Fusion
    gb = GradientBoostingClassifier(n_estimators=40, max_depth=3, learning_rate=0.1, random_state=42)
    gb_auc, gb_probs = run_cross_val_auc(gb, X, y)

    # Fit final Logistic Regression model on all data to export weights
    lr_final = LogisticRegression(C=1.0, max_iter=500, random_state=42)
    lr_final.fit(X, y)

    # ---------------------------------------------------------------------------
    # Feature Ablation: Remove one check at a time
    # ---------------------------------------------------------------------------
    ablation_records = []
    print("\nRunning feature ablation study (removing one check at a time)...")
    for idx, c_name in enumerate(check_cols):
        # Keep all features except idx
        sub_X = np.delete(X, idx, axis=1)
        if sub_X.shape[1] == 0:
            sub_X = np.zeros((X.shape[0], 1))
        ablated_auc, _ = run_cross_val_auc(LogisticRegression(max_iter=500, random_state=42), sub_X, y)
        delta = round(lr_auc - ablated_auc, 4)
        ablation_records.append({
            "removed_check": c_name.replace("check_", ""),
            "ablated_auc": round(ablated_auc, 4),
            "delta_auc": delta,
            "importance": "High" if delta > 0.05 else ("Moderate" if delta > 0 else "Neutral"),
        })

    # Sort ablation by highest drop in AUC
    ablation_records.sort(key=lambda x: x["delta_auc"], reverse=True)

    # Save ablation_table.csv
    ablation_csv_path = out_dir / "ablation_table.csv"
    with open(ablation_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["removed_check", "ablated_auc", "delta_auc", "importance"])
        writer.writeheader()
        writer.writerows(ablation_records)

    # ---------------------------------------------------------------------------
    # Export Model Coefficients for Runtime Inference
    # ---------------------------------------------------------------------------
    model_export_dir = config.STORAGE_DIR / "models"
    model_export_dir.mkdir(parents=True, exist_ok=True)
    model_export_file = model_export_dir / "fusion_model.json"

    model_spec = {
        "model_type": "Logistic Regression Fusion",
        "trained_on": "Demo Benchmark" if is_demo else "Real Benchmark Dataset",
        "is_demonstration": is_demo,
        "features": [c.replace("check_", "") for c in check_cols],
        "intercept": float(lr_final.intercept_[0]),
        "coefficients": {c.replace("check_", ""): float(coef) for c, coef in zip(check_cols, lr_final.coef_[0])},
        "performance": {
            "hand_tuned_auc": round(hand_tuned_auc, 4),
            "logistic_regression_auc": round(lr_auc, 4),
            "gradient_boosting_auc": round(gb_auc, 4),
        },
        "disclaimer": "This ML model is trained on benchmark evaluation data and provides an optional statistical confidence indicator. It is only as good as its training data and never replaces deterministic forensic scoring.",
    }
    with open(model_export_file, "w", encoding="utf-8") as f:
        json.dump(model_spec, f, indent=2)

    with open(out_dir / "fusion_comparison.json", "w", encoding="utf-8") as f:
        json.dump(model_spec, f, indent=2)

    # ---------------------------------------------------------------------------
    # Plot: ROC Curve Comparison
    # ---------------------------------------------------------------------------
    plt.figure(figsize=(6.5, 5))
    if len(np.unique(y)) > 1:
        fpr_ht, tpr_ht, _ = metrics.roc_curve(y, hand_tuned_probs)
        fpr_lr, tpr_lr, _ = metrics.roc_curve(y, lr_probs)
        fpr_gb, tpr_gb, _ = metrics.roc_curve(y, gb_probs)

        plt.plot(fpr_ht, tpr_ht, label=f"Hand-Tuned Heuristic (AUC = {hand_tuned_auc:.3f})", color="#6b7280", lw=2, linestyle="--")
        plt.plot(fpr_lr, tpr_lr, label=f"Logistic Regression Fusion (AUC = {lr_auc:.3f})", color="#2563eb", lw=2.5)
        plt.plot(fpr_gb, tpr_gb, label=f"Gradient Boosting Fusion (AUC = {gb_auc:.3f})", color="#10b981", lw=2)
    else:
        plt.plot([0, 1], [1, 1], label="Single Class in dataset", color="#2563eb", lw=2)

    plt.plot([0, 1], [0, 1], color="#d1d5db", linestyle=":", label="Random Chance (0.500)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Learned Fusion vs. Hand-Tuned Heuristic ROC", fontsize=11, fontweight="bold")
    plt.legend(loc="lower right")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(out_dir / "fusion_roc_comparison.png", dpi=200)
    plt.close()

    # Terminal Report
    print("\n" + "=" * 65)
    print("LEARNED FUSION MODEL PERFORMANCE COMPARISON")
    print("=" * 65)
    print(f"Hand-Tuned Forensic Score ROC-AUC:   {hand_tuned_auc:.3f}")
    print(f"Logistic Regression Fusion ROC-AUC:   {lr_auc:.3f}")
    print(f"Gradient Boosting Fusion ROC-AUC:     {gb_auc:.3f}")
    print("-" * 65)
    print("TOP ABLATION DROPS (Checks that matter most):")
    for ab in ablation_records[:5]:
        print(f"  - Without {ab['removed_check']:<24}: AUC = {ab['ablated_auc']:.3f} (Drop: {ab['delta_auc']:+.3f})")
    print("-" * 65)
    print(f"Exported runtime model: {model_export_file}")
    print(f"Saved ablation table:   {ablation_csv_path}")
    print(f"Saved comparison plot:  {out_dir / 'fusion_roc_comparison.png'}")
    print("=" * 65 + "\n")

    return model_spec


def main():
    parser = argparse.ArgumentParser(description="Train learned fusion and perform ablation on forensic evaluation output.")
    parser.add_argument("--results-csv", type=str, default=None, help="Path to results.csv from evaluate.py")
    parser.add_argument("--out-dir", type=str, default="fusion_results", help="Directory to save outputs")
    parser.add_argument("--demo", action="store_true", help="Generate demo evaluation if CSV not provided")

    args = parser.parse_args()
    out_dir = Path(args.out_dir).resolve()

    csv_path = None
    if args.results_csv and Path(args.results_csv).exists():
        csv_path = Path(args.results_csv).resolve()
    else:
        # Check standard locations
        candidates = [
            Path("evaluation_results/results.csv"),
            Path("eval_demo_out/results.csv"),
        ]
        for c in candidates:
            if c.exists():
                csv_path = c.resolve()
                break

    if not csv_path or args.demo:
        print("No evaluation CSV found; running evaluate.py in demo mode first...")
        from scripts import evaluate
        demo_eval_dir = Path(tempfile.gettempdir()) / "eip_eval_fusion_demo"
        demo_out_dir = Path("eval_demo_out").resolve()
        evaluate.build_demo_dataset(demo_eval_dir)
        evaluate.evaluate_dataset(demo_eval_dir, demo_out_dir, is_demo=True)
        csv_path = demo_out_dir / "results.csv"

    train_learned_fusion(csv_path, out_dir, is_demo=True)


if __name__ == "__main__":
    main()
