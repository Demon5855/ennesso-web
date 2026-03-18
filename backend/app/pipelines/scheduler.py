"""APScheduler configuration for Ennesso background jobs.

Jobs:
1. cenace_realtime_scrape — Daily at 02:00 ECT (UTC-5 = 07:00 UTC)
2. ckan_weekly_check — Weekly on Monday at 03:00 UTC (detect new quarterly data)
3. supabase_keepalive — Every 5 days (prevents Supabase free tier pause)

Integrate with FastAPI lifespan:

    from app.pipelines.scheduler import create_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = create_scheduler()
        scheduler.start()
        yield
        scheduler.shutdown()
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------


async def job_cenace_realtime() -> None:
    """Scheduled job: run the CENACE real-time HTML scraper.

    Runs daily at 02:00 ECT. Logs a summary on completion.
    Errors are caught here so the scheduler keeps running.
    """
    from app.services.etl import run_full_ingestion

    logger.info("[scheduler] Starting scheduled ingestion cycle")
    try:
        summary = await run_full_ingestion()
        logger.info(
            "[scheduler] Ingestion complete: %d inserted, %d warnings, %d errors",
            summary.total_inserted,
            summary.total_warnings,
            summary.total_errors,
        )
    except Exception as exc:
        logger.exception("[scheduler] Ingestion cycle failed unexpectedly: %s", exc)


async def job_ckan_weekly_check() -> None:
    """Scheduled job: check for new CKAN quarterly data.

    Runs weekly. Only downloads resources not yet ingested.
    """
    from app.pipelines.cenace_ckan import run_ckan_pipeline

    logger.info("[scheduler] Running weekly CKAN check")
    try:
        result = await run_ckan_pipeline()
        logger.info(
            "[scheduler] CKAN check done: %d inserted, %d skipped",
            result.records_inserted,
            result.records_skipped,
        )
    except Exception as exc:
        logger.exception("[scheduler] CKAN weekly check failed: %s", exc)


async def job_supabase_keepalive() -> None:
    """Scheduled job: keepalive ping to prevent Supabase free tier pause.

    Runs every 5 days. Performs a lightweight SELECT to keep the project active.
    """
    from app.db.client import get_client

    logger.info("[scheduler] Supabase keepalive ping")
    try:
        client = await get_client()
        await client.table("energy_records").select("id").limit(1).execute()
        logger.info("[scheduler] Keepalive OK at %s", datetime.utcnow().isoformat())
    except Exception as exc:
        logger.error("[scheduler] Keepalive failed: %s", exc)


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Reads cron expression from ``settings.scheduler_ingestion_cron``.
    Falls back to daily at 07:00 UTC (02:00 ECT) if the env var is not set.

    Returns:
        Configured ``AsyncIOScheduler`` — not yet started. Call
        ``scheduler.start()`` in the FastAPI lifespan context.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # ------------------------------------------------------------------
    # Job 1: Daily ingestion — CENACE real-time + ETL orchestrator
    # Use cron from settings, default 07:00 UTC = 02:00 ECT
    # ------------------------------------------------------------------
    try:
        cron_parts = settings.scheduler_ingestion_cron.split()
        if len(cron_parts) == 5:
            minute, hour, day, month, day_of_week = cron_parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone="UTC",
            )
        else:
            raise ValueError("Invalid cron expression length")
    except Exception:
        logger.warning(
            "Invalid SCHEDULER_INGESTION_CRON='%s', defaulting to '0 7 * * *'",
            settings.scheduler_ingestion_cron,
        )
        trigger = CronTrigger(hour=7, minute=0, timezone="UTC")

    scheduler.add_job(
        job_cenace_realtime,
        trigger=trigger,
        id="cenace_realtime_daily",
        name="CENACE Real-Time Daily Ingestion",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    # ------------------------------------------------------------------
    # Job 2: Weekly CKAN check — Mondays at 03:00 UTC
    # ------------------------------------------------------------------
    scheduler.add_job(
        job_ckan_weekly_check,
        trigger=CronTrigger(day_of_week="mon", hour=3, minute=0, timezone="UTC"),
        id="ckan_weekly_check",
        name="CKAN Weekly New Data Check",
        replace_existing=True,
        max_instances=1,
    )

    # ------------------------------------------------------------------
    # Job 3: Supabase keepalive — every 5 days
    # ------------------------------------------------------------------
    scheduler.add_job(
        job_supabase_keepalive,
        trigger=IntervalTrigger(days=5),
        id="supabase_keepalive",
        name="Supabase Free Tier Keepalive",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured: %d jobs registered",
        len(scheduler.get_jobs()),
    )
    return scheduler
