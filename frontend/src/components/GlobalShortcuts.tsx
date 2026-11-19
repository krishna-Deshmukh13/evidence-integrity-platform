import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Kbd, Modal } from "@/components/ui";

const GO: Record<string, string> = { d: "/", c: "/cases", s: "/search", m: "/compare", a: "/activity", u: "/users", h: "/how-it-works" };
const ROWS: { keys: string[]; label: string }[] = [
  { keys: ["/"], label: "Focus search" },
  { keys: ["a"], label: "Toggle assistant" },
  { keys: ["?"], label: "Show this dialog" },
  { keys: ["["], label: "Toggle sidebar" },
  { keys: ["g", "d"], label: "Go to dashboard" },
  { keys: ["g", "c"], label: "Go to cases" },
  { keys: ["g", "s"], label: "Go to search" },
  { keys: ["g", "m"], label: "Go to compare" },
  { keys: ["g", "a"], label: "Go to activity" },
  { keys: ["g", "u"], label: "Go to users" },
  { keys: ["g", "h"], label: "Go to how it works" },
  { keys: ["1", "-", "7"], label: "Switch evidence tabs" },
];

export default function GlobalShortcuts() {
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const pending = useRef<number | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable)) return;
      if (pending.current !== null) {
        window.clearTimeout(pending.current);
        pending.current = null;
        const dest = GO[e.key.toLowerCase()];
        if (dest) { e.preventDefault(); nav(dest); return; }
      }
      if (e.key === "/") { e.preventDefault(); document.getElementById("global-search")?.focus(); }
      else if (e.key === "?") { e.preventDefault(); setOpen(true); }
      else if (e.key === "[") { document.getElementById("sidebar-toggle")?.click(); }
      else if (e.key === "g") { pending.current = window.setTimeout(() => { pending.current = null; }, 1200); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [nav]);

  return (
    <Modal open={open} onClose={() => setOpen(false)} title="Keyboard shortcuts">
      <ul className="space-y-2">
        {ROWS.map((r) => (
          <li key={r.label} className="flex items-center justify-between gap-3">
            <span>{r.label}</span>
            <span className="flex items-center gap-1">
              {r.keys.map((k, i) => (k === "-" ? <span key={i} className="text-muted">to</span> : <Kbd key={i}>{k}</Kbd>))}
            </span>
          </li>
        ))}
      </ul>
    </Modal>
  );
}
