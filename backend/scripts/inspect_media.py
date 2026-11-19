import os, sys, pathlib
backend_dir = pathlib.Path(r"C:\Users\krish\.gemini\antigravity\scratch\evidence-integrity-platform\backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.database import SessionLocal
from app.models import Evidence

db = SessionLocal()
files = db.query(Evidence).all()
images = [f for f in files if f.media_type == "image"]
videos = [f for f in files if f.media_type == "video"]
audios = [f for f in files if f.media_type == "audio"]
docs = [f for f in files if f.media_type == "document"]

print(f"Total: {len(files)} | Images: {len(images)} | Videos: {len(videos)} | Audio: {len(audios)} | Docs: {len(docs)}")
for i in images[:3]:
    print(f"  Image #{i.id}: {i.filename} | score={i.score} | verdict={i.verdict}")
for v in videos[:3]:
    print(f"  Video #{v.id}: {v.filename} | score={v.score} | verdict={v.verdict}")
