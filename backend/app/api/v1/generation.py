"""Generation data endpoints."""

from fastapi import APIRouter, Query
from datetime import date

from app.models.generation import GenerationRecord, GenerationSource

router = APIRouter()


@router.get("/", response_model=list[GenerationRecord])
async def list_generation(
    country_code: str = Query(default="EC", min_length=2, max_length=2),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    source: GenerationSource | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=1000),
) -> list[GenerationRecord]:
    """
    Return paginated generation records.

    TODO: implement Supabase query via GenerationService.
    """
    raise NotImplementedError


@router.get("/summary")
async def generation_summary(
    country_code: str = Query(default="EC"),
    date: date | None = Query(default=None),
) -> dict[str, float]:
    """
    Return total generation by source for a given date.

    TODO: implement aggregation query.
    """
    raise NotImplementedError
