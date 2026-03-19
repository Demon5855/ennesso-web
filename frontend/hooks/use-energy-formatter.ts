"use client";

/**
 * useEnergyFormatter — locale-aware number and unit formatting for energy data.
 *
 * Uses next-intl's useFormatter for locale-sensitive number formatting.
 * Examples (es locale):
 *   mwh(1234567.8)  → "1.234.567,8 MWh"
 *   percent(0.823)  → "82,3%"
 *   co2(1830000)    → "1.830 t CO₂"
 */

import { useFormatter } from "next-intl";

export function useEnergyFormatter() {
  const format = useFormatter();

  return {
    /**
     * Format a MWh value with one decimal place.
     * @example mwh(1234567.8) → "1,234,567.8 MWh"
     */
    mwh(value: number): string {
      return `${format.number(value, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })} MWh`;
    },

    /**
     * Format a MW (capacity) value with one decimal place.
     */
    mw(value: number): string {
      return `${format.number(value, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })} MW`;
    },

    /**
     * Format a GWh value (large aggregates).
     */
    gwh(value: number): string {
      const gwh = value / 1000;
      return `${format.number(gwh, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })} GWh`;
    },

    /**
     * Format a decimal share as a percentage.
     * @example percent(0.823) → "82.3%"
     */
    percent(value: number): string {
      return format.number(value, {
        style: "percent",
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });
    },

    /**
     * Format CO₂ in kg — automatically converts to tonnes for large values.
     * < 10,000 kg → shows kg, >= 10,000 → shows t
     */
    co2(valueKg: number): string {
      if (valueKg >= 10_000) {
        const tonnes = valueKg / 1000;
        return `${format.number(tonnes, {
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        })} t CO₂`;
      }
      return `${format.number(valueKg, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })} kg CO₂`;
    },

    /**
     * Format carbon intensity in kg CO₂/MWh.
     */
    intensity(value: number): string {
      return `${format.number(value, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })} kg/MWh`;
    },

    /**
     * Format LCOE in USD/MWh.
     */
    lcoe(value: number): string {
      return `${format.number(value, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })} USD/MWh`;
    },

    /**
     * Format a date string (ISO) for display.
     * @example reportDate("2024-03-31") → "31 mar. 2024"
     */
    reportDate(isoDate: string): string {
      return format.dateTime(new Date(isoDate), {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    },

    /**
     * Format a compact large number (thousands → K, millions → M).
     */
    compact(value: number): string {
      return format.number(value, { notation: "compact" });
    },
  };
}
