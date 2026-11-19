from tests.conftest import login, make_user


def test_roles_enforced(admin, samples):
    make_user(admin, "rohan", "investigator")
    make_user(admin, "kavya", "viewer")
    cid = admin.post("/api/cases", json={"reference": "CR-9", "title": "Roles"}).json()["id"]
    admin.cookies.clear()
    login(admin, "kavya")
    assert admin.get("/api/cases").status_code == 200                      # viewer can read
    assert admin.post("/api/cases", json={"reference": "x", "title": "y"}).status_code == 403
    assert admin.get("/api/activity").status_code == 403
    admin.cookies.clear()
    login(admin, "rohan")
    assert admin.post("/api/cases", json={"reference": "CR-10", "title": "ok"}).status_code == 200
    assert admin.delete(f"/api/cases/{cid}").status_code == 403            # only admin deletes
    assert admin.post("/api/users", json={"username": "z", "full_name": "Z", "password": "12345678"}).status_code == 403


def test_last_admin_and_self_protection(admin):
    me = admin.get("/api/auth/me").json()
    assert admin.patch(f"/api/users/{me['id']}", json={"role": "viewer"}).status_code == 400
    assert admin.patch(f"/api/users/{me['id']}", json={"is_active": False}).status_code == 400


def test_review_notes_search_dashboard(admin, samples):
    cid = admin.post("/api/cases", json={"reference": "CR-5", "title": "Search me"}).json()["id"]
    with open(samples / "photo_tampered.jpg", "rb") as fh:
        e = admin.post(f"/api/cases/{cid}/evidence", files={"file": ("photo_tampered.jpg", fh, "image/jpeg")}).json()
    r = admin.patch(f"/api/evidence/{e['id']}", json={"review_status": "flagged", "tags": ["urgent", "cctv"]})
    assert r.json()["review_status"] == "flagged" and r.json()["tags"] == ["cctv", "urgent"]
    assert admin.patch(f"/api/evidence/{e['id']}", json={"review_status": "bogus"}).status_code == 400
    admin.post(f"/api/evidence/{e['id']}/notes", json={"body": "jacket looks pasted"})
    assert len(admin.get("/api/search", params={"q": "jacket"}).json()) == 1
    assert len(admin.get("/api/search", params={"verdict": "Likely manipulated"}).json()) == 1
    assert len(admin.get("/api/search", params={"category": "pixel", "check": "copy_move"}).json()) == 1
    d = admin.get("/api/dashboard").json()
    assert d["files"] == 1 and d["flagged"] == 1 and d["review_status"]["flagged"] == 1
    acts = admin.get("/api/activity").json()
    assert any(a["action"] == "upload" for a in acts)
    assert admin.get("/api/activity/export.csv").text.startswith("time,actor")
