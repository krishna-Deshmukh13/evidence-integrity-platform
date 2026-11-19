"""Dashboard numbers and cross-case search (Stage 3 adds compare + similar)."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json as _json
import re as _re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import activity, config, custody, llm, similarity
from ..database import get_db
from ..deps import client_ip, current_user, get_user_case_ids, require_role
from ..models import ActivityLog, Case, Evidence, Finding, Note, User, now_iso

router = APIRouter(prefix="/api")


def _row(e, case):
    return {"id": e.id, "filename": e.filename, "media_type": e.media_type, "score": e.score,
            "verdict": e.verdict, "review_status": e.review_status, "received_at": e.received_at,
            "case_id": e.case_id, "case_reference": case.reference if case else "", "size": e.size,
            "case_title": case.title if case else "", "status": e.status,
            "assignee_id": e.assignee_id, "tags": e.get_tags()}


def _live_queue_state(db: Session) -> dict:
    analyzing = db.query(Evidence).filter(Evidence.status == "analyzing").first()
    queued_count = db.query(Evidence).filter(Evidence.status == "queued").count()
    return {
        "active": analyzing is not None or queued_count > 0,
        "current_file": analyzing.filename if analyzing else None,
        "current_evidence_id": analyzing.id if analyzing else None,
        "stage": analyzing.stage if analyzing else "Idle",
        "progress": analyzing.progress if analyzing else 0,
        "number_waiting": queued_count,
        "report_model_status": llm.status()
    }


@router.get("/dashboard/live-queue")
def live_queue(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _live_queue_state(db)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    allowed_ids = get_user_case_ids(db, user)
    if allowed_ids is None:
        ev = db.query(Evidence).all()
        cases = {c.id: c for c in db.query(Case).all()}
    else:
        ev = [e for e in db.query(Evidence).all() if e.case_id in allowed_ids]
        cases = {c.id: c for c in db.query(Case).filter(Case.id.in_(allowed_ids)).all()}
    done = [e for e in ev if e.status == "done" and e.score is not None]

    # Score distribution in 10 bins & 3 bands (0-49, 50-79, 80-100)
    hist = [0] * 10
    for e in done:
        hist[min(9, e.score // 10)] += 1

    score_bands = {
        "0_49": sum(1 for e in done if e.score < 50),
        "50_79": sum(1 for e in done if 50 <= e.score < 80),
        "80_100": sum(1 for e in done if e.score >= 80),
    }

    risk = sorted(done, key=lambda e: e.score)[:8]
    status = {k: sum(1 for e in ev if e.review_status == k) for k in ("not_reviewed", "reviewed", "flagged", "cleared")}

    # Verdicts by media type
    media_types = sorted(list({e.media_type for e in ev} | {"image", "video", "audio", "document", "pdf"}))
    verdicts_by_media_type = {}
    for mt in media_types:
        mt_done = [e for e in done if e.media_type == mt]
        verdicts_by_media_type[mt] = {
            v: sum(1 for e in mt_done if e.verdict == v)
            for v in ("Likely manipulated", "Needs review", "Consistent")
        }
        verdicts_by_media_type[mt]["total"] = len(mt_done)

    # Top findings across all evidence
    check_counter = Counter()
    check_info = {}
    for f in db.query(Finding).all():
        check_counter[f.check] += 1
        if f.check not in check_info:
            check_info[f.check] = {
                "check": f.check,
                "title": f.title,
                "category": f.category,
                "severity": f.severity,
            }
    top_findings = []
    for chk, count in check_counter.most_common(8):
        info = check_info.get(chk, {"check": chk, "title": chk.replace("_", " ").title(), "category": "metadata", "severity": "info"})
        top_findings.append({
            "check": chk,
            "title": info["title"],
            "category": info["category"],
            "severity": info["severity"],
            "count": count
        })

    # Custody health (chains intact vs broken, last full check time)
    intact_chains = 0
    broken_chains = 0
    for e in ev:
        c_res = custody.verify_chain(e.custody)
        if c_res["ok"]:
            intact_chains += 1
        else:
            broken_chains += 1
    last_log = (db.query(ActivityLog)
                .filter(ActivityLog.action == "custody_verify_all")
                .order_by(ActivityLog.id.desc())
                .first())
    last_checked_at = last_log.at if last_log else None
    custody_health = {
        "chains_intact": intact_chains,
        "chains_broken": broken_chains,
        "last_checked_at": last_checked_at,
        "status": "broken" if broken_chains > 0 else "healthy",
    }

    # Needs attention:
    # 1. Failed analyses
    failed = [e for e in ev if e.status == "failed"]
    # 2. Files flagged but unreviewed for >3 days
    now_dt = datetime.now(timezone.utc)
    three_days_ago = now_dt - timedelta(days=3)
    unreviewed_flagged = []
    for e in done:
        if e.verdict != "Consistent" and e.review_status == "not_reviewed":
            try:
                rec_str = (e.received_at or "").replace("Z", "+00:00")
                rec_dt = datetime.fromisoformat(rec_str)
                if rec_dt < three_days_ago:
                    unreviewed_flagged.append(e)
            except Exception:
                pass
    # 3. Score < 50 and no assignee
    unassigned_low_score = [
        e for e in done
        if e.score is not None and e.score < 50 and e.assignee_id is None
    ]

    attention_items = []
    seen_ids = set()
    for e in failed:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            row = _row(e, cases.get(e.case_id))
            row["attention_reason"] = "failed"
            row["attention_label"] = "Analysis failed"
            attention_items.append(row)

    for e in unreviewed_flagged:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            row = _row(e, cases.get(e.case_id))
            row["attention_reason"] = "unreviewed_3d"
            row["attention_label"] = "Flagged & unreviewed > 3 days"
            attention_items.append(row)

    for e in unassigned_low_score:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            row = _row(e, cases.get(e.case_id))
            row["attention_reason"] = "unassigned_low_score"
            row["attention_label"] = "Score < 50 with no assignee"
            attention_items.append(row)

    needs_attention = {
        "total_count": len(attention_items),
        "failed_count": len(failed),
        "unreviewed_3d_count": len(unreviewed_flagged),
        "unassigned_low_score_count": len(unassigned_low_score),
        "items": attention_items[:12]
    }

    # Per-case summary (file count and counts per verdict)
    case_summaries = []
    for c_id, c in cases.items():
        c_ev = list(c.evidence)
        c_done = [e for e in c_ev if e.status == "done" and e.score is not None]
        case_summaries.append({
            "id": c.id,
            "reference": c.reference,
            "title": c.title,
            "investigator": c.investigator,
            "created_at": c.created_at,
            "file_count": len(c_ev),
            "verdicts": {
                v: sum(1 for e in c_done if e.verdict == v)
                for v in ("Likely manipulated", "Needs review", "Consistent")
            },
            "avg_score": round(sum(e.score for e in c_done) / len(c_done)) if c_done else None,
        })
    case_summaries.sort(key=lambda cs: (cs["verdicts"]["Likely manipulated"], cs["verdicts"]["Needs review"]), reverse=True)

    return {
        "cases": len(cases), "files": len(ev),
        "flagged": sum(1 for e in done if e.verdict != "Consistent"),
        "awaiting_review": status["not_reviewed"],
        "average_score": round(sum(e.score for e in done) / len(done)) if done else None,
        "verdicts": {v: sum(1 for e in done if e.verdict == v)
                     for v in ("Likely manipulated", "Needs review", "Consistent")},
        "score_distribution": hist,
        "score_bands": score_bands,
        "score_distribution_bins": [
            {
                "bin": f"{i*10}-{i*10+9 if i < 9 else 100}",
                "count": hist[i],
                "band": "0_49" if i < 5 else "50_79" if i < 8 else "80_100"
            } for i in range(10)
        ],
        "verdicts_by_media_type": verdicts_by_media_type,
        "top_findings": top_findings,
        "custody_health": custody_health,
        "live_queue": _live_queue_state(db),
        "needs_attention": needs_attention,
        "case_summaries": case_summaries,
        "review_status": status,
        "highest_risk": [_row(e, cases.get(e.case_id)) for e in risk],
        "assigned_to_me": [_row(e, cases.get(e.case_id)) for e in ev if e.assignee_id == user.id
                           and e.review_status == "not_reviewed"][:8],
        "recent_activity": [{"at": a.at, "actor": a.actor, "summary": a.summary}
                            for a in db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(8)],
    }


@router.post("/custody/verify-all")
def verify_all_custody(request: Request, db: Session = Depends(get_db),
                       user: User = Depends(require_role("investigator"))):
    """Re-verify all custody chains and check files on disk."""
    ev_list = db.query(Evidence).all()
    intact = 0
    broken = 0
    broken_ids = []
    actor = activity.actor_name(user)
    at_now = now_iso()

    for ev in ev_list:
        chain_res = custody.verify_chain(ev.custody)
        path = config.UPLOAD_DIR / ev.stored_name
        file_ok = True
        if path.exists():
            file_ok = custody.sha256_file(path) == ev.sha256
        ok = chain_res["ok"] and file_ok
        if ok:
            intact += 1
        else:
            broken += 1
            broken_ids.append(ev.id)
        custody.add_event(
            db, ev,
            "Chain verified" if ok else "Custody check FAILED",
            actor,
            "Custody chain re-verified and intact" if ok else (chain_res["message"] if not chain_res["ok"] else "File mismatch"),
            file_hash=ev.sha256
        )
    db.commit()

    summary_text = f"Re-verified all {len(ev_list)} chains: {intact} intact, {broken} broken"
    activity.log(
        db, actor, "custody_verify_all",
        summary_text,
        None, None,
        client_ip(request)
    )

    return {
        "total": len(ev_list),
        "chains_intact": intact,
        "chains_broken": broken,
        "broken_evidence_ids": broken_ids,
        "last_checked_at": at_now,
        "status": "broken" if broken > 0 else "healthy",
        "message": summary_text
    }


@router.get("/search")
def search(q: str = "", media_type: str = "", verdict: str = "", review_status: str = "", case_id: Optional[int] = None,
           category: str = "", check: str = "", assignee_id: Optional[int] = None,
           min_score: Optional[int] = None, max_score: Optional[int] = None,
           date_from: str = "", date_to: str = "", sort: str = "risk",
           db: Session = Depends(get_db), user: User = Depends(current_user)):
    qs = db.query(Evidence).join(Case, Case.id == Evidence.case_id)
    allowed_ids = get_user_case_ids(db, user)
    if allowed_ids is not None:
        qs = qs.filter(Evidence.case_id.in_(allowed_ids))
    if q:
        like = f"%{q}%"
        note_ids = db.query(Note.evidence_id).filter(Note.body.like(like))
        qs = qs.filter(or_(Evidence.filename.like(like), Evidence.sha256.like(like), Case.reference.like(like),
                           Case.title.like(like), Evidence.tags.like(like), Evidence.id.in_(note_ids)))
    for col, val in ((Evidence.media_type, media_type), (Evidence.verdict, verdict),
                     (Evidence.review_status, review_status)):
        if val:
            qs = qs.filter(col.in_(val.split(",")))
    if case_id:
        qs = qs.filter(Evidence.case_id == case_id)
    if assignee_id:
        qs = qs.filter(Evidence.assignee_id == assignee_id)
    if min_score is not None:
        qs = qs.filter(Evidence.score >= min_score)
    if max_score is not None:
        qs = qs.filter(Evidence.score <= max_score)
    if date_from:
        qs = qs.filter(Evidence.received_at >= date_from)
    if date_to:
        qs = qs.filter(Evidence.received_at <= date_to + "T23:59:59.999999Z")
    if category or check:
        fq = db.query(Finding.evidence_id).filter(Finding.severity != "info")
        if category:
            fq = fq.filter(Finding.category == category)
        if check:
            fq = fq.filter(Finding.check == check)
        qs = qs.filter(Evidence.id.in_(fq))
    if sort == "newest":
        qs = qs.order_by(Evidence.received_at.desc())
    else:
        qs = qs.order_by(Evidence.score.is_(None), Evidence.score.asc())
    cases = {c.id: c for c in db.query(Case).all()}
    return [_row(e, cases.get(e.case_id)) for e in qs.limit(500)]


# ---------------------------------------------------------------- similar + compare
import json as _json  # noqa: E402
import re as _re  # noqa: E402

from fastapi import HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

from .. import activity, config, similarity  # noqa: E402
from ..deps import client_ip  # noqa: E402


@router.get("/evidence/{evidence_id}/similar")
def similar(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ev = db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    cases = {c.id: c for c in db.query(Case).all()}
    exact = [dict(_row(e, cases.get(e.case_id)), similarity=100, same_case=e.case_id == ev.case_id)
             for e in db.query(Evidence).filter(Evidence.sha256 == ev.sha256, Evidence.id != ev.id)]
    near = []
    if ev.phash:
        for e in db.query(Evidence).filter(Evidence.phash.isnot(None), Evidence.id != ev.id,
                                           Evidence.sha256 != ev.sha256):
            if similarity.hamming(ev.phash, e.phash) <= similarity.PHASH_LIMIT:
                near.append(dict(_row(e, cases.get(e.case_id)), similarity=similarity.similarity_pct(ev.phash, e.phash),
                                 same_case=e.case_id == ev.case_id,
                                 bits=similarity.hamming(ev.phash, e.phash)))
    near.sort(key=lambda r: -r["similarity"])
    return {"exact": exact, "near": near, "limit_bits": similarity.PHASH_LIMIT}


def _pair(db, a, b):
    ea, eb = db.get(Evidence, a), db.get(Evidence, b)
    if not ea or not eb:
        raise HTTPException(404, "Evidence not found")
    return ea, eb


def _flat(d, prefix=""):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(_flat(v, f"{prefix}{k}."))
        elif not isinstance(v, (list,)):
            out[f"{prefix}{k}"] = str(v)
    return out


@router.get("/compare")
def compare(a: int, b: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ea, eb = _pair(db, a, b)
    da, db_ = ea.get_details(), eb.get_details()
    ma = {**_flat(da.get("exif")), **_flat(da.get("tags")), **_flat(da.get("properties"))}
    mb = {**_flat(db_.get("exif")), **_flat(db_.get("tags")), **_flat(db_.get("properties"))}
    meta = [{"field": k, "a": ma.get(k), "b": mb.get(k)} for k in sorted(set(ma) | set(mb)) if ma.get(k) != mb.get(k)]
    fa = {f.check: f for f in ea.findings}
    fb = {f.check: f for f in eb.findings}
    checks = []
    for k in sorted(set(fa) | set(fb)):
        x, y = fa.get(k), fb.get(k)
        if (x.severity if x else None) != (y.severity if y else None):
            checks.append({"check": k, "a": {"severity": x.severity, "title": x.title} if x else None,
                           "b": {"severity": y.severity, "title": y.title} if y else None})
    res = {"a": _row(ea, None), "b": _row(eb, None), "same_file": ea.sha256 == eb.sha256,
           "score_change": (eb.score - ea.score) if ea.score is not None and eb.score is not None else None,
           "visual_similarity": similarity.similarity_pct(ea.phash, eb.phash) if ea.phash and eb.phash else None,
           "metadata_diffs": meta, "check_diffs": checks, "pixels_changed_pct": None, "diff_boxes": [],
           "diff_image": None}
    if ea.media_type == "image" and eb.media_type == "image":
        out = config.ARTIFACT_DIR / "compare"
        out.mkdir(exist_ok=True)
        png = out / f"{a}_{b}.png"
        r = similarity.diff_map(config.UPLOAD_DIR / ea.stored_name, config.UPLOAD_DIR / eb.stored_name, png)
        if r:
            res.update(pixels_changed_pct=r["pixels_changed_pct"], diff_boxes=r["boxes"],
                       diff_image=f"/api/compare/image?a={a}&b={b}")
    activity.log(db, activity.actor_name(user), "compare", f"Compared evidence {ea.filename} vs {eb.filename}",
                 ea.case_id, ea.id, client_ip(request))
    return res


@router.get("/compare/image")
def compare_image(a: int, b: int, user: User = Depends(current_user)):
    p = config.ARTIFACT_DIR / "compare" / f"{a}_{b}.png"
    if not p.is_file():
        raise HTTPException(404, "Run the comparison first")
    return FileResponse(p)


@router.get("/custody/status")
def custody_status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    allowed_ids = get_user_case_ids(db, user)
    if allowed_ids is None:
        ev_list = db.query(Evidence).all()
        cases = {c.id: c for c in db.query(Case).all()}
    else:
        ev_list = [e for e in db.query(Evidence).all() if e.case_id in allowed_ids]
        cases = {c.id: c for c in db.query(Case).filter(Case.id.in_(allowed_ids)).all()}

    items = []
    intact_count = 0
    broken_count = 0

    for ev in ev_list:
        chain_res = custody.verify_chain(ev.custody)
        path = config.UPLOAD_DIR / ev.stored_name
        file_ok = True
        if path.exists():
            file_ok = (custody.sha256_file(path) == ev.sha256)

        ok = chain_res["ok"] and file_ok
        if ok:
            intact_count += 1
        else:
            broken_count += 1

        case_ref = cases[ev.case_id].reference if ev.case_id in cases else ""
        case_title = cases[ev.case_id].title if ev.case_id in cases else ""

        items.append({
            "id": ev.id,
            "filename": ev.filename,
            "media_type": ev.media_type,
            "case_id": ev.case_id,
            "case_reference": case_ref,
            "case_title": case_title,
            "sha256": ev.sha256,
            "score": ev.score,
            "verdict": ev.verdict,
            "events_count": len(ev.custody),
            "chain_intact": ok,
            "hash_matches_disk": file_ok,
            "last_event": ev.custody[-1].action if ev.custody else "None",
            "last_event_by": ev.custody[-1].actor if ev.custody else "System",
            "last_event_at": ev.custody[-1].at if ev.custody else ev.received_at,
            "error": None if ok else (chain_res.get("message") or "File hash mismatch on disk")
        })

    items.sort(key=lambda x: (x["chain_intact"], x["id"]))  # broken first
    return {
        "total": len(items),
        "intact": intact_count,
        "broken": broken_count,
        "items": items
    }


@router.get("/queue/jobs")
def queue_jobs(db: Session = Depends(get_db), user: User = Depends(current_user)):
    allowed_ids = get_user_case_ids(db, user)
    if allowed_ids is None:
        ev_list = db.query(Evidence).all()
        cases = {c.id: c for c in db.query(Case).all()}
    else:
        ev_list = [e for e in db.query(Evidence).all() if e.case_id in allowed_ids]
        cases = {c.id: c for c in db.query(Case).filter(Case.id.in_(allowed_ids)).all()}

    jobs = []
    for ev in ev_list:
        case_ref = cases[ev.case_id].reference if ev.case_id in cases else ""
        jobs.append({
            "id": ev.id,
            "filename": ev.filename,
            "media_type": ev.media_type,
            "size": ev.size,
            "case_id": ev.case_id,
            "case_reference": case_ref,
            "status": ev.status,
            "stage": ev.stage or ("Completed" if ev.status == "done" else "Queued"),
            "progress": ev.progress or (100 if ev.status == "done" else 0),
            "score": ev.score,
            "verdict": ev.verdict,
            "error": ev.error,
            "received_at": ev.received_at,
            "uploaded_by": ev.uploaded_by,
            "queue_position": pipeline.queue_position(ev.id) if ev.status == "queued" else None,
        })
    return jobs
