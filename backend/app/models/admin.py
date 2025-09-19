"""
Admin email management model
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from app.core.database import Base


class AdminEmail(Base):
    """
    Model to store admin emails dynamically
    """
    __tablename__ = "admin_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    added_by = Column(String(254), nullable=True)  # Email of admin who added this
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AdminEmail(email={self.email}, active={self.is_active})>"