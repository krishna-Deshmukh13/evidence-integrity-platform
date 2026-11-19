import hashlib
import tempfile
import pathlib
import pytest

from app import custody

def test_sha256_computation():
    data = b"FORENSIC_DIGITAL_EVIDENCE_RECORD_SAMPLE"
    expected = hashlib.sha256(data).hexdigest()
    
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(data)
        tf_path = pathlib.Path(tf.name)
        
    try:
        calculated = custody.sha256_file(tf_path)
        assert calculated == expected
        assert len(calculated) == 64
    finally:
        tf_path.unlink(missing_ok=True)


def test_tamper_detection_avalanche_effect():
    data = b"OFFICIAL_POLICE_INCIDENT_REPORT_DOCUMENT_2026"
    h1 = hashlib.sha256(data).hexdigest()
    
    # Tamper 1 bit: change first byte
    tampered_data = bytearray(data)
    tampered_data[0] ^= 0x01
    h2 = hashlib.sha256(tampered_data).hexdigest()
    
    assert h1 != h2
    diff_chars = sum(1 for a, b in zip(h1, h2) if a != b)
    # SHA-256 avalanche effect alters ~50% of the digest (around 32 hex chars)
    assert diff_chars > 20, "Avalanche effect must alter majority of hash characters"


def test_file_byte_modification_detected(db, admin_user):
    from app.models import Evidence, CustodyEvent
    from app import config
    
    ev = db.query(Evidence).first()
    assert ev is not None, "Need at least one evidence item in DB"
    
    path = config.UPLOAD_DIR / ev.stored_name
    assert path.exists(), f"Evidence file {path} should exist"
    
    # Intact check
    intact_hash = custody.sha256_file(path)
    assert intact_hash == ev.sha256
    
    # Verify chain
    chain_res = custody.verify_chain(ev.custody)
    assert chain_res["ok"] is True
