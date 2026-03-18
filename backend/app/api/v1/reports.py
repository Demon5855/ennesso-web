"""Report generation endpoints — PDF and Excel exports."""

import io
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db.client import SupabaseDep
from app.models.responses import ReportRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_report_request(req: ReportRequest) -> None:
    """Raise HTTPException if the report request is invalid."""
    if req.end_date < req.start_date:
        raise HTTPException(
            status_code=422,
            detail=f"end_date ({req.end_date}) must be >= start_date ({req.start_date}).",
        )
    delta = (req.end_date - req.start_date).days
    if delta > 366:
        raise HTTPException(
            status_code=422,
            detail="Report range cannot exceed 366 days.",
        )


async def _fetch_generation_data(
    client, start_date: date, end_date: date
) -> list[dict]:
    """Fetch aggregated daily generation for report use."""
    response = (
        await client.table("daily_balance")
        .select("record_date, generation_type, total_mwh")
        .eq("country_code", "EC")
        .gte("record_date", start_date.isoformat())
        .lte("record_date", end_date.isoformat())
        .order("record_date")
        .execute()
    )
    return response.data or []


# ---------------------------------------------------------------------------
# POST /reports/excel
# ---------------------------------------------------------------------------


@router.post("/excel")
async def generate_excel_report(
    req: ReportRequest,
    client: SupabaseDep,
) -> StreamingResponse:
    """Generate and stream an Excel report for the given date range.

    Workbook contains:
        - Sheet 1: Daily generation by source (MWh)
        - Sheet 2: Carbon emissions summary

    Args:
        req: Report request with start_date, end_date.

    Returns:
        Streaming .xlsx file download.
    """
    _validate_report_request(req)

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl is not installed. Run: pip install openpyxl",
        )

    rows = await _fetch_generation_data(client, req.start_date, req.end_date)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {req.start_date} to {req.end_date}.",
        )

    from app.services.carbon import calculate_emissions, calculate_avoided_emissions

    # Build daily pivot
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        d = row["record_date"]
        gen_type = row.get("generation_type", "other")
        mwh = float(row.get("total_mwh") or 0)
        if d not in daily:
            daily[d] = {}
        daily[d][gen_type] = daily[d].get(gen_type, 0) + mwh

    wb = openpyxl.Workbook()

    # -- Sheet 1: Generation --
    ws_gen = wb.active
    ws_gen.title = "Generation"

    header_fill = PatternFill("solid", fgColor="1A1D27")
    header_font = Font(bold=True, color="00C2A8")

    headers = ["Date", "Hydraulic (MWh)", "Thermal (MWh)", "Solar (MWh)",
               "Wind (MWh)", "Biomass (MWh)", "Other (MWh)", "Total (MWh)"]
    for col, h in enumerate(headers, 1):
        cell = ws_gen.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    for row_idx, (d, mix) in enumerate(sorted(daily.items()), 2):
        total = sum(mix.values())
        ws_gen.cell(row=row_idx, column=1, value=d)
        ws_gen.cell(row=row_idx, column=2, value=round(mix.get("hydraulic", 0), 2))
        ws_gen.cell(row=row_idx, column=3, value=round(mix.get("thermal", 0), 2))
        ws_gen.cell(row=row_idx, column=4, value=round(mix.get("solar", 0), 2))
        ws_gen.cell(row=row_idx, column=5, value=round(mix.get("wind", 0), 2))
        ws_gen.cell(row=row_idx, column=6, value=round(mix.get("biomass", 0), 2))
        ws_gen.cell(row=row_idx, column=7, value=round(mix.get("other", 0), 2))
        ws_gen.cell(row=row_idx, column=8, value=round(total, 2))

    for col in range(1, 9):
        ws_gen.column_dimensions[
            openpyxl.utils.get_column_letter(col)
        ].width = 18

    # -- Sheet 2: Carbon --
    ws_carbon = wb.create_sheet("Carbon")
    carbon_headers = ["Date", "Total CO₂ (kg)", "Intensity (kg/MWh)", "Avoided CO₂ (kg)"]
    for col, h in enumerate(carbon_headers, 1):
        cell = ws_carbon.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    for row_idx, (d, mix) in enumerate(sorted(daily.items()), 2):
        total_mwh = sum(mix.values())
        co2 = calculate_emissions(mix)
        avoided = calculate_avoided_emissions(mix)
        intensity = co2 / total_mwh if total_mwh > 0 else 0.0
        ws_carbon.cell(row=row_idx, column=1, value=d)
        ws_carbon.cell(row=row_idx, column=2, value=round(co2, 2))
        ws_carbon.cell(row=row_idx, column=3, value=round(intensity, 4))
        ws_carbon.cell(row=row_idx, column=4, value=round(avoided, 2))

    for col in range(1, 5):
        ws_carbon.column_dimensions[
            openpyxl.utils.get_column_letter(col)
        ].width = 20

    # Stream to client
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"ennesso_report_{req.start_date}_{req.end_date}.xlsx"
    return StreamingResponse(
        buffer,
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
    """Generate and stream a PDF summary report.

    Contains: title page, generation table, carbon summary.
    Lineage audit section included if ``include_lineage=True``.

    Args:
        req: Report request with start_date, end_date, include_lineage.

    Returns:
        Streaming .pdf file download.
    """
    _validate_report_request(req)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="reportlab is not installed. Run: pip install reportlab",
        )

    rows = await _fetch_generation_data(client, req.start_date, req.end_date)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {req.start_date} to {req.end_date}.",
        )

    from app.services.carbon import calculate_emissions, calculate_avoided_emissions

    # Build daily pivot
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        d = row["record_date"]
        gen_type = row.get("generation_type", "other")
        mwh = float(row.get("total_mwh") or 0)
        if d not in daily:
            daily[d] = {}
        daily[d][gen_type] = daily[d].get(gen_type, 0) + mwh

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(
        f"<b>Ennesso Energy Report</b>",
        styles["Title"]
    ))
    story.append(Paragraph(
        f"Period: {req.start_date} to {req.end_date} | Country: EC",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    # Generation table
    story.append(Paragraph("<b>Daily Generation (MWh)</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * cm))

    table_data = [["Date", "Hydraulic", "Thermal", "Solar", "Wind", "Total"]]
    for d, mix in sorted(daily.items()):
        total = sum(mix.values())
        table_data.append([
            d,
            f"{mix.get('hydraulic', 0):,.1f}",
            f"{mix.get('thermal', 0):,.1f}",
            f"{mix.get('solar', 0):,.1f}",
            f"{mix.get('wind', 0):,.1f}",
            f"{total:,.1f}",
        ])

    tbl = Table(table_data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1D27")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#00C2A8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Carbon summary
    story.append(Paragraph("<b>Carbon Summary</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * cm))

    total_co2 = sum(calculate_emissions(mix) for mix in daily.values())
    total_avoided = sum(calculate_avoided_emissions(mix) for mix in daily.values())
    total_gen = sum(sum(mix.values()) for mix in daily.values())
    avg_intensity = total_co2 / total_gen if total_gen > 0 else 0.0

    carbon_data = [
        ["Metric", "Value"],
        ["Total CO₂ Emissions", f"{total_co2:,.0f} kg"],
        ["Avg Carbon Intensity", f"{avg_intensity:.2f} kg/MWh"],
        ["Total CO₂ Avoided vs Thermal", f"{total_avoided:,.0f} kg"],
        ["Total Generation", f"{total_gen:,.1f} MWh"],
    ]
    carbon_tbl = Table(carbon_data)
    carbon_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1D27")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#00C2A8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(carbon_tbl)

    doc.build(story)
    buffer.seek(0)

    filename = f"ennesso_report_{req.start_date}_{req.end_date}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
