"""FastAPI app: auth, cases, evidence, uploads, files."""
import json
import os
import math
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import activity, auth, config, custody, pipeline, scoring
from .database import SessionLocal, get_db, init_db
from .deps import (
    client_ip, current_user, get_user_case_ids, has_case_access,
    require_role, verify_case_access, verify_evidence_access
)
from .models import Case, CaseMember, Evidence, User, now_iso

@asynccontextmanager
async def lifespan(_app):
    init_db()
    db = SessionLocal()  # anything left half-done by a restart goes back on the queue
    try:
        for ev in db.query(Evidence).filter(Evidence.status.in_(["queued", "analyzing"])).all():
            pipeline.enqueue(ev.id)
    finally:
        db.close()
    yield


app = FastAPI(title="Evidence Integrity Platform", version="1.0-stage1", lifespan=lifespan)


# ---------- helpers ----------
def compute_ml_confidence(findings):
    model_path = config.STORAGE_DIR / "models" / "fusion_model.json"
    if not model_path.exists():
        return None
    try:
        data = json.loads(model_path.read_text(encoding="utf-8"))
        intercept = float(data.get("intercept", 0.0))
        coefs = data.get("coefficients", {})
        z = intercept
        for f in findings:
            chk = getattr(f, "check", None) or (f.get("check") if isinstance(f, dict) else "")
            if chk in coefs:
                z += float(coefs[chk])
        prob = 1.0 / (1.0 + math.exp(-z))
        pct = int(round(prob * 100))
        return {
            "confidence_percent": pct,
            "manipulation_probability": round(float(prob), 4),
            "model_type": data.get("model_type", "Logistic Regression Fusion"),
            "is_demonstration": data.get("is_demonstration", True),
            "disclaimer": data.get("disclaimer", "ML-assisted confidence indicator. Model is only as good as its training data and does not replace deterministic forensic scoring.")
        }
    except Exception:
        return None


def serialize(ev: Evidence, full=False, user=None):
    d = {
        "id": ev.id, "case_id": ev.case_id, "filename": ev.filename, "media_type": ev.media_type,
        "size": ev.size, "sha256": ev.sha256, "status": ev.status, "stage": ev.stage,
        "progress": ev.progress, "error": ev.error, "score": ev.score, "verdict": ev.verdict,
        "breakdown": ev.get_breakdown(), "review_status": ev.review_status, "assignee_id": ev.assignee_id,
        "tags": ev.get_tags(), "received_at": ev.received_at, "uploaded_by": ev.uploaded_by,
        "flags": sum(1 for f in ev.findings if f.severity != "info"),
        "queue_position": pipeline.queue_position(ev.id) if ev.status == "queued" else None,
        "report_busy": ev.id in pipeline.report_busy,
    }
    if full:
        current_score = ev.score if ev.score is not None else 100
        current_verdict = ev.verdict or scoring.verdict_for(current_score)
        raw_findings = [
            {"category": f.category, "severity": f.severity,
             "penalty": f.penalty if f.penalty is not None else scoring.DEFAULT_PENALTY.get(f.severity, 0),
             "id": f.id}
            for f in ev.findings
        ]
        findings_list = []
        for f in ev.findings:
            rem = [x for x in raw_findings if x["id"] != f.id]
            new_s, _, new_v = scoring.compute(rem)
            pts_gained = max(0, new_s - current_score)
            findings_list.append({
                "id": f.id, "category": f.category, "check": f.check, "severity": f.severity,
                "penalty": f.penalty, "title": f.title, "detail": f.detail,
                "location": json.loads(f.location) if f.location else None,
                "feedback": getattr(f, "feedback", None),
                "feedback_by": getattr(f, "feedback_by", None),
                "feedback_at": getattr(f, "feedback_at", None),
                "feedback_note": getattr(f, "feedback_note", "") or "",
                "score_impact": {
                    "points_gained": pts_gained,
                    "new_score": new_s,
                    "current_score": current_score,
                    "current_verdict": current_verdict,
                    "new_verdict": new_v,
                    "band_changed": new_v != current_verdict,
                }
            })

        d.update({
            "details": ev.get_details(), "report": ev.report, "report_model": ev.report_model,
            "findings": findings_list,
            "ml_confidence": compute_ml_confidence(ev.findings),
            "custody": [{"seq": c.seq, "action": c.action, "actor": c.actor, "at": c.at, "note": c.note,
                         "file_hash": c.file_hash, "event_hash": c.event_hash, "prev_hash": c.prev_hash}
                        for c in ev.custody],
            "notes": [{"id": n.id, "author": n.author, "body": n.body, "created_at": n.created_at}
                      for n in ev.notes],
            "artifacts": sorted(p.name for p in (config.ARTIFACT_DIR / str(ev.id)).glob("*")
                                if p.is_file()) if (config.ARTIFACT_DIR / str(ev.id)).exists() else [],
        })
    return d


def get_evidence_or_404(db, evidence_id) -> Evidence:
    ev = db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    return ev


def media_type_for(filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for mt, exts in config.MEDIA_TYPES.items():
        if ext in exts:
            return mt, ext
    return None, ext


# ---------- auth ----------
class Creds(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)
    code: Optional[str] = None


class SetupBody(Creds):
    full_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=200)


def _set_cookies(resp: Response, user: User, db):
    refresh = auth.issue_refresh_token(db, user)
    _put_cookies(resp, auth.make_access_token(user), refresh)


def _put_cookies(resp, access, refresh):
    kw = dict(httponly=True, samesite="strict", secure=config.COOKIE_SECURE)
    resp.set_cookie("access_token", access, max_age=config.ACCESS_TOKEN_MINUTES * 60, path="/", **kw)
    resp.set_cookie("refresh_token", refresh, max_age=config.REFRESH_TOKEN_DAYS * 86400,
                    path="/api/auth", **kw)


def public_user(u: User):
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role,
        "totp_enabled": bool(u.totp_enabled),
        "totp_required": u.role in ("admin", "investigator"),
    }


@app.get("/api/auth/status")
def auth_status(db: Session = Depends(get_db)):
    return {"needs_setup": db.query(User).count() == 0}


@app.post("/api/auth/setup")
def auth_setup(body: SetupBody, response: Response, request: Request, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(409, "Setup already done")
    u = User(username=body.username.strip().lower(), full_name=body.full_name.strip(),
             password_hash=auth.hash_password(body.password), role="admin")
    db.add(u)
    db.commit()
    _set_cookies(response, u, db)
    activity.log(db, activity.actor_name(u), "account", "First admin account created", ip=client_ip(request))
    return public_user(u)


@app.post("/api/auth/login")
def login(body: Creds, response: Response, request: Request, db: Session = Depends(get_db)):
    ip, uname = client_ip(request), body.username.strip().lower()
    wait = auth.throttle.blocked(ip, uname)
    if wait:
        raise HTTPException(429, f"Too many attempts. Try again in {wait // 60 + 1} minutes.")
    user = auth.authenticate(db, uname, body.password)
    if not user:
        auth.throttle.fail(ip, uname)
        activity.log(db, uname, "login_failed", "Failed sign-in", ip=ip)
        raise HTTPException(401, "Wrong username or password")

    # Check if TOTP 2FA is enabled for this user
    if user.totp_enabled and user.totp_secret:
        if not body.code:
            # Prompt client for 2FA code
            return {"requires_2fa": True, "username": user.username}

        # Verify code: try TOTP first
        import hashlib
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        code_clean = body.code.strip()
        code_ok = totp.verify(code_clean, valid_window=1)
        used_recovery = False

        if not code_ok and user.recovery_codes:
            # Check recovery codes
            h_code = hashlib.sha256(code_clean.lower().encode("utf-8")).hexdigest()
            try:
                rec_list = json.loads(user.recovery_codes)
                if h_code in rec_list:
                    rec_list.remove(h_code)
                    user.recovery_codes = json.dumps(rec_list)
                    code_ok = True
                    used_recovery = True
            except Exception:
                pass

        if not code_ok:
            auth.throttle.fail(ip, uname)
            activity.log(db, uname, "login_failed", "Failed 2FA code verification", ip=ip)
            raise HTTPException(401, "Invalid authentication code or recovery code")

        if used_recovery:
            activity.log(db, activity.actor_name(user), "login", "Signed in using 2FA recovery code", ip=ip)

    auth.throttle.success(ip, uname)
    user.last_login_at = now_iso()
    db.commit()
    _set_cookies(response, user, db)
    activity.log(db, activity.actor_name(user), "login", "Signed in", ip=ip)
    return public_user(user)


@app.post("/api/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token", "")
    user, new_raw = auth.rotate_refresh_token(db, raw) if raw else (None, None)
    if not user:
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/api/auth")
        raise HTTPException(401, "Session expired")
    _put_cookies(response, auth.make_access_token(user), new_raw)
    return public_user(user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token", "")
    if raw:
        auth.revoke_token(db, raw)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


# ---------- cases ----------
class CaseIn(BaseModel):
    reference: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    investigator: str = ""
    incident_location: str = ""
    incident_lat: Optional[float] = None
    incident_lon: Optional[float] = None


class CaseMemberIn(BaseModel):
    user_id: int
    role: str = "member"  # member | lead


def serialize_case(c: Case):
    done = [e for e in c.evidence if e.status == "done"]
    return {
        "id": c.id,
        "reference": c.reference,
        "title": c.title,
        "investigator": c.investigator,
        "incident_location": getattr(c, "incident_location", "") or "",
        "incident_lat": getattr(c, "incident_lat", None),
        "incident_lon": getattr(c, "incident_lon", None),
        "created_at": c.created_at,
        "files": len(c.evidence),
        "likely_manipulated": sum(1 for e in done if e.verdict == "Likely manipulated"),
        "needs_review": sum(1 for e in done if e.verdict == "Needs review"),
        "consistent": sum(1 for e in done if e.verdict == "Consistent")
    }


@app.get("/api/cases")
def list_cases(db: Session = Depends(get_db), user: User = Depends(current_user)):
    allowed_ids = get_user_case_ids(db, user)
    q = db.query(Case).order_by(Case.id.asc())
    if allowed_ids is not None:
        q = q.filter(Case.id.in_(allowed_ids))
    return [serialize_case(c) for c in q.all()]


@app.post("/api/cases")
def create_case(body: CaseIn, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role("investigator"))):
    if db.query(Case).filter(Case.reference == body.reference).first():
        raise HTTPException(409, "A case with this reference already exists")
    c = Case(
        reference=body.reference,
        title=body.title,
        investigator=body.investigator or user.full_name,
        incident_location=body.incident_location or "",
        incident_lat=body.incident_lat,
        incident_lon=body.incident_lon
    )
    db.add(c)
    db.flush()
    # Creator is automatically assigned as lead member
    m = CaseMember(case_id=c.id, user_id=user.id, role="lead")
    db.add(m)
    db.commit()
    activity.log(db, activity.actor_name(user), "case_create", f"Created case {c.reference}", c.id,
                 ip=client_ip(request))
    return serialize_case(c)


@app.get("/api/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = verify_case_access(db, user, case_id)
    d = serialize_case(c)
    files = sorted(c.evidence, key=lambda e: (e.score is None, e.score if e.score is not None else 0))
    d["evidence"] = [serialize(e) for e in files]  # lowest score (riskiest) first
    d["members"] = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "username": m.user.username if m.user else "",
            "full_name": m.user.full_name if m.user else "",
            "user_role": m.user.role if m.user else "",
            "case_role": m.role,
            "added_at": m.added_at,
        }
        for m in c.members
    ]
    return d


@app.get("/api/cases/{case_id}/members")
def get_case_members(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = verify_case_access(db, user, case_id)
    return [
        {
            "id": m.id,
            "case_id": m.case_id,
            "user_id": m.user_id,
            "username": m.user.username if m.user else "",
            "full_name": m.user.full_name if m.user else "",
            "user_role": m.user.role if m.user else "",
            "case_role": m.role,
            "added_at": m.added_at,
        }
        for m in c.members
    ]


@app.post("/api/cases/{case_id}/members")
def add_case_member(case_id: int, body: CaseMemberIn, request: Request,
                    db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    target_user = db.get(User, body.user_id)
    if not target_user:
        raise HTTPException(404, "Target user not found")
    existing = db.query(CaseMember).filter(CaseMember.case_id == case_id, CaseMember.user_id == body.user_id).first()
    if existing:
        raise HTTPException(409, "User is already a member of this case")
    role = body.role if body.role in ("lead", "member") else "member"
    m = CaseMember(case_id=case_id, user_id=body.user_id, role=role)
    db.add(m)
    db.commit()
    activity.log(db, activity.actor_name(user), "case_member_add",
                 f"Added {target_user.full_name} ({target_user.username}) as {role} to case {c.reference}",
                 case_id, ip=client_ip(request))
    return {
        "id": m.id, "case_id": m.case_id, "user_id": m.user_id,
        "username": target_user.username, "full_name": target_user.full_name,
        "user_role": target_user.role, "case_role": m.role, "added_at": m.added_at
    }


@app.delete("/api/cases/{case_id}/members/{user_id}")
def remove_case_member(case_id: int, user_id: int, request: Request,
                       db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    m = db.query(CaseMember).filter(CaseMember.case_id == case_id, CaseMember.user_id == user_id).first()
    if not m:
        raise HTTPException(404, "Case member not found")
    target_user = db.get(User, user_id)
    name = target_user.full_name if target_user else f"User {user_id}"
    db.delete(m)
    db.commit()
    activity.log(db, activity.actor_name(user), "case_member_remove",
                 f"Removed {name} from case {c.reference}", case_id, ip=client_ip(request))
    return {"ok": True}


@app.delete("/api/cases/{case_id}")
def delete_case(case_id: int, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role("admin"))):
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    for e in c.evidence:
        _remove_files(e)
    ref = c.reference
    db.delete(c)
    db.commit()
    activity.log(db, activity.actor_name(user), "case_delete", f"Deleted case {ref}", case_id,
                 ip=client_ip(request))
    return {"ok": True}


def _remove_files(ev: Evidence):
    import shutil
    (config.UPLOAD_DIR / ev.stored_name).unlink(missing_ok=True)
    shutil.rmtree(config.ARTIFACT_DIR / str(ev.id), ignore_errors=True)


# ---------- evidence ----------
@app.post("/api/cases/{case_id}/evidence")
async def upload_evidence(case_id: int, request: Request, file: UploadFile = File(...),
                          db: Session = Depends(get_db), user: User = Depends(require_role("investigator"))):
    case = verify_case_access(db, user, case_id)
    raw_name = Path(file.filename or "evidence_file").name
    # Strict Filename Sanitization: strip null bytes, directory traversal, control chars
    clean_name = re.sub(r'[\x00-\x1f\x7f/\\]', '', raw_name)
    clean_name = re.sub(r'\.\.+', '.', clean_name).strip('. ')
    if not clean_name:
        clean_name = f"evidence_{secrets.token_hex(4)}.dat"
    stem, ext_raw = os.path.splitext(clean_name)
    ext = ext_raw.lstrip(".").lower()
    name = f"{stem[:100]}.{ext}"

    mt, _ = media_type_for(name)
    allowed_exts = set().union(*config.MEDIA_TYPES.values())
    if not mt or ext not in allowed_exts:
        raise HTTPException(400, f"Unsupported file type: .{ext}. Allowed formats: {', '.join(sorted(allowed_exts))}")
    stored = f"{secrets.token_hex(16)}.{ext}"  # random name: no clashes, no path escape
    dest = config.UPLOAD_DIR / stored
    import hashlib
    h, size = hashlib.sha256(), 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > config.MAX_UPLOAD_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "File is larger than 500 MB")
            h.update(chunk)
            out.write(chunk)
    ev = Evidence(case_id=case.id, filename=name, stored_name=stored, media_type=mt, size=size,
                  sha256=h.hexdigest(), status="queued", stage="Queued", uploaded_by=user.full_name)
    db.add(ev)
    db.flush()
    custody.add_event(db, ev, "Received", activity.actor_name(user), f"Uploaded as {name}, {size:,} bytes")
    db.commit()
    activity.log(db, activity.actor_name(user), "upload", f"Uploaded {name}", case.id, ev.id, client_ip(request))
    pipeline.enqueue(ev.id)
    db.refresh(ev)
    return serialize(ev)


@app.get("/api/evidence/{evidence_id}")
def get_evidence(evidence_id: int, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    ev = verify_evidence_access(db, user, evidence_id)
    activity.log_view(db, user, ev, client_ip(request))
    return serialize(ev, full=True)


@app.post("/api/evidence/{evidence_id}/verify")
def verify(evidence_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ev = verify_evidence_access(db, user, evidence_id)
    result = custody.verify_evidence(ev, config.UPLOAD_DIR)
    custody.add_event(db, ev, "Integrity verified" if result["ok"] else "Integrity check FAILED",
                      activity.actor_name(user), "Chain and file intact" if result["ok"] else result["message"],
                      file_hash=result["current_hash"] or ev.sha256)
    db.commit()
    activity.log(db, activity.actor_name(user), "verify", f"Verified integrity {ev.filename}: "
                 + ("Chain and file intact" if result["ok"] else "FAILED"), ev.case_id, ev.id, client_ip(request))
    return result


@app.post("/api/evidence/{evidence_id}/reanalyze")
def reanalyze(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("investigator"))):
    ev = verify_evidence_access(db, user, evidence_id)
    ev.status, ev.stage, ev.progress = "queued", "Queued", 0
    db.commit()
    pipeline.enqueue(ev.id)
    db.refresh(ev)
    return serialize(ev)


@app.delete("/api/evidence/{evidence_id}")
def delete_evidence(evidence_id: int, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_role("admin"))):
    ev = verify_evidence_access(db, user, evidence_id)
    _remove_files(ev)
    name, case_id = ev.filename, ev.case_id
    db.delete(ev)
    db.commit()
    activity.log(db, activity.actor_name(user), "evidence_delete", f"Deleted {name}", case_id,
                 ip=client_ip(request))
    return {"ok": True}


@app.get("/api/evidence/{evidence_id}/file")
def get_file(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ev = verify_evidence_access(db, user, evidence_id)
    return FileResponse(config.UPLOAD_DIR / ev.stored_name, filename=ev.filename)


@app.get("/api/evidence/{evidence_id}/artifact/{name}")
def get_artifact(evidence_id: int, name: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    verify_evidence_access(db, user, evidence_id)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise HTTPException(400, "Bad name")
    p = config.ARTIFACT_DIR / str(evidence_id) / name
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p)


from .routes import admin, ask, assistant, auth_2fa, case_intel, exports, insights, review  # noqa: E402

app.include_router(admin.router)
app.include_router(assistant.router)
app.include_router(auth_2fa.router)
app.include_router(insights.router)
app.include_router(review.router)
app.include_router(exports.router)
app.include_router(ask.router)
app.include_router(case_intel.router)

# Serve built frontend in container / production if dist exists
from fastapi.staticfiles import StaticFiles

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not _frontend_dist.exists():
    _frontend_dist = Path("/app/frontend/dist")

if _frontend_dist.exists() and (_frontend_dist / "index.html").exists():
    assets_dir = _frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Endpoint not found")
        target_file = _frontend_dist / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(_frontend_dist / "index.html")
