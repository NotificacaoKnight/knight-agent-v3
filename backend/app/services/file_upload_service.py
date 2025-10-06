"""
File upload and management service for FastAPI
Handles file validation, storage, and processing
"""
import os
import hashlib
import shutil
import logging
from typing import Optional, BinaryIO
from pathlib import Path
from fastapi import UploadFile, HTTPException
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileUploadService:
    """Service for managing file uploads"""

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.docx', '.doc', '.xlsx', '.xls',
        '.pptx', '.ppt', '.txt', '.md', '.csv'
    }

    # Max file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(self):
        self.upload_dir = Path(settings.MEDIA_ROOT) / 'uploads'
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def validate_file(
        self,
        file: UploadFile
    ) -> tuple[bool, Optional[str]]:
        """
        Validate uploaded file

        Args:
            file: Uploaded file

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"

        # Check file size (approximate check)
        file.file.seek(0, 2)  # Go to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > self.MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"

        return True, None

    async def save_uploaded_file(
        self,
        file: UploadFile,
        user_id: int,
        custom_filename: Optional[str] = None
    ) -> tuple[str, str, int]:
        """
        Save uploaded file to disk

        Args:
            file: Uploaded file
            user_id: User ID for organizing files
            custom_filename: Optional custom filename

        Returns:
            Tuple of (file_path, checksum, file_size)
        """
        try:
            # Create user directory
            user_dir = self.upload_dir / str(user_id)
            user_dir.mkdir(exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            original_name = Path(file.filename).stem
            extension = Path(file.filename).suffix

            if custom_filename:
                filename = f"{custom_filename}{extension}"
            else:
                filename = f"{timestamp}_{original_name}{extension}"

            file_path = user_dir / filename

            # Ensure unique filename
            counter = 1
            while file_path.exists():
                stem = Path(filename).stem
                filename = f"{stem}_{counter}{extension}"
                file_path = user_dir / filename
                counter += 1

            # Save file and calculate checksum
            checksum = hashlib.sha256()
            file_size = 0

            with open(file_path, 'wb') as f:
                while chunk := await file.read(8192):
                    f.write(chunk)
                    checksum.update(chunk)
                    file_size += len(chunk)

            # Return relative path for database storage
            relative_path = str(file_path.relative_to(settings.MEDIA_ROOT))

            logger.info(f"File saved: {relative_path} (size: {file_size} bytes)")

            return relative_path, checksum.hexdigest(), file_size

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from disk

        Args:
            file_path: Relative file path

        Returns:
            Success status
        """
        try:
            full_path = Path(settings.MEDIA_ROOT) / file_path

            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    async def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get file information

        Args:
            file_path: Relative file path

        Returns:
            File info dict or None
        """
        try:
            full_path = Path(settings.MEDIA_ROOT) / file_path

            if not full_path.exists():
                return None

            stat = full_path.stat()

            return {
                'path': file_path,
                'name': full_path.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime)
            }

        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    async def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up files older than specified days

        Args:
            days: Number of days to keep files

        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now(timezone.utc).timestamp() - (days * 86400)

            for file_path in self.upload_dir.rglob('*'):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA256 checksum of file

        Args:
            file_path: Full file path

        Returns:
            Checksum hex string
        """
        try:
            sha256 = hashlib.sha256()
            full_path = Path(settings.MEDIA_ROOT) / file_path

            with open(full_path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""


# Singleton instance
file_upload_service = FileUploadService()