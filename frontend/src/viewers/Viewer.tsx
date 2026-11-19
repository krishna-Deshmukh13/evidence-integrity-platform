// Picks the viewer for the evidence type. DO NOT EDIT (Part 3 replaces the five viewers it imports).
import type { EvidenceFull } from "@/lib/types";
import ImageViewer from "./ImageViewer";
import VideoViewer from "./VideoViewer";
import AudioViewer from "./AudioViewer";
import PdfViewer from "./PdfViewer";
import DocxViewer from "./DocxViewer";

export default function Viewer({ ev }: { ev: EvidenceFull }) {
  if (ev.media_type === "image") return <ImageViewer ev={ev} />;
  if (ev.media_type === "video") return <VideoViewer ev={ev} />;
  if (ev.media_type === "audio") return <AudioViewer ev={ev} />;
  return ev.filename.toLowerCase().endsWith(".docx") ? <DocxViewer ev={ev} /> : <PdfViewer ev={ev} />;
}
