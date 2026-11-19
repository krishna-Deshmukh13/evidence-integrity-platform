import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowsClockwise,
  CheckCircle,
  ClockCounterClockwise,
  HourglassHigh,
  Queue,
  WarningCircle,
  Play,
  ArrowRight,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { ago } from "@/lib/format";

export default function AnalysisQueuePage() {
  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const { data: jobs, loading, error, reload } = useApi(
    () => api.queueJobs(),
    [],
    { intervalMs: 3500 }
  );

  const handleReanalyze = async (id: number) => {
    setRetryingId(id);
    try {
      await api.reanalyze(id);
      reload();
    } catch (err: any) {
      alert(`Re-analyze failed: ${err.message}`);
    } finally {
      setRetryingId(null);
    }
  };

  if (loading && !jobs) return <Loading label="Loading Waiting List" />;
  if (error && !jobs) return <ErrorBox message={error} onRetry={reload} />;

  const allJobs = jobs || [];

  const runningJobs = allJobs.filter((j: any) => j.status === "analyzing");
  const queuedJobs = allJobs.filter((j: any) => j.status === "queued");
  const failedJobs = allJobs.filter((j: any) => j.status === "failed");
  const completedJobs = allJobs.filter((j: any) => j.status === "done");

  const filteredJobs = allJobs.filter((j: any) => {
    if (filterStatus === "all") return true;
    return j.status === filterStatus;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            Background check queue
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Waiting List
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => reload()}
            className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3.5 py-1.5 text-xs font-semibold text-ink shadow-2xs hover:border-accent hover:text-accent transition-all active:scale-[0.98]"
          >
            <ArrowsClockwise size={13} className={cx(runningJobs.length > 0 && "animate-spin")} />
            Refresh list
          </button>
        </div>
      </div>

      {/* KPI Status Badges - Compact Bento Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div
          onClick={() => setFilterStatus("analyzing")}
          className={cx(
            "cursor-pointer rounded-lg border p-3.5 transition-colors card-bento",
            filterStatus === "analyzing"
              ? "border-accent bg-accent/5 ring-2 ring-accent/30 shadow-xs"
              : "border-line bg-surface hover:border-accent/40"
          )}
        >
          <div className="flex items-center justify-between text-xs text-muted">
            <span className="font-bold text-[10px]">Checking now</span>
            <span className="size-2 rounded-full bg-accent" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-accent tabular-nums">
            {runningJobs.length}
          </div>
          <div className="mt-0.5 text-[11px] text-muted">Files currently being checked</div>
        </div>

        <div
          onClick={() => setFilterStatus("queued")}
          className={cx(
            "cursor-pointer rounded-lg border p-3.5 transition-colors card-bento",
            filterStatus === "queued"
              ? "border-warn bg-warn/5 ring-2 ring-warn/30 shadow-xs"
              : "border-line bg-surface hover:border-warn/40"
          )}
        >
          <div className="flex items-center justify-between text-xs text-muted">
            <span className="font-bold text-[10px]">In Queue</span>
            <HourglassHigh size={14} className="text-warn" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-warn tabular-nums">
            {queuedJobs.length}
          </div>
          <div className="mt-0.5 text-[11px] text-muted">Awaiting pipeline thread</div>
        </div>

        <div
          onClick={() => setFilterStatus("done")}
          className={cx(
            "cursor-pointer rounded-lg border p-3.5 transition-colors card-bento",
            filterStatus === "done"
              ? "border-good bg-good/5 ring-2 ring-good/30 shadow-xs"
              : "border-line bg-surface hover:border-good/40"
          )}
        >
          <div className="flex items-center justify-between text-xs text-muted">
            <span className="font-bold text-[10px]">Completed</span>
            <CheckCircle size={14} className="text-good" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-good tabular-nums">
            {completedJobs.length}
          </div>
          <div className="mt-0.5 text-[11px] text-muted">Verified & sealed</div>
        </div>

        <div
          onClick={() => setFilterStatus("failed")}
          className={cx(
            "cursor-pointer rounded-lg border p-3.5 transition-colors card-bento",
            filterStatus === "failed"
              ? "border-bad bg-bad/5 ring-2 ring-bad/30 shadow-xs"
              : "border-line bg-surface hover:border-bad/40"
          )}
        >
          <div className="flex items-center justify-between text-xs text-muted">
            <span className="font-bold text-[10px]">Failed</span>
            <WarningCircle size={14} className="text-bad" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-bad tabular-nums">
            {failedJobs.length}
          </div>
          <div className="mt-0.5 text-[11px] text-muted">Parsing or model error</div>
        </div>
      </div>

      {/* Main Jobs Table */}
      <Card className="rounded-[28px] overflow-hidden">
        <CardHeader
          title={`PIPELINE TASKS (${filteredJobs.length})`}
          right={
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted font-medium">Filter:</span>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="h-8 rounded-full border border-line bg-surface px-3 text-xs font-semibold text-ink outline-none focus:border-accent shadow-xs"
              >
                <option value="all">All Jobs</option>
                <option value="analyzing">Checking now</option>
                <option value="queued">Queued</option>
                <option value="done">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          }
        />

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-line bg-surface2/60 text-muted uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="px-5 py-3.5">File / Case</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Pipeline Stage</th>
                <th className="px-5 py-3.5">Progress</th>
                <th className="px-5 py-3.5">Score & Verdict</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-muted">
                    No jobs matching this filter
                  </td>
                </tr>
              ) : (
                filteredJobs.map((j: any) => {
                  const isRunning = j.status === "analyzing";
                  const isQueued = j.status === "queued";
                  const isDone = j.status === "done";
                  const isFailed = j.status === "failed";

                  return (
                    <tr key={j.id} className="transition hover:bg-surface2/50 group">
                      <td className="px-5 py-4 min-w-[200px]">
                        <Link to={`/evidence/${j.id}`} className="font-semibold text-ink group-hover:text-accent transition block">
                          {j.filename}
                        </Link>
                        <div className="text-[11px] text-muted font-mono mt-0.5">
                          {j.case_reference} · <span className="uppercase">{j.media_type}</span>
                        </div>
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span
                          className={cx(
                            "inline-flex items-center gap-1.5 text-[11px] font-bold ",
                            isRunning
                              ? "text-accent"
                              : isQueued
                              ? "text-[#D97706]"
                              : isDone
                              ? "text-[#12B981]"
                              : "text-[#EF4444]"
                          )}
                        >
                          <span className={cx("size-1.5 rounded-full shrink-0", isRunning ? "bg-accent animate-ping" : isQueued ? "bg-[#D97706]" : isDone ? "bg-[#12B981]" : "bg-[#EF4444]")} />
                          {j.status}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 text-ink font-semibold whitespace-nowrap">
                        {j.stage || "-"}
                      </td>

                      <td className="px-5 py-3.5 min-w-[150px]">
                        <div className="flex items-center gap-2.5">
                          <div className="h-2 flex-1 rounded-full bg-surface2 overflow-hidden border border-line/40">
                            <div
                              className={cx(
                                "h-full rounded-full transition-colors",
                                isRunning
                                  ? "bg-accent bg-striped-animated"
                                  : isDone
                                  ? "bg-good"
                                  : isFailed
                                  ? "bg-bad"
                                  : "bg-warn"
                              )}
                              style={{ width: `${j.progress || 0}%` }}
                            />
                          </div>
                          <span className="font-mono text-[11px] text-muted tabular-nums w-8">
                            {j.progress || 0}%
                          </span>
                        </div>
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap">
                        {j.score !== null ? (
                          <div className="flex items-center gap-2">
                            <span
                              className={cx(
                                "font-mono text-xs font-bold tabular-nums",
                                j.score < 50
                                  ? "text-[#EF4444]"
                                  : j.score < 80
                                  ? "text-[#D97706]"
                                  : "text-[#12B981]"
                              )}
                            >
                              {j.score}/100
                            </span>
                            <span className="text-[11px] text-muted">({j.verdict})</span>
                          </div>
                        ) : (
                          <span className="text-muted text-[11px] italic">Evaluating...</span>
                        )}
                      </td>

                      <td className="px-5 py-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleReanalyze(j.id)}
                          disabled={retryingId === j.id}
                          className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink shadow-2xs hover:bg-surface2 hover:border-accent/40 transition-all disabled:opacity-50 inline-flex items-center gap-1.5"
                        >
                          <Play size={12} className={cx(retryingId === j.id && "animate-spin")} />
                          {retryingId === j.id ? "Queuing..." : "Re-analyze"}
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
