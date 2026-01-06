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
    SendEmailRequest,
    SendEmailResponse,
)
from api.mappers.email_accounts import (
    email_account_list_to_api,
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
    return result


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
        return account
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
        account = service.create_validated_account(request)
        return account
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
        account = service.update_account(account_id, request)
        return account
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
        return account
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/{account_id}/send",
    response_model=SendEmailResponse,
    summary="Send email (test endpoint)",
    description="Send an email using the specified account. This endpoint can be used "
                "to test SMTP configuration before integrating into automated workflows.",
)
async def send_email(
    account_id: int,
    request: SendEmailRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> SendEmailResponse:
    """Send an email using the specified account."""
    try:
        result = service.send_email(
            account_id=account_id,
            to_address=request.to_address,
            subject=request.subject,
            body=request.body,
            body_html=request.body_html,
        )
        return SendEmailResponse(
            success=result.success,
            message=result.message,
        )
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
