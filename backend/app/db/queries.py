"""Database query functions for Ennesso data layer.

All functions accept an ``AsyncClient`` instance so they can be used both
inside FastAPI routes (via DI) and in pipeline code (direct calls).

Conventions:
    - Never DELETE rows. Deactivate or flag with quality_flag='error'.
    - Upsert on natural keys to ensure idempotent pipeline runs.
    - Return typed Pydantic models, never raw dicts.
"""

import logging
from datetime import date
from uuid import UUID

from supabase._async.client import AsyncClient

from app.models.energy import (
    EnergyBalanceSummary,
    EnergyRecord,
    EnergyRecordCreate,
    GenerationType,
    QualityFlag,
)
from app.models.lineage import DataLineage, DataLineageCreate

logger = logging.getLogger(__name__)


async def insert_energy_record(
    client: AsyncClient,
    record: EnergyRecordCreate,
) -> EnergyRecord:
    """Insert a new energy record and return the persisted row.

    Args:
        client: Authenticated Supabase async client.
        record: Validated energy record to insert.

    Returns:
        The inserted ``EnergyRecord`` including server-generated ``id``
        and ``created_at``.

    Raises:
        RuntimeError: If the Supabase insert returns no data.
    """
    payload = record.model_dump(mode="json")
    response = (
        await client.table("energy_records")
        .insert(payload)
        .execute()
    )
    if not response.data:
        raise RuntimeError(f"Insert returned no data: {response}")

    logger.debug("Inserted energy_record id=%s", response.data[0]["id"])
    return EnergyRecord.model_validate(response.data[0])


async def insert_lineage(
    client: AsyncClient,
    lineage: DataLineageCreate,
) -> DataLineage:
    """Insert a data lineage record linked to an energy record.

    Args:
        client: Authenticated Supabase async client.
        lineage: Lineage record to insert.

    Returns:
        The inserted ``DataLineage`` including server-generated fields.

    Raises:
        RuntimeError: If the Supabase insert returns no data.
    """
    payload = lineage.model_dump(mode="json")
    response = (
        await client.table("data_lineage")
        .insert(payload)
        .execute()
    )
    if not response.data:
        raise RuntimeError(f"Lineage insert returned no data: {response}")

    return DataLineage.model_validate(response.data[0])


async def get_energy_balance(
    client: AsyncClient,
    country_code: str = "EC",
    date_from: date | None = None,
    date_to: date | None = None,
    generation_type: GenerationType | None = None,
) -> list[EnergyBalanceSummary]:
    """Return aggregated daily generation balance from the ``daily_balance`` view.

    Args:
        client: Authenticated Supabase async client.
        country_code: ISO 3166-1 alpha-2 country code to filter by.
        date_from: Inclusive start date filter.
        date_to: Inclusive end date filter.
        generation_type: Optional filter to a specific generation type.

    Returns:
        List of ``EnergyBalanceSummary`` rows ordered by ``record_date`` ASC.
    """
    query = (
        client.table("daily_balance")
        .select("*")
        .eq("country_code", country_code)
        .order("record_date")
    )

    if date_from:
        query = query.gte("record_date", date_from.isoformat())
    if date_to:
        query = query.lte("record_date", date_to.isoformat())
    if generation_type:
        query = query.eq("generation_type", generation_type.value)

    response = await query.execute()
    return [EnergyBalanceSummary.model_validate(row) for row in response.data]


async def get_lineage_for_record(
    client: AsyncClient,
    record_id: UUID,
) -> list[DataLineage]:
    """Return all lineage entries for a given energy record.

    Args:
        client: Authenticated Supabase async client.
        record_id: UUID of the parent ``energy_records`` row.

    Returns:
        List of ``DataLineage`` entries ordered by ``ingested_at`` ASC.
    """
    response = (
        await client.table("data_lineage")
        .select("*")
        .eq("record_id", str(record_id))
        .order("ingested_at")
        .execute()
    )
    return [DataLineage.model_validate(row) for row in response.data]


async def get_quality_summary(
    client: AsyncClient,
    country_code: str = "EC",
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[QualityFlag, int]:
    """Return count of records by quality flag for a date range.

    Args:
        client: Authenticated Supabase async client.
        country_code: ISO 3166-1 alpha-2 country code to filter by.
        date_from: Inclusive start date filter.
        date_to: Inclusive end date filter.

    Returns:
        Dict mapping each ``QualityFlag`` to its record count.
    """
    query = (
        client.table("energy_records")
        .select("quality_flag")
        .eq("country_code", country_code)
    )
    if date_from:
        query = query.gte("record_date", date_from.isoformat())
    if date_to:
        query = query.lte("record_date", date_to.isoformat())

    response = await query.execute()

    summary: dict[QualityFlag, int] = {flag: 0 for flag in QualityFlag}
    for row in response.data:
        flag = QualityFlag(row["quality_flag"])
        summary[flag] += 1

    return summary
