// Shared UI kit — Simple, plain, human-made and functional design system
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { CheckCircle, Info, Warning, X } from "@phosphor-icons/react";
import type { Verdict } from "@/lib/types";
import { scoreTone, verdictTone } from "@/lib/format";

export const cx = (...a: (string | false | null | undefined)[]) => a.filter(Boolean).join(" ");

export type Tone = "good" | "warn" | "bad" | "muted" | "accent";

const TONE_TEXT: Record<Tone, string> = {
  good: "text-emerald-700 dark:text-emerald-400",
  warn: "text-amber-700 dark:text-amber-400",
  bad: "text-red-700 dark:text-red-400",
  muted: "text-slate-600 dark:text-slate-400",
  accent: "text-blue-700 dark:text-blue-400",
};

const TONE_SOFT: Record<Tone, string> = {
  good: "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800",
  warn: "bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800",
  bad: "bg-red-50 text-red-800 border border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800",
  muted: "bg-slate-100 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  accent: "bg-blue-50 text-blue-800 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800",
};

export const toneText = (t: Tone) => TONE_TEXT[t];
export const toneSoft = (t: Tone) => TONE_SOFT[t];

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "highlight";
  size?: "sm" | "md" | "lg";
}) {
  const v = {
    primary:
      "bg-blue-600 text-white hover:bg-blue-700 border border-blue-600 shadow-2xs",
    secondary:
      "bg-white text-slate-800 border border-slate-300 hover:bg-slate-50 shadow-2xs dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700 dark:hover:bg-slate-750",
    highlight:
      "bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-900",
    ghost:
      "hover:bg-slate-100 text-slate-600 hover:text-slate-900 dark:hover:bg-slate-800 dark:text-slate-400 dark:hover:text-slate-200",
    danger:
      "bg-red-600 text-white hover:bg-red-700 border border-red-600 shadow-2xs",
  }[variant];

  const s = {
    sm: "h-7.5 px-2.5 text-xs font-medium",
    md: "h-8.5 px-3.5 text-xs font-medium",
    lg: "h-10 px-4 text-sm font-semibold",
  }[size];

  return (
    <button
      {...p}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-md cursor-pointer transition-colors duration-100 disabled:opacity-50 disabled:pointer-events-none select-none",
        s,
        v,
        className
      )}
    />
  );
}

export function Card({
  className,
  highlight = false,
  children,
}: {
  className?: string;
  highlight?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className={cx(
        "rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-xs dark:bg-slate-850 dark:border-slate-750",
        highlight && "border-blue-200 bg-blue-50/40 dark:bg-blue-950/20 dark:border-blue-900",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  right,
}: {
  title: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 pb-3 mb-3 border-b border-slate-200 dark:border-slate-750">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      {right}
    </div>
  );
}

export function Badge({
  tone = "muted",
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 text-xs font-medium tabular-nums rounded px-2 py-0.5",
        TONE_SOFT[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

const VERDICT_MAP: Record<string, string> = {
  "Consistent": "Looks genuine",
  "Needs review": "Please check",
  "Likely manipulated": "Probably fake",
};

export function VerdictText({ verdict }: { verdict: Verdict | null }) {
  if (!verdict) return <span className="text-slate-500 text-xs font-medium">Not checked yet</span>;
  const t = verdictTone(verdict);
  return (
    <span className={cx("inline-flex items-center gap-1.5 text-xs font-semibold", TONE_TEXT[t])}>
      <span className={cx("size-2 rounded-full shrink-0", { good: "bg-emerald-600", warn: "bg-amber-500", bad: "bg-red-600", muted: "bg-slate-400", accent: "bg-blue-600" }[t])} />
      <span>{VERDICT_MAP[verdict] || verdict}</span>
    </span>
  );
}

export function ScoreChip({ score }: { score: number | null }) {
  return (
    <span
      className={cx(
        "inline-flex font-mono text-xs font-bold tabular-nums",
        TONE_TEXT[scoreTone(score)]
      )}
    >
      {score ?? "-"}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cx(
        "inline-block size-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600",
        className
      )}
    />
  );
}

export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-slate-500">
      <Spinner />
      <span className="text-xs font-medium">{label}</span>
    </div>
  );
}

export function ErrorBox({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:bg-red-950/40 dark:border-red-900 dark:text-red-300 flex items-center justify-between gap-3">
      <span className="text-xs sm:text-sm font-medium">{message}</span>
      {onRetry && (
        <Button size="sm" variant="danger" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function Empty({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 py-12 text-center">
      <div className="font-semibold text-sm text-slate-800 dark:text-slate-200">{title}</div>
      {hint && <div className="max-w-sm text-xs text-slate-500 leading-normal">{hint}</div>}
      {action && <div className="mt-2.5">{action}</div>}
    </div>
  );
}

export function Progress({
  value,
  tone = "accent",
}: {
  value: number;
  tone?: Tone;
}) {
  const barColor = {
    accent: "bg-blue-600",
    good: "bg-emerald-600",
    warn: "bg-amber-500",
    bad: "bg-red-600",
    muted: "bg-slate-400",
  }[tone];

  return (
    <div className="h-2 w-full overflow-hidden rounded bg-slate-200 dark:bg-slate-700">
      <div
        className={cx("h-full transition-colors", barColor)}
        style={{ width: `${Math.max(2, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-xs text-slate-500 mb-0.5">
            {eyebrow}
          </div>
        )}
        <h1 className="truncate text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100">
          {title}
        </h1>
        {subtitle && (
          <div className="mt-0.5 text-xs sm:text-sm text-slate-500">
            {subtitle}
          </div>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Stat({
  label,
  value,
  tone,
  to,
}: {
  label: string;
  value: ReactNode;
  tone?: Tone;
  to?: string;
}) {
  const body = (
    <div className="rounded-lg border border-slate-200 bg-white p-3.5 sm:p-4 shadow-xs dark:bg-slate-850 dark:border-slate-750">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className={cx("mt-1 text-xl sm:text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100", tone && TONE_TEXT[tone])}>
        {value}
      </div>
    </div>
  );
  return to ? (
    <a href={to} className="block hover:border-slate-400 transition-colors">
      {body}
    </a>
  ) : (
    body
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: ReactNode }[];
}) {
  return (
    <div className="inline-flex rounded-md border border-slate-200 bg-slate-100 p-0.5 dark:bg-slate-800 dark:border-slate-700">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cx(
            "rounded px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer",
            value === o.value
              ? "bg-white text-slate-900 shadow-xs border border-slate-200 dark:bg-slate-700 dark:text-white dark:border-slate-600"
              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Tabs<T extends string>({
  value,
  onChange,
  tabs,
}: {
  value: T;
  onChange: (v: T) => void;
  tabs: { value: T; label: ReactNode; count?: number }[];
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-md border border-slate-200 bg-slate-100 p-0.5 w-fit max-w-full overflow-x-auto dark:bg-slate-800 dark:border-slate-700">
      {tabs.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={cx(
            "whitespace-nowrap rounded px-3 py-1 text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5",
            value === t.value
              ? "bg-white text-slate-900 shadow-xs border border-slate-200 dark:bg-slate-700 dark:text-white dark:border-slate-600 font-semibold"
              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
          )}
        >
          <span>{t.label}</span>
          {t.count !== undefined && (
            <span
              className={cx(
                "rounded px-1.5 py-0.2 text-[10px] font-bold",
                value === t.value ? "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200" : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
              )}
            >
              {t.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

const field =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 outline-none transition-colors focus:border-blue-600 focus:ring-1 focus:ring-blue-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100";

export const Input = (p: InputHTMLAttributes<HTMLInputElement>) => (
  <input {...p} className={cx(field, "h-9", p.className)} />
);

export const Select = (p: SelectHTMLAttributes<HTMLSelectElement>) => (
  <select {...p} className={cx(field, "h-9 cursor-pointer", p.className)} />
);

export const Textarea = (p: TextareaHTMLAttributes<HTMLTextAreaElement>) => (
  <textarea
    {...p}
    className={cx(
      "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-600 focus:ring-1 focus:ring-blue-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100",
      p.className
    )}
  />
);

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block mb-3">
      <span className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={onClose}
    >
      <div
        role="dialog"
        className="w-full max-w-md rounded-lg border border-slate-300 bg-white shadow-md overflow-hidden dark:bg-slate-850 dark:border-slate-700"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-750">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
          <button
            onClick={onClose}
            className="size-7 rounded grid place-items-center text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-5">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-3 bg-slate-50 dark:bg-slate-800 dark:border-slate-750">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export function ConfirmModal({
  open,
  title,
  body,
  confirmLabel = "Delete",
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{body}</div>
    </Modal>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300">
      {children}
    </kbd>
  );
}

export const Mono = ({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) => <span className={cx("font-mono text-xs", className)}>{children}</span>;

// Toast System
type ToastItem = { id: number; msg: string; tone: Tone };
const ToastCtx = createContext<(msg: string, tone?: Tone) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((msg: string, tone: Tone = "good") => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, msg, tone }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4000);
  }, []);

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-5 right-5 z-[70] flex flex-col gap-2">
        {items.map((i) => (
          <div
            key={i.id}
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-2.5 shadow-sm text-xs font-medium text-slate-800 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200"
          >
            {i.tone === "good" ? (
              <CheckCircle className="text-emerald-600" size={16} weight="fill" />
            ) : i.tone === "bad" ? (
              <Warning className="text-red-600" size={16} weight="fill" />
            ) : (
              <Info className="text-blue-600" size={16} weight="fill" />
            )}
            <span>{i.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
