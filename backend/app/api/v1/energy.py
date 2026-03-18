"""Energy data endpoints — balance, generation, mix, demand."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.client import SupabaseDep
from app.models.energy import GenerationType, QualityFlag
from app.models.responses import (
    DailyBalanceResponse,
    DemandDataPoint,
    EnergyMixResponse,
    GenerationDataPoint,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_date_range(start_date: date, end_date: date) -> None:
    """Raise HTTPException if date range is invalid."""
    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail=f"end_date ({end_date}) must be >= start_date ({start_date}).",
        )
    delta = (end_date - start_date).days
    if delta > 366:
        raise HTTPException(
            status_code=422,
            detail="Date range cannot exceed 366 days. Use smaller intervals.",
        )


def _to_pct(value: float, total: float) -> float:
    """Return percentage rounded to 2 decimal places, or 0 if total is 0."""
    if total <= 0:
        return 0.0
    return round((value / total) * 100, 2)


# ---------------------------------------------------------------------------
# GET /energy/balance
# ---------------------------------------------------------------------------


@router.get("/balance", response_model=list[DailyBalanceResponse])
async def get_energy_balance(
    client: SupabaseDep,
    start_date: date = Query(..., description="Start date (ISO 8601)"),
    end_date: date = Query(..., description="End date (ISO 8601)"),
    country_code: str = Query(default="EC", min_length=2, max_length=2),
) -> list[DailyBalanceResponse]:
    """Return daily generation totals aggregated by source type.

    Queries the ``daily_balance`` view which pre-aggregates
    ``energy_records`` by date and generation type.
    """
    _validate_date_range(start_date, end_date)

    response = (
        await client.table("daily_balance")
        .select("*")
        .eq("country_code", country_code)
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .order("record_date")
        .execute()
    )

    # Pivot: group rows by date, spread generation types into columns
    daily: dict[date, DailyBalanceResponse] = {}

    for row in response.data:
        d = date.fromisoformat(row["record_date"])
        if d not in daily:
            daily[d] = DailyBalanceResponse(date=d)

        gen_type = row.get("generation_type", "other")
        mwh = float(row.get("total_mwh") or 0)

        entry = daily[d]
        if gen_type == "hydraulic":
            entry.hydraulic_mwh += mwh
        elif gen_type == "thermal":
            entry.thermal_mwh += mwh
        elif gen_type == "solar":
            entry.solar_mwh += mwh
        elif gen_type == "wind":
            entry.wind_mwh += mwh
        elif gen_type == "biomass":
            entry.biomass_mwh += mwh
        else:
            entry.other_mwh += mwh

        entry.total_mwh += mwh

    return sorted(daily.values(), key=lambda x: x.date)


# ---------------------------------------------------------------------------
# GET /energy/generation
# ---------------------------------------------------------------------------


@router.get("/generation", response_model=list[GenerationDataPoint])
async def get_generation(
    client: SupabaseDep,
    start_date: date = Query(..., description="Start date (ISO 8601)"),
    end_date: date = Query(..., description="End date (ISO 8601)"),
    generation_type: GenerationType | None = Query(default=None),
    country_code: str = Query(default="EC", min_length=2, max_length=2),
) -> list[GenerationDataPoint]:
    """Return raw generation records for a date range, optionally filtered
    by generation type.
    """
    _validate_date_range(start_date, end_date)

    query = (
        client.table("energy_records")
        .select("record_date, value_mwh, quality_flag")
        .eq("country_code", country_code)
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .order("record_date")
    )

    if generation_type:
        query = query.eq("generation_type", generation_type.value)

    response = await query.execute()

    return [
        GenerationDataPoint(
            date=date.fromisoformat(row["record_date"]),
            value_mwh=float(row.get("value_mwh") or 0),
            quality_flag=QualityFlag(row.get("quality_flag", "ok")),
        )
        for row in response.data
    ]


# ---------------------------------------------------------------------------
# GET /energy/mix
# ---------------------------------------------------------------------------


@router.get("/mix", response_model=EnergyMixResponse)
async def get_energy_mix(
    client: SupabaseDep,
    target_date: date = Query(..., alias="date", description="Single day (ISO 8601)"),
    country_code: str = Query(default="EC", min_length=2, max_length=2),
) -> EnergyMixResponse:
    """Return the generation mix percentages for a single day."""
    response = (
        await client.table("daily_balance")
        .select("generation_type, total_mwh")
        .eq("country_code", country_code)
        .eq("record_date", target_date.isoformat())
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail=f"No generation data found for {target_date} ({country_code}).",
        )

    totals: dict[str, float] = {}
    for row in response.data:
        totals[row["generation_type"]] = float(row.get("total_mwh") or 0)

    total_mwh = sum(totals.values())

    return EnergyMixResponse(
        date=target_date,
        hydraulic_pct=_to_pct(totals.get("hydraulic", 0), total_mwh),
        thermal_pct=_to_pct(totals.get("thermal", 0), total_mwh),
        solar_pct=_to_pct(totals.get("solar", 0), total_mwh),
        wind_pct=_to_pct(totals.get("wind", 0), total_mwh),
        biomass_pct=_to_pct(totals.get("biomass", 0), total_mwh),
        other_pct=_to_pct(totals.get("other", 0), total_mwh),
        total_mwh=total_mwh,
    )


# ---------------------------------------------------------------------------
# GET /energy/demand
# ---------------------------------------------------------------------------


@router.get("/demand", response_model=list[DemandDataPoint])
async def get_demand(
    client: SupabaseDep,
    start_date: date = Query(..., description="Start date (ISO 8601)"),
    end_date: date = Query(..., description="End date (ISO 8601)"),
    country_code: str = Query(default="EC", min_length=2, max_length=2),
) -> list[DemandDataPoint]:
    """Return daily demand estimates.

    Demand is estimated as the sum of all generation types per day
    (supply = demand assumption for a grid-balanced system).
    """
    _validate_date_range(start_date, end_date)

    response = (
        await client.table("daily_balance")
        .select("record_date, total_mwh")
        .eq("country_code", country_code)
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .order("record_date")
        .execute()
    )

    # Aggregate all generation types into a single daily demand value
    daily_demand: dict[date, float] = {}
    for row in response.data:
        d = date.fromisoformat(row["record_date"])
        daily_demand[d] = daily_demand.get(d, 0.0) + float(row.get("total_mwh") or 0)

    return [
        DemandDataPoint(date=d, demand_mwh=mwh)
        for d, mwh in sorted(daily_demand.items())
    ]
