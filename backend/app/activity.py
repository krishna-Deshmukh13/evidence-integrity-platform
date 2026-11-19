"""Audit log: who did what, across the whole system."""
from datetime import datetime, timedelta, timezone

from .models import ActivityLog, now_iso


def log(db, actor: str, action: str, summary: str = "", case_id=None, evidence_id=None, ip: str = ""):
    db.add(ActivityLog(actor=actor, action=action, summary=summary, case_id=case_id,
                       evidence_id=evidence_id, ip=ip, at=now_iso()))
    db.commit()


def log_view(db, user, ev, ip: str = ""):
    """One 'viewed' entry per person per file per 10 minutes (polling must not flood the log)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    exists = (db.query(ActivityLog).filter(ActivityLog.action == "view", ActivityLog.evidence_id == ev.id,
                                           ActivityLog.actor == actor_name(user), ActivityLog.at >= cutoff).first())
    if not exists:
        log(db, actor_name(user), "view", f"Viewed evidence {ev.filename}", ev.case_id, ev.id, ip)


def actor_name(user) -> str:
    return f"{user.full_name} ({user.username})"
