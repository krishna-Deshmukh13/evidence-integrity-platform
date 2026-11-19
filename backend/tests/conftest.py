import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="eip-test-")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["EI_STORAGE_DIR"] = _tmp
os.environ["EI_SYNC"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from app.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from scripts import make_samples  # noqa: E402

PW = "ram@1234"


@pytest.fixture(scope="session")
def samples():
    return make_samples.make(Path(_tmp) / "samples")


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    init_db()
    auth.throttle.reset()
    with TestClient(app) as c:
        yield c


def login(client, username, password=PW):
    return client.post("/api/auth/login", json={"username": username, "password": password})


@pytest.fixture()
def admin(client):
    r = client.post("/api/auth/setup", json={"username": "meera", "full_name": "Insp. Meera Kulkarni",
                                             "password": PW})
    assert r.status_code == 200
    return client


def make_user(client, username, role):
    r = client.post("/api/users", json={"username": username, "full_name": username.title(),
                                        "password": PW, "role": role})
    assert r.status_code == 200, r.text


@pytest.fixture(scope="session")
def samples2():
    from scripts import make_samples2
    return make_samples2.make(Path(_tmp) / "samples2")
