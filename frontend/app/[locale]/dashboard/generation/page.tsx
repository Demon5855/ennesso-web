"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Topbar } from "@/components/layout/topbar";
import { fetchEnergyBalance } from "@/lib/api-client";
import { GENERATION_COLORS } from "@/lib/chart-colors";
import { cn } from "@/lib/utils";
import type { DailyBalanceResponse } from "@/types/api";

type Filter = "all" | "hydraulic" | "thermal" | "solar" | "wind" | "biomass";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "hydraulic", label: "Hydraulic" },
  { key: "thermal", label: "Thermal" },
  { key: "solar", label: "Solar" },
  { key: "wind", label: "Wind" },
  { key: "biomass", label: "Biomass" },
];

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 12);
  return {
    start: start.toISOString().split("T")[0] ?? "",
    end: end.toISOString().split("T")[0] ?? "",
  };
}

export default function GenerationPage() {
  const dates = defaultDates();
  const [data, setData] = useState<DailyBalanceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");

  async function load(start: string, end: string) {
    setLoading(true);
    try {
      setData(await fetchEnergyBalance(start, end));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(dates.start, dates.end); }, []);

  const lines =
    filter === "all"
      ? (["hydraulic", "thermal", "solar", "wind", "biomass"] as const)
      : [filter];

  return (
    <div className="flex flex-col h-full">
      <Topbar title="GENERATION" onDateChange={(s, e) => void load(s, e)} />

      <div className="p-6 space-y-5">
        {/* Filter pills */}
        <div className="flex gap-2 flex-wrap">
          {FILTERS.map(({ key, label }) => (
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
                      backgroundColor: `${GENERATION_COLORS[key as keyof typeof GENERATION_COLORS]}15`,
                      borderColor: GENERATION_COLORS[key as keyof typeof GENERATION_COLORS],
                      color: GENERATION_COLORS[key as keyof typeof GENERATION_COLORS],
                    }
                  : undefined
              }
            >
              {label}
            </button>
          ))}
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
            Daily Generation — MWh
          </h2>
          {loading ? (
            <div className="h-96 flex items-center justify-center">
              <span className="font-mono text-sm text-muted animate-pulse">Loading…</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2D3A" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                  axisLine={{ stroke: "#2A2D3A" }}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                  tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1A1D27",
                    border: "1px solid #2A2D3A",
                    borderRadius: "6px",
                    fontFamily: "IBM Plex Mono",
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [`${(v / 1000).toFixed(1)} GWh`]}
                />
                <Legend wrapperStyle={{ fontFamily: "IBM Plex Sans", fontSize: 12, color: "#6B7280" }} />
                {lines.map((src) => (
                  <Line
                    key={src}
                    type="monotone"
                    dataKey={`${src}_mwh`}
                    name={src.charAt(0).toUpperCase() + src.slice(1)}
                    stroke={GENERATION_COLORS[src]}
                    strokeWidth={2}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
