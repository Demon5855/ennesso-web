"""Carbon emissions endpoints."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.client import SupabaseDep
from app.models.responses import CarbonDataPoint
from app.services.carbon import (
    calculate_avoided_emissions,
    calculate_carbon_intensity,
    calculate_emissions,
)
from app.services.indicators import calculate_renewable_share

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[CarbonDataPoint])
async def get_carbon(
    client: SupabaseDep,
    start_date: date = Query(..., description="Start date (ISO 8601)"),
    end_date: date = Query(..., description="End date (ISO 8601)"),
    country_code: str = Query(default="EC", min_length=2, max_length=2),
) -> list[CarbonDataPoint]:
    """Return daily carbon emissions, intensity, avoided CO₂, and renewable share.

    Uses IPCC AR5 lifecycle emission factors applied to the daily generation
    mix from ``energy_records``.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail=f"end_date ({end_date}) must be >= start_date ({start_date}).",
        )

    response = (
        await client.table("daily_balance")
        .select("record_date, generation_type, total_mwh")
        .eq("country_code", country_code)
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .order("record_date")
        .execute()
    )

    if not response.data:
        return []

    # Group by date → dict[generation_type → mwh]
    by_date: dict[date, dict[str, float]] = {}
    for row in response.data:
        d = date.fromisoformat(row["record_date"])
        if d not in by_date:
            by_date[d] = {}
        gen_type = row.get("generation_type", "other")
        by_date[d][gen_type] = float(row.get("total_mwh") or 0)

    results: list[CarbonDataPoint] = []

    for d, mix in sorted(by_date.items()):
        total_mwh = sum(mix.values())
        total_co2 = calculate_emissions(mix)
        avoided = calculate_avoided_emissions(mix)

        try:
            intensity = calculate_carbon_intensity(total_mwh, total_co2)
        except ValueError:
            intensity = 0.0

        try:
            renewable_share = calculate_renewable_share(mix)
        except ValueError:
            renewable_share = 0.0

        results.append(
            CarbonDataPoint(
                date=d,
                total_co2_kg=round(total_co2, 2),
                intensity_kg_per_mwh=round(intensity, 4),
                avoided_co2_kg=round(avoided, 2),
                renewable_share=round(renewable_share, 4),
            )
        )

    return results
