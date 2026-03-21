"""PDF report exporter for Ennesso energy balance reports.

Uses ReportLab for document structure and matplotlib for the
generation mix chart embedded as a PNG image.

Report structure:
    1. Header — Ennesso branding + date range
    2. Analysis — Claude-generated executive narrative
    3. Summary table — key metrics
    4. Generation mix chart — matplotlib stacked bar
    5. Data quality summary
    6. Footer — version + data sources + audit note
"""

import io
import logging
from datetime import date

from app.services.claude_reports import ReportMetrics, generate_narrative

logger = logging.getLogger(__name__)

# Ennesso design tokens (RGB 0-1 floats for ReportLab)
_TEAL = (0 / 255, 194 / 255, 168 / 255)       # #00C2A8
_DARK_BG = (26 / 255, 29 / 255, 39 / 255)      # #1A1D27
_TEXT = (232 / 255, 234 / 255, 240 / 255)       # #E8EAF0
_MUTED = (107 / 255, 114 / 255, 128 / 255)      # #6B7280
_HYDRAULIC = (42 / 255, 123 / 255, 228 / 255)   # #2A7BE4
_THERMAL = (224 / 255, 92 / 255, 42 / 255)      # #E05C2A
_SOLAR = (245 / 255, 166 / 255, 35 / 255)       # #F5A623
_WIND = (126 / 255, 211 / 255, 33 / 255)        # #7ED321
_BIOMASS = (109 / 255, 190 / 255, 126 / 255)    # #6DBE7E


def _build_chart(
    generation_by_type: dict[str, float],
) -> bytes:
    """Build a matplotlib generation mix bar chart and return PNG bytes.

    Args:
        generation_by_type: Dict mapping generation type to MWh value.

    Returns:
        PNG image as bytes, ready to embed in the PDF.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        logger.warning("matplotlib not installed — chart will be skipped")
        return b""

    labels = list(generation_by_type.keys())
    values = [v / 1000 for v in generation_by_type.values()]  # GWh

    color_map = {
        "hydraulic": _HYDRAULIC,
        "thermal": _THERMAL,
        "solar": _SOLAR,
        "wind": _WIND,
        "biomass": _BIOMASS,
        "other": _MUTED,
    }
    colors = [color_map.get(label, _MUTED) for label in labels]

    fig, ax = plt.subplots(figsize=(7, 3))
    fig.patch.set_facecolor((15 / 255, 17 / 255, 23 / 255))
    ax.set_facecolor((26 / 255, 29 / 255, 39 / 255))

    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="none")

    ax.set_ylabel("GWh", color=_MUTED, fontsize=9)
    ax.tick_params(colors=_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, color=(42 / 255, 45 / 255, 58 / 255), linewidth=0.5)
    ax.set_axisbelow(True)

    # Value labels on bars
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.02,
                f"{val:,.0f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color=_TEXT,
            )

    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


async def generate_pdf(
    start_date: date,
    end_date: date,
    generation_by_type: dict[str, float],
    metrics: ReportMetrics,
) -> bytes:
    """Generate a PDF energy balance report.

    Args:
        start_date: Report period start.
        end_date: Report period end.
        generation_by_type: Dict mapping generation type → total MWh.
        metrics: Aggregated metrics for Claude narrative and summary table.

    Returns:
        PDF document as bytes.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib.enums import TA_LEFT
    except ImportError as exc:
        raise RuntimeError("reportlab is not installed") from exc

    # Generate narrative (async)
    narrative = await generate_narrative(metrics)

    # Build chart PNG
    chart_png = _build_chart(generation_by_type)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Ennesso — Energy Balance Report {start_date} / {end_date}",
        author="Ennesso / Perennia Systems",
        subject="Ecuador SNI Energy Balance",
        creator="Ennesso v0.1.0",
    )

    rl_dark_bg = colors.HexColor("#1A1D27")   # just for the header
    rl_teal = colors.HexColor("#00C2A8")
    rl_text = colors.HexColor("#1A1A1A")       # black for body
    rl_muted = colors.HexColor("#555555")      # gray for notes
    rl_border = colors.HexColor("#DDDDDD")     # soft border
    rl_row_alt = colors.HexColor("#F9F9F9")    # alternate row
    rl_white = colors.white

    styles = getSampleStyleSheet()
    heading2 = ParagraphStyle(
        "Heading2Ennesso",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=rl_teal,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
    "BodyEnnesso",
    fontName="Helvetica",
    fontSize=8.5,
    textColor=colors.HexColor("#1A1A1A"),  # black
    leading=13,
    spaceAfter=4,
    )
    muted_style = ParagraphStyle(
        "MutedEnnesso",
        fontName="Helvetica",
        fontSize=7.5,
        textColor=colors.HexColor("#555555"),  # gray
    )

    story = []

    # -------------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------------
    header_data = [[
        Paragraph(
            '<font name="Helvetica-Bold" size="18" color="#00C2A8">ENNESSO</font>',
            styles["Normal"]
        ),
        Paragraph(
            f'<font name="Helvetica" size="9" color="#E8EAF0">'
            f'Energy Balance Report<br/>'
            f'{start_date} — {end_date}</font>',
            styles["Normal"]
        ),
    ]]
    header_tbl = Table(header_data, colWidths=["50%", "50%"])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rl_dark_bg),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, 0), 16),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # -------------------------------------------------------------------------
    # Analysis (Claude narrative)
    # -------------------------------------------------------------------------
    story.append(Paragraph("Analysis", heading2))
    for para in narrative.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body_style))
    story.append(Spacer(1, 0.3 * cm))

    # -------------------------------------------------------------------------
    # Summary table
    # -------------------------------------------------------------------------
    story.append(Paragraph("Key Metrics", heading2))

    renewable_pct = f"{metrics.renewable_share * 100:.1f}%"
    total_gwh = f"{metrics.total_mwh / 1000:,.1f} GWh"
    co2_tonnes = f"{metrics.total_co2_kg / 1000:,.0f} t CO2"
    avoided_tonnes = f"{metrics.avoided_co2_kg / 1000:,.0f} t CO2"
    intensity = f"{metrics.avg_intensity_kg_per_mwh:.1f} kg/MWh"

    summary_data = [
        ["Metric", "Value", "Notes"],
        ["Total Generation", total_gwh, f"{start_date} – {end_date}"],
        ["Renewable Share", renewable_pct, "Hydraulic + Solar + Wind + Biomass"],
        ["CO2 Emissions", co2_tonnes, "IPCC AR5 lifecycle factors"],
        ["CO2 Avoided", avoided_tonnes, "vs 100% thermal baseline"],
        ["Carbon Intensity", intensity, "Average across mix"],
    ]

    summary_tbl = Table(summary_data, colWidths=["40%", "25%", "35%"])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_dark_bg),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1A1A1A")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
        ("GRID", (0, 0), (-1, -1), 0.3, rl_border),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # -------------------------------------------------------------------------
    # Generation mix chart
    # -------------------------------------------------------------------------
    if chart_png:
        story.append(Paragraph("Generation Mix", heading2))
        img_buf = io.BytesIO(chart_png)
        chart_img = Image(img_buf, width=16 * cm, height=6 * cm)
        story.append(chart_img)
        story.append(Spacer(1, 0.3 * cm))

    # -------------------------------------------------------------------------
    # Data quality summary
    # -------------------------------------------------------------------------
    story.append(Paragraph("Data Quality", heading2))
    total_records = metrics.ok_count + metrics.warning_count + metrics.error_count
    quality_data = [
        ["Status", "Count", "Share"],
        ["✓ Valid", str(metrics.ok_count),
         f"{metrics.ok_count / max(total_records, 1) * 100:.1f}%"],
        ["⚠ Warning", str(metrics.warning_count),
         f"{metrics.warning_count / max(total_records, 1) * 100:.1f}%"],
        ["✗ Error", str(metrics.error_count),
         f"{metrics.error_count / max(total_records, 1) * 100:.1f}%"],
    ]
    quality_tbl = Table(quality_data, colWidths=["40%", "30%", "30%"])
    quality_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_dark_bg),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1A1A1A")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, rl_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ]))
    story.append(quality_tbl)
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "Note: 'Warning' flags on historical records indicate data age > 7 days "
        "(late-ingestion check), not measurement quality issues. "
        "This reflects the validation system working as designed.",
        muted_style
    ))

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------
    footer_text = (
        "Generated by Ennesso v0.1.0 &nbsp;|&nbsp; "
        "Data sources: CENACE, ARCERNNR &nbsp;|&nbsp; "
        "All data points traceable via data_lineage table"
    )
    story.append(Paragraph(footer_text, muted_style))

    doc.build(story)
    buf.seek(0)
    return buf.read()
