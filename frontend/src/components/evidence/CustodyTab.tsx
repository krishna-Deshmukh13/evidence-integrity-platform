import { useState } from "react";
import { ShieldCheck, ShieldWarning } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import type { EvidenceFull, VerifyResult } from "@/lib/types";
import { dateTime, shortHash } from "@/lib/format";
import { Button, Mono, Spinner, useToast } from "@/components/ui";
import { CopyButton } from "./util";

export default function CustodyTab({ ev, reload }: { ev: EvidenceFull; reload: () => void }) {
  const toast = useToast();
  const [res, setRes] = useState<VerifyResult | null>(null);
  const [busy, setBusy] = useState(false);
  const verify = async () => {
    setBusy(true);
    try { setRes(await api.verify(ev.id)); reload(); }
    catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
    finally { setBusy(false); }
  };
  return (
    <div className="p-4">
      <Button onClick={() => void verify()} disabled={busy}>{busy ? <Spinner /> : <ShieldCheck size={15} />}Verify integrity</Button>
      {res && (res.ok ? (
        <div className="mt-3 rounded-lg bg-good-soft p-3 text-good">
          <div className="font-medium">File and custody chain are intact</div>
          <div className="text-sm">{res.message}</div>
        </div>
      ) : (
        <div className="mt-3 rounded-lg bg-bad-soft p-3 text-bad">
          <div className="flex items-center gap-1.5 font-medium"><ShieldWarning size={16} />Integrity check failed</div>
          <div className="text-sm">{res.message}{res.broken_at !== null && ` Broken at event #${res.broken_at}.`}</div>
        </div>
      ))}
      <ol className="mt-4 space-y-3">
        {ev.custody.map((c) => (
          <li key={c.seq} className="flex gap-3">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-surface2 text-xs font-medium">{c.seq}</span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium">{c.action}</span>
                <span className="text-xs text-muted">{dateTime(c.at)}</span>
              </div>
              <div className="text-sm text-muted">{c.actor}{c.note ? ` / ${c.note}` : ""}</div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-muted">
                <span>file <Mono>{shortHash(c.file_hash)}</Mono><CopyButton text={c.file_hash} /></span>
                <span>event <Mono>{shortHash(c.event_hash)}</Mono><CopyButton text={c.event_hash} /></span>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
