/**
 * Ennesso API response types.
 * Mirrors the FastAPI Pydantic schemas from backend/app/models/responses.py
 */

export type QualityFlag = "ok" | "warning" | "error";

export type GenerationType =
  | "hydraulic"
  | "thermal"
  | "solar"
  | "wind"
  | "biomass"
  | "other";

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  version: string;
  last_ingestion: string | null;
}

// ---------------------------------------------------------------------------
// Energy
// ---------------------------------------------------------------------------

export interface DailyBalanceResponse {
  date: string;
  hydraulic_mwh: number;
  thermal_mwh: number;
  solar_mwh: number;
  wind_mwh: number;
  biomass_mwh: number;
  other_mwh: number;
  total_mwh: number;
}

export interface GenerationDataPoint {
  date: string;
  value_mwh: number;
  quality_flag: QualityFlag;
}

export interface EnergyMixResponse {
  date: string;
  hydraulic_pct: number;
  thermal_pct: number;
  solar_pct: number;
  wind_pct: number;
  biomass_pct: number;
  other_pct: number;
  total_mwh: number;
}

export interface DemandDataPoint {
  date: string;
  demand_mwh: number;
}

// ---------------------------------------------------------------------------
// Carbon
// ---------------------------------------------------------------------------

export interface CarbonDataPoint {
  date: string;
  total_co2_kg: number;
  intensity_kg_per_mwh: number;
  avoided_co2_kg: number;
  renewable_share: number;
}

// ---------------------------------------------------------------------------
// Lineage
// ---------------------------------------------------------------------------

export interface LineageResponse {
  id: string;
  record_id: string;
  source_url: string;
  ingestion_method: string;
  ingested_at: string;
  raw_value: string | null;
  transformed_value: string | null;
  quality_flag: QualityFlag;
  correction_note: string | null;
  corrected_by: string | null;
  corrected_at: string | null;
  pipeline_version: string | null;
}

// ---------------------------------------------------------------------------
// Quality
// ---------------------------------------------------------------------------

export interface QualityErrorSummary {
  record_id: string;
  record_date: string;
  generation_type: string;
  quality_notes: string | null;
}

export interface QualitySummaryResponse {
  total_records: number;
  ok_count: number;
  warning_count: number;
  error_count: number;
  recent_errors: QualityErrorSummary[];
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export interface ReportRequest {
  start_date: string;
  end_date: string;
  include_lineage?: boolean;
}
