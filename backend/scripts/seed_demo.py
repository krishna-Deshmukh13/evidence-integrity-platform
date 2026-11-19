"""
Seed realistic demo data for Evidence Integrity Platform.
Fictional Indian cyber & forensic cases, 40 evidence files across video, audio, image, and documents.
Distribution:
- 5 Suspicious ("Likely manipulated", scores 12-38%)
- 4 Waiting for Review ("Needs review", scores 52-68%)
- 31 Genuine ("Consistent", scores 82-97%)
All files written to disk so Merkle / SHA-256 custody checks pass with 0 broken files.
"""

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("EI_STORAGE_DIR", str(backend_dir / "storage"))

from app import auth, config, custody, database
from app.database import Base, SessionLocal, engine
from app.models import (
    ActivityLog,
    Case,
    CustodyEvent,
    Evidence,
    Finding,
    Note,
    User,
    now_iso,
)

UPLOAD_DIR = config.UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Generate a small valid dummy file of various formats
def make_dummy_file(filename: str, media_type: str, content_seed: str) -> tuple[Path, int, str]:
    path = UPLOAD_DIR / f"seed_{filename}"
    
    # Create realistic content based on type
    if media_type == "image":
        # Create a valid 200x200 PNG
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(140, 160, 200))
        img.save(path, format="PNG")
        raw = path.read_bytes()
    elif media_type == "video":
        # Dummy MP4 header
        raw = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42\x00\x00\x00\x08free" + content_seed.encode("utf-8") * 500
        path.write_bytes(raw)
    elif media_type == "audio":
        # Dummy WAV header
        header = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00"
        raw = header + (content_seed.encode("utf-8") * 300)
        path.write_bytes(raw)
    else: # document / pdf
        # Minimal valid PDF
        pdf_content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Forensic Exhibit) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000056 00000 n \n0000000111 00000 n \n0000000200 00000 n \n"
            b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n296\n%%EOF\n"
        )
        raw = pdf_content + content_seed.encode("utf-8") * 50
        path.write_bytes(raw)
        
    sha = hashlib.sha256(raw).hexdigest()
    # Stored name in uploads
    stored_name = f"{sha[:16]}_{filename}"
    final_path = UPLOAD_DIR / stored_name
    final_path.write_bytes(raw)
    try:
        path.unlink()
    except Exception:
        pass
        
    return final_path, len(raw), sha, stored_name


def run_seed(db=None):
    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True
    
    print("Clearing old evidence records...")
    db.query(ActivityLog).delete()
    db.query(Finding).delete()
    db.query(Note).delete()
    db.query(CustodyEvent).delete()
    db.query(Evidence).delete()
    db.query(Case).delete()
    db.commit()

    # Ensure demo users exist
    users_info = [
        ("krishna", "Krishna Deshmukh", "admin", "Krishna@0305"),
        ("nida", "Nida Latif", "admin", "Nida@2026"),
        ("meera", "Insp. Meera Kulkarni", "investigator", "ram@1234"),
        ("rohan", "SI Rohan Patil", "investigator", "ram@1234"),
        ("kavya", "Kavya Rao", "viewer", "ram@1234"),
    ]
    for uname, fname, urole, raw_pw in users_info:
        user_rec = db.query(User).filter(User.username == uname).first()
        phash = auth.hash_password(raw_pw)
        if not user_rec:
            user_rec = User(
                username=uname,
                password_hash=phash,
                full_name=fname,
                role=urole,
                totp_enabled=False,
                is_active=True
            )
            db.add(user_rec)
        else:
            user_rec.password_hash = phash
            user_rec.role = urole
            user_rec.full_name = fname
            user_rec.totp_enabled = False
            user_rec.is_active = True
    db.commit()

    base_time = datetime.now(timezone.utc) - timedelta(days=20)

    # 8 Fictional Indian Cases
    cases_meta = [
        {
            "reference": "CR-2024-MH-401",
            "title": "Bandra Corporate Payroll Forgery & Invoice Tampering",
            "desc": "Investigation into unauthorized vendor bank modifications and altered invoice PDFs in Mumbai.",
            "investigator": "Insp. Meera Kulkarni",
            "location": "Bandra Kurla Complex, Mumbai",
            "lat": 19.0657, "lon": 72.8687
        },
        {
            "reference": "CR-2024-DL-109",
            "title": "Connaught Place Banking Impersonation & Audio Deepfake",
            "desc": "Wire transfer authorization call spoofing senior bank manager via synthetic speech vocoder.",
            "investigator": "SI Rohan Patil",
            "location": "Connaught Place, New Delhi",
            "lat": 28.6315, "lon": 77.2167
        },
        {
            "reference": "CR-2024-KA-882",
            "title": "Bengaluru IT Registry Document Manipulation",
            "desc": "Alleged tampering of digitized software licensing agreements and property registry seals.",
            "investigator": "Insp. Meera Kulkarni",
            "location": "Electronic City, Bengaluru",
            "lat": 12.8399, "lon": 77.6770
        },
        {
            "reference": "CR-2024-TN-315",
            "title": "Chennai Harbor Logistics Bill of Lading Splicing",
            "desc": "Container shipping dispatch documents altered to disguise prohibited electronics shipment.",
            "investigator": "SI Rohan Patil",
            "location": "Chennai Port Trust, Chennai",
            "lat": 13.0837, "lon": 80.2925
        },
        {
            "reference": "CR-2024-WB-502",
            "title": "Kolkata Commercial Identity Theft & KYC Manipulation",
            "desc": "Digitally modified Aadhaar and PAN card image scans used for fraudulent loan applications.",
            "investigator": "Insp. Meera Kulkarni",
            "location": "Salt Lake Sector V, Kolkata",
            "lat": 22.5804, "lon": 88.4378
        },
        {
            "reference": "CR-2024-GJ-219",
            "title": "Ahmedabad Diamond Exchange Surveillance Feed Interruption",
            "desc": "CCTV camera footage splice and timestamp modification during vault transit window.",
            "investigator": "SI Rohan Patil",
            "location": "Navrangpura, Ahmedabad",
            "lat": 23.0365, "lon": 72.5611
        },
        {
            "reference": "CR-2024-TS-731",
            "title": "Hyderabad Pharma IP Extortion & WhatsApp Audio Clone",
            "desc": "Cloned CEO voice messages threatening release of proprietary vaccine formulation research.",
            "investigator": "Insp. Meera Kulkarni",
            "location": "HITEC City, Hyderabad",
            "lat": 17.4474, "lon": 78.3762
        },
        {
            "reference": "CR-2024-MH-914",
            "title": "Pune Automotive Design CAD Leak & Timestamp Forgery",
            "desc": "Telemetry logs and technical drawings backdated to contest electric vehicle patent priority.",
            "investigator": "SI Rohan Patil",
            "location": "Hinjawadi Infotech Park, Pune",
            "lat": 18.5913, "lon": 73.7389
        }
    ]

    created_cases = []
    for c_idx, c_info in enumerate(cases_meta):
        created_at = (base_time + timedelta(days=c_idx * 2)).isoformat()
        c = Case(
            reference=c_info["reference"],
            title=c_info["title"],
            description=c_info["desc"],
            status="active",
            created_at=created_at
        )
        db.add(c)
        db.flush()
        created_cases.append(c)

    # 40 Evidence Files Plan
    # Format: (case_idx, filename, media_type, verdict, score, review_status, findings_data, uploader, offset_hours)
    files_plan = [
        # Case 0: Bandra Corporate Payroll
        (0, "payroll_disbursement_aug2026.pdf", "document", "Consistent", 94, "reviewed", [("PDF Trailer Structure", "clean", "Incremental updates within normal range.")], "Insp. Meera Kulkarni", 2),
        (0, "vendor_bank_mandate_axis.pdf", "document", "Likely manipulated", 22, "not_reviewed", [("Font Anomaly", "critical", "Font mismatch in beneficiary account field."), ("Hidden Text Layer", "critical", "Underlying layer contains conflicting IFSC code.")], "SI Rohan Patil", 4),
        (0, "reception_desk_cctv.mp4", "video", "Consistent", 91, "reviewed", [("Frame Rate Analysis", "clean", "Continuous 25 FPS stream without dropped frames.")], "Insp. Meera Kulkarni", 6),
        (0, "finance_controller_briefing.wav", "audio", "Consistent", 89, "reviewed", [("Spectrogram Continuity", "clean", "Natural background reverberation and room acoustics.")], "Insp. Meera Kulkarni", 10),
        (0, "cancelled_cheque_leaf.png", "image", "Needs review", 62, "in_review", [("ELA Compression Difference", "warn", "Slight compression artifact around payee signature line.")], "SI Rohan Patil", 12),

        # Case 1: Connaught Place Banking Impersonation
        (1, "manager_call_transfer_auth.wav", "audio", "Likely manipulated", 18, "not_reviewed", [("Neural Vocoder Artifacts", "critical", "Phase vocoder synthesis signatures detected."), ("Synthetic Speech Model", "critical", "Harmonic spectral distribution matches ElevenLabs neural voice.")], "SI Rohan Patil", 1),
        (1, "branch_entry_log_scan.pdf", "document", "Consistent", 96, "reviewed", [], "SI Rohan Patil", 3),
        (1, "rtgs_transfer_slip_50lakh.pdf", "document", "Consistent", 88, "reviewed", [("Layout Verification", "clean", "Standard RBI RTGS format confirmed.")], "SI Rohan Patil", 5),
        (1, "server_room_hallway_feed.mp4", "video", "Consistent", 92, "reviewed", [], "Insp. Meera Kulkarni", 8),
        (1, "suspect_mobile_screenshot.jpg", "image", "Consistent", 85, "reviewed", [], "SI Rohan Patil", 12),

        # Case 2: Bengaluru IT Registry
        (2, "master_service_agreement_v3.pdf", "document", "Needs review", 58, "not_reviewed", [("Metadata Modification Date", "warn", "File modification timestamp precedes creation timestamp.")], "Insp. Meera Kulkarni", 2),
        (2, "notary_stamp_affidavit.jpg", "image", "Likely manipulated", 31, "not_reviewed", [("Copy-Move Forgery", "critical", "Keypoint cluster match between rubber stamp seal and duplicate."), ("Noise Discrepancy", "warn", "High-frequency noise variance in seal area.")], "Insp. Meera Kulkarni", 4),
        (2, "board_meeting_minutes_audio.wav", "audio", "Consistent", 90, "reviewed", [], "Insp. Meera Kulkarni", 6),
        (2, "dataroom_visitor_camera.mp4", "video", "Consistent", 93, "reviewed", [], "SI Rohan Patil", 9),
        (2, "digital_token_cert_export.pdf", "document", "Consistent", 95, "reviewed", [], "Insp. Meera Kulkarni", 14),

        # Case 3: Chennai Harbor Logistics
        (3, "bill_of_lading_cn_7721.pdf", "document", "Likely manipulated", 26, "in_review", [("Text Object Replacement", "critical", "HS Code text object replaced post-generation."), ("Font Kerning Anomaly", "warn", "Discontinuous glyph pitch in cargo description.")], "SI Rohan Patil", 3),
        (3, "container_inspection_wharf.jpg", "image", "Consistent", 92, "reviewed", [], "SI Rohan Patil", 5),
        (3, "gate_inward_weighbridge_cctv.mp4", "video", "Consistent", 89, "reviewed", [], "SI Rohan Patil", 7),
        (3, "customs_broker_wiretap.wav", "audio", "Consistent", 86, "reviewed", [], "Insp. Meera Kulkarni", 11),
        (3, "shipping_manifest_declaration.pdf", "document", "Consistent", 94, "reviewed", [], "SI Rohan Patil", 15),

        # Case 4: Kolkata Commercial Identity Theft
        (4, "pan_card_applicant_scan.jpg", "image", "Likely manipulated", 14, "not_reviewed", [("Error Level Analysis", "critical", "High ELA deviation on PAN number and DOB characters."), ("Font Rendering Discontinuity", "critical", "Rasterized font anti-aliasing differs from genuine NSDL format.")], "Insp. Meera Kulkarni", 1),
        (4, "aadhaar_front_verification.jpg", "image", "Needs review", 54, "not_reviewed", [("Pixel Inconsistency", "warn", "Minor blending border detected around photo frame.")], "Insp. Meera Kulkarni", 3),
        (4, "loan_sanction_order_branch.pdf", "document", "Consistent", 93, "reviewed", [], "Insp. Meera Kulkarni", 5),
        (4, "applicant_kyc_video_call.mp4", "video", "Needs review", 64, "in_review", [("Frame Boundary Inconsistency", "warn", "Compression rate shift between seconds 4.2 and 6.8.")], "SI Rohan Patil", 7),
        (4, "credit_appraisal_worksheet.pdf", "document", "Consistent", 91, "reviewed", [], "Insp. Meera Kulkarni", 10),

        # Case 5: Ahmedabad Diamond Exchange
        (5, "vault_corridor_cam04.mp4", "video", "Consistent", 84, "reviewed", [("Lighting Continuity", "clean", "Illumination vectors match corridor environment.")], "SI Rohan Patil", 2),
        (5, "transit_cart_cctv_frame.jpg", "image", "Consistent", 95, "reviewed", [], "SI Rohan Patil", 4),
        (5, "security_shift_radio_log.wav", "audio", "Consistent", 88, "reviewed", [], "SI Rohan Patil", 6),
        (5, "consignment_dispatch_slip.pdf", "document", "Consistent", 97, "reviewed", [], "Insp. Meera Kulkarni", 8),
        (5, "guard_access_badge_swipe.pdf", "document", "Consistent", 90, "reviewed", [], "SI Rohan Patil", 12),

        # Case 6: Hyderabad Pharma IP Extortion
        (6, "whatsapp_voicenote_threat.wav", "audio", "Consistent", 83, "reviewed", [("Acoustic Telemetry", "clean", "Natural GSM / Opus codec compression profiles.")], "Insp. Meera Kulkarni", 1),
        (6, "formulation_patent_draft_2025.pdf", "document", "Consistent", 96, "reviewed", [], "Insp. Meera Kulkarni", 3),
        (6, "cleanroom_access_feed_hq.mp4", "video", "Consistent", 94, "reviewed", [], "SI Rohan Patil", 5),
        (6, "lab_notebook_polaroid_scan.jpg", "image", "Consistent", 87, "reviewed", [], "Insp. Meera Kulkarni", 7),
        (6, "extortion_email_headers.pdf", "document", "Consistent", 89, "reviewed", [], "Insp. Meera Kulkarni", 9),

        # Case 7: Pune Automotive CAD Leak
        (7, "battery_chassis_cad_render.png", "image", "Consistent", 92, "reviewed", [], "SI Rohan Patil", 2),
        (7, "patent_office_certified_copy.pdf", "document", "Consistent", 98, "reviewed", [("Digital Signature", "clean", "Valid RSA 2048-bit PKI signature from Controller of Patents.")], "Insp. Meera Kulkarni", 4),
        (7, "r_and_d_secure_server_cctv.mp4", "video", "Consistent", 86, "reviewed", [], "SI Rohan Patil", 6),
        (7, "board_audit_interview_cto.wav", "audio", "Consistent", 91, "reviewed", [], "Insp. Meera Kulkarni", 8),
        (7, "vendor_nda_agreement_signed.pdf", "document", "Consistent", 95, "reviewed", [], "SI Rohan Patil", 10),
    ]

    print(f"Creating {len(files_plan)} evidence files across 8 cases...")

    for case_idx, filename, media_type, verdict, score, review_status, findings, uploader, offset_hours in files_plan:
        c = created_cases[case_idx]
        case_created = datetime.fromisoformat(c.created_at)
        recv_time = case_created + timedelta(hours=offset_hours)
        
        # Unique content seed per file so SHA is unique
        seed_token = f"{c.reference}:{filename}:{case_idx}"
        dest_path, file_size, sha, stored_name = make_dummy_file(filename, media_type, seed_token)
        
        ev = Evidence(
            case_id=c.id,
            filename=filename,
            stored_name=stored_name,
            file_size=file_size,
            file_hash=sha,
            media_type=media_type,
            status="done",
            verdict=verdict,
            score=score,
            review_status=review_status,
            reviewed_by=uploader if review_status == "reviewed" else None,
            reviewed_at=recv_time.isoformat() if review_status == "reviewed" else None,
            uploader=uploader,
            created_at=recv_time.isoformat(),
            error=None,
            ai_summary=f"Automated forensic inspection completed. Evidence exhibits consistent {media_type} telemetry." if verdict == "Consistent" else f"Structural anomalies detected in {media_type} signal. Requires statutory forensic verification."
        )
        db.add(ev)
        db.flush()

        # Add Findings
        for chk_name, severity, desc in findings:
            f = Finding(
                evidence_id=ev.id,
                check_name=chk_name,
                severity=severity,
                score_impact=-15 if severity == "warn" else -35,
                description=desc,
                data_json=json.dumps({"check": chk_name, "severity": severity, "message": desc})
            )
            db.add(f)

        # Add Notes if reviewed or suspicious
        if verdict == "Likely manipulated":
            n = Note(
                evidence_id=ev.id,
                author=uploader,
                content=f"Primary physical inspection confirms digital alteration in exhibit {filename}. Preserved for Section 63 BSA compliance reporting.",
                created_at=(recv_time + timedelta(hours=1)).isoformat()
            )
            db.add(n)

        # Add Chain of Custody Event
        c_evt = CustodyEvent(
            evidence_id=ev.id,
            seq=1,
            action="Ingested",
            actor=uploader,
            at=recv_time.isoformat(),
            file_hash=sha,
            prev_hash="GENESIS",
            event_hash=custody.compute_event_hash(ev.id, 1, "Ingested", uploader, recv_time.isoformat(), sha, "GENESIS", "Intake ingestion and initial SHA-256 fingerprinting"),
            note="Intake ingestion and initial SHA-256 fingerprinting"
        )
        db.add(c_evt)
        db.flush()
        
        # Add a second custody event for examined
        c_evt2 = CustodyEvent(
            evidence_id=ev.id,
            seq=2,
            action="Examined",
            actor="Forensic Engine",
            at=(recv_time + timedelta(minutes=5)).isoformat(),
            file_hash=sha,
            prev_hash=c_evt.event_hash,
            event_hash=custody.compute_event_hash(ev.id, 2, "Examined", "Forensic Engine", (recv_time + timedelta(minutes=5)).isoformat(), sha, c_evt.event_hash, "Automated rule verification"),
            note="Automated rule verification"
        )
        db.add(c_evt2)

    db.commit()

    # Log initial custody_verify_all in ActivityLog so custody health is populated
    act = ActivityLog(
        at=now_iso(),
        actor="System",
        action="custody_verify_all",
        case_id=None,
        evidence_id=None,
        summary=f"Full integrity sweep verified {len(files_plan)} files intact."
    )
    db.add(act)
    db.commit()

    # Print summary
    total_ev = db.query(Evidence).count()
    suspicious = db.query(Evidence).filter(Evidence.score < 50).count()
    awaiting = db.query(Evidence).filter(Evidence.review_status == "not_reviewed").count()
    avg_score = sum(e.score for e in db.query(Evidence).all()) / total_ev

    print(f"\nSeed Complete!")
    print(f"Cases: {db.query(Case).count()}")
    print(f"Total Evidence Files: {total_ev}")
    print(f"Suspicious files (<50): {suspicious}")
    print(f"Awaiting review: {awaiting}")
    print(f"Average score: {avg_score:.1f}%")
    print(f"Consistent files: {db.query(Evidence).filter(Evidence.verdict == 'Consistent').count()}")
    print(f"Needs review files: {db.query(Evidence).filter(Evidence.verdict == 'Needs review').count()}")
    print(f"Likely manipulated files: {db.query(Evidence).filter(Evidence.verdict == 'Likely manipulated').count()}")

    if close_when_done:
        db.close()


if __name__ == "__main__":
    run_seed()
