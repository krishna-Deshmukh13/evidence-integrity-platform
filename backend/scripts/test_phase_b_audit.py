import os
import sys
import pathlib

# Set working directory to backend
backend_dir = pathlib.Path(r"C:\Users\krish\.gemini\antigravity\scratch\evidence-integrity-platform\backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import ActivityLog, User, Case, Evidence
from app import auth, llm

client = TestClient(app)

print("=" * 60)
print("RUNNING PHASE B AUTOMATED VERIFICATION")
print("=" * 60)

# Setup admin user token
db = SessionLocal()
admin = db.query(User).filter(User.role == "admin").first()
if not admin:
    print("ERROR: No admin user found in database!")
    sys.exit(1)

token = auth.make_access_token(admin)
client.cookies.set("access_token", token)

# -------------------------------------------------------------
# TEST 1: AI Privacy Toggle
# -------------------------------------------------------------
print("\n[TEST 1] AI Privacy & Air-Gap Mode Toggle...")

# Set LLM to none (Air-gapped)
resp = client.post("/api/settings/llm", json={"provider": "none", "model": "deterministic"})
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
assert resp.json()["provider"] == "none", f"Expected provider none, got {resp.json()}"
assert not llm.enabled(), "llm.enabled() should be False when provider is none"

# Verify complete() raises LLMError and does NOT touch the network
try:
    llm.complete("System test", "User test")
    assert False, "llm.complete() should have raised LLMError in offline mode!"
except llm.LLMError as e:
    print(f"  -> Successfully blocked external AI call: {e}")

# Check test-llm endpoint in offline mode
test_llm_res = client.post("/api/settings/test-llm")
assert test_llm_res.status_code == 200
assert test_llm_res.json()["ok"] is True
assert "Local Deterministic Synthesis Engine" in test_llm_res.json()["message"]
print("  -> Offline health check verified: 100% local deterministic generation active")

# Restore LLM to free_online
resp2 = client.post("/api/settings/llm", json={"provider": "free_online", "model": "openai"})
assert resp2.status_code == 200
assert llm.enabled(), "llm.enabled() should be True after restoring free_online"
print("  -> Restored external AI toggle to free_online successfully")


# -------------------------------------------------------------
# TEST 2: Verify 5 Required Activity Log Events
# -------------------------------------------------------------
print("\n[TEST 2] Verifying the 5 required activity log events...")

# 2.1 Login event
print("  -> Testing 'login' event...")
# Trigger a login
login_res = client.post("/api/auth/login", json={"username": admin.username, "password": "password123"})
# Check activity log for 'login'
login_acts = client.get("/api/activity?action=login").json()
assert any(a["action"] == "login" for a in login_acts), "Expected 'login' in activity log"
print(f"     [PASS] 'login' event verified ({len(login_acts)} entries found)")

# 2.2 Upload event
print("  -> Testing 'upload' event...")
# Upload a valid minimal PDF to case 1
case = db.query(Case).first()
assert case is not None, "No case found"
test_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n115\n%%EOF\n"
files = {"file": ("audit_test_sample.pdf", test_content, "application/pdf")}
upload_res = client.post(f"/api/cases/{case.id}/evidence", files=files)
assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
ev_id = upload_res.json()["id"]

upload_acts = client.get("/api/activity?action=upload").json()
assert any(a["action"] == "upload" and "audit_test_sample.pdf" in a["summary"] for a in upload_acts), "Expected 'upload' in activity log"
print(f"     [PASS] 'upload' event verified (File #{ev_id})")

# 2.3 Verdict event
print("  -> Testing 'verdict' event...")
# Patch review status on the uploaded file
patch_res = client.patch(f"/api/evidence/{ev_id}", json={"review_status": "flagged"})
assert patch_res.status_code == 200, f"Review patch failed: {patch_res.text}"

verdict_acts = client.get("/api/activity?action=verdict").json()
assert any(a["action"] == "verdict" and (f"#{ev_id}" in str(a.get("evidence_id")) or "audit_test_sample.pdf" in a["summary"]) for a in verdict_acts), "Expected 'verdict' in activity log"
print(f"     [PASS] 'verdict' event verified ({len(verdict_acts)} entries found)")

# 2.4 Report export event
print("  -> Testing 'report_export' event...")
# Export Section 63 BSA certificate for evidence
cert_res = client.get(f"/api/evidence/{ev_id}/section63.pdf")
assert cert_res.status_code == 200, f"Section 63 cert export failed: {cert_res.status_code}"

# Also export Draft Charge Sheet
cs_res = client.get(f"/api/intel/chargesheet/{case.id}")
assert cs_res.status_code == 200, f"Chargesheet export failed: {cs_res.status_code}"

export_acts = client.get("/api/activity?action=report_export").json()
assert any(a["action"] == "report_export" for a in export_acts), "Expected 'report_export' in activity log"
print(f"     [PASS] 'report_export' event verified ({len(export_acts)} entries found)")

# 2.5 Role change event
print("  -> Testing 'role_change' event...")
# Find or create a secondary user to change role
target_user = db.query(User).filter(User.id != admin.id).first()
if not target_user:
    u_res = client.post("/api/users", json={"username": "test_investigator", "full_name": "Test Officer", "role": "viewer", "password": "password123"})
    target_user = db.query(User).filter(User.username == "test_investigator").first()

orig_role = target_user.role
new_role = "investigator" if orig_role == "viewer" else "viewer"

patch_user_res = client.patch(f"/api/users/{target_user.id}", json={"role": new_role})
assert patch_user_res.status_code == 200, f"User patch failed: {patch_user_res.text}"

role_acts = client.get("/api/activity?action=role_change").json()
assert any(a["action"] == "role_change" and target_user.username in a["summary"] for a in role_acts), "Expected 'role_change' in activity log"
print(f"     [PASS] 'role_change' event verified ({len(role_acts)} entries found)")

# Restore original role
client.patch(f"/api/users/{target_user.id}", json={"role": orig_role})

# Clean up test evidence file
client.delete(f"/api/evidence/{ev_id}")


# -------------------------------------------------------------
# TEST 3: Confirm Log Protection & API Immutability
# -------------------------------------------------------------
print("\n[TEST 3] Confirming Activity Log cannot be edited or deleted via API...")

# Try PUT /api/activity
put_res = client.put("/api/activity", json={"id": 1, "summary": "Tampered entry"})
print(f"  -> Attempt PUT /api/activity => HTTP {put_res.status_code} ({put_res.status_code in (404, 405)})")
assert put_res.status_code in (404, 405), f"PUT should be rejected, got {put_res.status_code}"

# Try PATCH /api/activity
patch_res = client.patch("/api/activity", json={"id": 1, "summary": "Tampered entry"})
print(f"  -> Attempt PATCH /api/activity => HTTP {patch_res.status_code} ({patch_res.status_code in (404, 405)})")
assert patch_res.status_code in (404, 405), f"PATCH should be rejected, got {patch_res.status_code}"

# Try DELETE /api/activity
del_res = client.delete("/api/activity")
print(f"  -> Attempt DELETE /api/activity => HTTP {del_res.status_code} ({del_res.status_code in (404, 405)})")
assert del_res.status_code in (404, 405), f"DELETE should be rejected, got {del_res.status_code}"

# Try DELETE /api/activity/1
del_item_res = client.delete("/api/activity/1")
print(f"  -> Attempt DELETE /api/activity/1 => HTTP {del_item_res.status_code} ({del_item_res.status_code in (404, 405)})")
assert del_item_res.status_code in (404, 405), f"DELETE /1 should be rejected, got {del_item_res.status_code}"

print("\n" + "=" * 60)
print("ALL PHASE B VERIFICATION CHECKS PASSED PERFECTLY!")
print("=" * 60)
