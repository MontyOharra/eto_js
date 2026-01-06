"""
Email Account Mappers

Convert between API request types and domain types for email accounts.
Since API schemas now reuse domain types directly, most conversions are trivial.
"""

from shared.types.email_accounts import (
    EmailAccountSummary,
    StandardProviderSettings,
    PasswordCredentials,
)
from api.schemas.email_accounts import (
    ValidateConnectionRequest,
    EmailAccountListResponse,
)


# ========== Request → Domain Conversions ==========

def provider_settings_to_domain(schema: StandardProviderSettings) -> StandardProviderSettings:
    """
    Convert API provider settings to domain type.
    Currently a pass-through since we use the same type.
    """
    return schema


def credentials_to_domain(schema: PasswordCredentials) -> PasswordCredentials:
    """
    Convert API credentials to domain type.
    Currently a pass-through since we use the same type.
    """
    return schema


# ========== Response Conversions ==========

def email_account_list_to_api(summaries: list[EmailAccountSummary]) -> EmailAccountListResponse:
    """Convert list of domain EmailAccountSummary to API response"""
    return EmailAccountListResponse(
        accounts=summaries,
        total=len(summaries),
    )
