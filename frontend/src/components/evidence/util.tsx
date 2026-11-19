import { useState, type ReactNode } from "react";
import { Check, Copy } from "@phosphor-icons/react";
import type { Location } from "@/lib/types";
import { Button } from "@/components/ui";

export function CopyButton({ text, label }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button size="sm" variant="ghost" title="Copy" onClick={() => {
      void navigator.clipboard?.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); });
    }}>
      {done ? <Check size={13} /> : <Copy size={13} />}{label}
    </Button>
  );
}

const r = (n: number) => String(Math.round(n));
const s1 = (n: number) => `${(Math.round(n * 10) / 10).toString()}s`;

export function whereText(l: Location | null): string | null {
  if (!l) return null;
  switch (l.kind) {
    case "region": return `from (${r(l.x0)}, ${r(l.y0)}) to (${r(l.x1)}, ${r(l.y1)})`;
    case "field": return l.name;
    case "time": return `${s1(l.start)} to ${s1(l.end)}`;
    case "page": return `page ${l.page}`;
    case "paragraph": return `paragraph ${l.indices.join(", ")}`;
  }
}

function inline(t: string): ReactNode[] {
  return t.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith("**") && p.endsWith("**") && p.length > 4 ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>);
}

export function Markdown({ text }: { text: string }) {
  const out: ReactNode[] = [];
  let bullets: string[] = [];
  const flush = (k: number) => {
    if (bullets.length) {
      out.push(<ul key={`u${k}`} className="my-2 list-disc space-y-1 pl-5">{bullets.map((b, i) => <li key={i}>{inline(b)}</li>)}</ul>);
      bullets = [];
    }
  };
  text.split("\n").forEach((line, i) => {
    const t = line.trim();
    if (/^[-*] /.test(t)) { bullets.push(t.slice(2)); return; }
    flush(i);
    if (/^#{1,6} /.test(t)) out.push(<h4 key={i} className="mb-1 mt-4 text-sm font-semibold">{inline(t.replace(/^#+ /, ""))}</h4>);
    else if (t) out.push(<p key={i} className="my-2 leading-relaxed">{inline(t)}</p>);
  });
  flush(-1);
  return <div className="text-sm">{out}</div>;
}
