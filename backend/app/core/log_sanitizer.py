"""
Log Sanitizer
Sanitizes sensitive data from logs to prevent information leakage
"""
import re
import logging
from typing import Any, Dict, List, Union
import json


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to remove sensitive data from log messages
    """

    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        # JWT tokens
        (r'Bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]+', 'Bearer [REDACTED_JWT]'),
        (r'eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]+', '[REDACTED_JWT]'),

        # API Keys
        (r'(api[_-]?key|apikey|api_secret)[\"\']?\s*[:=]\s*[\"\']?[A-Za-z0-9\-_]{20,}[\"\']?', r'\1=[REDACTED_API_KEY]'),
        (r'sk_[A-Za-z0-9]{32,}', '[REDACTED_API_KEY]'),

        # Passwords
        (r'(password|passwd|pwd)[\"\']?\s*[:=]\s*[\"\']?[^\"\';\s]+[\"\']?', r'\1=[REDACTED_PASSWORD]'),

        # Azure AD secrets
        (r'(client[_-]?secret|tenant[_-]?id)[\"\']?\s*[:=]\s*[\"\']?[A-Za-z0-9\-]{20,}[\"\']?', r'\1=[REDACTED_SECRET]'),

        # Access/Refresh tokens (but not boolean values or log messages)
        (r'(access[_-]?token|refresh[_-]?token)[\"\']?\s*[:=]\s*[\"\']?(?!True|False|true|false)[A-Za-z0-9\-_=]{20,}[\"\']?', r'\1=[REDACTED_TOKEN]'),

        # Session tokens
        (r'(session[_-]?token|session[_-]?id)[\"\']?\s*[:=]\s*[\"\']?[A-Za-z0-9\-_]{20,}[\"\']?', r'\1=[REDACTED_SESSION]'),

        # Email addresses (optional - uncomment if needed)
        # (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]'),

        # Credit card numbers (avoid Microsoft GUIDs/UUIDs which contain letters)
        # Only match pure numeric sequences, not hex strings like Microsoft audiences
        (r'\b(?!00000003-c000-000000000000)(?![0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', '[REDACTED_CARD]'),

        # Social Security Numbers
        (r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]'),

        # Database connection strings
        (r'(postgresql|mysql|mongodb)://[^@]+@[^\s]+', r'\1://[REDACTED_CREDENTIALS]@[REDACTED_HOST]'),
    ]

    # Headers to redact
    SENSITIVE_HEADERS = [
        'authorization',
        'x-api-key',
        'x-auth-token',
        'cookie',
        'set-cookie',
        'x-csrf-token'
    ]

    # Fields to redact in structured data
    SENSITIVE_FIELDS = [
        'password',
        'passwd',
        'pwd',
        'secret',
        'token',
        'api_key',
        'apikey',
        'access_token',
        'refresh_token',
        'session_token',
        'client_secret',
        'private_key',
        'credentials'
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter sensitive data from log records

        Args:
            record: Log record to filter

        Returns:
            True to allow the record to be logged
        """
        # Sanitize the main message
        if hasattr(record, 'msg'):
            record.msg = self.sanitize_string(str(record.msg))

        # Sanitize args if present
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = self.sanitize_dict(record.args)
            elif isinstance(record.args, tuple):
                sanitized_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        sanitized_args.append(self.sanitize_string(arg))
                    else:
                        sanitized_args.append(arg)
                record.args = tuple(sanitized_args)

        return True

    def sanitize_string(self, text: str) -> str:
        """
        Remove sensitive data from a string

        Args:
            text: String to sanitize

        Returns:
            Sanitized string
        """
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive data from a dictionary

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value)
            else:
                sanitized[key] = value
        return sanitized

    def sanitize_list(self, data: List[Any]) -> List[Any]:
        """
        Remove sensitive data from a list

        Args:
            data: List to sanitize

        Returns:
            Sanitized list
        """
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item))
            else:
                sanitized.append(item)
        return sanitized


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Sanitize HTTP headers for logging

    Args:
        headers: Dictionary of headers

    Returns:
        Sanitized headers dictionary
    """
    sanitized = {}
    for key, value in headers.items():
        if key.lower() in SensitiveDataFilter.SENSITIVE_HEADERS:
            sanitized[key] = '[REDACTED]'
        else:
            # Still check for patterns in header values
            filter = SensitiveDataFilter()
            sanitized[key] = filter.sanitize_string(value)
    return sanitized


def sanitize_request_body(body: Union[str, bytes, dict]) -> str:
    """
    Sanitize request body for logging

    Args:
        body: Request body (string, bytes, or dict)

    Returns:
        Sanitized body string
    """
    filter = SensitiveDataFilter()

    if isinstance(body, bytes):
        try:
            body = body.decode('utf-8')
        except UnicodeDecodeError:
            return "[BINARY_DATA]"

    if isinstance(body, dict):
        return json.dumps(filter.sanitize_dict(body), indent=2)

    if isinstance(body, str):
        # Try to parse as JSON
        try:
            data = json.loads(body)
            return json.dumps(filter.sanitize_dict(data), indent=2)
        except json.JSONDecodeError:
            # Not JSON, sanitize as string
            return filter.sanitize_string(body)

    return str(body)


def setup_logging():
    """
    Setup logging configuration with sensitive data filtering
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Add sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)

    # Also add to specific loggers
    loggers = [
        'uvicorn',
        'uvicorn.access',
        'uvicorn.error',
        'fastapi',
        'sqlalchemy',
        'app'
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            handler.addFilter(sensitive_filter)


# Convenience function for safe logging
def safe_log_dict(data: dict, max_length: int = 1000) -> str:
    """
    Safely log a dictionary with sensitive data removed

    Args:
        data: Dictionary to log
        max_length: Maximum string length

    Returns:
        Safe string representation
    """
    filter = SensitiveDataFilter()
    sanitized = filter.sanitize_dict(data)
    result = json.dumps(sanitized, indent=2, default=str)

    if len(result) > max_length:
        result = result[:max_length] + '... [TRUNCATED]'

    return result