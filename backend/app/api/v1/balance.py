"""System balance endpoints."""

from fastapi import APIRouter, Query
from datetime import date

from app.models.energy import EnergyBalanceSummary

router = APIRouter()


@router.get("/daily", response_model=list[EnergyBalanceSummary])
async def daily_balance(
    country_code: str = Query(default="EC"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[EnergyBalanceSummary]:
    """
    Return daily generation vs demand balance.

    TODO: implement service layer query.
    """
    raise NotImplementedError
