import { useState } from "react";
import type { Note } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dateTime } from "@/lib/format";
import { Button, Empty, Textarea, useToast } from "@/components/ui";

export default function NotesTab({ id, notes, reload }: { id: number; notes: Note[]; reload: () => void }) {
  const { can } = useAuth();
  const toast = useToast();
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const add = async () => {
    if (!body.trim()) return;
    setBusy(true);
    try { await api.addNote(id, body.trim()); setBody(""); toast("Note added"); reload(); }
    catch (e) { toast(e instanceof Error ? e.message : "Failed", "bad"); }
    finally { setBusy(false); }
  };
  return (
    <div className="p-4">
      {notes.length === 0 ? <Empty title="No notes yet" /> : (
        <div className="space-y-3">
          {notes.map((n) => (
            <div key={n.id} className="rounded-lg bg-surface2 p-3">
              <div className="text-xs text-muted">{n.author} · {dateTime(n.created_at)}</div>
              <p className="mt-1 whitespace-pre-wrap text-sm">{n.body}</p>
            </div>
          ))}
        </div>
      )}
      {can("investigator") && (
        <div className="mt-4 space-y-2">
          <Textarea rows={3} value={body} placeholder="Add a note" onChange={(e) => setBody(e.target.value)} />
          <Button variant="primary" onClick={() => void add()} disabled={busy || !body.trim()}>Add note</Button>
        </div>
      )}
    </div>
  );
}
