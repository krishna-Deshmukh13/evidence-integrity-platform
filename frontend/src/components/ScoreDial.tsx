// Circular 0-100 score dial. DO NOT EDIT. <ScoreDial score={42} size={150} />
import { scoreTone } from "@/lib/format";
const COLOR = { good: "var(--good)", warn: "var(--warn)", bad: "var(--bad)", muted: "var(--muted)" } as const;
export default function ScoreDial({ score, size = 140, label = "of 100" }: { score: number | null; size?: number; label?: string }) {
  const r = 44, c = 2 * Math.PI * r, arc = c * 0.75, v = score === null ? 0 : Math.max(0, Math.min(100, score)) / 100;
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`Score ${score ?? "unknown"} of 100`}>
      <g transform="rotate(135 50 50)">
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--surface2)" strokeWidth="8" strokeLinecap="round" strokeDasharray={`${arc} ${c}`} />
        <circle cx="50" cy="50" r={r} fill="none" stroke={COLOR[scoreTone(score)]} strokeWidth="8" strokeLinecap="round" strokeDasharray={`${arc * v} ${c}`} style={{ transition: "stroke-dasharray .6s" }} />
      </g>
      <text x="50" y="52" textAnchor="middle" fontSize="26" fontWeight="600" fill="var(--ink)">{score ?? "-"}</text>
      <text x="50" y="66" textAnchor="middle" fontSize="8" fill="var(--muted)">{label}</text>
    </svg>
  );
}
