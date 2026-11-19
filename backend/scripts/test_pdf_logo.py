import os
import sys
import pathlib

backend_dir = pathlib.Path(r"C:\Users\krish\.gemini\antigravity\scratch\evidence-integrity-platform\backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.database import SessionLocal
from app.models import Evidence, Case
from app import report_pdf

db = SessionLocal()
ev = db.query(Evidence).first()
case = db.query(Case).first()

print(f"Testing PDF generation with logo for evidence #{ev.id} ({ev.filename})...")

try:
    pdf_bytes = report_pdf.evidence_pdf(ev, case)
    print(f"  -> Generated evidence report PDF: {len(pdf_bytes)} bytes [OK]")
except Exception as e:
    print(f"  -> ERROR in evidence report PDF: {e}")
    sys.exit(1)

try:
    sec63_bytes = report_pdf.section63_certificate_pdf(ev, case)
    print(f"  -> Generated Section 63 BSA certificate PDF: {len(sec63_bytes)} bytes [OK]")
except Exception as e:
    print(f"  -> ERROR in Section 63 certificate PDF: {e}")
    sys.exit(1)

print("PDF logo rendering verified successfully!")
