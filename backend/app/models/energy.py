"""Pydantic models for energy generation records.

These models mirror the ``energy_records`` Supabase table and are used for
API I/O validation, pipeline ingestion, and DB query results.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GenerationType(StrEnum):
    """Generation source type — maps to the ``generation_type`` column."""

    HYDRAULIC = "hydraulic"
    THERMAL = "thermal"
    SOLAR = "solar"
    WIND = "wind"
    BIOMASS = "biomass"
    OTHER = "other"


class DataSource(StrEnum):
    """Upstream data provider — maps to the ``source`` column."""

    CENACE_CKAN = "cenace_ckan"
    CENACE_XHR = "cenace_xhr"
    ARCERNNR = "arcernnr"


class QualityFlag(StrEnum):
    """Data quality classification — maps to the ``quality_flag`` column."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class EnergyRecordBase(BaseModel):
    """Shared fields for energy record read and write models."""

    source: DataSource
    country_code: str = Field(
        default="EC",
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code.",
    )
    record_date: date
    generation_type: GenerationType
    value_mwh: float | None = Field(default=None, ge=0)
    quality_flag: QualityFlag = QualityFlag.OK
    quality_notes: str | None = None

    @field_validator("country_code")
    @classmethod
    def uppercase_country_code(cls, v: str) -> str:
        """Ensure country code is always uppercase."""
        return v.upper()


class EnergyRecordCreate(EnergyRecordBase):
    """Input model for inserting a new energy record.

    Used by pipeline code to create records before persisting to Supabase.
    """

    pass


class EnergyRecord(EnergyRecordBase):
    """Full energy record as returned from the database.

    Includes server-generated fields: ``id`` and ``created_at``.
    """

    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class EnergyBalanceSummary(BaseModel):
    """Aggregated daily generation balance — produced by the ``daily_balance`` view."""

    country_code: str
    record_date: date
    generation_type: GenerationType
    total_mwh: float
    record_count: int
    ok_count: int
    warning_count: int
    error_count: int
