"""CENACE Real-Time Data Scraper.

Extracts energy production and demand data from CENACE's Información Operativa
page. All data is embedded as Plotly.js chart data within a static HTML file
generated from SCADA.

NOTE: This is HTML scraping, not an API. The page structure may change without
notice. All parsing failures must be LOUD — never silently skip bad data.

Typical run: once daily at 02:00 ECT (UTC-5).
"""

import base64
import json
import logging
import re
import time
from datetime import date, datetime
from typing import Any

import httpx
import numpy as np

from app.db.client import get_client
from app.db.queries import insert_energy_record, insert_lineage
from app.models.energy import DataSource, EnergyRecordCreate, GenerationType, QualityFlag
from app.models.ingest import PipelineResult
from app.models.lineage import DataLineageCreate, IngestionMethod
from app.services.validation import ValidationService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CENACE_REALTIME_URL = (
    "https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm"
)

PIPELINE_VERSION = "0.1.0"

# Mapping from Plotly trace names → GenerationType
TRACE_NAME_MAPPING: dict[str, GenerationType] = {
    "hidráulica": GenerationType.HYDRAULIC,
    "hidroeléctrica": GenerationType.HYDRAULIC,
    "térmica": GenerationType.THERMAL,
    "solar": GenerationType.SOLAR,
    "eólica": GenerationType.WIND,
    "renovable": GenerationType.HYDRAULIC,  # grouped renewable → hydraulic for now
    "renovable no convencional": GenerationType.HYDRAULIC,
    "biomasa": GenerationType.BIOMASS,
}

# Pie chart label mapping (upper-case labels in pie traces)
PIE_LABEL_MAPPING: dict[str, GenerationType] = {
    "HIDROELÉCTRICA": GenerationType.HYDRAULIC,
    "TÉRMICA": GenerationType.THERMAL,
    "SOLAR": GenerationType.SOLAR,
    "EÓLICA": GenerationType.WIND,
    "RENOVABLE": GenerationType.HYDRAULIC,
    "RENOVABLE NO CONVENCIONAL": GenerationType.HYDRAULIC,
    "BIOMASA": GenerationType.BIOMASS,
}


# ---------------------------------------------------------------------------
# HTML fetch
# ---------------------------------------------------------------------------


async def fetch_html() -> str:
    """Download the CENACE Información Operativa page.

    Returns:
        Raw HTML content decoded as latin-1.

    Raises:
        httpx.HTTPError: On network or HTTP-level failures.
        ValueError: If the response is empty or too small to be valid.
    """
    logger.info("Fetching CENACE real-time HTML from %s", CENACE_REALTIME_URL)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(CENACE_REALTIME_URL)
        response.raise_for_status()

    # Page uses latin-1 / windows-1252
    html = response.content.decode("latin-1", errors="replace")

    if len(html) < 10_000:
        raise ValueError(
            f"Response too small ({len(html)} bytes) — page may be unavailable."
        )

    logger.info("Downloaded CENACE HTML: %d bytes", len(html))
    return html


# ---------------------------------------------------------------------------
# Plotly extraction
# ---------------------------------------------------------------------------


def extract_plotly_calls(html: str) -> list[list[dict[str, Any]]]:
    """Extract all Plotly.newPlot trace arrays from the HTML.

    Finds every ``Plotly.newPlot(id, traces, layout)`` call and returns the
    parsed traces argument. Uses a permissive regex + JSON parser.

    Args:
        html: Raw HTML content from the CENACE page.

    Returns:
        List of trace arrays, one per Plotly.newPlot call found.
    """
    # Match Plotly.newPlot("uuid", <traces_json>, ...)
    # The traces argument is a JSON array — we extract it by finding the
    # balanced bracket after the first argument.
    pattern = re.compile(
        r'Plotly\.newPlot\s*\(\s*["\'][^"\']+["\']\s*,\s*(\[)',
        re.DOTALL,
    )

    results: list[list[dict[str, Any]]] = []

    for match in pattern.finditer(html):
        start = match.start(1)
        bracket_depth = 0
        end = start

        for i, ch in enumerate(html[start:], start=start):
            if ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth -= 1
                if bracket_depth == 0:
                    end = i + 1
                    break

        raw_json = html[start:end]

        try:
            traces = json.loads(raw_json)
            results.append(traces)
        except json.JSONDecodeError:
            # Tolerate trailing commas by stripping them
            cleaned = re.sub(r",\s*([}\]])", r"\1", raw_json)
            try:
                traces = json.loads(cleaned)
                results.append(traces)
            except json.JSONDecodeError as exc:
                logger.warning("Could not parse Plotly traces: %s", exc)

    logger.info("Extracted %d Plotly.newPlot call(s)", len(results))
    return results


# ---------------------------------------------------------------------------
# Binary data decode
# ---------------------------------------------------------------------------


def decode_bdata(bdata: str, dtype: str = "f8") -> np.ndarray:
    """Decode Plotly binary data to numpy array.

    Args:
        bdata: Base64-encoded binary string from a Plotly trace ``y.bdata``.
        dtype: NumPy dtype string. ``"f8"`` = float64 (8 bytes per value).

    Returns:
        Array of float64 values (typically 48 values for 30-min intervals).

    Raises:
        ValueError: If the decoded bytes are not divisible by the dtype size.
    """
    raw_bytes = base64.b64decode(bdata)
    np_dtype = np.dtype(dtype)

    if len(raw_bytes) % np_dtype.itemsize != 0:
        raise ValueError(
            f"Byte length {len(raw_bytes)} is not divisible by dtype "
            f"item size {np_dtype.itemsize} for dtype '{dtype}'."
        )

    return np.frombuffer(raw_bytes, dtype=np_dtype)


# ---------------------------------------------------------------------------
# Production summary (pie/donut chart → daily totals)
# ---------------------------------------------------------------------------


def parse_production_summary(
    all_traces: list[list[dict[str, Any]]],
) -> dict[GenerationType, float]:
    """Extract daily production totals from pie/donut chart traces.

    Searches all trace arrays for a pie trace with ``labels`` and ``values``
    matching known energy source names.

    Args:
        all_traces: All Plotly trace arrays extracted from the page.

    Returns:
        Dict mapping GenerationType → total MWh for the day.
        Returns empty dict if no matching pie trace is found.
    """
    result: dict[GenerationType, float] = {}

    for trace_array in all_traces:
        for trace in trace_array:
            if trace.get("type") != "pie":
                continue

            labels: list[str] = trace.get("labels", [])
            values: list[float] = trace.get("values", [])

            if not labels or not values:
                continue

            # Check if this is an energy production pie
            matched = any(
                label.upper() in PIE_LABEL_MAPPING for label in labels
            )
            if not matched:
                continue

            for label, value in zip(labels, values):
                gen_type = PIE_LABEL_MAPPING.get(label.upper())
                if gen_type is None:
                    logger.debug("Unknown pie label: %s", label)
                    continue
                result[gen_type] = result.get(gen_type, 0.0) + float(value)

            logger.info(
                "Parsed production summary: %d source(s), total=%.2f MWh",
                len(result),
                sum(result.values()),
            )
            return result  # Use first matching pie found

    logger.warning("No production summary pie trace found in Plotly calls")
    return result


# ---------------------------------------------------------------------------
# Generation curve (stacked scatter → 48 half-hour values)
# ---------------------------------------------------------------------------


def parse_generation_curve(
    all_traces: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Extract half-hour generation curves from stacked scatter traces.

    Each trace represents one generation type with 48 values (30-min slots).
    Handles both plain array ``y`` and base64 binary ``y.bdata`` formats.

    Args:
        all_traces: All Plotly trace arrays extracted from the page.

    Returns:
        List of dicts with keys: ``generation_type``, ``timestamps``
        (list of "HH:MM" strings), ``values_mw`` (list of float).
    """
    curves: list[dict[str, Any]] = []

    for trace_array in all_traces:
        has_stackgroup = any(
            t.get("stackgroup") for t in trace_array if isinstance(t, dict)
        )
        if not has_stackgroup:
            continue

        for trace in trace_array:
            if not isinstance(trace, dict):
                continue

            name = trace.get("name", "").strip().lower()
            gen_type = TRACE_NAME_MAPPING.get(name)
            if gen_type is None:
                logger.debug("Unknown scatter trace name: '%s'", name)
                continue

            x_values: list[str] = trace.get("x", [])
            y_raw = trace.get("y", [])

            # Decode binary or use plain array
            if isinstance(y_raw, dict) and "bdata" in y_raw:
                try:
                    y_values = decode_bdata(
                        y_raw["bdata"], y_raw.get("dtype", "f8")
                    ).tolist()
                except (ValueError, Exception) as exc:
                    logger.error(
                        "Failed to decode bdata for trace '%s': %s", name, exc
                    )
                    continue
            elif isinstance(y_raw, list):
                y_values = [float(v) for v in y_raw]
            else:
                logger.warning("Unexpected y format for trace '%s'", name)
                continue

            if len(x_values) != len(y_values):
                logger.warning(
                    "x/y length mismatch for trace '%s': %d vs %d",
                    name,
                    len(x_values),
                    len(y_values),
                )
                continue

            curves.append(
                {
                    "generation_type": gen_type,
                    "timestamps": x_values,
                    "values_mw": y_values,
                }
            )
            logger.debug(
                "Parsed curve '%s': %d intervals, max=%.2f MW",
                name,
                len(y_values),
                max(y_values, default=0),
            )

    logger.info("Parsed %d generation curve(s)", len(curves))
    return curves


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_cenace_realtime_pipeline() -> PipelineResult:
    """Orchestrate the full CENACE real-time ingestion cycle.

    Steps:
        1. Download CENACE Información Operativa HTML.
        2. Extract all Plotly.newPlot trace arrays.
        3. Parse production summary (daily totals per source).
        4. Validate each record.
        5. Insert energy_records + data_lineage into Supabase.

    Returns:
        ``PipelineResult`` with counts and any warnings/errors.
    """
    start_time = time.monotonic()
    result = PipelineResult(pipeline="cenace_realtime")
    today = date.today()

    try:
        html = await fetch_html()
    except Exception as exc:
        result.errors.append(f"HTML fetch failed: {exc}")
        logger.error("CENACE realtime pipeline aborted: %s", exc)
        result.duration_seconds = time.monotonic() - start_time
        return result

    try:
        all_traces = extract_plotly_calls(html)
    except Exception as exc:
        result.errors.append(f"Plotly extraction failed: {exc}")
        result.duration_seconds = time.monotonic() - start_time
        return result

    if not all_traces:
        result.errors.append("No Plotly traces found — page structure may have changed.")
        result.duration_seconds = time.monotonic() - start_time
        return result

    production_summary = parse_production_summary(all_traces)

    if not production_summary:
        result.warnings.append("No production summary extracted from pie traces.")

    client = await get_client()

    for gen_type, value_mwh in production_summary.items():
        raw_value = str(value_mwh)

        record_create = EnergyRecordCreate(
            source=DataSource.CENACE_XHR,
            country_code="EC",
            record_date=today,
            generation_type=gen_type,
            value_mwh=value_mwh,
        )

        validation = ValidationService.validate(record_create)
        record_create.quality_flag = validation.overall_flag
        record_create.quality_notes = validation.combined_notes

        if validation.overall_flag == QualityFlag.ERROR:
            result.warnings.append(
                f"Validation error for {gen_type}: {validation.combined_notes}"
            )
            result.records_skipped += 1
            continue

        try:
            inserted = await insert_energy_record(client, record_create)

            await insert_lineage(
                client,
                DataLineageCreate(
                    record_id=inserted.id,
                    source_url=CENACE_REALTIME_URL,
                    ingestion_method=IngestionMethod.CENACE_XHR,
                    raw_value=raw_value,
                    transformed_value=str(value_mwh),
                    quality_flag=validation.overall_flag,
                    pipeline_version=PIPELINE_VERSION,
                ),
            )

            result.records_inserted += 1
            logger.info(
                "Inserted %s: %.2f MWh [%s]",
                gen_type,
                value_mwh,
                validation.overall_flag,
            )

        except Exception as exc:
            msg = f"DB insert failed for {gen_type}: {exc}"
            result.errors.append(msg)
            logger.error(msg)

    result.duration_seconds = time.monotonic() - start_time
    logger.info(
        "CENACE realtime pipeline done: %d inserted, %d skipped, %d errors in %.1fs",
        result.records_inserted,
        result.records_skipped,
        len(result.errors),
        result.duration_seconds,
    )
    return result
