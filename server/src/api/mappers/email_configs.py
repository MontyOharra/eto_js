from shared.types.email_configs import (
    EmailConfig,
    EmailConfigSummary,
    EmailConfigCreate,
    EmailConfigUpdate,
    FilterRule,
    ProviderSettings,
    ImapProviderSettings
)
from api.schemas.email_configs import (
    EmailConfigSummary as EmailConfigSummaryPydantic,
    EmailConfig as EmailConfigPydantic,
    FilterRule as FilterRulePydantic,
    CreateEmailConfigRequest,
    UpdateEmailConfigRequest,
    ProviderSettings as ProviderSettingsSchema,
    ImapProviderSettings as ImapProviderSettingsSchema,
)


def _provider_settings_to_api(settings: ProviderSettings | None) -> ProviderSettingsSchema | None:
    if not settings:
        return None

    if isinstance(settings, ImapProviderSettings):
        return ImapProviderSettingsSchema(
            host=settings.host,
            port=settings.port,
            email_address=settings.email_address,
            password=settings.password,
            use_ssl=settings.use_ssl
        )
    # ... similar for GraphApiProviderSettings

def _provider_settings_to_domain(schema: ProviderSettingsSchema | None) -> ProviderSettings | None:
    if not schema:
        return None

    if isinstance(schema, ImapProviderSettingsSchema):
        return ImapProviderSettings(
            host=schema.host,
            port=schema.port,
            email_address=schema.email_address,
            password=schema.password,
            use_ssl=schema.use_ssl
        )
    # ... similar for GraphApiProviderSettings

# ========== Domain → API (Response) Conversions ==========

def email_config_summary_list_to_api(summaries: list[EmailConfigSummary]) -> list[EmailConfigSummaryPydantic]:
    """Convert list of domain EmailConfigSummary to API schema"""
    return [
        EmailConfigSummaryPydantic(
            id=summary.id,
            name=summary.name,
            is_active=summary.is_active,
            last_check_time=summary.last_check_time.isoformat() if summary.last_check_time else None
        )
        for summary in summaries
    ]
    
    

def email_config_to_api(config: EmailConfig) -> EmailConfigPydantic:
    """Convert domain EmailConfig to API schema"""
    return EmailConfigPydantic(
        id=config.id,
        name=config.name,
        description=config.description,
        provider_type=config.provider_type,
        provider_settings=_provider_settings_to_api(config.provider_settings),
        folder_name=config.folder_name,
        filter_rules=[
            FilterRulePydantic(
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

def create_request_to_domain(request: CreateEmailConfigRequest) -> EmailConfigCreate:
    """Convert API CreateEmailConfigRequest to domain EmailConfigCreate"""
    return EmailConfigCreate(
        name=request.name,
        description=request.description,
        provider_type=request.provider_type,
        provider_settings=_provider_settings_to_domain(request.provider_settings),
        folder_name=request.folder_name,
        filter_rules=[
            FilterRule(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            )
            for rule in request.filter_rules
        ],
        poll_interval_seconds=request.poll_interval_seconds,
    )

def update_request_to_domain(request: UpdateEmailConfigRequest) -> EmailConfigUpdate:
    """Convert API UpdateEmailConfigRequest to domain EmailConfigUpdate"""
    filter_rules = None
    if request.filter_rules is not None:
        filter_rules = [
            FilterRule(
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