import { useRef } from "react";
import type { EvidenceFull } from "@/lib/types";
import { api } from "@/lib/api";
import { has, clock, frac, scoreColor, useMediaTime, SeekBar, Playhead, LegendItem, Swatch } from "./parts/util";

export default function AudioViewer({ ev }: { ev: EvidenceFull }) {
  const d = ev.details ?? {};
  const ref = useRef<HTMLAudioElement>(null);
  const { t, dur } = useMediaTime(ref);
  const duration = d.duration && d.duration > 0 ? d.duration : dur;
  const seek = (s: number) => { if (ref.current) ref.current.currentTime = s; };
  const wf = d.waveform ?? [];
  const wmax = Math.max(1e-9, ...wf.map(Math.abs));
  const n = wf.length;
  const silences = d.silences ?? [];
  const windows = d.windows ?? [];
  const pc = (v: number | undefined) => (v == null ? "-" : `${Math.round(frac(v) * 100)}%`);

  const stats = [
    d.synthetic_avg != null || d.synthetic_peak != null ? `Synthetic voice avg ${pc(d.synthetic_avg)} / peak ${pc(d.synthetic_peak)}` : null,
    `Digital silence ${silences.length}`,
    duration > 0 ? `Duration ${clock(duration)}` : null,
    d.sample_rate ? `${d.sample_rate} Hz` : null,
    d.cutoff_hz ? `Bandwidth cutoff ${(d.cutoff_hz / 1000).toFixed(1)} kHz` : null,
  ].filter(Boolean);

  return (
    <div className="space-y-3 p-3 sm:p-4">
      <audio ref={ref} controls src={api.url.file(ev.id)} className="w-full" />
      {n > 0 && (
        <div>
          <SeekBar duration={duration} onSeek={seek} className="h-24">
            <svg className="absolute inset-0 h-full w-full text-accent" viewBox={`0 0 ${n} 100`} preserveAspectRatio="none">
              {wf.map((v, i) => {
                const h = Math.max(1, (Math.abs(v) / wmax) * 48);
                return <rect key={i} x={i + 0.1} y={50 - h} width={0.8} height={h * 2} fill="currentColor" />;
              })}
            </svg>
            {duration > 0 && silences.map((s, i) => (
              <div key={i} className="absolute inset-y-0 bg-warn/30" title={`Silence ${clock(s.start)} - ${clock(s.end)}`}
                style={{ left: `${(s.start / duration) * 100}%`, width: `${Math.max(0.4, ((s.end - s.start) / duration) * 100)}%` }} />
            ))}
            <Playhead t={t} duration={duration} />
          </SeekBar>
          <div className="mt-1.5 flex flex-wrap items-center gap-4">
            <LegendItem swatch={<Swatch className="bg-warn" />}>Digital silence</LegendItem>
            <span className="ml-auto font-mono text-xs text-muted">{clock(t)} / {clock(duration)}</span>
          </div>
        </div>
      )}
      {windows.length > 0 && duration > 0 && (
        <div>
          <h4 className="mb-1 text-xs font-semibold">Synthetic voice</h4>
          <SeekBar duration={duration} onSeek={seek} className="h-5">
            {windows.map((w, i) => (
              <div key={i} className="absolute inset-y-0" title={`${clock(w.start)} - ${clock(w.end)}: ${Math.round(frac(w.score) * 100)}%`}
                style={{ left: `${(w.start / duration) * 100}%`, width: `${((w.end - w.start) / duration) * 100}%`, background: scoreColor(w.score) }} />
            ))}
            <Playhead t={t} duration={duration} />
          </SeekBar>
        </div>
      )}
      {has(ev, "spectrogram.png") && (
        <img src={api.url.artifact(ev.id, "spectrogram.png")} alt="Spectrogram" className="w-full rounded border border-line" />
      )}
      <p className="text-xs text-muted">{stats.join(" · ")}</p>
    </div>
  );
}
