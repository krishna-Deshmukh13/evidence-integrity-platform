import type { Category, MediaType, ReviewStatus, SearchParams, Verdict } from "@/lib/types";

export const MEDIA: MediaType[] = ["image", "video", "audio", "document"];
export const VERDICTS: Verdict[] = ["Consistent", "Needs review", "Likely manipulated"];
export const REVIEWS: ReviewStatus[] = ["not_reviewed", "reviewed", "flagged", "cleared"];
export const CATEGORIES: Category[] = ["metadata", "pixel", "ai", "document", "audio", "container"];
export const CHECKS = [
  "copy_move", "noise", "ela", "software", "modified_after_capture", "dates_out_of_order", "exif_stripped", "exif_thumbnail",
  "size_mismatch", "ai_image", "face_deepfake", "ai_video", "synthetic_voice", "digital_silence", "bandwidth", "tool_tags",
  "hard_cuts", "frozen_frames", "video_editor", "reencoded", "incremental_updates", "signature_coverage", "font_forensics",
  "hidden_text", "tracked_changes", "mixed_fonts", "pdf_producer", "hash_mismatch",
];
export const KEYS = ["q", "media_type", "verdict", "review_status", "case_id", "category", "check", "assignee_id", "min_score", "max_score", "date_from", "date_to", "sort"] as const;
export type Key = (typeof KEYS)[number];
export const MULTI: Key[] = ["media_type", "verdict", "review_status"];

export const humanize = (s: string) => { const t = s.replace(/_/g, " "); return t.charAt(0).toUpperCase() + t.slice(1); };
export const splitList = (s: string | null | undefined): string[] => (s ? s.split(",").filter(Boolean) : []);

const num = (s: string | null): number | undefined => {
  if (s === null || s === "") return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
};

export function toSearchParams(sp: URLSearchParams): SearchParams {
  const sort = sp.get("sort");
  return {
    q: sp.get("q") || undefined,
    media_type: sp.get("media_type") || undefined,
    verdict: sp.get("verdict") || undefined,
    review_status: sp.get("review_status") || undefined,
    case_id: num(sp.get("case_id")),
    category: sp.get("category") || undefined,
    check: sp.get("check") || undefined,
    assignee_id: num(sp.get("assignee_id")),
    min_score: num(sp.get("min_score")),
    max_score: num(sp.get("max_score")),
    date_from: sp.get("date_from") || undefined,
    date_to: sp.get("date_to") || undefined,
    sort: sort === "newest" || sort === "risk" ? sort : undefined,
  };
}

export type Patch = (p: Partial<Record<Key, string | undefined>>) => void;
