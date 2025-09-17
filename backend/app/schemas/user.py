"""
User schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    preferred_name: Optional[str] = ""
    department: Optional[str] = ""
    job_title: Optional[str] = ""
    theme_preference: str = "light"
    preferred_language: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: Optional[str] = Field(None, description="Optional password for non-SSO users")
    microsoft_id: Optional[str] = None

class UserUpdate(BaseModel):
    """Schema for updating user information"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    theme_preference: Optional[str] = None
    preferred_language: Optional[str] = None
    profile_picture: Optional[str] = None

class UserInDB(UserBase):
    """User schema as stored in database"""
    id: int
    microsoft_id: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    is_superuser: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    """User schema for API responses"""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserSession(BaseModel):
    """User session information"""
    id: int
    user_id: int
    session_token: str
    expires_at: datetime
    is_active: bool
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        from_attributes = True