"""
Base schemas with timezone-aware datetime serialization
"""
from typing import Optional, Any, Union, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_serializer, ConfigDict
# Import para compatibilidade com diferentes versões do Pydantic
try:
    from pydantic.json_schema import JsonSchemaValue
except ImportError:
    JsonSchemaValue = Any

from app.core.timezone_utils import (
    format_datetime_with_timezone,
    get_user_timezone,
    convert_utc_to_local,
    is_timezone_aware
)


class TimezoneAwareModel(BaseModel):
    """
    Base model with automatic timezone-aware datetime serialization
    """
    model_config = ConfigDict(
        # Automatically convert datetime fields to timezone-aware format
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        # Validate assignment to ensure timezone consistency
        validate_assignment=True,
        # Use enum values for serialization
        use_enum_values=True,
        # Enable arbitrary types for complex timezone handling
        arbitrary_types_allowed=True
    )

    @field_serializer('*', when_used='json')
    def serialize_datetime_fields(self, value: Any, _info) -> Any:
        """
        Custom serializer for datetime fields that ensures timezone-aware output
        """
        if isinstance(value, datetime):
            return self._serialize_datetime(value)
        return value

    def _serialize_datetime(
        self,
        dt: datetime,
        user_timezone: Optional[str] = None,
        include_timezone: bool = True
    ) -> str:
        """
        Serialize datetime to timezone-aware ISO 8601 format

        Args:
            dt: Datetime to serialize
            user_timezone: Target user timezone (defaults to system timezone)
            include_timezone: Whether to include timezone info in output

        Returns:
            ISO 8601 formatted datetime string
        """
        if dt is None:
            return None

        # Ensure datetime is timezone-aware (assume UTC if naive)
        if not is_timezone_aware(dt):
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to user timezone if specified
        if user_timezone:
            dt = convert_utc_to_local(dt, user_timezone)

        # Format as ISO 8601
        if include_timezone:
            return dt.isoformat()
        else:
            return dt.replace(tzinfo=None).isoformat()

    def model_dump(
        self,
        *,
        user_timezone: Optional[str] = None,
        localize_timestamps: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced model dump with timezone conversion options

        Args:
            user_timezone: Convert timestamps to this timezone
            localize_timestamps: Whether to localize all datetime fields
            **kwargs: Standard Pydantic model_dump arguments

        Returns:
            Dictionary representation with timezone-aware timestamps
        """
        # Get standard dump
        data = super().model_dump(**kwargs)

        # Apply timezone conversion if requested
        if localize_timestamps and user_timezone:
            data = self._convert_timestamps_in_dict(data, user_timezone)

        return data

    def _convert_timestamps_in_dict(
        self,
        data: Dict[str, Any],
        target_timezone: str
    ) -> Dict[str, Any]:
        """
        Recursively convert all datetime strings in dict to target timezone
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str) and self._is_iso_datetime(value):
                    # Parse and convert datetime string
                    try:
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        converted_dt = convert_utc_to_local(dt, target_timezone)
                        result[key] = converted_dt.isoformat()
                    except (ValueError, TypeError):
                        result[key] = value
                elif isinstance(value, (dict, list)):
                    result[key] = self._convert_timestamps_in_dict(value, target_timezone)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._convert_timestamps_in_dict(item, target_timezone) for item in data]
        else:
            return data

    def _is_iso_datetime(self, value: str) -> bool:
        """Check if string looks like ISO datetime"""
        try:
            # Simple heuristic for ISO datetime strings
            return (
                len(value) > 10 and
                'T' in value and
                (':' in value or 'Z' in value or '+' in value or '-' in value[-6:])
            )
        except (AttributeError, TypeError):
            return False


class TimezoneResponseModel(TimezoneAwareModel):
    """
    Response model that automatically includes timezone metadata
    """

    def __init__(self, **data):
        super().__init__(**data)
        # Store timezone info as instance attribute (not Pydantic field)
        self.__timezone_info: Optional[Dict[str, Any]] = None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Enhanced dump with timezone metadata"""
        data = super().model_dump(**kwargs)

        # Add timezone info if available
        if hasattr(self, '_TimezoneResponseModel__timezone_info') and self.__timezone_info:
            data['_meta'] = {
                'timezone': self.__timezone_info.get('timezone'),
                'utc_offset': self.__timezone_info.get('utc_offset'),
                'localized': self.__timezone_info.get('localized', False)
            }

        return data

    @classmethod
    def with_timezone_context(
        cls,
        user_timezone: Optional[str] = None,
        **model_data
    ):
        """
        Create instance with timezone context for automatic conversion

        Args:
            user_timezone: Target timezone for datetime fields
            **model_data: Model field data

        Returns:
            Model instance with timezone context
        """
        instance = cls(**model_data)

        # Store timezone context
        if user_timezone:
            instance._TimezoneResponseModel__timezone_info = {
                'timezone': user_timezone,
                'localized': True
            }

        return instance


class PaginatedResponse(TimezoneResponseModel):
    """
    Base model for paginated responses with timezone support
    """
    items: list = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list,
        total: int,
        page: int,
        page_size: int,
        **extra_fields
    ):
        """
        Create paginated response with calculated pagination metadata
        """
        pages = (total + page_size - 1) // page_size

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            **extra_fields
        )


# Utility functions for schemas
def ensure_timezone_aware_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all datetime values in dict are timezone-aware
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            if not is_timezone_aware(value):
                result[key] = value.replace(tzinfo=timezone.utc)
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = ensure_timezone_aware_dict(value)
        elif isinstance(value, list):
            result[key] = [
                ensure_timezone_aware_dict(item) if isinstance(item, dict)
                else item.replace(tzinfo=timezone.utc) if isinstance(item, datetime) and not is_timezone_aware(item)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


# Commonly used field types with timezone support
TimezoneAwareDatetime = Field(
    ...,
    description="Timezone-aware datetime in ISO 8601 format",
    json_schema_extra={
        "example": "2025-01-26T01:30:00-03:00"
    }
)

OptionalTimezoneAwareDatetime = Field(
    None,
    description="Optional timezone-aware datetime in ISO 8601 format",
    json_schema_extra={
        "example": "2025-01-26T01:30:00-03:00"
    }
)