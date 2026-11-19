import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { ArrowsLeftRight } from "@phosphor-icons/react";
import { Card, CardHeader, Empty, Segmented } from "@/components/ui";
import { api } from "@/lib/api";

type Mode = "swipe" | "diff" | "side";

function Swipe({ a, b }: { a: string; b: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState(50);
  const [ratio, setRatio] = useState(4 / 3);
  const move = (e: PointerEvent<HTMLDivElement>) => {
    const el = box.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPos(Math.min(100, Math.max(0, ((e.clientX - r.left) / r.width) * 100)));
  };
  const key = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowLeft") setPos((p) => Math.max(0, p - 3));
    if (e.key === "ArrowRight") setPos((p) => Math.min(100, p + 3));
  };
  return (
    <div ref={box} className="relative mx-auto w-full max-w-3xl cursor-ew-resize select-none overflow-hidden rounded-lg border border-line bg-surface2"
      style={{ aspectRatio: ratio, touchAction: "none" }}
      onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); move(e); }}
      onPointerMove={(e) => { if (e.currentTarget.hasPointerCapture(e.pointerId)) move(e); }}
      onPointerUp={(e) => e.currentTarget.releasePointerCapture(e.pointerId)}>
      <img src={a} alt="A" draggable={false} className="pointer-events-none absolute inset-0 size-full object-fill"
        onLoad={(e) => { const i = e.currentTarget; if (i.naturalWidth && i.naturalHeight) setRatio(i.naturalWidth / i.naturalHeight); }} />
      <img src={b} alt="B" draggable={false} className="pointer-events-none absolute inset-0 size-full object-fill" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }} />
      <span className="absolute left-2 top-2 rounded bg-surface px-1.5 py-0.5 text-xs font-semibold">B</span>
      <span className="absolute right-2 top-2 rounded bg-surface px-1.5 py-0.5 text-xs font-semibold">A</span>
      <div role="slider" tabIndex={0} aria-label="Swipe position" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pos)} onKeyDown={key}
        className="absolute inset-y-0 w-0.5 -translate-x-1/2 bg-accent outline-none" style={{ left: `${pos}%` }}>
        <span className="absolute left-1/2 top-1/2 grid size-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-line bg-surface text-accent shadow-lg"><ArrowsLeftRight size={16} /></span>
      </div>
    </div>
  );
}

export function ImageCompare({ aId, bId, diff }: { aId: number; bId: number; diff: string | null }) {
  const [mode, setMode] = useState<Mode>("swipe");
  const a = api.url.artifact(aId, "original.jpg");
  const b = api.url.artifact(bId, "original.jpg");
  return (
    <Card>
      <CardHeader title="Images" right={<Segmented<Mode> value={mode} onChange={setMode} options={[{ value: "swipe", label: "Swipe" }, { value: "diff", label: "Difference" }, { value: "side", label: "Side by side" }]} />} />
      <div className="p-4">
        {mode === "swipe" && <Swipe a={a} b={b} />}
        {mode === "diff" && (diff
          ? <div className="mx-auto max-w-3xl"><img src={diff} alt="Difference map" className="w-full rounded-lg border border-line" /><p className="mt-2 text-xs text-muted">Red marks pixels that changed between A and B, drawn over a grey copy of A.</p></div>
          : <Empty title="No difference map" hint="The server did not produce a difference image for this pair." />)}
        {mode === "side" && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {[{ t: "A", s: a }, { t: "B", s: b }].map((x) => (
              <figure key={x.t}><figcaption className="mb-1 text-xs font-semibold text-muted">{x.t}</figcaption><img src={x.s} alt={x.t} className="w-full rounded-lg border border-line" /></figure>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
