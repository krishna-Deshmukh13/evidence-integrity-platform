"""Tests for Group D: Research and Evaluation (Evaluation framework, Robustness, Learned Fusion, Examiner Feedback)."""
import json
from pathlib import Path
import tempfile
import pytest

from app.database import SessionLocal
from app.models import Evidence, Case, Finding, CustodyEvent
from scripts import evaluate, robustness, ml_fusion


def test_evaluation_framework_metrics():
    temp_dir = Path(tempfile.gettempdir()) / "eip_test_eval_run"
    out_dir = Path(tempfile.gettempdir()) / "eip_test_eval_out"

    # Build demo dataset
    evaluate.build_demo_dataset(temp_dir)
    summary = evaluate.evaluate_dataset(temp_dir, out_dir, is_demo=True)

    assert summary is not None
    assert summary["total_files"] > 0
    assert "accuracy" in summary["overall_metrics"]
    assert "precision" in summary["overall_metrics"]
    assert "recall" in summary["overall_metrics"]
    assert "f1_score" in summary["overall_metrics"]
    assert "roc_auc" in summary["overall_metrics"]

    # Verify output files
    assert (out_dir / "results.csv").exists()
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "confusion_matrix.png").exists()
    assert (out_dir / "roc_curve.png").exists()
    assert (out_dir / "per_check_metrics.png").exists()


def test_robustness_suite(samples):
    out_dir = Path(tempfile.gettempdir()) / "eip_test_robustness_out"
    target = samples / "photo_tampered.jpg"

    results = robustness.evaluate_robustness(target, out_dir)
    assert len(results) >= 8  # baseline + 3 jpegs + 2 resizes + screenshot + 2 noises
    assert (out_dir / "robustness_table.csv").exists()
    assert (out_dir / "robustness_degradation.png").exists()
    assert (out_dir / "robustness_heatmap.png").exists()


def test_ml_fusion_and_ablation():
    eval_csv = Path(tempfile.gettempdir()) / "eip_test_eval_out" / "results.csv"
    out_dir = Path(tempfile.gettempdir()) / "eip_test_fusion_out"

    if not eval_csv.exists():
        temp_dir = Path(tempfile.gettempdir()) / "eip_test_eval_run"
        evaluate.build_demo_dataset(temp_dir)
        evaluate.evaluate_dataset(temp_dir, eval_csv.parent, is_demo=True)

    model_spec = ml_fusion.train_learned_fusion(eval_csv, out_dir, is_demo=True)
    assert model_spec is not None
    assert "logistic_regression_auc" in model_spec["performance"]
    assert "coefficients" in model_spec
    assert (out_dir / "ablation_table.csv").exists()
    assert (out_dir / "fusion_roc_comparison.png").exists()


def test_examiner_feedback_flow(admin):
    # Setup case and evidence
    cid = admin.post("/api/cases", json={"reference": "CR-FEEDBACK-1", "title": "Feedback Case"}).json()["id"]
    db = SessionLocal()
    ev = Evidence(
        case_id=cid, filename="doc_check.pdf", stored_name="doc_check.pdf", media_type="document",
        sha256="d" * 64, status="done", score=65, verdict="Needs review",
        received_at="2024-05-18T10:00:00.000000Z",
    )
    db.add(ev)
    db.commit()
    ev_id = ev.id

    c1 = CustodyEvent(evidence_id=ev_id, seq=1, action="Acquired", actor="meera", at="2024-05-18T10:00:00.000000Z",
                      file_hash="d" * 64, prev_hash="0" * 64, event_hash="e4" * 32, note="Ingestion")
    db.add(c1)

    f1 = Finding(evidence_id=ev_id, category="document", check="incremental_updates", severity="medium",
                 penalty=14, title="Multiple %%EOF incremental updates", detail="File modified after signature")
    db.add(f1)
    db.commit()
    f1_id = f1.id
    db.close()

    # 1. Confirm finding
    res_conf = admin.post(f"/api/evidence/{ev_id}/findings/{f1_id}/feedback",
                          json={"decision": "confirmed", "note": "Verified incremental byte markers manually"})
    assert res_conf.status_code == 200
    d_conf = res_conf.json()
    assert d_conf["feedback"] == "confirmed"
    assert "meera" in d_conf["feedback_by"].lower()

    # Verify custody event was written
    ev_updated = admin.get(f"/api/evidence/{ev_id}").json()
    actions = [ce["action"] for ce in ev_updated["custody"]]
    assert "Finding feedback" in actions

    # Verify feedback serialization on evidence
    finding_obj = next(f for f in ev_updated["findings"] if f["id"] == f1_id)
    assert finding_obj["feedback"] == "confirmed"

    # 2. Reject finding
    res_rej = admin.post(f"/api/evidence/{ev_id}/findings/{f1_id}/feedback",
                         json={"decision": "rejected", "note": "Harmless PDF reader annotation"})
    assert res_rej.status_code == 200
    assert res_rej.json()["feedback"] == "rejected"

    # 3. Export CSV for retraining
    csv_res = admin.get("/api/examiner-feedback/export.csv")
    assert csv_res.status_code == 200
    assert csv_res.headers["content-type"].startswith("text/csv")
    csv_text = csv_res.text
    assert "incremental_updates" in csv_text
    assert "rejected" in csv_text
    assert "Harmless PDF reader annotation" in csv_text
