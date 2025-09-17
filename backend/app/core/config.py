"""
Configuration management using Pydantic Settings
Migrated from Django settings.py
"""
from typing import List, Optional, Literal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
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
    CORS_ALLOW_CREDENTIALS: bool = Field(default=False)

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

    # LLM Configuration
    LLM_PROVIDER: Literal["deepseek", "cohere", "together", "groq", "ollama", "gemini", "openai"] = Field(default="deepseek")

    # LLM API Keys
    DEEPSEEK_API_KEY: Optional[str] = Field(default="")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    COHERE_API_KEY: Optional[str] = Field(default="")
    TOGETHER_API_KEY: Optional[str] = Field(default="")
    GROQ_API_KEY: Optional[str] = Field(default="")
    OPENAI_API_KEY: Optional[str] = Field(default="")
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

    @validator("MEDIA_DIR", "STATIC_DIR", "DOCUMENTS_PATH", "PROCESSED_DOCS_PATH", "VECTOR_STORE_PATH")
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist"""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @validator("JWT_SECRET_KEY", pre=True)
    def set_jwt_secret(cls, v: str, values: dict) -> str:
        """Use SECRET_KEY for JWT if not specified"""
        if not v and "SECRET_KEY" in values:
            return values["SECRET_KEY"]
        return v or "default-jwt-secret-change-me"


# Create settings instance
settings = Settings()

# Export HuggingFace cache directories
os.environ['HF_HOME'] = settings.HF_HOME
os.environ['SENTENCE_TRANSFORMERS_HOME'] = settings.SENTENCE_TRANSFORMERS_HOME