import { FileText, Image as ImgIcon, VideoCamera, Waveform } from "@phosphor-icons/react";
import type { MediaType } from "@/lib/types";

export function MediaIcon({ type, size = 20, className }: { type: MediaType; size?: number; className?: string }) {
  const p = { size, className };
  if (type === "image") return <ImgIcon {...p} />;
  if (type === "video") return <VideoCamera {...p} />;
  if (type === "audio") return <Waveform {...p} />;
  return <FileText {...p} />;
}
