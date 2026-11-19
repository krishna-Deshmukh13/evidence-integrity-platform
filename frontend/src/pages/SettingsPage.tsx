import { useState } from "react";
import {
  ArrowsClockwise,
  CheckCircle,
  Cpu,
  Database,
  Gear,
  HardDrives,
  Lock,
  Pulse,
  ShieldCheck,
  WarningCircle,
} from "@phosphor-icons/react";
import { Card, CardHeader, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";

export default function SettingsPage() {
  const { user } = useAuth();
  const [testing, setTesting] = useState(false);
  const [updatingLlm, setUpdatingLlm] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  const { data: sys, loading, error, reload } = useApi(() => api.systemSettings(), []);

  const isOfflineOnly = sys?.llm?.provider === "none";

  const handleToggleExternalAi = async () => {
    setUpdatingLlm(true);
    setTestResult(null);
    try {
      if (isOfflineOnly) {
        await api.updateLlmSettings({ provider: "free_online", model: "openai" });
      } else {
        await api.updateLlmSettings({ provider: "none", model: "deterministic" });
      }
      await reload();
    } catch (err: any) {
      alert("Failed to update AI settings: " + (err.message || err));
    } finally {
      setUpdatingLlm(false);
    }
  };

  const handleTestLlm = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testLlm();
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ ok: false, error: err.message || "Failed to reach model service" });
    } finally {
      setTesting(false);
    }
  };

  if (loading && !sys) return <Loading label="Loading System Configuration" />;
  if (error && !sys) return <ErrorBox message={error} onRetry={reload} />;

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            Platform Engine & Subsystem Configuration
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-ink mt-1">
            Settings & System Status
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => reload()}
            className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-xs font-bold text-ink shadow-sm hover:border-accent hover:text-accent transition-all"
          >
            <ArrowsClockwise size={14} />
            Refresh Status
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: AI Privacy Toggle & Forensic Engines (7 Columns) */}
        <div className="lg:col-span-7 space-y-6">
          {/* AI Privacy & Offline Air-Gap Mode Control */}
          <Card className="p-6 space-y-4 rounded-[28px] shadow-[var(--shadow-bento)] border border-line">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className={cx(
                  "p-2.5 rounded-lg shrink-0",
                  isOfflineOnly ? "bg-[#E8FAF3] text-[#12B981]" : "bg-blue-50 text-accent"
                )}>
                  <ShieldCheck size={24} weight="bold" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-extrabold text-ink">
                      External AI Summaries & Privacy Control
                    </h2>
                    <span className={cx(
                      "rounded-full px-2.5 py-0.5 text-[10px] font-bold  border",
                      isOfflineOnly
                        ? "bg-[#E8FAF3] text-[#12B981] border-[#12B981]/30"
                        : "bg-blue-50 text-accent border-blue-200"
                    )}>
                      {isOfflineOnly ? "Air-Gapped Offline" : "Cloud-Assisted"}
                    </span>
                  </div>
                  <p className="text-xs text-muted mt-1 leading-relaxed">
                    Turn off external AI summaries to guarantee that 100% of case and evidence data stays on this device.
                  </p>
                </div>
              </div>

              {/* Interactive Switch */}
              <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                <span className="text-xs font-bold text-ink">
                  {isOfflineOnly ? "AI Summaries OFF" : "AI Summaries ON"}
                </span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={!isOfflineOnly}
                  disabled={updatingLlm}
                  onClick={handleToggleExternalAi}
                  className={cx(
                    "relative inline-flex h-7 w-13 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden disabled:opacity-50",
                    !isOfflineOnly ? "bg-accent" : "bg-zinc-300 dark:bg-zinc-700"
                  )}
                  title="Toggle external AI summaries"
                >
                  <span
                    className={cx(
                      "pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out",
                      !isOfflineOnly ? "translate-x-6" : "translate-x-0"
                    )}
                  />
                </button>
              </div>
            </div>

            {/* Explanatory Notice */}
            <div className={cx(
              "rounded-[20px] p-4 text-xs border leading-relaxed",
              isOfflineOnly
                ? "bg-[#E8FAF3] border-[#12B981]/30 text-[#065F46]"
                : "bg-surface2 border-line/60 text-muted"
            )}>
              {isOfflineOnly ? (
                <div>
                  <strong className="text-[#047857] block mb-1">
                    Guaranteed 100% Offline Air-Gapped Mode Active
                  </strong>
                  Zero case files, metadata, cryptographic hashes, or search queries leave this system. All case insights, Section 63 BSA certificates, and charge sheet documents are synthesized exclusively using the local deterministic forensic rule engine.
                </div>
              ) : (
                <div>
                  <strong className="text-ink block mb-1">
                    Cloud-Assisted Narrative Formatting Active ({sys?.llm?.provider || "free_online"})
                  </strong>
                  Plain-language narrative summaries are assisted by an external language model. <strong>Privacy note:</strong> Evidence files (images, audio, video) are <em>never</em> uploaded or transmitted. Only structured forensic bullet points are formatted into text.
                </div>
              )}
            </div>
          </Card>

          {/* Forensic Inference Engine Configuration */}
          <Card className="p-6 space-y-5 rounded-[28px] shadow-[var(--shadow-bento)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-extrabold text-ink">
                <Cpu size={20} className="text-accent" />
                <span>Forensic Neural & LLM Engine</span>
              </div>
              <span className={cx(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold",
                isOfflineOnly
                  ? "bg-[#E8FAF3] text-[#12B981]"
                  : "bg-blue-50 text-accent"
              )}>
                <span className={cx(
                  "size-2 rounded-full",
                  isOfflineOnly ? "bg-[#12B981]" : "bg-accent "
                )} />
                {isOfflineOnly ? "Air-Gapped Offline" : "Connected"}
              </span>
            </div>

            <div className="space-y-3.5 pt-3 border-t border-line/60 text-xs">
              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Active Model Identifier:</span>
                <span className="font-mono font-bold text-ink bg-surface2 px-2.5 py-1 rounded-full border border-line/40">
                  {sys?.llm?.model || (isOfflineOnly ? "deterministic" : "openai (gpt-oss)")}
                </span>
              </div>

              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Inference Provider:</span>
                <span className="font-bold text-ink">
                  {sys?.llm?.provider === "free_online"
                    ? "Free Online AI (ChatGPT-like, Zero Key)"
                    : sys?.llm?.provider === "none"
                    ? "Local Knowledge Engine (Deterministic)"
                    : sys?.llm?.provider || "Free Online AI"}
                </span>
              </div>

              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Host Connection:</span>
                <span className="font-mono text-muted">
                  {isOfflineOnly ? "None (Offline Air-Gapped)" : (sys?.llm?.base_url || "http://localhost:11434")}
                </span>
              </div>

              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Data Privacy Protection:</span>
                <span className="font-bold text-[#12B981] flex items-center gap-1.5">
                  <Lock size={14} />
                  {isOfflineOnly ? "Zero External Transmissions (Air-Gapped)" : "Evidence Files Never Uploaded"}
                </span>
              </div>
            </div>

            {/* Test Connection Button */}
            <div className="pt-4 border-t border-line/60">
              <button
                onClick={handleTestLlm}
                disabled={testing}
                className="w-full flex items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-xs font-bold text-white shadow-xs hover:bg-accent-hover transition-all disabled:opacity-50"
              >
                <Pulse size={16} className={cx(testing && "animate-spin")} />
                {testing ? "Testing Subsystem Connectivity..." : (isOfflineOnly ? "Verify Local Engine Health" : "Test Model Connection")}
              </button>

              {testResult && (
                <div
                  className={cx(
                    "mt-3.5 rounded-[20px] p-4 text-xs  border shadow-xs",
                    testResult.ok ? "bg-[#E8FAF3] border-[#12B981]/30 text-[#12B981]" : "bg-[#FEECEC] border-[#EF4444]/30 text-[#EF4444]"
                  )}
                >
                  <div className="font-extrabold flex items-center gap-2 text-sm">
                    {testResult.ok ? <CheckCircle size={18} weight="bold" /> : <WarningCircle size={18} weight="bold" />}
                    {testResult.ok ? "System Health Verified" : "Connection Notice"}
                  </div>
                  <div className="mt-1 text-ink/90 font-medium">{testResult.message || testResult.error}</div>
                  {testResult.latency_ms > 0 && (
                    <div className="mt-1 font-mono text-[11px] text-muted">
                      Engine Latency: {testResult.latency_ms} ms
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* Core Forensic Algorithms */}
          <Card className="rounded-[28px] overflow-hidden shadow-[var(--shadow-bento)]">
            <CardHeader title="FORENSIC DETECTION SUBSYSTEMS" />
            <div className="divide-y divide-line/60 text-xs">
              {sys?.models?.map((m: any, i: number) => (
                <div key={i} className="p-4 flex items-center justify-between hover:bg-surface2/50 transition">
                  <div>
                    <div className="font-bold text-ink">{m.name}</div>
                    <div className="text-muted text-[11px] mt-0.5">{m.type}</div>
                  </div>
                  <span className="rounded-full bg-[#E8FAF3] px-2.5 py-0.5 text-[10px] font-bold text-[#12B981]">
                    {m.status}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right Column: Dependencies & Storage (5 Columns) */}
        <div className="lg:col-span-5 space-y-6">
          {/* System Storage Utilization */}
          <Card className="p-6 space-y-5 rounded-[28px] shadow-[var(--shadow-bento)]">
            <div className="flex items-center gap-2.5 text-sm font-extrabold text-ink">
              <HardDrives size={20} className="text-accent" />
              <span>Storage & Database Volumes</span>
            </div>

            <div className="space-y-3.5 pt-3 border-t border-line/60 text-xs">
              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Evidence Database:</span>
                <span className="font-bold text-ink tabular-nums">
                  {formatBytes(sys?.storage?.database_bytes || 0)}
                </span>
              </div>

              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Raw Uploads:</span>
                <span className="font-bold text-ink tabular-nums">
                  {formatBytes(sys?.storage?.uploads_bytes || 0)} ({sys?.storage?.uploads_count || 0} files)
                </span>
              </div>

              <div className="flex justify-between items-center py-1">
                <span className="text-muted font-medium">Generated Artifacts:</span>
                <span className="font-bold text-ink tabular-nums">
                  {formatBytes(sys?.storage?.artifacts_bytes || 0)} ({sys?.storage?.artifacts_count || 0} layers)
                </span>
              </div>

              <div className="pt-3 border-t border-line/60 flex justify-between items-center font-bold text-ink">
                <span className="uppercase text-[11px] tracking-wider text-muted">Total Volume:</span>
                <span className="tabular-nums text-accent font-extrabold text-sm">
                  {formatBytes(sys?.storage?.total_bytes || 0)}
                </span>
              </div>
            </div>
          </Card>

          {/* Software Environment */}
          <Card className="rounded-[28px] overflow-hidden shadow-[var(--shadow-bento)]">
            <CardHeader title="RUNTIME ENVIRONMENT" />
            <div className="divide-y divide-line/60 text-xs">
              {sys?.dependencies?.map((dep: any, i: number) => (
                <div key={i} className="p-3.5 flex items-center justify-between hover:bg-surface2/50 transition">
                  <span className="font-semibold text-ink">{dep.name}</span>
                  <span className="font-mono text-muted text-[11px] bg-surface2 px-2 py-0.5 rounded-full">{dep.version}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
