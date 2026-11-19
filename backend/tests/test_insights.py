"""Tests for upgraded insights and dashboard endpoints."""
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import Evidence, Finding, Case, User, CustodyEvent
from tests.conftest import make_user, login, PW


def test_dashboard_upgraded_metrics(admin, samples):
    # Setup test case and evidence
    cid = admin.post("/api/cases", json={"reference": "CR-DASH-1", "title": "Dashboard Test Case"}).json()["id"]
    with open(samples / "photo_original.jpg", "rb") as f:
        admin.post(f"/api/cases/{cid}/evidence", files={"file": ("photo_original.jpg", f, "image/jpeg")})

    r = admin.get("/api/dashboard")
    assert r.status_code == 200
    d = r.json()

    # Score bands
    assert "score_bands" in d
    assert "0_49" in d["score_bands"]
    assert "50_79" in d["score_bands"]
    assert "80_100" in d["score_bands"]

    # Verdicts by media type
    assert "verdicts_by_media_type" in d
    assert "image" in d["verdicts_by_media_type"]
    assert "Consistent" in d["verdicts_by_media_type"]["image"]

    # Top findings
    assert "top_findings" in d
    assert isinstance(d["top_findings"], list)

    # Custody health
    assert "custody_health" in d
    assert d["custody_health"]["chains_intact"] >= 1
    assert d["custody_health"]["chains_broken"] == 0
    assert d["custody_health"]["status"] == "healthy"

    # Live queue
    assert "live_queue" in d
    assert "active" in d["live_queue"]
    assert "number_waiting" in d["live_queue"]
    assert "report_model_status" in d["live_queue"]

    # Live queue standalone endpoint
    lq = admin.get("/api/dashboard/live-queue").json()
    assert "active" in lq
    assert "stage" in lq

    # Needs attention
    assert "needs_attention" in d
    assert "total_count" in d["needs_attention"]
    assert "items" in d["needs_attention"]

    # Per-case summaries
    assert "case_summaries" in d
    assert len(d["case_summaries"]) >= 1
    cs = d["case_summaries"][0]
    assert "file_count" in cs
    assert "verdicts" in cs
    assert "Consistent" in cs["verdicts"]


def test_custody_verify_all_and_role_enforcement(admin, samples):
    # Create investigator and viewer
    make_user(admin, "test_inv", "investigator")
    make_user(admin, "test_view", "viewer")

    # Add evidence directly to db
    db = SessionLocal()
    c = Case(reference="CR-INV-1", title="Inv Case")
    db.add(c)
    db.flush()
    ev = Evidence(
        case_id=c.id, filename="test.jpg", stored_name="test.jpg", media_type="image",
        sha256="d" * 64, status="done"
    )
    db.add(ev)
    db.flush()
    from app import custody
    custody.add_event(db, ev, "Received", "System", "Test intake", file_hash="d" * 64)
    db.commit()
    db.close()

    # Viewer should be forbidden (403)
    login(admin, "test_view")
    r_view = admin.post("/api/custody/verify-all")
    assert r_view.status_code == 403

    # Investigator should succeed (200)
    login(admin, "test_inv")
    r_inv = admin.post("/api/custody/verify-all")
    assert r_inv.status_code == 200
    res = r_inv.json()
    assert res["chains_intact"] >= 1
    assert res["chains_broken"] == 0
    assert res["status"] == "healthy"
    assert res["last_checked_at"] is not None

    # Check that custody health reflects last_checked_at
    dash = admin.get("/api/dashboard").json()
    assert dash["custody_health"]["last_checked_at"] is not None


def test_needs_attention_categories(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-ATTN", "title": "Attention Case"}).json()["id"]
    db = SessionLocal()

    # 1. Failed evidence
    e_fail = Evidence(
        case_id=cid, filename="bad.mp4", stored_name="bad.mp4", media_type="video",
        sha256="a" * 64, status="failed", error="Decoding error"
    )
    # 2. Flagged and unreviewed > 3 days
    old_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    e_unrev = Evidence(
        case_id=cid, filename="old_flagged.jpg", stored_name="old.jpg", media_type="image",
        sha256="b" * 64, status="done", score=45, verdict="Likely manipulated",
        review_status="not_reviewed", received_at=old_time
    )
    # 3. Score < 50 with no assignee
    e_unassigned = Evidence(
        case_id=cid, filename="unassigned.jpg", stored_name="unass.jpg", media_type="image",
        sha256="c" * 64, status="done", score=30, verdict="Likely manipulated",
        review_status="not_reviewed", assignee_id=None
    )
    db.add_all([e_fail, e_unrev, e_unassigned])
    db.commit()
    db.close()

    dash = admin.get("/api/dashboard").json()
    na = dash["needs_attention"]
    assert na["total_count"] >= 3
    reasons = {item["attention_reason"] for item in na["items"]}
    assert "failed" in reasons
    assert "unreviewed_3d" in reasons
    assert "unassigned_low_score" in reasons
