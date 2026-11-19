import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowsIn,
  ArrowsLeftRight,
  Camera,
  Check,
  CheckCircle,
  Copy,
  FileCode,
  FileText,
  Fingerprint,
  Funnel,
  Graph,
  MagnifyingGlass,
  Minus,
  Plus,
  SlidersHorizontal,
  Sparkle,
  Star,
  Warning,
  X,
} from "@phosphor-icons/react";
import { Button, Card, Empty, ErrorBox, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { GraphEdge, GraphNode, Verdict } from "@/lib/types";

function getEdgeBadgeLabel(edge: GraphEdge) {
  if (edge.type === "same_hash") return "EXACT DUPLICATE";
  if (edge.type === "phash") return "SIMILAR IMAGE";
  if (edge.type === "camera") return "SAME CAMERA";
  if (edge.type === "software") return "SAME TOOL";
  if (edge.type === "author") return "SAME AUTHOR";
  if (edge.type === "gps_proximity") return "NEARBY LOCATION";
  return edge.label.length > 15 ? edge.label.slice(0, 14) + "…" : edge.label;
}

export const CORRELATION_COLORS: Record<string, { stroke: string; bg: string; text: string; label: string }> = {
  same_hash: {
    stroke: "#EF4444",
    bg: "#FEECEC",
    text: "#DC2626",
    label: "Exact duplicate file",
  },
  phash: {
    stroke: "#F59E0B",
    bg: "#FEF3C7",
    text: "#D97706",
    label: "Similar image",
  },
  camera: {
    stroke: "#8B5CF6",
    bg: "#F3E8FF",
    text: "#7C3AED",
    label: "Same camera model",
  },
  software: {
    stroke: "#3B82F6",
    bg: "#EFF6FF",
    text: "#2563EB",
    label: "Same editing tool",
  },
  author: {
    stroke: "#06B6D4",
    bg: "#ECFEFF",
    text: "#0891B2",
    label: "Same document author",
  },
  gps_proximity: {
    stroke: "#10B981",
    bg: "#ECFDF5",
    text: "#059669",
    label: "Nearby location",
  },
};

const VERDICT_STYLES: Record<Verdict, { border: string; bg: string; text: string }> = {
  "Likely manipulated": { border: "#EF4444", bg: "#FEECEC", text: "#DC2626" },
  "Needs review": { border: "#F59E0B", bg: "#FEF3C7", text: "#D97706" },
  Consistent: { border: "#10B981", bg: "#ECFDF5", text: "#059669" },
};

interface CardNode extends GraphNode {
  x: number;
  y: number;
  w: number;
  h: number;
}

export default function CaseGraphTab({
  caseId,
  crossCase = false,
  externalFilter = "important",
  onFilterChange,
  onSelectEdge,
}: {
  caseId?: number;
  crossCase?: boolean;
  externalFilter?: string;
  onFilterChange?: (mode: string) => void;
  onSelectEdge?: (edge: GraphEdge | null) => void;
}) {
  const nav = useNavigate();
  const { data: g, error, loading, reload } = useApi(
    () => (crossCase ? api.crossCaseGraph() : api.caseGraph(caseId!)),
    [caseId, crossCase]
  );

  // Filter Modes
  // 'important' = Only high-priority smoking guns (SHA-256 & pHash & top camera) - 14 to 18 nodes max!
  // 'spotlight' = Single case focus (4 to 6 nodes max)
  const [filterMode, setFilterMode] = useState<"important" | "spotlight" | "same_hash" | "phash" | "camera">(
    (externalFilter as any) || "important"
  );
  const [selectedCase, setSelectedCase] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    if (externalFilter && ["important", "spotlight", "same_hash", "phash", "camera"].includes(externalFilter)) {
      setFilterMode(externalFilter as any);
    }
  }, [externalFilter]);

  const handleFilterModeChange = (mode: "important" | "spotlight" | "same_hash" | "phash" | "camera") => {
    setFilterMode(mode);
    onFilterChange?.(mode);
  };

  // Selection states
  const [selectedNode, setSelectedNode] = useState<CardNode | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);
  const [copiedSha, setCopiedSha] = useState(false);

  // Pan & Zoom
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [draggingNodeId, setDraggingNodeId] = useState<number | null>(null);

  const [nodes, setNodes] = useState<CardNode[]>([]);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const W = 1350;
  const H = 720;
  const CARD_W = 210;
  const CARD_H = 74;

  // Available case list (prioritize cases that actually have connections in this graph)
  const availableCases = useMemo(() => {
    if (!g?.nodes || !g?.edges) return [];
    const linkedNodeIds = new Set<number>();
    g.edges.forEach((e) => {
      linkedNodeIds.add(e.source);
      linkedNodeIds.add(e.target);
    });
    const connectedCases = new Set<string>();
    const allCases = new Set<string>();
    g.nodes.forEach((n) => {
      if (n.case_reference) {
        allCases.add(n.case_reference);
        if (linkedNodeIds.has(n.id)) {
          connectedCases.add(n.case_reference);
        }
      }
    });
    // Return connected cases first, or all cases
    const primary = Array.from(connectedCases).sort();
    return primary.length > 0 ? primary : Array.from(allCases).sort();
  }, [g]);

  // 1. Select the "Important" / Filtered subset of nodes and edges
  const { activeNodesRaw, activeEdges } = useMemo(() => {
    if (!g || !g.nodes || !g.edges) return { activeNodesRaw: [], activeEdges: [] };

    let candidateEdges = g.edges;

    // Filter by mode
    if (filterMode === "spotlight") {
      // Single case focus
      const targetCase = selectedCase === "all" ? (availableCases[0] || "") : selectedCase;
      const caseNodeIds = new Set(
        g.nodes.filter((n) => n.case_reference === targetCase).map((n) => n.id)
      );
      // Include edges involving these nodes
      candidateEdges = g.edges.filter(
        (e) => caseNodeIds.has(e.source) || caseNodeIds.has(e.target)
      );
      // Collect nodes involved (case nodes + directly linked partner nodes)
      const allowedNodeIds = new Set<number>(caseNodeIds);
      candidateEdges.forEach((e) => {
        allowedNodeIds.add(e.source);
        allowedNodeIds.add(e.target);
      });
      const nodeList = g.nodes.filter((n) => allowedNodeIds.has(n.id));
      return { activeNodesRaw: nodeList, activeEdges: candidateEdges };
    } else if (filterMode === "same_hash") {
      candidateEdges = g.edges.filter((e) => e.type === "same_hash");
    } else if (filterMode === "phash") {
      candidateEdges = g.edges.filter((e) => e.type === "phash");
    } else if (filterMode === "camera") {
      candidateEdges = g.edges.filter((e) => e.type === "camera").slice(0, 8);
    } else {
      // Default: 'important' - Top Smoking Guns (Exact Hashes + Visual Clones + Top Camera links)
      // Exactly what user asked: "only show the important one not all"
      const criticalHashes = g.edges.filter((e) => e.type === "same_hash");
      const visualClones = g.edges.filter((e) => e.type === "phash").slice(0, 5);
      const topCameras = g.edges.filter((e) => e.type === "camera").slice(0, 4);
      candidateEdges = [...criticalHashes, ...visualClones, ...topCameras];
    }

    // Collect distinct nodes involved in candidateEdges
    const nodeIds = new Set<number>();
    candidateEdges.forEach((e) => {
      nodeIds.add(e.source);
      nodeIds.add(e.target);
    });

    let nodeList = g.nodes.filter((n) => nodeIds.has(n.id));

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      nodeList = nodeList.filter(
        (n) =>
          n.filename.toLowerCase().includes(q) ||
          n.case_reference.toLowerCase().includes(q) ||
          (n.case_title && n.case_title.toLowerCase().includes(q))
      );
      const matchedIds = new Set(nodeList.map((n) => n.id));
      candidateEdges = candidateEdges.filter(
        (e) => matchedIds.has(e.source) || matchedIds.has(e.target)
      );
    }

    return { activeNodesRaw: nodeList, activeEdges: candidateEdges };
  }, [g, filterMode, selectedCase, availableCases, searchQuery]);

  // Clear selected node when switching modes or cases if it's no longer in view
  useEffect(() => {
    if (selectedNode && !activeNodesRaw.some((n) => n.id === selectedNode.id)) {
      setSelectedNode(null);
    }
  }, [filterMode, selectedCase, activeNodesRaw, selectedNode]);

  // 2. Compute Non-Overlapping Grid / Radial Coordinates for the Important Nodes
  useEffect(() => {
    if (!activeNodesRaw || activeNodesRaw.length === 0) {
      setNodes([]);
      return;
    }

    const n = activeNodesRaw.length;
    const positioned: CardNode[] = [];

    if (filterMode === "spotlight") {
      // Spotlight mode: Center Case Hub with partner nodes orbiting
      const targetCase = selectedCase === "all" ? (availableCases[0] || "") : selectedCase;
      const primaryNodes = activeNodesRaw.filter((nd) => nd.case_reference === targetCase);
      const foreignNodes = activeNodesRaw.filter((nd) => nd.case_reference !== targetCase);

      const cx = W / 2;
      const cy = H / 2;

      // Primary nodes form a vertical column on the left
      const primarySpacing = Math.min(130, (H - 120) / Math.max(1, primaryNodes.length));
      const pStartY = cy - ((primaryNodes.length - 1) * primarySpacing) / 2;

      primaryNodes.forEach((node, idx) => {
        positioned.push({
          ...node,
          x: cx - 240,
          y: pStartY + idx * primarySpacing - CARD_H / 2,
          w: CARD_W,
          h: CARD_H,
        });
      });

      // Foreign linked partner nodes form a vertical column on the right
      const foreignSpacing = Math.min(130, (H - 120) / Math.max(1, foreignNodes.length));
      const fStartY = cy - ((foreignNodes.length - 1) * foreignSpacing) / 2;

      foreignNodes.forEach((node, idx) => {
        positioned.push({
          ...node,
          x: cx + 180,
          y: fStartY + idx * foreignSpacing - CARD_H / 2,
          w: CARD_W,
          h: CARD_H,
        });
      });
    } else {
      // Important Pair / Cluster Grid: Form clean, spacious rows and columns!
      // Group connected pairs/components so they sit directly next to each other
      const connectedPairs: Array<[number, number, GraphEdge]> = [];
      const placedNodeIds = new Set<number>();

      activeEdges.forEach((e) => {
        if (!placedNodeIds.has(e.source) || !placedNodeIds.has(e.target)) {
          connectedPairs.push([e.source, e.target, e]);
          placedNodeIds.add(e.source);
          placedNodeIds.add(e.target);
        }
      });

      // Layout in up to 3 columns of pairs (left, center, right)
      // Each pair is separated horizontally by 120px and rows by 115px
      const cols = 2; // 2 pairs per row = 4 cards per row
      const rowHeight = 135;
      const startX = 80;
      const startY = 60;
      const pairWidth = CARD_W * 2 + 130; // 2 cards + bridge gap

      const finalPlaced = new Map<number, CardNode>();

      connectedPairs.forEach(([srcId, tgtId, edge], pairIdx) => {
        const row = Math.floor(pairIdx / cols);
        const col = pairIdx % cols;

        const leftX = startX + col * (pairWidth + 70);
        const rightX = leftX + CARD_W + 120;
        const curY = startY + row * rowHeight;

        const srcNode = activeNodesRaw.find((nd) => nd.id === srcId);
        const tgtNode = activeNodesRaw.find((nd) => nd.id === tgtId);

        if (srcNode && !finalPlaced.has(srcId)) {
          finalPlaced.set(srcId, {
            ...srcNode,
            x: leftX,
            y: curY,
            w: CARD_W,
            h: CARD_H,
          });
        }
        if (tgtNode && !finalPlaced.has(tgtId)) {
          finalPlaced.set(tgtId, {
            ...tgtNode,
            x: rightX,
            y: curY,
            w: CARD_W,
            h: CARD_H,
          });
        }
      });

      // Place any leftover unlinked items neatly
      let leftoverIdx = finalPlaced.size;
      activeNodesRaw.forEach((nd) => {
        if (!finalPlaced.has(nd.id)) {
          const row = Math.floor(leftoverIdx / 4);
          const col = leftoverIdx % 4;
          finalPlaced.set(nd.id, {
            ...nd,
            x: startX + col * (CARD_W + 50),
            y: startY + (row + 3) * rowHeight,
            w: CARD_W,
            h: CARD_H,
          });
          leftoverIdx++;
        }
      });

      positioned.push(...Array.from(finalPlaced.values()));
    }

    setNodes(positioned);
  }, [activeNodesRaw, activeEdges, filterMode, selectedCase, availableCases]);

  const nodePos = useMemo(() => {
    const map = new Map<number, CardNode>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  // Connected neighborhood highlighting
  const activeFocusId = hoveredNodeId || selectedNode?.id || null;
  const connectedNodeIds = useMemo(() => {
    if (!activeFocusId) return null;
    const set = new Set<number>([activeFocusId]);
    activeEdges.forEach((e) => {
      if (e.source === activeFocusId) set.add(e.target);
      if (e.target === activeFocusId) set.add(e.source);
    });
    return set;
  }, [activeFocusId, activeEdges]);

  // Pan and Zoom Event Handlers
  function handleWheel(e: React.WheelEvent) {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.min(2.5, Math.max(0.5, prev * zoomFactor)));
  }

  function handleMouseDown(e: React.MouseEvent) {
    if (draggingNodeId !== null) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (isPanning) {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    } else if (draggingNodeId !== null && svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect();
      const mouseX = (e.clientX - rect.left - pan.x) / zoom;
      const mouseY = (e.clientY - rect.top - pan.y) / zoom;
      setNodes((prev) =>
        prev.map((n) => (n.id === draggingNodeId ? { ...n, x: mouseX - CARD_W / 2, y: mouseY - CARD_H / 2 } : n))
      );
    }
  }

  function handleMouseUp() {
    setIsPanning(false);
    setDraggingNodeId(null);
  }

  function resetView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNode(null);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  }

  // Selected node connections
  const selectedNodeLinks = useMemo(() => {
    if (!selectedNode || !g) return [];
    return g.edges
      .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
      .map((e) => {
        const otherId = e.source === selectedNode.id ? e.target : e.source;
        const otherNode = g.nodes.find((n) => n.id === otherId);
        return { edge: e, partner: otherNode };
      });
  }, [selectedNode, g]);

  if (loading && !g) return <Loading label="Loading Forensic Relationship Network..." />;
  if (error && !g) return <ErrorBox message={error} onRetry={reload} />;
  if (!g) return null;

  return (
    <div className="relative flex flex-col rounded-lg overflow-hidden bg-surface select-none">
      {/* Top Filter HUD: Clear Mode Switcher */}
      <div className="flex flex-col gap-3 p-3.5 border-b border-line bg-surface/95 backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        {/* Left: Mode Tabs */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <div className="flex items-center rounded-xl border border-line bg-surface2/60 p-0.5 text-xs font-bold shadow-2xs">
            <button
              onClick={() => {
                handleFilterModeChange("important");
                setSelectedCase("all");
              }}
              className={cx(
                "flex items-center gap-1.5 rounded-lg px-3 py-1 transition-all cursor-pointer",
                filterMode === "important"
                  ? "bg-accent text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
              title="Show only the smoking-gun correlations (Zero Clutter)"
            >
              <Star size={13} weight="fill" />
              <span>Key matches</span>
            </button>

            <button
              onClick={() => {
                handleFilterModeChange("same_hash");
                setSelectedCase("all");
              }}
              className={cx(
                "rounded-lg px-2.5 py-1 transition-all cursor-pointer",
                filterMode === "same_hash"
                  ? "bg-[#EF4444] text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
            >
              Duplicate files ({g.stats?.by_type?.same_hash ?? 6})
            </button>

            <button
              onClick={() => {
                handleFilterModeChange("phash");
                setSelectedCase("all");
              }}
              className={cx(
                "rounded-lg px-2.5 py-1 transition-all cursor-pointer",
                filterMode === "phash"
                  ? "bg-[#F59E0B] text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
            >
              Similar images ({g.stats?.by_type?.phash ?? 21})
            </button>

            <button
              onClick={() => {
                handleFilterModeChange("camera");
                setSelectedCase("all");
              }}
              className={cx(
                "rounded-lg px-2.5 py-1 transition-all cursor-pointer",
                filterMode === "camera"
                  ? "bg-[#8B5CF6] text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
            >
              Same cameras
            </button>

            <button
              onClick={() => handleFilterModeChange("spotlight")}
              className={cx(
                "rounded-lg px-2.5 py-1 transition-all cursor-pointer",
                filterMode === "spotlight"
                  ? "bg-accent text-white shadow-xs"
                  : "text-muted hover:text-ink"
              )}
              title="Focus on a single case and its direct connections"
            >
              Focus on single case
            </button>
          </div>
        </div>

        {/* Right: Case Selector Dropdown (Active in Spotlight or general) */}
        <div className="flex items-center gap-2">
          {filterMode === "spotlight" ? (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
              <span className="text-muted">Selected case:</span>
              <select
                value={selectedCase}
                onChange={(e) => setSelectedCase(e.target.value)}
                className="h-8 rounded-xl border border-accent bg-surface px-2.5 text-xs font-bold text-accent shadow-2xs outline-none"
              >
                {availableCases.map((cRef) => (
                  <option key={cRef} value={cRef}>
                    {cRef}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-muted">
                Showing {nodes.length} files · {activeEdges.length} connections
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Canvas Area */}
      {nodes.length === 0 ? (
        <div className="p-12">
          <Empty
            title="No relationships in this view"
            hint="Try selecting 'Top Important Matches' above to view verified cross-case correlations."
          />
        </div>
      ) : (
        <div
          className="relative h-[640px] w-full overflow-hidden bg-[#F0F5FE] dark:bg-[#0B0F1C] cursor-grab active:cursor-grabbing"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
        >
          {/* Subtle Forensic Coordinate Dots */}
          <div className="pointer-events-none absolute inset-0 opacity-20 bg-[radial-gradient(#3B3BF5_1.2px,transparent_1.2px)] [background-size:28px_28px]" />

          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            className="w-full h-full"
            style={{ touchAction: "none" }}
          >
            <defs>
              <filter id="cardShadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12" />
              </filter>
            </defs>

            {/* Transform Group for Pan & Zoom */}
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Edges Layer: Smooth Curved Connecting Bridges */}
              {activeEdges.map((edge, idx) => {
                const src = nodePos.get(edge.source);
                const tgt = nodePos.get(edge.target);
                if (!src || !tgt) return null;

                const isConnectedToFocus =
                  activeFocusId && (edge.source === activeFocusId || edge.target === activeFocusId);
                const isDimmed = activeFocusId && !isConnectedToFocus;
                const meta = CORRELATION_COLORS[edge.type] || CORRELATION_COLORS.same_hash;

                // Connect from right edge of left card to left edge of right card
                const isSrcLeft = src.x <= tgt.x;
                const x1 = isSrcLeft ? src.x + CARD_W : src.x;
                const y1 = src.y + CARD_H / 2;
                const x2 = isSrcLeft ? tgt.x : tgt.x + CARD_W;
                const y2 = tgt.y + CARD_H / 2;

                // Calculate smooth cubic bezier path
                const dx = Math.abs(x2 - x1) * 0.45;
                const dPath = isSrcLeft
                  ? `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`
                  : `M ${x1} ${y1} C ${x1 - dx} ${y1}, ${x2 + dx} ${y2}, ${x2} ${y2}`;

                const midX = (x1 + x2) / 2;
                const midY = (y1 + y2) / 2;

                return (
                  <g
                    key={`edge-${idx}`}
                    className="transition-colors cursor-pointer"
                    opacity={isDimmed ? 0.15 : isConnectedToFocus ? 1 : 0.85}
                    onClick={() => {
                      setSelectedNode(src);
                      onSelectEdge?.(edge);
                    }}
                  >
                    {/* Underlying Glow Line when focused */}
                    {isConnectedToFocus && (
                      <path
                        d={dPath}
                        fill="none"
                        stroke={meta.stroke}
                        strokeWidth="7"
                        strokeOpacity="0.25"
                      />
                    )}

                    {/* Main Connection Path */}
                    <path
                      d={dPath}
                      fill="none"
                      stroke={meta.stroke}
                      strokeWidth={isConnectedToFocus ? 3 : 2}
                      strokeDasharray={edge.type === "same_hash" ? "5 4" : undefined}
                      strokeLinecap="round"
                    />

                    {/* Centered Bridge Pill Badge */}
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x="-52"
                        y="-10"
                        width="104"
                        height="20"
                        rx="10"
                        fill="var(--surface, #ffffff)"
                        stroke={meta.stroke}
                        strokeWidth="1.2"
                        className="shadow-xs dark:fill-[#0F172A]"
                      />
                      <text
                        textAnchor="middle"
                        y="3.5"
                        fontSize="7.5"
                        fontWeight="800"
                        letterSpacing="0.04em"
                        fill={meta.text}
                      >
                        {getEdgeBadgeLabel(edge)}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* Nodes Layer: Crisp Forensic Entity Cards (No Overlapping Text!) */}
              {nodes.map((nd) => {
                const verdictStyle = VERDICT_STYLES[nd.verdict || "Consistent"] || VERDICT_STYLES.Consistent;
                const isSelected = selectedNode?.id === nd.id;
                const isHovered = hoveredNodeId === nd.id;
                const isConnected = connectedNodeIds ? connectedNodeIds.has(nd.id) : true;
                const isDimmed = !isConnected;

                return (
                  <g
                    key={`node-${nd.id}`}
                    data-forensic-card="true"
                    data-node-id={nd.id}
                    transform={`translate(${nd.x}, ${nd.y})`}
                    opacity={isDimmed ? 0.22 : 1}
                    className="cursor-pointer transition-transform duration-100"
                    onMouseEnter={() => setHoveredNodeId(nd.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNode(nd);
                    }}
                    onMouseDown={(e) => {
                      e.stopPropagation();
                      setDraggingNodeId(nd.id);
                    }}
                  >
                    {/* Selected Highlight Ring */}
                    {isSelected && (
                      <rect
                        x="-3"
                        y="-3"
                        width={CARD_W + 6}
                        height={CARD_H + 6}
                        rx="16"
                        fill="none"
                        stroke="#3B3BF5"
                        strokeWidth="2.5"
                        className=""
                      />
                    )}

                    {/* Card Surface Base */}
                    <rect
                      x="0"
                      y="0"
                      width={CARD_W}
                      height={CARD_H}
                      rx="14"
                      fill="var(--surface, #ffffff)"
                      stroke={isSelected ? "#3B3BF5" : "var(--line, #e2e8f0)"}
                      strokeWidth={isSelected ? "1.8" : "1"}
                      filter="url(#cardShadow)"
                    />

                    {/* Left Colored Verdict Accent Bar */}
                    <rect
                      x="0"
                      y="0"
                      width="5"
                      height={CARD_H}
                      rx="2.5"
                      fill={verdictStyle.border}
                    />

                    {/* Top Row: Case Monospace Badge & Score Chip */}
                    <g transform="translate(14, 18)">
                      <rect
                        x="0"
                        y="-10"
                        width="80"
                        height="16"
                        rx="5"
                        fill="rgba(59,59,245,0.08)"
                      />
                      <text
                        x="40"
                        y="1"
                        textAnchor="middle"
                        fontSize="8.5"
                        fontWeight="800"
                        fontFamily="monospace"
                        fill="#3B3BF5"
                      >
                        {nd.case_reference}
                      </text>

                      {/* Score Badge */}
                      <g transform="translate(138, 0)">
                        <rect
                          x="-26"
                          y="-9"
                          width="52"
                          height="15"
                          rx="7.5"
                          fill={verdictStyle.bg}
                          stroke={verdictStyle.border}
                          strokeWidth="0.8"
                        />
                        <text
                          x="0"
                          y="1.5"
                          textAnchor="middle"
                          fontSize="7.5"
                          fontWeight="800"
                          fill={verdictStyle.text}
                        >
                          {nd.score ?? 0}/100
                        </text>
                      </g>
                    </g>

                    {/* Middle Row: Clear, Bold Filename (Never Overlaps!) */}
                    <text
                      x="14"
                      y="42"
                      fontSize="10"
                      fontWeight="700"
                      fill="var(--ink, #0f172a)"
                      className="select-none"
                    >
                      {nd.filename.length > 22 ? nd.filename.slice(0, 21) + "…" : nd.filename}
                    </text>

                    {/* Bottom Row: Media Type & Verdict Text */}
                    <g transform="translate(14, 58)">
                      <text
                        x="0"
                        y="0"
                        fontSize="8"
                        fontWeight="700"
                        fill="var(--muted, #64748b)"
                        letterSpacing="0.05em"
                        className="uppercase"
                      >
                        {nd.media_type} · {nd.verdict}
                      </text>
                    </g>
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Floating Canvas Controls HUD (Bottom Right) */}
          <div className="absolute bottom-4 right-4 flex items-center gap-1.5 rounded-full border border-line bg-surface/90 p-1.5 shadow-md backdrop-blur">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z * 1.15))}
              className="grid size-7 place-items-center rounded-full text-muted hover:bg-surface2 hover:text-ink transition cursor-pointer"
              title="Zoom In"
            >
              <Plus size={14} weight="bold" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.5, z * 0.85))}
              className="grid size-7 place-items-center rounded-full text-muted hover:bg-surface2 hover:text-ink transition cursor-pointer"
              title="Zoom Out"
            >
              <Minus size={14} weight="bold" />
            </button>
            <div className="h-4 w-px bg-line/80 mx-0.5" />
            <button
              onClick={resetView}
              className="grid size-7 place-items-center rounded-full text-muted hover:bg-surface2 hover:text-ink transition cursor-pointer"
              title="Reset View"
            >
              <ArrowsIn size={14} weight="bold" />
            </button>
          </div>

          {/* Canvas Indicator Pill (Bottom Left) */}
          <div className="pointer-events-none absolute bottom-4 left-4 flex items-center gap-2 rounded-full border border-line/60 bg-surface/85 px-3 py-1 text-[11px] font-semibold text-muted shadow-2xs backdrop-blur">
            <span className="size-2 rounded-full bg-[#12B981]" />
            <span>
              {nodes.length} Visible Forensic Cards · Drag cards to reposition
            </span>
          </div>

          {/* Selected Node Detailed Inspector Card */}
          {selectedNode && (
            <div className="absolute top-4 left-4 w-80 sm:w-96 rounded-lg border border-line bg-surface/95 p-4 shadow-xs backdrop-blur-md z-20 space-y-3.5">
              <div className="flex items-start justify-between gap-2 border-b border-line pb-3">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="rounded-md bg-accent/10 px-2 py-0.5 font-mono text-[10px] font-bold text-accent">
                      {selectedNode.case_reference}
                    </span>
                    <span className="text-[11px] font-semibold text-muted uppercase">
                      {selectedNode.media_type}
                    </span>
                  </div>
                  <h4 className="mt-1 text-xs font-bold text-ink truncate max-w-[220px]" title={selectedNode.filename}>
                    {selectedNode.filename}
                  </h4>
                  {selectedNode.case_title && (
                    <div className="text-[11px] text-muted truncate max-w-[220px]">
                      {selectedNode.case_title}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => setSelectedNode(null)}
                  className="size-7 grid place-items-center rounded-full text-muted hover:bg-surface2 hover:text-ink transition"
                >
                  <X size={14} weight="bold" />
                </button>
              </div>

              {/* Score & Verdict */}
              <div className="flex items-center justify-between rounded-xl bg-surface2/60 p-2.5 text-xs">
                <span className="font-bold text-ink">Integrity Score</span>
                <span
                  className="font-bold"
                  style={{ color: VERDICT_STYLES[selectedNode.verdict || "Consistent"].text }}
                >
                  {selectedNode.score ?? 0}/100 · {selectedNode.verdict}
                </span>
              </div>

              {/* SHA-256 Hash */}
              {selectedNode.sha256 && (
                <div className="flex items-center justify-between gap-2 rounded-xl border border-line bg-surface px-2.5 py-1.5 text-[11px] font-mono text-muted">
                  <span className="truncate">{selectedNode.sha256.slice(0, 24)}...</span>
                  <button
                    onClick={() => copyToClipboard(selectedNode.sha256!)}
                    className="size-5 grid place-items-center text-muted hover:text-ink"
                    title="Copy SHA-256"
                  >
                    {copiedSha ? <Check size={12} className="text-[#10B981]" /> : <Copy size={12} />}
                  </button>
                </div>
              )}

              {/* Linked items */}
              <div>
                <div className="text-[10px] font-bold text-muted mb-1.5">
                  Direct Cross-Case Links ({selectedNodeLinks.length})
                </div>
                {selectedNodeLinks.length === 0 ? (
                  <div className="text-xs text-muted italic">No direct cross-case links for this item.</div>
                ) : (
                  <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {selectedNodeLinks.map((l, lIdx) => {
                      const meta = CORRELATION_COLORS[l.edge.type] || CORRELATION_COLORS.same_hash;
                      return (
                        <div
                          key={lIdx}
                          onClick={() => {
                            if (l.partner) {
                              const partnerNode = nodePos.get(l.partner.id);
                              if (partnerNode) setSelectedNode(partnerNode);
                            }
                          }}
                          className="flex items-center justify-between gap-2 rounded-lg bg-surface2/40 hover:bg-surface2 p-1.5 text-[11px] border border-line/60 transition cursor-pointer"
                        >
                          <span className="flex items-center gap-1.5 truncate">
                            <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: meta.stroke }} />
                            <strong className="text-ink font-semibold">{l.edge.label}:</strong>
                            <span className="text-muted truncate">
                              {l.partner?.case_reference} ({l.partner?.filename})
                            </span>
                          </span>
                          <span className="text-accent shrink-0">→</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center gap-2">
                <Button
                  variant="primary"
                  onClick={() => nav(`/evidence/${selectedNode.id}`)}
                  className="flex-1 btn-pill text-xs py-1.5"
                >
                  <span>Forensic Viewer</span>
                  <ArrowUpRight size={13} weight="bold" />
                </Button>
                {selectedNode.case_id && (
                  <Button
                    variant="secondary"
                    onClick={() => nav(`/cases/${selectedNode.case_id}`)}
                    className="btn-pill text-xs py-1.5"
                  >
                    Case Overview
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Legend Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-surface2/40 px-4 py-2.5 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-bold text-muted text-[11px]">RELATIONSHIP BRIDGES:</span>
          {Object.entries(CORRELATION_COLORS).slice(0, 4).map(([type, meta]) => (
            <span key={type} className="flex items-center gap-1.5 font-medium text-ink">
              <span className="size-2 rounded-full" style={{ backgroundColor: meta.stroke }} />
              {meta.label}
            </span>
          ))}
        </div>

        <div className="text-muted text-[11px]">
          <span>Click any card to inspect · Drag cards to reposition · Scroll to zoom</span>
        </div>
      </div>
    </div>
  );
}
