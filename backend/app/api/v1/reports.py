"""Report generation endpoints — PDF and Excel exports.

Wires the pdf_report.py and excel_report.py exporters to the FastAPI layer.
Both endpoints fetch data from Supabase, build the report, and stream it.
"""

import io
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db.client import SupabaseDep
from app.models.responses import ReportRequest
from app.services.carbon import (
    calculate_avoided_emissions,
    calculate_emissions,
)
from app.services.indicators import calculate_renewable_share

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Shared data fetch helper
# ---------------------------------------------------------------------------


async def _fetch_report_data(
    client,
    start_date: date,
    end_date: date,
) -> tuple[list[dict], list[dict], dict[str, float]]:
    """Fetch energy records, lineage, and build generation_by_type pivot.

    Returns:
        Tuple of (energy_records, lineage_records, generation_by_type).
    """
    energy_resp = (
        await client.table("energy_records")
        .select("*")
        .eq("country_code", "EC")
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .order("record_date")
        .execute()
    )
    energy_records = energy_resp.data or []

    # Build generation pivot
    generation_by_type: dict[str, float] = {}
    for row in energy_records:
        gen_type = row.get("generation_type", "other")
        mwh = float(row.get("value_mwh") or 0)
        generation_by_type[gen_type] = generation_by_type.get(gen_type, 0) + mwh

    # Fetch lineage for these record IDs
    record_ids = [str(r["id"]) for r in energy_records]
    lineage_records: list[dict] = []
    if record_ids:
        # Batch fetch in chunks of 100 (Supabase in() limit)
        for i in range(0, len(record_ids), 100):
            chunk = record_ids[i : i + 100]
            lineage_resp = (
                await client.table("data_lineage")
                .select("*")
                .in_("record_id", chunk)
                .execute()
            )
            lineage_records.extend(lineage_resp.data or [])

    return energy_records, lineage_records, generation_by_type


def _validate_request(req: ReportRequest) -> None:
    if req.end_date < req.start_date:
        raise HTTPException(
            status_code=422,
            detail=f"end_date ({req.end_date}) must be >= start_date ({req.start_date}).",
        )
    if (req.end_date - req.start_date).days > 366:
        raise HTTPException(
            status_code=422,
            detail="Report range cannot exceed 366 days.",
        )


# ---------------------------------------------------------------------------
# POST /reports/excel
# ---------------------------------------------------------------------------


@router.post("/excel")
async def generate_excel_report(
    req: ReportRequest,
    client: SupabaseDep,
) -> StreamingResponse:
    """Generate and stream an Excel report (.xlsx).

    Sheet 1: Summary metrics + generation by source.
    Sheet 2: Raw energy_records for the period.
    Sheet 3: Matching data_lineage records.
    """
    _validate_request(req)

    energy_records, lineage_records, generation_by_type = (
        await _fetch_report_data(client, req.start_date, req.end_date)
    )

    if not energy_records:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {req.start_date} to {req.end_date}.",
        )

    total_mwh = sum(generation_by_type.values())
    total_co2 = calculate_emissions(generation_by_type)
    avoided = calculate_avoided_emissions(generation_by_type)
    intensity = total_co2 / total_mwh if total_mwh > 0 else 0.0
    try:
        renewable_share = calculate_renewable_share(generation_by_type)
    except ValueError:
        renewable_share = 0.0

    from app.exporters.excel_report import generate_excel

    xlsx_bytes = generate_excel(
        start_date=req.start_date,
        end_date=req.end_date,
        energy_records=energy_records,
        lineage_records=lineage_records,
        generation_by_type=generation_by_type,
        metrics_summary={
            "total_mwh": total_mwh,
            "renewable_share": renewable_share,
            "total_co2_kg": total_co2,
            "avoided_co2_kg": avoided,
            "avg_intensity": intensity,
        },
    )

    filename = f"ennesso_report_{req.start_date}_{req.end_date}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# POST /reports/pdf
# ---------------------------------------------------------------------------


@router.post("/pdf")
async def generate_pdf_report(
    req: ReportRequest,
    client: SupabaseDep,
) -> StreamingResponse:
    """Generate and stream a PDF report.

    Sections: header, Claude narrative, summary table,
    generation mix chart, data quality, footer.
    """
    _validate_request(req)

    energy_records, _, generation_by_type = (
        await _fetch_report_data(client, req.start_date, req.end_date)
    )

    if not energy_records:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {req.start_date} to {req.end_date}.",
        )

    total_mwh = sum(generation_by_type.values())
    total_co2 = calculate_emissions(generation_by_type)
    avoided = calculate_avoided_emissions(generation_by_type)
    intensity = total_co2 / total_mwh if total_mwh > 0 else 0.0
    try:
        renewable_share = calculate_renewable_share(generation_by_type)
    except ValueError:
        renewable_share = 0.0

    hydraulic_mwh = generation_by_type.get("hydraulic", 0.0)
    thermal_mwh = generation_by_type.get("thermal", 0.0)

    ok_count = sum(1 for r in energy_records if r.get("quality_flag") == "ok")
    warning_count = sum(1 for r in energy_records if r.get("quality_flag") == "warning")
    error_count = sum(1 for r in energy_records if r.get("quality_flag") == "error")

    from app.services.claude_reports import ReportMetrics
    from app.exporters.pdf_report import generate_pdf

    metrics = ReportMetrics(
        start_date=req.start_date.isoformat(),
        end_date=req.end_date.isoformat(),
        total_mwh=total_mwh,
        hydraulic_mwh=hydraulic_mwh,
        thermal_mwh=thermal_mwh,
        renewable_share=renewable_share,
        total_co2_kg=total_co2,
        avoided_co2_kg=avoided,
        avg_intensity_kg_per_mwh=intensity,
        ok_count=ok_count,
        warning_count=warning_count,
        error_count=error_count,
    )

    pdf_bytes = await generate_pdf(
        start_date=req.start_date,
        end_date=req.end_date,
        generation_by_type=generation_by_type,
        metrics=metrics,
    )

    filename = f"ennesso_report_{req.start_date}_{req.end_date}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
