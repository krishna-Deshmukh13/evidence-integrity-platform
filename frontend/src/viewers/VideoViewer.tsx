import { useRef } from "react";
import type { EvidenceFull } from "@/lib/types";
import { api } from "@/lib/api";
import { has, clock, pctText, useMediaTime, SeekBar, Playhead, LegendItem, Swatch } from "./parts/util";

export default function VideoViewer({ ev }: { ev: EvidenceFull }) {
  const d = ev.details ?? {};
  const ref = useRef<HTMLVideoElement>(null);
  const { t, dur } = useMediaTime(ref);
  const duration = d.duration && d.duration > 0 ? d.duration : dur;
  const seek = (s: number) => { if (ref.current) { ref.current.currentTime = s; } };
  const tl = d.timeline ?? [];
  const max = Math.max(1e-9, ...tl);
  const frames = d.frames ?? [];
  const a = d.audio;

  return (
    <div className="space-y-4 p-3 sm:p-4">
      <video ref={ref} controls src={api.url.file(ev.id)} className="max-h-[60vh] w-full rounded-lg bg-black" />
      <div>
        <SeekBar duration={duration} onSeek={seek} className="h-16">
          {tl.length > 0 && (
            <div className="absolute inset-0 flex items-end gap-px px-px">
              {tl.map((v, i) => <div key={i} className="flex-1 rounded-t-sm bg-accent/60" style={{ height: `${Math.max(2, (v / max) * 100)}%` }} />)}
            </div>
          )}
          {duration > 0 && (d.frozen ?? []).map((f, i) => (
            <div key={`f${i}`} className="absolute inset-y-0 bg-warn/40" title={`Frozen ${clock(f.start)} - ${clock(f.end)}`}
              style={{ left: `${(f.start / duration) * 100}%`, width: `${Math.max(0.5, ((f.end - f.start) / duration) * 100)}%` }} />
          ))}
          {duration > 0 && (d.cuts ?? []).map((c, i) => (
            <div key={`c${i}`} className="absolute inset-y-0 w-0.5 bg-bad" title={`Cut at ${clock(c)}`} style={{ left: `${(c / duration) * 100}%` }} />
          ))}
          <Playhead t={t} duration={duration} />
        </SeekBar>
        <div className="mt-1.5 flex flex-wrap items-center gap-4">
          <LegendItem swatch={<Swatch className="bg-bad" />}>Cut</LegendItem>
          <LegendItem swatch={<Swatch className="bg-warn" />}>Frozen</LegendItem>
          <span className="ml-auto font-mono text-xs text-muted">{clock(t)} / {clock(duration)}</span>
        </div>
      </div>

      {frames.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold">Sampled frames</h4>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {frames.map((f) => (
              <button key={f.file} onClick={() => seek(f.t)} className="w-28 shrink-0 text-left">
                {has(ev, f.file)
                  ? <img src={api.url.artifact(ev.id, f.file)} alt={f.file} loading="lazy" className="aspect-video w-full rounded border border-line object-cover" />
                  : <div className="aspect-video w-full rounded border border-line bg-surface2" />}
                <div className="mt-0.5 flex justify-between font-mono text-[11px] text-muted"><span>{clock(f.t)}</span><span>AI {f.ai == null ? "-" : pctText(f.ai)}</span></div>
              </button>
            ))}
          </div>
        </div>
      )}

      {has(ev, "ai_heatmap.png") && (
        <div>
          <h4 className="mb-2 text-xs font-semibold">Worst frame: AI heatmap</h4>
          <img src={api.url.artifact(ev.id, "ai_heatmap.png")} alt="AI heatmap" className="max-h-72 max-w-full rounded border border-line" />
        </div>
      )}

      {a && (
        <div>
          <h4 className="mb-2 text-xs font-semibold">Audio track</h4>
          {has(ev, "audio_spectrogram.png") && <img src={api.url.artifact(ev.id, "audio_spectrogram.png")} alt="Audio spectrogram" className="w-full rounded border border-line" />}
          <p className="mt-1.5 text-xs text-muted">
            {[a.duration != null ? clock(a.duration) : null, a.sample_rate ? `${a.sample_rate} Hz` : null,
              a.synthetic_avg != null ? `synthetic voice avg ${pctText(a.synthetic_avg)}` : null,
              a.cutoff_hz ? `bandwidth cutoff ${(a.cutoff_hz / 1000).toFixed(1)} kHz` : null].filter(Boolean).join(" · ") || "No audio details."}
          </p>
        </div>
      )}
    </div>
  );
}
