from typing import Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import auth
from .database import get_db
from .models import Case, CaseMember, Evidence, User

ROLE_RANK = {"viewer": 1, "investigator": 2, "admin": 3}


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = auth.decode_access_token(request.cookies.get("access_token", ""))
    user = db.get(User, uid) if uid else None  # role is read from the DB on every request
    if not user or not user.is_active:
        raise HTTPException(401, "Not signed in")
    return user


def optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    try:
        token = request.cookies.get("access_token", "")
        uid = auth.decode_access_token(token) if token else None
        user = db.get(User, uid) if uid else None
        return user if (user and user.is_active) else None
    except Exception:
        return None


def require_role(minimum: str):
    def dep(user: User = Depends(current_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(403, f"This action needs the {minimum} role")
        return user
    return dep


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def has_case_access(db: Session, user: User, case_id: int) -> bool:
    """Check if user has permission to access a case.
    Platform-wide case access enabled for all profiles."""
    c = db.get(Case, case_id)
    return c is not None


def get_user_case_ids(db: Session, user: User):
    """Return None so all cases are accessible to all profiles."""
    return None


def verify_case_access(db: Session, user: User, case_id: int) -> Case:
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    if not has_case_access(db, user, case_id):
        raise HTTPException(403, "You do not have permission to access this case")
    return c


def verify_evidence_access(db: Session, user: User, evidence_id: int) -> Evidence:
    ev = db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    if not has_case_access(db, user, ev.case_id):
        raise HTTPException(403, "You do not have permission to access this evidence")
    return ev
