"""PDF and DOCX forensics."""
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .common import F, noop_progress

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

CONSUMER_EDITORS = re.compile(r"ilovepdf|smallpdf|sejda|pdfescape|nitro|foxit|pdfelement|wondershare|pdf24|"
                              r"soda pdf|pdfsam|pdf-xchange|pdfill|lightpdf|pdffiller|online2pdf|"
                              r"pdfcandy|docfly|pdf expert|master pdf", re.I)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def analyze(path: Path, art_dir: Path, progress=noop_progress):
    art_dir.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".docx":
        return analyze_docx(path, progress)
    return analyze_pdf(path, art_dir, progress)


# ------------------------------------------------------------------ PDF
def _pdf_date(s):
    m = re.match(r"D:(\d{4})(\d\d)?(\d\d)?(\d\d)?(\d\d)?(\d\d)?", s or "")
    if not m:
        return None
    p = [int(x) if x else d for x, d in zip(m.groups(), (0, 1, 1, 0, 0, 0))]
    try:
        return datetime(*p)
    except ValueError:
        return None


def _iso_date(s):
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _family(name: str) -> str:
    base = name.split("+")[-1].lower()
    fam = re.split(r"[-,_ ]", base)[0]
    return re.sub(r"(ps)?mt$", "", fam)


def _pdf_structure(raw: bytes):
    out = []
    eofs = len(re.findall(rb"%%EOF", raw))
    if b"/Linearized" in raw[:2048]:
        eofs -= 1
    if eofs > 1:
        out.append(F("document", "incremental_updates", "high", f"PDF was saved {eofs} times (incremental updates)",
                     f"The file holds {eofs} %%EOF markers. Each marker closes one save, so the content "
                     "was changed after the file was first created.", penalty=26,
                     location={"kind": "field", "name": "PDF structure: %%EOF markers"}))
    else:
        out.append(F("document", "incremental_updates", "info", "Single revision (no incremental updates)"))
    ends = [int(m.group(3)) + int(m.group(4)) for m in
            re.finditer(rb"/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]", raw)]
    if ends:
        extra = len(raw[max(ends):].strip())
        if extra > 0:
            out.append(F("document", "signature_coverage", "high", "Bytes added after the digital signature",
                         f"The signature covers the file up to byte {max(ends):,}, but {extra:,} further bytes "
                         "follow it: they were added after signing.", penalty=30,
                         location={"kind": "field", "name": "PDF signature byte range"}))
        else:
            out.append(F("document", "signature_coverage", "info", "Digital signature covers the whole file"))
    return out


def _pdf_metadata(doc):
    out, md = [], doc.metadata or {}
    prod = f"{md.get('producer', '')} {md.get('creator', '')}".strip()
    bad = False
    if prod and CONSUMER_EDITORS.search(prod):
        out.append(F("metadata", "pdf_producer", "medium", f"Produced by a consumer PDF editor ({prod})",
                     "The producer / creator fields name a PDF editing tool rather than the original system.",
                     location={"kind": "field", "name": "PDF Info: Producer"}))
        bad = True
    c, m = _pdf_date(md.get("creationDate")), _pdf_date(md.get("modDate"))
    if c and m and (m - c).total_seconds() > 86400:
        out.append(F("metadata", "pdf_dates", "medium", f"Modified {(m - c).total_seconds() / 86400:.1f} days after creation",
                     f"Created {c}, last modified {m}.", location={"kind": "field", "name": "PDF Info: ModDate"}))
        bad = True
    try:
        xmp = doc.get_xml_metadata() or ""
    except Exception:
        xmp = ""
    mx = re.search(r"<xmp:ModifyDate>(.*?)</xmp:ModifyDate>", xmp)
    xm = _iso_date(mx.group(1)) if mx else None
    if xm and m and abs((xm - m).total_seconds()) > 120:
        out.append(F("metadata", "pdf_xmp_mismatch", "medium", "Info dictionary and XMP metadata disagree",
                     f"Info ModDate is {m} but XMP ModifyDate is {xm}: only one of them was updated.",
                     location={"kind": "field", "name": "PDF Info vs XMP"}))
        bad = True
    if not bad:
        out.append(F("metadata", "pdf_metadata", "info", "PDF metadata consistent"))
    return out


def _font_boxes(page):
    spans = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                if sp["text"].strip():
                    spans.append(sp)
    if not spans:
        return []
    chars = Counter()
    for sp in spans:
        chars[_family(sp["font"])] += len(sp["text"].strip())
    page_dom = chars.most_common(1)[0][0]
    rows = []
    for sp in sorted(spans, key=lambda s: s["origin"][1]):
        if rows and abs(rows[-1][0] - sp["origin"][1]) <= 2.0:
            rows[-1][1].append(sp)
        else:
            rows.append([sp["origin"][1], [sp]])
    boxes = []
    for _, row in rows:
        if len(row) < 2:
            continue
        base = [s for s in row if _family(s["font"]) == page_dom]
        if not base:
            continue
        bsize = Counter(round(s["size"], 1) for s in base).most_common(1)[0][0]
        for s in row:
            if _family(s["font"]) != page_dom or abs(s["size"] - bsize) > 0.6:
                boxes.append([round(v, 1) for v in s["bbox"]] + [s["text"].strip()[:30]])
    return boxes


def _hidden_boxes(page):
    pr = page.rect
    whites = []
    try:
        for d in page.get_drawings():
            fill = d.get("fill")
            r = d["rect"]
            if fill and all(c >= 0.97 for c in fill) and r.width * r.height < 0.5 * pr.width * pr.height:
                whites.append((d.get("seqno", 0), r))
        trace = page.get_texttrace()
    except Exception:
        return []
    boxes = []
    for seq, r in whites:
        for t in trace:
            tb = fitz.Rect(t["bbox"])
            text = "".join(chr(c[0]) for c in t.get("chars", [])).strip()
            area = tb.width * tb.height
            if text and t.get("seqno", 0) < seq and area > 0:
                inter = tb & r
                if not inter.is_empty and inter.width * inter.height / area >= 0.6:
                    boxes.append([round(v, 1) for v in tb] + [text[:30]])
    return boxes


def analyze_pdf(path: Path, art_dir: Path, progress):
    raw = path.read_bytes()
    progress("Reading PDF structure", 10)
    findings = _pdf_structure(raw)
    doc = fitz.open(str(path))
    if doc.needs_pass:
        return findings + [F("document", "encrypted", "low", "PDF is password protected; content not checked")], \
               {"pages": doc.page_count}
    findings += _pdf_metadata(doc)
    details = {"pages": doc.page_count, "page_images": [], "flagged_pages": []}
    font_hits, hidden_hits = [], []
    n = min(doc.page_count, 30)
    for i in range(n):
        progress(f"Page {i + 1} of {n}", 20 + int(70 * i / max(n, 1)))
        page = doc[i]
        fb, hb = _font_boxes(page), _hidden_boxes(page)
        if fb:
            font_hits.append({"page": i + 1, "boxes": fb})
        if hb:
            hidden_hits.append({"page": i + 1, "boxes": hb})
        if i < 12:  # render with red boxes (in memory only; the file is never modified)
            for bx in fb:
                page.draw_rect(fitz.Rect(bx[:4]), color=(0.85, 0, 0), width=1.2)
            for bx in hb:
                page.draw_rect(fitz.Rect(bx[:4]), color=(0.9, 0.5, 0), width=1.2)
            name = f"page-{i + 1}.png"
            page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6)).save(str(art_dir / name))
            details["page_images"].append(name)
    if font_hits:
        cnt = sum(len(h["boxes"]) for h in font_hits)
        p0 = font_hits[0]
        findings.append(F("document", "font_forensics", "high", "Font or size changes inside a line",
                          f"{cnt} text item(s) use a different font or size from the rest of their line "
                          "(e.g. " + ", ".join(f"'{b[4]}'" for b in p0["boxes"][:3]) + "), the classic sign of "
                          "a patched amount or name.", penalty=26,
                          location={"kind": "page", "page": p0["page"], "boxes": p0["boxes"], "all": font_hits}))
    else:
        findings.append(F("document", "font_forensics", "info", "Fonts consistent within lines"))
    if hidden_hits:
        cnt = sum(len(h["boxes"]) for h in hidden_hits)
        p0 = hidden_hits[0]
        findings.append(F("document", "hidden_text", "high", "Text covered by a white shape (white-out)",
                          f"{cnt} text item(s) were painted over with a filled white shape; the original "
                          "text is still in the file.", penalty=26,
                          location={"kind": "page", "page": p0["page"], "boxes": p0["boxes"], "all": hidden_hits}))
    else:
        findings.append(F("document", "hidden_text", "info", "No text hidden under shapes"))
    details["flagged_pages"] = sorted({h["page"] for h in font_hits + hidden_hits})
    doc.close()
    return findings, details


# ------------------------------------------------------------------ DOCX
def _dt(s):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def analyze_docx(path: Path, progress):
    findings, details = [], {}
    progress("Reading Word document", 15)
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    if "word/document.xml" not in names:
        return [F("document", "docx", "low", "Not a valid Word document")], {}
    body = ET.fromstring(z.read("word/document.xml"))
    paragraphs = list(body.iter(W + "p"))
    ins, dels = list(body.iter(W + "ins")), list(body.iter(W + "del"))
    authors = sorted({e.get(W + "author", "?") for e in ins + dels})

    def text_of(e, tag):
        return "".join(t.text or "" for t in e.iter(W + tag))

    changed_idx = [i for i, p in enumerate(paragraphs) if any(True for _ in p.iter(W + "ins")) or
                   any(True for _ in p.iter(W + "del"))]
    mixed_idx = []
    for i, p in enumerate(paragraphs):
        fonts = set()
        for r in p.iter(W + "r"):
            rf = r.find(f"{W}rPr/{W}rFonts")
            if rf is not None and "".join(t.text or "" for t in r.iter(W + "t")).strip():
                fonts.add(rf.get(W + "ascii") or rf.get(W + "hAnsi"))
        if len(fonts - {None}) > 1:
            mixed_idx.append(i)
    details["paragraphs"] = [{"i": i, "text": "".join(t.text or "" for t in p.iter()
                                                      if t.tag in (W + "t", W + "delText"))[:300],
                              "tracked": i in changed_idx, "mixed_fonts": i in mixed_idx}
                             for i, p in enumerate(paragraphs[:400])]
    if ins or dels:
        sample = []
        for d in dels[:2]:
            sample.append(f"deleted '{text_of(d, 'delText')[:40]}'")
        for n_ in ins[:2]:
            sample.append(f"inserted '{text_of(n_, 't')[:40]}'")
        dates = sorted(filter(None, (e.get(W + "date") for e in ins + dels)))
        findings.append(F("document", "tracked_changes", "high",
                          f"Tracked changes: {len(ins)} insertion(s), {len(dels)} deletion(s)",
                          f"By {', '.join(authors)}" + (f" ({dates[0][:10]} to {dates[-1][:10]})" if dates else "")
                          + ". " + "; ".join(sample) + ".", penalty=26,
                          location={"kind": "paragraph", "indices": changed_idx[:20], "authors": authors}))
    else:
        findings.append(F("document", "tracked_changes", "info", "No tracked changes"))
    if mixed_idx:
        findings.append(F("document", "mixed_fonts", "medium", "Paragraph mixes fonts",
                          f"{len(mixed_idx)} paragraph(s) contain runs in different fonts, which can show "
                          "edited text.", location={"kind": "paragraph", "indices": mixed_idx[:20]}))
    progress("Checking properties", 60)
    creator = last = created = modified = None
    if "docProps/core.xml" in names:
        core = ET.fromstring(z.read("docProps/core.xml"))
        get = lambda tag: next((e.text for e in core.iter() if e.tag.endswith("}" + tag)), None)
        creator, last = get("creator"), get("lastModifiedBy")
        created, modified = _dt(get("created")), _dt(get("modified"))
        details["properties"] = {"creator": creator, "lastModifiedBy": last,
                                 "created": str(created or ""), "modified": str(modified or "")}
    bad_meta = False
    if authors and last and last not in authors:
        findings.append(F("metadata", "author_mismatch", "medium", "Last saved by someone other than the editor",
                          f"Tracked changes were written by {', '.join(authors)} but the file was last saved by {last}.",
                          location={"kind": "field", "name": "core.xml: lastModifiedBy"}))
        bad_meta = True
    if created and modified and modified < created:
        findings.append(F("metadata", "docx_dates", "medium", "Modified date is before the creation date",
                          f"Created {created}, modified {modified}.",
                          location={"kind": "field", "name": "core.xml: dates"}))
        bad_meta = True
    sessions = 0
    if "word/settings.xml" in names:
        sessions = sum(1 for e in ET.fromstring(z.read("word/settings.xml")).iter(W + "rsid"))
    details["editing_sessions"] = sessions
    if sessions > 40:
        findings.append(F("metadata", "docx_sessions", "low", f"Many editing sessions ({sessions})",
                          "The file has been opened and saved many times."))
        bad_meta = True
    if not bad_meta:
        findings.append(F("metadata", "docx_metadata", "info", "Word properties consistent"))
    return findings, details
