"""Supabase async client — singleton factory."""

import logging
from typing import Annotated

from fastapi import Depends
from supabase._async.client import AsyncClient
from supabase import acreate_client

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


async def get_client() -> AsyncClient:
    """Return a cached async Supabase client using the service role key."""
    global _client
    if _client is None:
        logger.info("Initialising Supabase async client")
        _client = await acreate_client(
            str(settings.supabase_url),
            settings.supabase_service_role_key,
        )
    return _client


SupabaseDep = Annotated[AsyncClient, Depends(get_client)]