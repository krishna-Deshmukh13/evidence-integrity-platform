"""Evidence Integrity Score = 100 - sum over categories of min(sum of penalties, cap)."""
CATEGORY_CAPS = {"metadata": 30, "pixel": 40, "ai": 55, "document": 45, "audio": 55, "container": 20}
CATEGORY_LABELS = {"metadata": "Metadata", "pixel": "Pixel forensics", "ai": "AI / deepfake",
                   "document": "Document structure", "audio": "Voice forensics", "container": "Container"}
DEFAULT_PENALTY = {"high": 26, "medium": 14, "low": 6, "info": 0}


def verdict_for(score: int) -> str:
    if score >= 80:
        return "Consistent"
    if score >= 50:
        return "Needs review"
    return "Likely manipulated"


def compute(findings):
    """findings: iterable of objects/dicts with category, severity, penalty. -> (score, breakdown, verdict)."""
    sums = {}
    for f in findings:
        get = (lambda k: f.get(k)) if isinstance(f, dict) else (lambda k: getattr(f, k))
        sev = get("severity")
        pen = get("penalty")
        if pen is None:
            pen = DEFAULT_PENALTY.get(sev, 0)
        if sev == "info":
            pen = 0
        sums[get("category")] = sums.get(get("category"), 0) + int(pen)
    breakdown = {}
    for cat, total in sums.items():
        capped = min(total, CATEGORY_CAPS.get(cat, 40))
        if capped > 0:
            breakdown[cat] = capped
    raw_score = 100 - sum(breakdown.values())
    # Never display flat 0% or 100%; clamp to 1-99%
    score = max(1, min(99, raw_score))
    return score, breakdown, verdict_for(score)
