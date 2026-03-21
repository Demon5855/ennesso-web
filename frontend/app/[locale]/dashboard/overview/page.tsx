"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { AreaStackedChart } from "@/components/charts/area-stacked-chart";
import { DonutChart } from "@/components/charts/donut-chart";
import { fetchEnergyBalance, fetchEnergyMix, fetchCarbon } from "@/lib/api-client";
import { useEnergyFormatter } from "@/hooks/use-energy-formatter";
import { useDateRange } from "@/hooks/use-date-range";
import type { DailyBalanceResponse, EnergyMixResponse, CarbonDataPoint } from "@/types/api";

export default function OverviewPage() {
  const fmt = useEnergyFormatter();
  const t = useTranslations("metrics");
  const tDash = useTranslations("dashboard");
  const tC = useTranslations("common");
  const tType = useTranslations("generationType");
  const { startDate, endDate } = useDateRange();

  const [balance, setBalance] = useState<DailyBalanceResponse[]>([]);
  const [mix, setMix] = useState<EnergyMixResponse | null>(null);
  const [carbon, setCarbon] = useState<CarbonDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [balanceData, carbonData] = await Promise.all([
          fetchEnergyBalance(startDate, endDate),
          fetchCarbon(startDate, endDate),
        ]);
        if (cancelled) return;
        setBalance(balanceData);
        setCarbon(carbonData);

        const latestDate = balanceData[balanceData.length - 1]?.date;
        if (latestDate) {
          try {
            const mixData = await fetchEnergyMix(latestDate);
            if (!cancelled) setMix(mixData);
          } catch { /* mix not available */ }
        }
      } catch (err) {
        console.error("Overview load failed:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [startDate, endDate]);

  const totalMwh = balance.reduce((s, d) => s + d.total_mwh, 0);
  const totalHydro = balance.reduce((s, d) => s + d.hydraulic_mwh + d.solar_mwh + d.wind_mwh + d.biomass_mwh, 0);
  const renewableShare = totalMwh > 0 ? totalHydro / totalMwh : 0;
  const avgIntensity = carbon.length > 0
    ? carbon.reduce((s, d) => s + d.intensity_kg_per_mwh, 0) / carbon.length
    : 0;
  const totalAvoided = carbon.reduce((s, d) => s + d.avoided_co2_kg, 0);

  return (
    <div className="flex flex-col h-full">
      <Topbar title={tDash("overview").toUpperCase()} />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label={t("totalGeneration")}
            value={loading ? "—" : fmt.compact(totalMwh)}
            unit="MWh"
            subValue={`${startDate} → ${endDate}`}
          />
          <MetricCard
            label={t("renewableShare")}
            value={loading ? "—" : fmt.percent(renewableShare)}
            subValue={tC("renewableComposition")}
            trend={renewableShare > 0.7 ? "up" : "neutral"}
          />
          <MetricCard
            label={t("co2Intensity")}
            value={loading ? "—" : avgIntensity.toFixed(1)}
            unit="kg/MWh"
            subValue={tC("ipccFactors")}
            trend={avgIntensity < 100 ? "up" : "down"}
          />
          <MetricCard
            label={t("co2Avoided")}
            value={loading ? "—" : fmt.co2(totalAvoided)}
            subValue={tC("vsThermalBaseline")}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 bg-surface border border-border rounded-lg p-5">
            <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
              {tDash("generationMix")}
            </h2>
            {loading ? (
              <div className="h-80 flex items-center justify-center">
                <span className="font-mono text-sm text-muted animate-pulse">Loading…</span>
              </div>
            ) : (
              <AreaStackedChart
                data={balance}
                height={300}
                labels={{
                  hydraulic: tType("hydraulic"),
                  thermal: tType("thermal"),
                  solar: tType("solar"),
                  wind: tType("wind"),
                  biomass: tType("biomass"),
                }}
              />
            )}
          </div>

          <div className="bg-surface border border-border rounded-lg p-5">
            <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
              {tDash("currentMix")}
            </h2>
            {loading || !mix ? (
              <div className="h-80 flex items-center justify-center">
                <span className="font-mono text-sm text-muted animate-pulse">Loading…</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 pt-4">
                <DonutChart
                  data={mix}
                  size={180}
                  labels={{
                    hydraulic: tType("hydraulic"),
                    thermal: tType("thermal"),
                    solar: tType("solar"),
                    wind: tType("wind"),
                    biomass: tType("biomass"),
                    other: tType("other"),
                  }}
                />
                <div className="text-center">
                  <p className="font-mono text-2xl font-semibold text-foreground">
                    {fmt.compact(mix.total_mwh)}
                  </p>
                  <p className="font-sans text-xs text-muted mt-1">{tC("mwhOn", { date: mix.date })}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
