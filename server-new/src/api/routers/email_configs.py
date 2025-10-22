"""
Email Configuration API Router
No deletion - configs are permanent, only deactivated
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.email_configs import (
    ListEmailConfigsResponse,
    EmailConfigDetail,
    CreateEmailConfigRequest,
    CreateEmailConfigResponse,
    UpdateEmailConfigRequest,
    UpdateEmailConfigResponse,
    ActivateEmailConfigResponse,
    DeactivateEmailConfigResponse,
    EmailAccount,
    DiscoverEmailAccountsResponse,
    DiscoverEmailFoldersResponse,
    ValidateEmailConfigRequest,
    ValidateEmailConfigResponse,
)

from shared.services.service_container import ServiceContainer

from features.email_ingestion.service import EmailIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/email-configs",
    tags=["Email Configurations"]
)


@router.get("", response_model=List[EmailConfigDetail])
async def list_email_configs() -> List[EmailConfigDetail]:
    """List all email configurations (summary)"""
    pass


@router.get("/{id}", response_model=EmailConfigDetail)
async def get_email_config(id: int) -> EmailConfigDetail:
    """Get email configuration details"""
    


@router.post("", response_model=CreateEmailConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_email_config(request: CreateEmailConfigRequest) -> CreateEmailConfigResponse:
    """Create new email configuration"""
    pass


@router.put("/{id}", response_model=UpdateEmailConfigResponse)
async def update_email_config(id: int, request: UpdateEmailConfigRequest) -> UpdateEmailConfigResponse:
    """Update email configuration"""
    pass


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_config(id: int) -> None:
    """Delete email configuration (must be deactivated first)"""
    pass


@router.post("/{id}/activate", response_model=ActivateEmailConfigResponse)
async def activate_email_config(id: int) -> ActivateEmailConfigResponse:
    """Activate email configuration (starts email monitoring)"""
    pass


@router.post("/{id}/deactivate", response_model=DeactivateEmailConfigResponse)
async def deactivate_email_config(id: int) -> DeactivateEmailConfigResponse:
    """Deactivate email configuration (stops email monitoring)"""
    pass

@router.get("/discovery/accounts", response_model=List[DiscoverEmailAccountsResponse])
async def discover_email_accounts(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),    
) -> DiscoverEmailAccountsResponse:
    """List available email accounts for configuration wizard Step 1"""
    accounts = await ingestion_service.discover_email_accounts()

    return DiscoverEmailAccountsResponse(
        accounts=[
            EmailAccount(
                email_address=account.email_address,
                display_name=account.display_name
            )
            for account in accounts
        ]
    )

@router.get("/discovery/folders", response_model=List[DiscoverEmailFoldersResponse])
async def discover_email_folders(email_address: Optional[str] = None) -> List[DiscoverEmailFoldersResponse]:
    """List available folders for selected email account (wizard Step 2)"""
    pass


@router.post("/validate", response_model=ValidateEmailConfigResponse)
async def validate_email_config(request: ValidateEmailConfigRequest) -> ValidateEmailConfigResponse:
    """Validate email configuration before creation (wizard Step 4)"""
    pass
