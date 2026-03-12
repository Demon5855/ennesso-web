"""Pydantic models for system balance domain."""

from datetime import date

from pydantic import BaseModel, Field

from app.models.generation import GenerationSource


class DailyBalance(BaseModel):
    date: date
    country_code: str = Field(min_length=2, max_length=2)
    generation_mwh: float = Field(ge=0)
    demand_mwh: float = Field(ge=0)
    balance_mwh: float  # can be negative (deficit)
    by_source: dict[GenerationSource, float]

    model_config = {"from_attributes": True}
