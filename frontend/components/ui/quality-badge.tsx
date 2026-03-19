import { cn } from "@/lib/utils";
import type { QualityFlag } from "@/types/api";

interface QualityBadgeProps {
  flag: QualityFlag;
  showLabel?: boolean;
  className?: string;
}

const CONFIG: Record<
  QualityFlag,
  { dot: string; label: string; text: string }
> = {
  ok: {
    dot: "bg-[#00C2A8]",
    label: "OK",
    text: "text-[#00C2A8]",
  },
  warning: {
    dot: "bg-[#F5A623]",
    label: "Warning",
    text: "text-[#F5A623]",
  },
  error: {
    dot: "bg-red-500",
    label: "Error",
    text: "text-red-500",
  },
};

export function QualityBadge({
  flag,
  showLabel = false,
  className,
}: QualityBadgeProps) {
  const { dot, label, text } = CONFIG[flag];

  return (
    <span
      className={cn("inline-flex items-center gap-1.5", className)}
      title={label}
    >
      <span
        className={cn("h-2 w-2 rounded-full flex-shrink-0", dot)}
        aria-hidden="true"
      />
      {showLabel && (
        <span className={cn("font-mono text-xs", text)}>{label}</span>
      )}
    </span>
  );
}
