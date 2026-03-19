"use client";

import { useEffect, useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { AreaStackedChart } from "@/components/charts/area-stacked-chart";
import { DonutChart } from "@/components/charts/donut-chart";
import {
  fetchEnergyBalance,
  fetchEnergyMix,
  fetchCarbon,
} from "@/lib/api-client";
import { useEnergyFormatter } from "@/hooks/use-energy-formatter";
import type {
  DailyBalanceResponse,
  EnergyMixResponse,
  CarbonDataPoint,
} from "@/types/api";

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 12);
  return {
    start: start.toISOString().split("T")[0] ?? "",
    end: end.toISOString().split("T")[0] ?? "",
  };
}

export default function OverviewPage() {
  const fmt = useEnergyFormatter();
  const dates = defaultDates();

  const [balance, setBalance] = useState<DailyBalanceResponse[]>([]);
  const [mix, setMix] = useState<EnergyMixResponse | null>(null);
  const [carbon, setCarbon] = useState<CarbonDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(dates.start);
  const [endDate, setEndDate] = useState(dates.end);

  async function load(start: string, end: string) {
    setLoading(true);
    try {
      const [balanceData, carbonData] = await Promise.all([
        fetchEnergyBalance(start, end),
        fetchCarbon(start, end),
      ]);
      setBalance(balanceData);
      setCarbon(carbonData);

      // Mix for latest available date
      if (balanceData.length > 0) {
        const latestDate = balanceData[balanceData.length - 1]?.date;
        if (latestDate) {
          try {
            const mixData = await fetchEnergyMix(latestDate);
            setMix(mixData);
          } catch {
            // Mix not available for this date
          }
        }
      }
    } catch (err) {
      console.error("Failed to load overview data:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(startDate, endDate);
  }, []);

  function handleDateChange(start: string, end: string) {
    setStartDate(start);
    setEndDate(end);
    void load(start, end);
  }

  // Aggregate metrics
  const totalMwh = balance.reduce((s, d) => s + d.total_mwh, 0);
  const totalHydro = balance.reduce((s, d) => s + d.hydraulic_mwh, 0);
  const renewableShare = totalMwh > 0 ? totalHydro / totalMwh : 0;
  const latestCarbon = carbon[carbon.length - 1];
  const avgIntensity =
    carbon.length > 0
      ? carbon.reduce((s, d) => s + d.intensity_kg_per_mwh, 0) / carbon.length
      : 0;

  return (
    <div className="flex flex-col h-full">
      <Topbar title="OVERVIEW" onDateChange={handleDateChange} />

      <div className="p-6 space-y-6">
        {/* KPI cards */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Total Generation"
            value={loading ? "—" : fmt.compact(totalMwh)}
            unit="MWh"
            subValue={`${startDate} → ${endDate}`}
          />
          <MetricCard
            label="Renewable Share"
            value={loading ? "—" : fmt.percent(renewableShare)}
            subValue="Hydraulic + Solar + Wind"
            trend={renewableShare > 0.7 ? "up" : "neutral"}
          />
          <MetricCard
            label="Avg CO₂ Intensity"
            value={loading ? "—" : avgIntensity.toFixed(1)}
            unit="kg/MWh"
            subValue="IPCC lifecycle factors"
            trend={avgIntensity < 100 ? "up" : "down"}
          />
          <MetricCard
            label="CO₂ Avoided"
            value={
              loading
                ? "—"
                : fmt.co2(
                    carbon.reduce((s, d) => s + d.avoided_co2_kg, 0)
                  )
            }
            subValue="vs 100% thermal baseline"
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-3 gap-4">
          {/* Stacked area — 2/3 width */}
          <div className="col-span-2 bg-surface border border-border rounded-lg p-5">
            <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
              Generation Mix — MWh
            </h2>
            {loading ? (
              <div className="h-80 flex items-center justify-center">
                <span className="font-mono text-sm text-muted animate-pulse">
                  Loading…
                </span>
              </div>
            ) : (
              <AreaStackedChart data={balance} height={300} />
            )}
          </div>

          {/* Donut — 1/3 width */}
          <div className="bg-surface border border-border rounded-lg p-5">
            <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
              Current Mix
            </h2>
            {loading || !mix ? (
              <div className="h-80 flex items-center justify-center">
                <span className="font-mono text-sm text-muted animate-pulse">
                  Loading…
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 pt-4">
                <DonutChart data={mix} size={180} />
                <div className="text-center">
                  <p className="font-mono text-2xl font-semibold text-foreground">
                    {fmt.compact(mix.total_mwh)}
                  </p>
                  <p className="font-sans text-xs text-muted mt-1">
                    MWh on {mix.date}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
