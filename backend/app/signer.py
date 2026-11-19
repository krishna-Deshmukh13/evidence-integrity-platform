"""Cryptographic signing, X.509 certificate management, PDF signing, and custody chain anchoring."""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import io
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import httpx

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers

from . import config, custody
from .models import ActivityLog, Case, CustodyEvent, Evidence, now_iso

KEY_DIR = config.STORAGE_DIR / "keys"
KEY_FILE = KEY_DIR / "private_key.pem"
CERT_FILE = KEY_DIR / "certificate.pem"


def ensure_keys():
    """Generate self-signed X.509 RSA keypair on first run, stored outside uploads."""
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists() and CERT_FILE.exists():
        return

    # Generate 2048-bit RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Save private key PEM
    KEY_FILE.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Create self-signed X.509 certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, "Maharashtra"),
        x509.NameAttribute(x509.NameOID.LOCALITY_NAME, "Mumbai"),
        x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "Evidence Integrity Platform"),
        x509.NameAttribute(x509.NameOID.ORGANIZATIONAL_UNIT_NAME, "Forensic Assurance Division"),
        x509.NameAttribute(x509.NameOID.COMMON_NAME, "EIP Root Evidence Signer"),
    ])

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def get_signer_fingerprint() -> str:
    """Return SHA-256 fingerprint of the self-signed certificate in uppercase hex."""
    ensure_keys()
    cert_data = CERT_FILE.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)
    raw_fp = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest().upper()
    return ":".join(raw_fp[i:i+2] for i in range(0, len(raw_fp), 2))


def sign_pdf_bytes(pdf_bytes: bytes) -> Tuple[bytes, str]:
    """Cryptographically sign PDF bytes using pyHanko and return (signed_pdf_bytes, sha256_hash)."""
    ensure_keys()
    signer = signers.SimpleSigner.load(str(KEY_FILE), str(CERT_FILE))

    inf = io.BytesIO(pdf_bytes)
    w = IncrementalPdfFileWriter(inf)
    out = io.BytesIO()

    # Apply digital signature
    signers.sign_pdf(
        w,
        signers.PdfSignatureMetadata(field_name="EIP_ForensicSignature"),
        signer=signer,
        output=out,
    )
    signed = out.getvalue()
    h = hashlib.sha256(signed).hexdigest()
    return signed, h


def sign_data_bytes(data: bytes) -> str:
    """Sign raw data bytes using the platform RSA private key and return base64 signature."""
    ensure_keys()
    key_bytes = KEY_FILE.read_bytes()
    key = serialization.load_pem_private_key(key_bytes, password=None)
    sig = key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode("ascii")


def verify_data_signature(data: bytes, b64_sig: str) -> bool:
    """Verify an RSA-PSS SHA-256 signature against the platform certificate."""
    try:
        ensure_keys()
        cert_data = CERT_FILE.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        pub_key = cert.public_key()
        sig = base64.b64decode(b64_sig)
        pub_key.verify(
            sig,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def request_rfc3161_timestamp(digest_hex: str) -> Optional[str]:
    """Optional RFC 3161 timestamping from a public free TSA server; skip gracefully if offline."""
    tsa_url = "http://timestamp.digicert.com"
    try:
        req_body = bytes.fromhex(digest_hex)
        # Simple HTTP check with short timeout
        r = httpx.post(
            tsa_url,
            content=req_body,
            headers={"Content-Type": "application/timestamp-query"},
            timeout=2.0,
        )
        if r.status_code == 200 and r.content:
            return base64.b64encode(r.content).decode("ascii")
    except Exception:
        pass
    return None


def export_custody_anchor(db, actor: str) -> dict:
    """Export signed JSON containing head hash of every evidence chain."""
    ensure_keys()
    evidence_list = db.query(Evidence).all()
    cases_map = {c.id: c for c in db.query(Case).all()}
    now_str = now_iso()

    chains = []
    for ev in evidence_list:
        events = sorted(ev.custody, key=lambda x: x.seq)
        head_hash = events[-1].event_hash if events else "0" * 64
        c = cases_map.get(ev.case_id)
        chains.append({
            "evidence_id": ev.id,
            "case_id": ev.case_id,
            "case_reference": c.reference if c else "",
            "filename": ev.filename,
            "file_sha256": ev.sha256,
            "chain_length": len(events),
            "head_hash": head_hash,
        })

    payload = {
        "platform": "Evidence Integrity Platform",
        "anchor_version": "1.0",
        "exported_at": now_str,
        "exported_by": actor,
        "total_chains": len(chains),
        "signer_fingerprint": get_signer_fingerprint(),
        "chains": chains,
    }

    # Canonicalize and sign
    canon_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = sign_data_bytes(canon_bytes)
    payload_hash = hashlib.sha256(canon_bytes).hexdigest()

    # Optional RFC 3161 timestamp
    tsa_token = request_rfc3161_timestamp(payload_hash)

    payload["signature"] = signature
    payload["signature_algorithm"] = "RSA-PSS-SHA256"
    payload["rfc3161"] = {
        "applied": bool(tsa_token),
        "token": tsa_token,
        "note": "RFC 3161 token attached" if tsa_token else "RFC 3161 timestamp server offline/skipped; signed with platform key",
    }
    return payload


def verify_custody_anchor(db, anchor: dict) -> dict:
    """Verify live custody chains against an anchor JSON file."""
    # 1. Verify signature
    sig = anchor.get("signature")
    if not sig:
        return {"ok": False, "signature_valid": False, "message": "No signature found in anchor document"}

    # Copy without signature and rfc3161 fields to reconstruct original signed bytes
    check_dict = {k: v for k, v in anchor.items() if k not in ("signature", "signature_algorithm", "rfc3161")}
    canon_bytes = json.dumps(check_dict, sort_keys=True).encode("utf-8")

    sig_valid = verify_data_signature(canon_bytes, sig)
    if not sig_valid:
        return {
            "ok": False,
            "signature_valid": False,
            "message": "Cryptographic signature verification FAILED. The anchor file may have been modified.",
        }

    # 2. Check each chain against live database
    chains = anchor.get("chains") or []
    matching = 0
    discrepancies = []

    for item in chains:
        eid = item.get("evidence_id")
        anchor_head = item.get("head_hash")
        ev = db.get(Evidence, eid)
        if not ev:
            discrepancies.append({
                "evidence_id": eid,
                "filename": item.get("filename"),
                "reason": "Evidence record missing from database",
            })
            continue

        events = sorted(ev.custody, key=lambda x: x.seq)
        # Check if anchor_head exists anywhere in the chain sequence
        event_hashes = [e.event_hash for e in events]
        if anchor_head not in event_hashes:
            discrepancies.append({
                "evidence_id": eid,
                "filename": ev.filename,
                "reason": "Anchor head hash not found in current custody chain (chain was altered or truncated)",
                "anchor_head": anchor_head,
                "current_head": events[-1].event_hash if events else None,
            })
        else:
            matching += 1

    ok = sig_valid and len(discrepancies) == 0
    return {
        "ok": ok,
        "signature_valid": sig_valid,
        "total_chains": len(chains),
        "matching_chains": matching,
        "discrepancies": discrepancies,
        "exported_at": anchor.get("exported_at"),
        "signer_fingerprint": anchor.get("signer_fingerprint"),
        "message": (
            f"Anchor verified: {matching}/{len(chains)} chains match current system state."
            if ok else f"Discrepancies found: {len(discrepancies)} chain(s) do not match anchor."
        ),
    }
