"""Data lineage endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db.client import SupabaseDep
from app.models.responses import LineageResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{record_id}", response_model=list[LineageResponse])
async def get_lineage(
    record_id: UUID,
    client: SupabaseDep,
) -> list[LineageResponse]:
    """Return all lineage entries for a given energy record.

    Provides full audit trail: source URL, ingestion method, raw and
    transformed values, quality flag, and pipeline version.
    """
    response = (
        await client.table("data_lineage")
        .select("*")
        .eq("record_id", str(record_id))
        .order("ingested_at")
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail=f"No lineage records found for record_id={record_id}.",
        )

    return [LineageResponse(**row) for row in response.data]
