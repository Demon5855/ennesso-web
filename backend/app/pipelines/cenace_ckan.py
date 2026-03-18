"""CENACE Historical Data Downloader.

Downloads quarterly CSV files from Ecuador's Open Data Portal and ingests
them into energy_records (production) and installed_capacity (capacity) tables.

NOTE: The CKAN datastore API is broken ("desconectado del servidor").
Files are downloaded directly via known resource URLs instead.

CSV characteristics:
- Separator: ; (semicolon)
- Decimal: , (comma)
- Encoding: latin-1 / windows-1252
- Null marker: "No hubo producción en este periodo" → value_mwh = 0.0
"""

import calendar
import logging
import time
from datetime import date
from io import StringIO
from typing import Any

import httpx
import pandas as pd

from app.db.client import get_client
from app.db.queries import insert_energy_record, insert_lineage
from app.models.capacity import InstalledCapacityCreate
from app.models.energy import DataSource, EnergyRecordCreate, GenerationType, QualityFlag
from app.models.ingest import PipelineResult
from app.models.lineage import DataLineageCreate, IngestionMethod
from app.services.validation import ValidationService

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Type mappings
# ---------------------------------------------------------------------------

PRODUCTION_TYPE_MAPPING: dict[str, GenerationType] = {
    "H": GenerationType.HYDRAULIC,
    "T": GenerationType.THERMAL,
    "BMAS": GenerationType.THERMAL,    # Biomasa combustión → thermal
    "FVOL": GenerationType.SOLAR,      # Fotovoltaica
    "EOL": GenerationType.WIND,        # Eólica
    "MCI": GenerationType.THERMAL,     # Motor combustión interna
    "TG": GenerationType.THERMAL,      # Turbo gas
    "TV": GenerationType.THERMAL,      # Turbo vapor
    "MH": GenerationType.HYDRAULIC,    # Mini-hidráulica
    "BI": GenerationType.BIOMASS,      # Biomasa
}

CAPACITY_TYPE_MAPPING: dict[str, GenerationType] = {
    "Pasada": GenerationType.HYDRAULIC,
    "Embalse": GenerationType.HYDRAULIC,
    "Turbo Gas": GenerationType.THERMAL,
    "Turbo Vapor": GenerationType.THERMAL,
    "MCI": GenerationType.THERMAL,
    "Solar": GenerationType.SOLAR,
    "Eólica": GenerationType.WIND,
    "Biomasa": GenerationType.BIOMASS,
}

MONTH_MAPPING: dict[str, int] = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}

NULL_PRODUCTION_MARKER = "No hubo producción en este periodo"

# ---------------------------------------------------------------------------
# Known CKAN resources registry
# ---------------------------------------------------------------------------

CKAN_RESOURCES: dict[str, dict[str, str]] = {
    # Potencia efectiva despachada → installed_capacity table
    "capacity_2023_q4": {
        "dataset_id": "c121b883-9033-4208-bdf5-be81065cc488",
        "resource_id": "c2c6c438-153d-4bde-a9d8-a84496f38299",
        "filename": "cenace_potenciadespachada_cd_2023-octubre_diciembre.csv",
        "format": "csv",
        "target_table": "installed_capacity",
        "period": "2023-Q4",
        "year": "2023",
    },
    # Producción de energía eléctrica → energy_records table
    # TODO: catalog resource_id for each additional quarter
    "production_2025_q4": {
        "dataset_id": "TODO",
        "resource_id": "TODO",
        "filename": "TODO.csv",
        "format": "csv",
        "target_table": "energy_records",
        "period": "2025-Q4",
        "year": "2025",
    },
}

CKAN_BASE_URL = "https://datosabiertos.presidencia.gob.ec"


def build_download_url(resource: dict[str, str]) -> str:
    """Build the direct download URL for a CKAN resource.

    Args:
        resource: Entry from ``CKAN_RESOURCES``.

    Returns:
        Full HTTPS download URL.
    """
    return (
        f"{CKAN_BASE_URL}/dataset/{resource['dataset_id']}"
        f"/resource/{resource['resource_id']}"
        f"/download/{resource['filename']}"
    )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


async def download_resource(resource_key: str) -> pd.DataFrame:
    """Download a CKAN resource and return it as a DataFrame.

    Uses semicolon separator, comma decimal, and latin-1 encoding as
    specified in the CENACE CSV format reference.

    Args:
        resource_key: Key from ``CKAN_RESOURCES``.

    Returns:
        Raw DataFrame with original column names.

    Raises:
        KeyError: If ``resource_key`` is not in ``CKAN_RESOURCES``.
        ValueError: If resource has TODO placeholders (not yet cataloged).
        httpx.HTTPError: On download failure.
    """
    resource = CKAN_RESOURCES[resource_key]

    if "TODO" in resource.get("dataset_id", ""):
        raise ValueError(
            f"Resource '{resource_key}' has not been cataloged yet. "
            "Update CKAN_RESOURCES with the actual dataset_id and resource_id."
        )

    url = build_download_url(resource)
    logger.info("Downloading CKAN resource '%s' from %s", resource_key, url)

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    content = response.content.decode("latin-1", errors="replace")
    df = pd.read_csv(
        StringIO(content),
        sep=";",
        decimal=",",
        encoding=None,  # already decoded
        dtype=str,       # read all as string first — we handle types manually
    )

    logger.info(
        "Downloaded '%s': %d rows × %d cols",
        resource_key,
        len(df),
        len(df.columns),
    )
    return df


# ---------------------------------------------------------------------------
# Production CSV parser
# ---------------------------------------------------------------------------


def _last_day_of_month(year: int, month: int) -> date:
    """Return the last calendar day of the given month."""
    return date(year, month, calendar.monthrange(year, month)[1])


def _parse_numeric_value(raw: Any) -> tuple[float | None, bool]:
    """Parse a raw CSV cell value to float.

    Handles: numeric strings, null marker text, NaN.

    Args:
        raw: Raw cell value from the DataFrame.

    Returns:
        Tuple of (value, is_null_marker) where is_null_marker indicates
        the cell contained the "no production" text.
    """
    if pd.isna(raw):
        return None, False

    str_val = str(raw).strip()

    if str_val == NULL_PRODUCTION_MARKER:
        return 0.0, True

    # Remove any thousands separators (some cells use period as thousands sep)
    str_val = str_val.replace(".", "").replace(",", ".")
    try:
        return float(str_val), False
    except ValueError:
        return None, False


def parse_production_csv(
    df: pd.DataFrame,
    period: str,
    year: int,
) -> list[EnergyRecordCreate]:
    """Parse a production CSV DataFrame into EnergyRecordCreate instances.

    Melts month columns into rows, converts GWh → MWh, applies type mapping.

    Expected columns: Agente, Tipo de Central, Central, Unidad, <month>...

    Args:
        df: Raw DataFrame from ``download_resource``.
        period: Quarter label e.g. ``"2025-Q4"`` (used for logging).
        year: Calendar year of the data, used to compute record_date.

    Returns:
        List of ``EnergyRecordCreate`` ready for validation and insertion.
    """
    records: list[EnergyRecordCreate] = []

    # Normalise column names
    df.columns = [str(c).strip() for c in df.columns]

    # Identify month columns
    month_cols = [c for c in df.columns if c in MONTH_MAPPING]
    if not month_cols:
        logger.error(
            "No recognised month columns found in production CSV for %s. "
            "Columns: %s",
            period,
            list(df.columns),
        )
        return records

    type_col = next(
        (c for c in df.columns if "tipo" in c.lower()), None
    )
    if type_col is None:
        logger.error("'Tipo de Central' column not found for %s", period)
        return records

    logger.info(
        "Parsing production CSV for %s: %d rows, months: %s",
        period,
        len(df),
        month_cols,
    )

    for _, row in df.iterrows():
        type_code = str(row.get(type_col, "")).strip().upper()
        gen_type = PRODUCTION_TYPE_MAPPING.get(type_code)

        if gen_type is None:
            logger.debug("Unknown Tipo de Central code: '%s' — skipping row", type_code)
            continue

        for month_name in month_cols:
            raw_val = row.get(month_name)
            value_gwh, is_null_marker = _parse_numeric_value(raw_val)

            if value_gwh is None:
                continue

            value_mwh = value_gwh * 1000.0
            month_num = MONTH_MAPPING[month_name]
            record_date = _last_day_of_month(year, month_num)

            quality_flag = QualityFlag.OK
            quality_notes: str | None = None

            if is_null_marker:
                quality_flag = QualityFlag.WARNING
                quality_notes = "Source reported: 'No hubo producción en este periodo'"

            records.append(
                EnergyRecordCreate(
                    source=DataSource.CENACE_CKAN,
                    country_code="EC",
                    record_date=record_date,
                    generation_type=gen_type,
                    value_mwh=value_mwh,
                    quality_flag=quality_flag,
                    quality_notes=quality_notes,
                )
            )

    logger.info(
        "Parsed %d production records from %s", len(records), period
    )
    return records


# ---------------------------------------------------------------------------
# Capacity CSV parser
# ---------------------------------------------------------------------------


def parse_capacity_csv(
    df: pd.DataFrame,
    period: str,
    year: int,
) -> list[InstalledCapacityCreate]:
    """Parse a capacity CSV DataFrame into InstalledCapacityCreate instances.

    Expected columns: Nro., Empresa, Unidad de Negocio, Central, Unidad, Tipo,
    <Capacidad ... Octubre>, <...Noviembre>, <...Diciembre>

    Args:
        df: Raw DataFrame from ``download_resource``.
        period: Quarter label e.g. ``"2023-Q4"``.
        year: Calendar year of the data.

    Returns:
        List of ``InstalledCapacityCreate`` ready for insertion.
    """
    records: list[InstalledCapacityCreate] = []

    df.columns = [str(c).strip() for c in df.columns]

    # Identify month capacity columns (contain month name in header)
    capacity_cols: dict[str, str] = {}  # month_name → column_name
    for col in df.columns:
        for month_name in MONTH_MAPPING:
            if month_name.lower() in col.lower():
                capacity_cols[month_name] = col
                break

    if not capacity_cols:
        logger.error(
            "No capacity month columns found for %s. Columns: %s",
            period,
            list(df.columns),
        )
        return records

    # Find Tipo column
    tipo_col = next(
        (c for c in df.columns if c.strip().lower() == "tipo"), None
    )
    if tipo_col is None:
        logger.error("'Tipo' column not found in capacity CSV for %s", period)
        return records

    logger.info(
        "Parsing capacity CSV for %s: %d rows, months: %s",
        period,
        len(df),
        list(capacity_cols.keys()),
    )

    for _, row in df.iterrows():
        tipo = str(row.get(tipo_col, "")).strip()
        gen_type = CAPACITY_TYPE_MAPPING.get(tipo)

        if gen_type is None:
            logger.debug("Unknown Tipo: '%s' — skipping row", tipo)
            continue

        for month_name, col_name in capacity_cols.items():
            raw_val = row.get(col_name)
            capacity_mw, _ = _parse_numeric_value(raw_val)

            if capacity_mw is None:
                continue

            month_num = MONTH_MAPPING[month_name]
            effective_date = date(year, month_num, 1)

            records.append(
                InstalledCapacityCreate(
                    country_code="EC",
                    generation_type=gen_type,
                    capacity_mw=capacity_mw,
                    effective_date=effective_date,
                    source=DataSource.CENACE_CKAN,
                    notes=f"CKAN download — {period}",
                )
            )

    logger.info(
        "Parsed %d capacity records from %s", len(records), period
    )
    return records


# ---------------------------------------------------------------------------
# Deduplication check
# ---------------------------------------------------------------------------


async def _period_already_ingested(
    resource_key: str,
) -> bool:
    """Check if a CKAN resource has already been ingested.

    Args:
        resource_key: Key from ``CKAN_RESOURCES``.

    Returns:
        True if records for this source + period exist in the DB.
    """
    resource = CKAN_RESOURCES[resource_key]
    period = resource["period"]
    client = await get_client()

    response = (
        await client.table("data_lineage")
        .select("id", count="exact")
        .ilike("correction_note", f"%{period}%")
        .limit(1)
        .execute()
    )

    count = response.count or 0
    if count > 0:
        logger.info(
            "Resource '%s' (period=%s) already ingested (%d lineage records) — skipping.",
            resource_key,
            period,
            count,
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_ckan_pipeline(
    resource_keys: list[str] | None = None,
) -> PipelineResult:
    """Orchestrate the CKAN historical data ingestion.

    Args:
        resource_keys: Subset of ``CKAN_RESOURCES`` keys to process.
            If None, processes all cataloged (non-TODO) resources.

    Returns:
        ``PipelineResult`` with counts and any warnings/errors.
    """
    start_time = time.monotonic()
    result = PipelineResult(pipeline="cenace_ckan")

    keys_to_process = resource_keys or [
        k for k, v in CKAN_RESOURCES.items()
        if "TODO" not in v.get("dataset_id", "")
    ]

    if not keys_to_process:
        result.warnings.append("No cataloged CKAN resources to process yet.")
        result.duration_seconds = time.monotonic() - start_time
        return result

    client = await get_client()

    for resource_key in keys_to_process:
        resource = CKAN_RESOURCES.get(resource_key)
        if not resource:
            result.errors.append(f"Unknown resource key: '{resource_key}'")
            continue

        # Deduplication check
        if await _period_already_ingested(resource_key):
            result.records_skipped += 1
            continue

        try:
            df = await download_resource(resource_key)
        except Exception as exc:
            msg = f"Download failed for '{resource_key}': {exc}"
            result.errors.append(msg)
            logger.error(msg)
            continue

        year = int(resource.get("year", date.today().year))
        period = resource["period"]
        target_table = resource["target_table"]
        download_url = build_download_url(resource)

        if target_table == "energy_records":
            parsed_records = parse_production_csv(df, period, year)

            for record_create in parsed_records:
                validation = ValidationService.validate(record_create)

                if validation.overall_flag == QualityFlag.ERROR:
                    result.warnings.append(
                        f"Validation error [{period}] {record_create.generation_type}: "
                        f"{validation.combined_notes}"
                    )
                    result.records_skipped += 1
                    continue

                record_create.quality_flag = validation.overall_flag
                record_create.quality_notes = validation.combined_notes

                try:
                    inserted = await insert_energy_record(client, record_create)
                    await insert_lineage(
                        client,
                        DataLineageCreate(
                            record_id=inserted.id,
                            source_url=download_url,
                            ingestion_method=IngestionMethod.CKAN_API,
                            raw_value=str(record_create.value_mwh),
                            transformed_value=str(record_create.value_mwh),
                            quality_flag=validation.overall_flag,
                            correction_note=f"CKAN period={period}",
                            pipeline_version=PIPELINE_VERSION,
                        ),
                    )
                    result.records_inserted += 1
                except Exception as exc:
                    result.errors.append(
                        f"DB insert failed [{period}]: {exc}"
                    )
                    logger.error("DB insert failed: %s", exc)

        elif target_table == "installed_capacity":
            capacity_records = parse_capacity_csv(df, period, year)

            for cap in capacity_records:
                try:
                    payload = cap.model_dump(mode="json")
                    await client.table("installed_capacity").insert(payload).execute()
                    result.records_inserted += 1
                except Exception as exc:
                    result.errors.append(
                        f"Capacity insert failed [{period}]: {exc}"
                    )
                    logger.error("Capacity insert failed: %s", exc)

    result.duration_seconds = time.monotonic() - start_time
    logger.info(
        "CKAN pipeline done: %d inserted, %d skipped, %d errors in %.1fs",
        result.records_inserted,
        result.records_skipped,
        len(result.errors),
        result.duration_seconds,
    )
    return result
