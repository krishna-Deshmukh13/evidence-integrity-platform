"""Examiner review: status, assignee, tags, notes, finding feedback, retraining export."""
import csv
import io
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import activity, custody
from ..database import get_db
from ..deps import client_ip, require_role, verify_evidence_access
from ..models import Case, Evidence, Finding, Note, User, now_iso

router = APIRouter(prefix="/api")
STATUSES = {"not_reviewed", "reviewed", "flagged", "cleared"}


class ReviewPatch(BaseModel):
    review_status: Optional[str] = None
    assignee_id: Optional[int] = None
    unassign: bool = False
    tags: Optional[List[str]] = None


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class FindingFeedbackIn(BaseModel):
    decision: str = Field(..., pattern="^(confirmed|rejected|cleared)$")
    note: Optional[str] = ""


@router.patch("/evidence/{evidence_id}")
def patch_evidence(evidence_id: int, body: ReviewPatch, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_role("investigator"))):
    ev = verify_evidence_access(db, user, evidence_id)
    changes = []
    if body.review_status is not None:
        if body.review_status not in STATUSES:
            raise HTTPException(400, "Unknown review status")
        ev.review_status = body.review_status
        changes.append(f"status={body.review_status}")
        activity.log(db, activity.actor_name(user), "verdict",
                     f"Updated review status of {ev.filename} to '{body.review_status}'",
                     ev.case_id, ev.id, client_ip(request))
    if body.unassign:
        ev.assignee_id = None
        changes.append("unassigned")
    elif body.assignee_id is not None:
        if not db.get(User, body.assignee_id):
            raise HTTPException(400, "Unknown user")
        ev.assignee_id = body.assignee_id
        changes.append(f"assigned to user {body.assignee_id}")
    if body.tags is not None:
        ev.tags = json.dumps(sorted({t.strip()[:40] for t in body.tags if t.strip()}))
        changes.append("tags")
    db.commit()
    activity.log(db, activity.actor_name(user), "review", f"Updated {ev.filename}: {', '.join(changes)}",
                 ev.case_id, ev.id, client_ip(request))
    return {"review_status": ev.review_status, "assignee_id": ev.assignee_id, "tags": ev.get_tags()}


@router.post("/evidence/{evidence_id}/notes")
def add_note(evidence_id: int, body: NoteIn, request: Request, db: Session = Depends(get_db),
             user: User = Depends(require_role("investigator"))):
    ev = verify_evidence_access(db, user, evidence_id)
    n = Note(evidence_id=ev.id, author=activity.actor_name(user), body=body.body)
    db.add(n)
    db.commit()
    activity.log(db, activity.actor_name(user), "note", f"Added a note on {ev.filename}", ev.case_id, ev.id,
                 client_ip(request))
    return {"id": n.id, "author": n.author, "body": n.body, "created_at": n.created_at}


@router.post("/evidence/{evidence_id}/findings/{finding_id}/feedback")
def set_finding_feedback(evidence_id: int, finding_id: int, body: FindingFeedbackIn, request: Request,
                         db: Session = Depends(get_db),
                         user: User = Depends(require_role("investigator"))):
    """Store examiner confirmation or rejection of an automated forensic finding."""
    ev = verify_evidence_access(db, user, evidence_id)
    finding = db.get(Finding, finding_id)
    if not finding or finding.evidence_id != evidence_id:
        raise HTTPException(404, "Finding not found on this evidence")

    decision = body.decision.lower()
    actor = activity.actor_name(user)
    now_str = now_iso()

    if decision == "cleared":
        finding.feedback = None
        finding.feedback_by = None
        finding.feedback_at = None
        finding.feedback_note = ""
        action_desc = f"Cleared feedback on finding '{finding.title}'"
    else:
        finding.feedback = decision
        finding.feedback_by = actor
        finding.feedback_at = now_str
        finding.feedback_note = (body.note or "").strip()
        action_desc = f"Marked finding '{finding.title}' as {decision.upper()}"

    # Write to custody log
    custody.add_event(db, ev, "Finding feedback", actor, f"{action_desc}. Note: {finding.feedback_note or 'None'}")
    db.commit()

    # Write to activity log
    activity.log(db, actor, "finding_feedback", action_desc, ev.case_id, ev.id, client_ip(request))

    return {
        "id": finding.id,
        "evidence_id": finding.evidence_id,
        "title": finding.title,
        "feedback": finding.feedback,
        "feedback_by": finding.feedback_by,
        "feedback_at": finding.feedback_at,
        "feedback_note": finding.feedback_note,
    }


@router.get("/examiner-feedback/export.csv")
def export_feedback_csv(request: Request, db: Session = Depends(get_db),
                        user: User = Depends(require_role("investigator"))):
    """Export examiner confirmed and rejected findings as CSV for machine learning retraining."""
    findings = db.query(Finding).filter(Finding.feedback.isnot(None)).all()
    ev_map = {e.id: e for e in db.query(Evidence).all()}
    case_map = {c.id: c for c in db.query(Case).all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "finding_id", "evidence_id", "filename", "case_reference",
        "category", "check", "severity", "penalty", "title", "detail",
        "feedback_decision", "feedback_by", "feedback_at", "feedback_note"
    ])

    for f in findings:
        ev = ev_map.get(f.evidence_id)
        case = case_map.get(ev.case_id) if ev else None
        writer.writerow([
            f.id,
            f.evidence_id,
            ev.filename if ev else "",
            case.reference if case else "",
            f.category,
            f.check,
            f.severity,
            f.penalty,
            f.title,
            f.detail,
            f.feedback,
            f.feedback_by,
            f.feedback_at,
            f.feedback_note or "",
        ])

    csv_text = output.getvalue()
    activity.log(db, activity.actor_name(user), "feedback_export",
                 f"Exported {len(findings)} examiner feedback rows to CSV", ip=client_ip(request))

    return Response(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="examiner-feedback-retraining.csv"'}
    )
