import { useState } from "react";
import type { Finding, MlConfidence, Severity } from "@/lib/types";
import { Badge, Button, Empty, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { sevTone, ago } from "@/lib/format";
import { CheckCircle, XCircle, DownloadSimple, Sparkle } from "@phosphor-icons/react";
import { whereText } from "./util";

const ORDER: Record<Severity, number> = { high: 0, medium: 1, low: 2, info: 3 };

function FindingRow({
  f,
  evidenceId,
  canEdit,
  onFeedbackChanged,
}: {
  f: Finding;
  evidenceId: number;
  canEdit: boolean;
  onFeedbackChanged?: () => void;
}) {
  const where = whereText(f.location);
  const impact = f.score_impact;
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);

  const handleFeedback = async (decision: "confirmed" | "rejected" | "cleared") => {
    setSubmitting(true);
    try {
      await api.findingFeedback(evidenceId, f.id, { decision });
      toast(decision === "cleared" ? "Feedback cleared" : `Finding marked as ${decision}`);
      onFeedbackChanged?.();
    } catch (e: any) {
      toast(e instanceof Error ? e.message : "Failed to save feedback", "bad");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="border-b border-line px-4 py-3.5 last:border-0 hover:bg-surface2/30 transition-colors">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={sevTone(f.severity)}>{f.severity === "info" ? "passed" : f.severity}</Badge>
        <span className="font-semibold text-ink text-sm">{f.title}</span>
        {f.penalty > 0 && <span className="ml-auto font-mono text-xs font-bold text-bad">-{f.penalty} pts</span>}
      </div>
      <p className="mt-1 text-sm text-muted leading-relaxed">{f.detail}</p>
      {where && <p className="mt-1 text-xs text-muted">Where: <span className="text-ink font-mono">{where}</span></p>}

      {/* What would change the score (Score sensitivity) */}
      {impact && impact.points_gained > 0 && (
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5 rounded-lg border border-accent/20 bg-accent/5 px-2.5 py-1.5 text-xs">
          <span className="font-semibold text-accent">+{impact.points_gained} pts if cleared</span>
          <span className="text-muted">
            — rises to <strong className="text-ink">{impact.new_score}/100</strong>
          </span>
          {impact.band_changed ? (
            <span className="rounded bg-good/15 px-1.5 py-0.5 font-semibold text-good">
              Band shifts to {impact.new_verdict}
            </span>
          ) : (
            <span className="text-muted text-[11px]">(verdict band remains {impact.current_verdict})</span>
          )}
        </div>
      )}

      {/* Examiner Feedback Controls */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line/40 pt-2.5 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-muted text-[11px] font-medium">Examiner Feedback:</span>
          {f.feedback === "confirmed" && (
            <span className="inline-flex items-center gap-1 rounded bg-good/15 px-2 py-0.5 font-medium text-good">
              <CheckCircle size={13} weight="fill" />
              Confirmed by {f.feedback_by || "Examiner"} {f.feedback_at ? `(${ago(f.feedback_at)})` : ""}
            </span>
          )}
          {f.feedback === "rejected" && (
            <span className="inline-flex items-center gap-1 rounded bg-bad/15 px-2 py-0.5 font-medium text-bad">
              <XCircle size={13} weight="fill" />
              Rejected by {f.feedback_by || "Examiner"} {f.feedback_at ? `(${ago(f.feedback_at)})` : ""}
            </span>
          )}
          {!f.feedback && (
            <span className="text-[11px] text-muted italic">Pending examiner confirmation</span>
          )}
        </div>

        {canEdit && (
          <div className="flex items-center gap-1.5">
            {f.feedback !== "confirmed" && (
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleFeedback("confirmed")}
                className="inline-flex items-center gap-1 rounded border border-line bg-surface px-2 py-1 text-[11px] font-medium text-good hover:bg-good/10 transition"
                title="Confirm finding as genuine forensic evidence"
              >
                <CheckCircle size={12} /> Confirm
              </button>
            )}
            {f.feedback !== "rejected" && (
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleFeedback("rejected")}
                className="inline-flex items-center gap-1 rounded border border-line bg-surface px-2 py-1 text-[11px] font-medium text-bad hover:bg-bad/10 transition"
                title="Reject finding as false positive or camera artifact"
              >
                <XCircle size={12} /> Reject
              </button>
            )}
            {f.feedback && (
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleFeedback("cleared")}
                className="text-[10px] text-muted hover:text-ink transition underline ml-1"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function FindingsTab({
  findings,
  evidenceId,
  mlConfidence,
  onReload,
}: {
  findings: Finding[];
  evidenceId?: number;
  mlConfidence?: MlConfidence | null;
  onReload?: () => void;
}) {
  const [showPassed, setShowPassed] = useState(false);
  const { can } = useAuth();
  const canEdit = can("investigator");

  const issues = findings
    .filter((f) => f.severity !== "info")
    .sort((a, b) => ORDER[a.severity] - ORDER[b.severity] || b.penalty - a.penalty);
  const passed = findings.filter((f) => f.severity === "info");
  const penalizingFindings = issues.filter((f) => f.penalty > 0);

  return (
    <div className="space-y-4">
      {/* Optional ML-Assisted Confidence Banner */}
      {mlConfidence && (
        <div className="m-3 p-3 rounded-xl border border-indigo-500/20 bg-indigo-50/50 dark:bg-indigo-950/20 text-xs">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 font-semibold text-indigo-700 dark:text-indigo-300">
              <Sparkle size={15} weight="fill" className="text-indigo-500" />
              <span>ML-Assisted Manipulation Confidence: {mlConfidence.confidence_percent}%</span>
              {mlConfidence.is_demonstration && (
                <span className="rounded bg-indigo-500/10 px-1.5 py-0.2 text-[10px] font-medium">Demonstration model</span>
              )}
            </div>
            <span className="text-[11px] text-muted font-mono">{mlConfidence.model_type}</span>
          </div>
          <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
            {mlConfidence.disclaimer}
          </p>
        </div>
      )}

      {/* Score Deduction Reasons Summary (Phase A1) */}
      <div className="mx-4 p-4 rounded-xl border border-line bg-surface shadow-2xs space-y-3">
        <div className="flex items-center justify-between border-b border-line pb-2.5">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-accent" />
            <h4 className="font-bold text-ink text-xs">
              Score Deduction Reasons
            </h4>
          </div>
          <span className="text-xs text-muted">
            Base: <strong className="text-ink">100 pts</strong>
          </span>
        </div>

        {penalizingFindings.length === 0 ? (
          <div className="py-2 text-xs text-emerald-700 dark:text-emerald-400 font-medium flex items-center gap-2">
            <CheckCircle size={16} weight="fill" className="text-[#12B981] shrink-0" />
            <span>No score deductions applied. File bitstream, metadata, and structural headers are authentic.</span>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-muted">
              The following forensic anomalies resulted in integrity score point deductions:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              {penalizingFindings.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-surface2/60 border border-line text-xs hover:border-bad/30 transition-colors"
                >
                  <div className="min-w-0 mr-2">
                    <div className="font-semibold text-ink truncate" title={f.title}>
                      {f.title}
                    </div>
                    <div className="text-[11px] text-muted truncate">{f.category} forensics</div>
                  </div>
                  <span className="font-mono font-bold text-bad shrink-0 text-sm">
                    -{f.penalty}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Retraining Export Action Bar */}
      <div className="flex items-center justify-between px-4 pt-1 text-xs">
        <span className="font-semibold text-muted text-[11px]">
          Detailed Forensic Indicators ({issues.length} detected)
        </span>
        {canEdit && (
          <a
            href={api.url.retrainingCsv()}
            download
            className="inline-flex items-center gap-1 rounded-md border border-line bg-surface2 px-2.5 py-1 text-[11px] font-medium text-muted hover:text-foreground transition"
            title="Export all confirmed and rejected findings for ML retraining"
          >
            <DownloadSimple size={12} />
            Export Retraining CSV
          </a>
        )}
      </div>

      {/* Findings List */}
      <div className="divide-y divide-line border-t border-line">
        {issues.length === 0 ? (
          <Empty title="No issues found" hint="Every check passed." />
        ) : (
          issues.map((f) => (
            <FindingRow
              key={f.id}
              f={f}
              evidenceId={evidenceId ?? 0}
              canEdit={canEdit}
              onFeedbackChanged={onReload}
            />
          ))
        )}

        {passed.length > 0 && (
          <div className="p-3 bg-surface2/20">
            <Button size="sm" variant="ghost" onClick={() => setShowPassed((v) => !v)}>
              {showPassed ? "Hide" : "Show"} {passed.length} passed checks
            </Button>
            {showPassed && (
              <div className="mt-2 divide-y divide-line">
                {passed.map((f) => (
                  <FindingRow
                    key={f.id}
                    f={f}
                    evidenceId={evidenceId ?? 0}
                    canEdit={canEdit}
                    onFeedbackChanged={onReload}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
