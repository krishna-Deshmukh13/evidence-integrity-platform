"""Seed real-world incident crime cases and authentic multi-media evidence files."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("EI_STORAGE_DIR", str(backend_dir / "storage"))

import cv2
import numpy as np
import pymupdf as fitz
from app import activity, auth, config, custody
from app.database import Base, SessionLocal, engine, init_db
from app.models import ActivityLog, Case, CustodyEvent, Evidence, Finding, Note, User

FFMPEG = r"C:\Users\krish\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
root_dir = backend_dir.parent
real_media_dir = root_dir / "real_incident_evidence_files"


def seed_real_incident_database():
    print("Re-initializing SQLite schema for real incident dataset...")
    Base.metadata.drop_all(engine)
    init_db()
    db = SessionLocal()

    # Clear uploads and artifacts
    shutil.rmtree(config.UPLOAD_DIR, ignore_errors=True)
    shutil.rmtree(config.ARTIFACT_DIR, ignore_errors=True)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Accounts
    pw_hash = auth.hash_password("ram@1234")
    meera = User(username="meera", full_name="Insp. Meera Kulkarni", role="admin",
                 password_hash=pw_hash, is_active=True, last_login_at="2026-10-21T15:30:00Z")
    rohan = User(username="rohan", full_name="SI Rohan Patil", role="investigator",
                 password_hash=pw_hash, is_active=True, last_login_at="2026-10-21T15:15:00Z")
    kavya = User(username="kavya", full_name="Kavya Rao", role="viewer",
                 password_hash=pw_hash, is_active=True)
    db.add_all([meera, rohan, kavya])
    db.commit()

    # 2. Four Real-World Cases
    c1 = Case(reference="CR-2022-1008", title="Crimean Bridge Explosion & Infrastructure Sabotage", investigator="Insp. Meera Kulkarni")
    c2 = Case(reference="CR-2013-0706", title="Asiana Flight 214 Emergency Runway Incident", investigator="SI Rohan Patil")
    c3 = Case(reference="CR-2024-0518", title="Metropolitan Surveillance & Counter-Terrorism ERT Operation", investigator="Insp. Meera Kulkarni")
    c4 = Case(reference="CR-2024-0820", title="Commercial Facility Break-In & Deepfake Extortion", investigator="SI Rohan Patil")
    db.add_all([c1, c2, c3, c4])
    db.commit()

    d_base = "2026-10-18T14:30:00.000000Z"

    def put_file(stored_name, src_name):
        src_path = real_media_dir / src_name
        dest_path = config.UPLOAD_DIR / stored_name
        shutil.copy(src_path, dest_path)
        data = dest_path.read_bytes()
        return len(data), hashlib.sha256(data).hexdigest()

    # -------------------------------------------------------------------------
    # CASE 1: Crimean Bridge Explosion & Infrastructure Sabotage
    # -------------------------------------------------------------------------
    # Ev 1: Authentic Incident CCTV
    sz, sha = put_file("e_crimean_bridge_cctv.mp4", "real_incident_cctv_crimean_bridge_2022.mp4")
    e1 = Evidence(
        case_id=c1.id, filename="cctv_crimean_bridge_explosion_2022.mp4", stored_name="e_crimean_bridge_cctv.mp4",
        media_type="video", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=88,
        verdict="Consistent", review_status="not_reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"metadata": 12}),
        details=json.dumps({"duration": 18.0, "fps": 25.0, "width": 1280, "height": 720, "cuts": [], "frozen": []}),
        report="## Summary\nReal security camera footage capturing the Crimean Bridge explosion.\n\n## Key findings\n- Continuous frame flow without inter-frame cuts or frozen stretches.\n- Timecode overlay aligns with CCTV camera sensor clock.\n\n## Consistent with an original\n- Authentic surveillance camera stream headers verified.\n\n## Recommended next steps\n- Preserve unaltered master stream copy.",
        report_model="template", tags=json.dumps(["cctv", "incident", "explosion"])
    )
    db.add(e1)
    db.flush()

    # Ev 2: Tampered CCTV Splice
    sz, sha = put_file("e_bridge_tampered.mp4", "real_incident_cctv_tampered_splice.mp4")
    e2 = Evidence(
        case_id=c1.id, filename="cctv_bridge_tampered_splice.mp4", stored_name="e_bridge_tampered.mp4",
        media_type="video", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=48,
        verdict="Likely manipulated", review_status="not_reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"container": 26, "metadata": 26}),
        details=json.dumps({"duration": 12.0, "fps": 25.0, "width": 1280, "height": 720, "cuts": [9.7], "frozen": [[7.2, 9.7]]}),
        report="## Summary\nCCTV footage shows evidence of deliberate video tampering and container re-encoding.\n\n## Key findings\n- Hard splice cut detected at timestamp 0:09.7.\n- Frozen frame duration detected between 0:07.2 and 0:09.7.\n- Video editor identified in metadata: CapCut.\n\n## Recommended next steps\n- Subpoena original NVR recording device.",
        report_model="template", tags=json.dumps(["tampered", "cctv", "splice"])
    )
    db.add(e2)
    db.flush()
    db.add_all([
        Finding(evidence_id=e2.id, category="container", check="hard_cuts", severity="high", penalty=26,
                title="Hard cut detected (at 0:09.7)", detail="Euclidean frame difference spike (z-score 15.4) indicates spliced content.",
                location=json.dumps({"kind": "time", "seconds": 9.7})),
        Finding(evidence_id=e2.id, category="metadata", check="video_editor", severity="high", penalty=26,
                title="Video editing software named in metadata (CapCut)", detail="Container metadata specifies CapCut editor export.",
                location=json.dumps({"kind": "field", "name": "comment"}))
    ])

    # Ev 3: Real Federal Affidavit PDF
    sz, sha = put_file("e_fbi_affidavit.pdf", "fbi_affidavit_ehsanul_sadequee_court_filing.pdf")
    e3 = Evidence(
        case_id=c1.id, filename="fbi_affidavit_ehsanul_sadequee_court_filing.pdf", stored_name="e_fbi_affidavit.pdf",
        media_type="document", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=96,
        verdict="Consistent", review_status="reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"metadata": 4}),
        details=json.dumps({"pages": 14, "revisions": 1}),
        report="## Summary\nAuthentic federal court criminal affidavit filed in US District Court.\n\n## Key findings\n- Font typography is consistent throughout legal pleading.\n- Court clerk docket stamp and filing signatures intact.",
        report_model="template", tags=json.dumps(["fbi", "court", "affidavit"])
    )
    db.add(e3)
    db.flush()

    # Ev 4: Benchmark Alley Clone Tampered Photo
    sz, sha = put_file("e_alley_cloned.jpg", "photo_tampered_alley_cloned.jpg")
    e4 = Evidence(
        case_id=c1.id, filename="photo_tampered_alley_cloned.jpg", stored_name="e_alley_cloned.jpg",
        media_type="image", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=42,
        verdict="Likely manipulated", review_status="not_reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"metadata": 28, "pixel": 30}),
        details=json.dumps({"width": 1600, "height": 1067, "clone_matches": 196, "ai_score": 0.012}),
        report="## Summary\nManipulated photograph exhibiting clone stamp duplication and editing software EXIF signatures.\n\n## Key findings\n- 196 matching keypoints copied from brick wall onto graffiti.\n- Edited using Adobe Photoshop 25.4 (Windows).\n- Modified 2.7 days after original capture.",
        report_model="template", tags=json.dumps(["clone", "tampered", "photoshop"])
    )
    db.add(e4)
    db.flush()
    db.add_all([
        Finding(evidence_id=e4.id, category="pixel", check="copy_move", severity="high", penalty=30,
                title="Cloned region detected", detail="196 matching features found copied across the brick wall.",
                location=json.dumps({"kind": "region", "from": [57, 536], "to": [487, 656]})),
        Finding(evidence_id=e4.id, category="metadata", check="software", severity="medium", penalty=14,
                title="Saved by image editing software (Adobe Photoshop 25.4 (Windows))",
                detail="EXIF Software tag specifies Adobe Photoshop.", location=json.dumps({"kind": "field", "name": "EXIF: Software"})),
        Finding(evidence_id=e4.id, category="metadata", check="modified_after_capture", severity="medium", penalty=14,
                title="Modified after capture (2.7 days later)", detail="EXIF DateTime is 2.7 days later than original capture.",
                location=json.dumps({"kind": "field", "name": "EXIF: DateTime"}))
    ])

    # -------------------------------------------------------------------------
    # CASE 2: Asiana Flight 214 Emergency Runway Incident
    # -------------------------------------------------------------------------
    # Ev 5: Authentic FAA Emergency ATC Radio
    sz, sha = put_file("e_asiana_atc.wav", "real_emergency_asiana214_atc_radio.wav")
    e5 = Evidence(
        case_id=c2.id, filename="asiana214_tower_atc_emergency.wav", stored_name="e_asiana_atc.wav",
        media_type="audio", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=94,
        verdict="Consistent", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"audio": 6}),
        details=json.dumps({"duration": 30.0, "sample_rate": 44100, "cutoff_hz": 16000, "silences": []}),
        report="## Summary\nAuthentic Federal Aviation Administration (FAA) KSFO Tower air traffic control transmission.\n\n## Key findings\n- Natural analog radio frequency envelope with consistent VHF acoustic noise.\n- Continuous voice cadence without splicing or synthetic artefacts.",
        report_model="template", tags=json.dumps(["faa", "atc", "emergency"])
    )
    db.add(e5)
    db.flush()

    # Ev 6: AI-Generated Synthetic Voice (Deepfake Audio)
    sz, sha = put_file("e_synth_voice.wav", "voice_synthetic_tts_elevenlabs.wav")
    e6 = Evidence(
        case_id=c2.id, filename="voice_synthetic_tts_elevenlabs.wav", stored_name="e_synth_voice.wav",
        media_type="audio", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=45,
        verdict="Likely manipulated", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"voice": 55}),
        details=json.dumps({"duration": 9.4, "cutoff_hz": 7000, "silences": [[1.2, 1.6], [3.5, 3.9]], "tts_timeline": [{"time": 0.0, "score": 1.0}]}),
        report="## Summary\nSynthesized speech audio exhibiting neural text-to-speech characteristics.\n\n## Key findings\n- wav2vec2 deepfake classifier identified synthetic voice with 100% probability.\n- Exact zero-amplitude digital silence intervals detected at 1.2s and 3.5s.\n- Bandwidth truncated at 7.0 kHz characteristic of speech synthesis engines.",
        report_model="template", tags=json.dumps(["tts", "deepfake", "synthetic"])
    )
    db.add(e6)
    db.flush()
    db.add_all([
        Finding(evidence_id=e6.id, category="voice", check="synthetic_voice", severity="high", penalty=52,
                title="Synthetic voice detected (100% probability)", detail="The wav2vec2 deepfake audio model identified speech synthesis artefacts.",
                location=json.dumps({"kind": "time_range", "start": 0.0, "end": 9.4})),
        Finding(evidence_id=e6.id, category="audio", check="digital_silence", severity="medium", penalty=14,
                title="Unnatural digital silence (2 stretches)", detail="Stretches of exact zero amplitude samples detected.",
                location=json.dumps({"kind": "time_ranges", "ranges": [[1.2, 1.6], [3.5, 3.9]]}))
    ])

    # Ev 7: Real US Federal Court Indictment PDF
    sz, sha = put_file("e_court_indictment.pdf", "us_district_court_federal_indictment.pdf")
    e7 = Evidence(
        case_id=c2.id, filename="us_district_court_federal_indictment.pdf", stored_name="e_court_indictment.pdf",
        media_type="document", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=98,
        verdict="Consistent", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 2}),
        details=json.dumps({"pages": 28, "revisions": 1}),
        report="## Summary\nAuthentic federal grand jury criminal indictment filed in US District Court.\n\n## Key findings\n- Single creator producer structure, consistent legal typography.\n- Document seals and docket filings verified.",
        report_model="template", tags=json.dumps(["court", "indictment", "pacer"])
    )
    db.add(e7)
    db.flush()

    # Ev 8: Tampered Invoice PDF
    sz, sha = put_file("e_invoice_font_tampered.pdf", "invoice_tampered_font_altered.pdf")
    e8 = Evidence(
        case_id=c2.id, filename="invoice_tampered_font_altered.pdf", stored_name="e_invoice_font_tampered.pdf",
        media_type="document", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=27,
        verdict="Likely manipulated", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 28, "document": 45}),
        details=json.dumps({"pages": 1, "revisions": 2}),
        report="## Summary\nCommercial invoice shows structural evidence of font substitution and white-out tampering.\n\n## Key findings\n- Font inconsistency: numerical amounts substituted with Times font over Helvetica body.\n- Concealing white-out rectangle placed over original amounts.\n- PDF document saved 2 incremental times.",
        report_model="template", tags=json.dumps(["invoice", "fraud", "font_tampering"])
    )
    db.add(e8)
    db.flush()
    db.add_all([
        Finding(evidence_id=e8.id, category="document", check="font_forensics", severity="high", penalty=26,
                title="Font inconsistency: edited amounts in different font", detail="Amounts use Times-Roman on a line set in Helvetica.",
                location=json.dumps({"kind": "page_boxes", "page": 1, "boxes": [[445, 290, 520, 315]]})),
        Finding(evidence_id=e8.id, category="document", check="hidden_text", severity="medium", penalty=14,
                title="Hidden text: white-out rectangle over amount", detail="White rectangle drawn directly over prior text.",
                location=json.dumps({"kind": "page_boxes", "page": 1, "boxes": [[445, 290, 520, 315]]})),
        Finding(evidence_id=e8.id, category="document", check="incremental_updates", severity="high", penalty=26,
                title="PDF was saved 2 times (incremental updates)", detail="Multiple %%EOF trailers found in file.",
                location=json.dumps({"kind": "field", "name": "PDF structure"}))
    ])

    # -------------------------------------------------------------------------
    # CASE 3: Metropolitan Surveillance & Counter-Terrorism ERT Operation
    # -------------------------------------------------------------------------
    # Ev 9: Real FBI Evidence Response Team Crime Scene Photo
    sz, sha = put_file("e_fbi_ert_photo.jpg", "fbi_evidence_response_team_photo.jpg")
    e9 = Evidence(
        case_id=c3.id, filename="fbi_evidence_response_team_photo.jpg", stored_name="e_fbi_ert_photo.jpg",
        media_type="image", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=100,
        verdict="Consistent", review_status="reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({}),
        details=json.dumps({"width": 3840, "height": 2560, "clone_matches": 0, "ai_score": 0.001}),
        report="## Summary\nAuthentic professional crime scene documentation photograph taken by the FBI Evidence Response Team (ERT).\n\n## Key findings\n- Complete professional DSLR camera sensor noise signature.\n- Original EXIF tags intact without editing software re-encoding.",
        report_model="template", tags=json.dumps(["fbi", "crime_scene", "dslr"])
    )
    db.add(e9)
    db.flush()

    # Ev 10: Real DC Police Surveillance Camera Photo
    sz, sha = put_file("e_dc_police_camera.jpg", "dc_police_surveillance_camera.jpg")
    e10 = Evidence(
        case_id=c3.id, filename="dc_police_surveillance_camera.jpg", stored_name="e_dc_police_camera.jpg",
        media_type="image", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=94,
        verdict="Consistent", review_status="not_reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"metadata": 6}),
        details=json.dumps({"width": 1280, "height": 960, "clone_matches": 0, "ai_score": 0.005}),
        report="## Summary\nAuthentic Metropolitan Police Department outdoor surveillance camera capture at Constitution Ave NW, Washington DC.\n\n## Key findings\n- Fixed focal length optics and authentic outdoor CMOS sensor profile verified.\n- No cloning or synthetic artefacts.",
        report_model="template", tags=json.dumps(["police", "surveillance", "cctv"])
    )
    db.add(e10)
    db.flush()

    # Ev 11: Real StyleGAN2 Photorealistic AI Deepfake Face (AI Record 1)
    sz, sha = put_file("e_stylegan_deepfake.jpg", "stylegan_ai_deepfake_face.jpg")
    e11 = Evidence(
        case_id=c3.id, filename="stylegan_ai_deepfake_face.jpg", stored_name="e_stylegan_deepfake.jpg",
        media_type="image", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=38,
        verdict="Likely manipulated", review_status="flagged", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"ai": 55, "metadata": 7}),
        details=json.dumps({"width": 1024, "height": 1024, "ai_score": 0.994, "clone_matches": 0}),
        report="## Summary\nPhotorealistic human face generated entirely via neural network synthesis (StyleGAN2 / This Person Does Not Exist).\n\n## Key findings\n- SwinV2 vision classifier detected synthetic generation with 99.4% confidence.\n- ViT deepfake detector flagged facial boundary and corneal reflection synthesis anomalies.\n- Absence of physical camera sensor PRNU noise.",
        report_model="template", tags=json.dumps(["deepfake", "ai_face", "stylegan"])
    )
    db.add(e11)
    db.flush()
    db.add(Finding(evidence_id=e11.id, category="ai", check="ai_image", severity="high", penalty=52,
                   title="AI-generated synthetic face detected (99.4%)",
                   detail="The SwinV2 / ViT deepfake model identified characteristic generative synthesis patterns in facial geometry.",
                   location=json.dumps({"kind": "model", "name": "Deep-Fake-Detector-v2-Model"})))

    # Ev 12: Tracked Changes Witness Statement DOCX
    sz, sha = put_file("e_statement_tracked.docx", "statement_tampered_tracked_revisions.docx")
    e12 = Evidence(
        case_id=c3.id, filename="statement_tampered_tracked_revisions.docx", stored_name="e_statement_tracked.docx",
        media_type="document", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=74,
        verdict="Needs review", review_status="not_reviewed", received_at=d_base, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"document": 26}),
        details=json.dumps({"tracked_changes": 1}),
        report="## Summary\nWord deposition document contains tracked revisions altering critical witness testimony.\n\n## Key findings\n- Tracked deletion and insertion: altered 'did not see the vehicle' to 'clearly saw the vehicle'.\n\n## Recommended next steps\n- Compare against audio transcript.",
        report_model="template", tags=json.dumps(["docx", "tracked_changes", "testimony"])
    )
    db.add(e12)
    db.flush()
    db.add(Finding(evidence_id=e12.id, category="document", check="tracked_changes", severity="high", penalty=26,
                   title="Tracked change detected (\"did not see\" -> \"clearly saw\")",
                   detail="Word XML revision tags show critical substantive edit.",
                   location=json.dumps({"kind": "field", "name": "revisions"})))

    # -------------------------------------------------------------------------
    # CASE 4: Commercial Facility Break-In & Deepfake Extortion
    # -------------------------------------------------------------------------
    # Ev 13: Real Dahua 4K Night Vision CCTV
    sz, sha = put_file("e_night_cctv.mp4", "real_incident_cctv_night_security_cam.mp4")
    e13 = Evidence(
        case_id=c4.id, filename="cctv_night_dahua_surveillance.mp4", stored_name="e_night_cctv.mp4",
        media_type="video", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=90,
        verdict="Consistent", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 10}),
        details=json.dumps({"duration": 25.0, "fps": 25.0, "width": 1920, "height": 1080, "cuts": [], "frozen": []}),
        report="## Summary\nReal commercial 4K Dahua night-vision security camera footage.\n\n## Key findings\n- Continuous frame progression without splices or missing timecodes.\n- Authentic hardware infrared sensor noise pattern.",
        report_model="template", tags=json.dumps(["night_vision", "cctv", "dahua"])
    )
    db.add(e13)
    db.flush()

    # Ev 14: Real Guam NTSB Emergency ATC Radio Recording
    sz, sha = put_file("e_guam_atc.wav", "real_emergency_korean_air_801_atc.wav")
    e14 = Evidence(
        case_id=c4.id, filename="korean_air_801_guam_atc_audio.wav", stored_name="e_guam_atc.wav",
        media_type="audio", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=92,
        verdict="Consistent", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"audio": 8}),
        details=json.dumps({"duration": 30.0, "sample_rate": 44100, "cutoff_hz": 16000, "silences": []}),
        report="## Summary\nAuthentic National Transportation Safety Board (NTSB) radio transmission recording.\n\n## Key findings\n- Acoustic room response and VHF spectrum verified.\n- No evidence of voice synthesis or splice editing.",
        report_model="template", tags=json.dumps(["ntsb", "atc", "radio"])
    )
    db.add(e14)
    db.flush()

    # Ev 15: Second Real AI Deepfake Face (AI Record 2)
    sz, sha = put_file("e_ai_suspect_face.jpg", "ai_generated_suspect_face.jpg")
    e15 = Evidence(
        case_id=c4.id, filename="ai_generated_suspect_face.jpg", stored_name="e_ai_suspect_face.jpg",
        media_type="image", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=40,
        verdict="Likely manipulated", review_status="flagged", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"ai": 55, "metadata": 5}),
        details=json.dumps({"width": 1024, "height": 1024, "ai_score": 0.988, "clone_matches": 0}),
        report="## Summary\nSynthetic suspect portrait generated via generative adversarial network.\n\n## Key findings\n- SwinV2 classifier flagged synthetic generation (98.8% probability).\n- Asymmetric ear rendering and synthetic hair frequency transitions detected.\n- Lacks camera sensor hardware signature.",
        report_model="template", tags=json.dumps(["deepfake", "ai_face", "extortion"])
    )
    db.add(e15)
    db.flush()
    db.add(Finding(evidence_id=e15.id, category="ai", check="ai_image", severity="high", penalty=52,
                   title="AI-generated synthetic face detected (98.8%)",
                   detail="Generative adversarial synthesis signatures detected in facial frequency spectrum.",
                   location=json.dumps({"kind": "model", "name": "ai-image-detector-deploy"})))

    # Ev 16: Manipulated Wire Transfer Receipt PDF
    sz, sha = put_file("e_wire_receipt_tampered.pdf", "invoice_tampered_font_altered.pdf")
    e16 = Evidence(
        case_id=c4.id, filename="wire_transfer_tampered_receipt.pdf", stored_name="e_wire_receipt_tampered.pdf",
        media_type="document", size=sz, sha256=sha, status="done", stage="Done", progress=100, score=35,
        verdict="Likely manipulated", review_status="not_reviewed", received_at=d_base, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"document": 45, "metadata": 20}),
        details=json.dumps({"pages": 1, "revisions": 3}),
        report="## Summary\nBank wire transfer document exhibits invalid digital signature coverage and altered beneficiary account details.\n\n## Key findings\n- Digital signature byte range invalidated by appended bytes.\n- Account number fields modified post-signing.",
        report_model="template", tags=json.dumps(["wire_transfer", "fraud", "extortion"])
    )
    db.add(e16)
    db.commit()

    # 3. Generate Forensics Artifacts for Every Evidence Item
    print("Generating visual forensic layers and artifacts...")
    all_evs = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13, e14, e15, e16]

    for ev in all_evs:
        art_dir = config.ARTIFACT_DIR / str(ev.id)
        art_dir.mkdir(parents=True, exist_ok=True)
        file_path = config.UPLOAD_DIR / ev.stored_name

        if ev.media_type == "image":
            # Read image and generate ELA, Noise, Heatmap
            img = cv2.imread(str(file_path))
            if img is not None:
                # original.jpg
                cv2.imwrite(str(art_dir / "original.jpg"), img)
                # ELA
                tmp_jpg = art_dir / "_ela.jpg"
                cv2.imwrite(str(tmp_jpg), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                recomp = cv2.imread(str(tmp_jpg))
                tmp_jpg.unlink(missing_ok=True)
                diff = cv2.absdiff(img, recomp)
                ela = cv2.applyColorMap(cv2.convertScaleAbs(diff, alpha=15.0), cv2.COLORMAP_INFERNO)
                cv2.imwrite(str(art_dir / "ela.png"), ela)
                # Noise
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                lap = cv2.Laplacian(gray, cv2.CV_64F)
                lap_norm = cv2.normalize(np.abs(lap), None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                cv2.imwrite(str(art_dir / "noise.png"), cv2.applyColorMap(lap_norm, cv2.COLORMAP_VIRIDIS))
                # AI Heatmap
                heat = cv2.applyColorMap(cv2.resize(lap_norm, (200, 133)), cv2.COLORMAP_JET)
                heat_full = cv2.resize(heat, (img.shape[1], img.shape[0]))
                cv2.imwrite(str(art_dir / "ai_heatmap.png"), cv2.addWeighted(img, 0.6, heat_full, 0.4, 0))
                # Clone map for cloned image
                if "cloned" in ev.filename:
                    cv2.imwrite(str(art_dir / "clone.png"), img)

        elif ev.media_type == "video":
            # Extract 20 thumbnail frames using ffmpeg or opencv
            cap = cv2.VideoCapture(str(file_path))
            total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 100)
            step = max(1, total_f // 20)
            for fi in range(20):
                cap.set(cv2.CAP_PROP_POS_FRAMES, fi * step)
                ret, frame = cap.read()
                if ret and frame is not None:
                    thumb = cv2.resize(frame, (160, 120))
                    cv2.imwrite(str(art_dir / f"frame_{fi:02d}.jpg"), thumb)
            cap.release()
            # Generate video audio spectrogram
            spec = np.zeros((240, 1200, 3), dtype=np.uint8)
            spec[:] = (20, 15, 30)
            cv2.putText(spec, f"Audio Track Analysis: {ev.filename}", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
            cv2.imwrite(str(art_dir / "audio_spectrogram.png"), spec)

        elif ev.media_type == "audio":
            # Generate audio spectrogram artifact
            spec = np.zeros((240, 1200, 3), dtype=np.uint8)
            spec[:] = (15, 10, 25)
            # Create synthetic spectrogram frequency bands
            for col in range(1200):
                val = int(120 + 80 * np.sin(col / 30) + np.random.randint(-20, 20))
                cv2.line(spec, (col, 240), (col, max(30, 240 - val)), (30, val, 220), 1)
            cv2.putText(spec, f"Spectrogram: {ev.filename}", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.imwrite(str(art_dir / "spectrogram.png"), spec)

        elif ev.media_type == "document" and ev.filename.endswith(".pdf"):
            # Render page 1 of PDF
            try:
                doc = fitz.open(str(file_path))
                if len(doc) > 0:
                    page = doc[0]
                    pix = page.get_pixmap(dpi=150)
                    pix.save(str(art_dir / "page-1.png"))
                doc.close()
            except Exception as e:
                print(f"Failed to render PDF page for {ev.filename}: {e}")

    # 4. Add Custody Events
    for ev in all_evs:
        ev_id = ev.id
        f_hash = ev.sha256
        events = [
            ("Received", ev.uploaded_by, f"Intake {ev.filename}, {ev.size:,} bytes", d_base),
            ("Analysis started", "Analysis engine", "Cryptographic hash verified", d_base),
            ("Analysis completed", "Analysis engine", f"Score {ev.score}/100, Verdict: {ev.verdict}", d_base),
            ("Integrity verified", "Insp. Meera Kulkarni (meera)", "Physical file and hash chain intact", "2026-10-21T15:35:00Z")
        ]
        prev = "0" * 64
        for seq, (action, actor, note, at_time) in enumerate(events, 1):
            eh = custody.compute_event_hash(ev_id, seq, action, actor, at_time, f_hash, prev, note)
            db.add(CustodyEvent(evidence_id=ev_id, seq=seq, action=action, actor=actor,
                                at=at_time, file_hash=f_hash, prev_hash=prev, event_hash=eh, note=note))
            prev = eh
    db.commit()

    # 5. Add Notes
    db.add(Note(evidence_id=e2.id, author="Insp. Meera Kulkarni",
                body="CCTV bridge footage has a 2.5s missing section where blast impact initiates. CapCut metadata confirmed.",
                created_at="2026-10-19T10:00:00Z"))
    db.add(Note(evidence_id=e6.id, author="SI Rohan Patil",
                body="Suspect dispatch voice matches synthetic ElevenLabs voice clone engine.",
                created_at="2026-10-19T11:30:00Z"))
    db.add(Note(evidence_id=e11.id, author="Insp. Meera Kulkarni",
                body="StyleGAN2 synthetic portrait generated at 1024x1024 resolution. Identified via SwinV2 transformer.",
                created_at="2026-10-20T09:15:00Z"))
    db.commit()

    # 6. Activity Log
    acts = [
        ("Insp. Meera Kulkarni (meera)", "view", f"Viewed evidence {e1.filename}", c1.id, e1.id, "2026-10-21T15:30:00Z"),
        ("Insp. Meera Kulkarni (meera)", "verify", f"Verified integrity {e1.filename}: Chain and file intact", c1.id, e1.id, "2026-10-21T15:31:00Z"),
        ("Insp. Meera Kulkarni (meera)", "view", f"Viewed evidence {e11.filename}", c3.id, e11.id, "2026-10-21T15:32:00Z"),
        ("SI Rohan Patil (rohan)", "view", f"Viewed evidence {e5.filename}", c2.id, e5.id, "2026-10-21T15:33:00Z"),
        ("SI Rohan Patil (rohan)", "compare", f"Compared evidence {e1.filename} vs {e2.filename}", c1.id, e2.id, "2026-10-21T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "login", "Signed in", None, None, "2026-10-21T15:35:00Z")
    ]
    for actor, action, summary, cid, eid, at_time in acts:
        db.add(ActivityLog(actor=actor, action=action, summary=summary, case_id=cid,
                           evidence_id=eid, ip="127.0.0.1", at=at_time))
    db.commit()
    db.close()
    print("Database successfully seeded with 4 real-world crime incident cases and authentic media!")


if __name__ == "__main__":
    seed_real_incident_database()
