from shared.types.email_configs import (
    EmailConfig,
    EmailConfigSummary,
    EmailConfigCreate,
    EmailConfigUpdate,
    FilterRule as FilterRuleDomain,
)
from api.schemas.email_configs import (
    EmailConfigSummary as EmailConfigSummarySchema,
    EmailConfig as EmailConfigSchema,
    FilterRule as FilterRuleSchema,
    CreateEmailConfigRequest,
    UpdateEmailConfigRequest,
)

# ========== Domain → API (Response) Conversions ==========

def convert_email_config_summary_list(summaries: list[EmailConfigSummary]) -> list[EmailConfigSummarySchema]:
    """Convert list of domain EmailConfigSummary to API schema"""
    return [
        EmailConfigSummarySchema(
            id=summary.id,
            name=summary.name,
            is_active=summary.is_active,
            last_check_time=summary.last_check_time.isoformat() if summary.last_check_time else None
        )
        for summary in summaries
    ]

def convert_email_config(config: EmailConfig) -> EmailConfigSchema:
    """Convert domain EmailConfig to API schema"""
    return EmailConfigSchema(
        id=config.id,
        name=config.name,
        description=config.description,
        email_address=config.email_address,
        folder_name=config.folder_name,
        filter_rules=[
            FilterRuleSchema(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            )
            for rule in config.filter_rules
        ],
        poll_interval_seconds=config.poll_interval_seconds,
        is_active=config.is_active,
        activated_at=config.activated_at.isoformat() if config.activated_at else None,
        last_check_time=config.last_check_time.isoformat() if config.last_check_time else None,
        last_error_message=config.last_error_message,
        last_error_at=config.last_error_at.isoformat() if config.last_error_at else None
    )

# ========== API (Request) → Domain Conversions ==========

def convert_create_request(request: CreateEmailConfigRequest) -> EmailConfigCreate:
    """Convert API CreateEmailConfigRequest to domain EmailConfigCreate"""
    return EmailConfigCreate(
        name=request.name,
        description=request.description,
        email_address=request.email_address,
        folder_name=request.folder_name,
        filter_rules=[
            FilterRuleDomain(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            )
            for rule in request.filter_rules
        ],
        poll_interval_seconds=request.poll_interval_seconds,
    )

def convert_update_request(request: UpdateEmailConfigRequest) -> EmailConfigUpdate:
    """Convert API UpdateEmailConfigRequest to domain EmailConfigUpdate"""
    filter_rules = None
    if request.filter_rules is not None:
        filter_rules = [
            FilterRuleDomain(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            )
            for rule in request.filter_rules
        ]

    return EmailConfigUpdate(
        description=request.description,
        filter_rules=filter_rules,
        poll_interval_seconds=request.poll_interval_seconds,
    )