/**
 * Ennesso chart color constants.
 * Single source of truth — used in Recharts, D3, and CSS.
 */

export const GENERATION_COLORS = {
  hydraulic: "#2A7BE4",
  thermal: "#E05C2A",
  solar: "#F5A623",
  wind: "#7ED321",
  biomass: "#6DBE7E",
  other: "#6B7280",
} as const satisfies Record<string, string>;

export const QUALITY_COLORS = {
  ok: "#00C2A8",
  warning: "#F5A623",
  error: "#EF4444",
} as const;

export const BRAND_COLORS = {
  primary: "#00C2A8",
  background: "#0F1117",
  surface: "#1A1D27",
  border: "#2A2D3A",
  text: "#E8EAF0",
  muted: "#6B7280",
} as const;

export type GenerationColorKey = keyof typeof GENERATION_COLORS;
