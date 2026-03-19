import { cn } from "@/lib/utils";
import { QualityBadge } from "@/components/ui/quality-badge";
import type { QualityFlag } from "@/types/api";

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  subValue?: string;
  qualityFlag?: QualityFlag;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function MetricCard({
  label,
  value,
  unit,
  subValue,
  qualityFlag,
  trend,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "bg-surface border border-border rounded-lg p-5 flex flex-col gap-3",
        className
      )}
    >
      {/* Label row */}
      <div className="flex items-center justify-between">
        <span className="font-sans text-xs font-medium uppercase tracking-widest text-muted">
          {label}
        </span>
        {qualityFlag && <QualityBadge flag={qualityFlag} />}
      </div>

      {/* Value */}
      <div className="flex items-end gap-2">
        <span className="font-mono text-3xl font-semibold text-foreground leading-none">
          {value}
        </span>
        {unit && (
          <span className="font-mono text-sm text-muted mb-0.5">{unit}</span>
        )}
        {trend && (
          <span
            className={cn(
              "font-mono text-sm mb-0.5",
              trend === "up" && "text-[#00C2A8]",
              trend === "down" && "text-red-400",
              trend === "neutral" && "text-muted"
            )}
          >
            {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"}
          </span>
        )}
      </div>

      {/* Sub value */}
      {subValue && (
        <span className="font-sans text-xs text-muted">{subValue}</span>
      )}
    </div>
  );
}
