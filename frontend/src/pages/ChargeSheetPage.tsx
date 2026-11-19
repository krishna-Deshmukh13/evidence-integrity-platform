import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Printer,
  FileText,
  DownloadSimple,
  ShieldCheck,
  Warning,
  CheckCircle,
  FolderSimple,
  ArrowLeft,
  Stamp,
  Scales,
  IdentificationCard,
  MapPin,
  Clock,
} from "@phosphor-icons/react";
import { Card, Button, Badge, Loading, ErrorBox, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function ChargeSheetPage() {
  const { id } = useParams<{ id?: string }>();
  const nav = useNavigate();

  // Load list of cases for top selector
  const { data: casesData } = useApi(() => api.cases(), []);
  const [selectedCaseId, setSelectedCaseId] = useState<number>(Number(id) || 1);

  // Load chargesheet data for selected case
  const [chargeData, setChargeData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChargeSheet = async (cId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.caseChargeSheet(cId);
      setChargeData(res);
    } catch (err: any) {
      console.error("Failed to fetch chargesheet:", err);
      setError("Unable to generate charge sheet for this case. Ensure the case exists and has evidence attached.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedCaseId) {
      fetchChargeSheet(selectedCaseId);
    }
  }, [selectedCaseId]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 pb-20 max-w-[1280px] mx-auto">
      {/* Top Controls Toolbar (Hidden during browser print) */}
      <div className="print:hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-accent mb-1">
            <Scales size={15} weight="bold" />
            <span>Statutory Legal Document</span>
          </div>
          <h1 className="text-2xl font-black text-ink">
            Draft Charge Sheet / Case Summary
          </h1>
          <p className="text-xs text-muted max-w-2xl mt-0.5">
            Automated digital evidence schedule and draft charge sheet summary compliant with Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Case Selector Dropdown */}
          <div className="flex items-center gap-2 bg-surface2 px-3 py-1.5 rounded-xl border border-line text-xs">
            <FolderSimple size={14} className="text-accent" />
            <span className="font-semibold text-muted">Case:</span>
            <select
              value={selectedCaseId}
              onChange={(e) => {
                const newId = Number(e.target.value);
                setSelectedCaseId(newId);
                nav(`/chargesheet/${newId}`, { replace: true });
              }}
              className="bg-transparent font-bold text-ink focus:outline-hidden cursor-pointer"
            >
              {casesData?.map((c: any) => (
                <option key={c.id} value={c.id} className="bg-surface text-ink">
                  #{c.id} · {c.title}
                </option>
              )) || <option value={selectedCaseId}>Case #{selectedCaseId}</option>}
            </select>
          </div>

          <Button variant="primary" size="sm" onClick={handlePrint}>
            <Printer size={15} weight="bold" />
            Print / Save as PDF
          </Button>

          <Link
            to={`/cases/${selectedCaseId}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-surface text-ink border border-line hover:bg-surface2 transition"
          >
            <ArrowLeft size={14} /> Back to Case
          </Link>
        </div>
      </div>

      {error && <ErrorBox message={error} onRetry={() => fetchChargeSheet(selectedCaseId)} />}

      {loading && !chargeData ? (
        <Loading label="Compiling Draft Charge Sheet Manifest & SHA-256 Schedules..." />
      ) : chargeData ? (
        /* Printable Document Canvas */
        <div className="bg-white dark:bg-zinc-950 rounded-lg shadow-lg border border-line p-8 sm:p-14 text-ink space-y-8 print:shadow-none print:border-none print:p-0 print:m-0">
          {/* Official Emblem & Legal Header */}
          <div className="text-center space-y-2 border-b-2 border-ink pb-6">
            <div className="inline-flex items-center justify-center size-16 rounded-full border-2 border-ink mb-1">
              <Scales size={32} weight="bold" />
            </div>
            <div className="text-[11px] font-mono uppercase font-bold text-muted">
              POLICE DEPARTMENT · CYBER & SPECIAL FINANCIAL CRIMES PRECINCT
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-ink">
              DRAFT CHARGE SHEET / CASE SUMMARY
            </h2>
            <div className="text-xs font-serif text-muted">
              [Prepared under Section 173 Cr.P.C. / Bharatiya Nagarik Suraksha Sanhita & Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act)]
            </div>
          </div>

          {/* Core Case Registry Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 p-4 rounded-xl bg-surface2/60 border border-line text-xs font-mono">
            <div>
              <span className="text-muted block text-[10px] uppercase font-bold">Charge Sheet Reference:</span>
              <strong className="text-ink text-sm">{chargeData.fir_number}</strong>
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-bold">Case Reference:</span>
              <strong className="text-ink text-sm">{chargeData.case_reference}</strong>
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-bold">Filing Timestamp:</span>
              <strong className="text-ink">{chargeData.filing_date}</strong>
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-bold">Jurisdiction / Police Station:</span>
              <span className="text-ink">{chargeData.police_station}</span>
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-bold">Investigating Officer:</span>
              <span className="text-ink font-bold">{chargeData.investigating_officer} ({chargeData.officer_badge})</span>
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-bold">Incident Venue / GPS:</span>
              <span className="text-ink">{chargeData.incident_location} ({chargeData.incident_lat?.toFixed(3)}, {chargeData.incident_lon?.toFixed(3)})</span>
            </div>
          </div>

          {/* Statutory Offense Sections */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold font-mono text-ink border-b border-line pb-1">
              I. Applicable Statutory Offenses & Penal Provisions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {chargeData.legal_sections?.map((sec: any, idx: number) => (
                <div key={idx} className="p-3 rounded-lg border border-line bg-surface2/40 text-xs space-y-1">
                  <div className="font-bold text-accent font-mono">{sec.section}</div>
                  <div className="text-ink/90 font-serif leading-relaxed">{sec.offense}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Evidence Schedule & Telemetry Manifest */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-line pb-1">
              <h3 className="text-xs font-bold font-mono text-ink">
                II. Schedule of Electronic Exhibits ({chargeData.total_exhibits})
              </h3>
              <div className="flex items-center gap-3 text-[11px] font-mono">
                <span className="text-emerald-600 font-bold">✓ {chargeData.consistent_exhibits_count} Genuine</span>
                <span className="text-rose-600 font-bold">⚠ {chargeData.tampered_exhibits_count} Altered / Fake</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-line text-[10px] font-mono uppercase text-muted">
                    <th className="py-2 px-2">Exhibit #</th>
                    <th className="py-2 px-2">Filename</th>
                    <th className="py-2 px-2">Media Type</th>
                    <th className="py-2 px-2">SHA-256 Bitstream Hash</th>
                    <th className="py-2 px-2">Verdict</th>
                    <th className="py-2 px-2 text-right">Trust</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line font-mono">
                  {chargeData.exhibits?.map((ex: any) => {
                    const isTampered = ex.tamper_detected;
                    return (
                      <tr key={ex.id} className="hover:bg-surface2/30">
                        <td className="py-2 px-2 font-bold text-accent">{ex.exhibit_no}</td>
                        <td className="py-2 px-2 font-sans font-medium text-ink max-w-[200px] truncate">{ex.filename}</td>
                        <td className="py-2 px-2 uppercase text-[10px] text-muted">{ex.media_type}</td>
                        <td className="py-2 px-2 text-[10px] text-muted max-w-[140px] truncate font-mono" title={ex.sha256}>
                          {ex.sha256}
                        </td>
                        <td className="py-2 px-2">
                          <span className={cx("font-bold text-[11px]", isTampered ? "text-rose-600" : "text-emerald-600")}>
                            {isTampered ? "Probably Fake" : "Looks Genuine"}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-right font-bold text-ink">{ex.score ?? "-"}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Investigation Narrative */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold font-mono text-ink border-b border-line pb-1">
              III. Forensic Examiner Narrative & Findings
            </h3>
            <p className="text-xs font-serif leading-relaxed text-ink/90 p-4 rounded-xl bg-surface2/40 border border-line">
              {chargeData.investigation_narrative}
            </p>
          </div>

          {/* Statutory Section 63 BSA Certification Clause */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold font-mono text-ink border-b border-line pb-1">
              IV. Statutory Digital Certification (Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (formerly Section 65B, Indian Evidence Act))
            </h3>
            <p className="text-[11px] font-mono leading-relaxed text-muted p-3 rounded-lg border border-line bg-surface2/20">
              "{chargeData.certification_clause}"
            </p>
          </div>

          {/* Legal Disclaimer */}
          <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs text-amber-900 dark:text-amber-200 font-medium text-center">
            <strong>Mandatory Legal Notice:</strong> This is a decision-support tool. The final opinion must be given by a qualified forensic examiner.
          </div>

          {/* Attestation & Signatures Section */}
          <div className="pt-8 border-t-2 border-ink grid grid-cols-1 sm:grid-cols-3 gap-8 text-center text-xs font-mono">
            {/* Investigating Officer Signature */}
            <div className="space-y-8">
              <div className="h-10 border-b border-dashed border-stone-400 flex items-end justify-center pb-1 italic font-serif text-sm">
                {chargeData.investigating_officer}
              </div>
              <div>
                <div className="font-bold text-ink">{chargeData.investigating_officer}</div>
                <div className="text-[10px] text-muted">{chargeData.officer_badge} · Investigating Officer</div>
              </div>
            </div>

            {/* Official Lab Seal */}
            <div className="flex flex-col items-center justify-center">
              <div className="size-20 rounded-full border-2 border-dashed border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400 flex flex-col items-center justify-center p-1">
                <Stamp size={24} weight="duotone" />
                <span className="text-[8px] font-bold mt-0.5">STATE CID CYBER</span>
                <span className="text-[7px]">VERIFIED SEAL</span>
              </div>
            </div>

            {/* Public Prosecutor / Magistrate Box */}
            <div className="space-y-8">
              <div className="h-10 border-b border-dashed border-stone-400 flex items-end justify-center pb-1 text-[10px] text-muted">
                (Sign & Date)
              </div>
              <div>
                <div className="font-bold text-ink">Public Prosecutor / Magistrate</div>
                <div className="text-[10px] text-muted">Metropolitan Sessions Court</div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
