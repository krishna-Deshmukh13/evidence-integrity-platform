import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ClockCounterClockwise,
  CalendarCheck,
  Warning,
  FileText,
  MagnifyingGlass,
  Funnel,
  ShieldCheck,
  CheckCircle,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function TimelinePage() {
  const { data: timelineData, loading, error, reload } = useApi(() => api.timeline(), []);
  const [filterType, setFilterType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  if (loading && !timelineData) return <Loading label="Loading Forensic Timeline" />;
  if (error && !timelineData) return <ErrorBox message={error} onRetry={reload} />;

  const events = timelineData?.events || [];
  const contradictions = timelineData?.contradictions || [];

  // Filter events
  const filteredEvents = events.filter((ev: any) => {
    if (filterType !== "all" && ev.kind !== filterType) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        ev.filename?.toLowerCase().includes(q) ||
        ev.case_reference?.toLowerCase().includes(q) ||
        ev.label?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  // Group events by date (YYYY-MM-DD)
  const grouped: Record<string, any[]> = {};
  filteredEvents.forEach((ev: any) => {
    const d = ev.timestamp ? ev.timestamp.substring(0, 10) : "Unknown Date";
    if (!grouped[d]) grouped[d] = [];
    grouped[d].push(ev);
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            Order of events
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-ink mt-1">
            Timeline
          </h1>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Search filter */}
          <div className="relative">
            <MagnifyingGlass size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search timeline..."
              className="h-10 w-48 sm:w-64 rounded-full border border-line bg-surface pl-9 pr-4 text-xs font-medium outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all shadow-xs"
            />
          </div>

          {/* Type filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="h-10 rounded-full border border-line bg-surface px-4 text-xs font-semibold text-ink outline-none focus:border-accent shadow-xs"
          >
            <option value="all">All events</option>
            <option value="created">File recorded</option>
            <option value="modified">File edited</option>
            <option value="uploaded">File uploaded</option>
            <option value="verified">File checked</option>
          </select>
        </div>
      </div>

      {/* Contradictions Alert Box */}
      {contradictions.length > 0 && (
        <div className="rounded-[24px] border border-[#EF4444]/20 bg-[#FEECEC] dark:bg-bad/10 p-5 space-y-3 shadow-sm card-bento">
          <div className="flex items-center gap-2 text-bad font-extrabold text-sm">
            <Warning size={20} weight="bold" className="animate-bounce" />
            <span>{contradictions.length} Timeline mismatch(es) found</span>
          </div>
          <div className="divide-y divide-bad/20 text-xs">
            {contradictions.map((c: any, i: number) => (
              <div key={i} className="py-2.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="font-bold text-ink mr-2">{c.filename}</span>
                  <span className="text-muted mr-2 font-mono text-[11px]">({c.case_reference})</span>
                  <span className="text-bad font-medium">{c.message}</span>
                </div>
                {c.evidence_id && (
                  <Link
                    to={`/evidence/${c.evidence_id}`}
                    className="inline-flex items-center gap-1 rounded-full bg-bad text-white px-3 py-1 text-[11px] font-bold shadow-xs hover:bg-bad/90 transition shrink-0"
                  >
                    See file →
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grouped Chronological Timeline */}
      <div className="space-y-6">
        {Object.keys(grouped).length === 0 ? (
          <Empty title="No timeline events found for this filter" />
        ) : (
          Object.entries(grouped).map(([date, dateEvents]) => (
            <div key={date} className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-extrabold text-muted">
                <CalendarCheck size={16} className="text-accent" />
                <span>{new Date(date).toLocaleDateString(undefined, { weekday: "short", year: "numeric", month: "short", day: "numeric" })}</span>
                <span className="ml-1 rounded-full bg-[#EBEBFE] text-accent px-2.5 py-0.5 text-[10px] font-bold">
                  {dateEvents.length} events
                </span>
              </div>

              <div className="relative pl-6 border-l-2 border-line/80 space-y-4">
                {dateEvents.map((ev: any, idx: number) => {
                  const isCreated = ev.kind === "created";
                  const isMod = ev.kind === "modified";
                  const isUpload = ev.kind === "uploaded";

                  return (
                    <div
                      key={idx}
                      className="relative rounded-[22px] border border-line bg-surface p-5 shadow-xs card-bento transition-colors hover:border-accent/40"
                    >
                      {/* Timeline dot marker */}
                      <span
                        className={cx(
                          "absolute -left-[31px] top-6 size-3.5 rounded-full border-2 border-bg ring-2 ring-line",
                          isCreated ? "bg-good" : isMod ? "bg-warn" : isUpload ? "bg-accent" : "bg-muted"
                        )}
                      />

                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={cx(
                              "rounded-full px-2.5 py-0.5 text-[10px] font-bold ",
                              isCreated
                                ? "bg-[#E8FAF3] text-[#12B981] dark:bg-good/20 dark:text-good"
                                : isMod
                                ? "bg-[#FFF5E0] text-[#D97706] dark:bg-warn/20 dark:text-warn"
                                : "bg-[#EBEBFE] text-accent dark:bg-accent/20 dark:text-accent"
                            )}
                          >
                            {ev.label || ev.kind}
                          </span>
                          <span className="text-xs text-muted font-mono tabular-nums">
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ""}
                          </span>
                        </div>

                        <Link
                          to={`/evidence/${ev.evidence_id}`}
                          className="text-xs font-semibold text-accent hover:underline flex items-center gap-1"
                        >
                          View evidence item →
                        </Link>
                      </div>

                      <div className="mt-2.5">
                        <span className="text-sm font-bold text-ink">{ev.filename}</span>
                        <span className="text-xs text-muted ml-2 font-mono">({ev.case_reference} · {ev.case_title})</span>
                      </div>

                      {ev.provenance && (
                        <div className="mt-2 text-xs text-muted font-mono bg-surface2/60 px-3 py-1.5 rounded-xl border border-line/40 inline-block">
                          Source: {ev.provenance}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
