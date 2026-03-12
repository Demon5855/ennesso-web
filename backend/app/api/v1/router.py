"""API v1 router — aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import generation, balance, export

api_router = APIRouter()

api_router.include_router(
    generation.router,
    prefix="/generation",
    tags=["generation"],
)
api_router.include_router(
    balance.router,
    prefix="/balance",
    tags=["balance"],
)
api_router.include_router(
    export.router,
    prefix="/export",
    tags=["export"],
)
