"""PDF export with ReportLab: per-file report, case bundle, and Section 63 BSA 2023 certificate with signing & verification QR."""
import io
import json
import os
from pathlib import Path
import re
import uuid
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from PIL import Image as PILImage
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import config, signer
from .analyzers.common import F

# ---------------------------------------------------------------------------
# Font Management (Nirmala for Hindi / Marathi support on Windows / Linux)
# ---------------------------------------------------------------------------
_FONTS_REGISTERED = False
HAS_NIRMALA = False


def ensure_fonts():
    global _FONTS_REGISTERED, HAS_NIRMALA
    if _FONTS_REGISTERED:
        return
    # Check Windows font locations
    candidates = [
        "C:/Windows/Fonts/Nirmala.ttc",
        "C:/Windows/Fonts/nirmala.ttc",
        "/usr/share/fonts/truetype/nirmala/Nirmala.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                sub_idx = 0 if p.endswith(".ttc") else None
                if sub_idx is not None:
                    pdfmetrics.registerFont(TTFont("Nirmala", p, subfontIndex=sub_idx))
                else:
                    pdfmetrics.registerFont(TTFont("Nirmala", p))
                pdfmetrics.registerFontFamily("Nirmala", normal="Nirmala", bold="Nirmala", italic="Nirmala", boldItalic="Nirmala")
                HAS_NIRMALA = True
                break
            except Exception:
                pass
    _FONTS_REGISTERED = True


I18N = {
    "en": {
        "title": "Evidence Integrity Report",
        "case": "Case",
        "type": "Type",
        "size": "Size",
        "received": "Received",
        "uploaded_by": "Uploaded by",
        "sha256": "SHA-256",
        "review_status": "Review status",
        "score_integrity": "Evidence Integrity Score",
        "score_breakdown": "Score breakdown (points lost)",
        "report_heading": "Report",
        "written_by": "Written by",
        "findings_heading": "Findings",
        "severity": "Severity",
        "finding": "Finding",
        "where": "Where",
        "penalty": "Penalty",
        "key_images": "Key images",
        "custody_heading": "Chain of custody",
        "action": "Action",
        "actor_note": "Actor / note",
        "time": "Time",
        "event_hash": "Event hash",
        "examiner_review": "Examiner review",
        "status": "Status",
        "tags": "Tags",
        "no_notes": "No notes.",
        "disclaimer": "This is a decision-support tool. The final opinion must be given by a qualified forensic examiner.",
        "case_bundle": "Case bundle",
        "investigator": "Investigator",
        "generated": "Generated",
        "evidence_index": "Evidence index",
        "file": "File",
        "score": "Score",
        "verdict": "Verdict",
        "review": "Review",
        "case_intel_summary": "Case Intelligence Summary",
        "model_engine": "Model engine",
        "verified_sec": "Official Forensic Report Verification",
        "verification_token": "Document Verification Token",
        "verify_instructions": "Scan QR code or enter hash/token at /verify to validate authenticity without exposing evidence content.",
        "signer_fp_label": "Signer Certificate Fingerprint",
        "sec63_title": "CERTIFICATE UNDER SECTION 63 OF THE BHARATIYA SAKSHYA ADHINIYAM (BSA), 2023 (FORMERLY SECTION 65B, INDIAN EVIDENCE ACT)",
        "sec63_subtitle": "(Conditions of Admissibility of Electronic Records in Court / Legal Proceedings)",
        "sec63_draft_warning": "DRAFT CERTIFICATE — FOR LEGAL REVIEW AND OFFICIAL EXECUTION BY AUTHORIZED EXAMINER ONLY",
        "sec63_decl_heading": "STATUTORY DECLARATION UNDER SECTION 63(2) & 63(4)",
        "sec63_sig_block": "Execution and Signature of Declarant / Authorized Officer",
    },
    "hi": {
        "title": "साक्ष्य अखंडता रिपोर्ट",
        "case": "मामला (Case)",
        "type": "प्रकार",
        "size": "आकार",
        "received": "प्राप्त हुआ",
        "uploaded_by": "अपलोडकर्ता",
        "sha256": "SHA-256",
        "review_status": "समीक्षा स्थिति",
        "score_integrity": "साक्ष्य अखंडता स्कोर",
        "score_breakdown": "स्कोर विवरण (अंक कटौती)",
        "report_heading": "विश्लेषण रिपोर्ट",
        "written_by": "द्वारा लिखित",
        "findings_heading": "तकनीकी निष्कर्ष",
        "severity": "गंभीरता",
        "finding": "निष्कर्ष",
        "where": "स्थान",
        "penalty": "अंक कटौती",
        "key_images": "मुख्य छवियां",
        "custody_heading": "अभिरक्षा श्रृंखला (Chain of Custody)",
        "action": "कार्रवाई",
        "actor_note": "कर्ता / टिप्पणी",
        "time": "समय",
        "event_hash": "इवेंट हैश",
        "examiner_review": "परीक्षक समीक्षा",
        "status": "स्थिति",
        "tags": "टैग",
        "no_notes": "कोई टिप्पणी नहीं।",
        "disclaimer": "यह मंच तकनीकी संकेतक प्रदान करता है। यह साक्ष्य की कानूनी स्वीकार्यता तय नहीं करता है और उच्च स्कोर फ़ाइल के पूरी तरह से प्रामाणिक होने का प्रमाण नहीं है। प्रशिक्षित परीक्षक ही अंतिम निर्णय लेता है।",
        "case_bundle": "केस बंडल",
        "investigator": "जांच अधिकारी",
        "generated": "तैयार किया गया",
        "evidence_index": "साक्ष्य अनुक्रमणिका",
        "file": "फ़ाइल",
        "score": "स्कोर",
        "verdict": "निर्णय",
        "review": "समीक्षा",
        "case_intel_summary": "केस इंटेलिजेंस सारांश",
        "model_engine": "मॉडल इंजन",
        "verified_sec": "आधिकारिक फोरेंसिक रिपोर्ट सत्यापन",
        "verification_token": "दस्तावेज़ सत्यापन टोकन",
        "verify_instructions": "साक्ष्य सामग्री उजागर किए बिना प्रामाणिकता की पुष्टि के लिए क्यूआर कोड स्कैन करें या /verify पर हैश/टोकन दर्ज करें।",
        "signer_fp_label": "हस्ताक्षरकर्ता प्रमाणपत्र फिंगरप्रिंट",
        "sec63_title": "भारतीय साक्ष्य अधिनियम, 2023 की धारा 63 के तहत प्रमाण पत्र",
        "sec63_subtitle": "(न्यायिक कार्यवाहियों में इलेक्ट्रॉनिक अभिलेखों की ग्राह्यता की शर्तें)",
        "sec63_draft_warning": "प्रारूप प्रमाण पत्र — केवल अधिकृत परीक्षक/अधिकारी द्वारा कानूनी समीक्षा और निष्पादन हेतु",
        "sec63_decl_heading": "धारा 63(2) एवं 63(4) के तहत वैधानिक घोषणा",
        "sec63_sig_block": "घोषणाकर्ता / अधिकृत अधिकारी के हस्ताक्षर एवं मुहर",
    },
    "mr": {
        "title": "पुरावा अखंडता अहवाल",
        "case": "खटला (Case)",
        "type": "प्रकार",
        "size": "आकार",
        "received": "प्राप्त झाले",
        "uploaded_by": "अपलोडकर्ता",
        "sha256": "SHA-256",
        "review_status": "पुनरावलोकन स्थिती",
        "score_integrity": "पुरावा अखंडता गुण",
        "score_breakdown": "गुण तपशील (गुण कपात)",
        "report_heading": "विश्लेषण अहवाल",
        "written_by": "द्वारे लिखित",
        "findings_heading": "तांत्रिक निष्कर्ष",
        "severity": "तीव्रता",
        "finding": "निष्कर्ष",
        "where": "स्थान",
        "penalty": "गुण वजावट",
        "key_images": "मुख्य प्रतिमा",
        "custody_heading": "ताबा साखळी (Chain of Custody)",
        "action": "कृती",
        "actor_note": "कर्ता / टीप",
        "time": "वेळ",
        "event_hash": "इव्हेंट हॅश",
        "examiner_review": "परीक्षक पुनरावलोकन",
        "status": "स्थिती",
        "tags": "टॅग्ज",
        "no_notes": "कोणतीही टीप नाही.",
        "disclaimer": "हे व्यासपीठ तांत्रिक निर्देशक प्रदान करते. हे पुराव्याची कायदेशीर स्वीकार्यता ठरवत नाही आणि उच्च गुण फाईल अस्सल असल्याचा पुरावा नाही. प्रशिक्षित परीक्षक अंतिम निर्णय घेतात.",
        "case_bundle": "खटला बंडल",
        "investigator": "तपास अधिकारी",
        "generated": "तयार केले",
        "evidence_index": "पुरावा अनुक्रमणिका",
        "file": "फाईल",
        "score": "गुण",
        "verdict": "निकाल",
        "review": "पुनरावलोकन",
        "case_intel_summary": "खटला बुद्धिमत्ता सारांश",
        "model_engine": "मॉडेल इंजिन",
        "verified_sec": "अधिकृत फॉरेन्सिक अहवाल पडताळणी",
        "verification_token": "दस्तऐवज पडताळणी टोकन",
        "verify_instructions": "पुरावा सामग्री उघड न करता सत्यता पडताळण्यासाठी क्यूआर कोड स्कॅन करा किंवा /verify वर हॅश/टोकन प्रविष्ट करा.",
        "signer_fp_label": "स्वाक्षरीकर्ता प्रमाणपत्र फिंगरप्रिंट",
        "sec63_title": "भारतीय साक्ष अधिनियम, २०२३ च्या कलम ६३ अन्वये प्रमाणपत्र",
        "sec63_subtitle": "(न्यायिक प्रक्रियेत इलेक्ट्रॉनिक नोंदींच्या स्वीकार्यतेच्या अटी)",
        "sec63_draft_warning": "मसुदा प्रमाणपत्र — केवळ अधिकृत परीक्षक/अधिकाऱ्याद्वारे कायदेशीर पुनरावलोकन आणि स्वाक्षरीसाठी",
        "sec63_decl_heading": "कलम ६३(२) आणि ६३(४) अन्वये वैधानिक घोषणा",
        "sec63_sig_block": "घोषणाकर्ता / अधिकृत अधिकाऱ्याची स्वाक्षरी आणि शिक्का",
    },
}


def t(key: str, lang: str = "en") -> str:
    lang_dict = I18N.get(lang, I18N["en"])
    return lang_dict.get(key, I18N["en"].get(key, key))


def get_styles(lang: str = "en"):
    ensure_fonts()
    fn = "Nirmala" if (lang in ("hi", "mr") and HAS_NIRMALA) else "Helvetica"
    fn_bold = "Nirmala" if (lang in ("hi", "mr") and HAS_NIRMALA) else "Helvetica-Bold"
    ss = getSampleStyleSheet()
    return {
        "H1": ParagraphStyle("H1", fontName=fn_bold, fontSize=18, leading=22, spaceAfter=6),
        "H2": ParagraphStyle("H2", fontName=fn_bold, fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=4, keepWithNext=1),
        "BODY": ParagraphStyle("B", fontName=fn, fontSize=9.5, leading=13),
        "SMALL": ParagraphStyle("S", fontName=fn, fontSize=8, leading=10, textColor=colors.HexColor("#555555")),
        "SCORE": ParagraphStyle("SC", fontName=fn_bold, fontSize=11, leading=30, spaceBefore=4, spaceAfter=6),
        "CELL": ParagraphStyle("C", fontName=fn, fontSize=8, leading=10),
        "CELL_BOLD": ParagraphStyle("CB", fontName=fn_bold, fontSize=8, leading=10),
    }


VERDICT_COL = {"Consistent": "#15803d", "Needs review": "#b45309", "Likely manipulated": "#b91c1c"}
SEV_COL = {"high": "#b91c1c", "medium": "#b45309", "low": "#6b7280", "info": "#15803d"}
STATUS = {"not_reviewed": "Not reviewed", "reviewed": "Reviewed", "flagged": "Flagged", "cleared": "Cleared"}


def _md(text: str, sty: dict):
    out = []
    for line in (text or "").splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(line))
        if line.startswith("## "):
            out.append(Paragraph(escape(line[3:]), sty["H2"]))
        elif line.lstrip().startswith("- "):
            out.append(Paragraph(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(line.lstrip()[2:])), sty["BODY"],
                                 bulletText="\u2022"))
        else:
            out.append(Paragraph(safe, sty["BODY"]))
    return out


def _img(path: Path, max_w=170 * mm, max_h=105 * mm):
    try:
        w, h = PILImage.open(path).size
    except Exception:
        return None
    k = min(max_w / w, max_h / h, 1e9)
    return Image(str(path), width=w * k, height=h * k)


def _where(f) -> str:
    try:
        return F(f.category, f.check, f.severity, f.title,
                 location=json.loads(f.location) if f.location else None).where()
    except Exception:
        return ""


def _key_images(ev):
    d = config.ARTIFACT_DIR / str(ev.id)
    det = ev.get_details()
    names = {"image": [("original.jpg", "Original (analysis size)"), ("ela.png", "Error level analysis"),
                       ("ai_heatmap.png", "AI heatmap (Grad-CAM)"), ("clone.png", "Clone map"),
                       ("noise.png", "Noise map")],
             "audio": [("spectrogram.png", "Spectrogram")],
             "video": [("ai_heatmap.png", "AI heatmap (worst frame)"), ("audio_spectrogram.png", "Audio spectrogram")],
             "document": []}[ev.media_type]
    out = [(d / n, cap) for n, cap in names if (d / n).exists()]
    if ev.media_type == "document":
        pages = det.get("flagged_pages") or [1]
        for pg in pages[:3]:
            if (d / f"page-{pg}.png").exists():
                out.append((d / f"page-{pg}.png", f"Page {pg} (flagged areas boxed)"))
    return out


def _qr_flowable(token: str, size_mm: float = 26.0):
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(f"http://localhost:5173/verify?h={token}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size_mm * mm, height=size_mm * mm)


def _verification_box(doc_token: str, signer_fp: str, lang: str, sty: dict):
    qr_img = _qr_flowable(doc_token, size_mm=26)
    fp_short = signer_fp or "PLATFORM-SELF-SIGNED"
    t_data = [
        [
            qr_img,
            [
                Paragraph(f"<b>{t('verified_sec', lang)}</b>", sty["BODY"]),
                Spacer(1, 1.5 * mm),
                Paragraph(f"<b>{t('verification_token', lang)}:</b> <font name='Helvetica'>{doc_token}</font>", sty["SMALL"]),
                Paragraph(f"<b>{t('signer_fp_label', lang)}:</b> <font name='Helvetica' size='7'>{fp_short}</font>", sty["SMALL"]),
                Spacer(1, 1.5 * mm),
                Paragraph(t("verify_instructions", lang), sty["SMALL"]),
            ]
        ]
    ]
    vt = Table(t_data, colWidths=[30 * mm, 140 * mm])
    vt.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#3b82f6")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([Spacer(1, 6), vt])


def evidence_story(ev, case=None, extras=False, lang: str = "en", doc_token: str = None):
    sty = get_styles(lang)
    s = []
    logo_path = Path(__file__).resolve().parent / "assets" / "logo-mark.png"
    if logo_path.exists():
        logo_img = Image(str(logo_path), width=10 * mm, height=10 * mm)
        hdr_table = Table([[logo_img, Paragraph("<b>Evidence Integrity Platform</b><br/><font size='8' color='#64748b'>Digital evidence, verified</font>", sty["SMALL"])]],
                          colWidths=[13 * mm, 161 * mm])
        hdr_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        s.append(hdr_table)
        s.append(Spacer(1, 2 * mm))
    s.append(Paragraph(escape(ev.filename), sty["H1"]))
    col = VERDICT_COL.get(ev.verdict, "#333333")
    s.append(Paragraph(f'<font size="22" color="{col}"><b>{ev.score if ev.score is not None else "-"}</b></font>'
                       f' / 100 &nbsp; <font color="{col}"><b>{escape(ev.verdict or "Not analysed")}</b></font>'
                       f" &nbsp; {t('score_integrity', lang)}", sty["SCORE"]))
    meta = [
        [t("case", lang), f"{case.reference} {case.title}" if case else ""],
        [t("type", lang), ev.media_type],
        [t("size", lang), f"{ev.size:,} bytes"],
        [t("received", lang), ev.received_at],
        [t("uploaded_by", lang), ev.uploaded_by],
        [t("sha256", lang), ev.sha256],
        [t("review_status", lang), STATUS.get(ev.review_status, ev.review_status)],
    ]
    t_table = Table([[Paragraph(a, sty["CELL"]), Paragraph(escape(str(b)), sty["CELL"])] for a, b in meta],
                    colWidths=[35 * mm, 135 * mm])
    t_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                                 ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f4f5"))]))
    s += [Spacer(1, 6), t_table]

    bd = ev.get_breakdown()
    if bd:
        s.append(Paragraph(f"{t('score_breakdown', lang)}: " + ", ".join(f"{k} -{v}" for k, v in bd.items()), sty["SMALL"]))

    s.append(Paragraph(t("report_heading", lang), sty["H2"]))
    s += _md(ev.report or "", sty)
    s.append(Paragraph(f"{t('written_by', lang)}: {escape(ev.report_model or 'template')}", sty["SMALL"]))

    s.append(Paragraph(t("findings_heading", lang), sty["H2"]))
    rows = [[Paragraph(f"<b>{t('severity', lang)}</b>", sty["CELL"]),
             Paragraph(f"<b>{t('finding', lang)}</b>", sty["CELL"]),
             Paragraph(f"<b>{t('where', lang)}</b>", sty["CELL"]),
             Paragraph(f"<b>{t('penalty', lang)}</b>", sty["CELL"])]]
    for f in ev.findings:
        rows.append([Paragraph(f'<font color="{SEV_COL.get(f.severity, "#333")}"><b>{f.severity.upper()}</b></font>', sty["CELL"]),
                     Paragraph(f"<b>{escape(f.title)}</b><br/>{escape(f.detail or '')}", sty["CELL"]),
                     Paragraph(escape(_where(f)), sty["CELL"]),
                     Paragraph(str(f.penalty or 0), sty["CELL"])])
    ft = Table(rows, colWidths=[20 * mm, 103 * mm, 35 * mm, 12 * mm], repeatRows=1)
    ft.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f4f5")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s.append(ft)

    imgs = _key_images(ev)
    if imgs:
        s.append(Paragraph(t("key_images", lang), sty["H2"]))
        for p, cap in imgs:
            im = _img(p)
            if im:
                s.append(KeepTogether([im, Paragraph(escape(cap), sty["SMALL"]), Spacer(1, 6)]))

    s.append(Paragraph(t("custody_heading", lang), sty["H2"]))
    rows = [[Paragraph(f"<b>{t(h, lang)}</b>", sty["CELL"]) for h in ("#", "action", "actor_note", "time", "event_hash")]]
    for c in ev.custody:
        rows.append([Paragraph(str(c.seq), sty["CELL"]),
                     Paragraph(escape(c.action), sty["CELL"]),
                     Paragraph(escape(f"{c.actor}. {c.note}"), sty["CELL"]),
                     Paragraph(c.at[:19].replace("T", " "), sty["CELL"]),
                     Paragraph(c.event_hash[:14] + "...", sty["CELL"])])
    ct = Table(rows, colWidths=[8 * mm, 30 * mm, 76 * mm, 30 * mm, 26 * mm], repeatRows=1)
    ct.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f4f5")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s.append(ct)

    if extras:
        s.append(Paragraph(t("examiner_review", lang), sty["H2"]))
        s.append(Paragraph(f"{t('status', lang)}: {STATUS.get(ev.review_status, ev.review_status)}. "
                           f"{t('tags', lang)}: {escape(', '.join(ev.get_tags()) or 'none')}.", sty["BODY"]))
        for n in ev.notes:
            s.append(Paragraph(f"<b>{escape(n.author or '')}</b> ({n.created_at[:16].replace('T', ' ')}): "
                               f"{escape(n.body or '')}", sty["BODY"]))
        if not ev.notes:
            s.append(Paragraph(t("no_notes", lang), sty["SMALL"]))

    s.append(Spacer(1, 8))
    s.append(Paragraph(t("disclaimer", lang), sty["SMALL"]))

    if doc_token:
        signer_fp = signer.get_signer_fingerprint()
        s.append(_verification_box(doc_token, signer_fp, lang, sty))

    return s


def _build(story, title: str, lang: str = "en") -> bytes:
    buf = io.BytesIO()
    signer_fp = signer.get_signer_fingerprint()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#777777"))
        fp_short = (signer_fp[:20] + "...") if signer_fp else "Self-Signed Platform Key"
        canvas.drawString(18 * mm, 10 * mm, f"Evidence Integrity Platform | {title[:40]} | Signer: {fp_short}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=18 * mm, title=title).build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def evidence_pdf(ev, case=None, lang: str = "en", doc_token: str = None) -> bytes:
    if not doc_token:
        doc_token = uuid.uuid4().hex
    story = evidence_story(ev, case, extras=True, lang=lang, doc_token=doc_token)
    return _build(story, ev.filename, lang=lang)


def case_bundle_pdf(case, evidence, summary_text: str = "", summary_model: str = "", lang: str = "en", doc_token: str = None) -> bytes:
    if not doc_token:
        doc_token = uuid.uuid4().hex
    sty = get_styles(lang)
    done = [e for e in evidence if e.status == "done"]
    s = [
        Spacer(1, 40 * mm),
        Paragraph(t("case_bundle", lang), ParagraphStyle("t", parent=sty["H1"], fontSize=26, leading=30)),
        Paragraph(escape(f"{case.reference}: {case.title}"), sty["H2"]),
        Paragraph(f"{t('investigator', lang)}: {escape(case.investigator or '')}", sty["BODY"]),
        Paragraph(f"{t('generated', lang)}: " + datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"), sty["BODY"]),
        Paragraph(f"{len(evidence)} file(s), {len(done)} analysed; "
                  f"{sum(1 for e in done if e.verdict == 'Likely manipulated')} likely manipulated, "
                  f"{sum(1 for e in done if e.verdict == 'Needs review')} need review, "
                  f"{sum(1 for e in done if e.verdict == 'Consistent')} consistent.", sty["BODY"]),
        PageBreak(),
        Paragraph(t("evidence_index", lang), sty["H1"]),
    ]
    rows = [[Paragraph(f"<b>{t(h, lang)}</b>", sty["CELL"]) for h in ("#", "file", "type", "score", "verdict", "review")]]
    for i, e in enumerate(sorted(done, key=lambda x: x.score if x.score is not None else 0), 1):
        rows.append([
            Paragraph(str(i), sty["CELL"]),
            Paragraph(escape(e.filename), sty["CELL"]),
            Paragraph(e.media_type, sty["CELL"]),
            Paragraph(str(e.score), sty["CELL"]),
            Paragraph(escape(e.verdict or ""), sty["CELL"]),
            Paragraph(STATUS.get(e.review_status, ""), sty["CELL"]),
        ])
    t_table = Table(rows, colWidths=[8 * mm, 70 * mm, 20 * mm, 14 * mm, 32 * mm, 26 * mm], repeatRows=1)
    t_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                                 ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f4f5"))]))
    s.append(t_table)

    if summary_text:
        s.append(PageBreak())
        s.append(Paragraph(t("case_intel_summary", lang), sty["H1"]))
        if summary_model:
            s.append(Paragraph(f"{t('model_engine', lang)}: {escape(summary_model)}", sty["SMALL"]))
            s.append(Spacer(1, 3 * mm))
        for line in summary_text.splitlines():
            line = line.strip()
            if not line:
                s.append(Spacer(1, 2 * mm))
            elif line.startswith("## "):
                s.append(Spacer(1, 3 * mm))
                s.append(Paragraph(escape(line[3:]), sty["H2"]))
            else:
                s.append(Paragraph(escape(line), sty["BODY"]))

    for e in sorted(done, key=lambda x: x.score if x.score is not None else 0):
        s.append(PageBreak())
        s += evidence_story(e, case, extras=True, lang=lang, doc_token=None)

    # Verification box on the final page of the bundle
    signer_fp = signer.get_signer_fingerprint()
    s.append(_verification_box(doc_token, signer_fp, lang, sty))

    return _build(s, f"{case.reference} case bundle", lang=lang)


def section63_certificate_pdf(ev, case, examiner_name: str = "Forensic Examiner", lang: str = "en", doc_token: str = None) -> bytes:
    """Generate Draft Certificate under Section 63 of Bharatiya Sakshya Adhiniyam, 2023."""
    if not doc_token:
        doc_token = uuid.uuid4().hex
    sty = get_styles(lang)
    events = sorted(ev.custody, key=lambda x: x.seq)
    first_event = events[0] if events else None
    head_event = events[-1] if events else None

    s = []
    # Header Banner
    logo_path = Path(__file__).resolve().parent / "assets" / "logo-mark.png"
    title_box = [
        Paragraph(f"<b>{t('sec63_title', lang)}</b>", ParagraphStyle("h_sec", parent=sty["H1"], fontSize=13, leading=16, alignment=1)),
        Spacer(1, 1 * mm),
        Paragraph(f"<i>{t('sec63_subtitle', lang)}</i>", ParagraphStyle("sub_sec", parent=sty["SMALL"], alignment=1)),
    ]
    if logo_path.exists():
        logo_img = Image(str(logo_path), width=12 * mm, height=12 * mm)
        t_top = Table([[logo_img, title_box]], colWidths=[16 * mm, 158 * mm])
        t_top.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1e3a8a")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
    else:
        t_top = Table([[title_box]], colWidths=[174 * mm])
        t_top.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1e3a8a")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
    s.append(t_top)
    s.append(Spacer(1, 4 * mm))

    # Draft Warning Callout
    warn_p = Paragraph(f"<b>NOTICE:</b> {t('sec63_draft_warning', lang)}",
                       ParagraphStyle("w", parent=sty["SMALL"], textColor=colors.HexColor("#991b1b"), alignment=1))
    t_warn = Table([[warn_p]], colWidths=[174 * mm])
    t_warn.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#f87171")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    s.append(t_warn)
    s.append(Spacer(1, 4 * mm))

    # Preamble
    s.append(Paragraph(
        f"I, <b>{escape(examiner_name)}</b>, do hereby certify that the electronic record detailed below has been "
        f"ingested, analysed, and cryptographically preserved under standard forensic operating procedures on the "
        f"Evidence Integrity Platform in accordance with <b>Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act)</b>.",
        sty["BODY"]
    ))
    s.append(Spacer(1, 4 * mm))

    # Part 1: Evidence Metadata Table
    s.append(Paragraph("<b>PART 1: IDENTIFICATION OF ELECTRONIC RECORD</b>", sty["H2"]))
    meta = [
        ["Case Reference", f"{case.reference} — {case.title}" if case else "N/A"],
        ["Target Evidence File", ev.filename],
        ["Cryptographic Hash (SHA-256)", ev.sha256],
        ["Hash Algorithm", "SHA-256 (FIPS 180-4 standard, 256-bit cryptographic digest)"],
        ["Media Category & Size", f"{ev.media_type.upper()} ({ev.size:,} bytes)"],
        ["Intake / Ingestion Timestamp", ev.received_at],
        ["Initial Custody Event Hash", first_event.event_hash if first_event else "N/A"],
        ["Current Chain Head Hash", head_event.event_hash if head_event else "N/A"],
        ["Forensic Integrity Verdict", f"{ev.verdict or 'Not analysed'} (Score: {ev.score}/100)"],
    ]
    t_meta = Table([[Paragraph(f"<b>{a}</b>", sty["CELL"]), Paragraph(escape(str(b)), sty["CELL"])] for a, b in meta],
                   colWidths=[55 * mm, 119 * mm])
    t_meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f4f5")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    s.append(t_meta)
    s.append(Spacer(1, 4 * mm))

    # Part 2: Statutory Declaration Clauses
    s.append(Paragraph(f"<b>PART 2: {t('sec63_decl_heading', lang)}</b>", sty["H2"]))
    clauses = [
        "(a) <b>Lawful Control & Regular Course:</b> The electronic record was received, processed, and stored on an automated forensic computing system during the period over which lawful control was exercised by the forensic division.",
        "(b) <b>System Proper Operation:</b> Throughout the material period, the computer system and evidence intake pipelines operated properly, and there were no operational defects or unauthorized interventions affecting the integrity of the data or its cryptographic representation.",
        "(c) <b>Cryptographic Chain of Custody:</b> The electronic record was ingested with SHA-256 bitstream validation, and every subsequent operation (analysis, inspection, export) was appended to a forward-secure hash-chained custody log where each event incorporates the previous event's SHA-256 digest.",
        "(d) <b>Factual Fidelity:</b> The output reproduced in this document accurately reproduces the electronic contents and cryptographic state of the original record submitted into custody.",
    ]
    for c in clauses:
        s.append(Paragraph(c, sty["BODY"]))
        s.append(Spacer(1, 1.5 * mm))

    # Part 3: Custody Trail Summary Table
    s.append(Spacer(1, 2 * mm))
    s.append(Paragraph("<b>PART 3: SUMMARY OF PRESERVATION CHAIN</b>", sty["H2"]))
    c_rows = [[Paragraph("<b>#</b>", sty["CELL"]), Paragraph("<b>Action</b>", sty["CELL"]),
               Paragraph("<b>Actor / Note</b>", sty["CELL"]), Paragraph("<b>Timestamp (UTC)</b>", sty["CELL"]),
               Paragraph("<b>Event Hash</b>", sty["CELL"])]]
    for c in events[:6]:  # show up to 6 key custody events
        c_rows.append([
            Paragraph(str(c.seq), sty["CELL"]),
            Paragraph(escape(c.action), sty["CELL"]),
            Paragraph(escape(f"{c.actor}: {c.note}"), sty["CELL"]),
            Paragraph(c.at[:19].replace("T", " "), sty["CELL"]),
            Paragraph(c.event_hash[:16] + "...", sty["CELL"]),
        ])
    t_cust = Table(c_rows, colWidths=[8 * mm, 32 * mm, 72 * mm, 32 * mm, 30 * mm])
    t_cust.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f4f5")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    s.append(t_cust)
    s.append(Spacer(1, 4 * mm))

    # Part 4: Declarant Execution & Blank Signature Block
    s.append(Paragraph(f"<b>PART 4: {t('sec63_sig_block', lang).upper()}</b>", sty["H2"]))
    sig_fields = [
        ["Full Name of Declarant:", "______________________________________________________"],
        ["Designation / Police Rank:", "______________________________________________________"],
        ["Official Station / Forensic Unit:", "______________________________________________________"],
        ["Officer Identity / Reg. No.:", "______________________________________________________"],
        ["Date & Place of Execution:", "______________________________________________________"],
        ["Signature & Official Seal:", "______________________________________________________"],
    ]
    t_sig = Table([[Paragraph(f"<b>{a}</b>", sty["CELL"]), Paragraph(b, sty["CELL"])] for a, b in sig_fields],
                  colWidths=[55 * mm, 119 * mm])
    t_sig.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    s.append(KeepTogether([t_sig]))

    # Part 5: Verification Box with QR Code
    signer_fp = signer.get_signer_fingerprint()
    s.append(_verification_box(doc_token, signer_fp, lang, sty))

    return _build(s, f"{ev.filename} Section 63 BSA 2023 Certificate", lang=lang)
