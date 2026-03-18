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
    # ==================================================================
    # energy_records — Producción de Energía Eléctrica
    # ==================================================================
    "production_2021_q1q2q3": {
        "dataset_id": "1c8f8ca2-c0b5-44e0-83a1-d45b8f9c95c4",
        "resource_id": "efadf291-8196-44f8-a6af-40bc3bb2e284",
        "filename": "cenace_producciondeenergia_cd_2021-enero_septiembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2021-Q1Q2Q3", "year": "2021",
    },
    "production_2021_q4": {
        "dataset_id": "64f82b4c-8346-4adc-9ba5-ee691f88f461",
        "resource_id": "d1975c07-c63f-4659-9b26-4b9d928fdc5a",
        "filename": "cenace_producciondeenergia_cd_2021-octubre_diciembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2021-Q4", "year": "2021",
    },
    "production_2022_q1": {
        "dataset_id": "d0c8be7a-ce49-4665-9a06-073b2b658b3b",
        "resource_id": "c0c74109-48ec-493b-8be4-d180a1c41ad4",
        "filename": "cenace_producciondeenergia_cd_2022-enero_marzo.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2022-Q1", "year": "2022",
    },
    "production_2022_q2": {
        "dataset_id": "711587dd-242d-4534-805e-0e5a1dedeac7",
        "resource_id": "8476d90a-9c03-4ea2-a0e3-2f541cf33273",
        "filename": "cenace_producciondeenergia_cd_2022-abril_junio.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2022-Q2", "year": "2022",
    },
    "production_2022_q3": {
        "dataset_id": "c1d9c9be-b572-41c6-a62f-4336bd0d2a57",
        "resource_id": "3f0ed126-a775-4e4d-b044-17791e958d00",
        "filename": "cenace_producciondeenergia_cd_2022-julio_septiembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2022-Q3", "year": "2022",
    },
    "production_2022_q4": {
        "dataset_id": "7a45c01e-9fe1-4d33-b468-915ac8882edf",
        "resource_id": "180001ec-f437-42e0-812b-3f7ac0c65d95",
        "filename": "cenace_producciondeenergia_cd_2022-octubre_diciembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2022-Q4", "year": "2022",
    },
    # production_2023_q1 → no CD available, only DD (XLSX) — skipped
    "production_2023_q2": {
        "dataset_id": "311b8eed-5624-46f3-a1dc-049844ec5419",
        "resource_id": "38dde4ee-138d-4f8b-87f3-14b8f4080d75",
        "filename": "cenace_producciondeenergia_cd_2023-abril_junio.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2023-Q2", "year": "2023",
    },
    "production_2023_q3": {
        "dataset_id": "387e36ba-a300-42ee-acaa-2ddd18c1926f",
        "resource_id": "f6402158-434c-4db8-a9b9-a1c2e493dca1",
        "filename": "cenace_producciondeenergia_cd_2023-julio_septiembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2023-Q3", "year": "2023",
    },
    "production_2023_q4": {
        "dataset_id": "709b6465-b4e2-431d-8e3a-e6416e72a770",
        "resource_id": "4fa27fad-8597-405a-98e3-b7c4408397e5",
        "filename": "cenace_producciondeenergia_cd_2023-octubre_diciembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2023-Q4", "year": "2023",
    },
    "production_2024_q1": {
        "dataset_id": "322f479e-ac8f-4f7d-b2d3-a58d980a24fa",
        "resource_id": "f0c43035-aee0-4436-b9b6-3ce4773892c1",
        "filename": "cenace_producciondeenergia_cd_2024-enero_marzo.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2024-Q1", "year": "2024",
    },
    "production_2024_q2": {
        "dataset_id": "e723d576-59b4-4c18-91b6-490e3e9f1e53",
        "resource_id": "07e13b52-19fa-4a14-8f18-b07b038b5572",
        "filename": "cenace_producciondeenergia_cd_2024-abril_junio.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2024-Q2", "year": "2024",
    },
    "production_2024_q3": {
        "dataset_id": "bb0ea80e-b6c1-4d88-bbfc-679eb6310f53",
        "resource_id": "4d72bc9c-daf9-4e2b-b3f1-74ac5095c47f",
        "filename": "cenace_producciondeenergia_cd_2024-julio_septiembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2024-Q3", "year": "2024",
    },
    "production_2024_q4": {
        "dataset_id": "ea6a3855-93cb-40e4-8ab5-0c6444655825",
        "resource_id": "a31fce7f-7fb9-46c3-8912-3e1ad45f71d2",
        "filename": "cenace_producciondeenergia_cd_2024-octubre_diciembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2024-Q4", "year": "2024",
    },
    "production_2025_q1": {
        "dataset_id": "4245e656-de47-40c3-9d46-120f16044137",
        "resource_id": "801af286-0aa5-4a05-b18c-4d3c701457a0",
        "filename": "cenace_producciondeenergia_cd_2025-enero_marzo.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2025-Q1", "year": "2025",
    },
    "production_2025_q2": {
        "dataset_id": "4245e656-de47-40c3-9d46-120f16044137",
        "resource_id": "edbab7ee-847c-4596-afa4-6a4d145d228c",
        "filename": "cenace_producciondeenergia_cd_2025-abril_junio.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2025-Q2", "year": "2025",
    },
    "production_2025_q3": {
        "dataset_id": "4245e656-de47-40c3-9d46-120f16044137",
        "resource_id": "3e48168a-2e76-4f04-862c-ed75c64ec5ad",
        "filename": "cenace_producciondeenergia_cd_2025-julio_septiembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2025-Q3", "year": "2025",
    },
    "production_2025_q4": {
        "dataset_id": "4245e656-de47-40c3-9d46-120f16044137",
        "resource_id": "26d661ef-a739-411b-a8ee-5733aaed456f",
        "filename": "cenace_producciondeenergia_cd_2025-octubre_diciembre.csv",
        "format": "csv", "target_table": "energy_records",
        "period": "2025-Q4", "year": "2025",
    },

    # ==================================================================
    # installed_capacity — Potencia Efectiva / Despachada / Instalada
    # ==================================================================
    "capacity_generationEffective_2024_q1": {
        "dataset_id": "8908b6e9-c7e8-4ae0-8f85-e43eb90f2fe2",
        "resource_id": "a5de26e8-2ae8-42ea-a957-54d07eebe4fc",
        "filename": "cenace_potenciaefectiva_cd_2024-enero_marzo.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2024-Q1", "year": "2024",
    },
    "capacity_generationEffective_2024_q2": {
        "dataset_id": "c26a8568-f579-4926-b25c-4a53445503e5",
        "resource_id": "bcc17fb7-adbd-4492-810f-1166053fd846",
        "filename": "cenace_potenciaefectiva_cd_2024-abril_junio.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2024-Q2", "year": "2024",
    },
    "capacity_generationEffective_2024_q3": {
        "dataset_id": "88a3d8eb-da2f-4dbd-a022-789aaa7479d7",
        "resource_id": "f9a77c77-efa0-49c0-a876-a1e65f8c9f8d",
        "filename": "cenace_potenciaefectiva_cd_2024-julio_septiembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2024-Q3", "year": "2024",
    },
    "capacity_generationEffective_2024_q4": {
        "dataset_id": "afa6b081-9046-447f-8dda-027eda43d4ec",
        "resource_id": "1169f9a2-ae3a-406c-b25d-7d44cb86ca06",
        "filename": "cenace_potenciaefectiva_cd_2024-octubre_diciembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2024-Q4", "year": "2024",
    },
    "capacity_generationEffective_2025_q1": {
        "dataset_id": "9319a78f-a13f-446f-bc6a-6497db2a611d",
        "resource_id": "ebb2a041-461c-4710-be6b-6e539606f49a",
        "filename": "cenace_potenciaefectiva_cd_2025-enero_marzo.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2025-Q1", "year": "2025",
    },
    "capacity_generationEffective_2025_q2": {
        "dataset_id": "9319a78f-a13f-446f-bc6a-6497db2a611d",
        "resource_id": "9f328bbb-4246-4ef5-8c50-c031a95e8ab1",
        "filename": "cenace_potenciaefectiva_cd_2025-abril-junio.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2025-Q2", "year": "2025",
    },
    "capacity_generationEffective_2025_q3": {
        "dataset_id": "9319a78f-a13f-446f-bc6a-6497db2a611d",
        "resource_id": "c9016d58-fef2-44b5-b85b-d374063f46f6",
        "filename": "cenace_potenciaefectiva_cd_2025-julio-septiembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2025-Q3", "year": "2025",
    },
    "capacity_generationEffective_2025_q4": {
        "dataset_id": "9319a78f-a13f-446f-bc6a-6497db2a611d",
        "resource_id": "715e6521-ca23-4509-97c1-3bbefa287a34",
        "filename": "cenace_potenciaefectiva_cd_2025-octubre-diciembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2025-Q4", "year": "2025",
    },
    "capacity_dispatched_2023_q1": {
        "dataset_id": "1c0f3c58-d29a-48c2-aa72-eff3c3ec2224",
        "resource_id": "3f54b589-5968-4e24-a03b-fad344841acd",
        "filename": "cenace_potenciadespachada_cd_2023-enero_marzo.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2023-Q1", "year": "2023",
    },
    "capacity_dispatched_2023_q2": {
        "dataset_id": "9bfb4d41-51bb-42cf-bd06-45b76953b5a1",
        "resource_id": "58a4117a-110e-48f0-9a5d-2cf43cf72ef7",
        "filename": "cenace_potenciadespachada_cd_2023-abril_junio.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2023-Q2", "year": "2023",
    },
    "capacity_dispatched_2023_q3": {
        "dataset_id": "f764566f-8a09-453f-b7e7-b2f8d136949e",
        "resource_id": "2cea2539-5783-44ab-a206-6ae340583166",
        "filename": "cenace_potenciadespachada_cd_2023-julio_septiembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2023-Q3", "year": "2023",
    },
    "capacity_dispatched_2023_q4": {
        "dataset_id": "c121b883-9033-4208-bdf5-be81065cc488",
        "resource_id": "c2c6c438-153d-4bde-a9d8-a84496f38299",
        "filename": "cenace_potenciadespachada_cd_2023-octubre_diciembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2023-Q4", "year": "2023",
    },
    "capacity_installed_2021_q1q2q3": {
        "dataset_id": "891a8333-8998-4e83-8758-8692db427c82",
        "resource_id": "79183bcf-46c8-4843-bb97-9af28d256113",
        "filename": "cenace_capacidadinstalada_cd_2021-enero_septiembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2021-Q1Q2Q3", "year": "2021",
    },
    "capacity_installed_2021_q4": {
        "dataset_id": "54e5eb96-9869-40dc-bb96-eecef405f596",
        "resource_id": "d61327a9-4edc-4699-a25a-a2b7de6f8177",
        "filename": "cenace_capacidadinstalada_cd_2021-octubre_diciembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2021-Q4", "year": "2021",
    },
    # capacity_installed_2022_q1 → XLSX format, deferred to V2
    "capacity_installed_2022_q2": {
        "dataset_id": "bd82c403-85d3-4407-bd6f-bf13b2783c0b",
        "resource_id": "e7d2a8bd-d8a4-4cca-bfeb-81fca401db3f",
        "filename": "cenace_capacidadinstalada_cd_2022-abril_junio.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2022-Q2", "year": "2022",
    },
    "capacity_installed_2022_q3": {
        "dataset_id": "80da60f2-7938-404a-9454-ac8edd65629c",
        "resource_id": "017a6f1a-6049-4f63-b3e8-e7b86a4ea8f9",
        "filename": "cenace_capacidadinstalada_cd_2022-julio_septiembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2022-Q3", "year": "2022",
    },
    "capacity_installed_2022_q4": {
        "dataset_id": "073cd3ec-0b9f-4b91-96e1-bae643df6d98",
        "resource_id": "1daa9b66-4aa9-4f86-a3c5-f4e8c3742337",
        "filename": "cenace_capacidadinstalada_cd_2022-octubre_diciembre.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2022-Q4", "year": "2022",
    },
    "capacity_installed_2023_q1": {
        "dataset_id": "936e95d3-bd78-4c82-b108-d2fb42216b27",
        "resource_id": "48bb51cf-88c2-40a9-a55c-d7683ea92163",
        "filename": "cenace_capacidadinstalada_cd_2023-enero_marzo.csv",
        "format": "csv", "target_table": "installed_capacity",
        "period": "2023-Q1", "year": "2023",
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
