import { useState } from "react";
import type { EvidenceFull } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Card, Empty, Spinner, useToast } from "@/components/ui";
import { FilePdf, ShieldCheck, CheckCircle } from "@phosphor-icons/react";
import { Markdown } from "./util";

export default function ReportTab({ ev, reload }: { ev: EvidenceFull; reload: () => void }) {
  const { can } = useAuth();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [lang, setLang] = useState<"en" | "hi" | "mr">("en");

  const rewrite = async () => {
    setBusy(true);
    try {
      await api.rewriteReport(ev.id);
      toast("Report rewrite queued");
      reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "bad");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      {/* Legal & Export Options Banner */}
      <Card className="p-3.5 bg-surface2/50 border border-line">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted">Report Language:</span>
            <div className="inline-flex rounded-lg border border-line bg-surface p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setLang("en")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  lang === "en" ? "bg-accent text-white" : "text-muted hover:text-foreground"
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => setLang("hi")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  lang === "hi" ? "bg-accent text-white" : "text-muted hover:text-foreground"
                }`}
              >
                हिन्दी (Hindi)
              </button>
              <button
                type="button"
                onClick={() => setLang("mr")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  lang === "mr" ? "bg-accent text-white" : "text-muted hover:text-foreground"
                }`}
              >
                मराठी (Marathi)
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {ev.status === "done" && (
              <>
                <a href={api.url.reportPdf(ev.id, lang)} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="secondary">
                    <FilePdf size={14} className="text-red-500" />
                    Download Signed Report
                  </Button>
                </a>
                <a href={api.url.section63Pdf(ev.id, lang)} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="primary">
                    <ShieldCheck size={14} />
                    Section 63 Certificate (BSA 2023)
                  </Button>
                </a>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* Model & Rewrite Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted">
          {ev.report_model ? `Written by ${ev.report_model}` : "Neural Forensic Synthesis Engine"}
        </span>
        {can("investigator") && (
          <Button size="sm" onClick={() => void rewrite()} disabled={busy || ev.report_busy}>
            {(busy || ev.report_busy) && <Spinner />}Rewrite with Model
          </Button>
        )}
      </div>

      {/* Report Content */}
      {ev.report ? <Markdown text={ev.report} /> : <Empty title="No report yet" />}
    </div>
  );
}
