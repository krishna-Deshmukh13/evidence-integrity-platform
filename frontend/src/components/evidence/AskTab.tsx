import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { api } from "@/lib/api";
import { Button, Input, Spinner, useToast } from "@/components/ui";
import { CopyButton } from "./util";

const CHIPS = ["Why did it get this score?", "Where is the edit?", "What should I do next?"];

export default function AskTab({ id }: { id: number }) {
  const toast = useToast();
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { api.chat(id).then(setMsgs).catch(() => undefined); }, [id]);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [msgs, busy]);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || busy) return;
    setQ(""); setBusy(true);
    setMsgs((m) => [...m, { id: -Date.now(), role: "user", content: question, source: null, created_at: new Date().toISOString() }]);
    try {
      const a = await api.ask(id, question);
      setMsgs((m) => [...m, a]);
    } catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
    finally { setBusy(false); }
  };
  const clear = async () => {
    try { await api.clearChat(id); setMsgs([]); } catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
  };

  return (
    <div className="p-4">
      {msgs.length === 0 && !busy ? (
        <div className="py-6 text-center">
          <div className="flex flex-wrap justify-center gap-2">
            {CHIPS.map((c) => <button key={c} onClick={() => void send(c)} className="rounded-full border border-line bg-surface2 px-3 py-1.5 text-xs hover:bg-accent-soft">{c}</button>)}
          </div>
        </div>
      ) : (
        <div className="max-h-[420px] space-y-3 overflow-y-auto">
          {msgs.map((m) => m.role === "user" ? (
            <div key={m.id} className="flex justify-end"><div className="max-w-[85%] whitespace-pre-wrap rounded-lg bg-accent px-3 py-2 text-sm text-accent-ink">{m.content}</div></div>
          ) : (
            <div key={m.id} className="flex justify-start"><div className="max-w-[85%] rounded-lg bg-surface2 px-3 py-2 text-sm">
              <div className="whitespace-pre-wrap">{m.content}</div>
              <div className="mt-1 flex items-center gap-2 text-[11px] text-muted">{m.source && <span>{m.source}</span>}<CopyButton text={m.content} label="Copy" /></div>
            </div></div>
          ))}
          {busy && <div className="flex items-center gap-2 text-sm text-muted"><Spinner />Thinking</div>}
          <div ref={end} />
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <Input value={q} placeholder="Ask about this file" onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void send(q); }} />
        <Button variant="primary" onClick={() => void send(q)} disabled={busy || !q.trim()}>Send</Button>
        {msgs.length > 0 && <Button onClick={() => void clear()}>Clear</Button>}
      </div>
      <p className="mt-2 text-xs text-muted">Answers use only this file's findings, report, custody log and notes. Only you can see this conversation.</p>
    </div>
  );
}
