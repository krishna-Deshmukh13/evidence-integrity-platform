import { useState } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle,
  Flag,
  Hourglass,
  MagnifyingGlass,
  ShieldCheck,
  Tag,
  UserCheck,
  ArrowUpRight,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import type { ReviewStatus } from "@/lib/types";

const COLUMNS: {
  status: ReviewStatus;
  label: string;
  icon: any;
  color: string;
  badge: string;
  columnTint: string;
}[] = [
  {
    status: "not_reviewed",
    label: "Waiting for review",
    icon: Hourglass,
    color: "text-muted",
    badge: "bg-surface text-muted border border-line",
    columnTint: "bg-surface2/50 border-line/70",
  },
  {
    status: "flagged",
    label: "Suspicious",
    icon: Flag,
    color: "text-[#EF4444]",
    badge: "bg-[#FEECEC] text-[#EF4444] border border-[#EF4444]/20",
    columnTint: "bg-[#FEECEC]/30 dark:bg-rose-950/20 border-[#EF4444]/20",
  },
  {
    status: "reviewed",
    label: "Under review",
    icon: UserCheck,
    color: "text-accent",
    badge: "bg-[#EBEBFE] text-accent border border-accent/20",
    columnTint: "bg-[#EBEBFE]/30 dark:bg-indigo-950/20 border-accent/20",
  },
  {
    status: "cleared",
    label: "Looks genuine",
    icon: CheckCircle,
    color: "text-[#12B981]",
    badge: "bg-[#E8FAF3] text-[#12B981] border border-[#12B981]/20",
    columnTint: "bg-[#E8FAF3]/30 dark:bg-emerald-950/20 border-[#12B981]/20",
  },
];

export default function MyTasksPage() {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const { data: searchResults, loading, error, reload } = useApi(() => api.search({}), []);

  const handleUpdateStatus = async (evidenceId: number, newStatus: ReviewStatus) => {
    setUpdatingId(evidenceId);
    try {
      await api.patchEvidence(evidenceId, { review_status: newStatus });
      setNotice(`Updated review status to: ${newStatus.replace("_", " ")}`);
      setTimeout(() => setNotice(null), 3000);
      reload();
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading && !searchResults) return <Loading label="Loading Review Tasks" />;
  if (error && !searchResults) return <ErrorBox message={error} onRetry={reload} />;

  const allItems: any[] = searchResults || [];

  const filteredItems = allItems.filter((it: any) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        it.filename.toLowerCase().includes(q) ||
        it.case_reference.toLowerCase().includes(q) ||
        it.case_title.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold text-muted">
            Review queue
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Waiting for review
          </h1>
        </div>

        {/* Search Input in Pill Shape */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <MagnifyingGlass size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter files..."
              className="h-9 w-48 sm:w-64 rounded-full border border-line bg-surface pl-9 pr-3 text-xs font-medium outline-none focus:border-accent transition shadow-2xs"
            />
          </div>
        </div>
      </div>

      {notice && (
        <div className="rounded-full border border-accent/30 bg-[#EBEBFE] px-5 py-3 text-xs text-accent font-bold flex items-center justify-between shadow-xs">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="font-bold underline ml-2 cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* 4 Kanban Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-start">
        {COLUMNS.map((col) => {
          const colItems = filteredItems.filter((it: any) => it.review_status === col.status);
          const ColIcon = col.icon;

          return (
            <div
              key={col.status}
              className={cx(
                "flex flex-col gap-3 rounded-lg border p-3.5 transition-colors",
                col.columnTint
              )}
            >
              {/* Column Header */}
              <div className="flex items-center justify-between px-1.5 py-0.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-ink">
                  <ColIcon size={15} className={col.color} weight="bold" />
                  <span>{col.label}</span>
                </div>
                <span className={cx("font-mono text-xs font-extrabold tabular-nums", col.color)}>
                  {colItems.length}
                </span>
              </div>

              {/* Column Cards */}
              <div className="space-y-3 min-h-[320px]">
                {colItems.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-line/80 p-6 text-center text-xs text-muted font-medium">
                    No items in {col.label}
                  </div>
                ) : (
                  colItems.map((item: any) => {
                    const isHighRisk = item.score !== null && item.score < 50;

                    return (
                      <div
                        key={item.id}
                        className="rounded-xl border border-line bg-surface p-3.5 shadow-[var(--shadow-bento)] space-y-2.5 transition-colors hover:shadow-[var(--shadow-bento-hover)] hover:border-accent/30 select-none"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            to={`/evidence/${item.id}`}
                            className="font-bold text-xs sm:text-sm text-ink hover:text-accent line-clamp-1 transition-colors flex-1"
                          >
                            {item.filename}
                          </Link>
                          <span
                            className={cx(
                              "font-mono text-xs font-bold tabular-nums shrink-0",
                              isHighRisk ? "text-[#EF4444]" : "text-[#F59E0B]"
                            )}
                          >
                            {item.score ?? "-"}
                          </span>
                        </div>

                        <div className="text-xs text-muted font-medium flex items-center justify-between">
                          <span className="font-mono text-[11px] text-accent font-bold">
                            {item.case_reference}
                          </span>
                          <span className="uppercase text-[10px] font-bold tracking-wider text-muted/80">
                            {item.media_type}
                          </span>
                        </div>

                        {/* Move To Status Pills */}
                        <div className="pt-3 border-t border-line/60 flex items-center justify-between text-[11px]">
                          <span className="text-muted font-bold">Move:</span>
                          <div className="flex items-center gap-1.5">
                            {col.status !== "flagged" && (
                              <button
                                onClick={() => handleUpdateStatus(item.id, "flagged")}
                                disabled={updatingId === item.id}
                                className="rounded-full px-2.5 py-1 bg-[#FEECEC] text-[#EF4444] border border-[#EF4444]/20 font-bold hover:bg-[#EF4444] hover:text-white transition cursor-pointer disabled:opacity-50"
                                title="Mark as Flagged"
                              >
                                Flag
                              </button>
                            )}
                            {col.status !== "reviewed" && (
                              <button
                                onClick={() => handleUpdateStatus(item.id, "reviewed")}
                                disabled={updatingId === item.id}
                                className="rounded-full px-2.5 py-1 bg-[#EBEBFE] text-accent border border-accent/20 font-bold hover:bg-accent hover:text-white transition cursor-pointer disabled:opacity-50"
                                title="Mark as Reviewed"
                              >
                                Review
                              </button>
                            )}
                            {col.status !== "cleared" && (
                              <button
                                onClick={() => handleUpdateStatus(item.id, "cleared")}
                                disabled={updatingId === item.id}
                                className="rounded-full px-2.5 py-1 bg-[#E8FAF3] text-[#12B981] border border-[#12B981]/20 font-bold hover:bg-[#12B981] hover:text-white transition cursor-pointer disabled:opacity-50"
                                title="Clear Item"
                              >
                                Clear
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
