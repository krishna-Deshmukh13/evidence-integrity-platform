import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowsClockwise,
  ArrowsLeftRight,
  Broadcast,
  Camera,
  CheckCircle,
  ClockCounterClockwise,
  Compass,
  Crosshair,
  Eye,
  FastForward,
  FileCode,
  Funnel,
  Globe,
  MagnifyingGlass,
  MapPin,
  NavigationArrow,
  Pause,
  Play,
  ShieldCheck,
  SkipBack,
  SkipForward,
  Sparkle,
  SpeakerHigh,
  VideoCamera,
  Warning,
  X,
} from "@phosphor-icons/react";
import { Button, Card, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";

// Fix default Leaflet icon paths
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function TacticalMapPage() {
  const nav = useNavigate();
  const { data: mapData, error, loading, reload } = useApi(() => api.tacticalMap(), []);

  const [selectedCity, setSelectedCity] = useState<string>("all");
  const [selectedVerdict, setSelectedVerdict] = useState<string>("all");
  const [showCorridors, setShowCorridors] = useState<boolean>(true);
  const [showRadar, setShowRadar] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedPoint, setSelectedPoint] = useState<any | null>(null);
  const [mapStyle, setMapStyle] = useState<"google-streets" | "google-hybrid" | "osm">("google-streets");

  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const corridorsLayerRef = useRef<L.LayerGroup | null>(null);
  const radarLayerRef = useRef<L.LayerGroup | null>(null);

  // Time-Lapse & Replay Engine State
  const [replayActive, setReplayActive] = useState<boolean>(false);
  const [isPlayingReplay, setIsPlayingReplay] = useState<boolean>(false);
  const [replayStep, setReplayStep] = useState<number>(0);
  const [replaySpeed, setReplaySpeed] = useState<number>(1);

  // Chronologically Sorted Incident Events for Replay
  const chronologicalEvents = useMemo(() => {
    if (!mapData?.points) return [];
    return [...mapData.points].sort((a, b) => {
      const tA = new Date(a.received_at || 0).getTime() || a.id;
      const tB = new Date(b.received_at || 0).getTime() || b.id;
      return tA - tB;
    });
  }, [mapData]);

  // Current Replay Point
  const currentReplayPoint = useMemo(() => {
    if (!chronologicalEvents.length) return null;
    return chronologicalEvents[Math.min(replayStep, chronologicalEvents.length - 1)];
  }, [chronologicalEvents, replayStep]);

  // Auto-play replay ticker
  useEffect(() => {
    if (!replayActive || !isPlayingReplay || chronologicalEvents.length === 0) return;
    const intervalTime = Math.max(250, 1500 / replaySpeed);
    const timer = setInterval(() => {
      setReplayStep((prev) => {
        if (prev >= chronologicalEvents.length - 1) {
          setIsPlayingReplay(false);
          return prev;
        }
        const next = prev + 1;
        const targetPt = chronologicalEvents[next];
        if (targetPt && mapInstanceRef.current) {
          mapInstanceRef.current.panTo([targetPt.lat, targetPt.lon], { animate: true, duration: 0.5 });
        }
        return next;
      });
    }, intervalTime);
    return () => clearInterval(timer);
  }, [replayActive, isPlayingReplay, replaySpeed, chronologicalEvents]);

  // Filtered Points (by City, Verdict, Search)
  const filteredPoints = useMemo(() => {
    if (!mapData?.points) return [];
    let list = mapData.points;

    if (selectedCity !== "all") {
      list = list.filter((p: any) => p.city === selectedCity);
    }
    if (selectedVerdict !== "all") {
      list = list.filter((p: any) => p.verdict === selectedVerdict);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (p: any) =>
          p.filename.toLowerCase().includes(q) ||
          p.case_reference.toLowerCase().includes(q) ||
          p.city.toLowerCase().includes(q) ||
          p.location_name.toLowerCase().includes(q)
      );
    }
    return list;
  }, [mapData, selectedCity, selectedVerdict, searchQuery]);

  // Active Points for Map Drawing (Replay Active or Filtered)
  const activePoints = useMemo(() => {
    if (replayActive) {
      return chronologicalEvents.slice(0, replayStep + 1);
    }
    return filteredPoints;
  }, [replayActive, chronologicalEvents, replayStep, filteredPoints]);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Center on India / Global Hubs
    const map = L.map(mapContainerRef.current, {
      center: [20.5937, 78.9629],
      zoom: 5,
      zoomControl: false,
    });

    // Zoom control at bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    corridorsLayerRef.current = L.layerGroup().addTo(map);
    radarLayerRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Tile Layer when mapStyle changes (Google Streets, Google Hybrid Satellite, OSM)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }

    let layer: L.TileLayer;
    if (mapStyle === "google-streets") {
      layer = L.tileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
        attribution: '&copy; Google Maps',
        maxZoom: 20,
      });
    } else if (mapStyle === "google-hybrid") {
      layer = L.tileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
        attribution: '&copy; Google Maps Satellite',
        maxZoom: 20,
      });
    } else {
      layer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });
    }

    layer.addTo(map);
    tileLayerRef.current = layer;
  }, [mapStyle, mapInstanceRef.current]);

  // Update Markers & Layers when data, filters, or replay changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !markersLayerRef.current) return;

    // Clear previous
    markersLayerRef.current.clearLayers();
    corridorsLayerRef.current?.clearLayers();
    radarLayerRef.current?.clearLayers();

    if (replayActive) {
      // Replay Mode: Sequential corridor drawing
      if (activePoints.length >= 2) {
        const replayCoords = activePoints.map((p: any) => [p.lat, p.lon] as [number, number]);
        const replayLine = L.polyline(replayCoords, {
          color: "#F59E0B",
          weight: 4.5,
          opacity: 0.95,
          dashArray: "6, 6",
        });
        replayLine.bindTooltip(`<strong>Timeline replay Sequence:</strong> Steps 1 to ${activePoints.length}`, { sticky: true });
        corridorsLayerRef.current?.addLayer(replayLine);
      }

      // Replay Mode: Draw pins up to current step
      activePoints.forEach((p: any, idx: number) => {
        const isCurrentLatest = idx === activePoints.length - 1;
        const isManipulated = p.verdict === "Likely manipulated" || p.score < 50;
        const markerColor = isManipulated ? "#EF4444" : "#10B981";

        const customIcon = L.divIcon({
          className: "custom-forensic-pin",
          html: `
            <div style="
              position: relative;
              width: ${isCurrentLatest ? "36px" : "28px"};
              height: ${isCurrentLatest ? "36px" : "28px"};
              border-radius: 50%;
              background-color: ${isCurrentLatest ? "#F59E0B" : markerColor};
              border: ${isCurrentLatest ? "3.5px solid #ffffff" : "2.5px solid #ffffff"};
              box-shadow: 0 4px 16px rgba(0,0,0,0.4);
              display: flex;
              align-items: center;
              justify-content: center;
              color: #ffffff;
              font-family: monospace;
              font-size: ${isCurrentLatest ? "11px" : "9px"};
              font-weight: 900;
              cursor: pointer;
              transition: all 0.2s ease;
            ">
              ${isCurrentLatest ? `★${p.score}` : p.score}
              ${isCurrentLatest ? `
                <span style="
                  position: absolute;
                  inset: -8px;
                  border-radius: 50%;
                  border: 3px solid #F59E0B;
                  opacity: 0.9;
                  animation: ping 1.2s cubic-bezier(0, 0, 0.2, 1) infinite;
                "></span>
              ` : isManipulated ? `
                <span style="
                  position: absolute;
                  inset: -5px;
                  border-radius: 50%;
                  border: 2px solid ${markerColor};
                  opacity: 0.75;
                  animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
                "></span>
              ` : ""}
            </div>
          `,
          iconSize: isCurrentLatest ? [36, 36] : [28, 28],
          iconAnchor: isCurrentLatest ? [18, 18] : [14, 14],
        });

        const marker = L.marker([p.lat, p.lon], { icon: customIcon });
        marker.on("click", () => setSelectedPoint(p));
        marker.bindPopup(`
          <div style="font-family: sans-serif; font-size: 11px; max-width: 250px; padding: 2px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <span style="font-family: monospace; font-weight: 800; color: #D97706; background: rgba(245,158,11,0.12); padding: 2px 6px; border-radius: 4px;">
                REPLAY EVENT #${idx + 1}
              </span>
              <span style="font-weight: 800; color: ${markerColor};">
                ${p.score}/100
              </span>
            </div>
            <div style="font-weight: bold; font-size: 12px; color: #0F172A; margin-bottom: 3px; word-break: break-all;">
              ${p.filename}
            </div>
            <div style="color: #64748B; font-size: 10.5px; margin-bottom: 6px;">
              ${p.location_name} (${p.city})
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid #E2E8F0; padding-top: 4px;">
              <span style="font-size: 9px; font-weight: bold; text-transform: uppercase; color: #94A3B8;">
                ${p.media_type}
              </span>
              <a href="/evidence/${p.id}" style="color: #3B3BF5; font-weight: bold; text-decoration: none;">
                Open file &rarr;
              </a>
            </div>
          </div>
        `);
        markersLayerRef.current?.addLayer(marker);
      });
    } else {
      // Normal Mode: 1. Draw Corridors
      if (showCorridors && mapData?.corridors) {
        mapData.corridors.forEach((corr: any) => {
          const latlngs = corr.points.map((p: any) => [p.lat, p.lon] as [number, number]);
          if (latlngs.length >= 2) {
            const polyline = L.polyline(latlngs, {
              color: "#3B82F6",
              weight: 3,
              opacity: 0.65,
              dashArray: "6, 8",
            });
            polyline.bindTooltip(
              `<strong>Suspect Movement Corridor:</strong> ${corr.case_reference} (${corr.total_points} events)`,
              { sticky: true }
            );
            corridorsLayerRef.current?.addLayer(polyline);
          }
        });
      }

      // 2. Draw Nearby circles Circles
      if (showRadar && mapData?.proximity_alerts) {
        mapData.proximity_alerts.forEach((alert: any) => {
          const circle = L.circle([alert.source.lat, alert.source.lon], {
            radius: alert.distance_meters,
            color: "#EF4444",
            fillColor: "#EF4444",
            fillOpacity: 0.08,
            weight: 1.5,
            dashArray: "4, 6",
          });
          circle.bindTooltip(
            `<strong>Syndicate Proximity Alert:</strong> ${alert.distance_meters}m between ${alert.source.case_reference} and ${alert.target.case_reference}`,
            { sticky: true }
          );
          radarLayerRef.current?.addLayer(circle);
        });
      }

      // 3. Draw All Filtered Pins
      filteredPoints.forEach((p: any) => {
        const isManipulated = p.verdict === "Likely manipulated" || p.score < 50;
        const markerColor = isManipulated ? "#EF4444" : "#10B981";

        const customIcon = L.divIcon({
          className: "custom-forensic-pin",
          html: `
            <div style="
              position: relative;
              width: 28px;
              height: 28px;
              border-radius: 50%;
              background-color: ${markerColor};
              border: 2.5px solid #ffffff;
              box-shadow: 0 4px 12px rgba(0,0,0,0.3);
              display: flex;
              align-items: center;
              justify-content: center;
              color: #ffffff;
              font-family: monospace;
              font-size: 9px;
              font-weight: 800;
              cursor: pointer;
              transition: transform 0.15s ease;
            ">
              ${p.score}
              ${isManipulated ? `
                <span style="
                  position: absolute;
                  inset: -5px;
                  border-radius: 50%;
                  border: 2px solid ${markerColor};
                  opacity: 0.75;
                  animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
                "></span>
              ` : ""}
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const marker = L.marker([p.lat, p.lon], { icon: customIcon });
        marker.on("click", () => setSelectedPoint(p));
        marker.bindPopup(`
          <div style="font-family: sans-serif; font-size: 11px; max-width: 240px; padding: 2px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <span style="font-family: monospace; font-weight: 800; color: #3B3BF5; background: rgba(59,59,245,0.08); padding: 2px 6px; border-radius: 4px;">
                ${p.case_reference}
              </span>
              <span style="font-weight: 800; color: ${markerColor};">
                ${p.score}/100
              </span>
            </div>
            <div style="font-weight: bold; font-size: 12px; color: #0F172A; margin-bottom: 3px; word-break: break-all;">
              ${p.filename}
            </div>
            <div style="color: #64748B; font-size: 10.5px; margin-bottom: 6px;">
              ${p.location_name} (${p.city})
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid #E2E8F0; padding-top: 4px;">
              <span style="font-size: 9px; font-weight: bold; text-transform: uppercase; color: #94A3B8;">
                ${p.media_type}
              </span>
              <a href="/evidence/${p.id}" style="color: #3B3BF5; font-weight: bold; text-decoration: none;">
                Open file &rarr;
              </a>
            </div>
          </div>
        `);
        markersLayerRef.current?.addLayer(marker);
      });

      // Auto-fit bounds if points exist
      if (filteredPoints.length > 0 && selectedCity !== "all") {
        const bounds = L.latLngBounds(filteredPoints.map((p: any) => [p.lat, p.lon]));
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 13 });
      }
    }
  }, [activePoints, replayActive, replayStep, showCorridors, showRadar, selectedCity]);

  // Center on a city
  const panToCity = (lat: number, lon: number) => {
    mapInstanceRef.current?.flyTo([lat, lon], 12, { duration: 1.2 });
  };

  if (loading && !mapData) return <Loading label="Loading Incident & Case Map..." />;
  if (error && !mapData) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div className="space-y-4 pb-10">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold text-muted flex items-center gap-1.5">
            <Compass size={14} className="text-accent" weight="fill" />
            Location map
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Incident & Case Map
          </h1>
          <p className="text-xs text-muted mt-0.5">
            See incident locations, movement paths, and nearby cases on the map
          </p>
        </div>

        {/* Global Summary Badge */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-xs font-semibold text-ink shadow-2xs">
            <span className="size-2 rounded-full bg-[#12B981]" />
            <span>
              <strong>{mapData?.total_mapped_evidence ?? 99}</strong> Mapped files across <strong>{mapData?.total_cities ?? 23}</strong> Cities
            </span>
          </div>
        </div>
      </div>

      {/* Top KPI Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="card-bento p-3.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="size-7 rounded-xl bg-blue-500/10 text-blue-600 grid place-items-center">
              <MapPin size={16} weight="bold" />
            </span>
            <span className="font-mono text-base font-extrabold text-ink">
              {mapData?.total_mapped_evidence ?? 99}
            </span>
          </div>
          <div className="text-xs font-bold text-ink">Pinned locations</div>
          <div className="text-[10px] text-muted">Locations found in file details</div>
        </Card>

        <Card className="card-bento p-3.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="size-7 rounded-xl bg-emerald-500/10 text-emerald-600 grid place-items-center">
              <Globe size={16} weight="bold" />
            </span>
            <span className="font-mono text-base font-extrabold text-ink">
              {mapData?.total_cities ?? 23}
            </span>
          </div>
          <div className="text-xs font-bold text-ink">Cities and places</div>
          <div className="text-[10px] text-muted">Local and global locations</div>
        </Card>

        <Card className="card-bento p-3.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="size-7 rounded-xl bg-rose-500/10 text-rose-600 grid place-items-center">
              <Broadcast size={16} weight="bold" />
            </span>
            <span className="font-mono text-base font-extrabold text-rose-600">
              {mapData?.proximity_alerts_count ?? 15}
            </span>
          </div>
          <div className="text-xs font-bold text-ink">Nearby cases (&lt;2.5 km)</div>
          <div className="text-[10px] text-muted">Files found close together</div>
        </Card>

        <Card className="card-bento p-3.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="size-7 rounded-xl bg-purple-500/10 text-purple-600 grid place-items-center">
              <NavigationArrow size={16} weight="bold" />
            </span>
            <span className="font-mono text-base font-extrabold text-ink">
              {mapData?.corridors?.length ?? 18}
            </span>
          </div>
          <div className="text-xs font-bold text-ink">Movement paths</div>
          <div className="text-[10px] text-muted">Connected paths over time</div>
        </Card>
      </div>

      {/* Main Map & Drawer Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left 8 or 9 Cols: The Interactive Leaflet Canvas */}
        <div className="lg:col-span-8 xl:col-span-9 flex flex-col rounded-lg border border-line bg-surface overflow-hidden shadow-[var(--shadow-bento)]">
          {/* Map Controls HUD Bar */}
          <div className="p-3 border-b border-line bg-surface/95 backdrop-blur flex flex-wrap items-center justify-between gap-2.5">
            {/* Left: Layer Toggles & Replay Engine */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const nextState = !replayActive;
                  setReplayActive(nextState);
                  setIsPlayingReplay(false);
                  if (nextState) {
                    setReplayStep(0);
                    if (chronologicalEvents[0] && mapInstanceRef.current) {
                      mapInstanceRef.current.panTo([chronologicalEvents[0].lat, chronologicalEvents[0].lon], { animate: true });
                    }
                  }
                }}
                className={cx(
                  "flex items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-bold transition cursor-pointer shadow-xs",
                  replayActive
                    ? "bg-amber-500 text-white border-amber-600 ring-2 ring-amber-400/30"
                    : "border-line bg-surface2/60 text-ink hover:border-accent hover:text-accent"
                )}
              >
                <ClockCounterClockwise size={15} weight="bold" />
                <span>{replayActive ? "Timeline playing" : "Play timeline"}</span>
              </button>

              <button
                onClick={() => setShowCorridors(!showCorridors)}
                className={cx(
                  "flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-bold transition cursor-pointer",
                  showCorridors
                    ? "bg-accent/10 border-accent text-accent"
                    : "border-line bg-surface2/60 text-muted hover:text-ink"
                )}
              >
                <NavigationArrow size={14} weight="bold" />
                <span>Movement paths</span>
              </button>

              <button
                onClick={() => setShowRadar(!showRadar)}
                className={cx(
                  "flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-bold transition cursor-pointer",
                  showRadar
                    ? "bg-rose-500/10 border-rose-500 text-rose-600"
                    : "border-line bg-surface2/60 text-muted hover:text-ink"
                )}
              >
                <Broadcast size={14} weight="bold" />
                <span>Nearby circles</span>
              </button>
            </div>

            {/* Right: Quick City Jump Bar */}
            <div className="flex items-center gap-1.5 overflow-x-auto py-0.5">
              <span className="text-[10px] font-bold uppercase text-muted tracking-wider mr-1">Cities:</span>
              {[
                { name: "Mumbai", lat: 18.9322, lon: 72.8336 },
                { name: "New Delhi", lat: 28.6180, lon: 77.2090 },
                { name: "Bengaluru", lat: 12.9797, lon: 77.5907 },
                { name: "Hyderabad", lat: 17.4474, lon: 78.3762 },
                { name: "San Francisco", lat: 37.6189, lon: -122.3750 },
                { name: "London", lat: 51.5055, lon: -0.0195 },
                { name: "New York", lat: 40.7071, lon: -74.0090 },
              ].map((c) => (
                <button
                  key={c.name}
                  onClick={() => {
                    setSelectedCity(c.name);
                    panToCity(c.lat, c.lon);
                  }}
                  className="rounded-lg border border-line bg-surface2/40 px-2 py-0.5 text-[11px] font-semibold text-ink hover:border-accent hover:text-accent transition cursor-pointer shrink-0"
                >
                  {c.name}
                </button>
              ))}
            </div>
          </div>

          {/* Leaflet Map Stage */}
          <div className="relative h-[620px] w-full bg-[#E5E9EC] dark:bg-[#111827]">
            <div ref={mapContainerRef} className="h-full w-full z-10" />

            {/* Real Map Layer Switcher (Top Right) */}
            <div className="absolute top-4 right-4 z-20 flex items-center gap-1 rounded-xl border border-line/80 bg-surface/95 p-1 shadow-md backdrop-blur">
              <button
                onClick={() => setMapStyle("google-streets")}
                className={cx(
                  "px-2.5 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer",
                  mapStyle === "google-streets" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink hover:bg-surface2"
                )}
              >
                <span>🗺️ Google Streets</span>
              </button>
              <button
                onClick={() => setMapStyle("google-hybrid")}
                className={cx(
                  "px-2.5 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer",
                  mapStyle === "google-hybrid" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink hover:bg-surface2"
                )}
              >
                <span>🛰️ Google Satellite</span>
              </button>
              <button
                onClick={() => setMapStyle("osm")}
                className={cx(
                  "px-2.5 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer",
                  mapStyle === "osm" ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink hover:bg-surface2"
                )}
              >
                <span>🏙️ Street Map</span>
              </button>
            </div>

            {/* Floating Top Left HUD Banner during Replay */}
            {replayActive && currentReplayPoint && (
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2.5 rounded-xl border border-amber-500/40 bg-surface/95 px-3 py-2 shadow-lg backdrop-blur text-xs">
                <span className="size-2.5 rounded-full bg-amber-500 animate-ping" />
                <div>
                  <div className="font-bold text-ink text-[10px]">
                    Timeline replay · Event #{replayStep + 1} of {chronologicalEvents.length}
                  </div>
                  <div className="font-mono text-muted text-[11px] truncate max-w-xs">
                    {currentReplayPoint.location_name} ({currentReplayPoint.city})
                  </div>
                </div>
              </div>
            )}

            {/* Floating Map Legend (Bottom Left - Hidden when Replay HUD is large) */}
            {!replayActive && (
              <div className="pointer-events-none absolute bottom-4 left-4 z-20 flex flex-col gap-1.5 rounded-xl border border-line/80 bg-surface/90 p-3 shadow-lg backdrop-blur text-[11px] font-semibold">
                <div className="flex items-center gap-2">
                  <span className="size-2.5 rounded-full bg-[#EF4444]" />
                  <span className="text-ink">Probably fake (&lt;50 trust)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="size-2.5 rounded-full bg-[#10B981]" />
                  <span className="text-ink">Looks genuine (&gt;75 trust)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-0.5 w-4 bg-blue-500 border-dashed" />
                  <span className="text-ink">Movement path</span>
                </div>
              </div>
            )}
          </div>

          {/* Play timeline & Replay Control Bar */}
          {replayActive && (
            <div className="p-3.5 bg-surface2/70 border-t border-line space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                {/* Playback Transport Buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      const prev = Math.max(0, replayStep - 1);
                      setReplayStep(prev);
                      const target = chronologicalEvents[prev];
                      if (target && mapInstanceRef.current) mapInstanceRef.current.panTo([target.lat, target.lon], { animate: true });
                    }}
                    disabled={replayStep <= 0}
                    className="size-9 rounded-xl border border-line bg-surface grid place-items-center text-ink hover:bg-surface2 disabled:opacity-40 transition cursor-pointer"
                    title="Previous event"
                  >
                    <SkipBack size={16} weight="bold" />
                  </button>

                  <button
                    onClick={() => setIsPlayingReplay(!isPlayingReplay)}
                    className="h-9 px-4 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs flex items-center gap-2 shadow-xs transition cursor-pointer"
                  >
                    {isPlayingReplay ? <Pause size={16} weight="fill" /> : <Play size={16} weight="fill" />}
                    <span>{isPlayingReplay ? "Pause" : "Play timeline"}</span>
                  </button>

                  <button
                    onClick={() => {
                      const next = Math.min(chronologicalEvents.length - 1, replayStep + 1);
                      setReplayStep(next);
                      const target = chronologicalEvents[next];
                      if (target && mapInstanceRef.current) mapInstanceRef.current.panTo([target.lat, target.lon], { animate: true });
                    }}
                    disabled={replayStep >= chronologicalEvents.length - 1}
                    className="size-9 rounded-xl border border-line bg-surface grid place-items-center text-ink hover:bg-surface2 disabled:opacity-40 transition cursor-pointer"
                    title="Next event"
                  >
                    <SkipForward size={16} weight="bold" />
                  </button>

                  {/* Speed Toggles */}
                  <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-line text-[11px] font-bold font-mono">
                    {[1, 2, 5].map((spd) => (
                      <button
                        key={spd}
                        onClick={() => setReplaySpeed(spd)}
                        className={cx(
                          "px-2 py-0.5 rounded-lg transition cursor-pointer",
                          replaySpeed === spd ? "bg-amber-500 text-white shadow-xs" : "text-muted hover:text-ink"
                        )}
                      >
                        {spd}x
                      </button>
                    ))}
                  </div>
                </div>

                {/* Event Status Ticker Summary */}
                {currentReplayPoint && (
                  <div className="flex items-center gap-3 text-xs font-mono">
                    <span className="text-muted">
                      {currentReplayPoint.received_at ? new Date(currentReplayPoint.received_at).toLocaleString() : `Event #${replayStep + 1}`}
                    </span>
                    <span className="font-bold text-ink truncate max-w-xs">
                      {currentReplayPoint.filename}
                    </span>
                    <span
                      className={cx(
                        "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                        currentReplayPoint.score < 50 ? "bg-rose-500/10 text-rose-600" : "bg-emerald-500/10 text-emerald-600"
                      )}
                    >
                      Score: {currentReplayPoint.score}/100
                    </span>
                  </div>
                )}
              </div>

              {/* Scrubber Progress Slider */}
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-bold text-amber-600 dark:text-amber-400 shrink-0">
                  Step {replayStep + 1} / {chronologicalEvents.length}
                </span>
                <input
                  type="range"
                  min="0"
                  max={Math.max(0, chronologicalEvents.length - 1)}
                  value={replayStep}
                  onChange={(e) => {
                    const step = Number(e.target.value);
                    setReplayStep(step);
                    const target = chronologicalEvents[step];
                    if (target && mapInstanceRef.current) mapInstanceRef.current.panTo([target.lat, target.lon], { animate: true });
                  }}
                  className="w-full h-2 bg-surface rounded-lg appearance-none cursor-pointer accent-amber-500"
                />
                <button
                  onClick={() => {
                    setReplayStep(0);
                    setIsPlayingReplay(false);
                    if (chronologicalEvents[0] && mapInstanceRef.current) mapInstanceRef.current.panTo([chronologicalEvents[0].lat, chronologicalEvents[0].lon], { animate: true });
                  }}
                  className="text-xs font-bold text-muted hover:text-ink shrink-0 underline cursor-pointer"
                >
                  Restart
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right 3 or 4 Cols: City Cluster Feed & Syndicate Proximity Inspector */}
        <div className="lg:col-span-4 xl:col-span-3 space-y-4">
          {/* Selected Evidence Inspector Card */}
          {selectedPoint ? (
            <Card className="card-bento p-4 space-y-3 border-accent/40 shadow-md">
              <div className="flex items-start justify-between gap-2 border-b border-line pb-2.5">
                <div>
                  <span className="rounded bg-accent/10 px-2 py-0.5 font-mono text-[10px] font-bold text-accent">
                    {selectedPoint.case_reference}
                  </span>
                  <h4 className="mt-1 text-xs font-bold text-ink truncate max-w-[200px]" title={selectedPoint.filename}>
                    {selectedPoint.filename}
                  </h4>
                  <div className="text-[11px] text-muted truncate max-w-[200px]">
                    {selectedPoint.location_name}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedPoint(null)}
                  className="size-6 grid place-items-center rounded-full text-muted hover:bg-surface2 hover:text-ink transition cursor-pointer"
                >
                  <X size={14} weight="bold" />
                </button>
              </div>

              {/* Coordinates and Score */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-xl bg-surface2/60 p-2">
                  <div className="text-[9.5px] uppercase font-bold text-muted">INTEGRITY</div>
                  <div className={cx(
                    "font-mono font-bold mt-0.5",
                    selectedPoint.score < 50 ? "text-rose-600" : "text-emerald-600"
                  )}>
                    {selectedPoint.score}/100 · {selectedPoint.verdict}
                  </div>
                </div>
                <div className="rounded-xl bg-surface2/60 p-2">
                  <div className="text-[9.5px] uppercase font-bold text-muted">COORDINATES</div>
                  <div className="font-mono text-[11px] font-bold text-ink mt-0.5">
                    {selectedPoint.lat.toFixed(4)}, {selectedPoint.lon.toFixed(4)}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-1 flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <Button
                    variant="primary"
                    onClick={() => nav(`/evidence/${selectedPoint.id}`)}
                    className="flex-1 btn-pill text-xs py-1.5"
                  >
                    <span>Open file</span>
                    <ArrowUpRight size={13} weight="bold" />
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      mapInstanceRef.current?.flyTo([selectedPoint.lat, selectedPoint.lon], 18, { duration: 1.0 });
                    }}
                    className="btn-pill text-xs py-1.5"
                    title="Zoom in to incident street level"
                  >
                    <span>Zoom in</span>
                    <Crosshair size={13} weight="bold" />
                  </Button>
                </div>
                {selectedPoint.media_type === "audio" && (
                  <Button
                    variant="secondary"
                    onClick={() => nav(`/audio-forensics?id=${selectedPoint.id}`)}
                    className="w-full btn-pill text-xs py-1.5 text-purple-600 border-purple-500/30 hover:bg-purple-50"
                  >
                    <SpeakerHigh size={13} weight="bold" />
                    <span>Open voice check</span>
                  </Button>
                )}
              </div>
            </Card>
          ) : null}

          {/* Proximity Alerts Syndicate Feed */}
          <Card className="card-bento p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Broadcast size={16} className="text-rose-600" weight="bold" />
                <h3 className="text-xs font-bold text-ink">
                  Nearby cases
                </h3>
              </div>
              <span className="rounded-full bg-rose-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-rose-600">
                {mapData?.proximity_alerts?.length ?? 0} ACTIVE
              </span>
            </div>

            <p className="text-[11px] text-muted leading-tight">
              Files from different cases that were recorded within 2.5 km of each other.
            </p>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {mapData?.proximity_alerts?.map((alert: any, idx: number) => (
                <div
                  key={idx}
                  onClick={() => {
                    setSelectedPoint(alert.source);
                    panToCity(alert.source.lat, alert.source.lon);
                  }}
                  className="rounded-xl border border-line/70 bg-surface2/40 hover:bg-surface2 p-2.5 space-y-1.5 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-[10px] font-bold text-accent">
                      {alert.source.case_reference} &harr; {alert.target.case_reference}
                    </span>
                    <span className="font-mono text-[10px] font-extrabold text-rose-600">
                      {alert.distance_meters}m
                    </span>
                  </div>
                  <div className="text-[11px] text-ink font-semibold truncate">
                    {alert.source.city}: {alert.source.location_name}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* City Cluster Overview */}
          <Card className="card-bento p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe size={16} className="text-accent" weight="bold" />
                <h3 className="text-xs font-bold text-ink">
                  Cities and places
                </h3>
              </div>
              <span className="text-xs font-bold text-muted">
                {mapData?.clusters?.length ?? 0} Cities
              </span>
            </div>

            <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
              {mapData?.clusters?.map((c: any) => (
                <div
                  key={c.city}
                  onClick={() => {
                    setSelectedCity(selectedCity === c.city ? "all" : c.city);
                    panToCity(c.lat, c.lon);
                  }}
                  className={cx(
                    "flex items-center justify-between rounded-xl px-2.5 py-1.5 text-xs transition cursor-pointer border",
                    selectedCity === c.city
                      ? "bg-accent/10 border-accent text-accent font-bold"
                      : "border-transparent bg-surface2/40 hover:bg-surface2 text-ink"
                  )}
                >
                  <span className="truncate">{c.city}</span>
                  <span className="font-mono text-[11px] text-muted">
                    {c.count} items · {c.avg_score}/100
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
