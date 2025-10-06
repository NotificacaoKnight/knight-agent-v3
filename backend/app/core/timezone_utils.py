"""
Timezone utilities for consistent datetime handling
"""
from datetime import datetime, timezone
from typing import Optional, Union
import pytz
from zoneinfo import ZoneInfo

from app.core.config import settings


def utc_now() -> datetime:
    """
    Get current UTC datetime (modern replacement for datetime.utcnow())

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def local_now(tz_name: Optional[str] = None) -> datetime:
    """
    Get current datetime in specified timezone

    Args:
        tz_name: Timezone name (e.g., 'America/Sao_Paulo').
                Falls back to settings.TIME_ZONE if not provided.

    Returns:
        datetime: Current time in specified timezone
    """
    if tz_name is None:
        tz_name = getattr(settings, 'TIME_ZONE', 'America/Sao_Paulo')

    try:
        # Use zoneinfo (Python 3.9+) first, fallback to pytz
        tz = ZoneInfo(tz_name)
    except Exception:
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            # Fallback to UTC if timezone not found
            tz = timezone.utc

    return datetime.now(tz)


def convert_utc_to_local(
    utc_dt: datetime,
    target_tz: Optional[str] = None
) -> datetime:
    """
    Convert UTC datetime to local timezone

    Args:
        utc_dt: UTC datetime (timezone-aware or naive)
        target_tz: Target timezone name

    Returns:
        datetime: Converted datetime in target timezone
    """
    if target_tz is None:
        target_tz = getattr(settings, 'TIME_ZONE', 'America/Sao_Paulo')

    # Ensure UTC datetime is timezone-aware
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    elif utc_dt.tzinfo != timezone.utc:
        utc_dt = utc_dt.astimezone(timezone.utc)

    try:
        # Convert to target timezone
        target_tz_obj = ZoneInfo(target_tz)
    except Exception:
        try:
            target_tz_obj = pytz.timezone(target_tz)
        except Exception:
            # Return UTC if conversion fails
            return utc_dt

    return utc_dt.astimezone(target_tz_obj)


def convert_local_to_utc(
    local_dt: datetime,
    source_tz: Optional[str] = None
) -> datetime:
    """
    Convert local datetime to UTC

    Args:
        local_dt: Local datetime (timezone-aware or naive)
        source_tz: Source timezone name (required if local_dt is naive)

    Returns:
        datetime: UTC datetime
    """
    if source_tz is None:
        source_tz = getattr(settings, 'TIME_ZONE', 'America/Sao_Paulo')

    # Make timezone-aware if needed
    if local_dt.tzinfo is None:
        try:
            source_tz_obj = ZoneInfo(source_tz)
        except Exception:
            try:
                source_tz_obj = pytz.timezone(source_tz)
            except Exception:
                source_tz_obj = timezone.utc

        local_dt = local_dt.replace(tzinfo=source_tz_obj)

    return local_dt.astimezone(timezone.utc)


def format_datetime_with_timezone(
    dt: datetime,
    include_timezone: bool = True,
    user_tz: Optional[str] = None
) -> str:
    """
    Format datetime as ISO 8601 string with timezone info

    Args:
        dt: Datetime to format
        include_timezone: Whether to include timezone in output
        user_tz: Convert to this timezone before formatting

    Returns:
        str: ISO 8601 formatted datetime
    """
    if dt is None:
        return None

    # Convert to user timezone if requested
    if user_tz and dt.tzinfo:
        dt = convert_utc_to_local(dt, user_tz)

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if include_timezone:
        return dt.isoformat()
    else:
        return dt.replace(tzinfo=None).isoformat()


def get_user_timezone(user_id: Optional[int] = None) -> str:
    """
    Get user's preferred timezone (placeholder for future user preference)

    Args:
        user_id: User ID to get timezone for

    Returns:
        str: Timezone name
    """
    # TODO: In future, lookup user preference from database
    # For now, return system default
    return getattr(settings, 'TIME_ZONE', 'America/Sao_Paulo')


def is_timezone_aware(dt: datetime) -> bool:
    """
    Check if datetime is timezone-aware

    Args:
        dt: Datetime to check

    Returns:
        bool: True if timezone-aware
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


class TimezoneAwareDatetime:
    """
    Context manager for timezone-aware datetime operations
    """

    def __init__(self, timezone_name: Optional[str] = None):
        self.timezone_name = timezone_name or getattr(settings, 'TIME_ZONE', 'America/Sao_Paulo')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def now(self) -> datetime:
        """Get current time in configured timezone"""
        return local_now(self.timezone_name)

    def utc_now(self) -> datetime:
        """Get current UTC time"""
        return utc_now()

    def convert_to_local(self, utc_dt: datetime) -> datetime:
        """Convert UTC to local timezone"""
        return convert_utc_to_local(utc_dt, self.timezone_name)

    def convert_to_utc(self, local_dt: datetime) -> datetime:
        """Convert local to UTC"""
        return convert_local_to_utc(local_dt, self.timezone_name)


# Common timezone instances for Brazil
BRAZIL_TZ = TimezoneAwareDatetime('America/Sao_Paulo')

# Helper aliases for common operations
brazil_now = lambda: local_now('America/Sao_Paulo')
utc_to_brazil = lambda dt: convert_utc_to_local(dt, 'America/Sao_Paulo')
brazil_to_utc = lambda dt: convert_local_to_utc(dt, 'America/Sao_Paulo')