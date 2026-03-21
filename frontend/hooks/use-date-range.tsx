"use client";

/**
 * Global date range context for the Ennesso dashboard.
 *
 * Persists the selected date range in URL search params (?from=&to=)
 * so it survives navigation and is shareable.
 *
 * Validation rules:
 *   - startDate >= MIN_DATE ("2021-01-01" — earliest CKAN historical data)
 *   - endDate <= today
 *   - startDate < endDate
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Earliest date with data in Supabase — matches CKAN historical catalogue. */
export const MIN_DATE = "2021-01-01";

function todayISO(): string {
  return new Date().toISOString().split("T")[0] ?? "";
}

function defaultStartISO(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().split("T")[0] ?? "";
}

function clamp(value: string, min: string, max: string): string {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/** Backend hard limit — matches FastAPI validation */
export const MAX_RANGE_DAYS = 365;

export type DateRangeError =
  | "start_too_early"
  | "end_in_future"
  | "start_after_end"
  | "range_too_large"
  | null;

export const DATE_RANGE_ERROR_MESSAGES: Record<
  NonNullable<DateRangeError>,
  string
> = {
  start_too_early: `Start date cannot be before ${MIN_DATE}`,
  end_in_future: "End date cannot be in the future",
  start_after_end: "Start date must be before end date",
  range_too_large: `Date range cannot exceed ${MAX_RANGE_DAYS} days`,
};

export function validateDateRange(start: string, end: string): DateRangeError {
  if (start < MIN_DATE) return "start_too_early";
  if (end > todayISO()) return "end_in_future";
  if (start >= end) return "start_after_end";
  const days = (new Date(end).getTime() - new Date(start).getTime()) / 86_400_000;
  if (days > MAX_RANGE_DAYS) return "range_too_large";
  return null;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface DateRangeContextValue {
  startDate: string;
  endDate: string;
  /** Attempt to set a new range. Returns false if validation fails. */
  setDateRange: (start: string, end: string) => boolean;
  /** Current validation error, or null if valid. */
  error: DateRangeError;
  /** Human-readable label e.g. "Jan 2024 — Mar 2025" */
  label: string;
}

const DateRangeContext = createContext<DateRangeContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function DateRangeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Read initial values from URL or fall back to defaults
  const initialStart =
    searchParams.get("from") ?? defaultStartISO();
  const initialEnd = searchParams.get("to") ?? todayISO();

  const [startDate, setStart] = useState(() =>
    clamp(initialStart, MIN_DATE, todayISO())
  );
  const [endDate, setEnd] = useState(() =>
    clamp(initialEnd, MIN_DATE, todayISO())
  );
  const [error, setError] = useState<DateRangeError>(null);

  // Sync URL params when dates change
  const syncToUrl = useCallback(
    (start: string, end: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("from", start);
      params.set("to", end);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [router, pathname, searchParams]
  );

  const setDateRange = useCallback(
    (start: string, end: string): boolean => {
      const err = validateDateRange(start, end);
      if (err) {
        setError(err);
        return false;
      }
      setError(null);
      setStart(start);
      setEnd(end);
      syncToUrl(start, end);
      return true;
    },
    [syncToUrl]
  );

  // Sync on mount if URL params exist
  useEffect(() => {
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  if (from && to) {
    const err = validateDateRange(from, to);
    if (!err) {
      setStart(from);
      setEnd(to);
    } else {
      // Stale/invalid URL params — reset to safe default
      const safeStart = defaultStartISO();
      const safeEnd = todayISO();
      setStart(safeStart);
      setEnd(safeEnd);
      syncToUrl(safeStart, safeEnd);
    }
  }
}, []); // eslint-disable-line react-hooks/exhaustive-deps

  const label = useMemo(() => {
    const fmt = (iso: string) =>
      new Date(iso + "T00:00:00").toLocaleDateString("en", {
        month: "short",
        year: "numeric",
      });
    return `${fmt(startDate)} — ${fmt(endDate)}`;
  }, [startDate, endDate]);

  const value = useMemo(
    () => ({ startDate, endDate, setDateRange, error, label }),
    [startDate, endDate, setDateRange, error, label]
  );

  return (
    <DateRangeContext.Provider value={value}>
      {children}
    </DateRangeContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useDateRange(): DateRangeContextValue {
  const ctx = useContext(DateRangeContext);
  if (!ctx) {
    throw new Error("useDateRange must be used inside DateRangeProvider");
  }
  return ctx;
}
