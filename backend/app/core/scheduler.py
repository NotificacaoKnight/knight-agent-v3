"""
Background Task Scheduler for FastAPI
Handles scheduled tasks like audio cleanup
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.audio_cleanup_service import audio_cleanup_service

logger = logging.getLogger(__name__)


# Create scheduler instance
scheduler = AsyncIOScheduler()


async def cleanup_audio_files_job():
    """
    Scheduled job to cleanup expired audio files

    Runs daily at 3 AM (configurable)
    """
    try:
        logger.info("🧹 Starting scheduled audio cleanup...")
        files_deleted, space_freed_mb = await audio_cleanup_service.cleanup_expired_audios()

        if files_deleted > 0:
            logger.info(
                f"✅ Audio cleanup complete: "
                f"{files_deleted} files deleted, {space_freed_mb}MB freed"
            )
        else:
            logger.info("✅ Audio cleanup complete: No expired files found")

    except Exception as e:
        logger.error(f"❌ Audio cleanup job failed: {e}", exc_info=True)


def setup_scheduler():
    """
    Configure scheduled tasks

    Jobs:
    - Audio cleanup: Daily at 3 AM (server time)
    """
    # Clear any existing jobs (for dev reload)
    scheduler.remove_all_jobs()

    # Add audio cleanup job - runs daily at 3 AM
    scheduler.add_job(
        cleanup_audio_files_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='audio_cleanup',
        name='Audio Files Cleanup',
        replace_existing=True
    )

    logger.info("📅 Scheduler configured:")
    logger.info("  - Audio cleanup: Daily at 3:00 AM")


def start_scheduler():
    """Start the background scheduler"""
    setup_scheduler()
    scheduler.start()
    logger.info("🚀 Background scheduler started")


def shutdown_scheduler():
    """Shutdown the background scheduler"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("🛑 Background scheduler stopped")
