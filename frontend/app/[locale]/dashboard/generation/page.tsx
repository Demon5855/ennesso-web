"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { Topbar } from "@/components/layout/topbar";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { ChartSkeleton } from "@/components/ui/skeletons";
import { fetchEnergyBalance } from "@/lib/api-client";
import { GENERATION_COLORS } from "@/lib/chart-colors";
import { useDateRange } from "@/hooks/use-date-range";
import { cn } from "@/lib/utils";
import type { DailyBalanceResponse } from "@/types/api";

type Filter = "all" | "hydraulic" | "thermal" | "solar" | "wind" | "biomass";

const FILTERS: { key: Filter; labelKey: string }[] = [
  { key: "all", labelKey: "all" },
  { key: "hydraulic", labelKey: "hydraulic" },
  { key: "thermal", labelKey: "thermal" },
  { key: "solar", labelKey: "solar" },
  { key: "wind", labelKey: "wind" },
  { key: "biomass", labelKey: "biomass" },
];

export default function GenerationPage() {
  const t = useTranslations("generationType");
  const tDash = useTranslations("dashboard");
  const { startDate, endDate } = useDateRange();
  const [data, setData] = useState<DailyBalanceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const result = await fetchEnergyBalance(startDate, endDate);
        if (!cancelled) setData(result);
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [startDate, endDate]);

  const lines =
    filter === "all"
      ? (["hydraulic", "thermal", "solar", "wind", "biomass"] as const)
      : [filter];

  return (
    <div className="flex flex-col h-full">
      <Topbar title={tDash("generation").toUpperCase()} />
      <ErrorBoundary>
        <div className="p-6 space-y-5">
          <div className="flex gap-2 flex-wrap">
            {FILTERS.map(({ key, labelKey }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={cn(
                  "px-3 py-1.5 rounded-full font-sans text-xs transition-colors border",
                  filter === key
                    ? "bg-primary/10 border-primary text-primary"
                    : "border-border text-muted hover:text-foreground hover:border-muted"
                )}
                style={
                  filter === key && key !== "all"
                    ? {
                      backgroundColor: `${GENERATION_COLORS[key]}15`,
                      borderColor: GENERATION_COLORS[key],
                      color: GENERATION_COLORS[key],
                    }
                    : undefined
                }
              >
                {t(labelKey)}
              </button>
            ))}
          </div>

          <div className="bg-surface border border-border rounded-lg p-5">
            <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
              {tDash("dailyGeneration")}
            </h2>
            {loading ? (
              <ChartSkeleton />
            ) : (
              <ResponsiveContainer width="100%" height={380}>
                <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2A2D3A" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }} axisLine={{ stroke: "#2A2D3A" }} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }} axisLine={false} tickLine={false} width={48} />
                  <Tooltip contentStyle={{ backgroundColor: "#1A1D27", border: "1px solid #2A2D3A", borderRadius: "6px", fontFamily: "IBM Plex Mono", fontSize: 12 }} formatter={(v: number) => [`${(v / 1000).toFixed(1)} GWh`]} />
                  <Legend wrapperStyle={{ fontFamily: "IBM Plex Sans", fontSize: 12, color: "#6B7280" }} />
                  {lines.map((src) => (
                    <Line key={src} type="monotone" dataKey={`${src}_mwh`}
                      name={t(src)}
                      stroke={GENERATION_COLORS[src]} strokeWidth={2} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </ErrorBoundary>
    </div>
  );
}
