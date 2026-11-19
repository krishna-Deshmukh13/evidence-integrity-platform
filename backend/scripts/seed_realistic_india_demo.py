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


def run_seed():
    db = SessionLocal()
    
    print("Clearing old evidence records...")
    db.query(ActivityLog).delete()
    db.query(Finding).delete()
    db.query(Note).delete()
    db.query(CustodyEvent).delete()
    db.query(Evidence).delete()
    db.query(Case).delete()
    db.commit()

    # Ensure demo users exist with standard password ram@1234
    users_info = [
        ("meera", "Insp. Meera Kulkarni", "admin"),
        ("rohan", "SI Rohan Patil", "investigator"),
        ("kavya", "Kavya Rao", "viewer"),
    ]
    for uname, fname, urole in users_info:
        user_rec = db.query(User).filter(User.username == uname).first()
        phash = auth.hash_password("ram@1234")
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
            "title": "Ahmedabad Industrial Park Security Frame Splicing",
            "desc": "Warehouse CCTV recording with suspected frame deletion during high-value inventory theft.",
            "investigator": "SI Rohan Patil",
            "location": "Sanand Industrial Zone, Ahmedabad",
            "lat": 22.9868, "lon": 72.3813
        },
        {
            "reference": "CR-2024-UP-633",
            "title": "Lucknow Municipal Land Registry Stamp Duplication",
            "desc": "Property title deed stamp duplicate discovered via clone-texture forensic heatmaps.",
            "investigator": "Insp. Meera Kulkarni",
            "location": "Hazratganj, Lucknow",
            "lat": 26.8467, "lon": 80.9462
        },
        {
            "reference": "CR-2024-TS-741",
            "title": "Hyderabad Telecom Voice Cloning & SIM Swap Inquiry",
            "desc": "Audio voice note extortion using cloned AI vocal synthesis across telecom gateways.",
            "investigator": "SI Rohan Patil",
            "location": "HITEC City, Hyderabad",
            "lat": 17.4435, "lon": 78.3772
        },
    ]

    cases = []
    for cm in cases_meta:
        c = Case(
            reference=cm["reference"],
            title=cm["title"],
            investigator=cm["investigator"],
            incident_location=cm["location"],
            incident_lat=cm["lat"],
            incident_lon=cm["lon"],
            created_at=(base_time + timedelta(days=len(cases) * 2)).isoformat()
        )
        db.add(c)
        cases.append(c)
    db.commit()

    # Exact 40 Files:
    # 5 Suspicious ("Likely manipulated", scores 14, 22, 28, 33, 37)
    # 4 Waiting for Review ("Needs review", scores 54, 58, 63, 67)
    # 31 Genuine ("Consistent", scores 82 to 97)
    # Review statuses: 3 "not_reviewed" (waiting for review), rest "reviewed" or "flagged" / "cleared"

    files_plan = [
        # --- Suspicious (5 files) ---
        {"c": 0, "fn": "payroll_summary_tampered.pdf", "mt": "document", "score": 28, "v": "Likely manipulated", "rs": "flagged", "note": "Altered font baseline and duplicated tax header block."},
        {"c": 1, "fn": "treasury_authorization_call_clone.wav", "mt": "audio", "score": 14, "v": "Likely manipulated", "rs": "flagged", "note": "High-frequency vocoder distortion and robotic pitch jitter detected."},
        {"c": 4, "fn": "identity_card_pan_tampered.jpg", "mt": "image", "score": 22, "v": "Likely manipulated", "rs": "flagged", "note": "ELA analysis reveals inconsistent compression artifacts on the DOB field."},
        {"c": 5, "fn": "gate_cctv_splice_cut.mp4", "mt": "video", "score": 33, "v": "Likely manipulated", "rs": "flagged", "note": "Abrupt frame timestamps and missing keyframes at 00:03:14."},
        {"c": 6, "fn": "notary_seal_stamp_cloned.png", "mt": "image", "score": 37, "v": "Likely manipulated", "rs": "flagged", "note": "Exact pixel-for-pixel match with duplicate seal in registry archive."},

        # --- Needs Review / Waiting (4 files) ---
        {"c": 0, "fn": "vendor_bank_mandate.pdf", "mt": "document", "score": 58, "v": "Needs review", "rs": "not_reviewed", "note": "Signature density differs slightly from primary account card."},
        {"c": 2, "fn": "software_license_schedule_b.pdf", "mt": "document", "score": 63, "v": "Needs review", "rs": "not_reviewed", "note": "Re-compressed PDF layer detected; requires manual comparison."},
        {"c": 3, "fn": "customs_dispatch_slip.png", "mt": "image", "score": 54, "v": "Needs review", "rs": "not_reviewed", "note": "Low resolution image scan; camera sensor signature inconclusive."},
        {"c": 7, "fn": "telecom_voicemail_dispatch.mp3", "mt": "audio", "score": 67, "v": "Needs review", "rs": "reviewed", "note": "Background noise filter applied; vocal tract features partially masked."},

        # --- Genuine (31 files) ---
        # Case 0 (Mumbai Corporate) - 3 files
        {"c": 0, "fn": "audit_ledger_q3_original.pdf", "mt": "document", "score": 94, "v": "Consistent", "rs": "cleared", "note": "Digital cryptographic signature intact; PDF structure verified."},
        {"c": 0, "fn": "corporate_tax_certificate.pdf", "mt": "document", "score": 96, "v": "Consistent", "rs": "cleared", "note": "Digital token authentic and verified with revenue registry."},
        {"c": 0, "fn": "reception_desk_cctv.mp4", "mt": "video", "score": 88, "v": "Consistent", "rs": "reviewed", "note": "Continuous timecode and smooth GOP cadences confirmed."},

        # Case 1 (Delhi Banking) - 4 files
        {"c": 1, "fn": "branch_entrance_cctv.mp4", "mt": "video", "score": 92, "v": "Consistent", "rs": "cleared", "note": "Standard H.264 stream with matching DVR timestamp markers."},
        {"c": 1, "fn": "manager_official_interview.wav", "mt": "audio", "score": 95, "v": "Consistent", "rs": "cleared", "note": "Natural human acoustic formant progression and room acoustics."},
        {"c": 1, "fn": "wire_transfer_confirmation.pdf", "mt": "document", "score": 91, "v": "Consistent", "rs": "reviewed", "note": "Authentic core banking engine output."},
        {"c": 1, "fn": "counter_teller_photo.jpg", "mt": "image", "score": 89, "v": "Consistent", "rs": "cleared", "note": "Original camera EXIF data and sensor noise profile consistent."},

        # Case 2 (Bengaluru IT) - 4 files
        {"c": 2, "fn": "it_vendor_contract_master.pdf", "mt": "document", "score": 93, "v": "Consistent", "rs": "cleared", "note": "Clean multi-page document structure with uniform typesetting."},
        {"c": 2, "fn": "server_room_access_log.pdf", "mt": "document", "score": 96, "v": "Consistent", "rs": "cleared", "note": "Automated access control system export."},
        {"c": 2, "fn": "data_center_corridor_cam.mp4", "mt": "video", "score": 87, "v": "Consistent", "rs": "reviewed", "note": "Continuous CCTV feed with valid camera hardware headers."},
        {"c": 2, "fn": "badge_scan_security_photo.png", "mt": "image", "score": 90, "v": "Consistent", "rs": "cleared", "note": "Sensor PRNU signature matches terminal camera."},

        # Case 3 (Chennai Harbor) - 4 files
        {"c": 3, "fn": "container_manifest_original.pdf", "mt": "document", "score": 95, "v": "Consistent", "rs": "cleared", "note": "Port trust EDI bitstream verified."},
        {"c": 3, "fn": "dockside_crane_camera.mp4", "mt": "video", "score": 88, "v": "Consistent", "rs": "cleared", "note": "Unaltered container loading sequence footage."},
        {"c": 3, "fn": "customs_inspector_radio_log.wav", "mt": "audio", "score": 86, "v": "Consistent", "rs": "reviewed", "note": "Authentic VHF analog spectrum with standard repeater tones."},
        {"c": 3, "fn": "cargo_seal_photo_highres.jpg", "mt": "image", "score": 94, "v": "Consistent", "rs": "cleared", "note": "Camera sensor profile and optical focal parameters authentic."},

        # Case 4 (Kolkata Identity) - 4 files
        {"c": 4, "fn": "bank_branch_kyc_terminal_log.pdf", "mt": "document", "score": 92, "v": "Consistent", "rs": "cleared", "note": "Standard e-KYC telemetry matching UIDAI timestamp."},
        {"c": 4, "fn": "officer_statement_recording.wav", "mt": "audio", "score": 95, "v": "Consistent", "rs": "cleared", "note": "Clean directional microphone audio without synthesis markers."},
        {"c": 4, "fn": "security_turnstile_cctv.mp4", "mt": "video", "score": 89, "v": "Consistent", "rs": "reviewed", "note": "Unbroken timecode from building access system."},
        {"c": 4, "fn": "submitted_utility_bill.pdf", "mt": "document", "score": 91, "v": "Consistent", "rs": "cleared", "note": "Genuine municipal electric distribution format."},

        # Case 5 (Ahmedabad Industrial) - 4 files
        {"c": 5, "fn": "perimeter_fence_thermal_cam.mp4", "mt": "video", "score": 94, "v": "Consistent", "rs": "cleared", "note": "FLIR thermal camera telemetry stream intact."},
        {"c": 5, "fn": "weighbridge_log_sheet.pdf", "mt": "document", "score": 97, "v": "Consistent", "rs": "cleared", "note": "Hardware scale printer output with verified checksum."},
        {"c": 5, "fn": "guard_radio_dispatch.wav", "mt": "audio", "score": 88, "v": "Consistent", "rs": "reviewed", "note": "Two-way radio communication with consistent transmission chirp."},
        {"c": 5, "fn": "vehicle_entry_license_plate.jpg", "mt": "image", "score": 93, "v": "Consistent", "rs": "cleared", "note": "ANPR capture with infrared strobe metadata verified."},

        # Case 6 (Lucknow Land Registry) - 4 files
        {"c": 6, "fn": "original_sale_deed_page1.pdf", "mt": "document", "score": 96, "v": "Consistent", "rs": "cleared", "note": "Official treasury stamp paper texture and watermarks authentic."},
        {"c": 6, "fn": "sub_registrar_office_cam.mp4", "mt": "video", "score": 90, "v": "Consistent", "rs": "cleared", "note": "Official courtroom recording with synchronized audio track."},
        {"c": 6, "fn": "registrar_witness_testimony.wav", "mt": "audio", "score": 92, "v": "Consistent", "rs": "reviewed", "note": "Live deposition audio recorded in magistrate chambers."},
        {"c": 6, "fn": "boundary_survey_map.png", "mt": "image", "score": 94, "v": "Consistent", "rs": "cleared", "note": "Surveyor digital CAD export with verified coordinate tags."},

        # Case 7 (Hyderabad Telecom) - 4 files
        {"c": 7, "fn": "telecom_cdr_metadata_export.pdf", "mt": "document", "score": 97, "v": "Consistent", "rs": "cleared", "note": "Cell tower telemetry and signaling switch records."},
        {"c": 7, "fn": "customer_support_verification_call.wav", "mt": "audio", "score": 94, "v": "Consistent", "rs": "cleared", "note": "Original PBX call recording with intact stereo channel separation."},
        {"c": 7, "fn": "tower_maintenance_cctv.mp4", "mt": "video", "score": 89, "v": "Consistent", "rs": "cleared", "note": "Base station security camera with valid H.264 GOP."},
        {"c": 7, "fn": "sim_packaging_barcode_scan.jpg", "mt": "image", "score": 91, "v": "Consistent", "rs": "reviewed", "note": "Macro lens photograph with authentic EXIF and sensor Bayer pattern."}
    ]

    print(f"Creating {len(files_plan)} evidence files across 8 cases...")
    for idx, fp in enumerate(files_plan):
        c_obj = cases[fp["c"]]
        final_path, size_bytes, sha, stored_name = make_dummy_file(
            fp["fn"], fp["mt"], f"evidence_seed_data_{c_obj.reference}_{idx}"
        )
        
        recv_time = base_time + timedelta(days=fp["c"] * 2, hours=idx % 12, minutes=idx * 7)
        recv_iso = recv_time.isoformat()

        ev = Evidence(
            case_id=c_obj.id,
            filename=fp["fn"],
            stored_name=stored_name,
            media_type=fp["mt"],
            size=size_bytes,
            sha256=sha,
            status="done",
            stage="Done",
            progress=100,
            score=fp["score"],
            verdict=fp["v"],
            review_status=fp["rs"],
            received_at=recv_iso,
            uploaded_by=c_obj.investigator,
            details=json.dumps({"verified_format": True, "channels": 2 if fp["mt"] == "audio" else 1}),
            report=f"## Forensic Analysis: {fp['fn']}\n\n**Verdict:** {fp['v']} ({fp['score']}% Trust Score)\n\n**Findings:** {fp['note']}",
            report_model="rule_engine"
        )
        db.add(ev)
        db.flush()

        # Add Finding
        sev = "high" if fp["score"] < 40 else "medium" if fp["score"] < 70 else "info"
        pen = 26 if sev == "high" else 14 if sev == "medium" else 0
        cat = "pixel" if fp["mt"] == "image" else "container" if fp["mt"] == "video" else "audio" if fp["mt"] == "audio" else "document"
        
        f = Finding(
            evidence_id=ev.id,
            category=cat,
            check=f"{cat}_analysis",
            severity=sev,
            title=f"Forensic signal: {fp['v']}",
            detail=fp["note"],
            penalty=pen
        )
        db.add(f)

        # Add initial Custody Event
        c_evt = CustodyEvent(
            evidence_id=ev.id,
            seq=1,
            action="Acquired",
            actor=c_obj.investigator,
            at=recv_iso,
            file_hash=sha,
            prev_hash="0" * 64,
            event_hash=custody.compute_event_hash(ev.id, 1, "Acquired", c_obj.investigator, recv_iso, sha, "0" * 64, "Intake into custody"),
            note="Intake into custody"
        )
        db.add(c_evt)
        
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

    db.close()


if __name__ == "__main__":
    run_seed()
