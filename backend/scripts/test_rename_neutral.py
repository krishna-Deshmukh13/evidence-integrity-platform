"""
Test for Phase A Task 2:
Rename 5 demo files to neutral names (file_001.mp4 etc.) and verify
whether verdicts stay identical.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models import Evidence
from app import scoring

db = SessionLocal()

targets = [
    (1, "file_001.pdf"),
    (2, "file_002.wav"),
    (4, "file_003.mp4"),
    (6, "file_004.pdf"),
    (10, "file_005.mp4"),
]

print("=" * 70)
print("PHASE A - TASK 2: NEUTRAL FILENAME RE-VERIFICATION TEST")
print("=" * 70)

results = []

for ev_id, new_name in targets:
    ev = db.query(Evidence).filter(Evidence.id == ev_id).first()
    if not ev:
        print(f"Evidence #{ev_id} not found!")
        continue
    
    old_name = ev.filename
    old_score = ev.score
    old_verdict = ev.verdict
    
    # 1. Update filename to neutral name
    ev.filename = new_name
    db.commit()
    db.refresh(ev)
    
    # 2. Recompute score from analysis findings
    raw_findings = [
        {"category": f.category, "severity": f.severity, "penalty": f.penalty}
        for f in ev.findings
    ]
    recomputed_score, bd, recomputed_verdict = scoring.compute(raw_findings)
    
    stayed_same = (ev.score == old_score) and (ev.verdict == old_verdict) and (recomputed_verdict == old_verdict)
    
    results.append({
        "id": ev.id,
        "old_name": old_name,
        "new_name": new_name,
        "old_score": old_score,
        "new_score": ev.score,
        "old_verdict": old_verdict,
        "new_verdict": ev.verdict,
        "recomputed_score": recomputed_score,
        "recomputed_verdict": recomputed_verdict,
        "stayed_same": stayed_same
    })

for r in results:
    status = "UNCHANGED (STAYED IDENTICAL)" if r["stayed_same"] else "CHANGED"
    print(f"\n[Evidence #{r['id']}]")
    print(f"  Old Filename : {r['old_name']}")
    print(f"  New Filename : {r['new_name']}")
    print(f"  Score        : {r['old_score']}% -> {r['new_score']}% (Recomputed: {r['recomputed_score']}%)")
    print(f"  Verdict      : '{r['old_verdict']}' -> '{r['new_verdict']}' (Recomputed: '{r['recomputed_verdict']}')")
    print(f"  Verdict State: {status}")

print("\n" + "=" * 70)
all_same = all(r["stayed_same"] for r in results)
print(f"SUMMARY: All 5 verdicts stayed identical: {all_same}")
print("=" * 70)

db.close()
