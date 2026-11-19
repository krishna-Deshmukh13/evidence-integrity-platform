import { useEffect, useRef, useState } from "react";
import { CaretDown, MagnifyingGlass } from "@phosphor-icons/react";
import { Input, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import type { SearchRow } from "@/lib/types";
import { MediaIcon } from "./MediaIcon";

export function Picker({ tag, id, row, onPick }: { tag: string; id: number | null; row: SearchRow | undefined; onPick: (r: SearchRow) => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 300);
  const [res, setRes] = useState<SearchRow[] | null>(null);
  const [failed, setFailed] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    let dead = false;
    setRes(null);
    api.search({ q: dq || undefined, sort: "newest" })
      .then((r) => { if (!dead) { setRes(r.slice(0, 10)); setFailed(false); } })
      .catch(() => { if (!dead) { setRes([]); setFailed(true); } });
    return () => { dead = true; };
  }, [open, dq]);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);

  return (
    <div ref={box} className="relative min-w-0">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="flex h-14 w-full items-center gap-3 rounded-xl border border-line bg-surface px-3 text-left hover:bg-surface2">
        <span className="grid size-7 shrink-0 place-items-center rounded-md bg-accent-soft text-xs font-semibold text-accent">{tag}</span>
        {row ? (
          <>
            <MediaIcon type={row.media_type} className="shrink-0 text-muted" />
            <span className="min-w-0 flex-1"><span className="block truncate font-medium">{row.filename}</span><span className="block truncate text-xs text-muted">{row.case_reference} · {row.case_title}</span></span>
          </>
        ) : (
          <span className="min-w-0 flex-1 truncate text-muted">{id ? `Evidence #${id}` : "Choose evidence"}</span>
        )}
        <CaretDown size={14} className="shrink-0 text-muted" />
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 rounded-xl border border-line bg-surface p-2 shadow-xs">
          <div className="relative mb-2">
            <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <Input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search filename, case, tag" className="pl-8" />
          </div>
          <div className="max-h-72 overflow-y-auto">
            {res === null && <div className="flex justify-center py-4"><Spinner /></div>}
            {res !== null && res.length === 0 && <div className="px-2 py-4 text-center text-sm text-muted">{failed ? "Search failed" : "No matches"}</div>}
            {res?.map((r) => (
              <button key={r.id} type="button" onClick={() => { onPick(r); setOpen(false); setQ(""); }}
                className={cx("flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-surface2", r.id === id && "bg-accent-soft")}>
                <MediaIcon type={r.media_type} size={16} className="shrink-0 text-muted" />
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{r.filename}</span><span className="block truncate text-xs text-muted">{r.case_reference}</span></span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
