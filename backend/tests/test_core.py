"""Custody chain, scoring, and image analysis."""
import json

from app import custody, scoring
from app.database import SessionLocal
from app.models import CustodyEvent, Evidence


def test_scoring_caps_and_bands():
    f = [{"category": "metadata", "severity": "medium", "penalty": 14},
         {"category": "metadata", "severity": "medium", "penalty": 14},
         {"category": "metadata", "severity": "high", "penalty": 26},
         {"category": "pixel", "severity": "high", "penalty": 30}]
    score, bd, verdict = scoring.compute(f)
    assert bd["metadata"] == 30 and bd["pixel"] == 30      # metadata capped at 30
    assert score == 40 and verdict == "Likely manipulated"
    assert scoring.verdict_for(80) == "Consistent" and scoring.verdict_for(79) == "Needs review"
    assert scoring.verdict_for(49) == "Likely manipulated"
    assert scoring.compute([])[0] == 100


def test_scoring_worked_example_from_guide():
    f = [{"category": "pixel", "severity": "high", "penalty": 30},
         {"category": "metadata", "severity": "medium", "penalty": 14},
         {"category": "metadata", "severity": "medium", "penalty": 14},
         {"category": "ai", "severity": "info", "penalty": 0}]
    assert scoring.compute(f)[0] == 42


def _upload(client, case_id, path):
    with open(path, "rb") as fh:
        r = client.post(f"/api/cases/{case_id}/evidence", files={"file": (path.name, fh, "image/jpeg")})
    assert r.status_code == 200, r.text
    return r.json()


def _case(client):
    return client.post("/api/cases", json={"reference": "CR-1", "title": "Test"}).json()["id"]


def test_tampered_scores_lower_than_original(admin, samples):
    cid = _case(admin)
    orig = _upload(admin, cid, samples / "photo_original.jpg")
    tam = _upload(admin, cid, samples / "photo_tampered.jpg")
    o = admin.get(f"/api/evidence/{orig['id']}").json()
    t = admin.get(f"/api/evidence/{tam['id']}").json()
    assert o["status"] == "done" and t["status"] == "done"
    assert o["score"] >= 80 and o["verdict"] == "Consistent", o["findings"]
    assert t["score"] < o["score"] - 25, (t["score"], t["findings"])
    checks = {f["check"] for f in t["findings"] if f["severity"] != "info"}
    assert "copy_move" in checks and "software" in checks and "modified_after_capture" in checks
    clone = next(f for f in t["findings"] if f["check"] == "copy_move")
    assert clone["location"]["kind"] == "region" and clone["penalty"] == 30
    assert "clone.png" in t["artifacts"] and "ela.png" in t["artifacts"]


def test_stripped_exif_is_low_flag(admin, samples):
    cid = _case(admin)
    e = _upload(admin, cid, samples / "photo_stripped.jpg")
    d = admin.get(f"/api/evidence/{e['id']}").json()
    assert any(f["check"] == "exif_stripped" for f in d["findings"])
    assert d["score"] >= 80


def test_custody_chain_detects_tampering(admin, samples):
    cid = _case(admin)
    e = _upload(admin, cid, samples / "photo_original.jpg")
    r = admin.post(f"/api/evidence/{e['id']}/verify").json()
    assert r["ok"] and r["file_ok"] and r["chain_ok"]
    d = admin.get(f"/api/evidence/{e['id']}").json()
    actions = [c["action"] for c in d["custody"]]
    assert actions[:3] == ["Received", "Analysis started", "Analysis completed"]
    assert actions[-1] == "Integrity verified"
    # edit an old event directly in the database -> chain breaks
    db = SessionLocal()
    ev = db.get(CustodyEvent, db.query(CustodyEvent).filter_by(evidence_id=e["id"], seq=2).one().id)
    ev.note = "edited later"
    db.commit()
    db.close()
    bad = admin.post(f"/api/evidence/{e['id']}/verify").json()
    assert not bad["ok"] and bad["broken_at"] == 2


def test_custody_detects_changed_file(admin, samples):
    from app import config
    cid = _case(admin)
    e = _upload(admin, cid, samples / "photo_original.jpg")
    db = SessionLocal()
    ev = db.get(Evidence, e["id"])
    with open(config.UPLOAD_DIR / ev.stored_name, "ab") as fh:
        fh.write(b"x")
    db.close()
    r = admin.post(f"/api/evidence/{e['id']}/verify").json()
    assert not r["ok"] and not r["file_ok"] and r["chain_ok"]
    # re-analysis notices the change and penalises it
    admin.post(f"/api/evidence/{e['id']}/reanalyze")
    d = admin.get(f"/api/evidence/{e['id']}").json()
    assert any(f["check"] == "hash_mismatch" for f in d["findings"])


def test_event_hash_formula():
    h1 = custody.compute_event_hash(1, 1, "Received", "a", "t", "f" * 64, "0" * 64, "n")
    h2 = custody.compute_event_hash(1, 1, "Received", "a", "t", "f" * 64, "0" * 64, "n2")
    assert h1 != h2 and len(h1) == 64


def test_unsupported_and_random_names(admin, samples):
    cid = _case(admin)
    r = admin.post(f"/api/cases/{cid}/evidence", files={"file": ("evil.exe", b"MZ", "application/x-msdownload")})
    assert r.status_code == 400
    r = admin.post(f"/api/cases/{cid}/evidence", files={"file": ("../../x.jpg", b"notimage", "image/jpeg")})
    assert r.status_code == 200
    db = SessionLocal()
    ev = db.query(Evidence).order_by(Evidence.id.desc()).first()
    assert "/" not in ev.stored_name and ".." not in ev.stored_name and ev.filename == "x.jpg"
    assert ev.status == "failed"          # not a real image: fails cleanly, file kept
    db.close()


def test_phash_stored(admin, samples):
    cid = _case(admin)
    e = _upload(admin, cid, samples / "photo_original.jpg")
    t = _upload(admin, cid, samples / "photo_tampered.jpg")
    from app.similarity import hamming
    db = SessionLocal()
    a, b = db.get(Evidence, e["id"]).phash, db.get(Evidence, t["id"]).phash
    db.close()
    assert len(a) == 64 and hamming(a, b) <= 16
