import { useRef, useState } from "react";
import { ArrowUp, Folder, UploadSimple, WarningCircle, ArrowClockwise } from "@phosphor-icons/react";
import { Button, Progress, cx } from "@/components/ui";
import { uploadEvidence } from "@/lib/api";
import { bytes } from "@/lib/format";

const EXT = new Set("jpg jpeg png webp bmp tif tiff gif mp4 mov avi mkv webm 3gp wmv mp3 wav m4a aac ogg opus flac amr wma pdf docx".split(" "));
const MAX = 500 * 1024 * 1024;
const extOf = (n: string) => n.split(".").pop()?.toLowerCase() ?? "";

type Item = { id: number; name: string; size: number; file: File; pct: number; state: "wait" | "up" | "done" | "err"; error?: string };

async function readAll(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  const out: FileSystemEntry[] = [];
  for (;;) {
    const batch = await new Promise<FileSystemEntry[]>((res, rej) => reader.readEntries(res, rej));
    if (!batch.length) return out;
    out.push(...batch);
  }
}

async function walk(entry: FileSystemEntry, out: File[]): Promise<void> {
  if (entry.isFile) {
    const f = await new Promise<File>((res, rej) => (entry as FileSystemFileEntry).file(res, rej));
    out.push(f);
  } else if (entry.isDirectory) {
    for (const e of await readAll((entry as FileSystemDirectoryEntry).createReader())) await walk(e, out);
  }
}

let seq = 1;

export default function UploadZone({ caseId, onUploaded }: { caseId: number; onUploaded: () => void }) {
  const [items, setItems] = useState<Item[]>([]);
  const [notes, setNotes] = useState<string[]>([]);
  const [over, setOver] = useState(false);
  const filesRef = useRef<HTMLInputElement>(null);
  const dirRef = useRef<HTMLInputElement>(null);

  const patch = (id: number, p: Partial<Item>) => setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));

  async function run(list: Item[]) {
    const queue = [...list];
    const worker = async () => {
      for (let it = queue.shift(); it; it = queue.shift()) {
        patch(it.id, { state: "up", pct: 0 });
        try {
          await uploadEvidence(caseId, it.file, (pct) => patch(it.id, { pct }));
          patch(it.id, { state: "done", pct: 100 });
        } catch (e) {
          patch(it.id, { state: "err", error: e instanceof Error ? e.message : "Upload failed" });
        }
        onUploaded();
      }
    };
    await Promise.all([worker(), worker()]);
  }

  function accept(files: File[]) {
    const skipped: string[] = [];
    const valid: Item[] = [];
    for (const f of files) {
      const ext = extOf(f.name);
      if (!EXT.has(ext)) skipped.push(`${f.name} (unsupported format)`);
      else if (f.size > MAX) skipped.push(`${f.name} (exceeds 500 MB limit)`);
      else valid.push({ id: seq++, name: f.name, size: f.size, file: f, pct: 0, state: "wait" });
    }
    if (skipped.length) setNotes((xs) => [...skipped, ...xs].slice(0, 10));
    if (valid.length) {
      setItems((xs) => [...xs, ...valid]);
      void run(valid);
    }
  }

  return (
    <div className="space-y-3">
      {/* Upload Box Matching PDF Page 3 */}
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={async (e) => {
          e.preventDefault();
          setOver(false);
          const raw: File[] = [];
          const items = Array.from(e.dataTransfer.items ?? []);
          for (const it of items) {
            const entry = (it as any).webkitGetAsEntry?.();
            if (entry) await walk(entry, raw);
            else { const f = it.getAsFile(); if (f) raw.push(f); }
          }
          if (raw.length) accept(raw);
          else if (e.dataTransfer.files?.length) accept(Array.from(e.dataTransfer.files));
        }}
        onClick={() => filesRef.current?.click()}
        className={cx(
          "cursor-pointer rounded-lg border-2 border-dashed p-6 transition-colors card-interactive",
          over ? "border-accent bg-accent/5 scale-[1.01]" : "border-line bg-surface hover:border-accent/50 hover:bg-surface2/30"
        )}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="grid size-10 place-items-center rounded-xl bg-accent/15 text-accent shrink-0 shadow-2xs">
              <ArrowUp size={20} weight="bold" />
            </div>
            <div>
              <div className="text-sm font-bold text-ink">
                Drop files or a whole folder to add evidence
              </div>
              <div className="text-xs text-muted mt-0.5">
                Images, video, audio, PDF, DOCX · up to 500 MB per file · 2 uploads at a time
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => dirRef.current?.click()}
              className="flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink shadow-xs hover:bg-surface2 transition btn-interactive"
            >
              <Folder size={14} className="text-muted" />
              Choose folder
            </button>
          </div>
        </div>

        {/* Hidden inputs */}
        <input
          ref={filesRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            accept(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
        <input
          ref={dirRef}
          type="file"
          hidden
          {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
          onChange={(e) => {
            accept(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
      </div>

      {notes.length > 0 && (
        <div className="rounded-xl bg-[#FEECEC] p-3.5 text-xs text-[#EF4444] border border-[#EF4444]/30 flex items-start justify-between gap-3">
          <div>
            <div className="font-extrabold flex items-center gap-1.5">
              <WarningCircle size={16} weight="bold" />
              <span>Unsupported or Exceeded Files ({notes.length})</span>
            </div>
            <div className="mt-1 space-y-0.5 text-ink/80">
              {notes.slice(0, 5).map((n, i) => (
                <div key={i} className="truncate">• {n}</div>
              ))}
            </div>
            <div className="mt-2 text-[11px] text-muted">
              Supported formats: Images (.jpg, .png, .webp), Video (.mp4, .mov, .avi), Audio (.wav, .mp3, .m4a), and Documents (.pdf, .docx). Max size 500 MB.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setNotes([])}
            className="text-muted hover:text-ink text-[11px] font-bold px-2 py-1 rounded-md hover:bg-surface2 transition cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* In-Flight Upload Items */}
      {items.length > 0 && (
        <div className="space-y-2">
          {items.slice(-6).map((it) => (
            <div key={it.id} className="rounded-xl border border-line bg-surface p-3 shadow-2xs space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-ink truncate">{it.name}</span>
                <span className={cx(
                  "font-mono font-bold tabular-nums text-[11px]",
                  it.state === "err" ? "text-bad" : it.state === "done" ? "text-good" : "text-accent"
                )}>
                  {it.state === "wait" ? "Waiting..." : it.state === "up" ? `${it.pct}%` : it.state === "done" ? "Uploaded" : it.error}
                </span>
              </div>
              {(it.state === "up" || it.state === "wait") && (
                <div className="h-1.5 w-full rounded-full bg-surface2 overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-colors"
                    style={{ width: `${it.pct}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
