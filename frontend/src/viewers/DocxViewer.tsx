import type { EvidenceFull } from "@/lib/types";
import { Badge } from "@/components/ui";
import { findingsOf, LegendItem, Swatch } from "./parts/util";

export default function DocxViewer({ ev }: { ev: EvidenceFull }) {
  const d = ev.details ?? {};
  const paras = d.paragraphs ?? [];
  const tracked = findingsOf(ev).find((f) => f.check === "tracked_changes");
  const props = Object.entries(d.properties ?? {});
  const sessions = d.editing_sessions;

  return (
    <div className="space-y-4 p-3 sm:p-4">
      {tracked && (
        <div className="rounded-lg border border-line bg-warn-soft p-3 text-sm">
          <div className="font-medium text-warn">{tracked.title}</div>
          {tracked.detail && <div className="mt-0.5 text-ink">{tracked.detail}</div>}
        </div>
      )}
      <div className="flex flex-wrap gap-4">
        <LegendItem swatch={<Swatch className="bg-warn" />}>Tracked change</LegendItem>
        <LegendItem swatch={<Swatch className="bg-bad" />}>Mixed fonts</LegendItem>
      </div>
      {paras.length === 0 ? (
        <div className="text-muted">No paragraph text available.</div>
      ) : (
        <div className="mx-auto max-h-[70vh] max-w-3xl space-y-2 overflow-auto rounded-lg border border-line bg-bg p-5 shadow-sm sm:p-8">
          {paras.map((p) => (
            <div key={p.i} className={`rounded px-2 py-1 font-serif text-[15px] leading-relaxed ${p.tracked ? "bg-warn-soft" : p.mixed_fonts ? "bg-bad-soft" : ""}`}>
              {(p.tracked || p.mixed_fonts) && (
                <div className="mb-0.5 flex gap-1">
                  {p.tracked && <Badge tone="warn">Tracked change</Badge>}
                  {p.mixed_fonts && <Badge tone="bad">Mixed fonts</Badge>}
                </div>
              )}
              {p.text.trim() ? p.text : <span className="text-muted">&nbsp;</span>}
            </div>
          ))}
        </div>
      )}
      {(props.length > 0 || sessions != null) && (
        <div className="rounded-lg border border-line">
          <div className="border-b border-line px-3 py-2 text-xs font-semibold">Document properties</div>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1 p-3 text-sm sm:grid-cols-[auto_1fr]">
            {props.map(([k, v]) => (<div key={k} className="contents"><dt className="text-muted">{k}</dt><dd className="break-words">{v}</dd></div>))}
            {sessions != null && <div className="contents"><dt className="text-muted">Editing sessions</dt><dd>{sessions}</dd></div>}
          </dl>
        </div>
      )}
    </div>
  );
}
