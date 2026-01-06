"""
Authentication API Schemas

Pydantic models for authentication API requests and responses.
Reuses domain types from shared/types where possible.
"""
from pydantic import BaseModel

from shared.types.auth import AuthenticatedUser


# ========== Requests ==========

class AutoLoginRequest(BaseModel):
    """Request for automatic login via WhosLoggedIn table."""
    pc_name: str
    pc_lid: str


class LoginRequest(BaseModel):
    """Request for manual username/password login."""
    username: str
    password: str


# ========== Responses ==========

# Reuse domain type directly for user response
AuthUserResponse = AuthenticatedUser


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    user: AuthenticatedUser | None = None
    error: str | None = None


class AuthStatusResponse(BaseModel):
    """Auth service status response."""
    available: bool
    message: str
