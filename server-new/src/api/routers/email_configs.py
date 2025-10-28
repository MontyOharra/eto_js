"""
Email Configuration API Router
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status

from api.schemas.email_configs import (
    CreateEmailConfigRequest,
    UpdateEmailConfigRequest,
    ValidateEmailConfigRequest,

    EmailConfig,
    EmailConfigSummary,
    DiscoverEmailAccountsResponse,
    DiscoverEmailFoldersResponse,
    ValidateEmailConfigResponse,
    EmailAccount,
    EmailFolder
)

from api.mappers.email_configs import (
    email_config_summary_list_to_api,
    email_config_to_api,
    create_request_to_domain,
    update_request_to_domain,
)

from shared.services.service_container import ServiceContainer
from features.email_configs.service import EmailConfigService
from features.email_ingestion.service import EmailIngestionService
from shared.exceptions.service import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/email-configs",
    tags=["Email Configurations"]
)


@router.get("", response_model=list[EmailConfigSummary])
async def list_email_configs(
    order_by: str = "name",
    desc: bool = False,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> list[EmailConfigSummary]:
    """List all email configurations (summary)"""

    configs = config_service.list_configs_summary(order_by=order_by, desc=desc)
    return email_config_summary_list_to_api(configs)


@router.get("/{id}", response_model=EmailConfig)
async def get_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Get email configuration details"""

    config = config_service.get_config(id)

    return email_config_to_api(config)


@router.post("", response_model=EmailConfig, status_code=status.HTTP_201_CREATED)
async def create_email_config(
    request: CreateEmailConfigRequest,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Create new email configuration"""
    config_create = create_request_to_domain(request)
    config = config_service.create_config(config_create)
    return email_config_to_api(config)

@router.put("/{id}", response_model=EmailConfig)
async def update_email_config(
    id: int,
    request: UpdateEmailConfigRequest,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Update email configuration"""
    config_update = update_request_to_domain(request)
    config = config_service.update_config(id, config_update)
    return email_config_to_api(config)


@router.delete("/{id}", response_model=EmailConfig)
async def delete_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Delete email configuration (must be deactivated first)"""

    return email_config_to_api(config_service.delete_config(id))



@router.post("/{id}/activate", response_model=EmailConfig)
async def activate_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Activate email configuration (starts email monitoring)"""
    config = config_service.activate_config(id)
    return email_config_to_api(config)


@router.post("/{id}/deactivate", response_model=EmailConfig)
async def deactivate_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Deactivate email configuration (stops email monitoring)"""

    config = config_service.deactivate_config(id)

    return email_config_to_api(config)


@router.get("/discovery/accounts", response_model=list[EmailAccount])
async def discover_email_accounts(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
) -> list[EmailAccount]:
    """List available email accounts for configuration wizard Step 1"""
    accounts = ingestion_service.discover_email_accounts()

    return [
            EmailAccount(
                email_address=account.email_address,
                display_name=account.display_name
            )
            for account in accounts
        ]

@router.get("/discovery/folders", response_model=list[EmailFolder])
async def discover_email_folders(
    email_address: str,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
) -> list[EmailFolder]:
    """List available folders for selected email account (wizard Step 2)"""

    folders = ingestion_service.discover_folders(
        email_address=email_address,
        provider_type='outlook_com'
    )

    return [
        EmailFolder(
            folder_name=folder.name,
            folder_path=folder.full_path
        )
        for folder in folders
    ]



@router.post("/validate", response_model=ValidateEmailConfigResponse)
async def validate_email_config(
    request: ValidateEmailConfigRequest,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
) -> ValidateEmailConfigResponse:
    """Validate email configuration before creation (wizard Step 4)"""

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
        raise ValidationError("Cannot connect to email account")
