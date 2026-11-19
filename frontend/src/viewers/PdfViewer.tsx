import { useState } from "react";
import type { EvidenceFull } from "@/lib/types";
import { api } from "@/lib/api";
import { Badge, Button, Segmented } from "@/components/ui";
import { findingsOf, has, LegendItem, Swatch } from "./parts/util";

export default function PdfViewer({ ev }: { ev: EvidenceFull }) {
  const d = ev.details ?? {};
  const pages = (d.page_images ?? []).filter((n) => has(ev, n));
  const flagged = d.flagged_pages ?? [];
  const [idx, setIdx] = useState(0);
  const [zoom, setZoom] = useState<"fit" | "100">("fit");

  const items = findingsOf(ev).flatMap((f) => {
    const l = f.location;
    if (!l || l.kind !== "page") return [];
    const list = l.all && l.all.length ? l.all : [{ page: l.page, boxes: l.boxes }];
    return list.map((p) => ({ f, page: p.page, n: p.boxes?.length ?? 0 }));
  });

  if (pages.length === 0) {
    return (
      <div className="p-4 text-muted">
        No page images available. <a className="text-accent hover:underline" href={api.url.file(ev.id)} target="_blank" rel="noreferrer">Open the original file</a>
      </div>
    );
  }
  const cur = Math.min(idx, pages.length - 1);
  const isFlagged = flagged.includes(cur + 1);

  return (
    <div className="space-y-3 p-3 sm:p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Button size="sm" disabled={cur === 0} onClick={() => setIdx(cur - 1)}>Prev</Button>
          <span className="text-sm">Page {cur + 1} of {pages.length}</span>
          <Button size="sm" disabled={cur >= pages.length - 1} onClick={() => setIdx(cur + 1)}>Next</Button>
          {isFlagged && <Badge tone="bad">Flagged</Badge>}
        </div>
        <Segmented value={zoom} onChange={setZoom} options={[{ value: "fit", label: "Fit" }, { value: "100", label: "100%" }]} />
      </div>
      {flagged.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 text-xs text-muted">
          Flagged pages:
          {flagged.map((p) => (
            <button key={p} onClick={() => p >= 1 && p <= pages.length && setIdx(p - 1)} className={`rounded px-1.5 py-0.5 font-medium ${p === cur + 1 ? "bg-bad text-white" : "bg-bad-soft text-bad"}`}>{p}</button>
          ))}
        </div>
      )}
      <div className="max-h-[75vh] overflow-auto rounded-lg bg-surface2 p-2">
        <img src={api.url.artifact(ev.id, pages[cur])} alt={`Page ${cur + 1}`} className={zoom === "fit" ? "mx-auto block h-auto w-full max-w-full" : "block h-auto max-w-none"} style={zoom === "100" ? { width: "auto" } : undefined} />
      </div>
      <div className="flex flex-wrap gap-4">
        <LegendItem swatch={<Swatch className="bg-bad" />}>Font or size change inside a line</LegendItem>
        <LegendItem swatch={<Swatch className="bg-warn" />}>Text under a white shape</LegendItem>
      </div>
      {items.length > 0 && (
        <div>
          <h4 className="mb-1 text-xs font-semibold">Flagged items</h4>
          <ul className="divide-y divide-line rounded-lg border border-line">
            {items.map((it, i) => (
              <li key={i}>
                <button onClick={() => it.page >= 1 && it.page <= pages.length && setIdx(it.page - 1)} className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-surface2">
                  <span className="min-w-0 truncate text-sm">{it.f.title}</span>
                  <span className="shrink-0 text-xs text-muted">Page {it.page}{it.n ? ` · ${it.n} box${it.n === 1 ? "" : "es"}` : ""}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
