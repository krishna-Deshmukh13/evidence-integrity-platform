"""Ask: questions about ONE file, answered from its findings, custody log, review status and notes."""
import json
import re

from . import llm
from .analyzers.common import F

ASK_SYSTEM = (
    "You answer an examiner's questions about one digital evidence file. Use ONLY the context provided. If "
    "something is not in the context, say it was not recorded; never guess. Quote locations exactly as given. "
    "Never claim the file is authentic or decide admissibility. Be concise.")


def _where(f):
    try:
        return F(f.category, f.check, f.severity, f.title,
                 location=json.loads(f.location) if f.location else None).where()
    except Exception:
        return ""


def context_text(ev) -> str:
    lines = [f"File: {ev.filename} ({ev.media_type}), SHA-256 {ev.sha256}",
             f"Score {ev.score}/100, verdict {ev.verdict}. Breakdown (points lost): {json.dumps(ev.get_breakdown())}",
             f"Review status: {ev.review_status}. Tags: {', '.join(ev.get_tags()) or 'none'}", "Findings:"]
    for f in ev.findings:
        w = _where(f)
        lines.append(f"- [{f.severity.upper()}] {f.title}: {f.detail}" + (f" [where: {w}]" if w else "")
                     + f" (penalty {f.penalty})")
    lines.append("Chain of custody:")
    for c in ev.custody:
        lines.append(f"- #{c.seq} {c.action} by {c.actor} at {c.at}: {c.note}")
    lines.append("Notes: " + ("; ".join(f"{n.author}: {n.body}" for n in ev.notes) or "none"))
    return "\n".join(lines)


def _flagged(ev):
    return sorted((f for f in ev.findings if f.severity != "info"), key=lambda f: -(f.penalty or 0))


def rule_answer(ev, q: str) -> str:
    ql = q.lower()
    fl = _flagged(ev)

    def bullets(items):
        return "\n".join(items) if items else "- Nothing was recorded for this."

    def fmt(f):
        w = _where(f)
        return f"- {f.severity.upper()}: {f.title}" + (f" [where: {w}]" if w else "") + f". {f.detail}"

    if re.search(r"custody|hash|chain|sha|receiv|handled|who ", ql):
        return "Chain of custody:\n" + "\n".join(f"- #{c.seq} {c.action} by {c.actor} ({c.at}). {c.note}"
                                                  for c in ev.custody)
    if re.search(r"next|step|recommend|should i|what now", ql):
        steps = ["Obtain the original device copy and compare it with this file." if fl else
                 "No indicators were raised, but do not treat a high score as proof of authenticity.",
                 "Review each located finding by eye (use the viewer layers).",
                 "Record your conclusion with the review status and a note."]
        return "Suggested next steps:\n" + "\n".join(f"- {s}" for s in steps)
    if re.search(r"review|note|assign|tag", ql):
        return (f"Review status is '{ev.review_status}'. Tags: {', '.join(ev.get_tags()) or 'none'}. "
                f"Notes: {len(ev.notes)}" + ("".join(f"\n- {n.author}: {n.body}" for n in ev.notes)))
    if re.search(r"where|locat|region|coordinate|timestamp|page|which part|what part", ql):
        located = [f for f in fl if _where(f)]
        return "Located findings:\n" + bullets([fmt(f) for f in located])
    if re.search(r"metadata|exif|software|date|camera|author|producer|tag", ql):
        return "Metadata findings:\n" + bullets([fmt(f) for f in ev.findings if f.category == "metadata"])
    if re.search(r"\bai\b|generat|deepfake|synthetic|fake|voice|clone|heatmap|detector", ql):
        return "AI and manipulation indicators:\n" + bullets(
            [fmt(f) for f in ev.findings if f.category in ("ai", "audio") or f.check == "copy_move"])
    if re.search(r"score|why|verdict|rating|low|high|how", ql):
        bd = ev.get_breakdown()
        head = (f"The score is {ev.score}/100 ({ev.verdict}). Points lost by category: "
                + (", ".join(f"{k} -{v}" for k, v in bd.items()) or "none") + ".")
        return head + "\nThe findings behind it:\n" + bullets([fmt(f) for f in fl])
    return (f"{ev.filename} scored {ev.score}/100 ({ev.verdict}) with {len(fl)} indicator(s). Ask me about the score, "
            "where the findings are, the metadata, AI detectors, the chain of custody, or next steps.")


def answer(ev, question: str, history):
    """-> (answer text, source label). Falls back to the rule-based answerer when no model is available."""
    if llm.enabled():
        turns = "\n".join(f"{m.role}: {m.content}" for m in history[-6:])
        try:
            text = llm.complete(ASK_SYSTEM, f"CONTEXT\n{context_text(ev)}\n\nRECENT CONVERSATION\n{turns}\n\n"
                                            f"QUESTION\n{question}", max_tokens=700)
            return text, llm.settings()["model"]
        except llm.LLMError:
            pass
    return rule_answer(ev, question), "rules"
