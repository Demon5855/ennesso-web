"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { GENERATION_COLORS } from "@/lib/chart-colors";
import type { EnergyMixResponse } from "@/types/api";

interface DonutChartProps {
  data: EnergyMixResponse;
  size?: number;
}

interface SliceEntry {
  name: string;
  value: number;
  color: string;
}

export function DonutChart({ data, size = 220 }: DonutChartProps) {
  const slices: SliceEntry[] = [
    { name: "Hydraulic", value: data.hydraulic_pct, color: GENERATION_COLORS.hydraulic },
    { name: "Thermal", value: data.thermal_pct, color: GENERATION_COLORS.thermal },
    { name: "Solar", value: data.solar_pct, color: GENERATION_COLORS.solar },
    { name: "Wind", value: data.wind_pct, color: GENERATION_COLORS.wind },
    { name: "Biomass", value: data.biomass_pct, color: GENERATION_COLORS.biomass },
    { name: "Other", value: data.other_pct, color: GENERATION_COLORS.other },
  ].filter((s) => s.value > 0);

  return (
    <div className="flex items-center gap-6">
      <div style={{ width: size, height: size, flexShrink: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="80%"
              dataKey="value"
              paddingAngle={2}
              strokeWidth={0}
            >
              {slices.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "#1A1D27",
                border: "1px solid #2A2D3A",
                borderRadius: "6px",
                fontFamily: "IBM Plex Mono",
                fontSize: 12,
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <ul className="flex flex-col gap-2.5">
        {slices.map((s) => (
          <li key={s.name} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: s.color }}
            />
            <span className="font-sans text-xs text-muted w-16">{s.name}</span>
            <span className="font-mono text-xs text-foreground">
              {s.value.toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
