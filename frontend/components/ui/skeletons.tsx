import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-white/5",
        className
      )}
    />
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-lg p-5 flex flex-col gap-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-2.5 w-20" />
    </div>
  );
}

export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div
      className="w-full rounded-lg bg-white/5 animate-pulse flex items-end justify-around px-6 pb-6 pt-4 gap-3"
      style={{ height }}
    >
      {/* Fake bars to give chart-like appearance */}
      {[65, 80, 45, 90, 55, 70, 40, 85, 60, 75, 50, 95].map((h, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm bg-white/10"
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex gap-4 px-5 py-2.5 border-b border-border">
        {[120, 80, 100, 160, 60].map((w, i) => (
          <Skeleton key={i} className="h-3" style={{ width: w }} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 px-5 py-3">
          {[120, 80, 100, 160, 60].map((w, j) => (
            <Skeleton key={j} className="h-3" style={{ width: w }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
      {/* Chart row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-surface border border-border rounded-lg p-5">
          <Skeleton className="h-3 w-32 mb-4" />
          <ChartSkeleton height={300} />
        </div>
        <div className="bg-surface border border-border rounded-lg p-5">
          <Skeleton className="h-3 w-24 mb-4" />
          <ChartSkeleton height={300} />
        </div>
      </div>
    </div>
  );
}
