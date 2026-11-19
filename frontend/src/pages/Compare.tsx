import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowsLeftRight } from "@phosphor-icons/react";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, Loading, PageHeader, Stat, type Tone } from "@/components/ui";
import { api } from "@/lib/api";
import { sevTone } from "@/lib/format";
import type { CompareResult, SearchRow } from "@/lib/types";
import { Picker } from "@/components/search/Picker";
import { ImageCompare } from "@/components/search/ImageCompare";
import { humanize } from "@/components/search/params";

const idOf = (s: string | null): number | null => { const n = Number(s); return s && Number.isInteger(n) && n > 0 ? n : null; };
const pct = (n: number | null, frac = false) => (n === null ? "-" : `${Math.round((frac && n <= 1 ? n * 100 : n) * 10) / 10}%`);

export default function Compare() {
  const [sp, setSp] = useSearchParams();
  const a = idOf(sp.get("a"));
  const b = idOf(sp.get("b"));
  const [rows, setRows] = useState<Record<number, SearchRow>>({});
  const [res, setRes] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const setIds = (na: number | null, nb: number | null) => setSp((prev) => {
    const n = new URLSearchParams(prev);
    if (na) n.set("a", String(na)); else n.delete("a");
    if (nb) n.set("b", String(nb)); else n.delete("b");
    return n;
  }, { replace: true });
  const pick = (which: "a" | "b") => (r: SearchRow) => {
    setRows((x) => ({ ...x, [r.id]: r }));
    if (which === "a") setIds(r.id, b); else setIds(a, r.id);
  };

  useEffect(() => {
    if (!a || !b) { setRes(null); setError(null); return; }
    let dead = false;
    setLoading(true); setError(null); setRes(null);
    api.compare(a, b)
      .then((r) => { if (dead) return; setRes(r); setRows((x) => ({ ...x, [r.a.id]: r.a, [r.b.id]: r.b })); })
      .catch((e: unknown) => { if (!dead) setError(e instanceof Error ? e.message : "Comparison failed"); })
      .finally(() => { if (!dead) setLoading(false); });
    return () => { dead = true; };
  }, [a, b, tick]);

  const delta = res?.score_change ?? null;
  const deltaTone: Tone = delta === null || delta === 0 ? "muted" : delta > 0 ? "good" : "bad";

  return (
    <div>
      <PageHeader title="Compare" subtitle="Check two pieces of evidence against each other" />
      <div className="mb-5 grid grid-cols-1 items-center gap-2 md:grid-cols-[1fr_auto_1fr]">
        <Picker tag="A" id={a} row={a ? rows[a] : undefined} onPick={pick("a")} />
        <Button aria-label="Swap A and B" className="mx-auto" disabled={!a && !b} onClick={() => setIds(b, a)}><ArrowsLeftRight size={16} /><span className="md:hidden">Swap</span></Button>
        <Picker tag="B" id={b} row={b ? rows[b] : undefined} onPick={pick("b")} />
      </div>

      {(!a || !b) && <Card><Empty title="Pick two files to compare" hint="Choose evidence for A and B above. Links from other pages fill these in for you." /></Card>}
      {a && b && loading && <Loading label="Comparing" />}
      {error && <ErrorBox message={error} onRetry={() => setTick((t) => t + 1)} />}

      {res && (
        <div className="space-y-4">
          <Card className="grid grid-cols-2 gap-2 p-3 md:grid-cols-4">
            <Stat label="Same file" value={res.same_file ? "Yes" : "No"} tone={res.same_file ? "good" : "muted"} />
            <Stat label="Score change (A to B)" tone={deltaTone}
              value={<>{res.a.score ?? "-"} → {res.b.score ?? "-"}{delta !== null && <span className="ml-1.5 text-sm">({delta > 0 ? "+" : ""}{delta})</span>}</>} />
            <Stat label="Visual similarity" value={pct(res.visual_similarity, true)} />
            <Stat label="Pixels changed" value={pct(res.pixels_changed_pct)} />
          </Card>

          {res.a.media_type === "image" && res.b.media_type === "image" && <ImageCompare aId={res.a.id} bId={res.b.id} diff={res.diff_image} />}

          <Card>
            <CardHeader title="Metadata differences" right={<Badge>{res.metadata_diffs.length}</Badge>} />
            {res.metadata_diffs.length === 0 ? <Empty title="No metadata differences" /> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[32rem] text-left text-sm">
                  <thead className="text-xs text-muted"><tr><th className="px-4 py-2 font-medium">Field</th><th className="px-4 py-2 font-medium">A</th><th className="px-4 py-2 font-medium">B</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {res.metadata_diffs.map((d) => (
                      <tr key={d.field}>
                        <td className="px-4 py-2 font-medium">{d.field}</td>
                        <td className="break-all px-4 py-2 font-mono text-xs">{d.a ?? <span className="text-muted">-</span>}</td>
                        <td className="break-all px-4 py-2 font-mono text-xs">{d.b ?? <span className="text-muted">-</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Check results differences" right={<Badge>{res.check_diffs.length}</Badge>} />
            {res.check_diffs.length === 0 ? <Empty title="No check differences" /> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[32rem] text-left text-sm">
                  <thead className="text-xs text-muted"><tr><th className="px-4 py-2 font-medium">Check</th><th className="px-4 py-2 font-medium">A result</th><th className="px-4 py-2 font-medium">B result</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {res.check_diffs.map((d) => (
                      <tr key={d.check} className="align-top">
                        <td className="px-4 py-2 font-medium">{humanize(d.check)}</td>
                        {[d.a, d.b].map((v, i) => (
                          <td key={i} className="px-4 py-2">
                            {v ? <div className="space-y-1"><Badge tone={sevTone(v.severity)}>{v.severity === "info" ? "passed" : v.severity}</Badge><div className="text-xs text-muted">{v.title}</div></div> : <span className="text-muted">Not run</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
