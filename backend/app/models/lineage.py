"""Pydantic models for data lineage records.

These models mirror the ``data_lineage`` Supabase table and are used to track
the full provenance of each energy record from ingestion through transformation.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.energy import QualityFlag


class IngestionMethod(StrEnum):
    """How the raw data was acquired — maps to ``ingestion_method`` column."""

    CKAN_API = "ckan_api"
    CENACE_XHR = "cenace_xhr"
    ARCERNNR_EXCEL = "arcernnr_excel"
    ARCERNNR_PDF = "arcernnr_pdf"


class DataLineageBase(BaseModel):
    """Shared fields for lineage read and write models."""

    record_id: UUID = Field(description="FK to energy_records.id")
    source_url: str = Field(min_length=1, description="URL the data was fetched from.")
    ingestion_method: IngestionMethod
    raw_value: str | None = Field(
        default=None,
        description="Original value as it appeared in the source.",
    )
    transformed_value: str | None = Field(
        default=None,
        description="Value after normalisation / unit conversion.",
    )
    quality_flag: QualityFlag = QualityFlag.OK
    correction_note: str | None = None
    corrected_by: str | None = None
    corrected_at: datetime | None = None
    pipeline_version: str | None = None


class DataLineageCreate(DataLineageBase):
    """Input model for inserting a new lineage record.

    Created automatically by the ingestion pipeline alongside each
    ``EnergyRecordCreate``.
    """

    pass


class DataLineage(DataLineageBase):
    """Full lineage record as returned from the database."""

    id: UUID
    ingested_at: datetime

    model_config = {"from_attributes": True}
