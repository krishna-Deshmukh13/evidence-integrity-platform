import { useEffect, useState } from "react";
import { X } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { Category, EvidenceFull, ReviewStatus } from "@/lib/types";
import { CATEGORY_LABEL, REVIEW_LABEL } from "@/lib/format";
import ScoreDial from "@/components/ScoreDial";
import { Card, CardHeader, Input, Segmented, Select, VerdictText, useToast } from "@/components/ui";

const CAP: Record<Category, number> = { metadata: 30, pixel: 40, ai: 55, document: 45, audio: 55, container: 20 };
const STATUSES: ReviewStatus[] = ["not_reviewed", "reviewed", "flagged", "cleared"];

export default function Sidebar({ ev, reload }: { ev: EvidenceFull; reload: () => void }) {
  const { can } = useAuth();
  const toast = useToast();
  const inv = can("investigator");
  const users = useApi(() => (inv ? api.users() : Promise.resolve([])), [inv]);
  const [tags, setTags] = useState<string[]>(ev.tags);
  const [tag, setTag] = useState("");
  useEffect(() => setTags(ev.tags), [ev.tags]);

  const save = async (b: Parameters<typeof api.review>[1]) => {
    try { await api.review(ev.id, b); toast("Saved"); reload(); }
    catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
  };
  const cats = (Object.keys(CAP) as Category[]).filter((c) => (ev.breakdown[c] ?? 0) !== 0);
  const counts = { high: 0, medium: 0, low: 0, info: 0 };
  ev.findings.forEach((f) => { counts[f.severity] += 1; });
  const done = ev.status === "done";

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col items-center gap-2 p-4">
          {done && ev.score !== null ? <ScoreDial score={ev.score} /> : <div className="py-8 text-muted">Not scored yet</div>}
          <VerdictText verdict={ev.verdict} />
          <div className="text-xs text-muted">Trust score</div>
          {done && ev.ml_confidence && (
            <div className="mt-2 w-full rounded-lg border border-line bg-surface2/60 p-2 text-center text-xs">
              <div className="text-[11px] text-muted">AI probability estimate</div>
              <div className="font-semibold text-accent mt-0.5">{ev.ml_confidence.confidence_percent}% probability</div>
              <div className="text-[10px] text-muted mt-0.5 leading-tight">Estimated from file features</div>
            </div>
          )}
        </div>
        {done && (
          <div className="space-y-2 border-t border-line p-4">
            <div className="text-[11px] font-bold text-muted mb-1">
              Score Deduction Reasons
            </div>
            {cats.length === 0 && <div className="text-xs text-muted">No deductions · File structure authentic</div>}
            {cats.map((c) => {
              const v = Math.abs(ev.breakdown[c] ?? 0);
              return (
                <div key={c}>
                  <div className="flex justify-between text-xs"><span>{CATEGORY_LABEL[c]}</span><span className="font-mono text-bad">-{v}</span></div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface2"><div className="h-full rounded-full bg-bad" style={{ width: `${Math.min(100, (v / CAP[c]) * 100)}%` }} /></div>
                </div>
              );
            })}
            <div className="flex flex-wrap gap-3 pt-2 text-xs">
              <span className="text-bad">{counts.high} high</span><span className="text-warn">{counts.medium} medium</span>
              <span className="text-muted">{counts.low} low</span><span className="text-good">{counts.info} passed</span>
            </div>
          </div>
        )}
      </Card>
      <Card>
        <CardHeader title="Review status" />
        <div className="space-y-3 p-4">
          {inv ? (
            <Segmented value={ev.review_status} onChange={(v) => void save({ review_status: v })} options={STATUSES.map((s) => ({ value: s, label: REVIEW_LABEL[s] }))} />
          ) : <div className="text-sm">{REVIEW_LABEL[ev.review_status]}</div>}
          {inv && (
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-muted">Assigned to</span>
              <Select value={ev.assignee_id ?? ""} onChange={(e) => void (e.target.value === "" ? save({ unassign: true }) : save({ assignee_id: Number(e.target.value) }))}>
                <option value="">Unassigned</option>
                {(users.data ?? []).filter((u) => u.is_active).map((u) => <option key={u.id} value={u.id}>{u.full_name || u.username}</option>)}
              </Select>
            </label>
          )}
          <div>
            <span className="mb-1 block text-xs font-medium text-muted">Tags</span>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {tags.map((t) => (
                <span key={t} className="inline-flex items-center gap-1 rounded-md bg-accent-soft px-1.5 py-0.5 text-xs text-accent">
                  {t}{inv && <button aria-label={`Remove ${t}`} onClick={() => { const n = tags.filter((x) => x !== t); setTags(n); void save({ tags: n }); }}><X size={11} /></button>}
                </span>
              ))}
              {tags.length === 0 && !inv && <span className="text-xs text-muted">No tags</span>}
            </div>
            {inv && <Input value={tag} placeholder="Add a tag, press Enter" onChange={(e) => setTag(e.target.value)} onKeyDown={(e) => {
              if (e.key !== "Enter") return;
              const t = tag.trim();
              if (!t || tags.includes(t)) { setTag(""); return; }
              const n = [...tags, t]; setTags(n); setTag(""); void save({ tags: n });
            }} />}
          </div>
        </div>
      </Card>
    </div>
  );
}
