"""Usage: python scripts/create_user.py kavya "Kavya Rao" --role viewer [--password ...]"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import auth  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import User  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("username")
p.add_argument("full_name")
p.add_argument("--role", default="viewer", choices=["admin", "investigator", "viewer"])
p.add_argument("--password")
a = p.parse_args()
pw = a.password or getpass.getpass("Password (min 8 chars): ")
init_db()
db = SessionLocal()
if db.query(User).filter(User.username == a.username.lower()).first():
    sys.exit("That username already exists")
db.add(User(username=a.username.lower(), full_name=a.full_name, role=a.role, password_hash=auth.hash_password(pw)))
db.commit()
print(f"Created {a.role} account '{a.username}'")
