"""PDF, DOCX, audio and video analyzers."""
import shutil

import pytest


def _run(client, path, mime="application/octet-stream"):
    cid = client.post("/api/cases", json={"reference": "S2-" + path.stem, "title": "t"}).json()["id"]
    with open(path, "rb") as fh:
        e = client.post(f"/api/cases/{cid}/evidence", files={"file": (path.name, fh, mime)}).json()
    d = client.get(f"/api/evidence/{e['id']}").json()
    assert d["status"] == "done", d.get("error")
    return d


def _checks(d):
    return {f["check"] for f in d["findings"] if f["severity"] != "info"}


def test_pdf_original_vs_tampered(admin, samples2):
    o = _run(admin, samples2 / "invoice_original.pdf")
    t = _run(admin, samples2 / "invoice_tampered.pdf")
    assert o["score"] >= 80, o["findings"]
    assert t["score"] < 50, (t["score"], t["findings"])
    assert {"incremental_updates", "font_forensics", "hidden_text", "pdf_producer"} <= _checks(t), _checks(t)
    font = next(f for f in t["findings"] if f["check"] == "font_forensics")
    assert font["location"]["kind"] == "page" and len(font["location"]["boxes"]) >= 2
    assert t["details"]["page_images"] == ["page-1.png"] and "page-1.png" in t["artifacts"]
    assert t["breakdown"]["document"] == 45          # capped


def test_docx_tracked_change(admin, samples2):
    o = _run(admin, samples2 / "statement_original.docx")
    t = _run(admin, samples2 / "statement_tampered.docx")
    assert o["score"] == 100
    assert t["score"] == 74 and t["verdict"] == "Needs review", t["findings"]
    f = next(x for x in t["findings"] if x["check"] == "tracked_changes")
    assert "did not see" in f["detail"] and "clearly saw" in f["detail"]
    assert any(p["tracked"] for p in t["details"]["paragraphs"])


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


@needs_ffmpeg
def test_audio_human_vs_tts(admin, samples2):
    h = _run(admin, samples2 / "voice_human.wav")
    t = _run(admin, samples2 / "voice_tts.wav")
    g = _run(admin, samples2 / "voice_tts_tagged.wav")
    assert h["score"] >= 80 and h["details"]["cutoff_hz"] > 15000, h["findings"]
    assert {"digital_silence", "bandwidth"} <= _checks(t), t["findings"]
    assert len(t["details"]["silences"]) == 2 and t["score"] < h["score"] - 20
    assert "tool_tags" in _checks(g) and g["score"] < t["score"]
    assert "spectrogram.png" in t["artifacts"] and len(t["details"]["waveform"]) == 500


@needs_ffmpeg
def test_video_original_vs_edited(admin, samples2):
    o = _run(admin, samples2 / "video_original.mp4")
    e = _run(admin, samples2 / "video_edited.mp4")
    assert o["score"] >= 75 and not o["details"]["cuts"], (o["score"], o["findings"], o["details"]["cuts"])
    assert {"hard_cuts", "frozen_frames", "video_editor"} <= _checks(e), e["findings"]
    assert e["score"] < o["score"] - 20 and e["breakdown"]["container"] == 20
    assert 1.9 <= e["details"]["cuts"][0] <= 2.1
    assert len(e["details"]["frames"]) >= 10
    assert any(f["title"].startswith("Audio track:") for f in e["findings"])
    assert "audio_spectrogram.png" in e["artifacts"]
