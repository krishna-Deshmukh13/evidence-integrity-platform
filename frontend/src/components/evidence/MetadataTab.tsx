import type { Details, EvidenceFull } from "@/lib/types";
import { Mono } from "@/components/ui";
import { CopyButton } from "./util";
import { ArrowSquareOut, MapPin } from "@phosphor-icons/react";

function rows(d: Details): [string, string][] {
  const out: [string, string][] = [];
  const add = (k: string, v: unknown) => { if (v !== undefined && v !== null && v !== "") out.push([k, String(v)]); };
  add("Format", d.format);
  if (d.width && d.height) add("Dimensions", `${d.width} x ${d.height}`);
  add("Duration", d.duration !== undefined ? `${d.duration}s` : undefined);
  add("Frame rate", d.fps);
  add("Sample rate", d.sample_rate);
  add("Pages", d.pages);
  add("Has audio", d.has_audio === undefined ? undefined : d.has_audio ? "yes" : "no");
  add("Editing sessions", d.editing_sessions);
  Object.entries(d.exif ?? {}).forEach(([k, v]) => add(`EXIF ${k}`, v));
  Object.entries(d.tags ?? {}).forEach(([k, v]) => add(`Tag ${k}`, v));
  Object.entries(d.properties ?? {}).forEach(([k, v]) => add(k, v));
  if (d.audio) rows(d.audio).forEach(([k, v]) => out.push([`Audio ${k}`, v]));
  return out;
}

export default function MetadataTab({ ev }: { ev: EvidenceFull }) {
  const list = rows(ev.details ?? {});
  const exif = ev.details?.exif || {};
  const lat = exif.GPSLatitude || exif.latitude;
  const lon = exif.GPSLongitude || exif.longitude;

  return (
    <div className="p-4">
      {lat !== undefined && lon !== undefined && (
        <div className="mb-4 rounded-xl border border-line bg-surface2/40 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 font-semibold text-xs text-ink">
              <MapPin size={16} className="text-accent" />
              <span>Embedded Geographic Coordinates</span>
            </div>
            <a
              href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-accent hover:underline inline-flex items-center gap-1"
            >
              Open in OpenStreetMap <ArrowSquareOut size={12} />
            </a>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-ink">
            <div>Latitude: <strong>{String(lat)}°</strong></div>
            <div>Longitude: <strong>{String(lon)}°</strong></div>
            {exif.GPSAltitude && <div>Altitude: <strong>{String(exif.GPSAltitude)}m</strong></div>}
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <tbody>
            {list.map(([k, v], i) => (
              <tr key={i} className="border-b border-line last:border-0">
                <td className="w-1/3 py-1.5 pr-3 align-top text-muted">{k}</td>
                <td className="break-all py-1.5">{v}</td>
              </tr>
            ))}
            <tr>
              <td className="py-1.5 pr-3 align-top text-muted">SHA-256</td>
              <td className="py-1.5"><Mono className="break-all">{ev.sha256}</Mono> <CopyButton text={ev.sha256} /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
