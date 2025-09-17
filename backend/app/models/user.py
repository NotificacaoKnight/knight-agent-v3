"""
User and Session models
Migrated from Django authentication models
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import uuid

from app.core.database import Base

class User(Base):
    """
    User model - migrated from Django AbstractUser
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Authentication fields
    username = Column(String(150), unique=True, index=True, nullable=False)
    email = Column(String(254), unique=True, index=True, nullable=False)
    password_hash = Column(String(255))  # Will use passlib for hashing

    # Microsoft Azure AD
    microsoft_id = Column(String(255), unique=True, index=True, nullable=True)

    # Profile fields
    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    preferred_name = Column(String(100), default="")
    profile_picture = Column(String(500), nullable=True)  # URL to image
    theme_preference = Column(String(10), default="light")  # light/dark
    department = Column(String(100), default="")
    job_title = Column(String(100), default="")

    # Language preference
    preferred_language = Column(String(10), nullable=True)  # pt-BR, en-US, etc

    # Permissions
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="uploaded_by")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

    @property
    def display_name(self):
        """Get display name for the user"""
        if self.preferred_name:
            return self.preferred_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email

    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()

class UserSession(Base):
    """
    User session model for token-based authentication
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Session tokens
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    microsoft_token = Column(Text, nullable=True)  # Microsoft access token
    refresh_token = Column(Text, nullable=True)  # Microsoft refresh token

    # Session metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, token={self.session_token[:10]}...)>"

    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)

    @staticmethod
    def generate_token() -> str:
        """Generate a unique session token"""
        return str(uuid.uuid4())