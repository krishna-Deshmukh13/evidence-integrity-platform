from tests.conftest import PW, login, make_user


def test_api_closed_without_session(client):
    for path in ("/api/cases", "/api/dashboard", "/api/search", "/api/users", "/api/activity", "/api/auth/me"):
        assert client.get(path).status_code == 401, path


def test_first_account_is_admin(client):
    assert client.get("/api/auth/status").json()["needs_setup"] is True
    r = client.post("/api/auth/setup", json={"username": "meera", "full_name": "M K", "password": PW})
    assert r.json()["role"] == "admin"
    assert client.get("/api/auth/status").json()["needs_setup"] is False
    assert client.post("/api/auth/setup", json={"username": "x", "full_name": "X", "password": PW}).status_code == 409


def test_cookies_httponly_samesite(admin):
    r = login(admin, "meera")
    sc = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "httponly" in sc and "samesite=strict" in sc
    assert "access_token" in sc and "refresh_token" in sc


def test_refresh_rotation_and_reuse_detection(admin):
    r = login(admin, "meera")
    old = admin.cookies.get("refresh_token")
    assert admin.post("/api/auth/refresh").status_code == 200
    new = admin.cookies.get("refresh_token")
    assert new and new != old
    admin.cookies.set("refresh_token", old, path="/api/auth", domain="testserver.local")   # replay the old one
    assert admin.post("/api/auth/refresh").status_code == 401
    admin.cookies.set("refresh_token", new, path="/api/auth", domain="testserver.local")   # the whole family is revoked
    assert admin.post("/api/auth/refresh").status_code == 401


def test_logout_revokes(admin):
    login(admin, "meera")
    raw = admin.cookies.get("refresh_token")
    admin.post("/api/auth/logout")
    admin.cookies.set("refresh_token", raw, path="/api/auth", domain="testserver.local")
    assert admin.post("/api/auth/refresh").status_code == 401


def test_rate_limit_and_same_error(client, admin):
    admin.cookies.clear()
    a = login(admin, "nobody", "wrong-password")
    b = login(admin, "meera", "wrong-password")
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    for _ in range(4):
        login(admin, "meera", "wrong-password")
    assert login(admin, "meera", PW).status_code == 429        # blocked even with the right password


def test_disabled_account_cannot_sign_in(admin):
    make_user(admin, "rohan", "investigator")
    uid = next(u["id"] for u in admin.get("/api/users").json() if u["username"] == "rohan")
    assert admin.patch(f"/api/users/{uid}", json={"is_active": False}).status_code == 200
    admin.cookies.clear()
    assert login(admin, "rohan").status_code == 401
