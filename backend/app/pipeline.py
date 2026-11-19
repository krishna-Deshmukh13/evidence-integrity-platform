"""Background analysis queue. ONE worker so the AI models never run at the same time."""
import json
import queue
import threading
import traceback

from . import activity, config, custody, report as report_mod, scoring, similarity
from .analyzers.common import F
from .database import SessionLocal
from .models import Evidence, Finding

_q: "queue.Queue[int]" = queue.Queue()
_waiting = []          # evidence ids in queue order (for "Queued, 2 ahead")
_lock = threading.Lock()
_worker = None
_rq: "queue.Queue[int]" = queue.Queue()   # second worker writes reports so a slow LLM never delays analysis
report_busy = set()
_rworker = None


def queue_position(evidence_id: int):
    with _lock:
        return _waiting.index(evidence_id) if evidence_id in _waiting else None


def enqueue(evidence_id: int):
    if config.SYNC_ANALYSIS:
        process(evidence_id)
        return
    with _lock:
        if evidence_id not in _waiting:
            _waiting.append(evidence_id)
    _q.put(evidence_id)
    start_worker()


def start_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_loop, daemon=True, name="analysis-worker")
        _worker.start()


def enqueue_report(evidence_id: int):
    report_busy.add(evidence_id)
    if config.SYNC_ANALYSIS:
        write_report(evidence_id)
        return
    _rq.put(evidence_id)
    global _rworker
    if _rworker is None or not _rworker.is_alive():
        _rworker = threading.Thread(target=_report_loop, daemon=True, name="report-worker")
        _rworker.start()


def _report_loop():
    while True:
        eid = _rq.get()
        try:
            write_report(eid)
        except Exception:
            traceback.print_exc()
        _rq.task_done()


def write_report(evidence_id: int):
    """Template report is already stored; replace it with the LLM version when the model delivers one."""
    db = SessionLocal()
    try:
        ev = db.get(Evidence, evidence_id)
        if ev and ev.status == "done":
            res = report_mod.write_with_llm(ev, ev.findings)
            if res:
                ev.report, ev.report_model = res
                db.commit()
    finally:
        report_busy.discard(evidence_id)
        db.close()


def _loop():
    while True:
        eid = _q.get()
        with _lock:
            if eid in _waiting:
                _waiting.remove(eid)
        try:
            process(eid)
        except Exception:
            traceback.print_exc()
        _q.task_done()


def _dispatch(ev, path, art_dir, progress):
    if ev.media_type == "image":
        from .analyzers import image
        return image.analyze(path, art_dir, progress)
    try:  # video / audio / document analyzers
        mod = __import__(f"app.analyzers.{ev.media_type}", fromlist=["analyze"])
        return mod.analyze(path, art_dir, progress)
    except ImportError as exc:
        return ([F("container", "unsupported", "info", f"No {ev.media_type} analyzer available",
                   f"A required package is missing: {exc}. Run setup again.")], {})


def process(evidence_id: int):
    db = SessionLocal()
    try:
        ev = db.get(Evidence, evidence_id)
        if not ev:
            return

        def progress(stage, pct):
            ev.stage, ev.progress = stage, int(pct)
            db.commit()

        ev.status, ev.error, ev.progress, ev.stage = "analyzing", None, 1, "Starting"
        db.commit()
        path = config.UPLOAD_DIR / ev.stored_name
        now_hash = custody.sha256_file(path) if path.exists() else None
        intact = now_hash == ev.sha256
        custody.add_event(db, ev, "Analysis started", "Analysis engine",
                          "Hash matches intake" if intact else "HASH MISMATCH: file differs from intake",
                          file_hash=now_hash or ev.sha256)
        db.commit()
        try:
            for old in list(ev.findings):
                db.delete(old)
            db.commit()
            art_dir = config.ARTIFACT_DIR / str(ev.id)
            findings, details = _dispatch(ev, path, art_dir, progress)
            if not intact:
                findings.append(F("metadata", "hash_mismatch", "high", "File changed since intake",
                                  "The stored file's SHA-256 no longer matches the hash taken at upload.",
                                  penalty=30))
            if ev.media_type == "image":
                ev.phash = similarity.phash_image(path)[:64]

            # Check KnownManipulated registry
            from .models import KnownManipulated
            for km in db.query(KnownManipulated).all():
                matched = False
                m_type = ""
                if km.sha256 and km.sha256.lower() == ev.sha256.lower():
                    matched = True
                    m_type = "exact SHA-256 match"
                elif km.phash and ev.phash and similarity.hamming(km.phash, ev.phash) <= similarity.PHASH_LIMIT:
                    matched = True
                    m_type = f"perceptual hash match ({similarity.similarity_pct(km.phash, ev.phash)}%)"

                if matched:
                    findings.append(F(
                        "metadata", "known_manipulated_match", "info",
                        "Matches a known manipulated file",
                        f"This file matches a known manipulated record ({km.reason}) via {m_type}. Registered by {km.added_by or 'Examiner'}.",
                        penalty=0
                    ))
                    custody.add_event(
                        db, ev, "Known manipulated match", "Analysis engine",
                        f"Matched known manipulated record #{km.id} ({km.reason}) via {m_type}"
                    )

            for f in findings:
                db.add(Finding(evidence_id=ev.id, category=f.category, check=f.check, severity=f.severity,
                               penalty=f.penalty if f.penalty is not None else
                               scoring.DEFAULT_PENALTY.get(f.severity, 0),
                               title=f.title, detail=f.detail, location=f.loc_json()))
            db.flush()
            ev.score, bd, ev.verdict = scoring.compute(
                [{"category": f.category, "severity": f.severity,
                  "penalty": f.penalty if f.penalty is not None else scoring.DEFAULT_PENALTY.get(f.severity, 0)}
                 for f in findings])
            ev.breakdown, ev.details = json.dumps(bd), json.dumps(details)
            db.commit()
            db.refresh(ev)
            ev.report, ev.report_model = report_mod.template_report(ev, ev.findings), "template"
            ev.status, ev.stage, ev.progress = "done", "Done", 100
            n_checks = len(findings)
            custody.add_event(db, ev, "Analysis completed", "Analysis engine",
                              f"Score {ev.score}/100, {ev.verdict}, {n_checks} checks recorded")
            db.commit()
            activity.log(db, "Analysis engine", "verdict",
                         f"Determined forensic verdict '{ev.verdict}' ({ev.score}/100) for {ev.filename}",
                         ev.case_id, ev.id)
            enqueue_report(ev.id)
        except Exception as exc:  # keep the file; allow re-analyse
            traceback.print_exc()
            ev.status, ev.error, ev.stage = "failed", f"{type(exc).__name__}: {exc}", "Failed"
            db.commit()
    finally:
        db.close()
