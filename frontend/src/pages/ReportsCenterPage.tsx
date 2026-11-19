import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Certificate,
  Copy,
  DownloadSimple,
  Eye,
  FilePdf,
  FileText,
  FolderSimple,
  MagnifyingGlass,
  Scales,
  Table,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import ChargeSheetModal from "@/components/legal/ChargeSheetModal";

export default function ReportsCenterPage() {
  const [reportType, setReportType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [chargeSheetCaseId, setChargeSheetCaseId] = useState<number | null>(null);

  const { data: casesData, loading: cLoading } = useApi(() => api.cases(), []);
  const { data: searchResults, loading: sLoading } = useApi(() => api.search({}), []);

  const handleCopy = (h: string) => {
    navigator.clipboard.writeText(h);
    setCopiedHash(h);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if ((cLoading && !casesData) || (sLoading && !searchResults)) {
    return <Loading label="Loading Reports" />;
  }

  const cases = casesData || [];
  const evidenceList: any[] = searchResults || [];

  // Build report catalog items
  const reports: any[] = [];

  // 1. Case reports & Police Charge-Sheets
  cases.forEach((c) => {
    reports.push({
      id: `case-${c.id}`,
      type: "bundle",
      title: `${c.reference} — Full Case Report`,
      reference: c.reference,
      description: `${c.title} · ${c.files} files included`,
      date: c.created_at,
      exporter: c.investigator || "Lead Investigator",
      downloadUrl: api.url.casePdf(c.id),
      fileCount: c.files,
      caseId: c.id,
    });

    reports.push({
      id: `chargesheet-${c.id}`,
      type: "chargesheet",
      title: `${c.reference} — Draft Charge Sheet / Case Summary`,
      reference: c.reference,
      description: `Summary sheet with charges, file list, and officer sign-off`,
      date: c.created_at,
      exporter: "Metropolitan Police Crime Branch",
      caseId: c.id,
    });
  });

  // 2. File reports & Section 63 Certificates
  evidenceList.forEach((e: any) => {
    reports.push({
      id: `ev-report-${e.id}`,
      type: "report",
      title: `${e.filename} — Full Analysis Report`,
      reference: e.case_reference,
      description: `Integrity Score: ${e.score ?? "-"}/100 · Verdict: ${e.verdict}`,
      date: e.received_at,
      exporter: "Forensic Synthesis Engine",
      sha256: e.sha256,
      downloadUrl: api.url.reportPdf(e.id),
      evidenceId: e.id,
    });

    reports.push({
      id: `ev-sec63-${e.id}`,
      type: "certificate",
      title: `${e.filename} — Section 63 Certificate`,
      reference: e.case_reference,
      description: `Official certificate compliant with Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act)`,
      date: e.received_at,
      exporter: "Authorized Examiner Signer",
      sha256: e.sha256,
      downloadUrl: api.url.section63Pdf(e.id),
      evidenceId: e.id,
    });
  });

  // 3. Activity CSV
  reports.push({
    id: "activity-csv",
    type: "csv",
    title: "Activity Log Export (CSV)",
    reference: "Platform Audit",
    description: "Complete history log of all files and checks",
    date: new Date().toISOString(),
    exporter: "System Audit Subsystem",
    downloadUrl: api.url.activityCsv(),
  });

  const filteredReports = reports.filter((r) => {
    if (reportType !== "all" && r.type !== reportType) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        r.title.toLowerCase().includes(q) ||
        r.reference?.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            Download case and file reports
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Reports
          </h1>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Search box */}
          <div className="relative">
            <MagnifyingGlass size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search reports or cases..."
              className="h-9 w-44 sm:w-60 rounded-full border border-line bg-surface pl-9 pr-3 text-xs font-medium outline-none focus:border-accent focus:ring-2 focus:ring-accent/15 transition-all shadow-2xs"
            />
          </div>

          {/* Type filter */}
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="h-9 rounded-full border border-line bg-surface px-3 text-xs font-semibold text-ink outline-none focus:border-accent shadow-2xs"
          >
            <option value="all">All reports ({reports.length})</option>
            <option value="chargesheet">Draft Charge Sheets / Summaries</option>
            <option value="bundle">Case reports</option>
            <option value="report">File reports</option>
            <option value="certificate">Section 63 Certificates</option>
            <option value="csv">Audit CSV Exports</option>
          </select>
        </div>
      </div>

      {/* Summary KPI Tiles */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-accent/40">
          <span className="text-[10px] font-bold text-muted">Case reports</span>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink tabular-nums">{cases.length}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">Complete case summaries</div>
        </div>
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-accent/40">
          <span className="text-[10px] font-bold text-muted">File reports</span>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-accent tabular-nums">{evidenceList.length}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">Detailed file checks</div>
        </div>
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-accent/40">
          <span className="text-[10px] font-bold text-muted">Section 63 Certificates</span>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-good tabular-nums">{evidenceList.length}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">BSA 2023 court-admissible</div>
        </div>
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-accent/40">
          <span className="text-[10px] font-bold text-muted">Available Exports</span>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink tabular-nums">{reports.length}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">Direct downloadable artifacts</div>
        </div>
      </div>

      {/* Main Reports List */}
      <Card className="rounded-lg overflow-hidden shadow-[var(--shadow-bento)]">
        <CardHeader title={`GENERATED REPORTS & DOSSIERS (${filteredReports.length})`} />
        <div className="divide-y divide-line/60">
          {filteredReports.length === 0 ? (
            <Empty title="No reports found matching this criteria" />
          ) : (
            filteredReports.map((r) => {
              const isBundle = r.type === "bundle";
              const isCertificate = r.type === "certificate";
              const isCsv = r.type === "csv";
              const isChargeSheet = r.type === "chargesheet";

              return (
                <div
                  key={r.id}
                  className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:bg-surface2/50 group"
                >
                  <div className="flex items-start gap-4 min-w-0 flex-1">
                    <div
                      className={cx(
                        "grid size-12 place-items-center rounded-lg shrink-0 text-white shadow-xs transition-transform group-",
                        isChargeSheet
                          ? "bg-amber-600 shadow-[0_4px_12px_rgba(217,119,6,0.30)]"
                          : isBundle
                          ? "bg-accent shadow-[0_4px_12px_rgba(59,59,245,0.30)]"
                          : isCertificate
                          ? "bg-good shadow-[0_4px_12px_rgba(18,185,129,0.30)]"
                          : isCsv
                          ? "bg-[#2251D1]"
                          : "bg-accent"
                      )}
                    >
                      {isChargeSheet ? (
                        <Scales size={22} weight="bold" />
                      ) : isBundle ? (
                        <FolderSimple size={22} weight="bold" />
                      ) : isCertificate ? (
                        <Certificate size={22} weight="bold" />
                      ) : isCsv ? (
                        <Table size={22} weight="bold" />
                      ) : (
                        <FilePdf size={22} weight="bold" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-ink flex items-center gap-2 flex-wrap">
                        <span className="group-hover:text-accent transition">{r.title}</span>
                        <span
                          className={cx(
                            "rounded-full px-2.5 py-0.5 text-[10px] font-bold ",
                            isChargeSheet
                              ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800"
                              : isBundle
                              ? "bg-[#EBEBFE] text-accent"
                              : isCertificate
                              ? "bg-[#E8FAF3] text-[#12B981]"
                              : isCsv
                              ? "bg-[#0B0B12] text-white"
                              : "bg-surface2 text-muted"
                          )}
                        >
                          {isChargeSheet ? "POLICE CHARGE-SHEET" : r.type}
                        </span>
                      </div>
                      <div className="text-xs text-muted mt-1 font-medium">{r.description}</div>
                      {r.sha256 && (
                        <div className="mt-2 font-mono text-[11px] text-muted flex items-center gap-1.5">
                          <span className="bg-surface2/70 px-2 py-0.5 rounded-lg border border-line/40">
                            SHA-256: {r.sha256.substring(0, 16)}...{r.sha256.substring(56)}
                          </span>
                          <button
                            onClick={() => handleCopy(r.sha256)}
                            className="p-1 hover:text-accent rounded transition"
                            title="Copy SHA-256"
                          >
                            <Copy size={13} />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {isChargeSheet ? (
                      <button
                        onClick={() => setChargeSheetCaseId(r.caseId)}
                        className="flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs font-bold text-amber-800 dark:text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer shadow-xs"
                      >
                        <Scales size={15} weight="bold" />
                        <span>View Charge-Sheet</span>
                      </button>
                    ) : (
                      <a
                        href={r.downloadUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-xs font-bold text-ink shadow-2xs hover:border-accent hover:text-accent hover:bg-surface2 transition-all"
                      >
                        <DownloadSimple size={15} weight="bold" />
                        Download
                      </a>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>

      {/* Charge-Sheet Modal */}
      {chargeSheetCaseId !== null && (
        <ChargeSheetModal
          caseId={chargeSheetCaseId}
          open={chargeSheetCaseId !== null}
          onClose={() => setChargeSheetCaseId(null)}
        />
      )}
    </div>
  );
}
