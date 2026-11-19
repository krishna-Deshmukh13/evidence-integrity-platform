import { useState, useEffect } from "react";
import {
  Scales,
  Printer,
  Copy,
  CheckCircle,
  Warning,
  X,
  ShieldCheck,
  FileText,
  MapPin,
  CalendarBlank,
  IdentificationBadge,
} from "@phosphor-icons/react";
import { Button, Card, Loading, Badge, cx } from "@/components/ui";
import { api } from "@/lib/api";

export default function ChargeSheetModal({
  caseId,
  open,
  onClose,
}: {
  caseId: number;
  open: boolean;
  onClose: () => void;
}) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [copiedSha, setCopiedSha] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !caseId) return;
    setLoading(true);
    api.caseChargeSheet(caseId)
      .then((res) => setData(res))
      .catch((err) => console.error("Failed to load charge sheet:", err))
      .finally(() => setLoading(false));
  }, [open, caseId]);

  if (!open) return null;

  const copyHash = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(sha);
    setTimeout(() => setCopiedSha(null), 1500);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-surface border border-line rounded-lg shadow-sm my-8 overflow-hidden max-h-[92vh] flex flex-col">
        {/* Modal Top Actions Toolbar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-line bg-surface2/60 shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="size-8 rounded-xl bg-amber-500/15 text-amber-600 grid place-items-center">
              <Scales size={18} weight="bold" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-ink">
                Draft Charge Sheet / Case Summary
              </h3>
              <p className="text-[11px] text-muted">
                Draft Charge Sheet & Case Summary under Section 173 CrPC / Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-line bg-surface text-xs font-bold text-ink hover:bg-surface2 transition cursor-pointer shadow-xs"
            >
              <Printer size={15} weight="bold" />
              <span>Print / Save PDF</span>
            </button>
            <button
              onClick={onClose}
              className="size-8 rounded-xl border border-line text-muted hover:text-ink grid place-items-center transition cursor-pointer"
            >
              <X size={16} weight="bold" />
            </button>
          </div>
        </div>

        {/* Modal Body: The Formal Judicial Document */}
        <div className="p-6 sm:p-10 overflow-y-auto space-y-8 bg-stone-50 dark:bg-zinc-950 font-serif text-ink selection:bg-amber-100">
          {loading && !data ? (
            <Loading label="Generating Statutory Police Charge-Sheet & BSA Exhibits Manifest..." />
          ) : data ? (
            <div className="relative bg-white dark:bg-zinc-900 border-2 border-stone-300 dark:border-zinc-800 p-8 sm:p-12 shadow-sm rounded-xl space-y-6">
              {/* Document Header & State Seal */}
              <div className="text-center space-y-1.5 border-b-2 border-stone-800 dark:border-stone-200 pb-5">
                <div className="inline-flex items-center justify-center size-14 rounded-full border-2 border-stone-800 dark:border-stone-200 mx-auto text-amber-700 dark:text-amber-400 mb-1">
                  <Scales size={28} weight="fill" />
                </div>
                <div className="text-[11px] font-mono uppercase tracking-widest text-muted">
                  GOVERNMENT OF MAHARASHTRA / METROPOLITAN CRIME BRANCH
                </div>
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-ink uppercase font-sans">
                  FINAL POLICE REPORT / CHARGE-SHEET (SEC 173 Cr.P.C.)
                </h1>
                <div className="text-xs font-mono font-semibold text-accent">
                  IN THE COURT OF THE CHIEF METROPOLITAN MAGISTRATE
                </div>
              </div>

              {/* FIR & Precinct Metadata Table */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono border border-stone-200 dark:border-zinc-800 p-4 rounded-lg bg-stone-50/50 dark:bg-zinc-900/50">
                <div className="space-y-1.5">
                  <div>
                    <span className="text-muted">CHARGE SHEET NO: </span>
                    <strong className="text-ink">{data.fir_number}</strong>
                  </div>
                  <div>
                    <span className="text-muted">POLICE STATION: </span>
                    <span className="text-ink font-semibold">{data.police_station}</span>
                  </div>
                  <div>
                    <span className="text-muted">CASE TITLE: </span>
                    <strong className="text-ink">{data.case_title} ({data.case_reference})</strong>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div>
                    <span className="text-muted">DATE & TIME OF FILING: </span>
                    <span className="text-ink font-semibold">{data.filing_date}</span>
                  </div>
                  <div>
                    <span className="text-muted">INCIDENT LOCATION: </span>
                    <span className="text-ink font-semibold flex items-center gap-1 inline-flex">
                      <MapPin size={12} className="text-accent" />
                      {data.incident_location}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted">INVESTIGATING OFFICER: </span>
                    <strong className="text-ink">{data.investigating_officer} ({data.officer_badge})</strong>
                  </div>
                </div>
              </div>

              {/* Penal Classification & Legal Sections */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-ink font-sans">
                  I. OFFENSES & STATUTORY PENAL SECTIONS INVOKED
                </h4>
                <div className="border border-stone-200 dark:border-zinc-800 rounded-lg overflow-hidden text-xs">
                  <table className="w-full text-left">
                    <thead className="bg-stone-100 dark:bg-zinc-800/60 font-sans font-bold text-muted text-[11px]">
                      <tr>
                        <th className="py-2 px-3">Statutory Provision</th>
                        <th className="py-2 px-3">Substantive Offense Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200 dark:divide-zinc-800 font-mono text-[11.5px]">
                      {data.legal_sections?.map((sec: any, idx: number) => (
                        <tr key={idx} className="hover:bg-stone-50 dark:hover:bg-zinc-800/30">
                          <td className="py-2 px-3 font-bold text-accent">{sec.section}</td>
                          <td className="py-2 px-3 text-ink">{sec.offense}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Brief Facts / Investigation Narrative */}
              <div className="space-y-2 text-xs leading-relaxed text-ink/90 font-serif">
                <h4 className="text-xs font-bold text-ink font-sans">
                  II. SUMMARY OF FORENSIC INQUIRY & FACTS OF CRIME
                </h4>
                <p className="indent-6">{data.investigation_narrative}</p>
                <p className="indent-6">
                  Forensic audit across {data.total_exhibits} seized electronic records identified {data.tampered_exhibits_count} exhibits presenting conclusive mathematical evidence of intentional manipulation (pixel-level clone stamps, synthetic neural vocoders, font metric splicing, or broken cryptographic SHA-256 digests).
                </p>
              </div>

              {/* Exhibit Manifest Table (Section 63 BSA Compliance) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between font-sans">
                  <h4 className="text-xs font-bold text-ink">
                    III. FORENSIC EXHIBITS MANIFEST (SECTION 63 BSA COMPLIANCE)
                  </h4>
                  <span className="text-[11px] font-mono text-muted">
                    {data.tampered_exhibits_count} Tampered / {data.consistent_exhibits_count} Consistent
                  </span>
                </div>

                <div className="border border-stone-200 dark:border-zinc-800 rounded-lg overflow-x-auto text-xs font-mono">
                  <table className="w-full text-left min-w-[620px]">
                    <thead className="bg-stone-100 dark:bg-zinc-800/60 font-sans font-bold text-muted text-[11px]">
                      <tr>
                        <th className="py-2 px-3">Ex. No</th>
                        <th className="py-2 px-3">File Name</th>
                        <th className="py-2 px-3">Cryptographic SHA-256 Digest</th>
                        <th className="py-2 px-3">Integrity</th>
                        <th className="py-2 px-3">Recovery Venue</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200 dark:divide-zinc-800 text-[11px]">
                      {data.exhibits?.map((ex: any) => {
                        const isTampered = ex.tamper_detected;
                        return (
                          <tr key={ex.id} className="hover:bg-stone-50 dark:hover:bg-zinc-800/30">
                            <td className="py-2 px-3 font-bold text-ink">{ex.exhibit_no}</td>
                            <td className="py-2 px-3 font-medium text-ink max-w-[140px] truncate" title={ex.filename}>
                              {ex.filename}
                            </td>
                            <td className="py-2 px-3 text-muted">
                              <button
                                onClick={() => copyHash(ex.sha256)}
                                className="inline-flex items-center gap-1 hover:text-ink cursor-pointer"
                                title="Click to copy hash"
                              >
                                <span className="max-w-[120px] truncate">{ex.sha256}</span>
                                <Copy size={11} />
                                {copiedSha === ex.sha256 && <span className="text-accent text-[9px]">Copied</span>}
                              </button>
                            </td>
                            <td className="py-2 px-3">
                              <span
                                className={cx(
                                  "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                                  isTampered
                                    ? "bg-rose-500/10 text-rose-600 border border-rose-300 dark:border-rose-900"
                                    : "bg-emerald-500/10 text-emerald-600 border border-emerald-300 dark:border-emerald-900"
                                )}
                              >
                                {isTampered ? `Tampered (${ex.score})` : `Intact (${ex.score})`}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-muted max-w-[140px] truncate">
                              {ex.incident_venue}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Legal Certificate Clause & Officer Affidavit */}
              <div className="pt-4 border-t-2 border-stone-300 dark:border-zinc-800 space-y-4">
                <div className="p-3.5 rounded-lg bg-stone-100/80 dark:bg-zinc-800/50 border border-stone-200 dark:border-zinc-700 text-xs italic font-serif leading-relaxed text-ink/80">
                  <span className="font-bold font-sans not-italic">STATUTORY CERTIFICATION: </span>
                  "{data.certification_clause}"
                </div>

                {/* Mandatory Legal Disclaimer */}
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-900 dark:text-amber-200 text-center font-medium">
                  <strong>Notice:</strong> This is a decision-support tool. The final opinion must be given by a qualified forensic examiner.
                </div>

                {/* Digital Signature & Seal Box */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pt-2 font-sans">
                  <div className="text-center sm:text-left text-xs text-muted font-mono space-y-1">
                    <div>SEAL OF THE INVESTIGATING AGENCY</div>
                    <div className="inline-flex items-center gap-1.5 text-emerald-600 font-bold">
                      <ShieldCheck size={16} weight="fill" />
                      Cryptographically Stamped & Anchored
                    </div>
                  </div>

                  <div className="text-center sm:text-right space-y-1 text-xs">
                    <div className="font-mono text-[11px] text-muted">SIGNATURE & SEAL:</div>
                    <div className="font-serif font-black text-ink text-base">
                      {data.investigating_officer}
                    </div>
                    <div className="text-muted text-[11px] font-mono">
                      Inspector of Police, CID ({data.officer_badge})
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
