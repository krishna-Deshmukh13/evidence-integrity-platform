"""Report text: a deterministic template, optionally rewritten in plain English by a language model."""
import json
import re

from . import llm

NOT_RUN = re.compile(r"not installed|unavailable|skipped|too small|not enough|no .* to compare|unreadable|"
                     r"no faces|too short|no analyzer|not applicable|password", re.I)
SECTIONS = ["Summary", "Key findings", "Consistent with an original", "Recommended next steps", "Limitation"]


def template_report(ev, findings) -> str:
    bad = [f for f in findings if f.severity != "info"]
    skipped = [f for f in findings if f.severity == "info" and NOT_RUN.search(f.title)]
    ok = [f for f in findings if f.severity == "info" and f not in skipped]
    bad.sort(key=lambda f: -(f.penalty if f.penalty is not None else {"high": 26, "medium": 14, "low": 6}[f.severity]))
    lines = ["## Summary",
             f'The file "{ev.filename}" scored {ev.score}/100 ({ev.verdict}). '
             + (f"{len(bad)} check(s) raised an indicator." if bad else "No check raised an indicator.")
             + " This is a technical indication, not proof of authenticity or forgery.", "",
             "## Key findings"]
    lines += [f"- **{f.title}**" + (f" ({_where(f)})" if _where(f) else "") + f": {f.detail}" for f in bad] or \
             ["- No indicators were recorded."]
    lines += ["", "## Consistent with an original"]
    lines += [f"- {f.title}" for f in ok] or ["- No individual check returned a clean result."]
    steps = []
    if any(f.category == "metadata" for f in bad):
        steps.append("Obtain the original device copy and compare its metadata with this file.")
    if any(f.category == "pixel" for f in bad):
        steps.append("Review the highlighted regions manually and compare them with the original image.")
    if any(f.category == "ai" for f in bad):
        steps.append("Have a specialist confirm the AI / deepfake indicators with a second method.")
    if any(f.category in ("document", "audio", "container") for f in bad):
        steps.append("Review the flagged locations (pages, timestamps) against the source system or recording.")
    steps.append("Consider the context and other evidence before relying on this file.")
    lines += ["", "## Recommended next steps"] + [f"- {s}" for s in steps]
    lines += ["", "## Limitation",
              "Automated indicators support, but do not replace, expert and legal judgement. "
              "A high score does not prove a file is authentic."]
    if skipped:
        lines.append("Checks not performed or not applicable: " + "; ".join(f.title for f in skipped) + ".")
    return "\n".join(lines)


def _where(f) -> str:
    import json
    from .analyzers.common import F
    if not f.location:
        return ""
    try:
        return F(f.category, f.check, f.severity, f.title, location=json.loads(f.location)).where()
    except Exception:
        return ""


REPORT_SYSTEM = (
    "You write short, plain-English forensic reports for an examiner. Use ONLY the facts in the JSON you are "
    "given. Never invent facts, numbers or locations. Quote locations exactly as given. Never say that a file is "
    "authentic, genuine or proven real; never decide admissibility. Use exactly these Markdown sections in this "
    "order: '## Summary', '## Key findings', '## Consistent with an original', '## Recommended next steps', "
    "'## Limitation'. Use '- ' bullets. If a section has nothing to say, write a single bullet saying so.")


def facts_for_llm(ev, findings) -> str:
    from .analyzers.common import F
    rows = []
    for f in findings:
        try:
            w = F(f.category, f.check, f.severity, f.title,
                  location=json.loads(f.location) if f.location else None).where()
        except Exception:
            w = ""
        rows.append({"severity": f.severity, "category": f.category, "title": f.title, "detail": f.detail,
                     "where": w, "penalty": f.penalty})
    return json.dumps({"file": ev.filename, "type": ev.media_type, "score": ev.score, "verdict": ev.verdict,
                       "score_breakdown": ev.get_breakdown(), "findings": rows}, indent=1)


def has_all_sections(text: str) -> bool:
    return all(re.search(r"^\W*#*\W*" + re.escape(name), text, re.I | re.M) for name in SECTIONS)


def write_with_llm(ev, findings):
    """-> (text, model label) or None if the model is off, offline or its answer lacks the required sections."""
    if not llm.enabled():
        return None
    try:
        text = llm.complete(REPORT_SYSTEM, "Write the report for these findings:\n" + facts_for_llm(ev, findings),
                            max_tokens=1100)
    except llm.LLMError:
        return None
    if not has_all_sections(text):
        return None
    return text, llm.settings()["model"]
