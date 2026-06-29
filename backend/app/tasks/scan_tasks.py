from celery import Celery
import asyncio
import structlog
import uuid

from app.core.config import settings

logger = structlog.get_logger()

# Celery app instance
# broker: Redis receives and queues tasks
# backend: Redis stores task results and state
celery_app = Celery(
    "dark_pattern_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry failed tasks up to 3 times with exponential backoff
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker
)


@celery_app.task(
    name="tasks.run_scan",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def run_scan_task(self, scan_id: str, url: str, user_id: str):
    """
    Celery task that runs the full scan pipeline.

    Why 'bind=True'? Gives access to 'self' — the task instance.
    We need self.retry() to retry on failure.

    Why run async code in a sync Celery task?
    Celery workers are synchronous. Our scanner and AI pipeline
    are async. We use asyncio.run() to bridge them —
    each task gets its own event loop.

    In production, you could use celery[eventlet] or celery[gevent]
    for async workers, but asyncio.run() is simpler and sufficient
    for our scan volume.
    """
    try:
        asyncio.run(_run_scan_async(scan_id, url, user_id))
    except Exception as exc:
        logger.exception(
            "Scan task failed",
            scan_id=scan_id,
        )
        raise


async def _run_scan_async(scan_id: str, url: str, user_id: str):
    """
    The actual async scan workflow.
    Separated from the task so it's independently testable.
    """
    from app.db.session import AsyncSessionLocal
    from app.services.scanner import WebScanner, ScannerError
    from app.services.ai_pipeline import AIPipeline
    from app.services.report import ReportService
    from app.repositories.scan import ScanRepository
    from app.db.models.scan import ScanStatus

    async with AsyncSessionLocal() as db:
        scan_repo = ScanRepository(db)
        scan = await scan_repo.get_by_id(uuid.UUID(scan_id))

        if not scan:
            logger.error("Scan not found", scan_id=scan_id)
            return

        # Mark as processing
        await scan_repo.update_status(
            scan.id, ScanStatus.PROCESSING
        )
        await db.commit()

        try:
            # Step 1: Scrape the website
            logger.info("Scanning URL", url=url, scan_id=scan_id)
            scanner = WebScanner()
            scan_data = await scanner.scan(url, scan_id)

            # Step 2: Run AI pipeline
            logger.info("Running AI pipeline", scan_id=scan_id)
            pipeline = AIPipeline()
            pipeline_result = await pipeline.run(scan_data)

            # Step 3: Save results
            report_service = ReportService(db)
            await report_service.build_and_save(scan, pipeline_result, scan_data)
            await db.commit()

            logger.info(
                "Scan completed successfully",
                scan_id=scan_id,
                patterns=pipeline_result.patterns_found,
                risk_score=pipeline_result.risk_score,
            )

        except ScannerError as e:
            logger.error("Scanner error", scan_id=scan_id, error=str(e))
            await scan_repo.update_status(
                scan.id,
                ScanStatus.FAILED,
                error_message=str(e),
            )
            await db.commit()
            raise

        except Exception as e:
            logger.error("Pipeline error", scan_id=scan_id, error=str(e))
            await scan_repo.update_status(
                scan.id,
                ScanStatus.FAILED,
                error_message=f"Analysis failed: {str(e)}",
            )
            await db.commit()
            raise
        