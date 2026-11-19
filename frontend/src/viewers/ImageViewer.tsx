import { useState } from "react";
import type { EvidenceFull } from "@/lib/types";
import { api } from "@/lib/api";
import { Segmented } from "@/components/ui";
import { has, findingsOf, isRegion } from "./parts/util";

const LAYERS = [
  { value: "original.jpg", label: "Original" },
  { value: "ela.png", label: "ELA" },
  { value: "noise.png", label: "Noise" },
  { value: "ai_heatmap.png", label: "AI heatmap" },
  { value: "clone.png", label: "Clone map" },
];

export default function ImageViewer({ ev }: { ev: EvidenceFull }) {
  const d = ev.details ?? {};
  const options = LAYERS.filter((l) => has(ev, l.value));
  const [layer, setLayer] = useState<string>(options[0]?.value ?? "original.jpg");
  const [hover, setHover] = useState<number | null>(null);
  const [pw, ph] = d.preview_size ?? [d.width ?? 0, d.height ?? 0];
  const sx = d.width && pw ? pw / d.width : 1;
  const sy = d.height && ph ? ph / d.height : 1;
  const boxes = findingsOf(ev).flatMap((f) => {
    const l = f.location;
    return (f.severity === "medium" || f.severity === "high") && isRegion(l) ? [{ f, l }] : [];
  });
  const showBoxes = layer === "original.jpg" && boxes.length > 0 && pw > 0 && ph > 0;

  if (options.length === 0) return <div className="p-4 text-muted">No image layers available.</div>;
  return (
    <div className="p-3 sm:p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="max-w-full overflow-x-auto"><Segmented value={layer} onChange={setLayer} options={options} /></div>
        <a href={`/compare?a=${ev.id}`} className="text-xs text-accent hover:underline">Compare</a>
      </div>
      <div className="flex justify-center rounded-lg bg-surface2 p-2">
        <div className="relative inline-block max-w-full">
          <img src={api.url.artifact(ev.id, layer)} alt={layer} className="block h-auto max-h-[70vh] w-auto max-w-full rounded" />
          {showBoxes && (
            <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 ${pw} ${ph}`} preserveAspectRatio="none">
              {boxes.map(({ f, l }, i) => (
                <rect key={f.id} x={l.x0 * sx} y={l.y0 * sy} width={Math.max(1, (l.x1 - l.x0) * sx)} height={Math.max(1, (l.y1 - l.y0) * sy)}
                  className="text-bad" stroke="currentColor" strokeWidth={2} vectorEffect="non-scaling-stroke"
                  fill={hover === i ? "rgba(220,38,38,0.3)" : "rgba(220,38,38,0.05)"} style={{ pointerEvents: "all" }}
                  onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
                  <title>{f.title}</title>
                </rect>
              ))}
            </svg>
          )}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span>{d.width && d.height ? `${d.width} x ${d.height} px` : "Size unknown"}</span>
        {typeof d.ai_score === "number" && <span>AI-generated {(d.ai_score * 100).toFixed(1)}%</span>}
        {typeof d.clone_matches === "number" && <span>Clone matches {d.clone_matches}</span>}
        {boxes.length > 0 && typeof d.clone_matches !== "number" && <span>{boxes.length} flagged region{boxes.length === 1 ? "" : "s"}</span>}
      </div>
    </div>
  );
}
