"""Tests for Group E: Per-case access control (E1) and TOTP 2FA (E2)."""
import json
import pyotp
import pytest
from app.database import SessionLocal
from app.models import Case, CaseMember, Evidence, User
from tests.conftest import make_user, login, PW


def test_per_case_access_control(admin, samples):
    """Test per-case access control isolation: non-members cannot access cases or files."""
    make_user(admin, "rohan_investigator", "investigator")
    make_user(admin, "kavya_viewer", "viewer")

    # Admin creates Case A
    case_a = admin.post("/api/cases", json={"reference": "CR-ALPHA", "title": "Alpha Operations"}).json()
    case_a_id = case_a["id"]
    with open(samples / "photo_original.jpg", "rb") as fh:
        ev_a = admin.post(f"/api/cases/{case_a_id}/evidence", files={"file": ("alpha.jpg", fh, "image/jpeg")}).json()
    ev_a_id = ev_a["id"]

    # Rohan creates Case B
    admin.cookies.clear()
    login(admin, "rohan_investigator")
    case_b = admin.post("/api/cases", json={"reference": "CR-BETA", "title": "Beta Operations"}).json()
    case_b_id = case_b["id"]
    with open(samples / "photo_tampered.jpg", "rb") as fh:
        ev_b = admin.post(f"/api/cases/{case_b_id}/evidence", files={"file": ("beta.jpg", fh, "image/jpeg")}).json()
    ev_b_id = ev_b["id"]

    # Rohan can access Case B and its evidence
    assert admin.get(f"/api/cases/{case_b_id}").status_code == 200
    assert admin.get(f"/api/evidence/{ev_b_id}").status_code == 200
    assert admin.get(f"/api/evidence/{ev_b_id}/file").status_code == 200

    # Rohan CANNOT access Case A or Case A's evidence (forbidden)
    assert admin.get(f"/api/cases/{case_a_id}").status_code == 403
    assert admin.get(f"/api/evidence/{ev_a_id}").status_code == 403
    assert admin.get(f"/api/evidence/{ev_a_id}/file").status_code == 403

    # Rohan's case list only shows Case B
    rohan_cases = admin.get("/api/cases").json()
    assert any(c["id"] == case_b_id for c in rohan_cases)
    assert not any(c["id"] == case_a_id for c in rohan_cases)

    # Kavya (viewer, non-member) accesses platform
    admin.cookies.clear()
    login(admin, "kavya_viewer")
    assert admin.get("/api/cases").json() == []
    assert admin.get(f"/api/cases/{case_a_id}").status_code == 403
    assert admin.get(f"/api/cases/{case_b_id}").status_code == 403

    # Switch to Admin to manage case membership
    admin.cookies.clear()
    login(admin, "meera")
    db = SessionLocal()
    try:
        kavya = db.query(User).filter(User.username == "kavya_viewer").first()
        kavya_id = kavya.id
    finally:
        db.close()

    # Admin adds Kavya to Case A
    add_res = admin.post(f"/api/cases/{case_a_id}/members", json={"user_id": kavya_id, "role": "member"})
    assert add_res.status_code == 200
    assert add_res.json()["user_id"] == kavya_id

    # Duplicate add returns 409
    dup_res = admin.post(f"/api/cases/{case_a_id}/members", json={"user_id": kavya_id, "role": "member"})
    assert dup_res.status_code == 409

    # Now Kavya has access to Case A!
    admin.cookies.clear()
    login(admin, "kavya_viewer")
    kavya_cases = admin.get("/api/cases").json()
    assert len(kavya_cases) == 1
    assert kavya_cases[0]["id"] == case_a_id
    assert admin.get(f"/api/cases/{case_a_id}").status_code == 200
    assert admin.get(f"/api/evidence/{ev_a_id}").status_code == 200
    # Still forbidden on Case B
    assert admin.get(f"/api/cases/{case_b_id}").status_code == 403

    # Admin removes Kavya from Case A
    admin.cookies.clear()
    login(admin, "meera")
    del_res = admin.delete(f"/api/cases/{case_a_id}/members/{kavya_id}")
    assert del_res.status_code == 200

    # Kavya is forbidden again
    admin.cookies.clear()
    login(admin, "kavya_viewer")
    assert admin.get(f"/api/cases/{case_a_id}").status_code == 403


def test_totp_enrolment_and_authentication(admin):
    """Test TOTP enrolment, 2FA prompt on sign-in, recovery codes, and admin reset."""
    make_user(admin, "sec_user", "investigator")
    admin.cookies.clear()
    login(admin, "sec_user")

    # 1. Setup 2FA
    setup_res = admin.get("/api/auth/2fa/setup")
    assert setup_res.status_code == 200
    setup_data = setup_res.json()
    secret = setup_data["secret"]
    recovery_codes = setup_data["recovery_codes"]
    assert "data:image/png;base64," in setup_data["qr_code"]
    assert len(recovery_codes) == 8

    # 2. Try enabling with invalid code
    bad_enable = admin.post("/api/auth/2fa/enable", json={
        "secret": secret, "code": "000000", "recovery_codes": recovery_codes
    })
    assert bad_enable.status_code == 400

    # 3. Enable with valid TOTP code
    valid_code = pyotp.TOTP(secret).now()
    good_enable = admin.post("/api/auth/2fa/enable", json={
        "secret": secret, "code": valid_code, "recovery_codes": recovery_codes
    })
    assert good_enable.status_code == 200
    assert good_enable.json()["totp_enabled"] is True

    # 4. Sign out and test login with 2FA
    admin.cookies.clear()
    login_prompt = admin.post("/api/auth/login", json={"username": "sec_user", "password": PW})
    assert login_prompt.status_code == 200
    assert login_prompt.json().get("requires_2fa") is True
    # Verify no auth cookie was set on the first 2FA step
    assert "access_token" not in admin.cookies

    # 5. Invalid 2FA code fails
    bad_login = admin.post("/api/auth/login", json={
        "username": "sec_user", "password": PW, "code": "123456"
    })
    assert bad_login.status_code == 401

    # 6. Valid 2FA code signs in successfully
    totp_now = pyotp.TOTP(secret).now()
    good_login = admin.post("/api/auth/login", json={
        "username": "sec_user", "password": PW, "code": totp_now
    })
    assert good_login.status_code == 200
    assert good_login.json()["username"] == "sec_user"
    assert "access_token" in admin.cookies

    # 7. Test Recovery Code login
    admin.cookies.clear()
    rec_code = recovery_codes[0]
    rec_login = admin.post("/api/auth/login", json={
        "username": "sec_user", "password": PW, "code": rec_code
    })
    assert rec_login.status_code == 200
    assert "access_token" in admin.cookies

    # 8. Reusing the same recovery code must fail
    admin.cookies.clear()
    reused_login = admin.post("/api/auth/login", json={
        "username": "sec_user", "password": PW, "code": rec_code
    })
    assert reused_login.status_code == 401

    # 9. Admin reset 2FA
    admin.cookies.clear()
    login(admin, "meera")
    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.username == "sec_user").first()
        target_uid = user_obj.id
    finally:
        db.close()

    reset_res = admin.post(f"/api/users/{target_uid}/reset-2fa")
    assert reset_res.status_code == 200
    assert reset_res.json()["totp_enabled"] is False

    # 10. User can now log in directly without 2FA
    admin.cookies.clear()
    direct_login = admin.post("/api/auth/login", json={"username": "sec_user", "password": PW})
    assert direct_login.status_code == 200
    assert direct_login.json().get("requires_2fa") is not True
    assert "access_token" in admin.cookies
