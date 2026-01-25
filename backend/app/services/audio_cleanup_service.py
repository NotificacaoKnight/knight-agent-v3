"""
Audio Cleanup Service - Automatic removal of expired audio files
Deletes audio files older than retention period while preserving transcriptions
"""
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_async_db
from app.models.chat import ChatMessage
from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioCleanupService:
    """
    Service for cleaning up expired audio files

    - Deletes audio files older than AUDIO_RETENTION_DAYS
    - Sets audio_file field to NULL in database
    - Preserves transcriptions and metadata
    - Runs as scheduled background task
    """

    def __init__(self):
        self.media_dir = settings.MEDIA_DIR
        self.retention_days = getattr(settings, 'AUDIO_RETENTION_DAYS', 30)

    async def cleanup_expired_audios(self) -> Tuple[int, int]:
        """
        Remove audio files older than retention period

        Returns:
            Tuple of (files_deleted, space_freed_mb)
        """
        logger.info(f"Starting audio cleanup (retention: {self.retention_days} days)")

        files_deleted = 0
        space_freed = 0

        try:
            async for db in get_async_db():
                # Calculate cutoff date
                cutoff_date = datetime.now() - timedelta(days=self.retention_days)

                # Find messages with audio files older than retention period
                query = select(ChatMessage).where(
                    ChatMessage.audio_file.isnot(None),
                    ChatMessage.created_at < cutoff_date
                )

                result = await db.execute(query)
                expired_messages = result.scalars().all()

                logger.info(f"Found {len(expired_messages)} messages with expired audio files")

                for message in expired_messages:
                    try:
                        # Construct full file path
                        file_path = self.media_dir / message.audio_file

                        # Delete file if it exists
                        if file_path.exists():
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            files_deleted += 1
                            space_freed += file_size
                            logger.debug(f"Deleted: {message.audio_file}")

                        # Update database: set audio_file to NULL but keep transcription
                        message.audio_file = None
                        # transcription, audio_duration remain intact

                    except Exception as e:
                        logger.error(f"Error deleting audio file {message.audio_file}: {e}")
                        continue

                # Commit all changes
                await db.commit()

                # Log summary
                space_freed_mb = space_freed / (1024 * 1024)
                logger.info(
                    f"Cleanup complete: deleted {files_deleted} files, "
                    f"freed {space_freed_mb:.2f}MB"
                )

                # Cleanup empty directories
                await self._cleanup_empty_directories()

                return files_deleted, int(space_freed_mb)

        except Exception as e:
            logger.error(f"Audio cleanup failed: {e}", exc_info=True)
            return 0, 0

    async def _cleanup_empty_directories(self):
        """
        Remove empty year/month directories after cleanup

        Walks through audios directory and removes empty subdirectories
        """
        try:
            audios_dir = self.media_dir / "audios"

            if not audios_dir.exists():
                return

            # Walk directory tree bottom-up to remove empty dirs
            for root, dirs, files in os.walk(audios_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        # Try to remove if empty
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            logger.debug(f"Removed empty directory: {dir_path}")
                    except OSError:
                        # Directory not empty or other error, skip
                        pass

        except Exception as e:
            logger.warning(f"Error cleaning empty directories: {e}")

    async def get_cleanup_stats(self) -> dict:
        """
        Get statistics about audio files eligible for cleanup

        Returns:
            Dict with cleanup statistics
        """
        try:
            async for db in get_async_db():
                cutoff_date = datetime.now() - timedelta(days=self.retention_days)

                # Count expired files
                query = select(ChatMessage).where(
                    ChatMessage.audio_file.isnot(None),
                    ChatMessage.created_at < cutoff_date
                )
                result = await db.execute(query)
                expired_count = len(result.scalars().all())

                # Count total audio files
                query_total = select(ChatMessage).where(
                    ChatMessage.audio_file.isnot(None)
                )
                result_total = await db.execute(query_total)
                total_count = len(result_total.scalars().all())

                return {
                    "retention_days": self.retention_days,
                    "expired_files": expired_count,
                    "total_files": total_count,
                    "active_files": total_count - expired_count,
                    "cutoff_date": cutoff_date.isoformat()
                }

        except Exception as e:
            logger.error(f"Error getting cleanup stats: {e}")
            return {
                "error": str(e)
            }


# Singleton instance
audio_cleanup_service = AudioCleanupService()
