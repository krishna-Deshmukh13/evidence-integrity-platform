import type { ReactNode } from "react";
import { Card, Field, Input, Select, cx } from "@/components/ui";
import type { CaseSummary, User } from "@/lib/types";
import { CATEGORIES, CHECKS, MEDIA, REVIEWS, VERDICTS, humanize, splitList, type Key, type Patch } from "./params";
import { CATEGORY_LABEL, MEDIA_LABEL, REVIEW_LABEL } from "@/lib/format";

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active}
      className={cx("rounded-full border px-3 py-1 text-xs font-medium transition", active ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface hover:bg-surface2")}>
      {children}
    </button>
  );
}

export function FilterPanel({ sp, patch, cases, users }: { sp: URLSearchParams; patch: Patch; cases: CaseSummary[]; users: User[] | null }) {
  const toggle = (key: Key, val: string) => {
    const cur = splitList(sp.get(key));
    const next = cur.includes(val) ? cur.filter((x) => x !== val) : [...cur, val];
    patch({ [key]: next.join(",") || undefined });
  };
  const has = (key: Key, val: string) => splitList(sp.get(key)).includes(val);
  const set = (key: Key) => (e: { target: { value: string } }) => patch({ [key]: e.target.value || undefined });

  return (
    <Card className="mb-4 space-y-4 p-4">
      <div className="space-y-3">
        <div>
          <div className="mb-1.5 text-xs font-medium text-muted">Type</div>
          <div className="flex flex-wrap gap-1.5">{MEDIA.map((m) => <Chip key={m} active={has("media_type", m)} onClick={() => toggle("media_type", m)}>{MEDIA_LABEL[m]}</Chip>)}</div>
        </div>
        <div>
          <div className="mb-1.5 text-xs font-medium text-muted">Verdict</div>
          <div className="flex flex-wrap gap-1.5">{VERDICTS.map((v) => <Chip key={v} active={has("verdict", v)} onClick={() => toggle("verdict", v)}>{v}</Chip>)}</div>
        </div>
        <div>
          <div className="mb-1.5 text-xs font-medium text-muted">Review</div>
          <div className="flex flex-wrap gap-1.5">{REVIEWS.map((r) => <Chip key={r} active={has("review_status", r)} onClick={() => toggle("review_status", r)}>{REVIEW_LABEL[r]}</Chip>)}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Finding category">
          <Select value={sp.get("category") ?? ""} onChange={set("category")}>
            <option value="">Any category</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>)}
          </Select>
        </Field>
        <Field label="Specific finding">
          <Select value={sp.get("check") ?? ""} onChange={set("check")}>
            <option value="">Any finding</option>
            {CHECKS.map((c) => <option key={c} value={c}>{humanize(c)}</option>)}
          </Select>
        </Field>
        <Field label="Case">
          <Select value={sp.get("case_id") ?? ""} onChange={set("case_id")}>
            <option value="">All cases</option>
            {cases.map((c) => <option key={c.id} value={c.id}>{c.reference} - {c.title}</option>)}
          </Select>
        </Field>
        {users && (
          <Field label="Assigned to">
            <Select value={sp.get("assignee_id") ?? ""} onChange={set("assignee_id")}>
              <option value="">Anyone</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.full_name || u.username}</option>)}
            </Select>
          </Field>
        )}
        <Field label="Score min">
          <Input type="number" min={0} max={100} inputMode="numeric" placeholder="0" value={sp.get("min_score") ?? ""} onChange={set("min_score")} />
        </Field>
        <Field label="Score max">
          <Input type="number" min={0} max={100} inputMode="numeric" placeholder="100" value={sp.get("max_score") ?? ""} onChange={set("max_score")} />
        </Field>
        <Field label="Received from">
          <Input type="date" value={sp.get("date_from") ?? ""} onChange={set("date_from")} />
        </Field>
        <Field label="Received to">
          <Input type="date" value={sp.get("date_to") ?? ""} onChange={set("date_to")} />
        </Field>
      </div>
    </Card>
  );
}
