"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { cn } from "@/lib/utils";
import { GENERATION_COLORS } from "@/lib/chart-colors";
import { useEnergyFormatter } from "@/hooks/use-energy-formatter";

// IPCC AR5 emission factors kg CO₂/MWh
const EMISSION_FACTORS: Record<string, number> = {
  hydraulic: 4,
  thermal: 490,
  solar: 48,
  wind: 11,
  biomass: 230,
};

// Estimated LCOE USD/MWh — approximate Ecuador 2024
const LCOE_FACTORS: Record<string, number> = {
  hydraulic: 45,
  thermal: 95,
  solar: 38,
  wind: 42,
  biomass: 110,
};

const SOURCES = ["hydraulic", "thermal", "solar", "wind", "biomass"] as const;
type Source = (typeof SOURCES)[number];

const SOURCE_LABELS: Record<Source, string> = {
  hydraulic: "Hydraulic",
  thermal: "Thermal",
  solar: "Solar",
  wind: "Wind",
  biomass: "Biomass",
};

const TOTAL_MWH = 100_000; // Reference total generation for calculations

export default function SimulatorPage() {
  const fmt = useEnergyFormatter();
  const t = useTranslations("simulator");
  const tType = useTranslations("generationType");
  const tM = useTranslations("metrics");
  const tC = useTranslations("common");

  const [mix, setMix] = useState<Record<Source, number>>({
    hydraulic: 70,
    thermal: 20,
    solar: 5,
    wind: 3,
    biomass: 2,
  });

  function handleSlider(source: Source, value: number) {
    const others = SOURCES.filter((s) => s !== source);
    const remaining = 100 - value;
    const currentOthersTotal = others.reduce((s, k) => s + (mix[k] ?? 0), 0);

    const newMix = { ...mix, [source]: value };

    if (currentOthersTotal === 0) {
      // Distribute evenly
      const each = remaining / others.length;
      others.forEach((s) => { newMix[s] = Math.round(each * 10) / 10; });
    } else {
      // Scale proportionally
      others.forEach((s) => {
        const proportion = (mix[s] ?? 0) / currentOthersTotal;
        newMix[s] = Math.round(proportion * remaining * 10) / 10;
      });
    }

    setMix(newMix);
  }

  const results = useMemo(() => {
    const totalCo2 = SOURCES.reduce((s, source) => {
      const mwh = ((mix[source] ?? 0) / 100) * TOTAL_MWH;
      return s + mwh * (EMISSION_FACTORS[source] ?? 490);
    }, 0);

    const thermalCo2 = TOTAL_MWH * 490;
    const avoided = thermalCo2 - totalCo2;
    const intensity = totalCo2 / TOTAL_MWH;

    const totalCost = SOURCES.reduce((s, source) => {
      const mwh = ((mix[source] ?? 0) / 100) * TOTAL_MWH;
      return s + mwh * (LCOE_FACTORS[source] ?? 95);
    }, 0);
    const avgLcoe = totalCost / TOTAL_MWH;

    const renewableShare =
      ((mix.hydraulic + mix.solar + mix.wind + mix.biomass) / 100);

    return { totalCo2, avoided, intensity, avgLcoe, renewableShare };
  }, [mix]);

  const total = SOURCES.reduce((s, k) => s + (mix[k] ?? 0), 0);
  const isBalanced = Math.abs(total - 100) < 0.5;

  return (
    <div className="flex flex-col h-full">
      <Topbar title={t("title").toUpperCase()} />

      <div className="p-6 space-y-6">
        <p className="font-sans text-sm text-muted">
          {t("description")}
          {" "}Reference total: {fmt.compact(TOTAL_MWH)} MWh.
        </p>

        <div className="grid grid-cols-2 gap-6">
          {/* Sliders */}
          <div className="bg-surface border border-border rounded-lg p-5 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="font-mono text-xs text-muted uppercase tracking-widest">
                {t("generationMix")}
              </h2>
              <span
                className={cn(
                  "font-mono text-xs",
                  isBalanced ? "text-[#00C2A8]" : "text-[#F5A623]"
                )}
              >
                {total.toFixed(1)}% {isBalanced ? "✓" : t("adjustToBalance")}
              </span>
            </div>

            {SOURCES.map((source) => (
              <div key={source} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-sm"
                      style={{ backgroundColor: GENERATION_COLORS[source] }}
                    />
                    <span className="font-sans text-sm text-foreground">
                      {tType(source)}
                    </span>
                  </div>
                  <span className="font-mono text-sm text-foreground w-12 text-right">
                    {(mix[source] ?? 0).toFixed(1)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={0.5}
                  value={mix[source]}
                  onChange={(e) =>
                    handleSlider(source, parseFloat(e.target.value))
                  }
                  className="w-full accent-primary h-1.5"
                  style={{ accentColor: GENERATION_COLORS[source] }}
                />
              </div>
            ))}
          </div>

          {/* Results */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <MetricCard
                label={tM("co2Total")}
                value={fmt.co2(results.totalCo2)}
                subValue={tC("lifecycleEmissions")}
              />
              <MetricCard
                label={tM("co2Avoided")}
                value={fmt.co2(results.avoided)}
                subValue={tC("vsThermal")}
                trend="up"
              />
              <MetricCard
                label={t("carbonIntensity")}
                value={results.intensity.toFixed(1)}
                unit="kg/MWh"
                trend={results.intensity < 100 ? "up" : "down"}
              />
              <MetricCard
                label={t("avgLcoe")}
                value={results.avgLcoe.toFixed(1)}
                unit="USD/MWh"
                subValue={t("approxEcuador")}
              />
            </div>

            <div className="bg-surface border border-border rounded-lg p-5">
              <h2 className="font-mono text-xs text-muted uppercase tracking-widest mb-4">
                {t("renewableShare")}
              </h2>
              <div className="flex items-end gap-3">
                <span className="font-mono text-4xl font-semibold text-primary">
                  {fmt.percent(results.renewableShare)}
                </span>
                <span className="font-sans text-xs text-muted mb-2">
                  {tC("renewableComposition")}
                </span>
              </div>

              {/* Bar */}
              <div className="mt-4 h-3 bg-background rounded-full overflow-hidden">
                {SOURCES.filter((s) => s !== "thermal").map((source) => (
                  <div
                    key={source}
                    className="h-full inline-block"
                    style={{
                      width: `${mix[source] ?? 0}%`,
                      backgroundColor: GENERATION_COLORS[source],
                    }}
                  />
                ))}
              </div>

              {/* Emission reference */}
              <div className="mt-4 pt-4 border-t border-border">
                <p className="font-sans text-xs text-muted">
                  {t("emissionFootnote")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
