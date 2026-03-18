"""Pydantic response schemas for the Ennesso API v1.

These models define the exact shape of every JSON response body.
They are intentionally separate from the DB models in app/models/
to allow independent evolution of the API contract.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.energy import QualityFlag


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    last_ingestion: datetime | None = None


# ---------------------------------------------------------------------------
# Energy balance
# ---------------------------------------------------------------------------


class DailyBalanceResponse(BaseModel):
    """Aggregated generation by source for one day."""

    date: date
    hydraulic_mwh: float = 0.0
    thermal_mwh: float = 0.0
    solar_mwh: float = 0.0
    wind_mwh: float = 0.0
    biomass_mwh: float = 0.0
    other_mwh: float = 0.0
    total_mwh: float = 0.0


class GenerationDataPoint(BaseModel):
    """Single generation measurement for a given type and day."""

    date: date
    value_mwh: float
    quality_flag: QualityFlag


class EnergyMixResponse(BaseModel):
    """Generation mix percentages for a single day."""

    date: date
    hydraulic_pct: float = Field(ge=0, le=100)
    thermal_pct: float = Field(ge=0, le=100)
    solar_pct: float = Field(ge=0, le=100)
    wind_pct: float = Field(ge=0, le=100)
    biomass_pct: float = Field(ge=0, le=100)
    other_pct: float = Field(ge=0, le=100)
    total_mwh: float


# ---------------------------------------------------------------------------
# Demand
# ---------------------------------------------------------------------------


class DemandDataPoint(BaseModel):
    """Daily demand estimate (sum of all generation as proxy)."""

    date: date
    demand_mwh: float


# ---------------------------------------------------------------------------
# Carbon
# ---------------------------------------------------------------------------


class CarbonDataPoint(BaseModel):
    """Carbon emissions and intensity for one day."""

    date: date
    total_co2_kg: float
    intensity_kg_per_mwh: float
    avoided_co2_kg: float
    renewable_share: float = Field(ge=0, le=1)


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------


class LineageResponse(BaseModel):
    """Full data lineage record for a single energy record."""

    id: UUID
    record_id: UUID
    source_url: str
    ingestion_method: str
    ingested_at: datetime
    raw_value: str | None
    transformed_value: str | None
    quality_flag: QualityFlag
    correction_note: str | None
    corrected_by: str | None
    corrected_at: datetime | None
    pipeline_version: str | None


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------


class QualityErrorSummary(BaseModel):
    """Brief description of a quality error record."""

    record_id: UUID
    record_date: date
    generation_type: str
    quality_notes: str | None


class QualitySummaryResponse(BaseModel):
    """Quality summary for a date range."""

    total_records: int
    ok_count: int
    warning_count: int
    error_count: int
    recent_errors: list[QualityErrorSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportRequest(BaseModel):
    """Request body for report generation endpoints."""

    start_date: date
    end_date: date
    include_lineage: bool = False
