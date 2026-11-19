"""Two-Factor Authentication (TOTP) enrolment and verification routes."""
import base64
import hashlib
import io
import json
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
import pyotp
import qrcode
from sqlalchemy.orm import Session

from .. import activity, auth
from ..database import get_db
from ..deps import client_ip, current_user, require_role
from ..models import User

router = APIRouter(prefix="/api/auth/2fa")


class Enable2FABody(BaseModel):
    secret: str = Field(min_length=16, max_length=64)
    code: str = Field(min_length=4, max_length=10)
    recovery_codes: List[str] = Field(min_length=4, max_length=16)


class Disable2FABody(BaseModel):
    password: str = Field(min_length=1)


def generate_recovery_codes(count: int = 8) -> List[str]:
    """Generate human-readable recovery codes formatted as 'xxxx-xxxx'."""
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(count)]


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode("utf-8")).hexdigest()


@router.get("/setup")
def setup_2fa(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Generate a new TOTP secret, provisioning URI, QR code, and recovery codes."""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.username,
        issuer_name="Evidence Integrity Platform"
    )

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    recovery_codes = generate_recovery_codes(8)

    return {
        "secret": secret,
        "otpauth_url": provisioning_uri,
        "qr_code": qr_b64,
        "recovery_codes": recovery_codes,
        "totp_enabled": bool(user.totp_enabled),
        "role": user.role,
        "totp_required": user.role in ("admin", "investigator"),
    }


@router.post("/enable")
def enable_2fa(body: Enable2FABody, request: Request,
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Confirm TOTP enrollment with a 6-digit code and save hashed recovery codes."""
    ip = client_ip(request)
    wait = auth.throttle.blocked(ip, user.username)
    if wait:
        raise HTTPException(429, f"Too many failed 2FA verification attempts. Try again in {wait // 60 + 1} minutes.")

    totp = pyotp.TOTP(body.secret.strip())
    if not totp.verify(body.code.strip(), valid_window=1):
        auth.throttle.fail(ip, user.username)
        raise HTTPException(400, "Invalid authentication code. Please check your authenticator app and try again.")
    auth.throttle.success(ip, user.username)

    hashed_recovery = [hash_code(rc) for rc in body.recovery_codes]
    user.totp_secret = body.secret.strip()
    user.totp_enabled = True
    user.recovery_codes = json.dumps(hashed_recovery)
    db.commit()

    activity.log(db, activity.actor_name(user), "account",
                 "Enrolled in two-factor authentication (TOTP)",
                 ip=client_ip(request))

    return {"ok": True, "totp_enabled": True}


@router.post("/disable")
def disable_2fa(body: Disable2FABody, request: Request,
                db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Disable TOTP two-factor authentication after confirming user's current password."""
    ip = client_ip(request)
    wait = auth.throttle.blocked(ip, user.username)
    if wait:
        raise HTTPException(429, f"Too many failed attempts. Try again in {wait // 60 + 1} minutes.")

    if not auth.verify_password(body.password, user.password_hash):
        auth.throttle.fail(ip, user.username)
        raise HTTPException(401, "Incorrect password")
    auth.throttle.success(ip, user.username)

    user.totp_secret = None
    user.totp_enabled = False
    user.recovery_codes = None
    db.commit()

    activity.log(db, activity.actor_name(user), "account",
                 "Disabled two-factor authentication (TOTP)",
                 ip=client_ip(request))

    return {"ok": True, "totp_enabled": False}
