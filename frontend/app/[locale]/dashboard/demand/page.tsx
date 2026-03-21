"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { fetchDemand } from "@/lib/api-client";
import { useEnergyFormatter } from "@/hooks/use-energy-formatter";
import { useDateRange } from "@/hooks/use-date-range";
import type { DemandDataPoint } from "@/types/api";

export default function DemandPage() {
  const fmt = useEnergyFormatter();
  const t = useTranslations("metrics");
  const tDash = useTranslations("dashboard");
  const tU = useTranslations("units");
  const { startDate, endDate } = useDateRange();
  const [data, setData] = useState<DemandDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const result = await fetchDemand(startDate, endDate);
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

  const total = data.reduce((s, d) => s + d.demand_mwh, 0);
  const avg = data.length > 0 ? total / data.length : 0;
  const max = data.length > 0 ? Math.max(...data.map((d) => d.demand_mwh)) : 0;

  return (
    <div className="flex flex-col h-full">
      <Topbar title={tDash("demand").toUpperCase()} />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <MetricCard label={t("totalDemand")} value={loading ? "—" : fmt.compact(total)} unit="MWh" />
          <MetricCard label={t("avgDaily")} value={loading ? "—" : fmt.compact(avg)} unit={tU("mwhPerDay")} />
          <MetricCard label={t("peakDay")} value={loading ? "—" : fmt.compact(max)} unit="MWh" />
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
            {tDash("historicalDemand")}
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
                <XAxis dataKey="date" tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }} axisLine={{ stroke: "#2A2D3A" }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }} axisLine={false} tickLine={false} width={48} />
                <Tooltip contentStyle={{ backgroundColor: "#1A1D27", border: "1px solid #2A2D3A", borderRadius: "6px", fontFamily: "IBM Plex Mono", fontSize: 12 }} formatter={(v: number) => [`${(v / 1000).toFixed(1)} GWh`]} />
                <Area type="monotone" dataKey="demand_mwh" name="Demand" stroke="#00C2A8" strokeWidth={2} fill="url(#demandGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
