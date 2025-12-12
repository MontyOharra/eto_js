"""
Email Account Mappers

Convert between domain types and API schemas for email accounts.
"""

from shared.types.email_accounts import (
    EmailAccount,
    EmailAccountSummary,
    EmailAccountCreate,
    EmailAccountUpdate,
    StandardProviderSettings,
    ProviderSettings,
    PasswordCredentials,
    OAuthCredentials,
    Credentials,
)
from features.email.integrations.base_integration import ValidationResult
from api.schemas.email_accounts import (
    EmailAccountResponse,
    EmailAccountSummaryResponse,
    EmailAccountListResponse,
    CreateEmailAccountRequest,
    UpdateEmailAccountRequest,
    ValidateConnectionRequest,
    ValidationResultResponse,
    StandardProviderSettingsSchema,
    PasswordCredentialsSchema,
    OAuthCredentialsSchema,
)


# ========== Provider Settings Conversions ==========

def provider_settings_to_api(settings: ProviderSettings) -> StandardProviderSettingsSchema:
    """Convert domain ProviderSettings to API schema"""
    if isinstance(settings, StandardProviderSettings):
        return StandardProviderSettingsSchema(
            imap_host=settings.imap_host,
            imap_port=settings.imap_port,
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            use_ssl=settings.use_ssl,
        )
    # Add other provider types here as needed
    raise ValueError(f"Unknown provider settings type: {type(settings)}")


def provider_settings_to_domain(schema: StandardProviderSettingsSchema) -> ProviderSettings:
    """Convert API schema to domain ProviderSettings"""
    return StandardProviderSettings(
        imap_host=schema.imap_host,
        imap_port=schema.imap_port,
        smtp_host=schema.smtp_host,
        smtp_port=schema.smtp_port,
        use_ssl=schema.use_ssl,
    )


# ========== Credentials Conversions ==========

def credentials_to_domain(schema: PasswordCredentialsSchema | OAuthCredentialsSchema) -> Credentials:
    """Convert API schema to domain Credentials"""
    if isinstance(schema, PasswordCredentialsSchema):
        return PasswordCredentials(password=schema.password)
    elif isinstance(schema, OAuthCredentialsSchema):
        from datetime import datetime
        token_expiry = None
        if schema.token_expiry:
            token_expiry = datetime.fromisoformat(schema.token_expiry)
        return OAuthCredentials(
            access_token=schema.access_token,
            refresh_token=schema.refresh_token,
            token_expiry=token_expiry,
        )
    raise ValueError(f"Unknown credentials type: {type(schema)}")


# ========== Domain → API (Response) Conversions ==========

def email_account_to_api(account: EmailAccount) -> EmailAccountResponse:
    """Convert domain EmailAccount to API response"""
    return EmailAccountResponse(
        id=account.id,
        name=account.name,
        description=account.description,
        provider_type=account.provider_type,
        email_address=account.email_address,
        provider_settings=provider_settings_to_api(account.provider_settings),
        is_validated=account.is_validated,
        validated_at=account.validated_at.isoformat() if account.validated_at else None,
        capabilities=account.capabilities,
        last_error_message=account.last_error_message,
        last_error_at=account.last_error_at.isoformat() if account.last_error_at else None,
        created_at=account.created_at.isoformat(),
        updated_at=account.updated_at.isoformat(),
    )


def email_account_summary_to_api(summary: EmailAccountSummary) -> EmailAccountSummaryResponse:
    """Convert domain EmailAccountSummary to API response"""
    return EmailAccountSummaryResponse(
        id=summary.id,
        name=summary.name,
        email_address=summary.email_address,
        provider_type=summary.provider_type,
        is_validated=summary.is_validated,
        capabilities=summary.capabilities,
    )


def email_account_list_to_api(summaries: list[EmailAccountSummary]) -> EmailAccountListResponse:
    """Convert list of domain EmailAccountSummary to API response"""
    return EmailAccountListResponse(
        accounts=[email_account_summary_to_api(s) for s in summaries],
        total=len(summaries),
    )


def validation_result_to_api(result: ValidationResult) -> ValidationResultResponse:
    """Convert domain ValidationResult to API response"""
    return ValidationResultResponse(
        success=result.success,
        message=result.message,
        capabilities=result.capabilities,
        folder_count=result.folder_count,
    )


# ========== API (Request) → Domain Conversions ==========

def create_request_to_domain(request: CreateEmailAccountRequest) -> EmailAccountCreate:
    """Convert API CreateEmailAccountRequest to domain EmailAccountCreate"""
    return EmailAccountCreate(
        name=request.name,
        description=request.description,
        provider_type=request.provider_type,
        email_address=request.email_address,
        provider_settings=provider_settings_to_domain(request.provider_settings),
        credentials=credentials_to_domain(request.credentials),
    )


def update_request_to_domain(request: UpdateEmailAccountRequest) -> EmailAccountUpdate:
    """Convert API UpdateEmailAccountRequest to domain EmailAccountUpdate"""
    provider_settings = None
    if request.provider_settings is not None:
        provider_settings = provider_settings_to_domain(request.provider_settings)

    credentials = None
    if request.credentials is not None:
        credentials = credentials_to_domain(request.credentials)

    return EmailAccountUpdate(
        name=request.name,
        description=request.description,
        provider_settings=provider_settings,
        credentials=credentials,
        is_validated=request.is_validated,
        capabilities=request.capabilities,
        clear_errors=request.clear_errors,
    )
