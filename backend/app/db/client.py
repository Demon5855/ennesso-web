"""Supabase async client — singleton factory.

Usage::

    from app.db.client import get_client

    client = await get_client()
    response = await client.table("energy_records").select("*").execute()
"""

import logging
from typing import Annotated

from fastapi import Depends
from supabase._async.client import AsyncClient
from supabase import acreate_client

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


async def get_client() -> AsyncClient:
    """Return a cached async Supabase client using the service role key.

    Initialises the client on first call and reuses it for subsequent calls.
    This is safe for use in FastAPI dependency injection.

    Returns:
        An authenticated ``AsyncClient`` instance with service role access.
    """
    global _client
    if _client is None:
        logger.info("Initialising Supabase async client")
        _client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


# FastAPI dependency type alias
SupabaseDep = Annotated[AsyncClient, Depends(get_client)]
