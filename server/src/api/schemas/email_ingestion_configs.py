"""
Email Ingestion Config API Schemas

Pydantic models for email ingestion config API requests and responses.
Reuses domain types from shared/types where possible.
"""

from pydantic import BaseModel, Field

from shared.types.email_ingestion_configs import (
    FilterRule,
    EmailIngestionConfig,
    EmailIngestionConfigSummary,
    EmailIngestionConfigWithAccount,
    EmailIngestionConfigCreate,
    EmailIngestionConfigUpdate,
)


# ========== Validation ==========

class ValidateIngestionConfigRequest(BaseModel):
    """Request to validate an ingestion config before creation"""
    account_id: int
    folder_name: str


class ValidateIngestionConfigResponse(BaseModel):
    """Response from ingestion config validation"""
    valid: bool
    message: str


# ========== CRUD - Reuse domain types ==========

CreateIngestionConfigRequest = EmailIngestionConfigCreate
UpdateIngestionConfigRequest = EmailIngestionConfigUpdate

# Response types
IngestionConfigResponse = EmailIngestionConfig
IngestionConfigSummaryResponse = EmailIngestionConfigSummary
IngestionConfigWithAccountResponse = EmailIngestionConfigWithAccount


class IngestionConfigListResponse(BaseModel):
    """List of ingestion configs with account info"""
    configs: list[EmailIngestionConfigWithAccount]
    total: int
