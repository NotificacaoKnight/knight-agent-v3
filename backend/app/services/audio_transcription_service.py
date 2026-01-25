"""
Audio Transcription Service - Groq Whisper Integration
Handles audio file processing, transcription, and storage management
"""
import os
import logging
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
import asyncio
import subprocess
import tempfile

from fastapi import HTTPException, UploadFile
from groq import AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """
    Service for transcribing audio files using Groq Whisper

    Features:
    - Audio transcription with Whisper Large v3
    - File storage management
    - Audio duration calculation
    - Format validation
    """

    # Supported audio formats
    SUPPORTED_FORMATS = {
        'audio/webm', 'audio/mpeg', 'audio/mp3', 'audio/wav',
        'audio/m4a', 'audio/mp4', 'audio/ogg', 'audio/x-m4a'
    }

    # Maximum file size: 25MB
    MAX_FILE_SIZE = 25 * 1024 * 1024

    def __init__(self):
        self.client = None
        self.media_dir = settings.MEDIA_DIR
        self.audios_dir = self.media_dir / "audios"

    async def initialize(self):
        """Initialize Groq client and create necessary directories"""
        if self.client:
            return

        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured in environment")

        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        # Create media directories
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.audios_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Audio transcription service initialized")

    def _validate_audio_file(self, audio_file: UploadFile, audio_bytes: bytes) -> None:
        """
        Validate audio file format and size

        Args:
            audio_file: Uploaded file object
            audio_bytes: File content bytes

        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        if len(audio_bytes) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo muito grande. Máximo: {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )

        # Check content type
        content_type = audio_file.content_type
        if content_type not in self.SUPPORTED_FORMATS:
            # Try to guess from filename
            guessed_type, _ = mimetypes.guess_type(audio_file.filename)
            if guessed_type not in self.SUPPORTED_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de áudio não suportado: {content_type}. "
                           f"Formatos aceitos: WebM, MP3, WAV, M4A, OGG"
                )

        logger.info(f"Audio file validated: {audio_file.filename}, "
                   f"size={len(audio_bytes)/1024:.1f}KB, type={content_type}")

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm"
    ) -> str:
        """
        Transcribe audio using Groq Whisper

        Args:
            audio_bytes: Audio file content
            filename: Original filename (for extension detection)

        Returns:
            Transcribed text

        Raises:
            HTTPException: If transcription fails
        """
        if not self.client:
            await self.initialize()

        try:
            # Ensure filename has proper extension for Groq API
            # If filename is "blob" or has no extension, add .webm
            if filename == "blob" or not any(filename.endswith(ext) for ext in ['.webm', '.mp3', '.wav', '.m4a', '.ogg', '.opus', '.flac', '.mp4', '.mpeg', '.mpga']):
                filename = "audio.webm"

            # Groq Whisper API requires file-like object
            transcription = await self.client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model="whisper-large-v3",
                language="pt",  # Portuguese
                response_format="text"
            )

            transcribed_text = transcription.strip()
            logger.info(f"Audio transcribed successfully: {len(transcribed_text)} characters")

            return transcribed_text

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao transcrever áudio: {str(e)}"
            )

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        ext = Path(filename).suffix
        if not ext:
            ext = '.webm'  # Default
        return ext

    async def save_audio_file(
        self,
        audio_bytes: bytes,
        user_id: int,
        filename: str
    ) -> str:
        """
        Save audio file to disk with organized directory structure

        Args:
            audio_bytes: Audio file content
            user_id: User ID for organization
            filename: Original filename

        Returns:
            Relative path to saved file (e.g., "audios/2025/01/user_5_msg_123.webm")
        """
        # Create year/month directory structure
        now = datetime.now()
        year_month_dir = self.audios_dir / str(now.year) / f"{now.month:02d}"
        year_month_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        ext = self._get_file_extension(filename)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        new_filename = f"user_{user_id}_{timestamp}{ext}"
        file_path = year_month_dir / new_filename

        # Save file
        with open(file_path, 'wb') as f:
            f.write(audio_bytes)

        # Return relative path from media directory
        relative_path = file_path.relative_to(self.media_dir)
        logger.info(f"Audio saved: {relative_path}")

        return str(relative_path)

    async def get_audio_duration(self, audio_bytes: bytes, filename: str) -> float:
        """
        Calculate audio duration using ffprobe

        Args:
            audio_bytes: Audio file content
            filename: Original filename

        Returns:
            Duration in seconds (float)
        """
        try:
            # Create temporary file for ffprobe
            with tempfile.NamedTemporaryFile(suffix=self._get_file_extension(filename), delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                # Run ffprobe to get duration
                result = await asyncio.create_subprocess_exec(
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    tmp_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await result.communicate()

                if result.returncode == 0:
                    duration = float(stdout.decode().strip())
                    logger.info(f"Audio duration: {duration:.2f}s")
                    return round(duration, 2)
                else:
                    logger.warning(f"ffprobe failed: {stderr.decode()}")
                    return 0.0

            finally:
                # Cleanup temp file
                os.unlink(tmp_path)

        except FileNotFoundError:
            logger.warning("ffprobe not found, cannot calculate duration")
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
            return 0.0

    async def process_audio(
        self,
        audio_file: UploadFile,
        user_id: int
    ) -> Tuple[str, str, float]:
        """
        Complete audio processing pipeline

        Args:
            audio_file: Uploaded audio file
            user_id: User ID

        Returns:
            Tuple of (transcription, file_path, duration)

        Raises:
            HTTPException: If processing fails
        """
        # Read file content
        audio_bytes = await audio_file.read()

        # Validate
        self._validate_audio_file(audio_file, audio_bytes)

        # Process in parallel for performance
        transcription_task = self.transcribe_audio(audio_bytes, audio_file.filename)
        duration_task = self.get_audio_duration(audio_bytes, audio_file.filename)
        save_task = self.save_audio_file(audio_bytes, user_id, audio_file.filename)

        # Wait for all tasks
        transcription, duration, file_path = await asyncio.gather(
            transcription_task,
            duration_task,
            save_task
        )

        logger.info(
            f"Audio processing complete: "
            f"transcription={len(transcription)} chars, "
            f"duration={duration}s, "
            f"path={file_path}"
        )

        return transcription, file_path, duration


# Singleton instance
audio_transcription_service = AudioTranscriptionService()
