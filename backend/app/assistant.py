"""Global assistant chatbot engine: intent routing, fact gathering, LLM prompt generation, and deterministic fallback."""
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import activity, config, custody, llm
from .assistant_glossary import lookup_term
from .deps import get_user_case_ids, has_case_access
from .models import Case, Evidence, Finding, Note, User

ASSISTANT_SYSTEM = (
    "You are an elite, highly knowledgeable digital forensics expert and investigative copilot "
    "for the Evidence Integrity Platform.\n"
    "You communicate like ChatGPT: articulate, friendly, thorough, and highly insightful.\n\n"
    "CORE CAPABILITIES & KNOWLEDGE:\n"
    "1. Comprehensive Forensic Science: Explain image tampering (Error Level Analysis, sensor noise discrepancies, "
    "copy-move clone detection), video frame splicing, audio voice cloning (synthetic speech, spectral formants, pitch jitter), "
    "PDF internal revision streams, and cryptographic SHA-256 integrity.\n"
    "2. Legal Admissibility & Compliance: Expert knowledge of Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA) "
    "(which replaced Section 65B of the Indian Evidence Act), cryptographic hash verification, digital signatures, and chains of custody.\n"
    "3. Case & Evidence Grounding: When answering about files, scores, or cases currently in the database, rely accurately "
    "on the provided facts. Never fabricate false file names or fake scores.\n"
    "4. Professional Forensic Tone: Be calm, objective, and constructive. Use objective forensic terms like 'shows indicators of modification' "
    "or 'exhibits compression discrepancies'. Avoid absolute legal declarations like 'this guarantees conviction' or slang.\n"
    "5. Formatting: Output clean, readable GitHub-flavored Markdown with bold key terms, clear bullet points, and headers where helpful.\n"
    "6. Multi-lingual Support: If the user addresses you in Hindi, Marathi, or English, reply fluently and naturally in that language.\n"
)

PROHIBITED_PHRASES = [
    (r"\bis fake\b", "shows signs of editing"),
    (r"\bit is fake\b", "it shows indicators of tampering"),
    (r"\bis authentic\b", "is consistent with recorded source parameters"),
    (r"\bis genuine\b", "is consistent with expected camera properties"),
    (r"\bare fake\b", "show indicators of modification"),
    (r"\bare authentic\b", "are consistent with recorded properties"),
    (r"\bare genuine\b", "are consistent with recorded properties"),
]


def sanitize_prohibited_phrases(text: str) -> str:
    """Post-processing safeguard to ensure forensic ethics compliance."""
    res = text
    for pat, repl in PROHIBITED_PHRASES:
        res = re.sub(pat, repl, res, flags=re.IGNORECASE)
    return res


def extract_first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    for p in parts:
        clean = p.rstrip(".,")
        if clean.lower() not in ("insp", "si", "inspector", "sub-inspector", "officer", "dr", "mr", "ms", "mrs"):
            return clean
    return parts[0] if parts else "there"


def serialize_card(ev: Evidence, case_map: Dict[int, Case]) -> dict:
    c = case_map.get(ev.case_id)
    return {
        "type": "evidence",
        "id": ev.id,
        "filename": ev.filename,
        "media_type": ev.media_type,
        "score": ev.score,
        "verdict": ev.verdict,
        "case_id": ev.case_id,
        "case_reference": c.reference if c else "",
        "case_title": c.title if c else "",
        "received_at": ev.received_at,
    }


def serialize_case_card(c: Case) -> dict:
    return {
        "type": "case",
        "id": c.id,
        "reference": c.reference,
        "title": c.title,
        "files": len(c.evidence),
        "investigator": c.investigator,
    }


def get_page_suggestions(page: str) -> List[str]:
    if page == "case":
        return [
            "Which file should I check first?",
            "Summarise this case",
            "Show files scoring below 50",
        ]
    if page == "evidence":
        return [
            "Why is this score what it is?",
            "Where is the edit?",
            "What should I do next?",
        ]
    # Default or dashboard
    return [
        "What needs my attention?",
        "Show likely manipulated files",
        "What is ELA?",
    ]


# ---------------------------------------------------------------- Intent Handlers

def handle_small_talk(user: User, message: str, context: dict) -> Tuple[str, List[dict], List[str]]:
    q = message.lower().strip()
    first_name = extract_first_name(user.full_name)
    page = context.get("page", "dashboard")
    suggestions = get_page_suggestions(page)
    sugg_text = "\n\nYou can ask me things like:\n" + "\n".join(f"- \"{s}\"" for s in suggestions)

    if re.search(r"\b(hi|hello|hey|namaste|good morning|good afternoon|good evening)\b", q):
        reply = f"Hello {first_name}. I am your Evidence Integrity assistant. I can help you search evidence, explain integrity scores, summarize cases, or define forensic checks." + sugg_text
        return reply, [], ["Greeting"]

    if re.search(r"\b(thank|thanks|dhanyavad|shukriya)\b", q):
        reply = f"You are very welcome, {first_name}. Let me know if you need anything else examined."
        return reply, [], ["User acknowledgement"]

    if re.search(r"\b(bye|goodbye|see you|cya)\b", q):
        reply = f"Goodbye, {first_name}. Have a good day."
        return reply, [], ["Goodbye"]

    if re.search(r"\b(who are you|what are you)\b", q):
        reply = (
            f"I am the Evidence Integrity Platform assistant. I help investigators and examiners review digital evidence, "
            f"understand tampering findings, inspect chains of custody, and find specific files across cases." + sugg_text
        )
        return reply, [], ["Assistant profile"]

    # Help / what can you do
    reply = (
        "Here are five things I can do to assist your investigation:\n"
        "1. **Find evidence**: Search by file type, verdict, score, or case (e.g., 'Show likely manipulated PDFs from CR-2013-0706').\n"
        "2. **Case intelligence**: Recommend which file to review first or summarize a case.\n"
        "3. **Explain scores and findings**: Explain why a file received a specific score and locate where edits occurred.\n"
        "4. **Explain terms**: Provide plain-language explanations of forensic concepts like ELA, SHA-256, clone detection, or pHash.\n"
        "5. **Contextual guidance**: Answer questions about the case or evidence page you are currently viewing." + sugg_text
    )
    return reply, [], ["Assistant capabilities"]


def handle_search(db: Session, user: User, message: str, context: dict) -> Tuple[str, List[dict], List[str]]:
    allowed_ids = get_user_case_ids(db, user)
    qs = db.query(Evidence).join(Case, Case.id == Evidence.case_id)
    if allowed_ids is not None:
        qs = qs.filter(Evidence.case_id.in_(allowed_ids))

    q_lower = message.lower()
    extracted_filters = []

    # 1. Media type filter
    media_match = None
    if re.search(r"\b(pdf|pdfs|document|documents|docx|doc)\b", q_lower):
        qs = qs.filter(Evidence.media_type == "document")
        media_match = "documents/PDFs"
        extracted_filters.append("Media: document")
    elif re.search(r"\b(image|images|photo|photos|picture|pictures|jpg|png)\b", q_lower):
        qs = qs.filter(Evidence.media_type == "image")
        media_match = "images"
        extracted_filters.append("Media: image")
    elif re.search(r"\b(audio|voice|sound|recording|recordings|wav|mp3)\b", q_lower):
        qs = qs.filter(Evidence.media_type == "audio")
        media_match = "audio"
        extracted_filters.append("Media: audio")
    elif re.search(r"\b(video|videos|footage|cctv|mp4)\b", q_lower):
        qs = qs.filter(Evidence.media_type == "video")
        media_match = "videos"
        extracted_filters.append("Media: video")

    # 2. Verdict filter
    verdict_match = None
    if re.search(r"\b(manipulated|tampered|edited|forged|likely manipulated|high risk)\b", q_lower):
        qs = qs.filter(Evidence.verdict == "Likely manipulated")
        verdict_match = "Likely manipulated"
        extracted_filters.append("Verdict: Likely manipulated")
    elif re.search(r"\b(needs review|review needed|uncertain)\b", q_lower):
        qs = qs.filter(Evidence.verdict == "Needs review")
        verdict_match = "Needs review"
        extracted_filters.append("Verdict: Needs review")
    elif re.search(r"\b(consistent|authentic|clean|original|unmodified)\b", q_lower):
        qs = qs.filter(Evidence.verdict == "Consistent")
        verdict_match = "Consistent"
        extracted_filters.append("Verdict: Consistent")

    # 3. Score range
    score_below = re.search(r"(?:score\s+)?(?:below|under|less than|<)\s*(\d+)", q_lower)
    score_above = re.search(r"(?:score\s+)?(?:above|over|greater than|>)\s*(\d+)", q_lower)
    if score_below:
        val = int(score_below.group(1))
        qs = qs.filter(Evidence.score < val)
        extracted_filters.append(f"Score < {val}")
    if score_above:
        val = int(score_above.group(1))
        qs = qs.filter(Evidence.score > val)
        extracted_filters.append(f"Score > {val}")

    # 4. Case reference
    case_ref_match = re.search(r"\b(CR-[A-Za-z0-9_-]+)\b", message, re.IGNORECASE)
    matched_case = None
    if case_ref_match:
        ref_text = case_ref_match.group(1).upper()
        matched_case = db.query(Case).filter(Case.reference.ilike(ref_text)).first()
        if matched_case:
            qs = qs.filter(Evidence.case_id == matched_case.id)
            extracted_filters.append(f"Case: {matched_case.reference}")
        else:
            qs = qs.filter(Evidence.case_id == -1)
            extracted_filters.append(f"Case: {ref_text}")
    elif context.get("case_id") and re.search(r"\b(this case|here|in this)\b", q_lower):
        c_id = context.get("case_id")
        qs = qs.filter(Evidence.case_id == c_id)
        c_obj = db.get(Case, c_id)
        if c_obj:
            extracted_filters.append(f"Case: {c_obj.reference}")

    # 5. General text search keywords
    # Filter out stopwords, filter terms, and case references
    stopwords = {
        "find", "show", "list", "search", "where", "are", "the", "files", "file", "all",
        "evidence", "items", "item", "give", "me", "from", "in", "with", "score", "scores",
        "scoring", "scored", "below", "under", "above", "over", "case", "cases", "likely",
        "manipulated", "audio", "video", "videos", "image", "images", "photo", "photos",
        "picture", "pictures", "recording", "recordings", "document", "documents", "docx",
        "pdf", "pdfs", "consistent", "forged", "tampered", "please", "can", "you", "tell",
        "what", "which", "how", "many", "check", "urgent", "attention", "about", "this"
    }
    tokens = [w for w in re.findall(r"[a-z0-9_.-]+", q_lower) if w not in stopwords and not w.startswith("cr-") and len(w) >= 3]
    if tokens:
        keyword = tokens[0]
        like = f"%{keyword}%"
        qs = qs.filter(or_(Evidence.filename.ilike(like), Evidence.sha256.ilike(like), Evidence.tags.ilike(like)))
        extracted_filters.append(f"Keyword: '{keyword}'")

    results = qs.order_by(Evidence.score.is_(None), Evidence.score.asc()).limit(10).all()
    case_ids = {e.case_id for e in results}
    case_map = {c.id: c for c in db.query(Case).filter(Case.id.in_(case_ids)).all()} if case_ids else {}
    cards = [serialize_card(e, case_map) for e in results]

    filter_desc = ", ".join(extracted_filters) if extracted_filters else "all criteria"
    based_on = [f"Search results ({len(results)} matches)", f"Filters applied: {filter_desc}"]

    if not results:
        reply = (
            f"I could not find any evidence files matching {filter_desc}. "
            "You might try widening your search filters, searching across all cases, or checking the file name."
        )
        return reply, [], based_on

    # Deterministic reply
    if len(results) == 1:
        e = results[0]
        reply = (
            f"I found 1 matching file: **{e.filename}** (Score: {e.score}/100, Verdict: {e.verdict}). "
            "You can click the card below to open its forensic analysis."
        )
    else:
        reply = (
            f"I found {len(results)} matching files for {filter_desc}. "
            "Here are the top results, ordered by risk (lowest score first):"
        )
    return reply, cards, based_on


def handle_case_overview(db: Session, user: User, message: str, context: dict) -> Tuple[str, List[dict], List[str]]:
    # Check if a case reference is explicitly in the message
    case_ref_match = re.search(r"\b(CR-[A-Za-z0-9_-]+)\b", message, re.IGNORECASE)
    case_obj = None
    if case_ref_match:
        ref_text = case_ref_match.group(1).upper()
        case_obj = db.query(Case).filter(Case.reference.ilike(ref_text)).first()
    elif context.get("case_id"):
        case_obj = db.get(Case, context["case_id"])

    if not case_obj:
        if case_ref_match:
            return (
                f"I could not find case {case_ref_match.group(1).upper()} in the repository. Please verify the reference.",
                [],
                ["Case lookup prompt"]
            )
        return (
            "Which case would you like me to inspect? Please specify a case reference like 'CR-2013-0706' or open a case page.",
            [],
            ["Case lookup prompt"]
        )

    if not has_case_access(db, user, case_obj.id):
        return (
            f"You do not currently have permission to access case {case_obj.reference}. Please contact your administrator.",
            [],
            ["Access control check"]
        )

    evidence_list = sorted(case_obj.evidence, key=lambda e: (e.score is None, e.score if e.score is not None else 100))
    done_ev = [e for e in evidence_list if e.status == "done" and e.score is not None]
    manipulated = sum(1 for e in done_ev if e.verdict == "Likely manipulated")
    needs_review = sum(1 for e in done_ev if e.verdict == "Needs review")
    consistent = sum(1 for e in done_ev if e.verdict == "Consistent")

    case_map = {case_obj.id: case_obj}
    cards = [serialize_card(e, case_map) for e in evidence_list[:5]]

    based_on = [
        f"Case {case_obj.reference} summary",
        f"{len(evidence_list)} total files ({manipulated} manipulated, {needs_review} review, {consistent} consistent)"
    ]

    q_lower = message.lower()
    if re.search(r"check first|first|start|highest risk|most suspicious", q_lower):
        if evidence_list:
            top_file = evidence_list[0]
            reply = (
                f"In case **{case_obj.reference}** ('{case_obj.title}'), you should check **{top_file.filename}** first. "
                f"It carries the lowest integrity score ({top_file.score}/100, {top_file.verdict}) and shows the most significant indicators of editing."
            )
        else:
            reply = f"Case **{case_obj.reference}** currently contains no evidence files."
    else:
        # General case summary
        reply = (
            f"Case **{case_obj.reference}** ('{case_obj.title}') contains {len(evidence_list)} digital evidence file(s). "
            f"Current analysis shows {manipulated} file(s) with signs of editing, {needs_review} requiring review, and {consistent} consistent file(s). "
            + (f"The highest priority item to inspect is **{evidence_list[0].filename}** (Score: {evidence_list[0].score}/100)." if evidence_list else "")
        )

    return reply, cards, based_on


def handle_system_overview(db: Session, user: User, message: str, context: dict) -> Tuple[str, List[dict], List[str]]:
    allowed_ids = get_user_case_ids(db, user)
    ev_query = db.query(Evidence)
    case_query = db.query(Case)
    if allowed_ids is not None:
        ev_query = ev_query.filter(Evidence.case_id.in_(allowed_ids))
        case_query = case_query.filter(Case.id.in_(allowed_ids))

    all_ev = ev_query.all()
    all_cases = {c.id: c for c in case_query.all()}
    done = [e for e in all_ev if e.status == "done" and e.score is not None]

    # Needs attention items: score < 50 without assignee, unreviewed > 3 days, or failed
    needs_att = [e for e in all_ev if (e.status == "failed") or (e.score is not None and e.score < 50 and not e.assignee_id)]
    highest_risk = sorted(done, key=lambda e: e.score)[:5]

    cards = [serialize_card(e, all_cases) for e in (needs_att[:5] if needs_att else highest_risk)]
    based_on = [
        f"Platform repository ({len(all_cases)} accessible cases, {len(all_ev)} evidence files)",
        f"{len(needs_att)} items requiring attention"
    ]

    q_lower = message.lower()
    if re.search(r"attention|urgent|pending", q_lower):
        if needs_att:
            top_item = needs_att[0]
            reply = (
                f"There are **{len(needs_att)} items** currently requiring attention across your cases. "
                f"Priority file: **{top_item.filename}** (Score: {top_item.score}/100, Verdict: {top_item.verdict}) has not yet been assigned to an examiner. "
                "The top items are listed below for direct review."
            )
        else:
            reply = "All evidence across your accessible cases is reviewed and up to date. No urgent items require attention right now."
    else:
        reply = (
            f"You have access to **{len(all_cases)} case(s)** encompassing **{len(all_ev)} evidence file(s)**. "
            f"Of these, {sum(1 for e in done if e.verdict == 'Likely manipulated')} show indicators of manipulation, "
            f"and {len(needs_att)} items currently require examiner review or assignment."
        )

    return reply, cards, based_on


def handle_file_explanation(db: Session, user: User, message: str, context: dict) -> Tuple[str, List[dict], List[str]]:
    ev = None
    # Check if context has evidence_id
    if context.get("evidence_id"):
        ev = db.get(Evidence, context["evidence_id"])
    else:
        # Check if user mentioned a specific filename in the message
        for cand in db.query(Evidence).all():
            if cand.filename.lower() in message.lower():
                ev = cand
                break

    if not ev:
        return (
            "Which evidence file would you like me to explain? You can ask about a specific file name or open a file detail page.",
            [],
            ["File context required"]
        )

    if not has_case_access(db, user, ev.case_id):
        return (
            f"You do not currently have access to file '{ev.filename}'. Please contact your case administrator.",
            [],
            ["Access control check"]
        )

    case_obj = db.get(Case, ev.case_id)
    case_map = {ev.case_id: case_obj} if case_obj else {}
    card = [serialize_card(ev, case_map)]

    # Gather file facts
    score = ev.score if ev.score is not None else 100
    verdict = ev.verdict or "Under analysis"
    bd = ev.get_breakdown()
    flagged = sorted([f for f in ev.findings if f.severity != "info"], key=lambda f: -(f.penalty or 0))

    based_on = [
        f"Findings of {ev.filename}",
        f"Score {score}/100 ({verdict})",
        f"{len(flagged)} active penalty indicators",
        f"Chain of custody ({len(ev.custody)} events)"
    ]

    q_lower = message.lower()

    if re.search(r"where|location|region|part|box|area", q_lower):
        located = [f for f in flagged if f.location]
        if located:
            parts = [f"- **{f.title}**: {f.detail}" for f in located[:3]]
            reply = (
                f"For **{ev.filename}**, spatial indicators were identified:\n"
                + "\n".join(parts) + "\n\nYou can inspect the colored overlay bounding boxes in the Forensics Viewer layers."
            )
        else:
            reply = f"For **{ev.filename}**, findings are based on file-level metadata and structure; no specific pixel bounding coordinates were recorded."
        return reply, card, based_on

    if re.search(r"what should i do|next step|recommend", q_lower):
        steps = [
            f"Verify the physical or original digital source copy against hash `{ev.sha256[:16]}...`.",
            "Inspect the located finding layers (ELA, Noise, and AI Heatmap) in the Forensics Viewer.",
            "Record your conclusion with the examiner review status and add an investigative note.",
        ]
        reply = f"Recommended next steps for **{ev.filename}**:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        return reply, card, based_on

    # Default score explanation
    bd_parts = [f"{k.capitalize()}: -{v} pts" for k, v in bd.items() if v > 0]
    bd_str = ", ".join(bd_parts) if bd_parts else "No category penalties applied"

    finding_summaries = []
    for f in flagged[:3]:
        finding_summaries.append(f"- **{f.title}** ({f.severity.capitalize()} severity, -{f.penalty} pts): {f.detail}")

    reply = (
        f"**{ev.filename}** received an integrity score of **{score}/100** ({verdict}). "
        f"Points were deducted across categories ({bd_str}).\n\n"
        f"Key findings behind this rating:\n" + "\n".join(finding_summaries if finding_summaries else ["- No manipulation indicators detected; metadata and structure are consistent."])
    )
    return reply, card, based_on


def generate_forensic_fallback(message: str, context: dict, db: Session, user: User) -> str:
    """Intelligent multi-topic forensic knowledge synthesis when external LLMs are unreachable or offline."""
    q = message.lower()
    first_name = extract_first_name(user.full_name)

    # 1. Section 63 BSA 2023 & Legal Admissibility
    if re.search(r"\b(section 63|bsa|65b|bharatiya sakshya|admissib|court|legal|certificate|judge|evidence act)\b", q):
        return (
            "### Section 63 Certificate (Bharatiya Sakshya Adhiniyam, 2023)\n\n"
            "Under **Section 63 of the BSA, 2023** (which supersedes Section 65B of the Indian Evidence Act, 1872), "
            "electronic records require cryptographic provenance to establish primary admissibility in court without requiring the physical seizure of host computers:\n\n"
            "- **Cryptographic Hash Binding**: Every evidentiary file must have its SHA-256 digest recorded immediately upon seizure or extraction.\n"
            "- **Chain of Custody Integrity**: The hash sequence must be verified chronologically from intake, through forensic analysis, to court presentation.\n"
            "- **Certificate of Authenticity**: The platform generates an automated, cryptographically signed Section 63 BSA certificate containing:\n"
            "  1. Original file SHA-256 and intake timestamp.\n"
            "  2. Hardware/software execution environment specifications.\n"
            "  3. Examiner verification signature and ED25519 public key fingerprint.\n"
            "  4. A public verification QR code verifiable on the standalone portal (`/verify`)."
        )

    # 2. Error Level Analysis (ELA)
    if re.search(r"\b(ela|error level|compression error|jpeg artifact)\b", q):
        return (
            "### Error Level Analysis (ELA) Methodology\n\n"
            "**Error Level Analysis** detects digital image composition by exploiting the lossy nature of the JPEG compression algorithm:\n\n"
            "- **Principle**: When a JPEG image is created, the entire 8x8 pixel block matrix reaches a uniform compression error rate. "
            "When an element is pasted into the photo from another source (or edited with Photoshop), that modified region has a different error potential.\n"
            "- **Execution**: The platform re-compresses the image at an intentional 90% quality level and computes pixel-wise absolute difference residuals.\n"
            "- **Interpretation**:\n"
            "  - **High brightness / bright edges**: Indicates recently modified or spliced content.\n"
            "  - **Uniform dark texture**: Indicates an untouched, authentic continuous image area.\n"
            "  - **Notice**: High-contrast edges naturally show higher ELA residuals; examiners must correlate ELA with the **Noise** and **Clone Map** layers."
        )

    # 3. Clone / Copy-Move Detection
    if re.search(r"\b(clone|copy[- ]move|cloning|duplicate region|orb|sift)\b", q):
        return (
            "### Copy-Move & Clone Detection (ORB Feature Matching)\n\n"
            "Copy-move forgery involves copying a patch within an image and pasting it elsewhere to conceal objects or duplicate details:\n\n"
            "- **Algorithm**: The platform applies **Oriented FAST and Rotated BRIEF (ORB)** feature extraction across the image to identify 2,000+ keypoints.\n"
            "- **Descriptor Matching**: Features with similar visual signatures are paired using Hamming distance with Lowe's ratio test (0.75).\n"
            "- **Spatial Clustering**: Points within a close spatial neighborhood (<15 px) are filtered out as natural textures. "
            "Clusters of parallel displacement vectors connecting distant regions confirm deliberate copy-paste manipulation.\n"
            "- **Forensics Viewer**: In the evidence detail viewer, select the **Clone** layer to inspect the vector lines and bounding boxes."
        )

    # 4. Deepfake, Face Swap & Generative AI Detection
    if re.search(r"\b(deepfake|face swap|ai generated|diffusion|gan|synthetic|synthetic media)\b", q):
        return (
            "### Deepfake & Synthetic Media Detection\n\n"
            "Our multi-modal neural inspection pipeline triages generative AI media across visual and frequency domains:\n\n"
            "- **Spatial Discrepancies**: Diffusion models and GANs often struggle with fine physical details: asymmetric iris reflections, "
            "unnatural ear contours, teeth boundary blending, and inconsistent depth-of-field blur.\n"
            "- **Fourier Frequency Artifacts**: Neural upsampling layers (e.g., transposed convolutions) leave distinct high-frequency periodic grid spikes "
            "in the 2D Fast Fourier Transform (FFT) spectrum that never occur in optical camera sensors.\n"
            "- **Grad-CAM Attention**: The platform computes Gradient-weighted Class Activation Mapping to highlight the exact facial or structural zones "
            "that contributed to the synthetic manipulation score."
        )

    # 5. Audio Forensics & Synthetic Voice Cloning
    if re.search(r"\b(audio|voice|speech|tts|elevenlabs|synthetic voice|waveform|spectrogram|pitch)\b", q):
        return (
            "### Audio Forensics & Voice Clone Triage\n\n"
            "Synthetic voice cloning (such as models from ElevenLabs or Bark) creates acoustic discrepancies detectable through spectral analysis:\n\n"
            "- **Spectral Roll-Off & High-Frequency Cutoffs**: Many neural vocoders hard-filter frequencies above 8 kHz or 12 kHz, "
            "creating an unnatural straight-line shelf in the spectrogram.\n"
            "- **Pitch Contour & Jitter**: Human vocal cords generate natural micro-fluctuations (jitter and shimmer). "
            "Synthesized speech often presents unnaturally smooth pitch tracks or robotic micro-pauses.\n"
            "- **Digital Silence**: Authentic microphone recordings capture ambient background room tone. "
            "TTS audio often contains blocks of true digital zero (`-∞ dB`), revealing inserted speech segments."
        )

    # 6. Video Forensics & Temporal Splice Detection
    if re.search(r"\b(video|cctv|splice|temporal|dropped frame|frame rate|fps|i-frame)\b", q):
        return (
            "### Video Forensics & Temporal Consistency\n\n"
            "Video tampering typically involves splicing out seconds of CCTV footage or inserting fabricated sequences:\n\n"
            "- **Presentation Timestamp (PTS) Gaps**: The platform inspects individual packet headers for discontinuous timestamp deltas.\n"
            "- **I-Frame Cadence**: Standard video encoders insert Intra-frames (key frames) at regular intervals (GOP size). "
            "Spliced footage causes abrupt GOP restarts or anomalous I-frame clustering.\n"
            "- **Optical Flow Discrepancies**: Motion vector tracking between consecutive frames flags sudden spatial velocity jumps that signify cut edits."
        )

    # 7. Cryptographic SHA-256 vs Perceptual Hash (pHash)
    if re.search(r"\b(sha256|sha-256|phash|perceptual hash|hash|collision)\b", q):
        return (
            "### SHA-256 Cryptographic Hash vs Perceptual Hash (pHash)\n\n"
            "- **SHA-256 (Exact Byte Proof)**:\n"
            "  - Computes a mathematical 256-bit digest of raw bytes.\n"
            "  - Avalanche effect: modifying a single pixel or byte completely changes the entire hash.\n"
            "  - Used for **legal chain of custody** and proving that an evidence file was never modified in storage.\n\n"
            "- **Perceptual Hash (Visual Similarity)**:\n"
            "  - Uses the Discrete Cosine Transform (DCT) to compute a structural image fingerprint.\n"
            "  - Tolerant to re-encoding, minor compression, or resizing.\n"
            "  - Files with a Hamming distance ≤16 bits are flagged as the same visual media across cases in the Intelligence Graph."
        )

    # 8. General investigative guidance
    page = context.get("page", "dashboard")
    return (
        f"Hello {first_name}. As your forensic assistant, I am ready to help investigate digital evidence:\n\n"
        "- **Analyze Evidence**: Open any photo, video, or audio file to inspect ELA, clone maps, noise variance, or waveforms.\n"
        "- **Verify Custody**: Inspect tamper-evident SHA-256 hashes and download Section 63 BSA legal certificates.\n"
        "- **Case Intelligence**: Review cross-case connections in the **Intelligence Graph** (`/graph`) and historical events in the **Timeline** (`/timeline`).\n"
        "- **Search**: Ask me to find files (e.g., *'Show likely manipulated files'* or *'Search PDFs in CR-2022-1008'*)."
    )


# ---------------------------------------------------------------- Core Orchestration

def route_and_gather(db: Session, user: User, message: str, context: dict) -> Tuple[str, str, List[dict], List[str], dict]:
    """Identify intent, gather facts, and generate the response.
    Returns (intent, deterministic_reply, cards, based_on, gathered_facts)."""
    q_lower = message.lower().strip()

    # 1. Check small talk
    if re.search(r"\b(hi|hello|hey|namaste|good morning|good afternoon|good evening|bye|goodbye|see you|thank|thanks|dhanyavad|shukriya|who are you|what are you)\b", q_lower):
        reply, cards, based_on = handle_small_talk(user, message, context)
        return "small_talk", reply, cards, based_on, {"type": "small_talk"}

    # 2. Check glossary term definition
    glossary_match = lookup_term(message)
    if glossary_match:
        term_title, definition = glossary_match
        reply = f"**{term_title}**\n\n{definition}"
        return "glossary", reply, [], [f"Glossary: {term_title}"], {"term": term_title, "definition": definition}

    # 3. Check file explanation intent
    if (
        re.search(r"(why\s+(?:is\s+)?(?:this|the)?\s*score|why\s+is\s+this\s+\d+|why\s+this|what\s+does\s+this\s+mean|where\s+is\s+the\s+edit|explain\s+this\s+file|what\s+findings|breakdown|what\s+should\s+i\s+do)", q_lower)
        or (context.get("page") == "evidence" and re.search(r"(explain|why|where|score|details|findings)", q_lower))
    ):
        reply, cards, based_on = handle_file_explanation(db, user, message, context)
        return "file_explanation", reply, cards, based_on, {"evidence_id": context.get("evidence_id")}

    # 4. Check case overview intent (explicit case summary / review request)
    if (
        re.search(r"(which\s+file\s+should\s+i\s+check\s+first|which\s+file\s+to\s+check|check\s+first|summarise|summarize|case\s+summary|case\s+overview|how\s+many\s+files\s+in\s+case|about\s+case|about\s+this\s+case)", q_lower)
        or (context.get("page") == "case" and re.search(r"(check\s+first|overview|summary|suspicious)", q_lower))
        or re.search(r"^\s*(?:about\s+)?case\s+CR-[A-Za-z0-9_-]+\s*$", message, re.IGNORECASE)
    ):
        reply, cards, based_on = handle_case_overview(db, user, message, context)
        return "case_overview", reply, cards, based_on, {"case_id": context.get("case_id")}

    # 5. Check system overview intent
    if re.search(r"(what\s+needs\s+(?:my\s+)?attention|system\s+summary|system\s+overview|dashboard\s+status|how\s+many\s+cases|custody\s+health|urgent\s+items)", q_lower):
        reply, cards, based_on = handle_system_overview(db, user, message, context)
        return "system_overview", reply, cards, based_on, {"type": "system_overview"}

    # 6. Check search intent
    if (
        re.search(r"(find|show|list|search|where\s+are|look\s+for|manipulated|audio|video|image|photo|pdf|document|score\s+below|score\s+above|scoring\s+below)", q_lower)
        or re.search(r"\bCR-[A-Za-z0-9_-]+\b", message, re.IGNORECASE)
    ):
        reply, cards, based_on = handle_search(db, user, message, context)
        return "search", reply, cards, based_on, {"type": "search"}

    # 7. Conversational & Open Forensic Intelligence Inquiry (ChatGPT style)
    fallback_reply = generate_forensic_fallback(message, context, db, user)
    based_on = ["Forensic knowledge base & AI intelligence engine"]
    if context.get("case_id"):
        based_on.append(f"Context: Case #{context['case_id']}")
    if context.get("evidence_id"):
        based_on.append(f"Context: File #{context['evidence_id']}")
    return "chat_qa", fallback_reply, [], based_on, {"type": "chat_qa"}


def process_message(db: Session, user: User, message: str, context: Optional[dict] = None) -> Tuple[str, str, List[dict], List[str]]:
    """Process user message and return (reply_text, source, results_cards, based_on)."""
    ctx = context or {}
    intent, fallback_reply, cards, based_on, facts = route_and_gather(db, user, message, ctx)

    # For pure small-talk greetings, return instant polite template
    if intent == "small_talk":
        cleaned = sanitize_prohibited_phrases(fallback_reply)
        return cleaned, "template", cards, based_on

    # For all queries, attempt live AI Model generation via free online API or configured provider
    if llm.enabled():
        try:
            # Build comprehensive prompt for ChatGPT-like conversational depth
            user_prompt = (
                f"USER QUESTION: {message}\n\n"
                f"CURRENT PLATFORM CONTEXT:\n"
                f"- Page: {ctx.get('page', 'dashboard')}\n"
                f"- Contextual Facts: {', '.join(based_on)}\n"
            )
            if fallback_reply and intent != "chat_qa":
                user_prompt += f"- Structured Data / Findings Summary:\n{fallback_reply}\n\n"
            user_prompt += (
                "Please provide a complete, clear, and professional response formatted in GitHub Markdown. "
                "Include actionable forensic insights, bold key terms, and bullet points where helpful."
            )

            model_text = llm.complete(ASSISTANT_SYSTEM, user_prompt, max_tokens=1000)
            if model_text and len(model_text.strip()) > 15:
                cleaned = sanitize_prohibited_phrases(model_text.strip())
                return cleaned, llm.settings()["label"], cards, based_on
        except Exception:
            # Fail gracefully to expert fallback
            pass

    # Deterministic fallback with deep forensic knowledge
    cleaned = sanitize_prohibited_phrases(fallback_reply)
    source_label = "Built-in glossary" if intent == "glossary" else "Forensic Knowledge Engine"
    return cleaned, source_label, cards, based_on
