"""CENACE data ingestion pipeline.

Fetches generation dispatch data from CENACE's CKAN open data portal
and XHR endpoints, normalises it, and upserts into Supabase.

Design principles:
- Never DELETE records; deactivate with is_active=False.
- Always upsert on (timestamp, plant_name, country_code) composite key.
- country_code is always "EC" for Ecuador.
"""

import logging
from datetime import date, timedelta

import httpx

from app.config import settings
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)


class CenacePipeline:
    """Orchestrates fetch → normalise → upsert for CENACE generation data."""

    def __init__(self) -> None:
        self.ckan_base = str(settings.cenace_ckan_base_url)
        self.xhr_base = str(settings.cenace_xhr_base_url)
        self.resource_id = settings.cenace_generation_resource_id
        self.country_code = "EC"

    async def run(self, target_date: date | None = None) -> int:
        """
        Execute the full ingestion cycle for a given date.

        Args:
            target_date: Date to ingest; defaults to yesterday.

        Returns:
            Number of records upserted.
        """
        target = target_date or date.today() - timedelta(days=1)
        logger.info("Starting CENACE ingestion for %s", target)

        raw_records = await self._fetch(target)
        normalised = self._normalise(raw_records)
        count = await self._upsert(normalised)

        logger.info("Ingested %d records for %s", count, target)
        return count

    async def _fetch(self, target: date) -> list[dict]:  # type: ignore[type-arg]
        """Fetch raw records from CENACE CKAN API."""
        # TODO: implement CKAN datastore_search query
        async with httpx.AsyncClient(timeout=30) as client:
            _ = client  # remove when implemented
        raise NotImplementedError

    def _normalise(self, raw: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Map raw CENACE fields to GenerationRecord schema."""
        # TODO: map plant codes → GenerationSource enum
        raise NotImplementedError

    async def _upsert(self, records: list[dict]) -> int:  # type: ignore[type-arg]
        """Upsert records into Supabase generation_records table."""
        # TODO: batch upsert with on_conflict strategy
        _ = await get_supabase()
        raise NotImplementedError
