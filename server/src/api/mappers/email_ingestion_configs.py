"""
Email Ingestion Config Mappers

Convert between domain types and API schemas for email ingestion configs.
"""

from shared.types.email_ingestion_configs import (
    EmailIngestionConfig,
    EmailIngestionConfigSummary,
    EmailIngestionConfigWithAccount,
    EmailIngestionConfigCreate,
    EmailIngestionConfigUpdate,
    FilterRule,
)
from api.schemas.email_ingestion_configs import (
    FilterRuleSchema,
    CreateIngestionConfigRequest,
    UpdateIngestionConfigRequest,
    IngestionConfigResponse,
    IngestionConfigSummaryResponse,
    IngestionConfigWithAccountResponse,
    IngestionConfigListResponse,
    ValidateIngestionConfigResponse,
)


# ========== Filter Rule Conversions ==========

def filter_rule_to_api(rule: FilterRule) -> FilterRuleSchema:
    """Convert domain FilterRule to API schema"""
    return FilterRuleSchema(
        field=rule.field,
        operation=rule.operation,
        value=rule.value,
        case_sensitive=rule.case_sensitive,
    )


def filter_rule_to_domain(schema: FilterRuleSchema) -> FilterRule:
    """Convert API schema to domain FilterRule"""
    return FilterRule(
        field=schema.field,
        operation=schema.operation,
        value=schema.value,
        case_sensitive=schema.case_sensitive,
    )


# ========== Domain → API (Response) Conversions ==========

def ingestion_config_to_api(config: EmailIngestionConfig) -> IngestionConfigResponse:
    """Convert domain EmailIngestionConfig to API response"""
    return IngestionConfigResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        account_id=config.account_id,
        folder_name=config.folder_name,
        filter_rules=[filter_rule_to_api(r) for r in config.filter_rules],
        poll_interval_seconds=config.poll_interval_seconds,
        use_idle=config.use_idle,
        is_active=config.is_active,
        activated_at=config.activated_at.isoformat() if config.activated_at else None,
        last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
        last_processed_uid=config.last_processed_uid,
        last_error_message=config.last_error_message,
        last_error_at=config.last_error_at.isoformat() if config.last_error_at else None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


def ingestion_config_summary_to_api(summary: EmailIngestionConfigSummary) -> IngestionConfigSummaryResponse:
    """Convert domain EmailIngestionConfigSummary to API response"""
    return IngestionConfigSummaryResponse(
        id=summary.id,
        name=summary.name,
        account_id=summary.account_id,
        folder_name=summary.folder_name,
        is_active=summary.is_active,
        last_check_time=summary.last_check_time.isoformat() if summary.last_check_time else None,
    )


def ingestion_config_with_account_to_api(config: EmailIngestionConfigWithAccount) -> IngestionConfigWithAccountResponse:
    """Convert domain EmailIngestionConfigWithAccount to API response"""
    return IngestionConfigWithAccountResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        account_id=config.account_id,
        account_name=config.account_name,
        account_email=config.account_email,
        folder_name=config.folder_name,
        is_active=config.is_active,
        last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
        last_error_message=config.last_error_message,
    )


def ingestion_config_list_to_api(configs: list[EmailIngestionConfigWithAccount]) -> IngestionConfigListResponse:
    """Convert list of domain EmailIngestionConfigWithAccount to API response"""
    return IngestionConfigListResponse(
        configs=[ingestion_config_with_account_to_api(c) for c in configs],
        total=len(configs),
    )


def validation_result_to_api(valid: bool, message: str) -> ValidateIngestionConfigResponse:
    """Create validation result API response"""
    return ValidateIngestionConfigResponse(
        valid=valid,
        message=message,
    )


# ========== API (Request) → Domain Conversions ==========

def create_request_to_domain(request: CreateIngestionConfigRequest) -> EmailIngestionConfigCreate:
    """Convert API CreateIngestionConfigRequest to domain EmailIngestionConfigCreate"""
    return EmailIngestionConfigCreate(
        name=request.name,
        account_id=request.account_id,
        folder_name=request.folder_name,
        description=request.description,
        filter_rules=[filter_rule_to_domain(r) for r in request.filter_rules],
        poll_interval_seconds=request.poll_interval_seconds,
        use_idle=request.use_idle,
    )


def update_request_to_domain(request: UpdateIngestionConfigRequest) -> EmailIngestionConfigUpdate:
    """Convert API UpdateIngestionConfigRequest to domain EmailIngestionConfigUpdate"""
    filter_rules = None
    if request.filter_rules is not None:
        filter_rules = [filter_rule_to_domain(r) for r in request.filter_rules]

    return EmailIngestionConfigUpdate(
        name=request.name,
        description=request.description,
        folder_name=request.folder_name,
        filter_rules=filter_rules,
        poll_interval_seconds=request.poll_interval_seconds,
        use_idle=request.use_idle,
    )
