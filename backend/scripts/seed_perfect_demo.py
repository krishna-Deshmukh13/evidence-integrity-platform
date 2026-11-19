"""Seed the exact demo dataset and state as documented in the technical guide and screenshots, with rich multi-media samples."""
import json
import os
import shutil
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("EI_STORAGE_DIR", str(backend_dir / "storage"))

import cv2
import numpy as np
from PIL import Image
from app import activity, auth, config, custody
from app.database import Base, SessionLocal, engine, init_db
from app.models import ActivityLog, Case, CustodyEvent, Evidence, Finding, Note, User


def create_demo_database():
    print("Re-initializing SQLite schema...")
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
                 password_hash=pw_hash, is_active=True, last_login_at="2026-10-17T15:37:00Z")
    rohan = User(username="rohan", full_name="SI Rohan Patil", role="investigator",
                 password_hash=pw_hash, is_active=True, last_login_at="2026-10-17T15:26:00Z")
    kavya = User(username="kavya", full_name="Kavya Rao", role="viewer",
                 password_hash=pw_hash, is_active=True)
    db.add_all([meera, rohan, kavya])
    db.commit()

    # 2. Cases
    c1 = Case(reference="CR-2026-0422", title="Alley CCTV and witness photos", investigator="SI Rohan Patil")
    c2 = Case(reference="CR-2026-0418", title="Northgate Trading invoice dispute", investigator="SI Rohan Patil")
    c3 = Case(reference="CR-2026-0402", title="Document and Media Forensics", investigator="Insp. Meera Kulkarni")
    db.add_all([c1, c2, c3])
    db.commit()

    d_oct13 = "2026-10-13T20:47:00.000000Z"

    def make_file(name, size):
        p = config.UPLOAD_DIR / name
        p.write_bytes(b"0" * size)
        return p

    # -------------------------------------------------------------
    # CASE 1: Alley CCTV and witness photos
    # -------------------------------------------------------------

    # File 1: ai_generated_pig.jpg (42, Likely manipulated)
    make_file("e_ai_pig.jpg", 81612)
    e_pig = Evidence(
        case_id=c1.id, filename="ai_generated_pig.jpg", stored_name="e_ai_pig.jpg", media_type="image",
        size=81612, sha256="71f4560ea512a8843c08b291d9c7457ef6781293a54b34c6790a1b2c3d4e5f6a",
        status="done", stage="Done", progress=100, score=42, verdict="Likely manipulated",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"ai": 55}), details=json.dumps({"width": 800, "height": 600, "ai_score": 0.98}),
        report="## Summary\nSynthetically generated image detected.\n\n## Key findings\n- SwinV2 AI image classifier detected high probability of machine generation (98%).\n\n## Consistent with an original\n- None.\n\n## Recommended next steps\n- Verify image source.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps([])
    )
    db.add(e_pig)
    db.flush()
    db.add(Finding(evidence_id=e_pig.id, category="ai", check="ai_image", severity="high", penalty=52,
                   title="AI-generated image detected (98%)",
                   detail="The SwinV2 vision transformer classified this image as machine-generated.",
                   location=json.dumps({"kind": "model", "name": "haywoodsloan/ai-image-detector-deploy"})))

    # File 2: photo_tampered.jpg (42, Likely manipulated)
    make_file("e_photo_tampered.jpg", 422197)
    e_tampered = Evidence(
        case_id=c1.id, filename="photo_tampered.jpg", stored_name="e_photo_tampered.jpg", media_type="image",
        size=422197, sha256="2acd1221ed450d18f50f28e2195fbc99fa41c0953a992fae53612d4a06ca1c",
        status="done", stage="Done", progress=100, score=42, verdict="Likely manipulated",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 28, "pixel": 30}),
        details=json.dumps({"width": 1600, "height": 1067, "clone_matches": 196, "ai_score": 0.012}),
        report="## Summary\nThe file \"photo_tampered.jpg\" is an image that has been manipulated and scored with a low integrity score of 42/100, indicating it is likely to have been tampered with. The key issues are the use of a cloning tool and the fact that the image was edited using Adobe Photoshop.\n\n## Key findings\n- Cloned region detected (from (57, 536) to (487, 656)): 196 matching features were found copied from one part of the image to another along the same offset, which is a clear sign of using a clone or copy-paste tool.\n- Saved by image editing software: The file was edited using Adobe Photoshop 25.4 (Windows), as indicated by the EXIF metadata.\n- Modified after capture: The last modification time is 2.7 days after the capture time, suggesting the image was edited after it was originally taken.\n\n## Consistent with an original\n- No individual check returned a clean result.\n\n## Recommended next steps\n- Obtain the original device copy of the image to compare with the tampered version.\n- Compare the image with a known-good source to determine the extent of the tampering.\n- Consider the context and other evidence to assess the significance of the tampering.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps([])
    )
    db.add(e_tampered)
    db.flush()
    db.add_all([
        Finding(evidence_id=e_tampered.id, category="pixel", check="copy_move", severity="high", penalty=30,
                title="Cloned region detected",
                detail="196 matching features were found copied from one part of the image to another along the same offset, which is a clear sign of using a clone or copy-paste tool.",
                location=json.dumps({"kind": "region", "from": [57, 536], "to": [487, 656]})),
        Finding(evidence_id=e_tampered.id, category="metadata", check="software", severity="medium", penalty=14,
                title="Saved by image editing software (Adobe Photoshop 25.4 (Windows))",
                detail="The EXIF Software tag names an image editor: Adobe Photoshop 25.4 (Windows).",
                location=json.dumps({"kind": "field", "name": "EXIF: Software"})),
        Finding(evidence_id=e_tampered.id, category="metadata", check="modified_after_capture", severity="medium", penalty=14,
                title="Modified after capture (2.7 days later)",
                detail="EXIF DateTime (2026:10:13 08:47:00) is later than DateTimeOriginal (2026:10:10 09:15:00).",
                location=json.dumps({"kind": "field", "name": "EXIF: DateTimeOriginal vs DateTime"})),
        Finding(evidence_id=e_tampered.id, category="ai", check="ai_image", severity="info", penalty=0,
                title="AI-generated image check: natural camera photo (1%)",
                detail="SwinV2 classifier rated this image 1.2% machine-generated.",
                location=json.dumps({"kind": "model", "name": "ai-image-detector-deploy"}))
    ])

    # File 3: video_edited.mp4 (54, Needs review)
    make_file("e_video_edited.mp4", 1048576)
    e_vedit = Evidence(
        case_id=c1.id, filename="video_edited.mp4", stored_name="e_video_edited.mp4", media_type="video",
        size=1048576, sha256="ab678e559afb5a242c3d51eb99a4c0a5d4d3e2182054a81e3a1ef5efa23d",
        status="done", stage="Done", progress=100, score=54, verdict="Needs review",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 26, "container": 20}),
        details=json.dumps({
            "duration": 17.0, "fps": 25.0, "width": 1280, "height": 720,
            "cuts": [9.7], "frozen": [[7.2, 9.7]],
            "frames": [
                {"time": 0.0, "score": 0.0}, {"time": 2.4, "score": 0.0},
                {"time": 4.8, "score": 0.0}, {"time": 7.2, "score": 0.01},
                {"time": 9.7, "score": 0.0}, {"time": 12.1, "score": 0.0},
                {"time": 14.5, "score": 0.01}, {"time": 17.0, "score": 0.0}
            ]
        }),
        report="## Summary\nVideo file shows evidence of editing cuts and frozen frames.\n\n## Key findings\n- Hard cut detected at 0:09.7.\n- Frozen frame interval detected between 0:07.2 and 0:09.7.\n- Metadata indicates editing app: CapCut.\n\n## Consistent with an original\n- Audio track matches natural acoustic expectations.\n\n## Recommended next steps\n- Request unaltered CCTV recorder export.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps([])
    )
    db.add(e_vedit)
    db.flush()
    db.add_all([
        Finding(evidence_id=e_vedit.id, category="container", check="hard_cuts", severity="medium", penalty=14,
                title="Hard cut detected (at 0:09.7)",
                detail="Consecutive frame difference spike (robust z-score 14.2) indicates a splice.",
                location=json.dumps({"kind": "time", "seconds": 9.7})),
        Finding(evidence_id=e_vedit.id, category="container", check="frozen_frames", severity="medium", penalty=14,
                title="Frozen frames detected (0:07.2 - 0:09.7)",
                detail="Identical consecutive frames for 2.5 seconds hide potential missing footage.",
                location=json.dumps({"kind": "time_range", "start": 7.2, "end": 9.7})),
        Finding(evidence_id=e_vedit.id, category="metadata", check="video_editor", severity="high", penalty=26,
                title="Video editing software named in metadata (CapCut)",
                detail="Container metadata indicates CapCut export.",
                location=json.dumps({"kind": "field", "name": "comment"}))
    ])

    # File 4: video_original.mp4 (82, Consistent)
    make_file("e_video_original.mp4", 402534)
    e_vorig = Evidence(
        case_id=c1.id, filename="video_original.mp4", stored_name="e_video_original.mp4", media_type="video",
        size=402534, sha256="f829a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
        status="done", stage="Done", progress=100, score=82, verdict="Consistent",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 18}), details=json.dumps({"duration": 17.0, "cuts": [], "frozen": []}),
        report="## Summary\nOriginal video footage with minor container re-encoding flags.\n\n## Key findings\n- No cuts or frozen frames detected.\n\n## Consistent with an original\n- Frame progression is smooth and continuous.\n\n## Recommended next steps\n- Ready for forensic archival.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_vorig)

    # File 5: photo_stripped.jpg (94, Consistent)
    make_file("e_photo_stripped.jpg", 285184)
    e_pstrip = Evidence(
        case_id=c1.id, filename="photo_stripped.jpg", stored_name="e_photo_stripped.jpg", media_type="image",
        size=285184, sha256="e1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
        status="done", stage="Done", progress=100, score=94, verdict="Consistent",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 6}), details=json.dumps({"width": 1600, "height": 1067}),
        report="## Summary\nImage is structurally authentic with stripped EXIF headers.\n\n## Key findings\n- Metadata stripped or absent.\n\n## Consistent with an original\n- Noise and pixel distributions are consistent.\n\n## Recommended next steps\n- Use original file where available.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_pstrip)
    db.flush()
    db.add(Finding(evidence_id=e_pstrip.id, category="metadata", check="exif_stripped", severity="low", penalty=6,
                   title="No camera metadata (EXIF stripped or absent)",
                   detail="A JPEG straight from a camera normally carries make, model and capture time.",
                   location=json.dumps({"kind": "field", "name": "EXIF"})))

    # File 6: photo_original.jpg (100, Consistent)
    make_file("e_photo_original.jpg", 521113)
    e_porig = Evidence(
        case_id=c1.id, filename="photo_original.jpg", stored_name="e_photo_original.jpg", media_type="image",
        size=521113, sha256="92cff3855ccd28a50f1883b4c6e917d23a54687b1c3e5d7f9a2b4c6e807f5812",
        status="done", stage="Done", progress=100, score=100, verdict="Consistent",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({}), details=json.dumps({"width": 1600, "height": 1067}),
        report="## Summary\nAuthentic camera photograph with intact EXIF and uniform sensor noise.\n\n## Key findings\n- All forensic checks passed.\n\n## Consistent with an original\n- Camera EXIF, noise distribution, and ELA are fully consistent with camera intake.\n\n## Recommended next steps\n- Intact reference for comparison.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_porig)
    db.flush()
    db.add(Finding(evidence_id=e_porig.id, category="metadata", check="exif", severity="info", penalty=0,
                   title="Metadata consistent",
                   detail="No editing software, date conflict or size mismatch in the metadata.",
                   location=json.dumps({"kind": "field", "name": "EXIF"})))

    # -------------------------------------------------------------
    # CASE 2: Northgate Trading invoice dispute
    # -------------------------------------------------------------

    # File 7: invoice_tampered.pdf (27, Likely manipulated)
    make_file("e_invoice_tampered.pdf", 5324)
    e_invtam = Evidence(
        case_id=c2.id, filename="invoice_tampered.pdf", stored_name="e_invoice_tampered.pdf", media_type="document",
        size=5324, sha256="4df7b357a09e139414e0f5451e5927ba1387d812a2010c28340d8525725",
        status="done", stage="Done", progress=100, score=27, verdict="Likely manipulated",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"metadata": 28, "document": 45}), details=json.dumps({"revisions": 2, "pages": 1}),
        report="## Summary\nPDF document shows structural evidence of multiple incremental saves and font tampering over invoice amounts.\n\n## Key findings\n- Font inconsistency: edited amounts \"2,51,000\" and \"3,29,000\" use Times-Roman while the document body is Helvetica.\n- White-out rectangle: filled white shape detected directly beneath altered amount.\n- Producer: iLovePDF editor identified.\n- Incremental updates: document saved 2 times after creation.\n\n## Consistent with an original\n- None.\n\n## Recommended next steps\n- Request vendor original ledger copy.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps([])
    )
    db.add(e_invtam)
    db.flush()
    db.add_all([
        Finding(evidence_id=e_invtam.id, category="document", check="font_forensics", severity="high", penalty=26,
                title="Font inconsistency: edited amounts in different font",
                detail="Amounts \"2,51,000\" and \"3,29,000\" use font tiro (Times) on a line set in helv (Helvetica).",
                location=json.dumps({"kind": "page_boxes", "page": 1, "boxes": [[445, 290, 520, 315], [445, 370, 520, 395]]})),
        Finding(evidence_id=e_invtam.id, category="document", check="hidden_text", severity="medium", penalty=14,
                title="Hidden text: white-out rectangle over amount",
                detail="Filled white shape drawn on top of earlier line items.",
                location=json.dumps({"kind": "page_boxes", "page": 1, "boxes": [[445, 290, 520, 315]]})),
        Finding(evidence_id=e_invtam.id, category="document", check="incremental_updates", severity="high", penalty=26,
                title="PDF was saved 2 times (incremental updates)",
                detail="Multiple %%EOF markers found.",
                location=json.dumps({"kind": "field", "name": "PDF structure"}))
    ])

    # File 8: voice_tts.wav (45, Likely manipulated)
    make_file("e_voice_tts.wav", 416870)
    e_vtts = Evidence(
        case_id=c2.id, filename="voice_tts.wav", stored_name="e_voice_tts.wav", media_type="audio",
        size=416870, sha256="633326ca409c2f44c680f585915d3fa968e734bc1a78e7208ff95f2442e75",
        status="done", stage="Done", progress=100, score=45, verdict="Likely manipulated",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"voice": 55}),
        details=json.dumps({
            "duration": 9.4, "cutoff_hz": 7000,
            "silences": [[1.2, 1.6], [3.5, 3.9]],
            "tts_timeline": [{"time": 0.0, "score": 1.0}, {"time": 4.0, "score": 1.0}, {"time": 8.0, "score": 1.0}]
        }),
        report="## Summary\nAudio recording exhibits artificial text-to-speech characteristics and unnatural digital silence splices.\n\n## Key findings\n- wav2vec2 classifier flagged synthetic voice: avg 100%, peak 100%.\n- Two stretches of exact digital silence (zero samples) detected.\n- Bandwidth cutoff at 7.0 kHz indicates speech-synthesis engine upsampling.\n\n## Consistent with an original\n- None.\n\n## Recommended next steps\n- Authenticate caller phone record.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps([])
    )
    db.add(e_vtts)
    db.flush()
    db.add_all([
        Finding(evidence_id=e_vtts.id, category="voice", check="synthetic_voice", severity="high", penalty=52,
                title="Synthetic voice detected (100% probability)",
                detail="The wav2vec2 deepfake audio model identified speech synthesis artefacts.",
                location=json.dumps({"kind": "time_range", "start": 0.0, "end": 9.4})),
        Finding(evidence_id=e_vtts.id, category="audio", check="digital_silence", severity="medium", penalty=14,
                title="Unnatural digital silence (2 stretches)",
                detail="Stretches of exact zero amplitude samples detected.",
                location=json.dumps({"kind": "time_ranges", "ranges": [[1.2, 1.6], [3.5, 3.9]]})),
        Finding(evidence_id=e_vtts.id, category="audio", check="bandwidth", severity="low", penalty=6,
                title="Bandwidth upsampled (cutoff at 7 kHz)",
                detail="Frequency ceiling indicates synthetic voice generation engine.",
                location=json.dumps({"kind": "field", "name": "bandwidth"}))
    ])

    # File 9: statement_tampered.docx (74, Needs review)
    make_file("e_statement_tampered.docx", 1520)
    e_stamtam = Evidence(
        case_id=c2.id, filename="statement_tampered.docx", stored_name="e_statement_tampered.docx", media_type="document",
        size=1520, sha256="87a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
        status="done", stage="Done", progress=100, score=74, verdict="Needs review",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"document": 26}), details=json.dumps({"tracked_changes": 1}),
        report="## Summary\nWord document contains tracked revisions altering witness testimony.\n\n## Key findings\n- Tracked deletion/insertion: changed \"did not see\" to \"clearly saw\".\n\n## Consistent with an original\n- Author metadata matches creator.\n\n## Recommended next steps\n- Compare with signed deposition transcript.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_stamtam)
    db.flush()
    db.add(Finding(evidence_id=e_stamtam.id, category="document", check="tracked_changes", severity="high", penalty=26,
                   title="Tracked change detected (\"did not see\" -> \"clearly saw\")",
                   detail="Revision marks indicate substantive edit after initial draft.",
                   location=json.dumps({"kind": "field", "name": "revisions"})))

    # File 10: statement_original.docx (75, Needs review)
    make_file("e_statement_v2.docx", 1490)
    e_stamorig = Evidence(
        case_id=c2.id, filename="statement_original.docx", stored_name="e_statement_v2.docx", media_type="document",
        size=1490, sha256="76a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a2",
        status="done", stage="Done", progress=100, score=75, verdict="Needs review",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({"document": 25}), details=json.dumps({"tracked_changes": 1}),
        report="## Summary\nWitness statement document with font modifications.\n\n## Key findings\n- Tracked font variation in paragraph 2.\n\n## Consistent with an original\n- Creator metadata intact.\n\n## Recommended next steps\n- Compare with signed original.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_stamorig)
    db.flush()
    db.add(Finding(evidence_id=e_stamorig.id, category="document", check="mixed_fonts", severity="medium", penalty=14,
                   title="Mixed fonts in paragraph",
                   detail="Multiple typography styles found within single paragraph block.",
                   location=json.dumps({"kind": "field", "name": "fonts"})))

    # File 11: voice_human.ogg (100, Consistent)
    make_file("e_voice_human.ogg", 541920)
    e_vhog = Evidence(
        case_id=c2.id, filename="voice_human.ogg", stored_name="e_voice_human.ogg", media_type="audio",
        size=541920, sha256="65a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a3",
        status="done", stage="Done", progress=100, score=100, verdict="Consistent",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({}), details=json.dumps({"duration": 6.0, "cutoff_hz": 22050}),
        report="## Summary\nHuman vocal recording with continuous ambient room noise.\n\n## Key findings\n- wav2vec2 classifier confirmed natural speech.\n\n## Consistent with an original\n- Microphone background noise is uniform.\n\n## Recommended next steps\n- Retain as original sample.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_vhog)

    # File 12: invoice_original.pdf (100, Consistent)
    make_file("e_invoice_original.pdf", 4410)
    e_invorig = Evidence(
        case_id=c2.id, filename="invoice_original.pdf", stored_name="e_invoice_original.pdf", media_type="document",
        size=4410, sha256="54a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a4",
        status="done", stage="Done", progress=100, score=100, verdict="Consistent",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="SI Rohan Patil",
        breakdown=json.dumps({}), details=json.dumps({"revisions": 1, "pages": 1}),
        report="## Summary\nClean original PDF invoice generated by ReportLab.\n\n## Key findings\n- Single revision, uniform fonts, no white-out.\n\n## Consistent with an original\n- Document structure intact.\n\n## Recommended next steps\n- Certified original.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps([])
    )
    db.add(e_invorig)

    # -------------------------------------------------------------
    # CASE 3: Additional Rich Evidence
    # -------------------------------------------------------------

    # File 13: cctv_suspect_crop.jpg (48, Likely manipulated)
    make_file("e_cctv_suspect.jpg", 145200)
    e_face = Evidence(
        case_id=c3.id, filename="cctv_suspect_face_crop.jpg", stored_name="e_cctv_suspect.jpg", media_type="image",
        size=145200, sha256="43a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a5",
        status="done", stage="Done", progress=100, score=48, verdict="Likely manipulated",
        review_status="flagged", received_at=d_oct13, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"ai": 46, "pixel": 6}),
        details=json.dumps({"width": 640, "height": 640, "ai_score": 0.88, "faces_detected": 1}),
        report="## Summary\nHigh probability of deepfake face swapping detected.\n\n## Key findings\n- Vision Transformer face detector scored 88% probability of deepfake facial insertion.\n- Facial boundary blending anomalies noted.\n\n## Consistent with an original\n- None.\n\n## Recommended next steps\n- Acquire raw camera DVR source.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps(["suspect", "deepfake"])
    )
    db.add(e_face)
    db.flush()
    db.add(Finding(evidence_id=e_face.id, category="ai", check="face_deepfake", severity="high", penalty=30,
                   title="Face deepfake detected (88%)",
                   detail="The ViT deepfake model identified facial manipulation artefacts in suspect face crop.",
                   location=json.dumps({"kind": "box", "x": 120, "y": 80, "w": 280, "h": 280})))

    # File 14: wire_transfer_audit.pdf (35, Likely manipulated)
    make_file("e_wire_transfer.pdf", 8940)
    e_wire = Evidence(
        case_id=c3.id, filename="wire_transfer_receipt.pdf", stored_name="e_wire_transfer.pdf", media_type="document",
        size=8940, sha256="32a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a6",
        status="done", stage="Done", progress=100, score=35, verdict="Likely manipulated",
        review_status="not_reviewed", received_at=d_oct13, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"document": 45, "metadata": 20}),
        details=json.dumps({"revisions": 3, "pages": 1}),
        report="## Summary\nBank wire receipt shows invalid signature coverage and post-signing alterations.\n\n## Key findings\n- Digital signature byte range invalidated: 1,420 bytes appended after signing.\n- Account numbers edited with substituted font.\n\n## Consistent with an original\n- None.\n\n## Recommended next steps\n- Cross-check with SWIFT confirmation logs.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps(["banking", "fraud"])
    )
    db.add(e_wire)
    db.flush()
    db.add(Finding(evidence_id=e_wire.id, category="document", check="signature_coverage", severity="high", penalty=26,
                   title="Signature coverage broken",
                   detail="Bytes added after the digital signature byte range invalidating authenticity.",
                   location=json.dumps({"kind": "field", "name": "ByteRange"})))

    # File 15: security_checkpoint_gate4.mp4 (90, Consistent)
    make_file("e_gate4.mp4", 3241500)
    e_gate = Evidence(
        case_id=c3.id, filename="security_checkpoint_gate4.mp4", stored_name="e_gate4.mp4", media_type="video",
        size=3241500, sha256="21a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a7",
        status="done", stage="Done", progress=100, score=90, verdict="Consistent",
        review_status="reviewed", received_at=d_oct13, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"metadata": 10}),
        details=json.dumps({"duration": 30.0, "fps": 30.0, "cuts": [], "frozen": []}),
        report="## Summary\nUnedited perimeter checkpoint CCTV video.\n\n## Key findings\n- Continuous frame flow without cuts or dropped frames.\n\n## Consistent with an original\n- Camera stream header and timestamp metadata verified.\n\n## Recommended next steps\n- Archived as authentic baseline.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="template", tags=json.dumps(["gate4", "cctv"])
    )
    db.add(e_gate)

    # File 16: ceo_extortion_call.wav (44, Likely manipulated)
    make_file("e_ceo_call.wav", 627100)
    e_call = Evidence(
        case_id=c3.id, filename="ceo_extortion_voicemail.wav", stored_name="e_ceo_call.wav", media_type="audio",
        size=627100, sha256="10a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a8",
        status="done", stage="Done", progress=100, score=44, verdict="Likely manipulated",
        review_status="flagged", received_at=d_oct13, uploaded_by="Insp. Meera Kulkarni",
        breakdown=json.dumps({"voice": 55, "audio": 14}),
        details=json.dumps({"duration": 14.2, "cutoff_hz": 8000, "silences": [[4.1, 4.6]]}),
        report="## Summary\nVoicemail recording identified as voice-cloning synthesis.\n\n## Key findings\n- wav2vec2 model scored 99.4% probability of voice cloning synthesis.\n- Tag signatures match ElevenLabs voice engine.\n\n## Consistent with an original\n- None.\n\n## Recommended next steps\n- Subpoena call origin telecommunications metadata.\n\n## Limitation\nAutomated indicators support, but do not replace, expert and legal judgement.",
        report_model="qwen2.5:7b", tags=json.dumps(["voicemail", "extortion"])
    )
    db.add(e_call)
    db.commit()

    # 4. Hash Chain for photo_tampered.jpg (matching Figure 4.7)
    ev_id = e_tampered.id
    f_hash = e_tampered.sha256
    events = [
        ("Received", "SI Rohan Patil", "Uploaded as photo_tampered.jpg, 422,197 bytes", "2026-10-13T20:47:00Z"),
        ("Analysis started", "Analysis engine", "Hash matches intake", "2026-10-13T20:47:00Z"),
        ("Analysis completed", "Analysis engine", "Score 42/100, Likely manipulated, 4 checks recorded", "2026-10-13T20:47:00Z"),
        ("Report exported", "Investigator", "PDF report downloaded", "2026-10-13T20:51:00Z"),
        ("Analysis started", "Analysis engine", "Hash matches intake", "2026-10-13T20:53:00Z"),
        ("Analysis completed", "Analysis engine", "Score 42/100, Likely manipulated, 4 checks recorded", "2026-10-13T20:53:00Z"),
        ("Integrity verified", "Insp. Meera Kulkarni (meera)", "Chain and file intact", "2026-10-17T15:34:00Z"),
        ("Integrity verified", "Insp. Meera Kulkarni (meera)", "Chain and file intact", "2026-10-17T15:37:00Z"),
    ]
    prev = "0" * 64
    for seq, (action, actor, note, at_time) in enumerate(events, 1):
        eh = custody.compute_event_hash(ev_id, seq, action, actor, at_time, f_hash, prev, note)
        db.add(CustodyEvent(evidence_id=ev_id, seq=seq, action=action, actor=actor,
                            at=at_time, file_hash=f_hash, prev_hash=prev, event_hash=eh, note=note))
        prev = eh
    db.commit()

    # 5. Add Notes for photo_tampered.jpg
    db.add(Note(evidence_id=e_tampered.id, author="SI Rohan Patil",
                body="Brick wall section cloned onto graffiti. Pasted jacket visible on right doorway.",
                created_at="2026-10-13T20:52:00Z"))
    db.commit()

    # 6. Activity log matching Figure 4.10
    act_entries = [
        ("Insp. Meera Kulkarni (meera)", "compare", "Compared evidence photo_original.jpg vs photo_tampered.jpg", c1.id, e_tampered.id, "2026-10-17T15:37:00Z"),
        ("Insp. Meera Kulkarni (meera)", "view", "Viewed evidence photo_tampered.jpg", c1.id, e_tampered.id, "2026-10-17T15:37:00Z"),
        ("Insp. Meera Kulkarni (meera)", "verify", "Verified integrity photo_tampered.jpg: Chain and file intact", c1.id, e_tampered.id, "2026-10-17T15:37:00Z"),
        ("Insp. Meera Kulkarni (meera)", "login", "Signed in", None, None, "2026-10-17T15:36:00Z"),
        ("Insp. Meera Kulkarni (meera)", "chat", "Asked about evidence photo_tampered.jpg", c1.id, e_tampered.id, "2026-10-17T15:36:00Z"),
        ("Insp. Meera Kulkarni (meera)", "compare", "Compared evidence photo_original.jpg vs photo_tampered.jpg", c1.id, e_tampered.id, "2026-10-17T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "view", "Viewed evidence photo_original.jpg", c1.id, e_porig.id, "2026-10-17T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "view", "Viewed evidence video_edited.mp4", c1.id, e_vedit.id, "2026-10-17T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "view", "Viewed evidence voice_tts.wav", c2.id, e_vtts.id, "2026-10-17T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "view", "Viewed evidence invoice_tampered.pdf", c2.id, e_invtam.id, "2026-10-17T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "verify", "Verified integrity photo_tampered.jpg: Chain and file intact", c1.id, e_tampered.id, "2026-10-17T15:34:00Z"),
        ("Insp. Meera Kulkarni (meera)", "login", "Signed in", None, None, "2026-10-17T15:34:00Z"),
    ]
    for actor, action, summary, cid, eid, at_time in act_entries:
        db.add(ActivityLog(actor=actor, action=action, summary=summary, case_id=cid,
                           evidence_id=eid, ip="127.0.0.1", at=at_time))
    db.commit()

    # 7. Generate beautiful visual artifacts for photo_tampered.jpg & photo_original.jpg
    src_ss = Path("C:/Users/krish/.gemini/antigravity/brain/bbc3bc24-13c3-43df-b2c7-26ae982f1e6d/.user_uploaded/media_1792576031580_da4eda9d.png")
    art_dir = config.ARTIFACT_DIR / str(e_tampered.id)
    art_dir.mkdir(parents=True, exist_ok=True)
    orig_art_dir = config.ARTIFACT_DIR / str(e_porig.id)
    orig_art_dir.mkdir(parents=True, exist_ok=True)
    strip_art_dir = config.ARTIFACT_DIR / str(e_pstrip.id)
    strip_art_dir.mkdir(parents=True, exist_ok=True)
    pig_art_dir = config.ARTIFACT_DIR / str(e_pig.id)
    pig_art_dir.mkdir(parents=True, exist_ok=True)
    face_art_dir = config.ARTIFACT_DIR / str(e_face.id)
    face_art_dir.mkdir(parents=True, exist_ok=True)

    if src_ss.exists():
        raw_ss = cv2.imread(str(src_ss))
        alley_crop = raw_ss[155:435, 163:590]
        alley_hires = cv2.resize(alley_crop, (1600, 1067), interpolation=cv2.INTER_CUBIC)

        cv2.imwrite(str(art_dir / "clone.png"), alley_hires)
        clean = alley_hires.copy()
        cv2.imwrite(str(art_dir / "original.jpg"), clean)
        cv2.imwrite(str(orig_art_dir / "original.jpg"), clean)
        cv2.imwrite(str(orig_art_dir / "clone.png"), clean)
        cv2.imwrite(str(strip_art_dir / "original.jpg"), clean)
        cv2.imwrite(str(strip_art_dir / "clone.png"), clean)

        # ELA layer
        tmp_jpg = art_dir / "_ela_tmp.jpg"
        cv2.imwrite(str(tmp_jpg), clean, [cv2.IMWRITE_JPEG_QUALITY, 90])
        recomp = cv2.imread(str(tmp_jpg))
        tmp_jpg.unlink(missing_ok=True)
        diff = cv2.absdiff(clean, recomp)
        ela = cv2.applyColorMap(cv2.convertScaleAbs(diff, alpha=15.0), cv2.COLORMAP_INFERNO)
        cv2.imwrite(str(art_dir / "ela.png"), ela)
        cv2.imwrite(str(orig_art_dir / "ela.png"), ela)
        cv2.imwrite(str(strip_art_dir / "ela.png"), ela)

        # Noise layer
        gray = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
        noise = cv2.Laplacian(gray, cv2.CV_64F)
        noise_norm = cv2.normalize(np.abs(noise), None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        cv2.imwrite(str(art_dir / "noise.png"), cv2.applyColorMap(noise_norm, cv2.COLORMAP_VIRIDIS))
        cv2.imwrite(str(orig_art_dir / "noise.png"), cv2.applyColorMap(noise_norm, cv2.COLORMAP_VIRIDIS))
        cv2.imwrite(str(strip_art_dir / "noise.png"), cv2.applyColorMap(noise_norm, cv2.COLORMAP_VIRIDIS))

        # AI heatmap
        ai_heat = cv2.applyColorMap(cv2.resize(noise_norm, (200, 133)), cv2.COLORMAP_JET)
        ai_heat_full = cv2.resize(ai_heat, (1600, 1067))
        overlay = cv2.addWeighted(clean, 0.6, ai_heat_full, 0.4, 0)
        cv2.imwrite(str(art_dir / "ai_heatmap.png"), overlay)
        cv2.imwrite(str(orig_art_dir / "ai_heatmap.png"), clean)
        cv2.imwrite(str(strip_art_dir / "ai_heatmap.png"), clean)
        cv2.imwrite(str(pig_art_dir / "original.jpg"), clean)
        cv2.imwrite(str(pig_art_dir / "ai_heatmap.png"), overlay)
        cv2.imwrite(str(face_art_dir / "original.jpg"), clean)
        cv2.imwrite(str(face_art_dir / "ai_heatmap.png"), overlay)

        cv2.imwrite(str(config.UPLOAD_DIR / e_tampered.stored_name), clean)
        cv2.imwrite(str(config.UPLOAD_DIR / e_porig.stored_name), clean)
        cv2.imwrite(str(config.UPLOAD_DIR / e_pstrip.stored_name), clean)
        cv2.imwrite(str(config.UPLOAD_DIR / e_pig.stored_name), clean)
        cv2.imwrite(str(config.UPLOAD_DIR / e_face.stored_name), clean)

    # 8. Video artifacts
    vedit_art = config.ARTIFACT_DIR / str(e_vedit.id)
    vedit_art.mkdir(parents=True, exist_ok=True)
    vorig_art = config.ARTIFACT_DIR / str(e_vorig.id)
    vorig_art.mkdir(parents=True, exist_ok=True)
    gate_art = config.ARTIFACT_DIR / str(e_gate.id)
    gate_art.mkdir(parents=True, exist_ok=True)

    if src_ss.exists():
        raw_ss = cv2.imread(str(src_ss))
        thumb = cv2.resize(raw_ss[155:435, 163:590], (160, 120))
        for i in range(20):
            cv2.imwrite(str(vedit_art / f"frame_{i:02d}.jpg"), thumb)
            cv2.imwrite(str(vorig_art / f"frame_{i:02d}.jpg"), thumb)
            cv2.imwrite(str(gate_art / f"frame_{i:02d}.jpg"), thumb)

    # 9. Audio spectrograms
    tts_art = config.ARTIFACT_DIR / str(e_vtts.id)
    tts_art.mkdir(parents=True, exist_ok=True)
    vhog_art = config.ARTIFACT_DIR / str(e_vhog.id)
    vhog_art.mkdir(parents=True, exist_ok=True)
    call_art = config.ARTIFACT_DIR / str(e_call.id)
    call_art.mkdir(parents=True, exist_ok=True)

    aud_ss = Path("C:/Users/krish/.gemini/antigravity/brain/bbc3bc24-13c3-43df-b2c7-26ae982f1e6d/.user_uploaded/media_1792576063595_be0747dd.png")
    if aud_ss.exists():
        raw_aud = cv2.imread(str(aud_ss))
        spec_crop = raw_aud[230:370, 35:530]
        if spec_crop.size > 0:
            spec_img = cv2.resize(spec_crop, (1200, 240))
            cv2.imwrite(str(tts_art / "spectrogram.png"), spec_img)
            cv2.imwrite(str(vedit_art / "audio_spectrogram.png"), spec_img)
            cv2.imwrite(str(vhog_art / "spectrogram.png"), spec_img)
            cv2.imwrite(str(call_art / "spectrogram.png"), spec_img)

    # 10. PDF page renders
    inv_art = config.ARTIFACT_DIR / str(e_invtam.id)
    inv_art.mkdir(parents=True, exist_ok=True)
    wire_art = config.ARTIFACT_DIR / str(e_wire.id)
    wire_art.mkdir(parents=True, exist_ok=True)

    inv_canvas = np.full((1000, 750, 3), 255, dtype=np.uint8)
    cv2.putText(inv_canvas, "NORTHGATE TRADING CO.", (60, 80), cv2.FONT_HERSHEY_DUPLEX, 0.7, (20, 20, 20), 2)
    cv2.putText(inv_canvas, "Tax Invoice INV-20418", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1)
    cv2.putText(inv_canvas, "Date: 03 Aug 2026", (60, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1)
    cv2.putText(inv_canvas, "Item", (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.putText(inv_canvas, "Qty", (330, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.putText(inv_canvas, "Rate", (420, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.putText(inv_canvas, "Amount", (540, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.line(inv_canvas, (60, 195), (690, 195), (200, 200, 200), 1)
    cv2.putText(inv_canvas, "Office chairs", (60, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "12", (330, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "4,250", (420, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "2,51,000", (540, 230), cv2.FONT_HERSHEY_COMPLEX, 0.5, (10, 10, 10), 1)
    cv2.rectangle(inv_canvas, (530, 212), (630, 238), (0, 0, 210), 2)
    cv2.putText(inv_canvas, "Standing desks", (60, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "4", (330, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "18,900", (420, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "75,600", (540, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "Delivery", (60, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "1", (330, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "2,400", (420, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "2,400", (540, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.line(inv_canvas, (60, 320), (690, 320), (200, 200, 200), 1)
    cv2.putText(inv_canvas, "Total", (420, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.putText(inv_canvas, "3,29,000", (540, 350), cv2.FONT_HERSHEY_COMPLEX, 0.5, (10, 10, 10), 1)
    cv2.rectangle(inv_canvas, (530, 332), (630, 358), (0, 0, 210), 2)
    cv2.imwrite(str(inv_art / "page-1.png"), inv_canvas)
    cv2.imwrite(str(wire_art / "page-1.png"), inv_canvas)

    db.close()
    print("Database and expanded multi-media demo dataset seeded successfully!")


if __name__ == "__main__":
    create_demo_database()
