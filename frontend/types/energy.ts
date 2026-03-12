// ---------------------------------------------------------------------------
// Energy generation source types
// ---------------------------------------------------------------------------

export type GenerationSource =
  | "hydraulic"
  | "thermal"
  | "solar"
  | "wind"
  | "biomass"
  | "other";

export interface GenerationRecord {
  id: string;
  timestamp: string; // ISO 8601
  source: GenerationSource;
  plant_name: string;
  country_code: string; // ISO 3166-1 alpha-2, e.g. "EC"
  value_mwh: number;
  unit: "MWh" | "MW";
}

export interface DailyBalance {
  date: string; // YYYY-MM-DD
  country_code: string;
  generation_mwh: number;
  demand_mwh: number;
  balance_mwh: number;
  by_source: Record<GenerationSource, number>;
}

// ---------------------------------------------------------------------------
// API response envelope
// ---------------------------------------------------------------------------

export interface ApiResponse<T> {
  data: T;
  meta: {
    page: number;
    per_page: number;
    total: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
