import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Calendar,
  Clock,
  FileText,
  ShieldCheck,
  UploadSimple,
  Warning,
  WarningCircle,
  PencilSimple,
  Camera,
} from "@phosphor-icons/react";
import { Card, Empty, ErrorBox, Loading, ScoreChip, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { ago } from "@/lib/format";
import type { TimelineEvent, TimelineContradiction } from "@/lib/types";
import { MediaIcon } from "@/components/case/helpers";

function EventIcon({ kind }: { kind: TimelineEvent["kind"] }) {
  const cls = "size-3.5";
  switch (kind) {
    case "created":
      return <Camera className={cls} />;
    case "modified":
      return <PencilSimple className={cls} />;
    case "upload":
      return <UploadSimple className={cls} />;
    case "custody":
      return <ShieldCheck className={cls} />;
    default:
      return <Clock className={cls} />;
  }
}

function kindTone(kind: TimelineEvent["kind"]) {
  switch (kind) {
    case "created":
      return "bg-accent/15 text-accent border-accent/30";
    case "modified":
      return "bg-warn/15 text-warn border-warn/30";
    case "upload":
      return "bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30";
    case "custody":
      return "bg-good/15 text-good border-good/30";
    default:
      return "bg-surface2 text-muted border-line";
  }
}

export default function CaseTimelineTab({ caseId }: { caseId: number }) {
  const { data: t, error, loading, reload } = useApi(() => api.caseTimeline(caseId), [caseId]);
  const [filter, setFilter] = useState<string>("all");

  if (loading && !t) return <Loading />;
  if (error && !t) return <ErrorBox message={error} onRetry={reload} />;
  if (!t) return null;

  const filteredEvents =
    filter === "all"
      ? t.events
      : t.events.filter((e) => e.kind === filter);

  return (
    <div className="space-y-4">
      {/* 1. Flagged Contradictions Alert */}
      {t.contradictions.length > 0 && (
        <Card className="border-bad/60 bg-bad/5 p-4">
          <div className="flex items-center gap-2 font-semibold text-bad">
            <WarningCircle size={20} weight="fill" />
            <span>{t.contradictions.length} Chronological Contradictions Detected</span>
          </div>
          <p className="mt-1 text-xs text-muted">
            The forensic timeline revealed inconsistent metadata timestamps between file creation,
            modification, intake, or future system clocks.
          </p>

          <div className="mt-3 space-y-2">
            {t.contradictions.map((c, i) => (
              <div
                key={i}
                className="flex flex-col gap-2 rounded-lg border border-bad/30 bg-surface p-3 text-xs sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-bad/15 px-1.5 py-0.5 text-[11px] font-semibold text-bad">
                      {c.kind.replace(/_/g, " ")}
                    </span>
                    <Link
                      to={`/evidence/${c.evidence_id}`}
                      className="font-medium text-ink hover:text-accent hover:underline"
                    >
                      {c.filename}
                    </Link>
                  </div>
                  <div className="text-muted">{c.message}</div>
                </div>

                <Link
                  to={`/evidence/${c.evidence_id}`}
                  className="inline-flex shrink-0 items-center gap-1 rounded bg-surface2 px-2.5 py-1 text-xs font-medium text-accent hover:bg-surface"
                >
                  Inspect Evidence →
                </Link>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 2. Timeline Controls & Chronological Stream */}
      <Card>
        <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-ink">Chronological Case Timeline</h3>
            <div className="text-xs text-muted">
              Unified chronology of intake, EXIF creation, modifications, and custody chain events
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap gap-1 text-xs">
            {[
              { id: "all", label: `All (${t.events.length})` },
              { id: "created", label: "Creation" },
              { id: "modified", label: "Modifications" },
              { id: "upload", label: "Intake" },
              { id: "custody", label: "Custody" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={cx(
                  "rounded-md px-2.5 py-1 font-medium transition",
                  filter === f.id
                    ? "bg-ink text-bg font-semibold"
                    : "bg-surface2 text-muted hover:text-ink"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {filteredEvents.length === 0 ? (
          <Empty title="No timeline events match the filter" />
        ) : (
          <div className="p-4 sm:p-6">
            <div className="relative border-l-2 border-line pl-6 space-y-6">
              {filteredEvents.map((e, idx) => {
                const dateObj = new Date(e.timestamp);
                const dateStr = isNaN(dateObj.getTime())
                  ? e.timestamp
                  : dateObj.toUTCString();

                return (
                  <div key={idx} className="relative group">
                    {/* Axis Bullet Icon */}
                    <div
                      className={cx(
                        "absolute -left-[35px] top-0.5 flex size-6 items-center justify-center rounded-full border shadow-xs transition group-hover:scale-110",
                        kindTone(e.kind)
                      )}
                    >
                      <EventIcon kind={e.kind} />
                    </div>

                    {/* Event Content Box */}
                    <div className="rounded-xl border border-line bg-surface p-3.5 transition group-hover:border-accent group-hover:shadow-xs">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-ink">{e.label}</span>
                            <span className="text-[11px] text-muted capitalize">· {e.source}</span>
                          </div>
                          <div className="mt-0.5 font-mono text-[11px] text-muted">
                            {dateStr} <span className="text-accent/80">({ago(e.timestamp)})</span>
                          </div>
                        </div>

                        {e.score !== null && (
                          <div className="shrink-0">
                            <ScoreChip score={e.score} />
                          </div>
                        )}
                      </div>

                      {e.detail && (
                        <div className="mt-2 text-xs text-muted border-t border-line/60 pt-1.5 font-mono">
                          {e.detail}
                        </div>
                      )}

                      <div className="mt-2.5 flex items-center justify-between border-t border-line/60 pt-2 text-xs">
                        <Link
                          to={`/evidence/${e.evidence_id}`}
                          className="flex items-center gap-2 text-accent font-medium hover:underline truncate"
                        >
                          <MediaIcon type={e.media_type} size={15} />
                          <span className="truncate">{e.filename}</span>
                        </Link>
                        <span className="text-[11px] text-muted">ID: #{e.evidence_id}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
