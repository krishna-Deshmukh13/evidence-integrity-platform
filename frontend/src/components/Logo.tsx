import { cx } from "@/components/ui";

export interface LogoProps {
  /**
   * "mark": Just the square "Ei" icon badge
   * "full": The horizontal brand lockup with "Ei" icon + "Evidence Integrity" + subtext
   */
  variant?: "full" | "mark";
  /** Predefined size preset or custom pixel number */
  size?: "sm" | "md" | "lg" | "xl" | number;
  /** Whether to show the "Digital evidence, verified" subtitle in "full" variant */
  showSubtitle?: boolean;
  /** Custom subtitle text if desired */
  subtitle?: string;
  /** Custom className for the container */
  className?: string;
}

const SIZE_MAP = {
  sm: { icon: 24, text: "text-sm", sub: "text-[10px]" },
  md: { icon: 32, text: "text-base", sub: "text-[11px]" },
  lg: { icon: 44, text: "text-xl", sub: "text-xs" },
  xl: { icon: 56, text: "text-2xl", sub: "text-sm" },
};

export function LogoMark({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <div
      style={{ width: size, height: size }}
      className={cx(
        "relative shrink-0 flex items-center justify-center rounded-md bg-[#0f172a] select-none overflow-hidden",
        className
      )}
      title="Evidence Integrity"
    >
      <img
        src="/logo-mark.png"
        alt="Ei"
        className="w-full h-full object-contain rounded-md"
      />
    </div>
  );
}

export default function Logo({
  variant = "full",
  size = "md",
  showSubtitle = true,
  subtitle = "Digital evidence, verified",
  className,
}: LogoProps) {
  const pixelSize = typeof size === "number" ? size : SIZE_MAP[size].icon;
  const textClass = typeof size === "number" ? "text-base" : SIZE_MAP[size].text;
  const subClass = typeof size === "number" ? "text-[11px]" : SIZE_MAP[size].sub;

  if (variant === "mark") {
    return <LogoMark size={pixelSize} className={className} />;
  }

  return (
    <div className={cx("inline-flex items-center gap-3 select-none", className)}>
      <LogoMark size={pixelSize} />
      <div className="flex flex-col justify-center min-w-0">
        <span
          className={cx(
            "font-black font-sans tracking-tight text-ink dark:text-white leading-tight truncate",
            textClass
          )}
        >
          Evidence Integrity
        </span>
        {showSubtitle && (
          <span
            className={cx(
              "font-medium text-muted dark:text-slate-400 tracking-normal leading-tight mt-0.5 truncate",
              subClass
            )}
          >
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
