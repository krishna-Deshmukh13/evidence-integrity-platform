import os
import sys
import pathlib
import pytest
from fastapi.testclient import TestClient

root_dir = pathlib.Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import User, Case, Evidence, Finding, now_iso
from app import auth

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(scope="session")
def db():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="session")
def admin_user(db):
    user = db.query(User).filter(User.role == "admin").first()
    if not user:
        user = User(username="admin_test", full_name="System Admin", role="admin",
                    password_hash=auth.hash_password("admin_pass_123"), is_active=True)
        db.add(user)
        db.commit()
    return user

@pytest.fixture(scope="session")
def investigator_user(db):
    user = db.query(User).filter(User.role == "investigator").first()
    if not user:
        user = User(username="insp_test", full_name="Inspector Test", role="investigator",
                    password_hash=auth.hash_password("insp_pass_123"), is_active=True)
        db.add(user)
        db.commit()
    return user

@pytest.fixture(scope="session")
def viewer_user(db):
    user = db.query(User).filter(User.role == "viewer").first()
    if not user:
        user = User(username="viewer_test", full_name="Viewer Test", role="viewer",
                    password_hash=auth.hash_password("viewer_pass_123"), is_active=True)
        db.add(user)
        db.commit()
    return user
