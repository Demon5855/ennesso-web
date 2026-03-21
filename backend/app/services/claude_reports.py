"""Claude-powered executive narrative generation for energy reports.

Uses claude-3-5-haiku for cost-efficient report narrative generation.
Input: aggregated metrics for a date range.
Output: 2-paragraph executive narrative suitable for ESG reporting.
"""

import logging
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReportMetrics:
    """Summary metrics passed to Claude for narrative generation.

    Attributes:
        start_date: Period start (ISO 8601).
        end_date: Period end (ISO 8601).
        total_mwh: Total generation in MWh.
        hydraulic_mwh: Hydraulic generation in MWh.
        thermal_mwh: Thermal generation in MWh.
        renewable_share: Renewable share as decimal (0-1).
        total_co2_kg: Total lifecycle CO₂ in kg.
        avoided_co2_kg: CO₂ avoided vs 100% thermal baseline in kg.
        avg_intensity_kg_per_mwh: Average carbon intensity (kg CO₂/MWh).
        ok_count: Records with quality flag 'ok'.
        warning_count: Records with quality flag 'warning'.
        error_count: Records with quality flag 'error'.
    """

    start_date: str
    end_date: str
    total_mwh: float
    hydraulic_mwh: float
    thermal_mwh: float
    renewable_share: float
    total_co2_kg: float
    avoided_co2_kg: float
    avg_intensity_kg_per_mwh: float
    ok_count: int
    warning_count: int
    error_count: int


def _build_prompt(metrics: ReportMetrics) -> str:
    """Build the Claude prompt from report metrics.

    Args:
        metrics: Aggregated energy metrics for the period.

    Returns:
        Formatted prompt string ready for the Anthropic API.
    """
    renewable_pct = metrics.renewable_share * 100
    avoided_tonnes = metrics.avoided_co2_kg / 1000
    total_gwh = metrics.total_mwh / 1000

    return f"""You are writing an executive summary section for an institutional energy report
about Ecuador's electricity system. Write exactly 2 concise paragraphs.

Period: {metrics.start_date} to {metrics.end_date}
Data source: CENACE (Centro Nacional de Control de Energía)

Key metrics:
- Total generation: {total_gwh:,.1f} GWh
- Hydraulic generation: {metrics.hydraulic_mwh / 1000:,.1f} GWh
- Thermal generation: {metrics.thermal_mwh / 1000:,.1f} GWh
- Renewable share: {renewable_pct:.1f}%
- Average carbon intensity: {metrics.avg_intensity_kg_per_mwh:.1f} kg CO₂/MWh
- CO₂ avoided vs 100% thermal baseline: {avoided_tonnes:,.0f} tonnes CO₂
- Data quality: {metrics.ok_count} valid records, {metrics.warning_count} warnings, \
{metrics.error_count} errors

Instructions:
- Paragraph 1: Summarize the generation mix and any notable trends.
  Mention Ecuador's reliance on hydraulic power and its implications.
- Paragraph 2: Address the carbon footprint, avoided emissions, and what this
  means for Ecuador's energy transition and climate commitments.
- Professional tone, suitable for an ESG or regulatory report.
- Do not use bullet points. Do not use headers. Plain prose only.
- Keep each paragraph to 3-4 sentences maximum."""


async def generate_narrative(metrics: ReportMetrics) -> str:
    """Generate a 2-paragraph executive narrative using Claude Haiku.

    Args:
        metrics: Aggregated energy metrics for the reporting period.

    Returns:
        Executive narrative as a plain text string (2 paragraphs).
        Falls back to a template string if the API call fails.
    """
    if not settings.anthropic_api_key:
        logger.warning(
            "ANTHROPIC_API_KEY not set — returning template narrative"
        )
        return _fallback_narrative(metrics)

    try:
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(metrics),
                }
            ],
        )
        text = message.content[0].text if message.content else ""
        logger.info(
            "Claude narrative generated: %d chars, %d input tokens, %d output tokens",
            len(text),
            message.usage.input_tokens,
            message.usage.output_tokens,
        )
        return text.strip()

    except Exception as exc:
        logger.error("Claude narrative generation failed: %s", exc)
        return _fallback_narrative(metrics)


def _fallback_narrative(metrics: ReportMetrics) -> str:
    """Return a template narrative when the API is unavailable.

    Args:
        metrics: Aggregated energy metrics.

    Returns:
        Static template narrative string.
    """
    renewable_pct = metrics.renewable_share * 100
    avoided_tonnes = metrics.avoided_co2_kg / 1000

    return (
        f"During the period from {metrics.start_date} to {metrics.end_date}, "
        f"Ecuador's national electricity system (SNI) generated a total of "
        f"{metrics.total_mwh / 1000:,.1f} GWh, with hydraulic sources accounting for "
        f"the dominant share of the generation mix. The system maintained a renewable "
        f"energy share of {renewable_pct:.1f}%, reflecting the country's continued "
        f"dependence on hydroelectric resources and their sensitivity to seasonal "
        f"hydrological conditions.\n\n"
        f"From a carbon perspective, the generation mix produced an average intensity "
        f"of {metrics.avg_intensity_kg_per_mwh:.1f} kg CO₂/MWh on a lifecycle basis "
        f"(IPCC AR5 factors), avoiding approximately {avoided_tonnes:,.0f} tonnes of "
        f"CO₂ compared to a hypothetical 100% thermal baseline. These avoided emissions "
        f"underscore the climate value of Ecuador's hydroelectric infrastructure and "
        f"highlight the importance of protecting watershed capacity as part of the "
        f"country's long-term decarbonisation strategy."
    )
