"""Seed demo cases, users, and evidence files for the Evidence Integrity Platform."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure environment is set
os.environ.setdefault("EI_STORAGE_DIR", str(backend_dir / "storage"))

import numpy as np
from PIL import Image
from app import activity, auth, config, custody, pipeline
from app.database import SessionLocal, init_db
from app.models import ActivityLog, Case, Evidence, Note, User, now_iso
from scripts import make_samples, make_samples2


def generate_ai_pig_image(out_path: Path):
    """Generate a synthetic scene image that triggers the AI generator detector."""
    W, H = 800, 600
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Smooth wave / diffusion-like mathematical gradients
    r = 128 + 110 * np.sin(xx / 25.0) + 40 * np.cos(yy / 35.0)
    g = 120 + 90 * np.cos(xx / 30.0) + 50 * np.sin(yy / 20.0)
    b = 140 + 80 * np.sin((xx + yy) / 40.0)
    img = np.clip(np.stack([r, g, b], axis=2), 0, 255).astype(np.uint8)
    Image.fromarray(img).save(out_path, quality=95)


def add_evidence(db, case_id: int, file_path: Path, uploader: User):
    with open(file_path, "rb") as fh:
        raw = fh.read()
    import hashlib
    sha256 = hashlib.sha256(raw).hexdigest()
    ext = file_path.suffix.lstrip(".").lower()
    stored_name = f"{sha256[:16]}_{file_path.name}"
    dest = config.UPLOAD_DIR / stored_name
    dest.write_bytes(raw)

    # Detect media type
    media_type = None
    for mt, exts in config.MEDIA_TYPES.items():
        if ext in exts:
            media_type = mt
            break
    if not media_type:
        media_type = "document"

    ev = Evidence(
        case_id=case_id,
        filename=file_path.name,
        stored_name=stored_name,
        media_type=media_type,
        size=len(raw),
        sha256=sha256,
        status="queued",
        stage="Queued",
        uploaded_by=uploader.full_name,
    )
    db.add(ev)
    db.flush()
    custody.add_event(db, ev, "Received", activity.actor_name(uploader),
                      f"Uploaded as {file_path.name}, {len(raw):,} bytes")
    db.commit()
    activity.log(db, activity.actor_name(uploader), "upload", f"Uploaded {file_path.name}",
                 case_id, ev.id, "127.0.0.1")

    # Process immediately
    pipeline.process(ev.id)
    pipeline.write_report(ev.id)
    db.refresh(ev)
    return ev


def main():
    print("Initializing database...")
    init_db()
    db = SessionLocal()

    # 1. Accounts
    users = {
        "meera": ("Insp. Meera Kulkarni", "admin"),
        "rohan": ("SI Rohan Patil", "investigator"),
        "kavya": ("Kavya Rao", "viewer"),
    }
    user_objs = {}
    for uname, (fname, role) in users.items():
        u = db.query(User).filter(User.username == uname).first()
        if not u:
            u = User(username=uname, full_name=fname, role=role,
                     password_hash=auth.hash_password("ram@1234"), is_active=True)
            db.add(u)
            db.commit()
            print(f"Created account '{uname}' ({role})")
        user_objs[uname] = u

    # 2. Generate samples
    temp_dir = Path(tempfile.mkdtemp(prefix="eip-demo-samples-"))
    try:
        print("Generating demo files...")
        make_samples.make(temp_dir)
        make_samples2.make(temp_dir)
        ai_pig = temp_dir / "ai_generated_pig.jpg"
        generate_ai_pig_image(ai_pig)

        # 3. Cases
        c1 = db.query(Case).filter(Case.reference == "CR-2026-0422").first()
        if not c1:
            c1 = Case(reference="CR-2026-0422", title="Alley CCTV and witness photos",
                      investigator="SI Rohan Patil")
            db.add(c1)
            db.commit()
            print("Created Case CR-2026-0422")

        c2 = db.query(Case).filter(Case.reference == "CR-2026-0418").first()
        if not c2:
            c2 = Case(reference="CR-2026-0418", title="Northgate Trading invoice dispute",
                      investigator="SI Rohan Patil")
            db.add(c2)
            db.commit()
            print("Created Case CR-2026-0418")

        # 4. Upload and process evidence if not already present
        case1_files = [
            "photo_original.jpg",
            "photo_tampered.jpg",
            "photo_stripped.jpg",
            "ai_generated_pig.jpg",
        ]
        if shutil.which("ffmpeg"):
            case1_files.extend(["video_original.mp4", "video_edited.mp4"])

        case2_files = [
            "invoice_original.pdf",
            "invoice_tampered.pdf",
            "statement_original.docx",
            "statement_tampered.docx",
            "voice_human.wav",
            "voice_tts.wav",
        ]

        print("Processing Case 1 evidence...")
        for fname in case1_files:
            p = temp_dir / fname
            if p.exists() and not db.query(Evidence).filter_by(case_id=c1.id, filename=fname).first():
                print(f"  Analyzing {fname}...")
                ev = add_evidence(db, c1.id, p, user_objs["rohan"])
                if fname == "photo_tampered.jpg":
                    ev.review_status = "flagged"
                    ev.tags = json.dumps(["cctv", "suspect"])
                    db.add(Note(evidence_id=ev.id, author="SI Rohan Patil",
                                body="Detected cloned region in brick alley and pasted coat on door frame."))
                    db.commit()

        print("Processing Case 2 evidence...")
        for fname in case2_files:
            p = temp_dir / fname
            if p.exists() and not db.query(Evidence).filter_by(case_id=c2.id, filename=fname).first():
                print(f"  Analyzing {fname}...")
                ev = add_evidence(db, c2.id, p, user_objs["rohan"])
                if fname == "invoice_tampered.pdf":
                    ev.review_status = "flagged"
                    ev.tags = json.dumps(["invoice", "finance"])
                    db.add(Note(evidence_id=ev.id, author="Insp. Meera Kulkarni",
                                body="Discrepancy in item total font face and white-out rectangle over amount."))
                    db.commit()

        # Add initial audit activity
        if db.query(ActivityLog).count() == 0:
            activity.log(db, "Insp. Meera Kulkarni (meera)", "login", "Signed in", ip="127.0.0.1")
            activity.log(db, "SI Rohan Patil (rohan)", "login", "Signed in", ip="127.0.0.1")

        print("\nSeed completed successfully!")
        print("Demo accounts available:")
        print("  - meera (Admin): password ram@1234")
        print("  - rohan (Investigator): password ram@1234")
        print("  - kavya (Viewer): password ram@1234")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        db.close()


if __name__ == "__main__":
    main()
