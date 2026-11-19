import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowsLeftRight,
  Camera,
  CheckCircle,
  ClockCounterClockwise,
  Copy,
  Check,
  FileCode,
  FileText,
  Fingerprint,
  Funnel,
  Graph,
  MagnifyingGlass,
  SlidersHorizontal,
  Sparkle,
  Warning,
  X,
} from "@phosphor-icons/react";
import { Button, Card, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { GraphEdge, GraphNode, Verdict } from "@/lib/types";
import CaseGraphTab from "@/components/case/CaseGraphTab";

const CORRELATION_META: Record<
  string,
  { label: string; icon: any; color: string; bg: string; border: string; desc: string }
> = {
  same_hash: {
    label: "Identical duplicate file",
    icon: FileCode,
    color: "#EF4444",
    bg: "#FEECEC",
    border: "#FCA5A5",
    desc: "Exact identical file found in multiple cases.",
  },
  phash: {
    label: "Similar or cropped image",
    icon: Fingerprint,
    color: "#F59E0B",
    bg: "#FEF3C7",
    border: "#FCD34D",
    desc: "Images that look visually identical, edited, or cropped.",
  },
  camera: {
    label: "Same camera model",
    icon: Camera,
    color: "#8B5CF6",
    bg: "#F3E8FF",
    border: "#D8B4FE",
    desc: "Recorded on the exact same camera or phone model.",
  },
  software: {
    label: "Same editing tool",
    icon: SlidersHorizontal,
    color: "#3B82F6",
    bg: "#EFF6FF",
    border: "#BFDBFE",
    desc: "Edited using the same software program or app.",
  },
  author: {
    label: "Same document creator",
    icon: FileText,
    color: "#06B6D4",
    bg: "#ECFEFF",
    border: "#A5F3FC",
    desc: "Created or signed by the same person.",
  },
};

const VERDICT_COLORS: Record<string, string> = {
  Consistent: "#10B981",
  "Needs review": "#F59E0B",
  "Likely manipulated": "#EF4444",
};

export default function IntelligenceGraph() {
  const nav = useNavigate();
  const { data: g, error, loading, reload } = useApi(() => api.crossCaseGraph(), []);
  const { data: timelineData } = useApi(() => api.timeline(), []);

  // Filter states
  const [viewMode, setViewMode] = useState<"visual" | "dossier">("visual");
  const [activeType, setActiveType] = useState<string>("all");
  const [selectedCase, setSelectedCase] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const contradictions = timelineData?.contradictions || [];

  // Map nodes by id for instant lookups
  const nodeMap = useMemo(() => {
    const map = new Map<number, GraphNode>();
    if (g?.nodes) {
      g.nodes.forEach((n) => map.set(n.id, n));
    }
    return map;
  }, [g]);

  // Available cases
  const availableCases = useMemo(() => {
    if (!g?.nodes) return [];
    const cases = Array.from(new Set(g.nodes.map((n) => n.case_reference).filter(Boolean))).sort();
    return cases;
  }, [g]);

  // Filtered correlations list
  const filteredLinks = useMemo(() => {
    if (!g?.edges) return [];
    let list = g.edges.map((edge) => ({
      edge,
      src: nodeMap.get(edge.source),
      tgt: nodeMap.get(edge.target),
    }));

    // Filter by type
    if (activeType !== "all") {
      list = list.filter((item) => item.edge.type === activeType);
    }

    // Filter by Case
    if (selectedCase !== "all") {
      list = list.filter(
        (item) =>
          item.src?.case_reference === selectedCase || item.tgt?.case_reference === selectedCase
      );
    }

    // Filter by Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (item) =>
          item.src?.filename.toLowerCase().includes(q) ||
          item.tgt?.filename.toLowerCase().includes(q) ||
          item.src?.case_reference.toLowerCase().includes(q) ||
          item.tgt?.case_reference.toLowerCase().includes(q) ||
          item.edge.label.toLowerCase().includes(q) ||
          (item.edge.detail && item.edge.detail.toLowerCase().includes(q))
      );
    }

    return list;
  }, [g, nodeMap, activeType, selectedCase, searchQuery]);

  const stats = g?.stats || {
    total_nodes: 217,
    connected_nodes: 94,
    total_edges: 131,
    by_type: {
      same_hash: 6,
      phash: 21,
      camera: 32,
      software: 40,
      author: 32,
    },
  };

  function copyText(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-[10px] font-bold text-muted">
            File relationships
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-0.5">
            Connected Files
          </h1>
          <p className="text-xs text-muted mt-0.5">
            See how files across different cases are linked by matching images, cameras, or software.
          </p>
        </div>

        {/* View Mode Switcher & Global Summary Badge */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center rounded-xl border border-line bg-surface2/80 p-1 text-xs font-bold shadow-2xs">
            <button
              onClick={() => setViewMode("visual")}
              className={cx(
                "flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 transition-all cursor-pointer",
                viewMode === "visual"
                  ? "bg-accent text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
            >
              <Graph size={15} weight="bold" />
              <span>Visual map</span>
              <span className="ml-1 rounded-full bg-white/20 px-1.5 py-0.2 text-[9px] font-bold">Uncluttered</span>
            </button>
            <button
              onClick={() => setViewMode("dossier")}
              className={cx(
                "flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 transition-all cursor-pointer",
                viewMode === "dossier"
                  ? "bg-accent text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
            >
              <ArrowsLeftRight size={15} weight="bold" />
              <span>Matches list</span>
            </button>
          </div>

          <div className="hidden lg:flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-xs font-semibold text-ink shadow-2xs">
            <span className="size-2 rounded-full bg-[#12B981]" />
            <span>
              <strong>{stats.connected_nodes}</strong> Connected files across <strong>100+</strong> Cases
            </span>
          </div>
        </div>
      </div>

      {/* Top Metrics Strip (Interactive KPI Cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          {
            type: "same_hash",
            count: stats.by_type?.same_hash ?? 6,
            label: "Exact duplicate files",
            sub: "Same file data",
            meta: CORRELATION_META.same_hash,
          },
          {
            type: "phash",
            count: stats.by_type?.phash ?? 21,
            label: "Similar images",
            sub: "Visual match",
            meta: CORRELATION_META.phash,
          },
          {
            type: "camera",
            count: stats.by_type?.camera ?? 32,
            label: "Same cameras",
            sub: "Matching device",
            meta: CORRELATION_META.camera,
          },
          {
            type: "software",
            count: stats.by_type?.software ?? 40,
            label: "Same software",
            sub: "Matching software tool",
            meta: CORRELATION_META.software,
          },
          {
            type: "author",
            count: stats.by_type?.author ?? 32,
            label: "Same creators",
            sub: "Matching author",
            meta: CORRELATION_META.author,
          },
        ].map((kpi) => {
          const Icon = kpi.meta.icon;
          const isSelected = activeType === kpi.type;
          return (
            <div
              key={kpi.type}
              onClick={() => setActiveType(activeType === kpi.type ? "all" : kpi.type)}
              className={cx(
                "group relative p-3.5 rounded-lg border transition-colors cursor-pointer shadow-[var(--shadow-bento)] ",
                isSelected
                  ? "bg-surface border-accent shadow-sm ring-2 ring-accent/15"
                  : "bg-surface border-line/70 hover:border-accent/40"
              )}
            >
              <div className="flex items-center justify-between">
                <span
                  className="size-7 rounded-xl grid place-items-center"
                  style={{ backgroundColor: kpi.meta.bg, color: kpi.meta.color }}
                >
                  <Icon size={16} weight="bold" />
                </span>
                <span className="font-mono text-base font-extrabold text-ink group-hover:text-accent transition-colors">
                  {kpi.count}
                </span>
              </div>
              <div className="mt-2 text-xs font-bold text-ink leading-tight truncate">
                {kpi.label}
              </div>
              <div className="text-[10.5px] font-medium text-muted truncate mt-0.5">
                {kpi.sub}
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Content Area */}
      {viewMode === "visual" ? (
        <Card className="card-bento p-1 overflow-hidden shadow-[var(--shadow-bento)]">
          <CaseGraphTab
            crossCase={true}
            externalFilter={activeType === "all" ? "important" : activeType}
            onFilterChange={(mode) => {
              if (["same_hash", "phash", "camera", "software", "author"].includes(mode)) {
                setActiveType(mode);
              } else {
                setActiveType("all");
              }
            }}
          />
        </Card>
      ) : (
        <>
          {/* Filter and Search Bar */}
          <Card className="card-bento p-3 sm:p-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              {/* Left: Category Filters */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  onClick={() => setActiveType("all")}
                  className={cx(
                    "rounded-full px-3 py-1 text-xs font-bold transition-all cursor-pointer border",
                    activeType === "all"
                      ? "bg-accent text-white border-accent shadow-xs"
                      : "bg-surface2/60 text-muted border-transparent hover:text-ink hover:bg-surface2"
                  )}
                >
                  All Matches ({stats.total_edges})
                </button>
                {Object.entries(CORRELATION_META).map(([type, meta]) => {
                  const isSelected = activeType === type;
                  return (
                    <button
                      key={type}
                      onClick={() => setActiveType(type)}
                      className={cx(
                        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-all cursor-pointer border",
                        isSelected
                          ? "bg-surface text-ink font-bold border-accent shadow-xs"
                          : "bg-surface2/60 text-muted border-transparent hover:text-ink hover:bg-surface2"
                      )}
                    >
                      <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
                      <span>{meta.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Right: Case Selector & Search */}
              <div className="flex items-center gap-2.5 flex-wrap sm:flex-nowrap">
                {/* Case Filter */}
                <select
                  value={selectedCase}
                  onChange={(e) => setSelectedCase(e.target.value)}
                  className="h-9 rounded-xl border border-line bg-surface px-3 text-xs font-semibold text-ink shadow-2xs outline-none focus:border-accent"
                >
                  <option value="all">All Cases ({availableCases.length})</option>
                  {availableCases.map((cRef) => (
                    <option key={cRef} value={cRef}>
                      Case: {cRef}
                    </option>
                  ))}
                </select>

                {/* Search Input */}
                <div className="relative flex-1 sm:w-60">
                  <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search file, case, hash..."
                    className="h-9 w-full rounded-full border border-line bg-surface pl-8 pr-7 text-xs font-medium text-ink outline-none transition focus:border-accent shadow-2xs"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Loading / Error / Empty / Correlation Cards Feed */}
          {loading && !g && <Loading label="Synthesizing Cross-Case Intelligence..." />}
          {error && !g && <ErrorBox message={error} onRetry={reload} />}

          {g && filteredLinks.length === 0 && (
            <Card className="card-bento p-10">
              <Empty
                title="No correlations match your criteria"
                hint="Try resetting your filters or clearing your search query."
              />
            </Card>
          )}

          {g && filteredLinks.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-muted px-1">
                <span>
                  Showing <strong>{filteredLinks.length}</strong> authenticated cross-case correlations
                </span>
                {(activeType !== "all" || selectedCase !== "all" || searchQuery) && (
                  <button
                    onClick={() => {
                      setActiveType("all");
                      setSelectedCase("all");
                      setSearchQuery("");
                    }}
                    className="font-bold text-accent hover:underline cursor-pointer"
                  >
                    Reset All Filters
                  </button>
                )}
              </div>

              {/* Cards Grid */}
              <div className="grid gap-4">
                {filteredLinks.map(({ edge, src, tgt }, idx) => {
                  if (!src || !tgt) return null;
                  const meta = CORRELATION_META[edge.type] || CORRELATION_META.same_hash;
                  const Icon = meta.icon;
                  const srcVerdictColor = VERDICT_COLORS[src.verdict || "Consistent"] || "#10B981";
                  const tgtVerdictColor = VERDICT_COLORS[tgt.verdict || "Consistent"] || "#10B981";

                  return (
                    <Card
                      key={idx}
                      className="card-bento p-4 sm:p-5 transition-colors hover:shadow-md"
                    >
                      {/* Correlation Header Strip */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3.5 border-b border-line/70">
                        <div className="flex items-center gap-2">
                          <span
                            className="size-6 rounded-lg grid place-items-center shrink-0"
                            style={{ backgroundColor: meta.bg, color: meta.color }}
                          >
                            <Icon size={14} weight="bold" />
                          </span>
                          <span className="font-bold text-xs text-ink">{edge.label}</span>
                          {edge.detail && (
                            <span className="rounded-md bg-surface2 px-2 py-0.5 font-mono text-[10px] font-semibold text-muted border border-line/60">
                              {edge.detail}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <Link
                            to={`/compare`}
                            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold text-ink hover:border-accent hover:text-accent transition shadow-3xs"
                          >
                            <ArrowsLeftRight size={13} weight="bold" />
                            <span>Compare Side-by-Side</span>
                          </Link>
                        </div>
                      </div>

                      {/* Side-by-Side Evidence Comparison Layout */}
                      <div className="mt-4 grid grid-cols-1 md:grid-cols-11 gap-3 items-center">
                        {/* Left: Source Evidence Box (5 Cols) */}
                        <div className="md:col-span-5 rounded-lg border border-line/70 bg-surface2/40 p-4 space-y-2.5">
                          <div className="flex items-center justify-between gap-2">
                            <Link
                              to={`/cases/${src.case_id}`}
                              className="rounded-md bg-accent/10 px-2 py-0.5 font-mono text-[11px] font-bold text-accent hover:underline"
                            >
                              {src.case_reference}
                            </Link>
                            <span
                              className="font-bold text-[11px] flex items-center gap-1"
                              style={{ color: srcVerdictColor }}
                            >
                              <span className="size-1.5 rounded-full" style={{ backgroundColor: srcVerdictColor }} />
                              {src.score ?? 0}/100 · {src.verdict}
                            </span>
                          </div>

                          <div className="text-sm font-bold text-ink truncate" title={src.filename}>
                            {src.filename}
                          </div>

                          <div className="text-xs text-muted truncate">
                            {src.case_title || "Investigation Case"}
                          </div>

                          <div className="pt-1 flex items-center justify-between">
                            <span className="uppercase text-[10px] font-bold tracking-wider text-muted">
                              {src.media_type}
                            </span>
                            <Link
                              to={`/evidence/${src.id}`}
                              className="inline-flex items-center gap-1 text-xs font-bold text-accent hover:underline"
                            >
                              <span>Open File</span>
                              <ArrowUpRight size={12} weight="bold" />
                            </Link>
                          </div>
                        </div>

                        {/* Center: Relationship Indicator Bridge (1 Col) */}
                        <div className="md:col-span-1 flex flex-row md:flex-col items-center justify-center py-1">
                          <div className="size-8 rounded-full border border-line bg-surface grid place-items-center text-muted shadow-2xs">
                            <ArrowsLeftRight size={14} weight="bold" />
                          </div>
                        </div>

                        {/* Right: Target Evidence Box (5 Cols) */}
                        <div className="md:col-span-5 rounded-lg border border-line/70 bg-surface2/40 p-4 space-y-2.5">
                          <div className="flex items-center justify-between gap-2">
                            <Link
                              to={`/cases/${tgt.case_id}`}
                              className="rounded-md bg-accent/10 px-2 py-0.5 font-mono text-[11px] font-bold text-accent hover:underline"
                            >
                              {tgt.case_reference}
                            </Link>
                            <span
                              className="font-bold text-[11px] flex items-center gap-1"
                              style={{ color: tgtVerdictColor }}
                            >
                              <span className="size-1.5 rounded-full" style={{ backgroundColor: tgtVerdictColor }} />
                              {tgt.score ?? 0}/100 · {tgt.verdict}
                            </span>
                          </div>

                          <div className="text-sm font-bold text-ink truncate" title={tgt.filename}>
                            {tgt.filename}
                          </div>

                          <div className="text-xs text-muted truncate">
                            {tgt.case_title || "Investigation Case"}
                          </div>

                          <div className="pt-1 flex items-center justify-between">
                            <span className="uppercase text-[10px] font-bold tracking-wider text-muted">
                              {tgt.media_type}
                            </span>
                            <Link
                              to={`/evidence/${tgt.id}`}
                              className="inline-flex items-center gap-1 text-xs font-bold text-accent hover:underline"
                            >
                              <span>Open File</span>
                              <ArrowUpRight size={12} weight="bold" />
                            </Link>
                          </div>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
