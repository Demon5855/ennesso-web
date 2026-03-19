/**
 * Ennesso API client.
 *
 * Typed wrapper for the FastAPI backend. Base URL comes from
 * NEXT_PUBLIC_API_URL environment variable.
 *
 * All functions throw on HTTP errors with a descriptive message.
 */

import type {
  CarbonDataPoint,
  DailyBalanceResponse,
  DemandDataPoint,
  EnergyMixResponse,
  GenerationDataPoint,
  GenerationType,
  HealthResponse,
  LineageResponse,
  QualitySummaryResponse,
  ReportRequest,
} from "@/types/api";

const BASE_URL =
  process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status} — ${path}: ${body}`);
  }

  return res.json() as Promise<T>;
}

function toParams(obj: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined) params.set(k, v);
  }
  const str = params.toString();
  return str ? `?${str}` : "";
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/health");
}

// ---------------------------------------------------------------------------
// Energy
// ---------------------------------------------------------------------------

export async function fetchEnergyBalance(
  startDate: string,
  endDate: string,
  countryCode = "EC"
): Promise<DailyBalanceResponse[]> {
  const qs = toParams({
    start_date: startDate,
    end_date: endDate,
    country_code: countryCode,
  });
  return apiFetch<DailyBalanceResponse[]>(`/api/v1/energy/balance${qs}`);
}

export async function fetchGeneration(
  startDate: string,
  endDate: string,
  generationType?: GenerationType,
  countryCode = "EC"
): Promise<GenerationDataPoint[]> {
  const qs = toParams({
    start_date: startDate,
    end_date: endDate,
    generation_type: generationType,
    country_code: countryCode,
  });
  return apiFetch<GenerationDataPoint[]>(`/api/v1/energy/generation${qs}`);
}

export async function fetchEnergyMix(
  date: string,
  countryCode = "EC"
): Promise<EnergyMixResponse> {
  const qs = toParams({ date, country_code: countryCode });
  return apiFetch<EnergyMixResponse>(`/api/v1/energy/mix${qs}`);
}

export async function fetchDemand(
  startDate: string,
  endDate: string,
  countryCode = "EC"
): Promise<DemandDataPoint[]> {
  const qs = toParams({
    start_date: startDate,
    end_date: endDate,
    country_code: countryCode,
  });
  return apiFetch<DemandDataPoint[]>(`/api/v1/energy/demand${qs}`);
}

// ---------------------------------------------------------------------------
// Carbon
// ---------------------------------------------------------------------------

export async function fetchCarbon(
  startDate: string,
  endDate: string,
  countryCode = "EC"
): Promise<CarbonDataPoint[]> {
  const qs = toParams({
    start_date: startDate,
    end_date: endDate,
    country_code: countryCode,
  });
  return apiFetch<CarbonDataPoint[]>(`/api/v1/energy/carbon${qs}`);
}

// ---------------------------------------------------------------------------
// Lineage
// ---------------------------------------------------------------------------

export async function fetchLineage(
  recordId: string
): Promise<LineageResponse[]> {
  return apiFetch<LineageResponse[]>(`/api/v1/lineage/${recordId}`);
}

// ---------------------------------------------------------------------------
// Quality
// ---------------------------------------------------------------------------

export async function fetchQualitySummary(
  startDate: string,
  endDate: string,
  countryCode = "EC"
): Promise<QualitySummaryResponse> {
  const qs = toParams({
    start_date: startDate,
    end_date: endDate,
    country_code: countryCode,
  });
  return apiFetch<QualitySummaryResponse>(`/api/v1/quality/summary${qs}`);
}

// ---------------------------------------------------------------------------
// Reports (download triggers)
// ---------------------------------------------------------------------------

export async function downloadReport(
  format: "excel" | "pdf",
  req: ReportRequest
): Promise<void> {
  const url = `${BASE_URL}/api/v1/reports/${format}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`Report ${format} failed: ${body}`);
  }

  const blob = await res.blob();
  const ext = format === "excel" ? "xlsx" : "pdf";
  const filename = `ennesso_report_${req.start_date}_${req.end_date}.${ext}`;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
