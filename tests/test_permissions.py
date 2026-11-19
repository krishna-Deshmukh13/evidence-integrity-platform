import pytest
from app import auth
from app.models import Case, Evidence

def test_viewer_permission_enforcement(client, viewer_user, db):
    token = auth.make_access_token(viewer_user)
    client.cookies.set("access_token", token)
    
    # Viewer can read cases
    r_get = client.get("/api/cases")
    assert r_get.status_code == 200

    # Viewer CANNOT create a case (Requires Investigator)
    r_post_case = client.post("/api/cases", json={"reference": "CR-DENIED-01", "title": "Unauthorized Case"})
    assert r_post_case.status_code == 403, f"Expected 403 for viewer, got {r_post_case.status_code}"

    # Viewer CANNOT upload evidence
    case = db.query(Case).first()
    assert case is not None
    r_upload = client.post(f"/api/cases/{case.id}/evidence", files={"file": ("test.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")})
    assert r_upload.status_code == 403, f"Expected 403 for viewer, got {r_upload.status_code}"

    # Viewer CANNOT patch evidence review status
    ev = db.query(Evidence).first()
    assert ev is not None
    r_patch = client.patch(f"/api/evidence/{ev.id}", json={"review_status": "flagged"})
    assert r_patch.status_code == 403, f"Expected 403 for viewer, got {r_patch.status_code}"

    # Viewer CANNOT delete evidence
    r_del = client.delete(f"/api/evidence/{ev.id}")
    assert r_del.status_code == 403, f"Expected 403 for viewer, got {r_del.status_code}"


def test_investigator_permission_enforcement(client, investigator_user, db):
    token = auth.make_access_token(investigator_user)
    client.cookies.set("access_token", token)

    # Investigator can read cases
    r_get = client.get("/api/cases")
    assert r_get.status_code == 200

    # Investigator CANNOT delete cases (Requires Admin)
    case = db.query(Case).first()
    assert case is not None
    r_del = client.delete(f"/api/cases/{case.id}")
    assert r_del.status_code == 403, f"Expected 403 for investigator, got {r_del.status_code}"

    # Investigator CANNOT create new users (Requires Admin)
    r_users = client.post("/api/users", json={"username": "unauth", "password": "123", "role": "admin"})
    assert r_users.status_code == 403, f"Expected 403 for investigator, got {r_users.status_code}"


def test_admin_permissions(client, admin_user, db):
    token = auth.make_access_token(admin_user)
    client.cookies.set("access_token", token)

    # Admin can list users
    r_users = client.get("/api/users")
    assert r_users.status_code == 200
    assert len(r_users.json()) > 0
