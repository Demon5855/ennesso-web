"""Data quality endpoints."""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.db.client import SupabaseDep
from app.models.responses import QualityErrorSummary, QualitySummaryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", response_model=QualitySummaryResponse)
async def get_quality_summary(
    client: SupabaseDep,
    start_date: date = Query(..., description="Start date (ISO 8601)"),
    end_date: date = Query(..., description="End date (ISO 8601)"),
    country_code: str = Query(default="EC", min_length=2, max_length=2),
) -> QualitySummaryResponse:
    """Return a quality summary for a date range.

    Counts records by quality flag and lists the most recent errors
    (up to 10) for investigation.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail=f"end_date ({end_date}) must be >= start_date ({start_date}).",
        )

    # Fetch all records in range
    response = (
        await client.table("energy_records")
        .select("id, record_date, generation_type, quality_flag, quality_notes")
        .eq("country_code", country_code)
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .execute()
    )

    rows = response.data or []

    ok_count = sum(1 for r in rows if r.get("quality_flag") == "ok")
    warning_count = sum(1 for r in rows if r.get("quality_flag") == "warning")
    error_count = sum(1 for r in rows if r.get("quality_flag") == "error")

    # Collect up to 10 most recent errors
    error_rows = [r for r in rows if r.get("quality_flag") == "error"]
    error_rows.sort(key=lambda r: r.get("record_date", ""), reverse=True)

    recent_errors = [
        QualityErrorSummary(
            record_id=r["id"],
            record_date=date.fromisoformat(r["record_date"]),
            generation_type=r.get("generation_type", ""),
            quality_notes=r.get("quality_notes"),
        )
        for r in error_rows[:10]
    ]

    return QualitySummaryResponse(
        total_records=len(rows),
        ok_count=ok_count,
        warning_count=warning_count,
        error_count=error_count,
        recent_errors=recent_errors,
    )
