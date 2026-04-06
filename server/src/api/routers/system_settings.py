"""
System Settings API Routes

REST endpoints for application-wide settings management.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.system_settings import (
    EmailSettingsResponse,
    UpdateEmailSettingsRequest,
    OrderManagementSettingsResponse,
    UpdateOrderManagementSettingsRequest,
)
from shared.database import DatabaseConnectionManager
from shared.database.repositories.system_settings import SystemSettingsRepository
from shared.database.repositories.email_account import EmailAccountRepository
from shared.services.service_container import ServiceContainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["System Settings"])


# Setting keys
EMAIL_DEFAULT_SENDER_ACCOUNT_ID = "email.default_sender_account_id"
ORDER_MANAGEMENT_AUTO_CREATE_ENABLED = "order_management.auto_create_enabled"
ORDER_MANAGEMENT_AUTO_CREATE_ENABLED_AT = "order_management.auto_create_enabled_at"


def get_connection_manager() -> DatabaseConnectionManager:
    """Get database connection manager from service container."""
    return ServiceContainer.get_main_connection()


@router.get(
    "/email",
    response_model=EmailSettingsResponse,
    summary="Get email settings",
    description="Get email-related system settings including the default sender account.",
)
def get_email_settings(
    connection_manager: DatabaseConnectionManager = Depends(get_connection_manager),
) -> EmailSettingsResponse:
    """Get email settings."""
    repo = SystemSettingsRepository(connection_manager=connection_manager)

    sender_id_str = repo.get(EMAIL_DEFAULT_SENDER_ACCOUNT_ID)
    sender_id = int(sender_id_str) if sender_id_str else None

    return EmailSettingsResponse(
        default_sender_account_id=sender_id,
    )


@router.put(
    "/email",
    response_model=EmailSettingsResponse,
    summary="Update email settings",
    description="Update email-related system settings. Set default_sender_account_id to null to clear.",
)
def update_email_settings(
    request: UpdateEmailSettingsRequest,
    connection_manager: DatabaseConnectionManager = Depends(get_connection_manager),
) -> EmailSettingsResponse:
    """Update email settings."""
    settings_repo = SystemSettingsRepository(connection_manager=connection_manager)

    # Validate account exists if setting a sender
    if request.default_sender_account_id is not None:
        account_repo = EmailAccountRepository(connection_manager=connection_manager)
        account = account_repo.get_by_id(request.default_sender_account_id)

        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email account {request.default_sender_account_id} not found",
            )

        if not account.is_validated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email account {request.default_sender_account_id} is not validated",
            )

    # Update the setting
    value = str(request.default_sender_account_id) if request.default_sender_account_id else None
    settings_repo.set(EMAIL_DEFAULT_SENDER_ACCOUNT_ID, value)

    logger.info(f"Updated email.default_sender_account_id to {request.default_sender_account_id}")

    return EmailSettingsResponse(
        default_sender_account_id=request.default_sender_account_id,
    )


# ==================== Order Management Settings ====================


@router.get(
    "/order-management",
    response_model=OrderManagementSettingsResponse,
    summary="Get order management settings",
    description="Get order management settings including auto-create toggle.",
)
def get_order_management_settings(
    connection_manager: DatabaseConnectionManager = Depends(get_connection_manager),
) -> OrderManagementSettingsResponse:
    """Get order management settings."""
    repo = SystemSettingsRepository(connection_manager=connection_manager)

    auto_create_str = repo.get(ORDER_MANAGEMENT_AUTO_CREATE_ENABLED)
    # Default to True if not set
    auto_create_enabled = auto_create_str.lower() == "true" if auto_create_str else True

    enabled_at_str = repo.get(ORDER_MANAGEMENT_AUTO_CREATE_ENABLED_AT)
    enabled_at = datetime.fromisoformat(enabled_at_str) if enabled_at_str else None

    return OrderManagementSettingsResponse(
        auto_create_enabled=auto_create_enabled,
        auto_create_enabled_at=enabled_at,
    )


@router.put(
    "/order-management",
    response_model=OrderManagementSettingsResponse,
    summary="Update order management settings",
    description="Update order management settings.",
)
def update_order_management_settings(
    request: UpdateOrderManagementSettingsRequest,
    connection_manager: DatabaseConnectionManager = Depends(get_connection_manager),
) -> OrderManagementSettingsResponse:
    """Update order management settings."""
    settings_repo = SystemSettingsRepository(connection_manager=connection_manager)

    # Store as string "true" or "false"
    value = "true" if request.auto_create_enabled else "false"
    settings_repo.set(ORDER_MANAGEMENT_AUTO_CREATE_ENABLED, value)

    # Track enabled_at timestamp for the auto-create worker
    # Only set on OFF→ON transitions (when currently None); clear on disable
    enabled_at: datetime | None = None
    if request.auto_create_enabled:
        current_enabled_at = settings_repo.get(ORDER_MANAGEMENT_AUTO_CREATE_ENABLED_AT)
        if current_enabled_at is None:
            # OFF→ON transition: set fresh timestamp
            enabled_at = datetime.now(timezone.utc)
            settings_repo.set(
                ORDER_MANAGEMENT_AUTO_CREATE_ENABLED_AT,
                enabled_at.isoformat(),
            )
        else:
            # Already ON: preserve existing timestamp
            enabled_at = datetime.fromisoformat(current_enabled_at)
    else:
        # Disabling: clear enabled_at so re-enable gets a fresh timestamp
        settings_repo.set(ORDER_MANAGEMENT_AUTO_CREATE_ENABLED_AT, None)

    logger.info(f"Updated order_management.auto_create_enabled to {request.auto_create_enabled}")

    return OrderManagementSettingsResponse(
        auto_create_enabled=request.auto_create_enabled,
        auto_create_enabled_at=enabled_at,
    )
