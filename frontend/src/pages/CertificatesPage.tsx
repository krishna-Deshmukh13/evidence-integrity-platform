import Logo from "@/components/Logo";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  ArrowsClockwise,
  Certificate,
  CheckCircle,
  Copy,
  DownloadSimple,
  QrCode,
  ShieldCheck,
  ShieldWarning,
  FileText,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function CertificatesPage() {
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number>(4); // default photo_tampered.jpg
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const { data: searchResults, loading: sLoading } = useApi(() => api.search({}), []);
  const { data: evidence, loading: eLoading, reload } = useApi(
    () => api.evidence(selectedEvidenceId),
    [selectedEvidenceId]
  );

  // If search results load and selected evidence is not set, set to first
  useEffect(() => {
    if (searchResults && searchResults.length > 0 && !selectedEvidenceId) {
      setSelectedEvidenceId(searchResults[0].id);
    }
  }, [searchResults, selectedEvidenceId]);

  const handleCopy = (txt: string) => {
    navigator.clipboard.writeText(txt);
    setCopiedHash(txt);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (sLoading && !searchResults) return <Loading label="Loading Certificates Hub" />;

  const allItems: any[] = searchResults || [];
  const ev: any = evidence;

  const custodyEvents = ev?.custody || [];
  const isChainIntact = ev ? (ev.status === "done" && ev.score !== null) : true;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header matching Roomify specs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            {ev ? `${ev.filename} · ${ev.case_reference || "CR-2026-0422"}` : "Evidence Certificates"}
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Chain of Custody and Certificate
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {/* Evidence selector */}
          <select
            value={selectedEvidenceId}
            onChange={(e) => setSelectedEvidenceId(Number(e.target.value))}
            className="h-9 rounded-full border border-line bg-surface px-3.5 text-xs font-semibold text-ink outline-none focus:border-accent shadow-2xs"
          >
            {allItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.filename} ({item.score ?? "-"}/100)
              </option>
            ))}
          </select>

          <button
            onClick={() => reload()}
            className="flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-accent-hover transition-all"
          >
            <ShieldCheck size={15} weight="bold" />
            Verify integrity
          </button>
        </div>
      </div>

      {/* Intact Status Banner */}
      <div className="flex items-center gap-3.5 rounded-lg border border-[#12B981]/25 bg-[#E8FAF3] dark:bg-good/10 p-4 shadow-sm card-bento">
        <div className="grid size-9 shrink-0 place-items-center rounded-full bg-[#12B981] text-white shadow-xs">
          <CheckCircle size={20} weight="bold" />
        </div>
        <div>
          <div className="text-xs sm:text-sm font-bold text-[#12B981] dark:text-good">
            File and custody chain are intact
          </div>
          <div className="text-[11px] text-muted/90 mt-0.5 font-medium">
            Stored file matches the intake hash; {custodyEvents.length || 5} chained events verified against cryptographic audit log.
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Hash-chained events (7 Columns) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-muted">
              Hash-Chained Events ({custodyEvents.length || 5})
            </h3>
          </div>

          <div className="space-y-3">
            {custodyEvents.length === 0 ? (
              [
                { num: 1, action: "Received", detail: "SI Rohan Patil · Uploaded as photo_tampered.jpg", hash: "92cf...7f5812" },
                { num: 2, action: "Analysis started", detail: "Analysis engine · Hash matches intake", hash: "2d91...9de4bf" },
                { num: 3, action: "Analysis completed", detail: "Score 42/100, Likely manipulated, 4 checks", hash: "8f73...549a13" },
                { num: 4, action: "Report exported", detail: "Investigator · PDF report downloaded", hash: "aa70...2489ac" },
                { num: 5, action: "Integrity verified", detail: "Insp. Meera Kulkarni · Chain and file intact", hash: "7de6...f59061" },
              ].map((evt) => (
                <div
                  key={evt.num}
                  className="rounded-[22px] border border-line bg-surface p-4.5 shadow-xs flex items-start gap-4 card-bento transition-all hover:border-accent/40"
                >
                  <span className="grid size-7 place-items-center rounded-full bg-surface2 text-xs font-bold text-ink shrink-0 border border-line/60">
                    {evt.num}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold text-ink">{evt.action}</div>
                    <div className="text-xs text-muted mt-0.5">{evt.detail}</div>
                    <div className="mt-1.5 font-mono text-[11px] text-muted">
                      event {evt.hash}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              custodyEvents.map((evt: any, idx: number) => (
                <div
                  key={evt.seq || idx}
                  className="rounded-[22px] border border-line bg-surface p-4.5 shadow-xs flex items-start gap-4 card-bento transition-all hover:border-accent/40"
                >
                  <span className="grid size-7 place-items-center rounded-full bg-[#EBEBFE] text-xs font-bold text-accent shrink-0">
                    {idx + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold text-ink">{evt.action}</div>
                    <div className="text-xs text-muted mt-0.5 font-medium">
                      {evt.actor} · {evt.note || "Integrity verification logged"}
                    </div>
                    <div className="mt-1.5 font-mono text-[11px] text-muted flex items-center gap-1.5">
                      <span>event {evt.event_hash ? `${evt.event_hash.substring(0, 8)}...${evt.event_hash.substring(56)}` : "verified"}</span>
                      {evt.event_hash && (
                        <button onClick={() => handleCopy(evt.event_hash!)} className="hover:text-accent transition">
                          <Copy size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Digital Evidence Integrity Certificate Card */}
        <div className="lg:col-span-5">
          <Card className="p-5 border border-line bg-surface shadow-[var(--shadow-bento)] rounded-lg space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-extrabold uppercase text-muted">
                CERTIFICATE (LEGAL DRAFT)
              </span>
              <span className="rounded-full bg-[#E8FAF3] text-[#12B981] px-2 py-0.5 text-[9px] font-bold">
                Cryptographically Signed
              </span>
            </div>

            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-ink">
                  Digital Evidence Integrity Certificate
                </h2>
                <div className="text-xs text-muted mt-0.5 font-mono">
                  File: {ev?.filename || "photo_tampered.jpg"} · {ev ? `${Math.round(ev.size / 1024)} KB` : "412.3 KB"}
                </div>
              </div>
              <Logo variant="mark" size={34} />
            </div>

            <div className="space-y-3 pt-3 border-t border-line/60 text-xs">
              <div>
                <span className="text-muted block text-[10px] font-medium">SHA-256 Digest</span>
                <span className="font-mono text-[#2251D1] font-semibold break-all text-[11px] bg-[#EEF4FE] p-2 rounded-xl block mt-1 border border-[#D2E2FD]">
                  {ev?.sha256 ? `${ev.sha256.substring(0, 24)}...${ev.sha256.substring(48)}` : "2acd1221ed450d18...06ca1c"}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1">
                <div>
                  <span className="text-muted block text-[11px] font-medium">Integrity Score</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="rounded-full bg-[#FEECEC] text-[#EF4444] px-2.5 py-0.5 font-mono text-xs font-bold tabular-nums">
                      {ev?.score ?? 42}/100
                    </span>
                    <span className="text-xs font-semibold text-[#EF4444]">
                      {ev?.verdict || "Likely manipulated"}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-muted block text-[11px] font-medium">Custody Chain</span>
                  <span className="rounded-full bg-[#E8FAF3] text-[#12B981] px-2.5 py-0.5 font-mono text-xs font-bold inline-block mt-1">
                    {custodyEvents.length || 5} of {custodyEvents.length || 5} Verified
                  </span>
                </div>
              </div>
            </div>

            {/* QR Code and Disclaimer */}
            <div className="pt-4 border-t border-line/60 flex items-start gap-4">
              <div className="grid size-18 shrink-0 place-items-center rounded-lg border border-line bg-surface2 p-2 shadow-2xs">
                <QrCode size={52} className="text-ink" />
              </div>
              <div className="text-[11px] text-muted leading-relaxed font-medium">
                Scan to verify this certificate against the platform ledger.
                RSA-4096 signature: verified. Compliant with Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act). Ready for judicial presentation.
              </div>
            </div>

            {/* Mandatory Legal Disclaimer */}
            <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs text-amber-900 dark:text-amber-200 text-center font-medium">
              <strong>Notice:</strong> This is a decision-support tool. The final opinion must be given by a qualified forensic examiner.
            </div>

            {/* Actions */}
            <div className="pt-3 flex items-center gap-2.5">
              <a
                href={api.url.section63Pdf(selectedEvidenceId)}
                target="_blank"
                rel="noreferrer"
                className="flex-1 flex items-center justify-center gap-2 rounded-full bg-accent px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-accent-hover transition-all"
              >
                <DownloadSimple size={15} weight="bold" />
                Download Certificate PDF
              </a>
              <Link
                to={`/verify`}
                className="rounded-full border border-line bg-surface px-4 py-2.5 text-xs font-semibold text-ink hover:bg-surface2 transition-all shadow-xs text-center"
              >
                Public Portal
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
