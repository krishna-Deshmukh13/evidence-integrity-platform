import re
import pathlib

app_dir = pathlib.Path(r"C:\Users\krish\.gemini\antigravity\scratch\evidence-integrity-platform\backend\app")

endpoints = []
for p in list(app_dir.glob("*.py")) + list((app_dir / "routes").glob("*.py")):
    text = p.read_text(encoding="utf-8")
    for m in re.finditer(r'@(?:app|router)\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']', text):
        method = m.group(1).upper()
        route = m.group(2)
        pos = m.end()
        fn_match = re.search(r'def\s+([a-zA-Z0-9_]+)\(([^)]*)\)', text[pos:pos+400])
        sig = fn_match.group(2) if fn_match else ""
        
        role = "UNPROTECTED"
        if 'require_role("admin")' in sig or "require_role('admin')" in sig:
            role = "ADMIN"
        elif 'require_role("investigator")' in sig or "require_role('investigator')" in sig:
            role = "INVESTIGATOR"
        elif "current_user" in sig or "verify_evidence_access" in text[pos:pos+500] or "verify_case_access" in text[pos:pos+500]:
            role = "AUTHENTICATED"
        elif "optional_user" in sig:
            role = "OPTIONAL"
        elif "auth" in route or "setup" in route or "health" in route or "verify" in route or "file" in route:
            role = "PUBLIC_OR_FILE_URL"

        endpoints.append((p.name, method, route, role))

print(f"Total endpoints found: {len(endpoints)}")
for fn, method, route, role in endpoints:
    if role == "UNPROTECTED":
        print(f"  [UNPROTECTED] {method} {route} in {fn}")
    else:
        print(f"  [{role}] {method} {route}")
