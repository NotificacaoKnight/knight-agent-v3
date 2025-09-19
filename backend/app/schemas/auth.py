"""
Authentication schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Request schemas
class LoginRequest(BaseModel):
    """Microsoft OAuth login initiation"""
    redirect_url: Optional[str] = Field(None, description="Optional redirect URL after login")

class CallbackRequest(BaseModel):
    """OAuth callback parameters"""
    code: str = Field(..., description="Authorization code from Microsoft")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="JWT refresh token")

class MicrosoftTokenRequest(BaseModel):
    """Microsoft token exchange request"""
    access_token: str = Field(..., description="Microsoft access token from MSAL")

class MicrosoftIdTokenRequest(BaseModel):
    """Request model for Microsoft ID token + Access token exchange (RECOMMENDED)"""
    id_token: str = Field(..., description="Microsoft ID token for authentication")
    access_token: str = Field(..., description="Microsoft access token for Graph API calls")

# Response schemas
class TokenResponse(BaseModel):
    """Token response after successful authentication"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = 3600

class LoginUrlResponse(BaseModel):
    """Microsoft login URL response"""
    auth_url: str = Field(..., description="Microsoft OAuth authorization URL")

class UserInfo(BaseModel):
    """Basic user information"""
    id: int
    email: EmailStr
    username: str
    display_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    preferred_language: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    """Complete login response with tokens and user info"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: UserInfo

class LogoutResponse(BaseModel):
    """Logout response"""
    message: str = "Successfully logged out"
    success: bool = True