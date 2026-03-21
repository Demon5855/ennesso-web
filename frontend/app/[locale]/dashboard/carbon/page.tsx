"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { fetchCarbon } from "@/lib/api-client";
import { useEnergyFormatter } from "@/hooks/use-energy-formatter";
import { useDateRange } from "@/hooks/use-date-range";
import { BRAND_COLORS } from "@/lib/chart-colors";
import type { CarbonDataPoint } from "@/types/api";

export default function CarbonPage() {
  const fmt = useEnergyFormatter();
  const t = useTranslations("metrics");
  const tDash = useTranslations("dashboard");
  const tC = useTranslations("common");
  const { startDate, endDate } = useDateRange();
  const [data, setData] = useState<CarbonDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const result = await fetchCarbon(startDate, endDate);
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

  const totalCo2 = data.reduce((s, d) => s + d.total_co2_kg, 0);
  const totalAvoided = data.reduce((s, d) => s + d.avoided_co2_kg, 0);
  const avgIntensity = data.length > 0
    ? data.reduce((s, d) => s + d.intensity_kg_per_mwh, 0) / data.length : 0;
  const avgRenewable = data.length > 0
    ? data.reduce((s, d) => s + d.renewable_share, 0) / data.length : 0;

  return (
    <div className="flex flex-col h-full">
      <Topbar title={tDash("carbon").toUpperCase()} />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label={t("co2Total")} value={loading ? "—" : fmt.co2(totalCo2)} subValue={tC("lifecycleEmissions")} />
          <MetricCard label={t("co2Intensity")} value={loading ? "—" : avgIntensity.toFixed(1)} unit="kg/MWh" trend={avgIntensity < 100 ? "up" : "down"} />
          <MetricCard label={t("co2Avoided")} value={loading ? "—" : fmt.co2(totalAvoided)} subValue={tC("vsThermal")} trend="up" />
          <MetricCard label={t("avgRenewable")} value={loading ? "—" : fmt.percent(avgRenewable)} trend={avgRenewable > 0.7 ? "up" : "neutral"} />
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
            {tDash("carbonTrend")}
          </h2>
          {loading ? (
            <div className="h-72 flex items-center justify-center">
              <span className="font-mono text-sm text-muted animate-pulse">Loading…</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2D3A" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }} axisLine={{ stroke: "#2A2D3A" }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "IBM Plex Mono" }} axisLine={false} tickLine={false} width={48} />
                <Tooltip contentStyle={{ backgroundColor: "#1A1D27", border: "1px solid #2A2D3A", borderRadius: "6px", fontFamily: "IBM Plex Mono", fontSize: 12 }} />
                <Legend wrapperStyle={{ fontFamily: "IBM Plex Sans", fontSize: 12, color: "#6B7280" }} />
                <Line type="monotone" dataKey="intensity_kg_per_mwh" name={t("co2Intensity")} stroke={BRAND_COLORS.primary} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="renewable_share" name={t("renewableShare")} stroke="#7ED321" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
