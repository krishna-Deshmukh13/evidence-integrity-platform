import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { SimilarRow } from "@/lib/types";
import { Badge, Button, Empty, ErrorBox, Loading, ScoreChip } from "@/components/ui";

function Row({ r, id }: { r: SimilarRow; id: number }) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5 last:border-0">
      <ScoreChip score={r.score} />
      <Link to={`/evidence/${r.id}`} className="min-w-0 flex-1 truncate font-medium hover:text-accent">{r.filename}</Link>
      <span className="text-xs text-muted">{r.case_reference}</span>
      {r.same_case && <Badge tone="accent">this case</Badge>}
      <span className="font-mono text-xs text-muted">{Math.round(r.similarity * (r.similarity <= 1 ? 100 : 1))}%</span>
      <Link to={`/compare?a=${id}&b=${r.id}`}><Button size="sm">Compare</Button></Link>
    </div>
  );
}

export default function SimilarTab({ id }: { id: number }) {
  const q = useApi(() => api.similar(id), [id]);
  if (q.error) return <div className="p-4"><ErrorBox message={String(q.error)} /></div>;
  if (!q.data) return <Loading />;
  const { exact, near } = q.data;
  return (
    <div>
      <p className="border-b border-line px-4 py-3 text-xs text-muted">Exact copies share the SHA-256. Near copies are images whose perceptual hash differs by at most 16 of 64 bits: resized, recompressed, cropped or edited versions.</p>
      <div className="px-4 pt-3 text-xs font-semibold text-muted">Exact copies</div>
      {exact.length === 0 ? <Empty title="No exact copies" /> : exact.map((r) => <Row key={r.id} r={r} id={id} />)}
      <div className="px-4 pt-3 text-xs font-semibold text-muted">Near copies</div>
      {near.length === 0 ? <Empty title="No near copies" /> : near.map((r) => <Row key={r.id} r={r} id={id} />)}
    </div>
  );
}
