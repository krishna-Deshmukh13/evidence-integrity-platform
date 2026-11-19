"""Reports (template + LLM), PDF export, Ask, compare, similar images, new endpoints are protected."""
import io

import httpx
import pymupdf
import pytest

from app import llm
from app.database import SessionLocal
from app.models import ActivityLog
from tests.conftest import login, make_user

GOOD = ("## Summary\nA short summary.\n\n## Key findings\n- A finding.\n\n## Consistent with an original\n- None.\n\n"
        "## Recommended next steps\n- Check it.\n\n## Limitation\nIndicators only.")


def _case(c, ref="CR-S3"):
    return c.post("/api/cases", json={"reference": ref, "title": "Stage 3"}).json()["id"]


def _up(c, cid, path, name=None):
    with open(path, "rb") as fh:
        e = c.post(f"/api/cases/{cid}/evidence", files={"file": (name or path.name, fh, "image/jpeg")}).json()
    return e["id"]


def _text(pdf_bytes):
    d = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(p.get_text() for p in d), d.page_count


def test_new_endpoints_need_login(client):
    for path in ("/api/llm/status", "/api/compare?a=1&b=2", "/api/evidence/1/similar", "/api/evidence/1/chat",
                 "/api/evidence/1/report.pdf", "/api/cases/1/report.pdf"):
        assert client.get(path).status_code == 401, path


def test_ai_detector_degrades_gracefully_without_torch(admin, samples):
    try:
        import torch  # noqa: F401
        pytest.skip("torch is installed here")
    except ImportError:
        pass
    d = admin.get(f"/api/evidence/{_up(admin, _case(admin), samples / 'photo_original.jpg')}").json()
    f = next(x for x in d["findings"] if x["check"] == "ai_image")
    assert d["status"] == "done" and f["severity"] == "info" and "not installed" in f["title"]
    assert d["score"] >= 80


def test_report_template_then_llm_rewrite(admin, samples, monkeypatch):
    eid = _up(admin, _case(admin), samples / "photo_tampered.jpg")
    d = admin.get(f"/api/evidence/{eid}").json()
    assert d["report_model"] == "template" and "## Key findings" in d["report"] and "Cloned region" in d["report"]
    assert "(from (" in d["report"]                      # exact location quoted
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "my-model")
    seen = {}

    def fake(url, headers=None, json=None, timeout=None):
        seen["body"] = json
        return httpx.Response(200, json={"choices": [{"message": {"content": GOOD}}]})

    monkeypatch.setattr(httpx, "post", fake)
    assert admin.post(f"/api/evidence/{eid}/rewrite-report").json()["queued"] is True
    d = admin.get(f"/api/evidence/{eid}").json()
    assert d["report_model"] == "my-model" and d["report"].startswith("## Summary\nA short summary")
    sent = str(seen["body"])                              # only structured findings are sent, never the file
    assert "Cloned region" in sent and "photo_tampered.jpg" in sent and "never say that a file is" in sent.lower()
    # a model answer without the required sections is rejected -> template kept
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"choices": [{"message": {"content": "just chatting"}}]}))
    admin.post(f"/api/evidence/{eid}/rewrite-report")
    assert admin.get(f"/api/evidence/{eid}").json()["report_model"] == "my-model"     # unchanged
    # offline model -> upload still gets a template report
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    e2 = _up(admin, _case(admin, "CR-S3b"), samples / "photo_original.jpg")
    assert admin.get(f"/api/evidence/{e2}").json()["report_model"] == "template"


def test_evidence_pdf_and_custody(admin, samples):
    eid = _up(admin, _case(admin), samples / "photo_tampered.jpg")
    r = admin.get(f"/api/evidence/{eid}/report.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    txt, pages = _text(r.content)
    for want in ("photo_tampered.jpg", "Chain of custody", "Cloned region detected", "Key images", "SHA-256"):
        assert want in txt, want
    d = admin.get(f"/api/evidence/{eid}").json()
    assert d["custody"][-1]["action"] == "Report exported"
    assert admin.post(f"/api/evidence/{eid}/verify").json()["ok"]          # chain still valid after export events


def test_case_bundle(admin, samples):
    cid = _case(admin)
    a = _up(admin, cid, samples / "photo_original.jpg")
    b = _up(admin, cid, samples / "photo_tampered.jpg")
    admin.patch(f"/api/evidence/{b}", json={"review_status": "flagged", "tags": ["cctv"]})
    admin.post(f"/api/evidence/{b}/notes", json={"body": "jacket pasted"})
    r = admin.get(f"/api/cases/{cid}/report.pdf")
    assert r.status_code == 200
    txt, pages = _text(r.content)
    assert "Case bundle" in txt and "Evidence index" in txt and "CR-S3" in txt and pages >= 4
    assert "photo_original.jpg" in txt and "jacket pasted" in txt and "Flagged" in txt
    assert admin.get(f"/api/evidence/{a}").json()["custody"][-1]["action"] == "Case bundle exported"
    empty = _case(admin, "EMPTY")
    assert admin.get(f"/api/cases/{empty}/report.pdf").status_code == 409


def test_ask_rules_private_and_unlogged(admin, samples):
    eid = _up(admin, _case(admin), samples / "photo_tampered.jpg")
    make_user(admin, "kavya", "viewer")
    r = admin.post(f"/api/evidence/{eid}/chat", json={"question": "Why did it get this score?"}).json()
    assert r["role"] == "assistant" and r["source"] == "rules" and "32/100" in r["content"]
    assert "Cloned region" in r["content"]
    loc = admin.post(f"/api/evidence/{eid}/chat", json={"question": "Where is the edit?"}).json()["content"]
    assert "where: from (" in loc
    cust = admin.post(f"/api/evidence/{eid}/chat", json={"question": "Who handled this? custody"}).json()["content"]
    assert "Received" in cust and "Analysis completed" in cust
    assert len(admin.get(f"/api/evidence/{eid}/chat").json()) == 6
    acts = [a["summary"] for a in admin.get("/api/activity").json() if a["action"] == "ask"]
    assert acts and not any("score" in s.lower() for s in acts)           # only that a question was asked
    admin.cookies.clear()
    login(admin, "kavya")
    assert admin.get(f"/api/evidence/{eid}/chat").json() == []             # another user cannot see it
    admin.cookies.clear()
    login(admin, "meera")
    assert admin.delete(f"/api/evidence/{eid}/chat").status_code == 200
    assert admin.get(f"/api/evidence/{eid}/chat").json() == []


def test_ask_uses_llm_when_available(admin, samples, monkeypatch):
    eid = _up(admin, _case(admin), samples / "photo_original.jpg")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "k")
    sent = {}

    def fake(url, headers=None, json=None, timeout=None):
        sent["u"] = json["messages"][1]["content"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "Model answer"}}]})

    monkeypatch.setattr(httpx, "post", fake)
    r = admin.post(f"/api/evidence/{eid}/chat", json={"question": "Summarise"}).json()
    assert r["content"] == "Model answer" and r["source"] == llm.settings()["model"]
    assert "CONTEXT" in sent["u"] and "photo_original.jpg" in sent["u"] and "QUESTION" in sent["u"]
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("x")))
    assert admin.post(f"/api/evidence/{eid}/chat", json={"question": "score?"}).json()["source"] == "rules"


def test_similar_and_compare(admin, samples):
    cid = _case(admin)
    o = _up(admin, cid, samples / "photo_original.jpg")
    t = _up(admin, cid, samples / "photo_tampered.jpg")
    c2 = _case(admin, "CR-OTHER")
    dup = _up(admin, c2, samples / "photo_original.jpg", "copy_of_original.jpg")
    s = admin.get(f"/api/evidence/{o}/similar").json()
    assert [x["id"] for x in s["exact"]] == [dup] and s["exact"][0]["same_case"] is False
    assert t in [x["id"] for x in s["near"]] and s["near"][0]["similarity"] >= 75
    cmp_ = admin.get(f"/api/compare?a={o}&b={t}").json()
    assert cmp_["same_file"] is False and cmp_["score_change"] < -50
    assert cmp_["visual_similarity"] is not None and cmp_["pixels_changed_pct"] > 0 and cmp_["diff_boxes"]
    assert any("Software" in m["field"] or m["field"] == "131" for m in cmp_["metadata_diffs"]) or cmp_["metadata_diffs"]
    assert any(c["check"] == "copy_move" and c["a"]["severity"] == "info" and c["b"]["severity"] == "high"
               for c in cmp_["check_diffs"])
    img = admin.get(cmp_["diff_image"])
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    assert admin.get(f"/api/compare?a={o}&b={dup}").json()["same_file"] is True
    assert any(a["action"] == "compare" for a in admin.get("/api/activity").json())


def test_llm_status_endpoint(admin):
    assert admin.get("/api/llm/status").json()["provider"] in llm.PROVIDERS
