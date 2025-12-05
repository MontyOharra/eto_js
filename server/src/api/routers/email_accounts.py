"""
Email Account API Routes

REST endpoints for email account management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.email_accounts import (
    ValidateConnectionRequest,
    ValidationResultResponse,
    CreateEmailAccountRequest,
    UpdateEmailAccountRequest,
    EmailAccountResponse,
    EmailAccountListResponse,
    FolderListResponse,
)
from api.mappers.email_accounts import (
    email_account_to_api,
    email_account_list_to_api,
    validation_result_to_api,
    create_request_to_domain,
    update_request_to_domain,
    provider_settings_to_domain,
    credentials_to_domain,
)
from shared.services.service_container import ServiceContainer
from features.email.service import EmailService
from shared.exceptions.service import ObjectNotFoundError, ValidationError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-accounts", tags=["Email Accounts"])


@router.post(
    "/validate",
    response_model=ValidationResultResponse,
    summary="Test email connection",
    description="Test email server connection without creating an account. "
                "Use this to validate credentials before creating an account.",
)
async def validate_connection(
    request: ValidateConnectionRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> ValidationResultResponse:
    """Test email connection with provided credentials."""
    result = service.validate_connection(
        provider_type=request.provider_type,
        email_address=request.email_address,
        provider_settings=provider_settings_to_domain(request.provider_settings),
        credentials=credentials_to_domain(request.credentials),
    )
    return validation_result_to_api(result)


@router.get(
    "",
    response_model=EmailAccountListResponse,
    summary="List email accounts",
    description="Get all email accounts as summaries (credentials excluded).",
)
async def list_accounts(
    order_by: str = Query("name", description="Field to sort by"),
    desc: bool = Query(False, description="Sort descending"),
    validated_only: bool = Query(False, description="Only validated accounts"),
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> EmailAccountListResponse:
    """List all email accounts."""
    summaries = service.list_accounts(
        order_by=order_by,
        desc=desc,
        validated_only=validated_only,
    )
    return email_account_list_to_api(summaries)


@router.get(
    "/{account_id}/folders",
    response_model=FolderListResponse,
    summary="List account folders",
    description="List available folders/mailboxes for an email account. "
                "Connects to the server to retrieve the folder list.",
)
async def list_account_folders(
    account_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> FolderListResponse:
    """List folders for an email account."""
    try:
        folders = service.list_account_folders(account_id)
        return FolderListResponse(account_id=account_id, folders=folders)
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{account_id}",
    response_model=EmailAccountResponse,
    summary="Get email account",
    description="Get a single email account by ID.",
)
async def get_account(
    account_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> EmailAccountResponse:
    """Get email account by ID."""
    try:
        account = service.get_account(account_id)
        return email_account_to_api(account)
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "",
    response_model=EmailAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create email account",
    description="Create a new email account. The account should have been validated "
                "via the /validate endpoint first.",
)
async def create_account(
    request: CreateEmailAccountRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> EmailAccountResponse:
    """Create a new email account."""
    try:
        account_data = create_request_to_domain(request)
        account = service.create_validated_account(
            account_data=account_data,
            capabilities=request.capabilities,
        )
        return email_account_to_api(account)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{account_id}",
    response_model=EmailAccountResponse,
    summary="Update email account",
    description="Update an email account. If credentials are changed, "
                "re-validate using /validate endpoint.",
)
async def update_account(
    account_id: int,
    request: UpdateEmailAccountRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> EmailAccountResponse:
    """Update an email account."""
    try:
        account_update = update_request_to_domain(request)
        account = service.update_account(account_id, account_update)
        return email_account_to_api(account)
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{account_id}",
    response_model=EmailAccountResponse,
    summary="Delete email account",
    description="Delete an email account. Will fail if account has active ingestion configs.",
)
async def delete_account(
    account_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> EmailAccountResponse:
    """Delete an email account."""
    try:
        account = service.delete_account(account_id)
        return email_account_to_api(account)
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
