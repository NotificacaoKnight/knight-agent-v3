"""
Custom validators for Pydantic schemas
Provides robust input validation and sanitization
"""
import re
import bleach
from typing import Any, Optional
from pydantic import validator, Field
from pydantic.validators import str_validator
import logging

logger = logging.getLogger(__name__)

# Maximum field lengths
MAX_USERNAME_LENGTH = 150
MAX_EMAIL_LENGTH = 254
MAX_NAME_LENGTH = 100
MAX_TEXT_LENGTH = 10000
MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 2000
MAX_URL_LENGTH = 2048
MAX_QUERY_LENGTH = 1000

# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'code', 'pre']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'code': ['class'],
}

# Regular expressions for validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')
URL_REGEX = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def sanitize_html(value: str, allowed_tags: list = None, allowed_attributes: dict = None) -> str:
    """
    Sanitize HTML content to prevent XSS attacks

    Args:
        value: HTML string to sanitize
        allowed_tags: List of allowed HTML tags
        allowed_attributes: Dict of allowed attributes per tag

    Returns:
        Sanitized HTML string
    """
    if not value:
        return value

    tags = allowed_tags or ALLOWED_TAGS
    attributes = allowed_attributes or ALLOWED_ATTRIBUTES

    cleaned = bleach.clean(
        value,
        tags=tags,
        attributes=attributes,
        strip=True,
        strip_comments=True
    )

    return cleaned

def validate_no_sql_injection(value: str) -> str:
    """
    Check for potential SQL injection patterns

    Args:
        value: String to validate

    Returns:
        Original string if safe

    Raises:
        ValueError if SQL injection pattern detected
    """
    if not value:
        return value

    # Common SQL injection patterns
    sql_patterns = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|FROM|WHERE)\b)',
        r'(--|\||;|\/\*|\*\/|xp_|sp_|0x)',
        r'(\bOR\b\s*\d+\s*=\s*\d+)',
        r'(\bAND\b\s*\d+\s*=\s*\d+)',
        r"('\s*OR\s*')",
        r'(1\s*=\s*1)',
        r'(1\'\s*OR\s*\'1\'\s*=\s*\'1)',
    ]

    value_upper = value.upper()
    for pattern in sql_patterns:
        if re.search(pattern, value_upper):
            logger.warning(f"Potential SQL injection detected: {value[:50]}...")
            raise ValueError("Invalid input: potential security risk detected")

    return value

def validate_no_script_injection(value: str) -> str:
    """
    Check for script injection patterns

    Args:
        value: String to validate

    Returns:
        Original string if safe

    Raises:
        ValueError if script injection pattern detected
    """
    if not value:
        return value

    # Script injection patterns
    script_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers like onclick, onload
        r'<iframe',
        r'<embed',
        r'<object',
        r'eval\s*\(',
        r'expression\s*\(',
    ]

    value_lower = value.lower()
    for pattern in script_patterns:
        if re.search(pattern, value_lower, re.IGNORECASE | re.DOTALL):
            logger.warning(f"Potential script injection detected: {value[:50]}...")
            raise ValueError("Invalid input: potential security risk detected")

    return value

class SecureStr(str):
    """
    Custom string type with built-in validation
    """
    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError('string required')

        # Remove leading/trailing whitespace
        v = v.strip()

        # Check for script injection
        v = validate_no_script_injection(v)

        # Check for SQL injection
        v = validate_no_sql_injection(v)

        return v

class SanitizedHTML(str):
    """
    Custom HTML string type with sanitization
    """
    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError('string required')

        # Sanitize HTML
        v = sanitize_html(v)

        return v

# Field validators for common fields
def validate_email(email: str) -> str:
    """Validate email format"""
    if not email:
        raise ValueError("Email is required")

    email = email.strip().lower()

    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email must be less than {MAX_EMAIL_LENGTH} characters")

    if not EMAIL_REGEX.match(email):
        raise ValueError("Invalid email format")

    return email

def validate_username(username: str) -> str:
    """Validate username format"""
    if not username:
        raise ValueError("Username is required")

    username = username.strip()

    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")

    if len(username) > MAX_USERNAME_LENGTH:
        raise ValueError(f"Username must be less than {MAX_USERNAME_LENGTH} characters")

    if not USERNAME_REGEX.match(username):
        raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")

    return username

def validate_password(password: str) -> str:
    """Validate password strength"""
    if not password:
        raise ValueError("Password is required")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if len(password) > 128:
        raise ValueError("Password must be less than 128 characters")

    # Check password complexity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower and has_digit):
        raise ValueError("Password must contain uppercase, lowercase, and numbers")

    return password

def validate_url(url: str) -> str:
    """Validate URL format"""
    if not url:
        return url  # URLs are often optional

    url = url.strip()

    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL must be less than {MAX_URL_LENGTH} characters")

    if not URL_REGEX.match(url):
        raise ValueError("Invalid URL format")

    # Additional security checks
    if any(pattern in url.lower() for pattern in ['javascript:', 'data:', 'vbscript:']):
        raise ValueError("Invalid URL protocol")

    return url

def validate_query_string(query: str) -> str:
    """Validate search query string"""
    if not query:
        raise ValueError("Query is required")

    query = query.strip()

    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Query must be less than {MAX_QUERY_LENGTH} characters")

    # Remove potentially dangerous characters
    query = validate_no_sql_injection(query)
    query = validate_no_script_injection(query)

    return query

def validate_file_name(filename: str) -> str:
    """Validate file name for security"""
    if not filename:
        raise ValueError("Filename is required")

    # Remove path traversal attempts
    filename = filename.replace("..", "")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")

    # Check for null bytes
    if "\x00" in filename:
        raise ValueError("Invalid filename")

    # Limit length
    if len(filename) > 255:
        raise ValueError("Filename too long")

    # Check extension
    allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.csv', '.xlsx', '.xls'}
    ext = filename[filename.rfind('.'):].lower() if '.' in filename else ''

    if ext and ext not in allowed_extensions:
        raise ValueError(f"File type {ext} not allowed")

    return filename

def validate_text_field(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Validate general text field"""
    if not text:
        return text

    text = text.strip()

    if len(text) > max_length:
        raise ValueError(f"Text must be less than {max_length} characters")

    # Basic sanitization
    text = validate_no_script_injection(text)

    return text

def validate_positive_integer(value: int) -> int:
    """Validate positive integer"""
    if value <= 0:
        raise ValueError("Value must be positive")

    return value

def validate_limit(value: int, max_limit: int = 100) -> int:
    """Validate pagination limit"""
    if value <= 0:
        raise ValueError("Limit must be positive")

    if value > max_limit:
        raise ValueError(f"Limit cannot exceed {max_limit}")

    return value

# Pydantic field factories with validators
def EmailField(**kwargs):
    """Create email field with validation"""
    return Field(
        ...,
        max_length=MAX_EMAIL_LENGTH,
        regex=EMAIL_REGEX.pattern,
        **kwargs
    )

def UsernameField(**kwargs):
    """Create username field with validation"""
    return Field(
        ...,
        min_length=3,
        max_length=MAX_USERNAME_LENGTH,
        regex=USERNAME_REGEX.pattern,
        **kwargs
    )

def PasswordField(**kwargs):
    """Create password field with validation"""
    return Field(
        ...,
        min_length=8,
        max_length=128,
        **kwargs
    )

def URLField(**kwargs):
    """Create URL field with validation"""
    return Field(
        None,
        max_length=MAX_URL_LENGTH,
        **kwargs
    )

def TextField(max_length: int = MAX_TEXT_LENGTH, **kwargs):
    """Create text field with validation"""
    return Field(
        None,
        max_length=max_length,
        **kwargs
    )