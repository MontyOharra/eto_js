"""
Authentication API Router

Provides endpoints for user authentication:
- Auto-login via HTC WhosLoggedIn table
- Manual login via username/password
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from shared.services.service_container import ServiceContainer
from features.auth.service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ==================== Request/Response Schemas ====================

class AutoLoginRequest(BaseModel):
    """Request for automatic login via WhosLoggedIn table."""
    pc_name: str
    pc_lid: str

    class Config:
        json_schema_extra = {
            "example": {
                "pc_name": "WORKSTATION-01",
                "pc_lid": "john.smith"
            }
        }


class LoginRequest(BaseModel):
    """Request for manual username/password login."""
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "jsmith",
                "password": "password123"
            }
        }


class AuthUserResponse(BaseModel):
    """Authenticated user information."""
    staff_emp_id: int
    username: str  # Staff_Login - used for audit trail
    display_name: str
    first_name: str
    last_name: str


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    user: Optional[AuthUserResponse] = None
    error: Optional[str] = None


class AuthStatusResponse(BaseModel):
    """Auth service status response."""
    available: bool
    message: str


# ==================== Dependency ====================

def get_auth_service() -> AuthService:
    """Get auth service from container."""
    return ServiceContainer.get_auth_service()


# ==================== Endpoints ====================

@router.post("/auto-login", response_model=AuthResponse)
async def auto_login(
    request: AutoLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """
    Attempt automatic login using machine credentials.

    Checks the HTC WhosLoggedIn table for an active session matching
    the provided computer name and Windows login ID.

    Use this on app startup to automatically authenticate users who
    are already logged into the HTC system.
    """
    try:
        user = auth_service.attempt_auto_login(request.pc_name, request.pc_lid)

        if user:
            return AuthResponse(
                success=True,
                user=AuthUserResponse(
                    staff_emp_id=user.staff_emp_id,
                    username=user.username,
                    display_name=user.display_name,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
            )
        else:
            return AuthResponse(
                success=False,
                error="No active session found for this machine"
            )

    except Exception as e:
        logger.error(f"Auto-login error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error="Authentication service error"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """
    Manual login with username and password.

    Validates credentials against the HTC Staff table.
    """
    try:
        user = auth_service.validate_credentials(request.username, request.password)

        if user:
            return AuthResponse(
                success=True,
                user=AuthUserResponse(
                    staff_emp_id=user.staff_emp_id,
                    username=user.username,
                    display_name=user.display_name,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
            )
        else:
            return AuthResponse(
                success=False,
                error="Invalid username or password"
            )

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error="Authentication service error"
        )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthStatusResponse:
    """
    Check if authentication service is available.

    Returns whether the staff database is configured and accessible.
    """
    try:
        available = auth_service.is_available()
        return AuthStatusResponse(
            available=available,
            message="Auth service is available" if available else "Auth service not configured"
        )
    except Exception as e:
        logger.error(f"Auth status check error: {e}", exc_info=True)
        return AuthStatusResponse(
            available=False,
            message=f"Auth service error: {str(e)}"
        )
