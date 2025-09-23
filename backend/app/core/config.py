"""
Configuration management using Pydantic Settings for FastAPI
"""
from typing import List, Optional, Literal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import os

class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env
    )

    # Base Configuration
    APP_NAME: str = "Knight Agent API"
    VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="fastapi-insecure-change-me-in-production")

    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MEDIA_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "media")
    STATIC_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "static")
    DOCUMENTS_PATH: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "documents")
    PROCESSED_DOCS_PATH: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "processed_documents")
    VECTOR_STORE_PATH: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "vector_store")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1", "*.loca.lt"])

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://knight-frontend-dev.loca.lt"
        ]
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)  # MUST be True for httpOnly cookies

    # Database Configuration
    DB_ENGINE: str = Field(default="postgresql")
    DB_NAME: str = Field(default="knight_db")
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL"""
        if self.DB_ENGINE == "sqlite":
            return f"sqlite:///{self.BASE_DIR}/db.sqlite3"
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Construct synchronous database URL for Alembic"""
        if self.DB_ENGINE == "sqlite":
            return f"sqlite:///{self.BASE_DIR}/db.sqlite3"
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Microsoft Azure AD Configuration
    AZURE_AD_CLIENT_ID: str = Field(default="")
    AZURE_AD_CLIENT_SECRET: str = Field(default="")
    AZURE_AD_TENANT_ID: str = Field(default="")
    AZURE_AD_REDIRECT_URI: str = Field(default="http://localhost:8000/auth/microsoft/callback/")

    # JWT Configuration
    JWT_SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Security Configuration
    REQUIRE_JWT_SIGNATURE_VERIFICATION: bool = Field(default=True)
    USE_MSAL_VALIDATION: bool = Field(default=True)
    ALLOW_FALLBACK_VALIDATION: bool = Field(default=False)  # Should be False in production

    @field_validator('SECRET_KEY', 'JWT_SECRET_KEY')
    @classmethod
    def validate_secret_keys(cls, v, info):
        """Validate that secret keys are not using default values in production"""
        default_keys = [
            'dev-secret-key-change-in-production',
            'dev-jwt-secret-key-change-in-production',
            'fastapi-insecure-change-me-in-production',
            'your-secret-key-here',
            'your-jwt-secret-key-here',
            'change-me',
            'changeme',
            'default'
        ]

        # Check for insecure default values
        if v and any(default in v.lower() for default in default_keys):
            import logging
            logger = logging.getLogger(__name__)

            # In production, raise an error instead of just warning
            if not cls.model_fields.get('DEBUG', True):
                raise ValueError(
                    f"SECURITY ERROR: {info.field_name} is using an insecure default value. "
                    "Generate a secure key using: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )

            logger.warning(
                f"⚠️  SECURITY WARNING: {info.field_name} is using a default development value. "
                "Please generate a secure key for production!"
            )

        # Check minimum key length (32 characters for security)
        if v and len(v) < 32:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"⚠️  SECURITY WARNING: {info.field_name} is too short ({len(v)} chars). "
                "Recommended minimum: 32 characters for security."
            )

        return v

    # LLM Configuration
    LLM_PROVIDER: Literal["deepseek", "cohere", "together", "groq", "ollama", "gemini", "openai"] = Field(default="deepseek")

    # LLM API Keys
    DEEPSEEK_API_KEY: Optional[str] = Field(default="")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    COHERE_API_KEY: Optional[str] = Field(default="")
    TOGETHER_API_KEY: Optional[str] = Field(default="")
    GROQ_API_KEY: Optional[str] = Field(default="")
    OPENAI_API_KEY: Optional[str] = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    GOOGLE_API_KEY: Optional[str] = Field(default="")
    GEMINI_API_KEY: Optional[str] = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash")

    # RAG Configuration
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-m3")
    CHUNK_SIZE: int = Field(default=700)
    CHUNK_OVERLAP: int = Field(default=100)
    BM25_WEIGHT: float = Field(default=0.3)
    SEMANTIC_WEIGHT: float = Field(default=0.7)

    # HuggingFace Configuration
    HF_HOME: str = Field(default="/home/felipealbertuxd/.cache/huggingface")
    SENTENCE_TRANSFORMERS_HOME: str = Field(default="/home/felipealbertuxd/.cache/huggingface")

    # Redis Configuration (for caching)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # PgVector Configuration
    USE_PGVECTOR: bool = Field(default=True)
    ENABLE_VECTOR_FALLBACK: bool = Field(default=True)
    HNSW_EF_SEARCH: int = Field(default=64)
    IVFFLAT_PROBES: int = Field(default=10)
    SIMILARITY_THRESHOLD: float = Field(default=0.8)
    VECTOR_BATCH_SIZE: int = Field(default=100)

    # Downloads Configuration
    DOWNLOADS_RETENTION_DAYS: int = Field(default=7)

    # i18n Configuration
    DEFAULT_LANGUAGE: str = Field(default="en")
    SUPPORTED_LANGUAGES: List[str] = Field(
        default=["pt-br", "en", "es", "sv"]
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Security
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_PERIOD: int = Field(default=60)  # seconds

    # Session Configuration
    SESSION_EXPIRE_HOURS: int = Field(default=1)

    # Cookie Configuration
    COOKIE_SECURE: bool = Field(default=False)  # Set to True in production (HTTPS)
    COOKIE_SAMESITE: str = Field(default="lax")  # 'lax' for OAuth flow, 'strict' for better security
    COOKIE_DOMAIN: Optional[str] = Field(default=None)
    USE_HTTPONLY_COOKIES: bool = Field(default=True)

    # Security Configuration
    CSRF_ENABLED: bool = Field(default=True)
    SECURE_HEADERS_ENABLED: bool = Field(default=True)
    MAX_REQUEST_SIZE: int = Field(default=16 * 1024 * 1024)  # 16MB

    # Content Security Policy
    CSP_DEFAULT_SRC: str = Field(default="'self'")
    CSP_SCRIPT_SRC: str = Field(default="'self' 'unsafe-inline'")
    CSP_STYLE_SRC: str = Field(default="'self' 'unsafe-inline'")
    CSP_IMG_SRC: str = Field(default="'self' data: blob:")
    CSP_CONNECT_SRC: str = Field(default="'self'")

    # Token Security
    TOKEN_BLACKLIST_CLEANUP_INTERVAL: int = Field(default=3600)  # 1 hour
    MAX_LOGIN_ATTEMPTS: int = Field(default=5)
    LOGIN_ATTEMPT_TIMEOUT: int = Field(default=900)  # 15 minutes

    @field_validator("MEDIA_DIR", "STATIC_DIR", "DOCUMENTS_PATH", "PROCESSED_DOCS_PATH", "VECTOR_STORE_PATH")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist"""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("JWT_SECRET_KEY", mode='before')
    @classmethod
    def set_jwt_secret(cls, v: str, info) -> str:
        """Use SECRET_KEY for JWT if not specified"""
        if not v and info.data.get("SECRET_KEY"):
            return info.data["SECRET_KEY"]
        return v or "default-jwt-secret-change-me"


# Create settings instance
settings = Settings()

# Export HuggingFace cache directories
os.environ['HF_HOME'] = settings.HF_HOME
os.environ['SENTENCE_TRANSFORMERS_HOME'] = settings.SENTENCE_TRANSFORMERS_HOME