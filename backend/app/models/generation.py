"""Pydantic models for generation domain."""

from enum import StrEnum
from datetime import datetime

from pydantic import BaseModel, Field


class GenerationSource(StrEnum):
    HYDRAULIC = "hydraulic"
    THERMAL = "thermal"
    SOLAR = "solar"
    WIND = "wind"
    BIOMASS = "biomass"
    OTHER = "other"


class GenerationRecord(BaseModel):
    id: str
    timestamp: datetime
    source: GenerationSource
    plant_name: str
    country_code: str = Field(
        min_length=2, max_length=2, description="ISO 3166-1 alpha-2"
    )
    value_mwh: float = Field(ge=0)
    unit: str = "MWh"

    model_config = {"from_attributes": True}
