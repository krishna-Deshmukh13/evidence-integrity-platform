"""PDF exports, report rewrite, language-model status, cryptographic report verification, and custody anchoring."""
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from .. import activity, custody, llm, pipeline, report_pdf, signer
from ..database import get_db
from ..deps import client_ip, current_user, require_role, verify_case_access, verify_evidence_access
from ..models import Case, Evidence, ExportedReport, User, now_iso

router = APIRouter(prefix="/api")


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


@router.get("/llm/status")
def llm_status(user: User = Depends(current_user)):
    return llm.status()


@router.get("/evidence/{evidence_id}/report.pdf")
def evidence_report(evidence_id: int, request: Request, lang: str = Query("en"),
                    db: Session = Depends(get_db), user: User = Depends(current_user)):
    ev = verify_evidence_access(db, user, evidence_id)
    if ev.status != "done":
        raise HTTPException(409, "Analysis is not finished yet")

    case = db.get(Case, ev.case_id)
    doc_token = uuid.uuid4().hex
    raw_pdf = report_pdf.evidence_pdf(ev, case, lang=lang, doc_token=doc_token)
    signed_pdf, rep_hash = signer.sign_pdf_bytes(raw_pdf)

    # Save to ExportedReport registry
    record = ExportedReport(
        report_sha256=rep_hash,
        doc_token=doc_token,
        case_id=ev.case_id,
        case_reference=case.reference if case else "",
        evidence_id=ev.id,
        report_type="evidence",
        signer_fingerprint=signer.get_signer_fingerprint(),
    )
    db.add(record)

    custody.add_event(db, ev, "Report exported", activity.actor_name(user), f"Signed PDF report downloaded ({lang})")
    db.commit()
    activity.log(db, activity.actor_name(user), "report_export", f"Exported signed report for {ev.filename}", ev.case_id, ev.id,
                 client_ip(request))

    return Response(
        signed_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe(ev.filename)}-report.pdf"'}
    )


@router.get("/cases/{case_id}/report.pdf")
def case_report(case_id: int, request: Request, lang: str = Query("en"),
                db: Session = Depends(get_db), user: User = Depends(current_user)):
    case = verify_case_access(db, user, case_id)
    if not any(e.status == "done" for e in case.evidence):
        raise HTTPException(409, "No analysed files in this case yet")

    from .case_intel import generate_case_summary
    sum_text, sum_model = generate_case_summary(case, db)
    doc_token = uuid.uuid4().hex
    raw_pdf = report_pdf.case_bundle_pdf(case, case.evidence, summary_text=sum_text, summary_model=sum_model,
                                         lang=lang, doc_token=doc_token)
    signed_pdf, rep_hash = signer.sign_pdf_bytes(raw_pdf)

    record = ExportedReport(
        report_sha256=rep_hash,
        doc_token=doc_token,
        case_id=case.id,
        case_reference=case.reference,
        evidence_id=None,
        report_type="bundle",
        signer_fingerprint=signer.get_signer_fingerprint(),
    )
    db.add(record)

    for e in case.evidence:
        if e.status == "done":
            custody.add_event(db, e, "Case bundle exported", activity.actor_name(user), f"Case bundle {case.reference}")
    db.commit()
    activity.log(db, activity.actor_name(user), "report_export", f"Exported signed case bundle {case.reference}", case.id,
                 ip=client_ip(request))

    return Response(
        signed_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe(case.reference)}-bundle.pdf"'}
    )


@router.get("/evidence/{evidence_id}/section63.pdf")
def section63_certificate(evidence_id: int, request: Request, lang: str = Query("en"),
                          db: Session = Depends(get_db),
                          user: User = Depends(require_role("investigator"))):
    """Generate Draft Certificate under Section 63 of Bharatiya Sakshya Adhiniyam, 2023."""
    ev = verify_evidence_access(db, user, evidence_id)

    case = db.get(Case, ev.case_id)
    doc_token = uuid.uuid4().hex
    raw_pdf = report_pdf.section63_certificate_pdf(ev, case, examiner_name=activity.actor_name(user),
                                                   lang=lang, doc_token=doc_token)
    signed_pdf, rep_hash = signer.sign_pdf_bytes(raw_pdf)

    record = ExportedReport(
        report_sha256=rep_hash,
        doc_token=doc_token,
        case_id=ev.case_id,
        case_reference=case.reference if case else "",
        evidence_id=ev.id,
        report_type="section63",
        signer_fingerprint=signer.get_signer_fingerprint(),
    )
    db.add(record)

    custody.add_event(db, ev, "Section 63 certificate exported", activity.actor_name(user),
                      f"Draft Section 63 BSA 2023 certificate downloaded ({lang})")
    db.commit()
    activity.log(db, activity.actor_name(user), "report_export",
                 f"Exported Section 63 BSA 2023 certificate for {ev.filename}", ev.case_id, ev.id,
                 client_ip(request))

    return Response(
        signed_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe(ev.filename)}-section63-certificate.pdf"'}
    )


@router.get("/reports/verify")
def verify_report(hash: str = Query(..., description="Report SHA-256 hash or document verification token"),
                  db: Session = Depends(get_db)):
    """Public verification endpoint: checks if report hash/token matches an official export.
    Exposes no evidence content, filenames, or case details beyond case reference and issue date."""
    h = hash.strip().lower()
    rep = db.query(ExportedReport).filter(
        (ExportedReport.report_sha256 == h) | (ExportedReport.doc_token == h)
    ).first()

    if rep:
        return {
            "match": True,
            "message": f"Matches an authentic forensic report issued on {rep.issued_at} for case {rep.case_reference}.",
            "issued_at": rep.issued_at,
            "case_reference": rep.case_reference,
            "report_type": rep.report_type,
            "signer_fingerprint": rep.signer_fingerprint,
        }
    return {
        "match": False,
        "message": "No match found in platform registry. Document hash is unrecorded or may have been modified.",
    }


@router.get("/custody/anchor")
def export_anchor(request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_role("investigator"))):
    """Export signed JSON containing the head hash of every chain on the platform."""
    anchor_data = signer.export_custody_anchor(db, actor=activity.actor_name(user))
    activity.log(db, activity.actor_name(user), "anchor_export",
                 f"Exported custody anchor with {anchor_data.get('total_chains')} chains",
                 ip=client_ip(request))
    now_tag = now_iso()[:19].replace(":", "-").replace("T", "_")
    return Response(
        json.dumps(anchor_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="eip-custody-anchor-{now_tag}.json"'}
    )


@router.post("/custody/verify-anchor")
async def verify_anchor(request: Request, file: Optional[UploadFile] = File(None),
                        db: Session = Depends(get_db),
                        user: User = Depends(require_role("investigator"))):
    """Verify live custody chains against an uploaded anchor JSON file or request body."""
    anchor_dict = None
    if file:
        content = await file.read()
        try:
            anchor_dict = json.loads(content.decode("utf-8"))
        except Exception:
            raise HTTPException(400, "Invalid JSON in uploaded anchor file")
    else:
        try:
            anchor_dict = await request.json()
        except Exception:
            raise HTTPException(400, "Please provide an anchor JSON file or body")

    result = signer.verify_custody_anchor(db, anchor_dict)
    activity.log(db, activity.actor_name(user), "anchor_verify",
                 f"Verified custody anchor: ok={result.get('ok')}, matching={result.get('matching_chains')}/{result.get('total_chains')}",
                 ip=client_ip(request))
    return result


@router.post("/evidence/{evidence_id}/rewrite-report")
def rewrite_report(evidence_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_role("investigator"))):
    ev = verify_evidence_access(db, user, evidence_id)
    if ev.status != "done":
        raise HTTPException(409, "Analysis is not finished yet")
    pipeline.enqueue_report(ev.id)
    return {"queued": True, "llm": llm.status()}
