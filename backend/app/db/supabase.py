"""Supabase client factory for backend use."""

from functools import lru_cache

from supabase import AsyncClient, acreate_client

from app.config import settings


@lru_cache
async def get_supabase() -> AsyncClient:
    """Return a cached async Supabase client using the service role key."""
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
