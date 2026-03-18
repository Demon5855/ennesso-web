"""Ennesso backend — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.pipelines.scheduler import create_scheduler
from app.models.ingest import IngestSummary


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: start scheduler on startup, shut down cleanly."""
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Ennesso API",
    description=(
        "Energy data governance and balance API for Ecuador's electricity system. "
        "Provides generation, carbon, lineage, and quality endpoints."
    ),
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.post("/api/v1/ingest/trigger", response_model=IngestSummary, tags=["ops"])
async def trigger_ingestion(background_tasks: BackgroundTasks) -> dict:
    """Manually trigger a full ingestion cycle (dev / backfill use only).

    Runs pipelines in the background — returns immediately.
    Check logs for results.
    """
    from app.services.etl import run_full_ingestion
    background_tasks.add_task(run_full_ingestion)
    return {"status": "ingestion triggered", "env": settings.app_env}
