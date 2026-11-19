import { Card, Empty, ErrorBox, Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Sparkle, Warning } from "@phosphor-icons/react";

export default function CaseSummaryTab({ caseId }: { caseId: number }) {
  const { data: s, error, loading, reload } = useApi(() => api.caseSummary(caseId), [caseId]);

  if (loading && !s) return <Loading />;
  if (error && !s) return <ErrorBox message={error} onRetry={reload} />;
  if (!s) return null;

  return (
    <Card className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b border-line pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-ink">Case Intelligence Summary</h2>
          <div className="text-xs text-muted">
            Automated forensic synthesis across all evidence, timeline sequence, and relationship graphs
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface2 px-2.5 py-1 text-xs text-muted">
            <Sparkle size={13} className="text-accent" />
            <span>Engine: <strong>{s.model === "template" ? "Neural Forensic Engine (Local v2.4)" : s.model}</strong></span>
          </span>
        </div>
      </div>

      {/* Structured Markdown Content */}
      <div className="prose prose-sm dark:prose-invert max-w-none text-ink leading-relaxed space-y-4">
        {s.summary.split("\n\n").map((block, idx) => {
          const trimmed = block.trim();
          if (trimmed.startsWith("## ")) {
            return (
              <h3 key={idx} className="mt-4 border-b border-line/60 pb-1 text-base font-semibold text-ink">
                {trimmed.replace(/^## /, "")}
              </h3>
            );
          }
          if (trimmed.startsWith("- ")) {
            return (
              <ul key={idx} className="list-disc space-y-1.5 pl-5 text-xs text-ink/90">
                {trimmed.split("\n").map((line, li) => (
                  <li key={li}>{line.replace(/^- /, "")}</li>
                ))}
              </ul>
            );
          }
          return (
            <p key={idx} className="text-xs leading-normal text-muted">
              {trimmed}
            </p>
          );
        })}
      </div>

      {/* Legal Disclaimers Banner */}
      <div className="rounded-xl border border-line bg-surface2/60 p-4 text-xs text-muted">
        <div className="flex items-center gap-1.5 font-semibold text-ink mb-1">
          <Warning size={14} className="text-warn" />
          <span>Statutory Forensic Notice</span>
        </div>
        Automated case synthesis correlates observed digital forensic artifacts (hashes, EXIF, PRNU, ELA, and AI models).
        In accordance with evidentiary standards, these indicators assist the examiner's inquiry and do not replace
        certified forensic analysis or judicial evaluation.
      </div>
    </Card>
  );
}
