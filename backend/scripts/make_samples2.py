"""Synthetic demo files for documents, audio and video (used by tests and the demo seed)."""
import shutil
import subprocess
import sys
import wave
import zipfile
from pathlib import Path

import numpy as np


# ------------------------------------------------------------------ PDF
def make_pdfs(out: Path):
    import pymupdf as fitz
    rows = [("Office chairs", "12", "4,250", "51,000", 300), ("Standing desks", "4", "18,900", "75,600", 320),
            ("Delivery", "1", "2,400", "2,400", 340)]
    doc = fitz.open()
    pg = doc.new_page()
    pg.insert_text((72, 90), "NORTHGATE TRADING CO.", fontname="helv", fontsize=14)
    pg.insert_text((72, 110), "Tax Invoice INV-20418", fontname="helv", fontsize=10)
    for name, q, rate, amt, y in rows:
        for x, t in ((72, name), (330, q), (380, rate), (450, amt)):
            pg.insert_text((x, y), t, fontname="helv", fontsize=10)
    pg.insert_text((380, 380), "Total", fontname="helv", fontsize=10)
    pg.insert_text((450, 380), "1,29,000", fontname="helv", fontsize=10)
    doc.set_metadata({"producer": "ReportLab PDF Library", "creationDate": "D:20260803101500",
                      "modDate": "D:20260803101500"})
    orig = out / "invoice_original.pdf"
    doc.save(str(orig))
    doc.close()
    tam = out / "invoice_tampered.pdf"
    shutil.copy(orig, tam)
    d = fitz.open(str(tam))
    p = d[0]
    for old_y, newtext in ((300, "2,51,000"), (380, "3,29,000")):
        p.draw_rect(fitz.Rect(445, old_y - 11, 520, old_y + 4), color=None, fill=(1, 1, 1))   # white-out
        p.insert_text((450, old_y), newtext, fontname="tiro", fontsize=10)                    # Times: font change
    d.set_metadata({"producer": "iLovePDF", "creationDate": "D:20260803101500", "modDate": "D:20260810101500"})
    d.saveIncr()
    d.close()


# ------------------------------------------------------------------ DOCX
_CT = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
       '<Default Extension="xml" ContentType="application/xml"/>'
       '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
       '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
         '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
_CORE = ('<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
         'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:creator>Ravi Shah</dc:creator>'
         '<cp:lastModifiedBy>Ravi Shah</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">2026-09-01T10:00:00Z</dcterms:created>'
         '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-09-02T10:00:00Z</dcterms:modified></cp:coreProperties>')
_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(out: Path):
    plain = ('<w:p><w:r><w:t>Witness statement of Ravi Shah.</w:t></w:r></w:p>'
             '<w:p><w:r><w:t>On the night in question I did not see the vehicle.</w:t></w:r></w:p>')
    tracked = ('<w:p><w:r><w:t>Witness statement of Ravi Shah.</w:t></w:r></w:p>'
               '<w:p><w:r><w:t xml:space="preserve">On the night in question I </w:t></w:r>'
               '<w:del w:id="1" w:author="Ravi Shah" w:date="2026-09-02T09:00:00Z"><w:r><w:delText>did not see</w:delText></w:r></w:del>'
               '<w:ins w:id="2" w:author="Ravi Shah" w:date="2026-09-02T09:00:00Z"><w:r><w:t>clearly saw</w:t></w:r></w:ins>'
               '<w:r><w:t xml:space="preserve"> the vehicle.</w:t></w:r></w:p>')
    for name, body in (("statement_original.docx", plain), ("statement_tampered.docx", tracked)):
        with zipfile.ZipFile(out / name, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", _CT)
            z.writestr("_rels/.rels", _RELS)
            z.writestr("docProps/core.xml", _CORE)
            z.writestr("word/document.xml",
                       f'<?xml version="1.0" encoding="UTF-8"?><w:document {_NS}><w:body>{body}</w:body></w:document>')


# ------------------------------------------------------------------ audio
SR = 44100


def _write_wav(path: Path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _voice(seconds=6.0, seed=3, noise=0.004):
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * seconds)) / SR
    env = np.clip(np.sin(2 * np.pi * 1.3 * t), 0, 1) ** 0.5
    sig = sum(np.sin(2 * np.pi * 140 * k * t + k) / k for k in range(1, 12)) * 0.12 * env
    return sig + rng.normal(0, noise, len(t))


def make_audio(out: Path):
    _write_wav(out / "voice_human.wav", _voice())
    x = _voice(noise=0.0012)
    spec = np.fft.rfft(x)
    spec[np.fft.rfftfreq(len(x), 1 / SR) > 7000] = 0           # speech-engine bandwidth
    y = np.fft.irfft(spec, len(x))
    y[int(1.2 * SR):int(1.6 * SR)] = 0                          # two cuts to digital silence
    y[int(3.5 * SR):int(3.9 * SR)] = 0
    _write_wav(out / "voice_tts.wav", y)
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / "voice_tts.wav"), "-metadata",
                        "comment=Generated with ElevenLabs text-to-speech", "-c", "copy", str(out / "voice_tts_tagged.wav")],
                       check=False)


# ------------------------------------------------------------------ video
VW, VH, FPS = 320, 240, 25


def _frame(i, scene, rng, noise=True):
    yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
    if scene == "A":
        f = np.stack([120 + 60 * np.sin((xx + 3 * i) / 40), 110 + 50 * np.cos((yy + 2 * i) / 30), 90 + 0 * xx], 2)
    else:
        f = np.stack([200 - 70 * np.cos((xx - 2 * i) / 25), 60 + 40 * np.sin((yy + i) / 15), 150 - 0 * xx], 2)
    if noise:
        f = f + rng.normal(0, 2, f.shape)
    return np.clip(f, 0, 255).astype(np.uint8)


def _encode(frames, path: Path, audio: Path, extra):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
           "-i", "-", "-i", str(audio), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac",
           "-shortest", *extra, str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()


def make_video(out: Path):
    rng = np.random.default_rng(5)
    wav = out / "_a.wav"
    _write_wav(wav, _voice(seconds=6))
    orig = [_frame(i, "A", rng) for i in range(125)]
    _encode(orig, out / "video_original.mp4", wav, ["-metadata", "creation_time=2026-10-10T09:00:00Z"])
    ed = [_frame(i, "A", rng) for i in range(50)]
    b = [_frame(i, "B", rng) for i in range(40)]
    ed += b + [b[-1]] * 30 + [_frame(i, "B", rng) for i in range(40, 60)]      # hard cut, then a frozen stretch
    _encode(ed, out / "video_edited.mp4", wav, ["-metadata", "comment=Edited with CapCut"])
    wav.unlink()


def make(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    make_pdfs(out)
    make_docx(out)
    make_audio(out)
    if shutil.which("ffmpeg"):
        make_video(out)
    return out


if __name__ == "__main__":
    print(make(Path(sys.argv[1] if len(sys.argv) > 1 else "samples")))
