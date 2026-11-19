import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, FilePdf, GitDiff, Trash, ArrowsClockwise, ShieldCheck, VideoCamera, SpeakerHigh } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { bytes, dateTime, shortHash } from "@/lib/format";
import { MEDIA_LABEL } from "@/lib/format";
import Viewer from "@/viewers/Viewer";
import { Button, Card, ConfirmModal, ErrorBox, Loading, Mono, PageHeader, Progress, Tabs, useToast } from "@/components/ui";
import { CopyButton } from "@/components/evidence/util";
import Sidebar from "@/components/evidence/Sidebar";
import FindingsTab from "@/components/evidence/FindingsTab";
import ReportTab from "@/components/evidence/ReportTab";
import AskTab from "@/components/evidence/AskTab";
import NotesTab from "@/components/evidence/NotesTab";
import SimilarTab from "@/components/evidence/SimilarTab";
import MetadataTab from "@/components/evidence/MetadataTab";
import CustodyTab from "@/components/evidence/CustodyTab";
import type { EvidenceFull } from "@/lib/types";

type Tab = "findings" | "report" | "ask" | "notes" | "similar" | "metadata" | "custody";
const KEYS: Tab[] = ["findings", "report", "ask", "notes", "similar", "metadata", "custody"];

function CaseLink({ caseId }: { caseId: number }) {
  const c = useApi(() => api.case(caseId), [caseId]);
  return (
    <Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-foreground">
      <ArrowLeft size={12} />
      <span>{c.data ? `${c.data.reference} ${c.data.title}` : "Case"}</span>
    </Link>
  );
}

const busy = (e: EvidenceFull | null | undefined) => !!e && (e.status === "queued" || e.status === "analyzing" || e.report_busy);

export default function Evidence() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const q = useApi(() => api.evidence(id), [id], { shouldPoll: (d: EvidenceFull | null | undefined) => busy(d) });
  const [tab, setTab] = useState<Tab>("findings");
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const n = Number(e.key);
      if (n >= 1 && n <= 7) setTab(KEYS[n - 1]);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const ev = q.data;
  if (q.error && !ev) return <ErrorBox message={String(q.error)} onRetry={q.reload} />;
  if (!ev) return <Loading />;

  const reload = () => q.reload();
  const reanalyze = async () => {
    try { await api.reanalyze(id); toast("Re-analysis queued"); reload(); }
    catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
  };
  const del = async () => {
    try { await api.deleteEvidence(id); toast("Evidence deleted"); nav(`/cases/${ev.case_id}`); }
    catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
  };
  const running = ev.status === "queued" || ev.status === "analyzing";

  return (
    <div>
      <PageHeader
        eyebrow={<CaseLink caseId={ev.case_id} />}
        title={ev.filename}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-2">
            <span>{MEDIA_LABEL[ev.media_type]}</span><span>· {bytes(ev.size)}</span><span>· received {dateTime(ev.received_at)}</span>
            <span className="inline-flex items-center">· <Mono className="ml-1">{shortHash(ev.sha256)}</Mono><CopyButton text={ev.sha256} /></span>
          </span>
        }
        actions={<>
          {ev.media_type === "audio" && (
            <Link to={`/audio-forensics?id=${id}`}>
              <Button variant="secondary" className="border-purple-500/40 text-purple-600 hover:bg-purple-50">
                <SpeakerHigh size={15} weight="bold" />
                Voice Studio
              </Button>
            </Link>
          )}
          {can("investigator") && <Button onClick={() => void reanalyze()} disabled={running}><ArrowsClockwise size={15} />Check again</Button>}
          <Link to={`/compare?a=${id}`}><Button><GitDiff size={15} />Compare files</Button></Link>
          {can("admin") && <Button variant="danger" onClick={() => setConfirm(true)}><Trash size={15} />Delete</Button>}
          {ev.status === "done" && can("investigator") && (
            <a href={api.url.section63Pdf(id)} target="_blank" rel="noreferrer">
              <Button variant="secondary"><ShieldCheck size={15} />Section 63 (BSA)</Button>
            </a>
          )}
          {ev.status === "done"
            ? <a href={api.url.reportPdf(id)} target="_blank" rel="noreferrer"><Button variant="primary"><FilePdf size={15} />Download report PDF</Button></a>
            : <Button disabled variant="primary"><FilePdf size={15} />Download report PDF</Button>}
        </>}
      />
      {running && (
        <Card className="mb-4 p-4">
          <div className="mb-2 flex justify-between text-sm">
            <span>{ev.status === "queued" ? `Queued, ${ev.queue_position ?? 0} ahead` : ev.stage}</span>
            <span className="font-mono text-muted">{Math.round(ev.progress)}%</span>
          </div>
          <Progress value={ev.progress} />
        </Card>
      )}
      {ev.status === "failed" && (
        <div className="mb-4"><ErrorBox message={ev.error ?? "Analysis failed"} onRetry={can("investigator") ? () => void reanalyze() : undefined} /></div>
      )}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-4">
          <Card className="overflow-hidden"><Viewer ev={ev} /></Card>
          <Tabs value={tab} onChange={setTab} tabs={[
            { value: "findings", label: "1 Findings", count: ev.findings.filter((f) => f.severity !== "info").length },
            { value: "report", label: "2 Summary" },
            { value: "ask", label: "3 Ask" },
            { value: "notes", label: "4 Notes", count: ev.notes.length },
            { value: "similar", label: "5 Related files" },
            { value: "metadata", label: "6 File details" },
            { value: "custody", label: "7 File safety", count: ev.custody.length },
          ]} />
          <Card>
            {tab === "findings" && (
              <FindingsTab
                findings={ev.findings}
                evidenceId={ev.id}
                mlConfidence={ev.ml_confidence}
                onReload={reload}
              />
            )}
            {tab === "report" && <ReportTab ev={ev} reload={reload} />}
            {tab === "ask" && <AskTab id={id} />}
            {tab === "notes" && <NotesTab id={id} notes={ev.notes} reload={reload} />}
            {tab === "similar" && <SimilarTab id={id} />}
            {tab === "metadata" && <MetadataTab ev={ev} />}
            {tab === "custody" && <CustodyTab ev={ev} reload={reload} />}
          </Card>
        </div>
        <Sidebar ev={ev} reload={reload} />
      </div>
      <ConfirmModal open={confirm} title="Delete this evidence?" body="The file, its analysis and custody log will be removed." onConfirm={() => void del()} onClose={() => setConfirm(false)} />
    </div>
  );
}
