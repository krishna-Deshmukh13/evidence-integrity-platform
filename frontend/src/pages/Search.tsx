import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Funnel, MagnifyingGlass, X } from "@phosphor-icons/react";
import { Button, Card, Empty, ErrorBox, PageHeader, Select, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useDebounced } from "@/lib/hooks";
import { CATEGORY_LABEL, MEDIA_LABEL, REVIEW_LABEL } from "@/lib/format";
import type { CaseSummary, Category, MediaType, ReviewStatus, SearchRow, User } from "@/lib/types";
import { FilterPanel } from "@/components/search/FilterPanel";
import { ResultRow } from "@/components/search/ResultRow";
import CaseGraphTab from "@/components/case/CaseGraphTab";
import { KEYS, MULTI, humanize, splitList, toSearchParams, type Key, type Patch } from "@/components/search/params";

type ActiveChip = { key: Key; value: string; label: string };

export default function Search() {
  const [sp, setSp] = useSearchParams();
  const { can } = useAuth();
  const canAssign = can("investigator");
  const spStr = sp.toString();

  const patch: Patch = useCallback((p) => {
    setSp((prev) => {
      const n = new URLSearchParams(prev);
      Object.entries(p).forEach(([k, v]) => { if (v === undefined || v === "") n.delete(k); else n.set(k, v); });
      return n;
    }, { replace: true });
  }, [setSp]);

  const urlQ = sp.get("q") ?? "";
  const [q, setQ] = useState(urlQ);
  const dq = useDebounced(q, 300);
  useEffect(() => { if (dq !== (new URLSearchParams(window.location.search).get("q") ?? "")) patch({ q: dq || undefined }); }, [dq]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setQ(urlQ); }, [urlQ]);

  const [showFilters, setShowFilters] = useState(() => KEYS.some((k) => k !== "q" && k !== "sort" && sp.get(k)));
  const [viewMode, setViewMode] = useState<"list" | "graph">("list");
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [users, setUsers] = useState<User[] | null>(null);
  useEffect(() => { api.cases().then(setCases).catch(() => setCases([])); }, []);
  useEffect(() => { if (canAssign) api.users().then(setUsers).catch(() => setUsers([])); }, [canAssign]);

  const [rows, setRows] = useState<SearchRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let dead = false;
    setLoading(true);
    api.search(toSearchParams(new URLSearchParams(spStr)))
      .then((r) => { if (!dead) { setRows(r); setError(null); } })
      .catch((e: unknown) => { if (!dead) setError(e instanceof Error ? e.message : "Search failed"); })
      .finally(() => { if (!dead) setLoading(false); });
    return () => { dead = true; };
  }, [spStr, tick]);

  const chips = useMemo<ActiveChip[]>(() => {
    const out: ActiveChip[] = [];
    const params = new URLSearchParams(spStr);
    const get = (k: Key) => params.get(k) ?? "";
    MULTI.forEach((k) => splitList(get(k)).forEach((v) => {
      const label = k === "media_type" ? (MEDIA_LABEL[v as MediaType] ?? v) : k === "review_status" ? (REVIEW_LABEL[v as ReviewStatus] ?? v) : v;
      out.push({ key: k, value: v, label });
    }));
    if (get("category")) out.push({ key: "category", value: get("category"), label: `Category: ${CATEGORY_LABEL[get("category") as Category] ?? get("category")}` });
    if (get("check")) out.push({ key: "check", value: get("check"), label: `Finding: ${humanize(get("check"))}` });
    if (get("case_id")) { const c = cases.find((x) => String(x.id) === get("case_id")); out.push({ key: "case_id", value: get("case_id"), label: `Case: ${c ? c.reference : get("case_id")}` }); }
    if (get("assignee_id")) { const u = users?.find((x) => String(x.id) === get("assignee_id")); out.push({ key: "assignee_id", value: get("assignee_id"), label: `Assigned: ${u ? u.full_name || u.username : get("assignee_id")}` }); }
    if (get("min_score")) out.push({ key: "min_score", value: get("min_score"), label: `Score ≥ ${get("min_score")}` });
    if (get("max_score")) out.push({ key: "max_score", value: get("max_score"), label: `Score ≤ ${get("max_score")}` });
    if (get("date_from")) out.push({ key: "date_from", value: get("date_from"), label: `From ${get("date_from")}` });
    if (get("date_to")) out.push({ key: "date_to", value: get("date_to"), label: `To ${get("date_to")}` });
    return out;
  }, [spStr, cases, users]);

  const removeChip = (c: ActiveChip) => {
    if (MULTI.includes(c.key)) {
      const next = splitList(sp.get(c.key)).filter((x) => x !== c.value);
      patch({ [c.key]: next.join(",") || undefined });
    } else patch({ [c.key]: undefined });
  };
  const clearAll = () => {
    const p: Partial<Record<Key, string | undefined>> = {};
    KEYS.forEach((k) => { if (k !== "sort") p[k] = undefined; });
    setQ("");
    patch(p);
  };

  const sort = sp.get("sort") === "newest" ? "newest" : "risk";

  return (
    <div>
      <PageHeader title="Search files" subtitle="Find files across every case" />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <MagnifyingGlass size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by filename, case name, tag, or details..."
            className="h-10 w-full rounded-full border border-line bg-surface pl-10 pr-9 text-xs sm:text-sm font-medium outline-none focus:border-accent focus:ring-2 focus:ring-accent/15 transition-all shadow-2xs"
          />
          {q && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => setQ("")}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink cursor-pointer"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            className={cx("h-10 flex-1 sm:flex-none rounded-full", viewMode === "graph" && "border-accent text-accent font-bold")}
            onClick={() => setViewMode((m) => (m === "list" ? "graph" : "list"))}
          >
            {viewMode === "list" ? "Connected files graph" : "File list"}
          </Button>
          <Button
            className={cx("h-10 flex-1 sm:flex-none rounded-full", showFilters && "border-accent text-accent")}
            onClick={() => setShowFilters((s) => !s)}
          >
            <Funnel size={14} />Filters ({chips.length})
          </Button>
          <Select
            aria-label="Sort"
            value={sort}
            onChange={(e) => patch({ sort: e.target.value })}
            className="h-10 flex-1 sm:w-44 sm:flex-none rounded-full"
          >
            <option value="risk">Most suspicious first</option>
            <option value="newest">Newest first</option>
          </Select>
        </div>
      </div>

      {showFilters && <FilterPanel sp={sp} patch={patch} cases={cases} users={canAssign ? users ?? [] : null} />}

      {viewMode === "graph" ? (
        <div className="mt-4">
          <CaseGraphTab crossCase={true} />
        </div>
      ) : (
        <>
          {(chips.length > 0 || q) && (
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          {chips.map((c) => (
            <span key={`${c.key}:${c.value}`} className="inline-flex items-center gap-1 rounded-full bg-accent-soft py-1 pl-3 pr-1.5 text-xs font-medium text-accent">
              {c.label}
              <button type="button" aria-label={`Remove ${c.label}`} onClick={() => removeChip(c)} className="grid size-4 place-items-center rounded-full hover:bg-surface"><X size={10} /></button>
            </span>
          ))}
          <button type="button" onClick={clearAll} className="px-2 text-xs font-medium text-muted hover:text-ink">Clear all</button>
        </div>
      )}

      {error ? <ErrorBox message={error} onRetry={() => setTick((t) => t + 1)} /> : (
        <>
          <div className="mb-2 flex items-center gap-2 text-sm text-muted">
            {rows ? <span>{rows.length} result{rows.length === 1 ? "" : "s"}</span> : <span>Searching</span>}
            {loading && rows && <span className="inline-block size-3 animate-spin rounded-full border-2 border-line border-t-accent" />}
          </div>
          <Card className={cx("divide-y divide-line overflow-hidden", loading && rows && "opacity-60 transition-opacity")}>
            {rows === null && Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="flex animate-pulse items-center gap-3 px-4 py-3">
                <div className="size-9 rounded-lg bg-surface2" />
                <div className="flex-1 space-y-2"><div className="h-3.5 w-1/3 rounded bg-surface2" /><div className="h-3 w-1/2 rounded bg-surface2" /></div>
                <div className="h-5 w-9 rounded bg-surface2" />
              </div>
            ))}
            {rows?.length === 0 && <Empty title="No matching evidence" hint="Try a different search or remove some filters." action={chips.length > 0 || q ? <Button size="sm" onClick={clearAll}>Clear all</Button> : undefined} />}
            {rows?.map((r) => <ResultRow key={r.id} r={r} />)}
          </Card>
        </>
      )}
      </>
      )}
    </div>
  );
}
