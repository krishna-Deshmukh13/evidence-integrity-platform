"""Tests for Group C: Legal and Provenance (Signed PDFs, Report Verification, Custody Anchoring, Section 63 BSA 2023, Hindi/Marathi)."""
import json
import pytest
from app import signer
from app.models import Evidence, Case, ExportedReport, CustodyEvent
from app.database import SessionLocal


def test_key_generation_and_fingerprint():
    signer.ensure_keys()
    fp = signer.get_signer_fingerprint()
    assert fp is not None
    assert len(fp) == 32 * 2 + 31  # 32 bytes hex separated by colons
    assert ":" in fp


def test_sign_pdf_bytes():
    from app.report_pdf import _build, get_styles
    from reportlab.platypus import Paragraph
    sty = get_styles("en")
    pdf_bytes = _build([Paragraph("Test Forensic Report", sty["H1"])], "Test")
    signed_pdf, h = signer.sign_pdf_bytes(pdf_bytes)
    assert len(signed_pdf) > len(pdf_bytes)
    assert len(h) == 64


def test_report_verification_endpoint(admin):
    # 1. Non-existent hash
    r = admin.get("/api/reports/verify?hash=0000000000000000000000000000000000000000000000000000000000000000")
    assert r.status_code == 200
    data = r.json()
    assert data["match"] is False

    # 2. Create case and evidence
    cid = admin.post("/api/cases", json={"reference": "CR-VERIFY-1", "title": "Verification Case"}).json()["id"]
    db = SessionLocal()
    ev = Evidence(
        case_id=cid, filename="test_doc.pdf", stored_name="test_doc.pdf", media_type="document",
        sha256="a" * 64, status="done", score=85, verdict="Consistent",
        received_at="2024-05-18T10:00:00.000000Z",
    )
    db.add(ev)
    db.commit()
    ev_id = ev.id

    c1 = CustodyEvent(evidence_id=ev_id, seq=1, action="Acquired", actor="meera", at="2024-05-18T10:00:00.000000Z",
                      file_hash="a" * 64, prev_hash="0" * 64, event_hash="e1" * 32, note="File ingested")
    db.add(c1)
    db.commit()
    db.close()

    # Export report
    res = admin.get(f"/api/evidence/{ev_id}/report.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"

    # Query verify endpoint using the registered record
    db = SessionLocal()
    rec = db.query(ExportedReport).filter(ExportedReport.evidence_id == ev_id).first()
    assert rec is not None
    rep_hash = rec.report_sha256
    doc_token = rec.doc_token
    db.close()

    # Test verification by report SHA-256
    r_hash = admin.get(f"/api/reports/verify?hash={rep_hash}")
    assert r_hash.status_code == 200
    d_hash = r_hash.json()
    assert d_hash["match"] is True
    assert d_hash["case_reference"] == "CR-VERIFY-1"
    assert "test_doc.pdf" not in d_hash.get("message", "")  # No evidence filename leaked

    # Test verification by document token
    r_tok = admin.get(f"/api/reports/verify?hash={doc_token}")
    assert r_tok.status_code == 200
    d_tok = r_tok.json()
    assert d_tok["match"] is True


def test_section63_and_multilingual(admin):
    cid = admin.post("/api/cases", json={"reference": "CR-SEC63-1", "title": "Sec63 Case"}).json()["id"]
    db = SessionLocal()
    ev = Evidence(
        case_id=cid, filename="cctv_frame.jpg", stored_name="cctv_frame.jpg", media_type="image",
        sha256="b" * 64, status="done", score=72, verdict="Needs review",
        received_at="2024-05-18T10:00:00.000000Z",
    )
    db.add(ev)
    db.commit()
    ev_id = ev.id

    c1 = CustodyEvent(evidence_id=ev_id, seq=1, action="Acquired", actor="meera", at="2024-05-18T10:00:00.000000Z",
                      file_hash="b" * 64, prev_hash="0" * 64, event_hash="e2" * 32, note="Ingestion")
    db.add(c1)
    db.commit()
    db.close()

    # Section 63 draft certificate in English
    s63_en = admin.get(f"/api/evidence/{ev_id}/section63.pdf?lang=en")
    assert s63_en.status_code == 200
    assert s63_en.headers["content-type"] == "application/pdf"
    assert len(s63_en.content) > 1000

    # Section 63 draft certificate in Hindi
    s63_hi = admin.get(f"/api/evidence/{ev_id}/section63.pdf?lang=hi")
    assert s63_hi.status_code == 200
    assert len(s63_hi.content) > 1000

    # Section 63 draft certificate in Marathi
    s63_mr = admin.get(f"/api/evidence/{ev_id}/section63.pdf?lang=mr")
    assert s63_mr.status_code == 200
    assert len(s63_mr.content) > 1000

    # Case bundle in Hindi
    bundle_hi = admin.get(f"/api/cases/{cid}/report.pdf?lang=hi")
    assert bundle_hi.status_code == 200
    assert len(bundle_hi.content) > 1000

    # Check custody event was written
    ev_updated = admin.get(f"/api/evidence/{ev_id}").json()
    actions = [ce["action"] for ce in ev_updated["custody"]]
    assert "Section 63 certificate exported" in actions


def test_custody_anchor_export_and_verify(admin):
    # Setup some evidence
    cid = admin.post("/api/cases", json={"reference": "CR-ANCHOR-1", "title": "Anchor Case"}).json()["id"]
    db = SessionLocal()
    ev = Evidence(
        case_id=cid, filename="chain_test.wav", stored_name="chain_test.wav", media_type="audio",
        sha256="c" * 64, status="done", score=95, verdict="Consistent",
        received_at="2024-05-18T10:00:00.000000Z",
    )
    db.add(ev)
    db.commit()
    ev_id = ev.id

    c1 = CustodyEvent(evidence_id=ev_id, seq=1, action="Acquired", actor="meera", at="2024-05-18T10:00:00.000000Z",
                      file_hash="c" * 64, prev_hash="0" * 64, event_hash="e3" * 32, note="Ingestion")
    db.add(c1)
    db.commit()
    db.close()

    # 1. Export anchor
    res = admin.get("/api/custody/anchor")
    assert res.status_code == 200
    anchor = res.json()

    assert anchor["platform"] == "Evidence Integrity Platform"
    assert "signature" in anchor
    assert "chains" in anchor
    assert anchor["total_chains"] > 0

    # 2. Verify unmodified anchor
    ver_res = admin.post("/api/custody/verify-anchor", json=anchor)
    assert ver_res.status_code == 200
    v = ver_res.json()
    assert v["ok"] is True
    assert v["signature_valid"] is True
    assert v["matching_chains"] == anchor["total_chains"]
    assert len(v["discrepancies"]) == 0

    # 3. Tamper with anchor payload to ensure signature check fails
    tampered = dict(anchor)
    tampered["total_chains"] = 99999
    tampered_res = admin.post("/api/custody/verify-anchor", json=tampered)
    assert tampered_res.status_code == 200
    vt = tampered_res.json()
    assert vt["ok"] is False
    assert vt["signature_valid"] is False
