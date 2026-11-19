import { Link } from "react-router-dom";
import { ArrowSquareOut, MapPin, WarningCircle } from "@phosphor-icons/react";
import { Card, Empty, ErrorBox, Loading, ScoreChip, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { MediaIcon } from "@/components/case/helpers";
import type { GpsPoint } from "@/lib/types";

export default function CaseGpsTab({ caseId }: { caseId: number }) {
  const { data: g, error, loading, reload } = useApi(() => api.caseGps(caseId), [caseId]);

  if (loading && !g) return <Loading />;
  if (error && !g) return <ErrorBox message={error} onRetry={reload} />;
  if (!g) return null;

  if (!g.has_gps || g.points.length === 0) {
    return (
      <Card className="p-8 text-center">
        <Empty
          title="No GPS coordinates recorded"
          hint="None of the files in this case contain embedded EXIF GPS tags or coordinates."
        />
      </Card>
    );
  }

  // Calculate bounding box for SVG plotting
  const lats = g.points.map((p) => p.lat);
  const lons = g.points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const latSpan = Math.max(0.01, maxLat - minLat);
  const lonSpan = Math.max(0.01, maxLon - minLon);

  const W = 640;
  const H = 340;
  const PAD = 50;

  // Convert lat/lon to SVG (x, y) coordinates
  const project = (lat: number, lon: number) => {
    const x = PAD + ((lon - minLon) / lonSpan) * (W - 2 * PAD);
    // Invert y because latitude increases upwards, SVG increases downwards
    const y = H - (PAD + ((lat - minLat) / latSpan) * (H - 2 * PAD));
    return { x, y };
  };

  return (
    <div className="space-y-4">
      {/* 1. Anomaly Alert Banner */}
      {g.anomalies.length > 0 && (
        <Card className="border-bad/60 bg-bad/5 p-4">
          <div className="flex items-center gap-2 font-semibold text-bad">
            <WarningCircle size={20} weight="fill" />
            <span>Geographic Outlier Alert (&gt; 50 km from case cluster)</span>
          </div>
          <div className="mt-2 space-y-2">
            {g.anomalies.map((a, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-bad/30 bg-surface p-2.5 text-xs"
              >
                <div>
                  <Link
                    to={`/evidence/${a.evidence_id}`}
                    className="font-medium text-ink hover:text-accent hover:underline"
                  >
                    {a.filename}
                  </Link>
                  <div className="text-muted">{a.message}</div>
                </div>
                <Link
                  to={`/evidence/${a.evidence_id}`}
                  className="rounded bg-bad/15 px-2 py-1 text-xs font-semibold text-bad hover:bg-bad/25"
                >
                  Inspect File →
                </Link>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 2. Offline-Friendly SVG Coordinate Plot */}
      <Card>
        <div className="border-b border-line p-4">
          <h3 className="text-sm font-semibold text-ink">Geographic Coordinate Plot</h3>
          <div className="text-xs text-muted">
            Relative spatial positioning of EXIF GPS pins across case evidence
          </div>
        </div>

        <div className="p-4">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-80 rounded-xl border border-line bg-surface2/30 select-none">
            {/* Grid Lines */}
            <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="currentColor" strokeDasharray="3 3" className="text-line" />
            <line x1={W - PAD} y1={PAD} x2={W - PAD} y2={H - PAD} stroke="currentColor" strokeDasharray="3 3" className="text-line" />
            <line x1={PAD} y1={PAD} x2={W - PAD} y2={PAD} stroke="currentColor" strokeDasharray="3 3" className="text-line" />
            <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="currentColor" strokeDasharray="3 3" className="text-line" />

            {/* Centroid Marker */}
            {g.centroid && (
              <g transform={`translate(${project(g.centroid.lat, g.centroid.lon).x}, ${project(g.centroid.lat, g.centroid.lon).y})`}>
                <circle r="14" fill="currentColor" className="text-accent/15" />
                <circle r="3" fill="currentColor" className="text-accent" />
                <text y="-8" fontSize="8" textAnchor="middle" className="fill-muted font-medium">Cluster Centroid</text>
              </g>
            )}

            {/* Evidence Pins */}
            {g.points.map((p) => {
              const { x, y } = project(p.lat, p.lon);
              const toneColor =
                p.is_anomaly
                  ? "fill-bad"
                  : p.verdict === "Likely manipulated"
                  ? "fill-bad"
                  : p.verdict === "Needs review"
                  ? "fill-warn"
                  : "fill-good";

              return (
                <g key={p.evidence_id} transform={`translate(${x}, ${y})`} className="cursor-pointer group">
                  <circle r={p.is_anomaly ? 18 : 12} className={cx(toneColor, "opacity-20 transition group-hover:opacity-40")} />
                  <circle r="6" className={cx(toneColor, "stroke-surface stroke-2 transition group-hover:scale-125")} />

                  <text
                    y="-10"
                    textAnchor="middle"
                    fontSize="9"
                    fontWeight="600"
                    className="fill-ink"
                  >
                    {p.filename.length > 14 ? p.filename.slice(0, 12) + "…" : p.filename}
                  </text>
                  <text
                    y="18"
                    textAnchor="middle"
                    fontSize="7.5"
                    className="fill-muted"
                  >
                    {p.lat.toFixed(4)}, {p.lon.toFixed(4)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* 3. Coordinates Table */}
        <div className="border-t border-line overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface2 text-muted">
              <tr>
                <th className="px-4 py-2.5">File</th>
                <th className="px-3 py-2.5">Latitude / Longitude</th>
                <th className="px-3 py-2.5">Dist to Others</th>
                <th className="px-3 py-2.5">Verdict</th>
                <th className="px-4 py-2.5 text-right">Map Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {g.points.map((p) => (
                <tr key={p.evidence_id} className="hover:bg-surface2 transition">
                  <td className="px-4 py-2.5 font-medium">
                    <Link to={`/evidence/${p.evidence_id}`} className="hover:text-accent flex items-center gap-2">
                      <MediaIcon type={p.media_type} size={15} />
                      {p.filename}
                    </Link>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-muted">
                    {p.lat.toFixed(5)}°, {p.lon.toFixed(5)}°
                  </td>
                  <td className="px-3 py-2.5">
                    {p.is_anomaly ? (
                      <span className="rounded bg-bad/15 px-1.5 py-0.5 font-semibold text-bad">
                        {p.min_dist_to_others_km} km (Outlier &gt;50km)
                      </span>
                    ) : (
                      <span className="text-muted">{p.min_dist_to_others_km ?? 0} km</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <ScoreChip score={p.score} />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <a
                      href={`https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lon}#map=16/${p.lat}/${p.lon}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-accent hover:underline"
                    >
                      <span>OSM</span>
                      <ArrowSquareOut size={13} />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
