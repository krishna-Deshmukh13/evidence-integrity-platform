"""Tests for Case Intelligence: Timeline, Graph, GPS view, Summary, Score Sensitivity, Known Manipulated."""
import json
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import Case, Evidence, CustodyEvent, Finding, KnownManipulated
from tests.conftest import make_user, login


def test_timeline_and_contradictions(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-TIMELINE-1", "title": "Timeline Test"}).json()["id"]

    db = SessionLocal()
    e1 = Evidence(
        case_id=cid, filename="normal.jpg", stored_name="normal.jpg", media_type="image",
        sha256="1" * 64, status="done", score=90, verdict="Consistent",
        received_at="2024-05-18T10:00:00.000000Z",
        details=json.dumps({"exif": {"DateTimeOriginal": "2024:05:18 09:30:00", "ModifyDate": "2024:05:18 09:45:00"}})
    )
    e2 = Evidence(
        case_id=cid, filename="tampered_time.jpg", stored_name="tampered_time.jpg", media_type="image",
        sha256="2" * 64, status="done", score=45, verdict="Likely manipulated",
        received_at="2024-05-18T12:00:00.000000Z",
        details=json.dumps({"exif": {"DateTimeOriginal": "2024:05:18 10:00:00", "ModifyDate": "2024:05:18 08:00:00"}})
    )
    e3 = Evidence(
        case_id=cid, filename="post_dated.jpg", stored_name="post_dated.jpg", media_type="image",
        sha256="3" * 64, status="done", score=40, verdict="Likely manipulated",
        received_at="2024-05-18T10:00:00.000000Z",
        details=json.dumps({"exif": {"DateTimeOriginal": "2024:05:18 15:00:00"}})
    )
    future_str = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y:%m:%d %H:%M:%S")
    e4 = Evidence(
        case_id=cid, filename="future.jpg", stored_name="future.jpg", media_type="image",
        sha256="4" * 64, status="done", score=50, verdict="Needs review",
        received_at="2024-05-18T10:00:00.000000Z",
        details=json.dumps({"exif": {"DateTimeOriginal": future_str}})
    )

    db.add_all([e1, e2, e3, e4])
    db.commit()

    from app import custody
    custody.add_event(db, e1, "Received", "Investigator", "Intake file verified", file_hash="1" * 64)
    db.commit()
    db.close()

    r = admin.get(f"/api/cases/{cid}/timeline")
    assert r.status_code == 200
    res = r.json()

    assert res["case_id"] == cid
    assert res["total_events"] >= 5

    contra = res["contradictions"]
    kinds = {c["kind"] for c in contra}
    assert "modified_before_created" in kinds
    assert "captured_after_upload" in kinds
    assert "future_date" in kinds

    for c in contra:
        assert "evidence_id" in c
        assert "filename" in c
        assert "message" in c


def test_evidence_graph_links(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-GRAPH-1", "title": "Graph Test"}).json()["id"]

    db = SessionLocal()
    # e1 & e2 share same software and camera
    e1 = Evidence(
        case_id=cid, filename="cam1.jpg", stored_name="cam1.jpg", media_type="image",
        sha256="a" * 64, phash="0000000000000000", status="done", score=85, verdict="Consistent",
        details=json.dumps({"exif": {"Make": "Sony", "Model": "A7 III", "Software": "Adobe Lightroom 12.0"}})
    )
    e2 = Evidence(
        case_id=cid, filename="cam2.jpg", stored_name="cam2.jpg", media_type="image",
        sha256="b" * 64, phash="0000000000000001", status="done", score=80, verdict="Consistent",
        details=json.dumps({"exif": {"Make": "Sony", "Model": "A7 III", "Software": "Adobe Lightroom 12.0"}})
    )
    # e3 shares author with a docx file
    e3 = Evidence(
        case_id=cid, filename="doc1.pdf", stored_name="doc1.pdf", media_type="document",
        sha256="c" * 64, status="done", score=75, verdict="Needs review",
        details=json.dumps({"properties": {"Author": "Forensic Examiner Smith"}})
    )
    e4 = Evidence(
        case_id=cid, filename="doc2.docx", stored_name="doc2.docx", media_type="document",
        sha256="d" * 64, status="done", score=70, verdict="Needs review",
        details=json.dumps({"properties": {"Author": "Forensic Examiner Smith"}})
    )
    # e5 has GPS within 50m of e6
    e5 = Evidence(
        case_id=cid, filename="geo1.jpg", stored_name="geo1.jpg", media_type="image",
        sha256="e" * 64, status="done", score=90, verdict="Consistent",
        details=json.dumps({"exif": {"GPSLatitude": 37.7749, "GPSLongitude": -122.4194}})
    )
    e6 = Evidence(
        case_id=cid, filename="geo2.jpg", stored_name="geo2.jpg", media_type="image",
        sha256="f" * 64, status="done", score=90, verdict="Consistent",
        details=json.dumps({"exif": {"GPSLatitude": 37.7750, "GPSLongitude": -122.4195}})
    )

    db.add_all([e1, e2, e3, e4, e5, e6])
    db.commit()
    db.close()

    r = admin.get(f"/api/cases/{cid}/graph")
    assert r.status_code == 200
    graph = r.json()

    assert len(graph["nodes"]) == 6
    edge_types = {e["type"] for e in graph["edges"]}
    assert "software" in edge_types
    assert "camera" in edge_types
    assert "phash" in edge_types
    assert "author" in edge_types
    assert "gps_proximity" in edge_types

    # Cross-case graph endpoint
    cross = admin.get("/api/graph").json()
    assert len(cross["nodes"]) >= 6


def test_gps_view_and_anomaly(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-GPS-1", "title": "GPS Test"}).json()["id"]

    db = SessionLocal()
    # Cluster in San Francisco
    g1 = Evidence(
        case_id=cid, filename="sf1.jpg", stored_name="sf1.jpg", media_type="image",
        sha256="11" * 32, status="done", score=85, verdict="Consistent",
        details=json.dumps({"exif": {"GPSLatitude": 37.7749, "GPSLongitude": -122.4194}})
    )
    g2 = Evidence(
        case_id=cid, filename="sf2.jpg", stored_name="sf2.jpg", media_type="image",
        sha256="22" * 32, status="done", score=85, verdict="Consistent",
        details=json.dumps({"exif": {"GPSLatitude": 37.7800, "GPSLongitude": -122.4100}})
    )
    # File in Sacramento (~120 km away, well > 50km threshold)
    g3 = Evidence(
        case_id=cid, filename="sacramento.jpg", stored_name="sacramento.jpg", media_type="image",
        sha256="33" * 32, status="done", score=40, verdict="Likely manipulated",
        details=json.dumps({"exif": {"GPSLatitude": 38.5816, "GPSLongitude": -121.4944}})
    )
    db.add_all([g1, g2, g3])
    db.commit()
    db.close()

    r = admin.get(f"/api/cases/{cid}/gps")
    assert r.status_code == 200
    res = r.json()
    assert res["has_gps"] is True
    assert len(res["points"]) == 3
    assert len(res["anomalies"]) >= 1
    assert any("sacramento.jpg" in a["filename"] and a["distance_km"] > 50 for a in res["anomalies"])


def test_case_summary_endpoint(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-SUM-1", "title": "Summary Test"}).json()["id"]
    r = admin.get(f"/api/cases/{cid}/summary")
    assert r.status_code == 200
    res = r.json()
    assert "summary" in res
    assert "## Summary" in res["summary"]
    assert "## Limitations" in res["summary"]
    assert "model" in res


def test_what_would_change_the_score(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-SENS-1", "title": "Score Sensitivity"}).json()["id"]
    db = SessionLocal()
    ev = Evidence(
        case_id=cid, filename="photo.jpg", stored_name="photo.jpg", media_type="image",
        sha256="55" * 32, status="done", score=40, verdict="Likely manipulated"
    )
    db.add(ev)
    db.flush()
    # Add two findings
    f1 = Finding(evidence_id=ev.id, category="pixel", check="copy_move", severity="high", penalty=30, title="Clone detected")
    f2 = Finding(evidence_id=ev.id, category="metadata", check="software", severity="medium", penalty=14, title="Photoshop edited")
    db.add_all([f1, f2])
    db.commit()
    db.close()

    r = admin.get(f"/api/evidence/{ev.id}")
    assert r.status_code == 200
    data = r.json()
    findings = data["findings"]
    assert len(findings) == 2
    f1_resp = next(f for f in findings if f["check"] == "copy_move")
    assert "score_impact" in f1_resp
    impact = f1_resp["score_impact"]
    # If copy_move (penalty 30) is cleared, score rises from 56 (100 - 30 - 14) to 86 (100 - 14)
    assert impact["points_gained"] > 0
    assert impact["new_score"] > data["score"]
    assert "new_verdict" in impact


def test_known_manipulated_registry(admin):
    # Investigator adds a known manipulated record
    make_user(admin, "investigator_km", "investigator")
    login(admin, "investigator_km")

    target_hash = "99" * 32
    r_add = admin.post("/api/known-manipulated", json={
        "sha256": target_hash,
        "reason": "Known deepfake facial splice from CASIA v2 dataset",
        "filename": "casia_deepfake.jpg"
    })
    assert r_add.status_code == 200
    km_id = r_add.json()["id"]

    # List records
    r_list = admin.get("/api/known-manipulated")
    assert r_list.status_code == 200
    assert any(item["sha256"] == target_hash for item in r_list.json())

    # Delete record (requires admin)
    login(admin, "investigator_km")
    r_del_fail = admin.delete(f"/api/known-manipulated/{km_id}")
    assert r_del_fail.status_code == 403  # Forbidden for investigator

    login(admin, "meera")
    r_del_ok = admin.delete(f"/api/known-manipulated/{km_id}")
    assert r_del_ok.status_code == 200
