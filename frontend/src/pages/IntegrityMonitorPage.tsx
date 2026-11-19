import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowsClockwise,
  CheckCircle,
  Copy,
  DownloadSimple,
  FileCode,
  Fingerprint,
  ShieldCheck,
  ShieldWarning,
  WarningCircle,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { ago } from "@/lib/format";
import MerkleTreeViewer from "@/components/integrity/MerkleTreeViewer";

export default function IntegrityMonitorPage() {
  const [verifying, setVerifying] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | "broken" | "intact">("all");
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const { data: status, loading, error, reload } = useApi(() => api.custodyStatus(), []);

  const handleVerifyAll = async () => {
    if (verifying) return;
    setVerifying(true);
    try {
      await api.verifyAllCustody();
      reload();
    } catch (err: any) {
      alert(`Verification failed: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleCopy = (h: string) => {
    navigator.clipboard.writeText(h);
    setCopiedHash(h);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (loading && !status) return <Loading label="Loading Integrity Status" />;
  if (error && !status) return <ErrorBox message={error} onRetry={reload} />;

  const items = status?.items || [];
  const intactCount = status?.intact || 0;
  const brokenCount = status?.broken || 0;
  const totalCount = status?.total || 0;

  const filteredItems = items.filter((it: any) => {
    if (statusFilter === "broken") return !it.chain_intact;
    if (statusFilter === "intact") return it.chain_intact;
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            File safety checks
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100">
            File Safety
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyAll}
            disabled={verifying}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3.5 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer"
          >
            <ArrowsClockwise size={14} className={cx(verifying && "animate-spin")} />
            {verifying ? "Checking all files..." : "Check all files"}
          </button>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-accent/40">
          <div className="flex items-center justify-between text-[11px] text-muted font-bold">
            <span>File safety score</span>
            <ShieldCheck size={18} className="text-good" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink tracking-tight">
            {brokenCount === 0 ? "100% safe and untouched" : `${brokenCount} Issues Found`}
          </div>
          <div className="mt-0.5 text-xs text-muted font-medium">
            {totalCount} files tracked and protected
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-good/40">
          <div className="flex items-center justify-between text-[11px] text-muted font-bold">
            <span>Untouched files</span>
            <CheckCircle size={18} className="text-good" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-good tabular-nums tracking-tight">
            {intactCount} / {totalCount}
          </div>
          <div className="mt-0.5 text-xs text-muted font-medium">
            All file hashes match original records
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-bad/40">
          <div className="flex items-center justify-between text-[11px] text-muted font-bold">
            <span>Changed files</span>
            <ShieldWarning size={18} className={brokenCount > 0 ? "text-bad" : "text-muted"} />
          </div>
          <div className={cx("mt-2 text-2xl sm:text-3xl font-extrabold tabular-nums tracking-tight", brokenCount > 0 ? "text-bad" : "text-muted")}>
            {brokenCount} files
          </div>
          <div className="mt-0.5 text-xs text-muted font-medium">
            {brokenCount === 0 ? "Zero broken hash links detected" : "Requires immediate investigation"}
          </div>
        </div>
      </div>

      {/* Visual Cryptographic Merkle Tree Audit Ledger */}
      <MerkleTreeViewer />

      {/* Main Verification Audit Table */}
      <Card className="rounded-lg overflow-hidden shadow-[var(--shadow-bento)]">
        <CardHeader
          title={`EVIDENCE CUSTODY RECORDS (${filteredItems.length})`}
          right={
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted font-medium">View:</span>
              <div className="flex rounded-full border border-line bg-surface p-0.5 shadow-2xs">
                <button
                  onClick={() => setStatusFilter("all")}
                  className={cx(
                    "rounded-full px-3 py-1 text-xs font-bold transition-all cursor-pointer",
                    statusFilter === "all" ? "bg-[#EEF4FE] text-[#2251D1] border border-[#D2E2FD] shadow-xs dark:bg-[#1E223D] dark:text-[#8FAEFF]" : "text-muted hover:text-ink"
                  )}
                >
                  All ({items.length})
                </button>
                <button
                  onClick={() => setStatusFilter("intact")}
                  className={cx(
                    "rounded-full px-3 py-1 text-xs font-bold transition-all cursor-pointer",
                    statusFilter === "intact" ? "bg-[#E8FAF3] text-[#12B981] border border-[#12B981]/30 shadow-xs" : "text-muted hover:text-ink"
                  )}
                >
                  Intact ({intactCount})
                </button>
                <button
                  onClick={() => setStatusFilter("broken")}
                  className={cx(
                    "rounded-full px-3 py-1 text-xs font-bold transition-all cursor-pointer",
                    statusFilter === "broken" ? "bg-[#FEECEC] text-[#EF4444] border border-[#EF4444]/30 shadow-xs" : "text-muted hover:text-ink"
                  )}
                >
                  Failed ({brokenCount})
                </button>
              </div>
            </div>
          }
        />

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-line bg-surface2/60 text-muted uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="px-5 py-3">File / Case</th>
                <th className="px-5 py-3">Chain Status</th>
                <th className="px-5 py-3">Disk Hash Match</th>
                <th className="px-5 py-3">Chained Events</th>
                <th className="px-5 py-3">SHA-256 Digest</th>
                <th className="px-5 py-3">Last Verified</th>
                <th className="px-5 py-3 text-right">Certificate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted">
                    No records found for this filter
                  </td>
                </tr>
              ) : (
                filteredItems.map((it: any) => (
                  <tr key={it.id} className="transition-all hover:bg-surface2/50 group">
                    <td className="px-5 py-3.5 min-w-[200px]">
                      <Link to={`/evidence/${it.id}`} className="font-semibold text-ink group-hover:text-accent transition block">
                        {it.filename}
                      </Link>
                      <div className="text-[11px] text-muted font-mono mt-0.5">
                        {it.case_reference} · <span className="uppercase">{it.media_type}</span>
                      </div>
                    </td>

                    <td className="px-5 py-3.5 whitespace-nowrap">
                      {it.chain_intact ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#12B981]">
                          <CheckCircle size={13} weight="bold" />
                          Intact
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#EF4444]">
                          <ShieldWarning size={13} weight="bold" />
                          Failed
                        </span>
                      )}
                    </td>

                    <td className="px-5 py-3.5 whitespace-nowrap">
                      {it.hash_matches_disk ? (
                        <span className="text-good font-semibold">Verified</span>
                      ) : (
                        <span className="text-bad font-semibold">Mismatch</span>
                      )}
                    </td>

                    <td className="px-5 py-3.5 whitespace-nowrap font-medium text-ink">
                      {it.events_count} events
                    </td>

                    <td className="px-5 py-3.5 whitespace-nowrap font-mono text-[11px] text-muted">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[#2251D1] font-semibold">
                          {it.sha256 ? `${it.sha256.substring(0, 10)}...${it.sha256.substring(58)}` : "-"}
                        </span>
                        {it.sha256 && (
                          <button
                            onClick={() => handleCopy(it.sha256)}
                            className="p-1 hover:text-accent rounded transition"
                            title="Copy SHA-256"
                          >
                            <Copy size={12} />
                          </button>
                        )}
                      </div>
                    </td>

                    <td className="px-5 py-4 whitespace-nowrap text-muted text-[11px]">
                      {it.last_event_at ? ago(it.last_event_at) : "At intake"}
                    </td>

                    <td className="px-5 py-4 text-right whitespace-nowrap">
                      <a
                        href={api.url.section63Pdf(it.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-bold text-accent hover:bg-surface2 transition-all inline-flex items-center gap-1.5 shadow-2xs"
                      >
                        <DownloadSimple size={13} weight="bold" />
                        Section 63
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
