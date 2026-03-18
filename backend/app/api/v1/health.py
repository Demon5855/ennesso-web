"""Health check endpoint."""

from fastapi import APIRouter

from app.models.responses import HealthResponse

router = APIRouter()

# Stores timestamp of last successful ingestion — updated by ETL orchestrator
_last_ingestion: None = None


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health_check() -> HealthResponse:
    """Liveness probe for Railway / load balancers.

    Returns application status, version, and timestamp of the last
    successful ingestion cycle.
    """
    return HealthResponse(
        status="ok",
        version="0.1.0",
        last_ingestion=_last_ingestion,
    )
