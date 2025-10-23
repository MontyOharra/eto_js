"""
Email Configuration API Router
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response

from api.schemas.email_configs import (
    ListEmailConfigsResponse,
    EmailConfigSummaryItem,
    EmailConfigDetail,
    CreateEmailConfigRequest,
    CreateEmailConfigResponse,
    UpdateEmailConfigRequest,
    UpdateEmailConfigResponse,
    ActivateEmailConfigResponse,
    DeactivateEmailConfigResponse,
    EmailAccount,
    EmailFolderItem,
    DiscoverEmailAccountsResponse,
    DiscoverEmailFoldersResponse,
    ValidateEmailConfigRequest,
    ValidateEmailConfigResponse,
    FilterRule,
)

from shared.services.service_container import ServiceContainer
from features.email_configs.service import EmailConfigService
from features.email_ingestion.service import EmailIngestionService
from shared.types import FilterRule as FilterRuleDataclass, EmailConfigCreate, EmailConfigUpdate
from shared.exceptions import ObjectNotFoundError, ConflictError, ServiceError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/email-configs",
    tags=["Email Configurations"]
)


@router.get("", response_model=List[EmailConfigSummaryItem])
async def list_email_configs(
    order_by: str = "name",
    desc: bool = False,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> List[EmailConfigSummaryItem]:
    """List all email configurations (summary)"""

    configs = config_service.list_configs_summary(order_by=order_by, desc=desc)

    return [
        EmailConfigSummaryItem(
            id=config.id,
            name=config.name,
            is_active=config.is_active,
            last_check_time=config.last_check_time.isoformat() if config.last_check_time else None
        )
        for config in configs
    ]


@router.get("/{id}", response_model=EmailConfigDetail)
async def get_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfigDetail:
    """Get email configuration details"""

    try:
        config = config_service.get_config(id)
        if not config:
            raise ObjectNotFoundError(f"Email configuration {id} not found")

        return EmailConfigDetail(
            id=config.id,
            name=config.name,
            description=config.description,
            email_address=config.email_address,
            folder_name=config.folder_name,
            filter_rules=[
                FilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                )
                for rule in config.filter_rules
            ],
            poll_interval_seconds=config.poll_interval_seconds,
            max_backlog_hours=config.max_backlog_hours,
            error_retry_attempts=config.error_retry_attempts,
            is_active=config.is_active,
            activated_at=config.activated_at.isoformat() if config.activated_at else None,
            last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at.isoformat() if config.last_error_at else None
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {id} not found"
        )


@router.post("", response_model=CreateEmailConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_email_config(
    request: CreateEmailConfigRequest,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> CreateEmailConfigResponse:
    """Create new email configuration"""

    try:
        # Convert Pydantic FilterRuleCreate to dataclass FilterRule
        filter_rules = [
            FilterRuleDataclass(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive or False
            )
            for rule in (request.filter_rules or [])
        ]

        # Create EmailConfigCreate dataclass
        config_create = EmailConfigCreate(
            name=request.name,
            description=request.description,
            email_address=request.email_address,
            folder_name=request.folder_name,
            filter_rules=filter_rules,
            poll_interval_seconds=request.poll_interval_seconds or 5,
            max_backlog_hours=request.max_backlog_hours or 24,
            error_retry_attempts=request.error_retry_attempts or 3
        )

        # Create config via service
        config = config_service.create_config(config_create)

        return CreateEmailConfigResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            email_address=config.email_address,
            folder_name=config.folder_name,
            filter_rules=[
                FilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                )
                for rule in config.filter_rules
            ],
            poll_interval_seconds=config.poll_interval_seconds,
            max_backlog_hours=config.max_backlog_hours,
            error_retry_attempts=config.error_retry_attempts,
            is_active=config.is_active,
            activated_at=config.activated_at.isoformat() if config.activated_at else None,
            last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at.isoformat() if config.last_error_at else None
        )

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{id}", response_model=UpdateEmailConfigResponse)
async def update_email_config(
    id: int,
    request: UpdateEmailConfigRequest,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> UpdateEmailConfigResponse:
    """Update email configuration"""

    try:
        # Convert Pydantic FilterRuleUpdate to dataclass FilterRule (if provided)
        filter_rules = None
        if request.filter_rules is not None:
            filter_rules = [
                FilterRuleDataclass(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive or False
                )
                for rule in request.filter_rules
            ]

        # Create EmailConfigUpdate dataclass
        config_update = EmailConfigUpdate(
            description=request.description,
            filter_rules=filter_rules,
            poll_interval_seconds=request.poll_interval_seconds,
            max_backlog_hours=request.max_backlog_hours,
            error_retry_attempts=request.error_retry_attempts
        )

        # Update config via service
        config = config_service.update_config(id, config_update)

        return UpdateEmailConfigResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            email_address=config.email_address,
            folder_name=config.folder_name,
            filter_rules=[
                FilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                )
                for rule in config.filter_rules
            ],
            poll_interval_seconds=config.poll_interval_seconds,
            max_backlog_hours=config.max_backlog_hours,
            error_retry_attempts=config.error_retry_attempts,
            is_active=config.is_active,
            activated_at=config.activated_at.isoformat() if config.activated_at else None,
            last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at.isoformat() if config.last_error_at else None
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {id} not found"
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> None:
    """Delete email configuration (must be deactivated first)"""

    try:
        config_service.delete_config(id)

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {id} not found"
        )

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post("/{id}/activate", response_model=ActivateEmailConfigResponse)
async def activate_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> ActivateEmailConfigResponse:
    """Activate email configuration (starts email monitoring)"""

    try:
        config = config_service.activate_config(id)

        return ActivateEmailConfigResponse(
            id=config.id,
            is_active=config.is_active,
            activated_at=config.activated_at.isoformat() if config.activated_at else '',
            name=config.name,
            description=config.description,
            email_address=config.email_address,
            folder_name=config.folder_name,
            filter_rules=[
                FilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                )
                for rule in config.filter_rules
            ],
            poll_interval_seconds=config.poll_interval_seconds,
            max_backlog_hours=config.max_backlog_hours,
            error_retry_attempts=config.error_retry_attempts,
            last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at.isoformat() if config.last_error_at else None
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {id} not found"
        )


@router.post("/{id}/deactivate", response_model=DeactivateEmailConfigResponse)
async def deactivate_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> DeactivateEmailConfigResponse:
    """Deactivate email configuration (stops email monitoring)"""

    try:
        config = config_service.deactivate_config(id)

        return DeactivateEmailConfigResponse(
            id=config.id,
            is_active=config.is_active,
            name=config.name,
            description=config.description,
            email_address=config.email_address,
            folder_name=config.folder_name,
            filter_rules=[
                FilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                )
                for rule in config.filter_rules
            ],
            poll_interval_seconds=config.poll_interval_seconds,
            max_backlog_hours=config.max_backlog_hours,
            error_retry_attempts=config.error_retry_attempts,
            last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at.isoformat() if config.last_error_at else None
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {id} not found"
        )

@router.get("/discovery/accounts", response_model=DiscoverEmailAccountsResponse)
async def discover_email_accounts(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
) -> DiscoverEmailAccountsResponse:
    """List available email accounts for configuration wizard Step 1"""
    accounts = ingestion_service.discover_email_accounts()

    return DiscoverEmailAccountsResponse(
        accounts=[
            EmailAccount(
                email_address=account.email_address,
                display_name=account.display_name
            )
            for account in accounts
        ]
    )

@router.get("/discovery/folders", response_model=List[EmailFolderItem])
async def discover_email_folders(
    email_address: str,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
) -> List[EmailFolderItem]:
    """List available folders for selected email account (wizard Step 2)"""

    try:
        folders = ingestion_service.discover_folders(
            email_address=email_address,
            provider_type='outlook_com'
        )

        return [
            EmailFolderItem(
                folder_name=folder.name,
                folder_path=folder.full_path
            )
            for folder in folders
        ]

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/validate", response_model=ValidateEmailConfigResponse)
async def validate_email_config(
    request: ValidateEmailConfigRequest,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
) -> ValidateEmailConfigResponse:
    """Validate email configuration before creation (wizard Step 4)"""

    try:
        # Test connection to email account and folder
        result = ingestion_service.test_connection(
            email_address=request.email_address,
            folder_name=request.folder_name,
            provider_type="outlook_com"
        )

        if result.success:
            return ValidateEmailConfigResponse(
                email_address=request.email_address,
                folder_name=request.folder_name,
                message="Configuration is valid"
            )
        else:
            # Connection test failed - return 400
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Cannot connect to email account"
            )

    except HTTPException:
        # Re-raise HTTP exceptions unchanged
        raise

    except Exception as e:
        logger.error(f"Error validating email config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service error"
        )
