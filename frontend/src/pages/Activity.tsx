import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DownloadSimple } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useApi, useDebounced } from "@/lib/hooks";
import { Button, Card, Empty, ErrorBox, Field, Input, Loading, PageHeader, Select, cx } from "@/components/ui";
import type { ActivityRow } from "@/lib/types";

const ACTIONS = [
  "login",
  "upload",
  "verdict",
  "report_export",
  "role_change",
  "settings_llm",
  "login_failed",
  "view",
  "analysis",
  "review",
  "note",
  "ask",
  "verify",
  "compare",
  "export",
  "case_create",
  "case_delete",
  "evidence_delete",
  "account",
];

const ACTION_COLORS: Record<string, string> = {
  login: "bg-blue-50 text-blue-700 border-blue-200",
  upload: "bg-purple-50 text-purple-700 border-purple-200",
  verdict: "bg-amber-50 text-amber-700 border-amber-200",
  report_export: "bg-emerald-50 text-emerald-700 border-emerald-200",
  role_change: "bg-rose-50 text-rose-700 border-rose-200",
  settings_llm: "bg-indigo-50 text-indigo-700 border-indigo-200",
  export: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const dayLabel = (iso: string) => new Date(iso).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
const timeLabel = (iso: string) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

export default function Activity() {
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const dq = useDebounced(q, 300);
  const [people, setPeople] = useState<string[]>([]);

  const state = useApi(
    () => api.activity({ q: dq, action, actor, date_from: from, date_to: to, limit: 500 }).then((rows) => {
      setPeople((p) => Array.from(new Set([...p, ...rows.map((r) => r.actor)])).sort());
      return rows;
    }),
    [dq, action, actor, from, to],
  );
  const rows: ActivityRow[] | null = state.data ?? null;

  const groups = useMemo(() => {
    const m = new Map<string, ActivityRow[]>();
    (rows ?? []).forEach((r) => { const k = dayLabel(r.at); m.set(k, [...(m.get(k) ?? []), r]); });
    return Array.from(m.entries());
  }, [rows]);

  return (
    <div>
      <PageHeader title="Activity" subtitle="Everything that happened on the platform"
        actions={<a href={api.url.activityCsv()}><Button><DownloadSimple size={16} />Export CSV</Button></a>} />
      <Card className="mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="Search"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search activity" /></Field>
          <Field label="Action">
            <Select value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="">All actions</option>
              {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
            </Select>
          </Field>
          <Field label="Person">
            <Select value={actor} onChange={(e) => setActor(e.target.value)}>
              <option value="">Everyone</option>
              {people.map((p) => <option key={p} value={p}>{p}</option>)}
            </Select>
          </Field>
          <Field label="From"><Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
          <Field label="To"><Input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field>
        </div>
      </Card>
      {state.error ? <ErrorBox message={String(state.error)} /> : !rows ? <Loading /> : groups.length === 0 ? (
        <Card><Empty title="No activity found" hint="Try changing or clearing the filters." /></Card>
      ) : (
        <div className="space-y-4">
          {groups.map(([day, items]) => (
            <Card key={day}>
              <div className="border-b border-line px-4 py-2 text-xs font-semibold text-muted">{day}</div>
              <ul className="divide-y divide-line">
                {items.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
                    <span className="font-mono text-xs text-muted shrink-0">{timeLabel(r.at)}</span>
                    <span className={cx(
                      "rounded-full px-2 py-0.5 text-[10px] font-bold font-mono  border",
                      ACTION_COLORS[r.action] || "bg-surface2 text-muted border-line/60"
                    )}>
                      {r.action}
                    </span>
                    <span className="font-medium text-ink shrink-0">{r.actor}</span>
                    <span className="min-w-0 flex-1 break-words text-ink/80 text-xs">{r.summary}</span>
                    {r.evidence_id ? <Link className="text-accent hover:underline text-xs font-semibold" to={`/evidence/${r.evidence_id}`}>Evidence #{r.evidence_id}</Link>
                      : r.case_id ? <Link className="text-accent hover:underline text-xs font-semibold" to={`/cases/${r.case_id}`}>Case #{r.case_id}</Link> : null}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
