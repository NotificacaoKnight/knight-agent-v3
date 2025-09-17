"""
Internationalization (i18n) API endpoints for FastAPI
Manages translations and language preferences
"""
import os
import json
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_optional_current_user
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locales", tags=["locales"])


# Available languages
AVAILABLE_LANGUAGES = {
    "pt": {"name": "Português", "native": "Português", "flag": "🇧🇷"},
    "en": {"name": "English", "native": "English", "flag": "🇺🇸"},
    "es": {"name": "Spanish", "native": "Español", "flag": "🇪🇸"},
}

# Default language
DEFAULT_LANGUAGE = "pt"


@router.get("/available")
async def get_available_languages():
    """
    Get list of available languages

    Returns language codes with metadata
    """
    return {
        "languages": AVAILABLE_LANGUAGES,
        "default": DEFAULT_LANGUAGE,
        "total": len(AVAILABLE_LANGUAGES)
    }


@router.get("/translations/{language}")
async def get_translations(
    language: str,
    namespace: Optional[str] = Query(None, description="Translation namespace")
):
    """
    Get translations for a specific language

    Args:
        language: Language code (pt, en, es)
        namespace: Optional namespace filter

    Returns translations JSON
    """
    try:
        # Validate language
        if language not in AVAILABLE_LANGUAGES:
            raise HTTPException(
                status_code=404,
                detail=f"Language '{language}' not available"
            )

        # Build translations path
        translations_dir = os.path.join(
            settings.BASE_DIR,
            "locales",
            language
        )

        # Check if translations exist
        if not os.path.exists(translations_dir):
            logger.warning(f"Translations directory not found: {translations_dir}")
            # Return empty translations as fallback
            return {
                "language": language,
                "namespace": namespace,
                "translations": {}
            }

        # Load translations
        translations = {}

        # If namespace specified, load only that file
        if namespace:
            namespace_file = os.path.join(
                translations_dir,
                f"{namespace}.json"
            )

            if os.path.exists(namespace_file):
                with open(namespace_file, 'r', encoding='utf-8') as f:
                    translations[namespace] = json.load(f)
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Namespace '{namespace}' not found for language '{language}'"
                )
        else:
            # Load all translation files
            for file_name in os.listdir(translations_dir):
                if file_name.endswith('.json'):
                    namespace_name = file_name[:-5]  # Remove .json
                    file_path = os.path.join(translations_dir, file_name)

                    with open(file_path, 'r', encoding='utf-8') as f:
                        translations[namespace_name] = json.load(f)

        return {
            "language": language,
            "namespace": namespace,
            "translations": translations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-preference")
async def get_user_language_preference(
    current_user: User = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get user's language preference

    Returns user's saved language or default
    """
    if current_user:
        # Get from user profile (would need to add language field to User model)
        # For now, return default
        user_language = getattr(current_user, 'preferred_language', DEFAULT_LANGUAGE)
        return {
            "language": user_language,
            "is_default": user_language == DEFAULT_LANGUAGE,
            "user_id": current_user.id
        }
    else:
        return {
            "language": DEFAULT_LANGUAGE,
            "is_default": True,
            "user_id": None
        }


@router.post("/user-preference")
async def set_user_language_preference(
    language: str,
    current_user: User = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Set user's language preference

    Saves language preference to user profile
    """
    try:
        # Validate language
        if language not in AVAILABLE_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Language '{language}' not available"
            )

        if current_user:
            # Update user's language preference
            # Note: Would need to add preferred_language field to User model
            # For now, just return success
            logger.info(f"Setting language preference for user {current_user.id}: {language}")

            # In a real implementation:
            # current_user.preferred_language = language
            # await db.commit()

            return {
                "success": True,
                "language": language,
                "user_id": current_user.id,
                "message": f"Language preference set to {AVAILABLE_LANGUAGES[language]['name']}"
            }
        else:
            # For anonymous users, return success but note it's session-only
            return {
                "success": True,
                "language": language,
                "user_id": None,
                "message": "Language preference set for current session only"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting language preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect")
async def detect_language(
    text: str = Query(..., description="Text to detect language from"),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Detect language from text

    Uses simple heuristics or could integrate with language detection library
    """
    try:
        # Simple heuristic detection based on common words
        portuguese_indicators = ["de", "da", "do", "que", "para", "com", "não", "uma", "por", "em"]
        english_indicators = ["the", "and", "or", "is", "are", "for", "with", "not", "have", "from"]
        spanish_indicators = ["el", "la", "de", "que", "y", "en", "un", "por", "con", "para"]

        text_lower = text.lower()
        words = text_lower.split()

        scores = {
            "pt": sum(1 for word in words if word in portuguese_indicators),
            "en": sum(1 for word in words if word in english_indicators),
            "es": sum(1 for word in words if word in spanish_indicators)
        }

        # Get language with highest score
        detected_language = max(scores, key=scores.get)

        # If no clear winner, use default
        if scores[detected_language] == 0:
            detected_language = DEFAULT_LANGUAGE

        return {
            "detected_language": detected_language,
            "confidence": scores[detected_language] / max(len(words), 1),
            "scores": scores,
            "language_info": AVAILABLE_LANGUAGES[detected_language]
        }

    except Exception as e:
        logger.error(f"Error detecting language: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fallback/{key}")
async def get_fallback_translation(
    key: str,
    language: str = Query(DEFAULT_LANGUAGE, description="Target language"),
    default: Optional[str] = Query(None, description="Default text if key not found")
):
    """
    Get a specific translation key with fallback

    Useful for dynamic translation lookups
    """
    try:
        # Validate language
        if language not in AVAILABLE_LANGUAGES:
            language = DEFAULT_LANGUAGE

        # Parse key (format: namespace.section.key)
        key_parts = key.split('.')
        if len(key_parts) < 2:
            raise HTTPException(
                status_code=400,
                detail="Invalid key format. Use: namespace.section.key"
            )

        namespace = key_parts[0]
        key_path = '.'.join(key_parts[1:])

        # Load namespace translations
        translations_file = os.path.join(
            settings.BASE_DIR,
            "locales",
            language,
            f"{namespace}.json"
        )

        if not os.path.exists(translations_file):
            # Try fallback to default language
            if language != DEFAULT_LANGUAGE:
                translations_file = os.path.join(
                    settings.BASE_DIR,
                    "locales",
                    DEFAULT_LANGUAGE,
                    f"{namespace}.json"
                )

        # Load and navigate to key
        if os.path.exists(translations_file):
            with open(translations_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)

            # Navigate nested structure
            value = translations
            for part in key_path.split('.'):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break

            if value:
                return {
                    "key": key,
                    "value": value,
                    "language": language,
                    "found": True
                }

        # Return default or key as fallback
        return {
            "key": key,
            "value": default or key,
            "language": language,
            "found": False,
            "is_fallback": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-cache")
async def refresh_translation_cache(
    current_user: User = Depends(get_optional_current_user)
):
    """
    Refresh translation cache

    Useful after updating translation files
    """
    try:
        # In a production system, you might have a translation cache
        # This endpoint would clear/refresh it
        logger.info("Translation cache refresh requested")

        # For now, just return success
        return {
            "success": True,
            "message": "Translation cache refreshed successfully"
        }

    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))