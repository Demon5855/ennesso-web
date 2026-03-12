"""Pydantic models for installed generation capacity."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.energy import DataSource, GenerationType


class InstalledCapacityBase(BaseModel):
    country_code: str = Field(default="EC", min_length=2, max_length=2)
    generation_type: GenerationType
    capacity_mw: float = Field(ge=0)
    effective_date: date
    source: DataSource
    notes: str | None = None


class InstalledCapacityCreate(InstalledCapacityBase):
    pass


class InstalledCapacity(InstalledCapacityBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}