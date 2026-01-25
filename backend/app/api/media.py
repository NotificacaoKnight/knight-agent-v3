"""
Media API endpoints for FastAPI
Serves audio files and other media content
"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/audios/{year}/{month}/{filename}")
async def serve_audio_file(year: str, month: str, filename: str):
    """
    Serve audio file from media storage

    Args:
        year: Year directory (e.g., "2025")
        month: Month directory (e.g., "01")
        filename: Audio filename (e.g., "user_5_20250108_153045.webm")

    Returns:
        FileResponse with audio file
    """
    try:
        # Construct file path
        file_path = settings.MEDIA_DIR / "audios" / year / month / filename

        # Security check: ensure path is within media directory
        resolved_path = file_path.resolve()
        media_dir_resolved = settings.MEDIA_DIR.resolve()

        if not str(resolved_path).startswith(str(media_dir_resolved)):
            logger.warning(f"Path traversal attempt: {file_path}")
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Audio file not found: {file_path}")
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Check if file is actually a file (not directory)
        if not file_path.is_file():
            logger.warning(f"Invalid file type: {file_path}")
            raise HTTPException(status_code=400, detail="Invalid file")

        # Determine media type based on extension
        suffix = file_path.suffix.lower()
        media_types = {
            '.webm': 'audio/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
        }

        media_type = media_types.get(suffix, 'application/octet-stream')

        logger.info(f"Serving audio file: {file_path}")

        # Return file
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error serving audio file")
