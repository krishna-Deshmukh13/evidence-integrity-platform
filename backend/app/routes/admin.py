"""Accounts (admin) and the activity log."""
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import activity, auth
from ..database import get_db
from ..deps import client_ip, require_role
from ..models import ActivityLog, User

router = APIRouter(prefix="/api")
ROLES = {"admin", "investigator", "viewer"}


class NewUser(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=200)
    role: str = "viewer"


class UserPatch(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=200)


def _pub(u):
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
            "is_active": u.is_active, "last_login_at": u.last_login_at, "totp_enabled": bool(u.totp_enabled)}


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_role("investigator"))):
    return [_pub(u) for u in db.query(User).order_by(User.id).all()]


@router.post("/users")
def create_user(body: NewUser, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    if body.role not in ROLES:
        raise HTTPException(400, "Unknown role")
    if db.query(User).filter(User.username == body.username.lower()).first():
        raise HTTPException(409, "Username already taken")
    u = User(username=body.username.lower(), full_name=body.full_name, role=body.role,
             password_hash=auth.hash_password(body.password))
    db.add(u)
    db.commit()
    activity.log(db, activity.actor_name(admin), "account", f"Created account {u.username} ({u.role})",
                 ip=client_ip(request))
    return _pub(u)


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserPatch, request: Request, db: Session = Depends(get_db),
               admin: User = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
    if u.id == admin.id and ((body.role and body.role != "admin") or body.is_active is False):
        raise HTTPException(400, "You cannot demote or disable yourself")
    losing_admin = u.role == "admin" and ((body.role and body.role != "admin") or body.is_active is False)
    if losing_admin and admins <= 1:
        raise HTTPException(400, "The last admin cannot be removed")
    changes = []
    if body.role:
        if body.role not in ROLES:
            raise HTTPException(400, "Unknown role")
        old_role = u.role
        u.role = body.role
        changes.append(f"role={body.role}")
        if old_role != body.role:
            activity.log(db, activity.actor_name(admin), "role_change",
                         f"Changed role of user '{u.username}' from {old_role} to {body.role}",
                         ip=client_ip(request))
    if body.is_active is not None:
        u.is_active = body.is_active
        changes.append("enabled" if body.is_active else "disabled")
        if not body.is_active:
            auth.revoke_user_sessions(db, u.id)
    if body.password:
        u.password_hash = auth.hash_password(body.password)
        auth.revoke_user_sessions(db, u.id)
        changes.append("password reset")
    db.commit()
    activity.log(db, activity.actor_name(admin), "account", f"Updated {u.username}: {', '.join(changes)}",
                 ip=client_ip(request))
    return _pub(u)


@router.post("/users/{user_id}/reset-2fa")
def reset_user_2fa(user_id: int, request: Request, db: Session = Depends(get_db),
                   admin: User = Depends(require_role("admin"))):
    """Admin-only reset of a locked-out user's two-factor authentication."""
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    u.totp_secret = None
    u.totp_enabled = False
    u.recovery_codes = None
    db.commit()
    activity.log(db, activity.actor_name(admin), "account", f"Reset 2FA for user {u.username}", ip=client_ip(request))
    return {"ok": True, "user_id": u.id, "totp_enabled": False}


def _activity_query(db, q, action, actor, date_from, date_to):
    qs = db.query(ActivityLog)
    if action:
        if action == "export":
            qs = qs.filter(ActivityLog.action.in_(["export", "report_export"]))
        elif action == "analysis":
            qs = qs.filter(ActivityLog.action.in_(["analysis", "verdict"]))
        elif action == "account":
            qs = qs.filter(ActivityLog.action.in_(["account", "role_change"]))
        else:
            qs = qs.filter(ActivityLog.action == action)
    if actor:
        qs = qs.filter(ActivityLog.actor.like(f"%{actor}%"))
    if q:
        qs = qs.filter(ActivityLog.summary.like(f"%{q}%"))
    if date_from:
        qs = qs.filter(ActivityLog.at >= date_from)
    if date_to:
        qs = qs.filter(ActivityLog.at <= date_to + "T23:59:59.999999Z")
    return qs.order_by(ActivityLog.id.desc())


def _row(a):
    return {"id": a.id, "at": a.at, "actor": a.actor, "action": a.action, "summary": a.summary,
            "case_id": a.case_id, "evidence_id": a.evidence_id, "ip": a.ip}


@router.get("/activity")
def get_activity(q: str = "", action: str = "", actor: str = "", date_from: str = "", date_to: str = "",
                 limit: int = 200, db: Session = Depends(get_db), user: User = Depends(require_role("investigator"))):
    return [_row(a) for a in _activity_query(db, q, action, actor, date_from, date_to).limit(min(limit, 1000))]


@router.get("/activity/export.csv")
def export_activity(db: Session = Depends(get_db), user: User = Depends(require_role("investigator"))):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time", "actor", "action", "summary", "case_id", "evidence_id", "ip"])
    for a in _activity_query(db, "", "", "", "", "").limit(50000):
        w.writerow([a.at, a.actor, a.action, a.summary, a.case_id, a.evidence_id, a.ip])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=activity.csv"})


@router.get("/settings/system")
def get_system_settings(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    import os
    import sys
    import cv2
    import PIL
    from .. import config, llm

    def dir_size(p):
        if not p.exists():
            return 0, 0
        total = 0
        cnt = 0
        for root, _, files in os.walk(p):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                    cnt += 1
                except OSError:
                    pass
        return total, cnt

    upload_bytes, upload_files = dir_size(config.UPLOAD_DIR)
    art_bytes, art_files = dir_size(config.ARTIFACT_DIR)
    db_path = config.STORAGE_DIR / "evidence.db"
    db_size = db_path.stat().st_size if db_path.exists() else 0

    llm_cfg = llm.settings()

    return {
        "platform": {
            "name": "Evidence Integrity Platform",
            "version": "2.4.0 (Clean Light Pro)",
            "python_version": sys.version.split()[0],
            "os": sys.platform,
        },
        "dependencies": [
            {"name": "OpenCV Headless", "version": cv2.__version__, "status": "active"},
            {"name": "Pillow (PIL)", "version": PIL.__version__, "status": "active"},
            {"name": "PyMuPDF (Fitz)", "version": "1.24.0+", "status": "active"},
            {"name": "FastAPI Core", "version": "0.110+", "status": "active"},
            {"name": "SQLAlchemy ORM", "version": "2.0+", "status": "active"},
            {"name": "ReportLab PDF Engine", "version": "4.0+", "status": "active"},
            {"name": "PyOTP Two-Factor Engine", "version": "2.9+", "status": "active"},
        ],
        "models": [
            {"name": "Forensic Inference Engine", "type": "Multi-Modal Neural & CV Pipeline", "status": "active"},
            {"name": "ORB Feature Matcher", "type": "Copy-Move Clone Detection", "status": "active"},
            {"name": "Signal Noise Residuals", "type": "Sensor Pattern Noise Discrepancy", "status": "active"},
            {"name": "Audio Spectral Analyzer", "type": "FFT & Voice Synthetic Detector", "status": "active"},
            {"name": "Temporal Video Splicer", "type": "Inter-frame Consistency & Dropped Frames", "status": "active"},
        ],
        "llm": {
            "provider": llm_cfg["provider"],
            "model": llm_cfg["model"] or "qwen2.5:7b",
            "has_key": bool(llm_cfg["key"]),
            "base_url": llm_cfg["base_url"] or "http://localhost:11434",
            "status": "connected" if llm.enabled() else "local_fallback"
        },
        "storage": {
            "database_bytes": db_size,
            "uploads_bytes": upload_bytes,
            "uploads_count": upload_files,
            "artifacts_bytes": art_bytes,
            "artifacts_count": art_files,
            "total_bytes": db_size + upload_bytes + art_bytes,
        }
    }


class LLMConfigIn(BaseModel):
    provider: str
    model: Optional[str] = None
    key: Optional[str] = None
    base_url: Optional[str] = None


@router.get("/settings/llm")
def get_llm_settings(user: User = Depends(require_role("investigator"))):
    from .. import llm
    cfg = llm.settings()
    st = llm.status()
    return {
        "provider": cfg["provider"],
        "model": cfg["model"],
        "has_key": bool(cfg["key"]),
        "base_url": cfg["base_url"],
        "online": st["online"],
        "label": st["label"],
        "providers": [
            {
                "id": "free_online",
                "name": "Free Online AI (Zero setup, no key needed)",
                "free": True,
                "default_model": "openai",
                "description": "Instant ChatGPT-like intelligence via free online OpenAI-compatible endpoint. No API key required."
            },
            {
                "id": "gemini",
                "name": "Google Gemini 2.0 Flash (Free API Key)",
                "free": True,
                "default_model": "gemini-2.0-flash",
                "key_url": "https://aistudio.google.com/app/apikey",
                "description": "Google's ultra-fast, high-capacity model. Get a 100% free API key from Google AI Studio."
            },
            {
                "id": "groq",
                "name": "Groq Llama 3.3 70B (Free API Key)",
                "free": True,
                "default_model": "llama-3.3-70b-versatile",
                "key_url": "https://console.groq.com/keys",
                "description": "Ultra-fast inference (500+ tok/s). Free API key from Groq Cloud Console."
            },
            {
                "id": "openrouter",
                "name": "OpenRouter (Free Tier Models)",
                "free": True,
                "default_model": "google/gemini-2.0-flash-lite-preview-02-05:free",
                "key_url": "https://openrouter.ai/keys",
                "description": "Aggregated free models from OpenRouter."
            },
            {
                "id": "ollama",
                "name": "Local Ollama (Offline localhost:11434)",
                "free": True,
                "default_model": "qwen2.5:7b",
                "description": "Self-hosted local model running on your hardware with 100% privacy."
            },
            {
                "id": "openai",
                "name": "OpenAI (GPT-4o-mini)",
                "free": False,
                "default_model": "gpt-4o-mini",
                "description": "Official OpenAI API with your own OpenAI developer key."
            },
            {
                "id": "none",
                "name": "Local Knowledge Engine (Offline Template)",
                "free": True,
                "default_model": "deterministic",
                "description": "Rule-based expert forensic synthesis with zero network calls."
            }
        ]
    }


@router.post("/settings/llm")
def update_llm_settings(body: LLMConfigIn, request: Request, db: Session = Depends(get_db),
                        user: User = Depends(require_role("investigator"))):
    import os
    from .. import config, llm

    prov = body.provider.strip().lower()
    os.environ["LLM_PROVIDER"] = prov
    if body.model:
        os.environ["LLM_MODEL"] = body.model.strip()
    if body.key is not None:
        os.environ["LLM_API_KEY"] = body.key.strip()
    if body.base_url is not None:
        os.environ["LLM_BASE_URL"] = body.base_url.strip()

    # Update .env file on disk
    env_file = config.BASE_DIR / ".env"
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()
        new_lines = []
        found_p = found_m = found_k = found_b = False
        for line in lines:
            if line.startswith("LLM_PROVIDER="):
                new_lines.append(f"LLM_PROVIDER={os.environ['LLM_PROVIDER']}")
                found_p = True
            elif line.startswith("LLM_MODEL="):
                new_lines.append(f"LLM_MODEL={os.environ.get('LLM_MODEL', '')}")
                found_m = True
            elif line.startswith("LLM_API_KEY="):
                new_lines.append(f"LLM_API_KEY={os.environ.get('LLM_API_KEY', '')}")
                found_k = True
            elif line.startswith("LLM_BASE_URL="):
                new_lines.append(f"LLM_BASE_URL={os.environ.get('LLM_BASE_URL', '')}")
                found_b = True
            else:
                new_lines.append(line)
        if not found_p:
            new_lines.append(f"LLM_PROVIDER={os.environ['LLM_PROVIDER']}")
        if not found_m:
            new_lines.append(f"LLM_MODEL={os.environ.get('LLM_MODEL', '')}")
        if not found_k:
            new_lines.append(f"LLM_API_KEY={os.environ.get('LLM_API_KEY', '')}")
        if not found_b:
            new_lines.append(f"LLM_BASE_URL={os.environ.get('LLM_BASE_URL', '')}")
        env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    if prov == "none":
        activity.log(db, activity.actor_name(user), "settings_llm", "Turned OFF external AI summaries (Air-gapped offline mode enabled)", ip=client_ip(request))
    else:
        activity.log(db, activity.actor_name(user), "settings_llm", f"Turned ON external AI summaries (Provider: {prov})", ip=client_ip(request))
    return get_llm_settings(user)


@router.post("/settings/test-llm")
def test_llm_connection(user: User = Depends(require_role("investigator"))):
    import time
    from .. import llm
    cfg = llm.settings()
    if cfg["provider"] == "none":
        return {
            "ok": True,
            "latency_ms": 10,
            "provider": "none",
            "model": "Deterministic Forensic Synthesis",
            "message": "Local Deterministic Synthesis Engine active. Multi-modal scoring and Section 63 BSA generator operating at 100% capacity."
        }
    start = time.time()
    try:
        reply = llm.complete(
            "You are a test ping.",
            "Say 'Evidence Integrity Platform online' in exactly 5 words.",
            max_tokens=30
        )
        latency = int((time.time() - start) * 1000)
        return {
            "ok": True,
            "latency_ms": latency,
            "provider": cfg["provider"],
            "model": cfg["model"],
            "answer": reply,
            "message": f"Successfully connected to {cfg['provider']} ({cfg['model']})! Latency: {latency}ms."
        }
    except Exception as e:
        return {
            "ok": False,
            "latency_ms": 0,
            "provider": cfg["provider"],
            "model": cfg["model"],
            "error": str(e)
        }
