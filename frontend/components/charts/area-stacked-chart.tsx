"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { GENERATION_COLORS } from "@/lib/chart-colors";
import type { DailyBalanceResponse } from "@/types/api";

interface AreaStackedChartProps {
  data: DailyBalanceResponse[];
  height?: number;
  labels?: {
    hydraulic: string;
    thermal: string;
    solar: string;
    wind: string;
    biomass: string;
  };
}

export function AreaStackedChart({
  data,
  height = 320,
  labels,
}: AreaStackedChartProps) {
  const SOURCES = [
    { key: "hydraulic_mwh", color: GENERATION_COLORS.hydraulic, label: labels?.hydraulic ?? "Hydraulic" },
    { key: "thermal_mwh",   color: GENERATION_COLORS.thermal,   label: labels?.thermal   ?? "Thermal"   },
    { key: "solar_mwh",     color: GENERATION_COLORS.solar,     label: labels?.solar     ?? "Solar"     },
    { key: "wind_mwh",      color: GENERATION_COLORS.wind,      label: labels?.wind      ?? "Wind"      },
    { key: "biomass_mwh",   color: GENERATION_COLORS.biomass,   label: labels?.biomass   ?? "Biomass"   },
  ] as const;

  function formatAxisDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString("en", {
      month: "short",
      day: "numeric",
    });
  }

  function formatTooltipValue(value: number): string {
    return `${(value / 1000).toFixed(1)} GWh`;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart
        data={data}
        margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
      >
        <defs>
          {SOURCES.map(({ key, color }) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2A2D3A" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatAxisDate}
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
          labelStyle={{ color: "#E8EAF0", marginBottom: 4 }}
          labelFormatter={formatAxisDate}
          formatter={(value: number, name: string) => [
            formatTooltipValue(value),
            name,
          ]}
        />
        <Legend
          wrapperStyle={{
            fontFamily: "IBM Plex Sans",
            fontSize: 12,
            color: "#6B7280",
            paddingTop: 12,
          }}
        />
        {SOURCES.map(({ key, color, label }) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            name={label}
            stackId="1"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#grad-${key})`}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
