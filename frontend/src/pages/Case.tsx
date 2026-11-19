import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CaretRight, DownloadSimple, Trash, Warning, MapPin, Scales, Compass } from "@phosphor-icons/react";
import { Button, Card, ConfirmModal, Empty, ErrorBox, Loading, Progress, ScoreChip, VerdictText, cx, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { ago, bytes, MEDIA_LABEL, REVIEW_LABEL } from "@/lib/format";
import type { EvidenceSummary } from "@/lib/types";
import { MediaIcon } from "@/components/case/helpers";
import UploadZone from "@/components/case/UploadZone";
import CaseTimelineTab from "@/components/case/CaseTimelineTab";
import CaseGraphTab from "@/components/case/CaseGraphTab";
import CaseGpsTab from "@/components/case/CaseGpsTab";
import CaseSummaryTab from "@/components/case/CaseSummaryTab";
import CaseMembersTab from "@/components/case/CaseMembersTab";
import ChargeSheetModal from "@/components/legal/ChargeSheetModal";

function getFileBadge(filename: string, mediaType: string): string {
  const ext = filename.split(".").pop()?.toUpperCase() || "";
  if (["JPG", "JPEG", "PNG", "WEBP"].includes(ext)) return "JPG";
  if (["MP4", "MOV", "AVI"].includes(ext)) return "MP4";
  if (["WAV", "MP3", "M4A"].includes(ext)) return "WAV";
  if (ext === "PDF") return "PDF";
  if (["DOC", "DOCX"].includes(ext)) return "DOC";
  if (mediaType === "audio") return "WAV";
  if (mediaType === "video") return "MP4";
  if (mediaType === "document") return "DOC";
  return "FILE";
}

export default function Case() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const { data: c, error, loading, reload } = useApi(
    () => api.case(id),
    [id],
    { shouldPoll: (d) => d.evidence.some((e) => e.status !== "done" && e.status !== "failed") }
  );
  const [sel, setSel] = useState<number[]>([]);
  const [del, setDel] = useState(false);
  const [tab, setTab] = useState<"evidence" | "timeline" | "graph" | "gps" | "summary" | "members">("evidence");
  const [pdfLang, setPdfLang] = useState<"en" | "hi" | "mr">("en");
  const [chargeSheetOpen, setChargeSheetOpen] = useState(false);

  if (loading && !c) return <Loading label="Loading Case" />;
  if (error && !c) return <ErrorBox message={error} onRetry={reload} />;
  if (!c) return null;

  const toggle = (eid: number) => setSel((s) => (s.includes(eid) ? s.filter((x) => x !== eid) : [...s, eid]));
  const anyDone = c.evidence.some((e) => e.status === "done");
  const reanalyze = async (eid: number) => {
    try {
      await api.reanalyze(eid);
      reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "bad");
    }
  };
  const remove = async () => {
    try {
      await api.deleteCase(id);
      nav("/cases");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "bad");
      setDel(false);
    }
  };

  const stage = (e: EvidenceSummary) => (
    <div className="min-w-40">
      <div className="mb-1 text-xs text-muted flex items-center justify-between">
        <span>{e.status === "queued" ? `Queued, ${e.queue_position ?? 2} ahead` : e.stage || "Analyzing"}</span>
        <span className="font-mono text-[10px]">{e.progress || 0}%</span>
      </div>
      <Progress value={e.status === "queued" ? 0 : e.progress} />
    </div>
  );
  const failed = (e: EvidenceSummary) => (
    <div className="flex items-center gap-2 text-xs text-bad">
      <span className="truncate">{e.error ?? "Analysis failed"}</span>
      {can("investigator") && (
        <Button size="sm" onClick={(ev) => { ev.stopPropagation(); void reanalyze(e.id); }}>
          Re-analyze
        </Button>
      )}
    </div>
  );

  return (
    <div className="space-y-5 pb-16">
      {/* Top Breadcrumb & Lead */}
      <div className="flex items-center justify-between">
        <Link to="/cases" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent font-medium transition">
          <ArrowLeft size={14} /> Cases
        </Link>
      </div>

      {/* Case Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-muted">
            <span>{c.reference}</span>
            <span>·</span>
            <span>{c.investigator || "Lead Investigator"}</span>
            {c.incident_location && (
              <>
                <span>·</span>
                <span className="text-accent flex items-center gap-1 font-semibold normal-case text-xs">
                  <MapPin size={13} weight="fill" />
                  {c.incident_location}
                </span>
              </>
            )}
          </div>
          <h1 className="mt-0.5 text-xl sm:text-2xl font-bold text-ink">
            {c.title}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setChargeSheetOpen(true)}
            className="flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-4 py-2.5 text-xs font-bold text-amber-800 dark:text-amber-300 hover:bg-amber-500/20 transition-all shadow-xs cursor-pointer"
          >
            <Scales size={15} weight="bold" />
            <span>Draft Charge Sheet / Summary</span>
          </button>

          {can("admin") && (
            <button
              onClick={() => setDel(true)}
              className="rounded-full border border-line bg-surface px-4 py-2 text-xs font-bold text-muted hover:text-bad hover:bg-bad-soft transition-all shadow-xs"
            >
              Delete case
            </button>
          )}
          {anyDone ? (
            <div className="flex items-center gap-2">
              <select
                value={pdfLang}
                onChange={(e) => setPdfLang(e.target.value as "en" | "hi" | "mr")}
                className="h-10 rounded-full border border-line bg-surface px-3 text-xs font-bold text-ink focus:outline-none focus:border-accent shadow-xs"
                title="Select Report Language"
              >
                <option value="en">English</option>
                <option value="hi">हिन्दी (Hindi)</option>
                <option value="mr">मराठी (Marathi)</option>
              </select>
              <a href={api.url.casePdf(c.id, pdfLang)} target="_blank" rel="noreferrer">
                <button className="flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-accent-hover transition-all">
                  <DownloadSimple size={15} weight="bold" />
                  Download report PDF
                </button>
              </a>
            </div>
          ) : (
            <button disabled className="rounded-full bg-accent/50 px-5 py-2.5 text-xs font-bold text-white opacity-50 cursor-not-allowed">
              <DownloadSimple size={15} /> Download report PDF
            </button>
          )}
        </div>
      </div>

      {/* 4 Stat Tiles in Horizontal Bento Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-accent/40">
          <div className="text-[10px] font-bold text-muted">Files in case</div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink tabular-nums tracking-tight">{c.files}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">Saved & checked</div>
        </div>
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-bad/40">
          <div className="text-[10px] font-bold text-muted">Probably fake</div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-bad tabular-nums tracking-tight">{c.likely_manipulated}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">Changes found</div>
        </div>
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-warn/40">
          <div className="text-[10px] font-bold text-muted">Please check</div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-warn tabular-nums tracking-tight">{c.needs_review}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">Needs a look</div>
        </div>
        <div className="rounded-lg border border-line bg-surface p-3.5 shadow-xs card-bento transition-all hover:border-good/40">
          <div className="text-[10px] font-bold text-muted">Looks genuine</div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-good tabular-nums tracking-tight">{c.consistent}</div>
          <div className="mt-0.5 text-[11px] text-muted font-medium">All checks passed</div>
        </div>
      </div>

      {/* Case Intelligence Tabs - Faint Blue Active State */}
      <div className="flex items-center gap-1 p-0.5 rounded-full bg-surface2/70 border border-line/60 w-fit overflow-x-auto scrollbar-none shadow-2xs">
        {[
          { id: "evidence", label: `Files (${c.files})` },
          { id: "timeline", label: "Timeline" },
          { id: "graph", label: "Connected files" },
          { id: "gps", label: "Location map" },
          { id: "summary", label: "Case overview" },
          { id: "members", label: `Team (${c.members?.length ?? 0})` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as any)}
            className={cx(
              "px-3.5 py-1 font-bold transition-all rounded-full shrink-0 text-xs cursor-pointer",
              tab === t.id
                ? "bg-[#EEF4FE] text-[#2251D1] border border-[#D2E2FD] shadow-xs dark:bg-[#1E223D] dark:text-[#8FAEFF]"
                : "text-muted hover:text-ink"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "evidence" && (
        <div className="space-y-5">
          {/* Add Evidence Upload Zone */}
          {can("investigator") && (
            <div>
              <UploadZone caseId={c.id} onUploaded={reload} />
            </div>
          )}

          {/* Files list */}
          <Card className="rounded-lg overflow-hidden shadow-[var(--shadow-bento)]">
            <div className="flex items-center justify-between border-b border-line/60 px-5 py-3.5">
              <h3 className="text-xs font-bold text-muted">Files list</h3>
              <span className="text-xs text-muted font-semibold bg-surface2 px-2.5 py-0.5 rounded-full">Most suspicious first</span>
            </div>

            {c.evidence.length === 0 ? (
              <Empty title="No files uploaded yet" hint={can("investigator") ? "Drop files above to check them." : undefined} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="border-b border-line bg-surface2/60 text-muted uppercase text-[10px] tracking-wider font-semibold">
                    <tr>
                      <th className="w-10 px-4 py-3" />
                      <th className="py-3">File</th>
                      <th className="py-3">Trust score</th>
                      <th className="py-3">Result</th>
                      <th className="py-3">Review status</th>
                      <th className="py-3">Findings</th>
                      <th className="py-3">Added</th>
                      <th className="w-8 py-3 pr-4" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {c.evidence.map((e) => {
                      const badge = getFileBadge(e.filename, e.media_type);
                      const isHighRisk = e.score !== null && e.score < 50;
                      const isSelected = sel.includes(e.id);

                      return (
                        <tr
                          key={e.id}
                          onClick={() => nav(`/evidence/${e.id}`)}
                          className={cx(
                            "group cursor-pointer transition hover:bg-surface2/60",
                            isSelected && "bg-accent/5"
                          )}
                        >
                          <td className="px-4 py-3" onClick={(ev) => ev.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggle(e.id)}
                              aria-label={`Select ${e.filename}`}
                              className="size-4 rounded border-line text-accent focus:ring-accent"
                            />
                          </td>
                          <td className="py-3 pr-3">
                            <div className="flex items-center gap-3">
                              <span className="grid h-6 w-9 shrink-0 place-items-center rounded bg-surface2 text-[10px] font-bold text-muted uppercase border border-line/60">
                                {badge}
                              </span>
                              <div className="min-w-0">
                                <div className="truncate font-semibold text-ink group-hover:text-accent">
                                  {e.filename}
                                </div>
                                <div className="text-[11px] text-muted">
                                  {MEDIA_LABEL[e.media_type]} / {bytes(e.size)}
                                </div>
                              </div>
                            </div>
                          </td>
                          {e.status === "done" ? (
                            <>
                              <td className="py-3">
                                <span className={cx(
                                  "font-mono text-xs font-bold tabular-nums",
                                  isHighRisk ? "text-bad" : e.score! < 80 ? "text-warn" : "text-good"
                                )}>
                                  {e.score}
                                </span>
                              </td>
                              <td className="py-3 font-semibold">
                                <VerdictText verdict={e.verdict} />
                              </td>
                              <td className="py-3 text-muted capitalize">
                                {REVIEW_LABEL[e.review_status]}
                              </td>
                              <td className="py-3 text-muted font-medium">
                                {e.flags} flags
                              </td>
                            </>
                          ) : (
                            <td className="py-3 pr-3" colSpan={4}>
                              {e.status === "failed" ? failed(e) : stage(e)}
                            </td>
                          )}
                          <td className="py-3 text-muted text-[11px]">{ago(e.received_at)}</td>
                          <td className="py-3 pr-4 text-right text-muted group-hover:text-ink">
                            <CaretRight size={14} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab 2: Chronological Timeline */}
      {tab === "timeline" && <CaseTimelineTab caseId={c.id} />}

      {/* Tab 3: Relationship Graph */}
      {tab === "graph" && <CaseGraphTab caseId={c.id} />}

      {/* Tab 4: GPS Coordinates & Anomaly Mapping */}
      {tab === "gps" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-lg bg-gradient-to-r from-accent/10 via-surface to-surface border border-accent/30 shadow-xs">
            <div className="flex items-center gap-3">
              <span className="size-9 rounded-xl bg-accent text-white grid place-items-center shrink-0">
                <Compass size={20} weight="bold" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-ink">
                  Explore map and location
                </h4>
                <p className="text-[11px] text-muted">
                  Interactive Google map, movement paths, nearby cases, and timeline replay.
                </p>
              </div>
            </div>
            <Link
              to={`/map?caseId=${c.id}`}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent text-white text-xs font-bold hover:bg-accent-hover transition cursor-pointer shrink-0 shadow-xs"
            >
              <span>Open full map</span>
              <CaretRight size={14} weight="bold" />
            </Link>
          </div>
          <CaseGpsTab caseId={c.id} />
        </div>
      )}

      {/* Tab 5: Case Summary */}
      {tab === "summary" && <CaseSummaryTab caseId={c.id} />}

      {/* Tab 6: Case Members */}
      {tab === "members" && <CaseMembersTab caseId={c.id} members={c.members ?? []} onUpdated={reload} />}

      {/* Draft Charge Sheet / Case Summary Modal */}
      <ChargeSheetModal
        caseId={c.id}
        open={chargeSheetOpen}
        onClose={() => setChargeSheetOpen(false)}
      />

      {/* Floating Selection Bar (Matches PDF Page 3 `2 files selected Compare`) */}
      {sel.length >= 2 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 flex items-center gap-4 rounded-full bg-[#151a2d] px-5 py-2.5 text-white shadow-sm border border-line/20">
          <span className="text-xs font-semibold">{sel.length} files selected</span>
          <Link to={`/compare?a=${sel[0]}&b=${sel[1]}`}>
            <button className="rounded-full bg-accent px-4 py-1 text-xs font-bold text-white hover:bg-accent/90 transition shadow-xs">
              Compare
            </button>
          </Link>
        </div>
      )}

      <ConfirmModal
        open={del}
        title="Delete case?"
        body="This will delete this case and all of its files."
        onConfirm={remove}
        onClose={() => setDel(false)}
      />
    </div>
  );
}
