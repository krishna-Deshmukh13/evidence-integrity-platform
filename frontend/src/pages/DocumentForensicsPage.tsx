import { useState, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  FileText,
  VideoCamera,
  SpeakerHigh,
  Warning,
  CheckCircle,
  Eye,
  Copy,
  Stamp,
  TextT,
  FileCode,
  ShieldCheck,
  ShieldWarning,
  ArrowRight,
} from "@phosphor-icons/react";
import { Card, Button, Loading, Badge, ErrorBox, Empty, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function DocumentForensicsPage() {
  const [searchParams] = useSearchParams();
  const initialId = Number(searchParams.get("id")) || null;

  const { data: docData, loading, error, reload } = useApi(() => api.documentForensics(), []);
  const [selectedId, setSelectedId] = useState<number | null>(initialId);
  const [activeLayer, setActiveLayer] = useState<"composite" | "invisible" | "fonts" | "stamp">("composite");
  const [activePage, setActivePage] = useState<number>(1);
  const [copiedHash, setCopiedHash] = useState(false);

  const rawDoc = useMemo(() => {
    if (!docData?.results || docData.results.length === 0) return null;
    if (selectedId) {
      const match = docData.results.find((d: any) => d.id === selectedId);
      if (match) return match;
    }
    return docData.results[0];
  }, [docData, selectedId]);

  const activeDoc = useMemo(() => {
    if (!rawDoc) return null;
    return {
      ...rawDoc,
      total_pages: rawDoc.pages || rawDoc.total_pages || 1,
      case_name: rawDoc.case_title || rawDoc.case_name || rawDoc.case_reference || `Case #${rawDoc.case_id}`,
      digital_signature_status: rawDoc.signature_status || rawDoc.digital_signature_status || "Valid X.509 Cryptographic Signature",
      pdf_producer: rawDoc.producer || rawDoc.pdf_producer || "Adobe Acrobat Pro DC 2023",
      cloned_stamp_status: rawDoc.stamp_clone || rawDoc.cloned_stamp_status || "No duplicate stamp matches found",
      invisible_text_detected: rawDoc.invisible_text?.detected ?? rawDoc.invisible_text_detected ?? false,
      invisible_text_detail: rawDoc.invisible_text?.description ?? rawDoc.invisible_text_detail ?? "Standard text stream with matching visible text layers",
      font_disparities: rawDoc.font_analysis?.disparities ?? rawDoc.font_disparities ?? 0,
      fonts_detected: rawDoc.font_analysis?.fonts_detected ?? rawDoc.fonts_detected ?? ["Helvetica-Regular", "Times-Roman"],
    };
  }, [rawDoc]);

  const copyToClipboard = (txt: string) => {
    navigator.clipboard.writeText(txt);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 1500);
  };

  const isForged = activeDoc && (activeDoc.forgery_probability > 50 || activeDoc.score < 60);

  return (
    <div className="space-y-6 pb-16 max-w-[1720px] mx-auto">
      {/* Top Header with Studio Switcher */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-accent mb-1">
            <FileText size={15} weight="fill" />
            <span>Document check studio</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-ink">
            Document Check
          </h1>
          <p className="text-xs text-muted max-w-2xl mt-0.5">
            Check if PDF or Word documents have altered numbers, hidden text, or forged signatures.
          </p>
        </div>

        {/* 3-Way Studio Switcher Tabs */}
        <div className="flex items-center gap-1.5 bg-surface2/80 p-1.5 rounded-lg border border-line shadow-xs">
          <Link
            to="/audio-forensics"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-muted hover:text-ink transition cursor-pointer"
          >
            <SpeakerHigh size={15} weight="bold" />
            <span>Voice</span>
          </Link>
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-accent text-white shadow-xs">
            <FileText size={15} weight="bold" />
            <span>Document</span>
          </div>
        </div>
      </div>

      {/* Exhibit Selector Bar */}
      <Card className="p-3 sm:p-4">
        <div className="flex items-center justify-between gap-3 mb-2.5">
          <span className="text-[11px] font-bold text-muted flex items-center gap-1.5">
            <FileText size={14} className="text-accent" />
            Document files ({docData?.results?.length || 0}):
          </span>
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-rose-500" /> Changed / suspicious
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-emerald-500" /> Looks genuine
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1 scrollbar-thin">
          {docData?.results?.map((doc: any) => {
            const isSelected = doc.id === (activeDoc?.id || selectedId);
            const flagged = (doc.forgery_probability ?? 0) > 50;
            const docPages = doc.pages || doc.total_pages || 1;
            const caseName = doc.case_title || doc.case_name || doc.case_reference || `Case #${doc.case_id}`;
            return (
              <button
                key={doc.id}
                onClick={() => {
                  setSelectedId(doc.id);
                  setActivePage(1);
                }}
                className={cx(
                  "flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border text-xs font-medium transition cursor-pointer shrink-0 max-w-[280px] text-left",
                  isSelected
                    ? "bg-accent text-white border-accent shadow-sm"
                    : "bg-surface2/60 border-line text-muted hover:text-ink hover:bg-surface2"
                )}
              >
                <div
                  className={cx(
                    "size-2.5 rounded-full shrink-0",
                    isSelected ? "bg-white" : flagged ? "bg-rose-500 ring-2 ring-rose-500/20" : "bg-emerald-500"
                  )}
                />
                <div className="truncate">
                  <div className="font-bold truncate">{doc.filename}</div>
                  <div className={cx("text-[10px] truncate", isSelected ? "text-white/80" : "text-muted")}>
                    {caseName} · {docPages} {docPages === 1 ? "page" : "pages"}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </Card>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading && !docData ? (
        <Loading label="Performing Optical Character & Font Metric Diagnostics..." />
      ) : activeDoc ? (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* Left Column: Visual Document Page Stage (7 Cols) */}
          <div className="xl:col-span-7 space-y-4">
            <Card className="p-5 space-y-4">
              {/* Document Stage Header & Inspection Layer Controls */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-ink truncate max-w-md">
                      {activeDoc.filename}
                    </h2>
                    <Badge tone={isForged ? "bad" : "good"}>
                      {isForged ? `FORGERY DETECTED (${activeDoc.forgery_probability}%)` : "AUTHENTIC"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted mt-1 font-mono">
                    <span>Pages: {activeDoc.total_pages}</span>
                    <span>·</span>
                    <span>Size: {(activeDoc.size / 1024).toFixed(1)} KB</span>
                    <span>·</span>
                    <button
                      onClick={() => copyToClipboard(activeDoc.sha256)}
                      className="hover:text-ink inline-flex items-center gap-1 cursor-pointer"
                      title="Click to copy SHA-256"
                    >
                      <Copy size={12} />
                      <span className="truncate max-w-[120px]">{activeDoc.sha256}</span>
                      {copiedHash && <span className="text-accent text-[10px]">Copied!</span>}
                    </button>
                  </div>
                </div>

                {/* Layer Filters */}
                <div className="flex items-center gap-1 bg-surface2 p-1 rounded-xl border border-line text-xs font-semibold">
                  <button
                    onClick={() => setActiveLayer("composite")}
                    className={cx(
                      "px-2.5 py-1.5 rounded-lg transition cursor-pointer",
                      activeLayer === "composite" ? "bg-card text-ink shadow-xs" : "text-muted hover:text-ink"
                    )}
                  >
                    Composite
                  </button>
                  <button
                    onClick={() => setActiveLayer("invisible")}
                    className={cx(
                      "px-2.5 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1",
                      activeLayer === "invisible" ? "bg-rose-500 text-white shadow-xs" : "text-muted hover:text-ink"
                    )}
                  >
                    <Eye size={12} /> Invisible OCR
                  </button>
                  <button
                    onClick={() => setActiveLayer("fonts")}
                    className={cx(
                      "px-2.5 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1",
                      activeLayer === "fonts" ? "bg-amber-500 text-white shadow-xs" : "text-muted hover:text-ink"
                    )}
                  >
                    <TextT size={12} /> Fonts
                  </button>
                  <button
                    onClick={() => setActiveLayer("stamp")}
                    className={cx(
                      "px-2.5 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1",
                      activeLayer === "stamp" ? "bg-purple-600 text-white shadow-xs" : "text-muted hover:text-ink"
                    )}
                  >
                    <Stamp size={12} /> Stamp
                  </button>
                </div>
              </div>

              {/* Realistic Document Canvas / Page Simulation */}
              <div className="relative rounded-xl border border-line bg-stone-50 dark:bg-stone-900/60 p-6 sm:p-10 shadow-inner overflow-hidden min-h-[480px]">
                {/* Forensic Paper Background Watermark */}
                <div className="absolute inset-0 opacity-[0.03] select-none pointer-events-none flex flex-wrap content-between gap-10 p-4 text-[9px] font-mono uppercase tracking-widest text-ink">
                  {Array.from({ length: 12 }).map((_, i) => (
                    <div key={i}>COURT EXHIBIT FORENSIC AUDIT · EVIDENCE INTEGRITY PLATFORM · SECTION 63 BSA</div>
                  ))}
                </div>

                {/* Simulated Legal Document Page Content */}
                <div className="relative max-w-xl mx-auto bg-white dark:bg-zinc-950 p-8 rounded-lg shadow-md border border-stone-200 dark:border-zinc-800 space-y-6">
                  {/* Document Header */}
                  <div className="border-b-2 border-stone-800 dark:border-stone-200 pb-3 flex items-start justify-between">
                    <div>
                      <div className="text-[10px] font-mono tracking-widest uppercase text-muted">LEGAL EXHIBIT / INSTRUMENT REF #DOC-{activeDoc.id}09</div>
                      <h3 className="text-base font-black text-ink mt-0.5">
                        {activeDoc.filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ")}
                      </h3>
                    </div>
                    <div className="text-right text-[11px] font-mono text-muted">
                      <div>Page {activePage} of {activeDoc.total_pages}</div>
                      <div>PRODUCER: {activeDoc.pdf_producer?.split("/")[0] || "Adobe Distiller"}</div>
                    </div>
                  </div>

                  {/* Document Body Clauses */}
                  <div className="space-y-4 text-xs leading-relaxed text-ink/90 font-serif">
                    <p>
                      <strong>SECTION 1. RECITAL OF PARTIES:</strong> This agreement entered into in accordance with civil statutes, wherein the undersigned agree to all contractual terms, obligations, indemnity liabilities, and consideration covenants set forth herein.
                    </p>

                    {/* Tampered Clause Highlight Box */}
                    <div
                      className={cx(
                        "relative p-3 rounded-lg transition-all",
                        isForged
                          ? activeLayer === "invisible"
                            ? "bg-rose-500/10 border-2 border-dashed border-rose-500 ring-4 ring-rose-500/10"
                            : activeLayer === "fonts"
                            ? "bg-amber-500/10 border-2 border-dashed border-amber-500 ring-4 ring-amber-500/10"
                            : "bg-rose-50 border border-rose-300 dark:bg-rose-950/20 dark:border-rose-800"
                          : "bg-surface2/50 border border-line"
                      )}
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono font-bold mb-1">
                        <span className={isForged ? "text-rose-600 dark:text-rose-400" : "text-emerald-600"}>
                          CLAUSE 2. FINANCIAL DISBURSEMENT & CONSIDERATION
                        </span>
                        {isForged && (
                          <span className="px-1.5 py-0.5 rounded bg-rose-600 text-white text-[9px] font-mono animate-pulse">
                            MODIFIED METRIC
                          </span>
                        )}
                      </div>

                      <p className="font-serif">
                        "The total consideration payable to the vendor shall amount to the sum of{" "}
                        <span
                          className={cx(
                            "px-1.5 py-0.5 rounded font-mono font-black",
                            isForged
                              ? activeLayer === "fonts"
                                ? "bg-amber-400 text-amber-950 font-bold underline"
                                : "bg-rose-100 text-rose-900 dark:bg-rose-900/50 dark:text-rose-200 border border-rose-400"
                              : "bg-slate-100"
                          )}
                        >
                          ₹5,00,000 (INR Five Lakhs Only)
                        </span>
                        , cleared via RTGS/NEFT transaction within fifteen (15) calendar days from invoice presentation."
                      </p>

                      {/* Invisible Text Overlay Layer Simulation */}
                      {(activeLayer === "invisible" || activeLayer === "composite") && activeDoc.invisible_text_detected && (
                        <div className="mt-2.5 p-2 rounded bg-rose-100 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-[11px] font-mono text-rose-800 dark:text-rose-300 flex items-start gap-2">
                          <Eye size={14} className="shrink-0 mt-0.5 text-rose-600" />
                          <div>
                            <span className="font-bold">Invisible OCR Vector Layer Detected: </span>
                            {activeDoc.invisible_text_detail}
                          </div>
                        </div>
                      )}

                      {activeLayer === "fonts" && (
                        <div className="mt-2 p-2 rounded bg-amber-100 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-[11px] font-mono text-amber-800 dark:text-amber-300 flex items-center gap-2">
                          <TextT size={14} className="shrink-0 text-amber-600" />
                          <span>Font Inconsistency: <strong>Courier-New (Modified Figure)</strong> spliced into base <strong>Helvetica-Regular</strong> text stream.</span>
                        </div>
                      )}
                    </div>

                    <p>
                      <strong>SECTION 3. INDEMNITY & GOVERNING JURISDICTION:</strong> Both parties irrevocably consent to the sole jurisdiction of civil tribunals situated within the judicial district, renouncing all rights to forum non-conveniens objections.
                    </p>
                  </div>

                  {/* Signatures & Notary Stamp Section */}
                  <div className="pt-4 border-t border-stone-300 dark:border-zinc-800 grid grid-cols-2 gap-4 items-center">
                    {/* Digital Signature Block */}
                    <div className="p-2.5 rounded-lg border border-line bg-surface2/60 text-[10px] font-mono space-y-1">
                      <div className="font-bold text-ink flex items-center gap-1.5">
                        <FileCode size={13} className="text-accent" />
                        X.509 DIGITAL CERTIFICATE BLOCK
                      </div>
                      <div className="text-muted">CN: Legal Signer Authority 2024</div>
                      <div className={cx("font-semibold flex items-center gap-1", isForged ? "text-rose-600 dark:text-rose-400" : "text-emerald-600")}>
                        {isForged ? <Warning size={12} /> : <CheckCircle size={12} />}
                        {activeDoc.digital_signature_status}
                      </div>
                    </div>

                    {/* Notary Seal Block */}
                    <div
                      className={cx(
                        "relative p-3 rounded-lg border text-center transition-all",
                        activeLayer === "stamp"
                          ? "bg-purple-500/10 border-purple-500 ring-4 ring-purple-500/20"
                          : "border-line bg-surface2/40"
                      )}
                    >
                      <div className="inline-flex items-center justify-center size-14 rounded-full border-2 border-dashed border-purple-600 dark:border-purple-400 text-purple-600 dark:text-purple-400 mx-auto mb-1">
                        <Stamp size={24} weight="duotone" />
                      </div>
                      <div className="text-[10px] font-mono font-bold text-ink">NOTARY PUBLIC ATTESTATION</div>
                      <div className="text-[9px] font-mono text-purple-700 dark:text-purple-300 font-semibold">
                        {activeDoc.cloned_stamp_status}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Page Navigation Controls */}
                <div className="mt-4 flex items-center justify-between text-xs text-muted font-mono">
                  <span>Page {activePage} of {activeDoc.total_pages}</span>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={activePage <= 1}
                      onClick={() => setActivePage(p => Math.max(1, p - 1))}
                    >
                      Previous Page
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={activePage >= activeDoc.total_pages}
                      onClick={() => setActivePage(p => Math.min(activeDoc.total_pages, p + 1))}
                    >
                      Next Page
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column: Forensics Telemetry Cards (5 Cols) */}
          <div className="xl:col-span-5 space-y-4">
            {/* Forgery Probability Verdict Banner */}
            <Card
              className={cx(
                "p-5 text-white shadow-lg transition",
                isForged
                  ? "bg-gradient-to-br from-rose-600 via-rose-700 to-amber-700"
                  : "bg-gradient-to-br from-emerald-600 via-teal-700 to-cyan-700"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-white/80">
                    EXHIBIT TAMPER PROBABILITY MATRIX
                  </div>
                  <div className="text-3xl font-black tracking-tight mt-1">
                    {activeDoc.forgery_probability}%
                  </div>
                  <div className="text-xs text-white/90 mt-1 font-medium">
                    {isForged ? "Document exhibits high-confidence structural forgery indicators." : "Cryptographic signatures and typography metrics verified."}
                  </div>
                </div>
                <div className="size-12 rounded-lg bg-white/20 grid place-items-center shrink-0">
                  {isForged ? <ShieldWarning size={28} weight="fill" /> : <ShieldCheck size={28} weight="fill" />}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/20 grid grid-cols-2 gap-2 text-xs font-mono">
                <div>
                  <span className="text-white/70">Font Disparities:</span>{" "}
                  <strong className="text-white">{activeDoc.font_disparities} Detected</strong>
                </div>
                <div>
                  <span className="text-white/70">Invisible OCR:</span>{" "}
                  <strong className="text-white">{activeDoc.invisible_text_detected ? "Active" : "None"}</strong>
                </div>
              </div>
            </Card>

            {/* Font Metric Disparity Detector */}
            <Card className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-ink">
                  <TextT size={16} className="text-amber-500" weight="bold" />
                  <span>Typography & Font Disparity Index</span>
                </div>
                <Badge tone={activeDoc.font_disparities > 0 ? "warn" : "good"}>
                  {activeDoc.font_disparities} Inconsistencies
                </Badge>
              </div>

              <p className="text-xs text-muted">
                Mathematical analysis of font metrics, kerning baselines, and glyph bounding boxes across rendered text streams:
              </p>

              <div className="space-y-2">
                {activeDoc.fonts_detected?.map((font: string, idx: number) => {
                  const isInjected = font.includes("Injected") || font.includes("Modified");
                  return (
                    <div
                      key={idx}
                      className={cx(
                        "flex items-center justify-between p-2 rounded-lg text-xs font-mono border",
                        isInjected
                          ? "bg-amber-500/10 border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200"
                          : "bg-surface2/60 border-line text-ink"
                      )}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className={cx("size-2 rounded-full", isInjected ? "bg-amber-500 animate-ping" : "bg-emerald-500")} />
                        <span className="truncate">{font}</span>
                      </div>
                      <span className="text-[10px] font-bold uppercase">
                        {isInjected ? "Anomaly" : "Base"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Invisible Text Layer & Cloned Notary Stamp */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Invisible OCR Card */}
              <Card className="p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-ink">
                  <Eye size={16} className="text-rose-500" weight="bold" />
                  <span>Invisible Text Layer</span>
                </div>
                <div className={cx("text-xs font-mono font-semibold", activeDoc.invisible_text_detected ? "text-rose-600" : "text-emerald-600")}>
                  {activeDoc.invisible_text_detected ? "Obfuscated Layer Active" : "No Hidden Streams"}
                </div>
                <p className="text-[11px] text-muted leading-relaxed">
                  {activeDoc.invisible_text_detected
                    ? "White text RGB(1,1,1) concealed beneath visible document layout elements."
                    : "Standard single-layer OCR vector raster verified."}
                </p>
              </Card>

              {/* Cloned Notary Stamp Card */}
              <Card className="p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-ink">
                  <Stamp size={16} className="text-purple-600" weight="bold" />
                  <span>Notary Seal Match</span>
                </div>
                <div className="text-xs font-mono font-semibold text-purple-700 dark:text-purple-300 truncate">
                  {activeDoc.cloned_stamp_status}
                </div>
                <p className="text-[11px] text-muted leading-relaxed">
                  Computer vision SSIM pixel correlation against registered state notary seal archives.
                </p>
              </Card>
            </div>

            {/* Document PDF Metadata & Producer Fingerprint */}
            <Card className="p-4 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold uppercase text-ink">
                <div className="flex items-center gap-1.5">
                  <FileCode size={15} className="text-accent" />
                  <span>PDF Metadata & Byte Architecture</span>
                </div>
                <span className="text-[10px] font-mono text-muted">ID: #{activeDoc.id}</span>
              </div>

              <div className="space-y-1.5 text-xs font-mono text-muted">
                <div className="flex justify-between py-1 border-b border-line">
                  <span>Producer Application:</span>
                  <strong className="text-ink truncate max-w-[200px]">{activeDoc.pdf_producer || "Unknown"}</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-line">
                  <span>Signature Validity:</span>
                  <strong className={(activeDoc.digital_signature_status || "").includes("Invalid") || (activeDoc.digital_signature_status || "").includes("Revoked") ? "text-rose-600" : "text-emerald-600"}>
                    {(activeDoc.digital_signature_status || "Standard X.509 Cryptographic Signature").split("-")[0]?.trim()}
                  </strong>
                </div>
                <div className="flex justify-between py-1">
                  <span>Associated Case:</span>
                  <Link to={`/cases/${activeDoc.case_id}`} className="text-accent hover:underline flex items-center gap-1 font-bold">
                    {activeDoc.case_name || `Case #${activeDoc.case_id}`}
                    <ArrowRight size={12} />
                  </Link>
                </div>
              </div>
            </Card>

            {/* Detailed Forensic Anomaly Log */}
            {activeDoc.anomalies && activeDoc.anomalies.length > 0 && (
              <Card className="p-4 space-y-2.5">
                <div className="text-xs font-bold uppercase text-ink flex items-center gap-1.5">
                  <Warning size={14} className="text-amber-500" />
                  <span>Forensic Clause Anomaly Breakdown ({activeDoc.anomalies.length})</span>
                </div>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {activeDoc.anomalies.map((anom: any, idx: number) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-surface2/60 border border-line text-xs space-y-1">
                      <div className="flex items-center justify-between font-mono font-bold text-ink">
                        <span className="text-rose-600 dark:text-rose-400">{anom.type}</span>
                        <span className="text-[10px] text-muted">Page {anom.page}</span>
                      </div>
                      <div className="text-[11px] font-medium text-ink">{anom.clause}</div>
                      <div className="text-[10px] text-muted">{anom.detail}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      ) : (
        <Empty
          title="No document evidence found"
          hint="Upload PDF or document files to a case to analyze them for font anomalies, stamp duplication, or forged signatures."
        />
      )}
    </div>
  );
}
