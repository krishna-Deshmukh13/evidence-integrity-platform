import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ReportVerification } from "@/lib/types";
import { Button } from "@/components/ui";

export default function Verify() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReportVerification | null>(null);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const h = params.get("h");
    if (h) {
      setQuery(h);
      runVerify(h);
    }
  }, []);

  const runVerify = async (val: string) => {
    const clean = val.trim();
    if (!clean) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.verifyReport(clean);
      setResult(res);
      setSearched(true);
    } catch (err: any) {
      setError(err?.message || "Verification request failed");
      setResult(null);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runVerify(query);
  };

  return (
    <div className="min-h-screen mesh-gradient-bg text-ink flex flex-col justify-between p-4 sm:p-8">
      <div className="max-w-2xl w-full mx-auto my-auto py-8">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center size-16 rounded-[22px] bg-accent text-white shadow-xs mb-4">
            <svg className="size-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div className="text-xs text-slate-500 mb-0.5">Cryptographic Proof & Attestation</div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-ink mt-1">Report Verification Portal</h1>
          <p className="text-sm text-muted mt-1.5 font-medium">
            Public cryptographic verification for Evidence Integrity Platform official exports
          </p>
        </div>

        {/* Search Card */}
        <div className="bg-surface rounded-[28px] border border-line shadow-[var(--shadow-bento)] p-6 sm:p-8 mb-6 card-bento">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="hash-input" className="block text-xs font-bold text-muted mb-2">
                Report SHA-256 Hash or Document Token
              </label>
              <input
                id="hash-input"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Paste 64-character SHA-256 hash or 32-character token..."
                className="w-full px-4 py-3 rounded-full border border-line bg-surface2/60 text-xs font-mono text-ink focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all shadow-xs"
              />
            </div>
            <div className="flex gap-3">
              <Button type="submit" disabled={loading || !query.trim()} className="w-full py-3 rounded-full font-bold">
                {loading ? "Verifying Record..." : "Verify Authenticity"}
              </Button>
              {query && (
                <Button
                  type="button"
                  variant="secondary"
                  className="rounded-full"
                  onClick={() => {
                    setQuery("");
                    setResult(null);
                    setSearched(false);
                    setError(null);
                  }}
                >
                  Clear
                </Button>
              )}
            </div>
          </form>

          {/* Results Area */}
          {error && (
            <div className="mt-6 p-4 rounded-[20px] bg-[#FEECEC] dark:bg-bad/10 border border-[#EF4444]/30 text-[#EF4444] text-xs font-medium flex items-start gap-3">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>{error}</div>
            </div>
          )}

          {searched && !loading && result && (
            <div className="mt-6 pt-6 border-t border-zinc-100 dark:border-zinc-800">
              {result.match ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex items-start gap-3.5">
                    <div className="p-2 bg-emerald-600 text-white rounded-lg flex-shrink-0">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-100">
                        Official Forensic Export Verified
                      </h3>
                      <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-0.5">
                        {result.message}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800">
                      <span className="text-zinc-500 dark:text-zinc-400 block font-medium">Case Reference</span>
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100 mt-0.5 block">
                        {result.case_reference || "N/A"}
                      </span>
                    </div>

                    <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800">
                      <span className="text-zinc-500 dark:text-zinc-400 block font-medium">Export Type</span>
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100 mt-0.5 block capitalize">
                        {result.report_type === "section63" ? "Section 63 BSA 2023 Certificate" : `${result.report_type} Report`}
                      </span>
                    </div>

                    <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 sm:col-span-2">
                      <span className="text-zinc-500 dark:text-zinc-400 block font-medium">Issued Timestamp (UTC)</span>
                      <span className="font-mono text-zinc-900 dark:text-zinc-100 mt-0.5 block">
                        {result.issued_at || "N/A"}
                      </span>
                    </div>

                    {result.signer_fingerprint && (
                      <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 sm:col-span-2">
                        <span className="text-zinc-500 dark:text-zinc-400 block font-medium">Digital Signer Fingerprint</span>
                        <span className="font-mono text-[11px] text-zinc-700 dark:text-zinc-300 break-all mt-0.5 block">
                          {result.signer_fingerprint}
                        </span>
                      </div>
                    )}
                  </div>

                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed bg-zinc-50 dark:bg-zinc-800/30 p-3 rounded-lg border border-zinc-200 dark:border-zinc-800">
                    <span className="font-semibold text-zinc-700 dark:text-zinc-300">Privacy & Legal Assurance:</span> This public verification confirms that the document was cryptographically signed and registered by the platform without disclosing case contents, filenames, individual scores, or investigative notes.
                  </p>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 flex items-start gap-3.5">
                  <div className="p-2 bg-amber-600 text-white rounded-lg flex-shrink-0">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-amber-900 dark:text-amber-100">
                      Document Hash Not Found
                    </h3>
                    <p className="text-xs text-amber-700 dark:text-amber-300 mt-1 leading-relaxed">
                      {result.message}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Back Link */}
        <div className="text-center">
          <a href="/" className="text-xs text-zinc-500 hover:text-blue-600 dark:hover:text-blue-400 transition font-medium">
            ← Return to Platform Sign-In / Dashboard
          </a>
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center text-xs text-zinc-400 dark:text-zinc-600 py-4">
        Evidence Integrity Platform &bull; Forensic Provenance Engine &bull; Section 63 BSA 2023 Compliant
      </footer>
    </div>
  );
}
