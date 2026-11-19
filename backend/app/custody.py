"""SHA-256 fingerprints and the hash-chained chain of custody."""
import hashlib
from pathlib import Path

from .models import CustodyEvent, Evidence, now_iso

GENESIS = "0" * 64


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_event_hash(evidence_id, seq, action, actor, at, file_hash, prev_hash, note) -> str:
    raw = "|".join(str(x) for x in (evidence_id, seq, action, actor, at, file_hash, prev_hash, note or ""))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def add_event(db, ev: Evidence, action: str, actor: str, note: str = "", file_hash: str = None):
    """Append one event to the evidence's chain (caller commits)."""
    last = (db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id)
            .order_by(CustodyEvent.seq.desc()).first())
    seq = (last.seq + 1) if last else 1
    prev = last.event_hash if last else GENESIS
    at = now_iso()
    fh = file_hash or ev.sha256
    h = compute_event_hash(ev.id, seq, action, actor, at, fh, prev, note)
    e = CustodyEvent(evidence_id=ev.id, seq=seq, action=action, actor=actor, at=at,
                     file_hash=fh, prev_hash=prev, event_hash=h, note=note)
    db.add(e)
    db.flush()
    return e


def verify_chain(events) -> dict:
    """Walk the chain recomputing every hash. Returns {ok, broken_at, message}."""
    prev = GENESIS
    expected_seq = 1
    for e in sorted(events, key=lambda x: x.seq):
        if e.seq != expected_seq:
            return {"ok": False, "broken_at": expected_seq,
                    "message": f"Event {expected_seq} is missing (sequence jumps to {e.seq})."}
        if e.prev_hash != prev:
            return {"ok": False, "broken_at": e.seq,
                    "message": f"Event {e.seq} does not link to the event before it."}
        h = compute_event_hash(e.evidence_id, e.seq, e.action, e.actor, e.at, e.file_hash, e.prev_hash, e.note)
        if h != e.event_hash:
            return {"ok": False, "broken_at": e.seq, "message": f"Event {e.seq} was altered after it was recorded."}
        prev = e.event_hash
        expected_seq += 1
    return {"ok": True, "broken_at": None, "message": f"{expected_seq - 1} chained events verified."}


def verify_evidence(ev: Evidence, upload_dir: Path) -> dict:
    """Re-hash the stored file and walk the chain."""
    path = upload_dir / ev.stored_name
    file_ok, current = False, None
    if path.exists():
        current = sha256_file(path)
        file_ok = current == ev.sha256
    chain = verify_chain(ev.custody)
    if file_ok and chain["ok"]:
        msg = f"File and custody chain are intact. Stored file matches the intake hash; {chain['message']}"
    elif not path.exists():
        msg = "The stored file is missing."
    elif not file_ok:
        msg = "The stored file no longer matches the hash taken at intake."
    else:
        msg = chain["message"]
    return {"ok": file_ok and chain["ok"], "file_ok": file_ok, "chain_ok": chain["ok"],
            "broken_at": chain["broken_at"], "current_hash": current, "intake_hash": ev.sha256,
            "message": msg}
