"""API v1 router — aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import carbon, energy, health, lineage, quality, reports

api_router = APIRouter()

api_router.include_router(health.router, tags=["ops"])
api_router.include_router(energy.router, prefix="/energy", tags=["energy"])
api_router.include_router(carbon.router, prefix="/energy/carbon", tags=["carbon"])
api_router.include_router(lineage.router, prefix="/lineage", tags=["lineage"])
api_router.include_router(quality.router, prefix="/quality", tags=["quality"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
