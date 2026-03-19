"use client";

import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { fetchDemand } from "@/lib/api-client";
import { useEnergyFormatter } from "@/hooks/use-energy-formatter";
import type { DemandDataPoint } from "@/types/api";

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 12);
  return {
    start: start.toISOString().split("T")[0] ?? "",
    end: end.toISOString().split("T")[0] ?? "",
  };
}

export default function DemandPage() {
  const fmt = useEnergyFormatter();
  const dates = defaultDates();
  const [data, setData] = useState<DemandDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  async function load(start: string, end: string) {
    setLoading(true);
    try {
      setData(await fetchDemand(start, end));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(dates.start, dates.end); }, []);

  const total = data.reduce((s, d) => s + d.demand_mwh, 0);
  const avg = data.length > 0 ? total / data.length : 0;
  const max = data.length > 0 ? Math.max(...data.map((d) => d.demand_mwh)) : 0;

  return (
    <div className="flex flex-col h-full">
      <Topbar title="DEMAND" onDateChange={(s, e) => void load(s, e)} />

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="Total Demand"
            value={loading ? "—" : fmt.compact(total)}
            unit="MWh"
          />
          <MetricCard
            label="Avg Daily"
            value={loading ? "—" : fmt.compact(avg)}
            unit="MWh/day"
          />
          <MetricCard
            label="Peak Day"
            value={loading ? "—" : fmt.compact(max)}
            unit="MWh"
          />
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
            Historical Demand — MWh
          </h2>
          {loading ? (
            <div className="h-80 flex items-center justify-center">
              <span className="font-mono text-sm text-muted animate-pulse">Loading…</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00C2A8" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#00C2A8" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
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
                <Area
                  type="monotone"
                  dataKey="demand_mwh"
                  name="Demand"
                  stroke="#00C2A8"
                  strokeWidth={2}
                  fill="url(#demandGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
