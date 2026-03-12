"""Ennesso backend — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    # TODO: initialise DB connection pool
    # TODO: start APScheduler ingestion jobs
    yield
    # TODO: shutdown scheduler and close connections


app = FastAPI(
    title="Ennesso API",
    description="Energy data governance and balance API for Ecuador's electricity system.",
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


@app.get("/health", tags=["ops"])
async def health_check() -> dict[str, str]:
    """Liveness probe for Railway / load balancers."""
    return {"status": "ok", "env": settings.app_env}
