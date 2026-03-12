"""System balance endpoints."""

from fastapi import APIRouter, Query
from datetime import date

from app.models.balance import DailyBalance

router = APIRouter()


@router.get("/daily", response_model=list[DailyBalance])
async def daily_balance(
    country_code: str = Query(default="EC"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[DailyBalance]:
    """
    Return daily generation vs demand balance.

    TODO: implement service layer query.
    """
    raise NotImplementedError
