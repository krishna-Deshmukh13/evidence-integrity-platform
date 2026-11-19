import { Link } from "react-router-dom";
import { FileImage, FileText, VideoCamera, Waveform } from "@phosphor-icons/react";
import type { MediaType } from "@/lib/types";
import { cx, toneText, type Tone } from "@/components/ui";

export function MediaIcon({ type, size = 18 }: { type: MediaType; size?: number }) {
  const c = "shrink-0 text-muted";
  if (type === "image") return <FileImage size={size} className={c} />;
  if (type === "video") return <VideoCamera size={size} className={c} />;
  if (type === "audio") return <Waveform size={size} className={c} />;
  return <FileText size={size} className={c} />;
}

/** Search URL builder: keeps commas readable. */
export function searchUrl(p: Record<string, string>) {
  const q = Object.entries(p).map(([k, v]) => `${k}=${encodeURIComponent(v).replace(/%2C/g, ",")}`).join("&");
  return `/search?${q}`;
}

export function StatLink({ label, value, tone, to }: { label: string; value: React.ReactNode; tone?: Tone; to?: string }) {
  const body = (
    <>
      <div className="text-xs text-muted">{label}</div>
      <div className={cx("mt-1 text-2xl font-semibold", tone && toneText(tone))}>{value}</div>
    </>
  );
  const cls = "block rounded-xl border border-line bg-surface p-4";
  return to ? <Link to={to} className={cx(cls, "hover:bg-surface2")}>{body}</Link> : <div className={cls}>{body}</div>;
}
