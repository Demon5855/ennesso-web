"""Data export endpoints (Excel / PDF / CSV)."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from datetime import date
from typing import Literal

router = APIRouter()

ExportFormat = Literal["csv", "xlsx", "pdf"]


@router.get("/{format}")
async def export_data(
    format: ExportFormat,
    country_code: str = Query(default="EC"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> StreamingResponse:
    """
    Stream a data export in the requested format.

    TODO: implement ExcelExporter / PDFExporter via exporters module.
    """
    raise NotImplementedError
