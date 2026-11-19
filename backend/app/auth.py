"""Passwords (bcrypt), access JWT, rotating refresh tokens, login throttling."""
import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import or_

from . import config
from .models import RefreshToken, User, now_iso

ALGO = "HS256"
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=10)).decode()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(rounds=10)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def authenticate(db, username: str, password: str):
    """Same work and same answer for unknown user and wrong password."""
    term = username.strip().lower()
    user = db.query(User).filter(or_(User.username.ilike(term), User.email.ilike(term))).first()
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user and ok and user.is_active:
        return user
    return None


def make_access_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "exp": exp, "typ": "access"}, config.JWT_SECRET, algorithm=ALGO)


def decode_access_token(token: str):
    try:
        data = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGO])
        return int(data["sub"]) if data.get("typ") == "access" else None
    except Exception:
        return None


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _expiry_iso(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def issue_refresh_token(db, user: User, family_id: str = None) -> str:
    raw = secrets.token_urlsafe(32)  # 256 bits
    db.add(RefreshToken(user_id=user.id, token_hash=_hash_token(raw),
                        family_id=family_id or secrets.token_hex(16),
                        expires_at=_expiry_iso(config.REFRESH_TOKEN_DAYS)))
    db.commit()
    return raw


def rotate_refresh_token(db, raw: str):
    """-> (user, new_raw) or (None, None). A reused old token revokes the whole family."""
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw)).first()
    if not rt:
        return None, None
    if rt.revoked_at or rt.rotated:
        revoke_family(db, rt.family_id)  # someone copied it
        return None, None
    if rt.expires_at < now_iso():
        return None, None
    user = db.get(User, rt.user_id)
    if not user or not user.is_active:
        return None, None
    rt.rotated = True
    db.commit()
    return user, issue_refresh_token(db, user, rt.family_id)


def revoke_family(db, family_id: str):
    for t in db.query(RefreshToken).filter(RefreshToken.family_id == family_id,
                                           RefreshToken.revoked_at.is_(None)).all():
        t.revoked_at = now_iso()
    db.commit()


def revoke_token(db, raw: str):
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw)).first()
    if rt:
        revoke_family(db, rt.family_id)


def revoke_user_sessions(db, user_id: int):
    for t in db.query(RefreshToken).filter(RefreshToken.user_id == user_id,
                                           RefreshToken.revoked_at.is_(None)).all():
        t.revoked_at = now_iso()
    db.commit()


class LoginThrottle:
    """5 wrong passwords from one address for one account blocks that pair for 15 minutes."""
    def __init__(self):
        self._fails = {}
        self._lock = threading.Lock()

    def blocked(self, ip, username) -> int:
        with self._lock:
            rec = self._fails.get((ip, username))
            if rec and rec["until"] > time.time():
                return int(rec["until"] - time.time())
            return 0

    def fail(self, ip, username):
        with self._lock:
            rec = self._fails.setdefault((ip, username), {"n": 0, "until": 0})
            if rec["until"] and rec["until"] <= time.time():
                rec.update(n=0, until=0)
            rec["n"] += 1
            if rec["n"] >= config.LOGIN_MAX_FAILS:
                rec["until"] = time.time() + config.LOGIN_BLOCK_SECONDS

    def success(self, ip, username):
        with self._lock:
            self._fails.pop((ip, username), None)

    def reset(self):
        with self._lock:
            self._fails.clear()


throttle = LoginThrottle()
