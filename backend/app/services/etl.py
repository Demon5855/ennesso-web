"""ETL Orchestrator — runs all ingestion pipelines in priority order.

Each pipeline is wrapped in try/except so one failure does not abort others.
Returns an IngestSummary with aggregate counts and all warnings/errors.

Usage::

    from app.services.etl import run_full_ingestion

    summary = await run_full_ingestion()
    print(f"Inserted {summary.total_inserted} records in {summary.duration_seconds:.1f}s")
"""

import logging
from datetime import datetime

from app.models.ingest import IngestSummary
from app.pipelines.cenace_realtime import run_cenace_realtime_pipeline
from app.pipelines.cenace_ckan import run_ckan_pipeline

logger = logging.getLogger(__name__)


async def run_full_ingestion() -> IngestSummary:
    """Run all pipelines in priority order.

    Priority 1: CENACE real-time HTML scraper (fresh daily data).
    Priority 2: CKAN historical downloads (quarterly, only if new data).

    Each pipeline is wrapped in try/except — one failure does not kill others.

    Returns:
        ``IngestSummary`` with records_inserted, warnings, errors, duration
        aggregated across all pipelines.
    """
    summary = IngestSummary(started_at=datetime.utcnow())
    logger.info("Starting full ingestion cycle")

    # ------------------------------------------------------------------
    # Priority 1 — CENACE real-time HTML scraper
    # ------------------------------------------------------------------
    try:
        logger.info("Running pipeline: cenace_realtime")
        realtime_result = await run_cenace_realtime_pipeline()
        summary.pipelines.append(realtime_result)

        if realtime_result.success:
            logger.info(
                "cenace_realtime: %d inserted in %.1fs",
                realtime_result.records_inserted,
                realtime_result.duration_seconds,
            )
        else:
            logger.error(
                "cenace_realtime completed with %d errors",
                len(realtime_result.errors),
            )

    except Exception as exc:
        logger.exception("cenace_realtime pipeline raised unexpected error: %s", exc)
        from app.models.ingest import PipelineResult
        summary.pipelines.append(
            PipelineResult(
                pipeline="cenace_realtime",
                errors=[f"Unexpected exception: {exc}"],
            )
        )

    # ------------------------------------------------------------------
    # Priority 2 — CKAN historical quarterly downloads
    # ------------------------------------------------------------------
    try:
        logger.info("Running pipeline: cenace_ckan")
        ckan_result = await run_ckan_pipeline()
        summary.pipelines.append(ckan_result)

        if ckan_result.success:
            logger.info(
                "cenace_ckan: %d inserted, %d skipped in %.1fs",
                ckan_result.records_inserted,
                ckan_result.records_skipped,
                ckan_result.duration_seconds,
            )
        else:
            logger.error(
                "cenace_ckan completed with %d errors", len(ckan_result.errors)
            )

    except Exception as exc:
        logger.exception("cenace_ckan pipeline raised unexpected error: %s", exc)
        from app.models.ingest import PipelineResult
        summary.pipelines.append(
            PipelineResult(
                pipeline="cenace_ckan",
                errors=[f"Unexpected exception: {exc}"],
            )
        )

    summary.finished_at = datetime.utcnow()

    logger.info(
        "Full ingestion cycle complete: %d inserted, %d warnings, %d errors in %.1fs",
        summary.total_inserted,
        summary.total_warnings,
        summary.total_errors,
        summary.duration_seconds,
    )

    return summary
