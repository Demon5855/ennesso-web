"""Excel report exporter for Ennesso energy balance reports.

Uses openpyxl to generate a workbook with three sheets:
    Sheet 1 "Summary"  — key metrics with Ennesso formatting
    Sheet 2 "Raw Data" — all energy_records for the date range
    Sheet 3 "Lineage"  — matching data_lineage records

All column widths are auto-fitted to content.
"""

import io
import logging
from datetime import date

logger = logging.getLogger(__name__)


def _auto_width(ws, min_width: int = 10, max_width: int = 50) -> None:
    """Set column widths based on maximum cell content length.

    Args:
        ws: openpyxl worksheet.
        min_width: Minimum column width in characters.
        max_width: Maximum column width in characters.
    """
    from openpyxl.utils import get_column_letter

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(
            max(max_len + 2, min_width), max_width
        )


def _apply_header_style(cell, fill_color: str = "00C2A8") -> None:
    """Apply Ennesso header styling to a cell.

    Args:
        cell: openpyxl cell object.
        fill_color: Hex fill color without '#'.
    """
    from openpyxl.styles import Font, PatternFill, Alignment

    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = PatternFill("solid", fgColor=fill_color)
    cell.alignment = Alignment(horizontal="left", vertical="center")


def _apply_row_style(cell, row_idx: int) -> None:
    """Apply alternating row fill for readability.

    Args:
        cell: openpyxl cell object.
        row_idx: 1-based row index.
    """
    from openpyxl.styles import PatternFill, Font, Alignment

    color = "F9F9F9" if row_idx % 2 == 0 else "FFFFFF"
    cell.fill = PatternFill("solid", fgColor=color)
    cell.font = Font(color="1A1A1A", size=9)
    cell.alignment = Alignment(vertical="center")


def generate_excel(
    start_date: date,
    end_date: date,
    energy_records: list[dict],
    lineage_records: list[dict],
    generation_by_type: dict[str, float],
    metrics_summary: dict[str, float],
) -> bytes:
    """Generate a 3-sheet Excel workbook.

    Args:
        start_date: Report period start.
        end_date: Report period end.
        energy_records: Raw rows from energy_records table.
        lineage_records: Raw rows from data_lineage table.
        generation_by_type: Aggregated MWh by generation type.
        metrics_summary: Dict with keys: total_mwh, renewable_share,
            total_co2_kg, avoided_co2_kg, avg_intensity.

    Returns:
        Excel workbook as bytes (.xlsx).
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError as exc:
        raise RuntimeError("openpyxl is not installed") from exc

    wb = openpyxl.Workbook()

    # -------------------------------------------------------------------------
    # Sheet 1: Summary
    # -------------------------------------------------------------------------
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.sheet_properties.tabColor = "00C2A8"

    # Title block
    ws_summary["A1"] = "Ennesso — Energy Balance Report"
    ws_summary["A1"].font = Font(bold=True, color="00C2A8", size=14)
    ws_summary["A2"] = f"Period: {start_date} — {end_date}"
    ws_summary["A2"].font = Font(color="6B7280", size=9)
    ws_summary["A3"] = "Data source: CENACE / ARCERNNR"
    ws_summary["A3"].font = Font(color="6B7280", size=9)

    # Key metrics table
    headers = ["Metric", "Value", "Unit", "Notes"]
    for col, h in enumerate(headers, 1):
        cell = ws_summary.cell(row=5, column=col, value=h)
        _apply_header_style(cell)

    metric_rows = [
        ("Total Generation",
         round(metrics_summary.get("total_mwh", 0) / 1000, 2),
         "GWh",
         f"{start_date} to {end_date}"),
        ("Renewable Share",
         round(metrics_summary.get("renewable_share", 0) * 100, 2),
         "%",
         "Hydraulic + Solar + Wind + Biomass"),
        ("Total CO₂ Emissions",
         round(metrics_summary.get("total_co2_kg", 0) / 1000, 0),
         "t CO₂",
         "IPCC AR5 lifecycle factors"),
        ("CO₂ Avoided",
         round(metrics_summary.get("avoided_co2_kg", 0) / 1000, 0),
         "t CO₂",
         "vs 100% thermal baseline"),
        ("Avg Carbon Intensity",
         round(metrics_summary.get("avg_intensity", 0), 2),
         "kg/MWh",
         "Average across mix"),
    ]

    for row_idx, row_data in enumerate(metric_rows, 6):
        for col, value in enumerate(row_data, 1):
            cell = ws_summary.cell(row=row_idx, column=col, value=value)
            _apply_row_style(cell, row_idx)

    # Generation by type sub-table
    ws_summary.cell(row=12, column=1, value="Generation by Source").font = Font(
        bold=True, color="00C2A8", size=10
    )
    type_headers = ["Source", "MWh", "GWh", "Share %"]
    for col, h in enumerate(type_headers, 1):
        cell = ws_summary.cell(row=13, column=col, value=h)
        _apply_header_style(cell)

    total_mwh = sum(generation_by_type.values())
    for row_idx, (source, mwh) in enumerate(generation_by_type.items(), 14):
        share = (mwh / total_mwh * 100) if total_mwh > 0 else 0
        row_data = [source.title(), round(mwh, 2), round(mwh / 1000, 2), round(share, 1)]
        for col, value in enumerate(row_data, 1):
            cell = ws_summary.cell(row=row_idx, column=col, value=value)
            _apply_row_style(cell, row_idx)

    _auto_width(ws_summary)

    # -------------------------------------------------------------------------
    # Sheet 2: Raw Data
    # -------------------------------------------------------------------------
    ws_raw = wb.create_sheet("Raw Data")

    raw_headers = [
        "id", "record_date", "generation_type", "source",
        "country_code", "value_mwh", "quality_flag", "quality_notes",
        "created_at",
    ]
    for col, h in enumerate(raw_headers, 1):
        cell = ws_raw.cell(row=1, column=col, value=h)
        _apply_header_style(cell)

    for row_idx, record in enumerate(energy_records, 2):
        row_data = [
            str(record.get("id", "")),
            record.get("record_date", ""),
            record.get("generation_type", ""),
            record.get("source", ""),
            record.get("country_code", ""),
            record.get("value_mwh"),
            record.get("quality_flag", ""),
            record.get("quality_notes", ""),
            record.get("created_at", ""),
        ]
        for col, value in enumerate(row_data, 1):
            cell = ws_raw.cell(row=row_idx, column=col, value=value)
            _apply_row_style(cell, row_idx)

    ws_raw.auto_filter.ref = f"A1:{chr(64 + len(raw_headers))}1"
    _auto_width(ws_raw)

    # -------------------------------------------------------------------------
    # Sheet 3: Lineage
    # -------------------------------------------------------------------------
    ws_lineage = wb.create_sheet("Lineage")

    lineage_headers = [
        "id", "record_id", "source_url", "ingestion_method",
        "ingested_at", "raw_value", "transformed_value",
        "quality_flag", "correction_note", "pipeline_version",
    ]
    for col, h in enumerate(lineage_headers, 1):
        cell = ws_lineage.cell(row=1, column=col, value=h)
        _apply_header_style(cell)

    for row_idx, record in enumerate(lineage_records, 2):
        row_data = [
            str(record.get("id", "")),
            str(record.get("record_id", "")),
            record.get("source_url", ""),
            record.get("ingestion_method", ""),
            record.get("ingested_at", ""),
            record.get("raw_value", ""),
            record.get("transformed_value", ""),
            record.get("quality_flag", ""),
            record.get("correction_note", ""),
            record.get("pipeline_version", ""),
        ]
        for col, value in enumerate(row_data, 1):
            cell = ws_lineage.cell(row=row_idx, column=col, value=value)
            _apply_row_style(cell, row_idx)

    ws_lineage.auto_filter.ref = f"A1:{chr(64 + len(lineage_headers))}1"
    _auto_width(ws_lineage)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
