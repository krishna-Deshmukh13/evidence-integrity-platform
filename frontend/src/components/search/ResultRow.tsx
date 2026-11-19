import { Link } from "react-router-dom";
import { ScoreChip, VerdictText } from "@/components/ui";
import { ago, bytes, REVIEW_LABEL } from "@/lib/format";
import type { SearchRow } from "@/lib/types";
import { MediaIcon } from "./MediaIcon";

export function ResultRow({ r }: { r: SearchRow }) {
  return (
    <Link to={`/evidence/${r.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-surface2">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-surface2 text-muted"><MediaIcon type={r.media_type} /></span>
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{r.filename}</div>
        <div className="truncate text-xs text-muted">{bytes(r.size)} · {r.case_reference} · {r.case_title}</div>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs sm:hidden">
          <VerdictText verdict={r.verdict} /><span className="text-muted">{REVIEW_LABEL[r.review_status]}</span><span className="text-muted">{ago(r.received_at)}</span>
        </div>
      </div>
      <div className="hidden w-36 shrink-0 text-sm sm:block"><VerdictText verdict={r.verdict} /></div>
      <div className="hidden w-28 shrink-0 text-xs text-muted sm:block">{REVIEW_LABEL[r.review_status]}</div>
      <div className="hidden w-20 shrink-0 text-right text-xs text-muted md:block">{ago(r.received_at)}</div>
      <ScoreChip score={r.score} />
    </Link>
  );
}
