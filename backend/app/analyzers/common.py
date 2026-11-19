import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class F:
    """One result of one check."""
    category: str            # metadata | pixel | ai | document | audio | container
    check: str
    severity: str            # info (passed) | low | medium | high
    title: str
    detail: str = ""
    penalty: Optional[int] = None
    location: Optional[dict] = None   # {"kind":"region","x0":..,"y0":..,"x1":..,"y1":..} etc.

    def where(self) -> str:
        loc = self.location or {}
        if loc.get("kind") == "region":
            return f"from ({loc['x0']}, {loc['y0']}) to ({loc['x1']}, {loc['y1']})"
        if loc.get("kind") == "field":
            return f"{loc.get('name')}"
        if loc.get("kind") == "time":
            return f"{loc.get('start', 0):.1f}s to {loc.get('end', 0):.1f}s"
        if loc.get("kind") == "page":
            return f"page {loc.get('page')}"
        return ""

    def loc_json(self) -> str:
        return json.dumps(self.location) if self.location else ""


def noop_progress(stage: str, pct: int):
    pass
