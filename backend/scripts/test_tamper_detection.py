"""
Automated Test for Task 8: Merkle / SHA-256 Storage Tamper Detection.

Modifies one byte of a stored evidence file on disk, verifies that the
integrity monitor detects the hash mismatch and flags the file, and restores
the original byte, confirming the chain returns to intact state.
"""

import sys
from pathlib import Path

# Set up paths
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import config, custody
from app.database import SessionLocal
from app.models import Evidence


def run_integrity_test():
    print("=" * 65)
    print("TASK 8: QUICK INTEGRITY TEST - BIT-FLIP STORAGE TAMPER DETECTION")
    print("=" * 65)

    db = SessionLocal()
    try:
        # 1. Pick a stored evidence file
        ev = db.query(Evidence).first()
        assert ev is not None, "No evidence records found in database."
        file_path = config.UPLOAD_DIR / ev.stored_name
        assert file_path.exists(), f"Evidence file {file_path} not found on disk."

        print(f"\n[Step 1] Target Evidence Selected:")
        print(f"  - Evidence ID : #{ev.id}")
        print(f"  - Filename    : {ev.filename}")
        print(f"  - Stored Path : {file_path.name}")
        print(f"  - Intake SHA  : {ev.sha256}")

        # 2. Baseline Check
        res_before = custody.verify_evidence(ev, config.UPLOAD_DIR)
        print(f"\n[Step 2] Baseline Verification (Prior to modification):")
        print(f"  - File OK    : {res_before['file_ok']}")
        print(f"  - Chain OK   : {res_before['chain_ok']}")
        print(f"  - Overall OK : {res_before['ok']}")
        print(f"  - Message    : {res_before['message']}")
        assert res_before["ok"] is True, "Baseline check failed! File is not initially intact."
        assert res_before["file_ok"] is True, "Baseline file hash does not match intake hash."

        # 3. Modify exactly ONE byte
        original_bytes = bytearray(file_path.read_bytes())
        assert len(original_bytes) > 0, "Target file is empty."
        original_byte_val = original_bytes[0]
        # Flip bit 0 of the first byte
        modified_byte_val = original_byte_val ^ 0x01
        original_bytes[0] = modified_byte_val
        file_path.write_bytes(original_bytes)

        tampered_hash = custody.sha256_file(file_path)
        print(f"\n[Step 3] One Byte Modified at Offset 0:")
        print(f"  - Original byte 0x00 : 0x{original_byte_val:02X}")
        print(f"  - Modified byte 0x00 : 0x{modified_byte_val:02X}")
        print(f"  - Tampered Disk SHA  : {tampered_hash}")
        assert tampered_hash != ev.sha256, "Modified file has the same hash as original (impossible)."

        # 4. Check that custody/Merkle monitor DETECTS the alteration
        res_tampered = custody.verify_evidence(ev, config.UPLOAD_DIR)
        print(f"\n[Step 4] Tamper Detection Evaluation:")
        print(f"  - File OK    : {res_tampered['file_ok']} (Expected False)")
        print(f"  - Overall OK : {res_tampered['ok']} (Expected False)")
        print(f"  - Current SHA: {res_tampered['current_hash']}")
        print(f"  - Intake SHA : {res_tampered['intake_hash']}")
        print(f"  - Alert Msg  : {res_tampered['message']}")

        assert res_tampered["ok"] is False, "TEST FAILED: Tampered file was NOT reported as broken!"
        assert res_tampered["file_ok"] is False, "TEST FAILED: file_ok was True for tampered file!"
        print("  -> SUCCESS: Tamper was instantly caught by SHA-256 verification!")

        # 5. Restore original byte
        original_bytes[0] = original_byte_val
        file_path.write_bytes(original_bytes)
        restored_hash = custody.sha256_file(file_path)
        print(f"\n[Step 5] Restoring Original Byte:")
        print(f"  - Restored Disk SHA  : {restored_hash}")
        assert restored_hash == ev.sha256, "Restored hash does not match original intake hash."

        # 6. Verify custody returns to intact
        res_after = custody.verify_evidence(ev, config.UPLOAD_DIR)
        print(f"\n[Step 6] Post-Restoration Verification:")
        print(f"  - File OK    : {res_after['file_ok']} (Expected True)")
        print(f"  - Chain OK   : {res_after['chain_ok']} (Expected True)")
        print(f"  - Overall OK : {res_after['ok']} (Expected True)")
        print(f"  - Message    : {res_after['message']}")

        assert res_after["ok"] is True, "TEST FAILED: File did not return to intact state after restoration!"
        print("\n" + "=" * 65)
        print("RESULT: ALL TASK 8 TAMPER DETECTION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    run_integrity_test()
