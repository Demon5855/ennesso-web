import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format a numeric energy value with appropriate precision.
 * @example formatEnergy(12345.6789, "MWh") → "12,345.68 MWh"
 */
export function formatEnergy(
  value: number,
  unit: string,
  decimals = 2
): string {
  return `${value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} ${unit}`;
}

/**
 * Return a CSS color token for a given generation source.
 */
export function sourceColor(source: string): string {
  const palette: Record<string, string> = {
    hydraulic: "#2A7BE4",
    thermal: "#E05C2A",
    solar: "#F4C842",
    wind: "#74C2A8",
    biomass: "#6DBE7E",
    other: "#6B7280",
  };
  return palette[source] ?? palette["other"]!;
}
