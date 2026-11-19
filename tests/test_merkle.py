import hashlib
import pytest
from app.models import Case, Evidence

def _hash_pair(a: str, b: str) -> str:
    combined = (a + b).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()

def compute_merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return ""
    current = list(hashes)
    while len(current) > 1:
        nxt = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                nxt.append(_hash_pair(current[i], current[i + 1]))
            else:
                nxt.append(_hash_pair(current[i], current[i]))
        current = nxt
    return current[0]

def test_merkle_tree_construction():
    hashes = [
        hashlib.sha256(b"leaf_1").hexdigest(),
        hashlib.sha256(b"leaf_2").hexdigest(),
        hashlib.sha256(b"leaf_3").hexdigest(),
        hashlib.sha256(b"leaf_4").hexdigest(),
    ]
    root = compute_merkle_root(hashes)
    assert len(root) == 64
    
    # Determinism check
    assert compute_merkle_root(hashes) == root
    
    # Tamper one leaf
    tampered_hashes = list(hashes)
    tampered_hashes[2] = hashlib.sha256(b"leaf_3_TAMPERED").hexdigest()
    tampered_root = compute_merkle_root(tampered_hashes)
    assert tampered_root != root


def test_case_merkle_endpoint(client, admin_user, db):
    from app import auth
    case = db.query(Case).first()
    assert case is not None
    
    token = auth.make_access_token(admin_user)
    client.cookies.set("access_token", token)
    
    resp = client.get(f"/api/intel/merkle/{case.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "root_hash" in data
    assert "leaves_count" in data
    assert len(data["root_hash"]) == 64
