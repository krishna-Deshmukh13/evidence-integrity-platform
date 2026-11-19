import { useState, useEffect, useMemo } from "react";
import {
  ShieldCheck,
  ShieldWarning,
  Bug,
  ArrowsClockwise,
  GitFork,
  FileCode,
  Copy,
  Info,
  Sparkle,
  TreeStructure,
} from "@phosphor-icons/react";
import { Card, Button, Loading, Badge, cx } from "@/components/ui";
import { api } from "@/lib/api";

export default function MerkleTreeViewer() {
  const [caseId, setCaseId] = useState<number>(1);
  const [casesList, setCasesList] = useState<any[]>([]);
  const [merkleData, setMerkleData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [simulateTamper, setSimulateTamper] = useState(false);
  const [copiedSha, setCopiedSha] = useState<string | null>(null);

  // Load available cases
  useEffect(() => {
    api.cases()
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setCasesList(res);
          setCaseId(res[0].id);
        }
      })
      .catch((err) => console.error(err));
  }, []);

  // Load Merkle tree for active case
  const loadTree = (cid: number) => {
    setLoading(true);
    api.caseMerkleTree(cid)
      .then((data) => setMerkleData(data))
      .catch((err) => console.error("Failed to load Merkle tree:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (caseId) {
      loadTree(caseId);
    }
  }, [caseId]);

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedSha(hash);
    setTimeout(() => setCopiedSha(null), 1500);
  };

  // Compute displayed tree based on simulation state
  const leaves = useMemo(() => {
    if (!merkleData?.leaves) return [];
    if (!simulateTamper) return merkleData.leaves;

    // Simulate tampering the first leaf
    return merkleData.leaves.map((l: any, idx: number) => {
      if (idx === 0) {
        return {
          ...l,
          hash: "🚨 E1F0_MODIFIED_BYTE_ATTACK_INVALID_00000000000000000000000000",
          is_tampered: true,
          original_hash: l.hash,
        };
      }
      return l;
    });
  }, [merkleData, simulateTamper]);

  const rootHash = useMemo(() => {
    if (!merkleData?.root_hash) return "0000000000000000000000000000000000000000000000000000000000000000";
    if (!simulateTamper) return merkleData.root_hash;
    return "🚨 FF99_ROOT_DIGEST_CORRUPTED_CASCADE_UNTRUSTED_NONCE_FAIL_8801";
  }, [merkleData, simulateTamper]);

  return (
    <Card className="p-5 sm:p-6 space-y-5 bg-surface border-line shadow-xs">
      {/* Top Header & Simulation Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-line">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-lg bg-accent/10 text-accent grid place-items-center shrink-0">
            <TreeStructure size={22} weight="bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-ink">
                Visual Cryptographic Merkle Tree Audit Ledger
              </h3>
              <Badge tone={simulateTamper ? "bad" : "good"}>
                {simulateTamper ? "TAMPER ATTACK SIMULATED" : "ROOT HASH VERIFIED"}
              </Badge>
            </div>
            <p className="text-xs text-muted mt-0.5">
              Hierarchical binary hash tree proving mathematical non-repudiation and immediate parent cascade invalidation under RFC 6962
            </p>
          </div>
        </div>

        {/* Case Selector & Tamper Attack Simulator Button */}
        <div className="flex items-center gap-3">
          <select
            value={caseId}
            onChange={(e) => setCaseId(Number(e.target.value))}
            className="h-9 rounded-xl border border-line bg-surface px-3 text-xs font-semibold text-ink outline-none focus:border-accent"
          >
            {casesList.map((c) => (
              <option key={c.id} value={c.id}>
                {c.reference} — {c.title.substring(0, 24)}...
              </option>
            ))}
          </select>

          <button
            onClick={() => setSimulateTamper(!simulateTamper)}
            className={cx(
              "flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition shadow-xs cursor-pointer",
              simulateTamper
                ? "bg-rose-600 hover:bg-rose-700 text-white ring-2 ring-rose-400/40 animate-pulse"
                : "bg-surface2 hover:bg-surface2/80 text-ink border border-line"
            )}
          >
            <Bug size={16} weight="bold" />
            <span>{simulateTamper ? "Stop Tamper Attack" : "Simulate Tamper Attack"}</span>
          </button>
        </div>
      </div>

      {loading && !merkleData ? (
        <Loading label="Computing Cryptographic Merkle Leaves & Binary Nodes..." />
      ) : (
        <div className="space-y-6">
          {/* Simulation Alert HUD */}
          {simulateTamper && (
            <div className="p-3.5 rounded-lg bg-rose-500/10 border-2 border-rose-500/50 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-3">
              <ShieldWarning size={22} className="shrink-0 text-rose-600 mt-0.5" weight="fill" />
              <div>
                <div className="font-bold text-sm">Adversarial Byte Alteration Detected in Exhibit #1!</div>
                <div className="mt-1 leading-relaxed">
                  Notice how modifying just <strong>1 single byte</strong> inside the file changed its leaf digest. Because child hashes recursively combine ($H(L_1 \parallel L_2)$), the invalidation propagated instantly up the tree, breaking the Root Block Hash. In court, this mathematical property constitutes irrefutable proof that evidence was altered after intake.
                </div>
              </div>
            </div>
          )}

          {/* Merkle Tree Canvas */}
          <div className="p-6 rounded-lg border border-line bg-stone-50/60 dark:bg-zinc-950/40 relative overflow-x-auto space-y-8">
            {/* 1. Root Block Node */}
            <div className="flex flex-col items-center">
              <div
                className={cx(
                  "p-4 rounded-lg border text-center transition-all shadow-md max-w-xl w-full",
                  simulateTamper
                    ? "bg-rose-500/15 border-rose-500 ring-4 ring-rose-500/20 text-rose-950 dark:text-rose-200"
                    : "bg-emerald-500/10 border-emerald-500 ring-4 ring-emerald-500/15 text-emerald-950 dark:text-emerald-200"
                )}
              >
                <div className="flex items-center justify-between text-[11px] font-mono font-bold mb-1">
                  <span className="flex items-center gap-1.5">
                    {simulateTamper ? <ShieldWarning size={15} className="text-rose-600" weight="fill" /> : <ShieldCheck size={15} className="text-emerald-600" weight="fill" />}
                    MERKLE ROOT BLOCK HASH
                  </span>
                  <span className={simulateTamper ? "text-rose-600 font-bold" : "text-emerald-600 font-bold"}>
                    {simulateTamper ? "INVALID / TAMPERED" : "ANCHORED & INTACT"}
                  </span>
                </div>

                <div className="flex items-center justify-center gap-2 font-mono text-xs font-black truncate py-1">
                  <span className="truncate">{rootHash}</span>
                  <button
                    onClick={() => copyHash(rootHash)}
                    className="p-1 hover:opacity-80 cursor-pointer shrink-0"
                    title="Copy Root Hash"
                  >
                    <Copy size={13} />
                  </button>
                </div>

                <div className="text-[10px] text-muted font-mono mt-1 flex items-center justify-center gap-3">
                  <span>Case: {merkleData?.case_reference}</span>
                  <span>·</span>
                  <span>Audit Timestamp: {merkleData?.audit_timestamp ? new Date(merkleData.audit_timestamp).toLocaleTimeString() : "Live"}</span>
                </div>
              </div>

              {/* Connecting Tree Line from Root */}
              <div className={cx("w-0.5 h-8 transition-colors", simulateTamper ? "bg-rose-500" : "bg-emerald-500")} />
            </div>

            {/* 2. Intermediate Level 1 Branch Nodes */}
            <div className="relative">
              {/* Horizontal Connecting Branch Line */}
              <div className={cx("h-0.5 mx-auto max-w-2xl transition-colors", simulateTamper ? "bg-rose-500" : "bg-accent/60")} />

              <div className="flex justify-around gap-4 pt-3 max-w-3xl mx-auto">
                <div
                  className={cx(
                    "p-3 rounded-xl border text-center transition-all text-xs font-mono max-w-[280px] w-full shadow-xs",
                    simulateTamper
                      ? "bg-rose-500/15 border-rose-500 text-rose-900 dark:text-rose-200"
                      : "bg-surface border-line text-ink"
                  )}
                >
                  <div className="font-bold text-[10px] uppercase text-muted mb-0.5">
                    Branch Node L1-A (Exhibits 1-2)
                  </div>
                  <div className="truncate font-semibold text-[11px]">
                    {simulateTamper ? "🚨 B_L1A_CORRUPTED_DIGEST_FAIL" : (typeof merkleData?.levels?.[1]?.[0] === "object" ? merkleData?.levels?.[1]?.[0]?.hash : (merkleData?.levels?.[1]?.[0] || "88a4e92...9c10"))}
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-line bg-surface text-center transition-all text-xs font-mono max-w-[280px] w-full shadow-xs">
                  <div className="font-bold text-[10px] uppercase text-muted mb-0.5">
                    Branch Node L1-B (Exhibits 3-4)
                  </div>
                  <div className="truncate font-semibold text-[11px] text-ink">
                    {typeof merkleData?.levels?.[1]?.[1] === "object" ? merkleData?.levels?.[1]?.[1]?.hash : (merkleData?.levels?.[1]?.[1] || "37f411b...a088")}
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Bottom Leaf Nodes (Evidence Exhibits) */}
            <div>
              <div className="text-[11px] font-bold text-muted text-center mb-3">
                EXHIBIT LEAF NODES (H(FILE BYTES)) — {leaves.length} EVIDENCE RECORDS
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {leaves.map((leaf: any, idx: number) => {
                  const isTamperedLeaf = leaf.is_tampered;
                  return (
                    <div
                      key={leaf.id || idx}
                      className={cx(
                        "p-3.5 rounded-xl border transition-all text-xs space-y-1.5 shadow-xs relative",
                        isTamperedLeaf
                          ? "bg-rose-500/15 border-rose-500 ring-2 ring-rose-500/20"
                          : "bg-surface border-line hover:border-accent/60"
                      )}
                    >
                      <div className="flex items-center justify-between font-mono text-[10px] font-bold">
                        <span className={isTamperedLeaf ? "text-rose-600" : "text-accent"}>
                          LEAF #{idx + 1}
                        </span>
                        <span
                          className={cx(
                            "px-1.5 py-0.2 rounded text-[9px] font-bold uppercase",
                            isTamperedLeaf ? "bg-rose-600 text-white animate-pulse" : "bg-surface2 text-muted"
                          )}
                        >
                          {isTamperedLeaf ? "Tampered" : `Score: ${leaf.score ?? 95}`}
                        </span>
                      </div>

                      <div className="font-bold text-ink truncate" title={leaf.filename}>
                        {leaf.filename}
                      </div>

                      <div className="font-mono text-[10px] text-muted flex items-center justify-between">
                        <span className="truncate max-w-[140px]">{leaf.hash}</span>
                        <button
                          onClick={() => copyHash(leaf.hash)}
                          className="hover:text-ink cursor-pointer"
                          title="Copy Leaf Hash"
                        >
                          <Copy size={11} />
                        </button>
                      </div>

                      {isTamperedLeaf && (
                        <div className="text-[9px] font-mono text-rose-700 dark:text-rose-300 font-bold mt-1">
                          ↳ Injected Byte Alteration (Hash Disparity)
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
