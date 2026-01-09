"""Shared domain types (dataclasses) for internal service/repository layer"""

# Email account types
from shared.types.email_accounts import (
    ProviderType,
    StandardProviderSettings,
    ProviderSettings,
    PasswordCredentials,
    Credentials,
    EmailAccount,
    EmailAccountSummary,
    EmailAccountCreate,
    EmailAccountUpdate,
    EmailAccountValidationResult,
)

# Email ingestion configuration types
from shared.types.email_ingestion_configs import (
    FilterRule,
    EmailIngestionConfig,
    EmailIngestionConfigSummary,
    EmailIngestionConfigWithAccount,
    EmailIngestionConfigCreate,
    EmailIngestionConfigUpdate,
)

# Email types
from shared.types.email import (
    Email,
    EmailCreate,
)

# Email integration types (transient dataclasses from integrations)
from shared.types.email_integrations import (
    EmailMessage,
    EmailAttachment,
    ValidationResult,
    SendEmailResult,
)

# PDF files types
from shared.types.pdf_files import (
    PdfFile,
    PdfFileCreate,
)

# Module types
from shared.types.modules import (
    AllowedNodeType,
    ModuleKind,
    NodeTypeRule,
    NodeGroup,
    IOSideShape,
    IOShape,
    ModuleMeta,
    Module,
    ModuleCreate,
    ModuleUpdate
)

# Pipeline execution types (in-memory results, no persistence)
from shared.types.pipeline_execution import (
    PipelineExecutionStepResult,
    PipelineExecutionResult,
)

# Pending actions types (new unified system)
from shared.types.pending_actions import (
    PendingActionType,
    PendingActionStatus,
    OrderFieldDataType,
    OrderFieldDef,
    ORDER_FIELDS,
    REQUIRED_ORDER_FIELDS,
    VALID_ORDER_FIELD_NAMES,
    LocationValue,
    DimObject,
    PendingActionCreate,
    PendingActionUpdate,
    PendingAction,
    PendingActionFieldCreate,
    PendingActionFieldUpdate,
    PendingActionField,
    PendingActionFieldView,
    PendingActionListView,
    PendingActionDetailView,
    CleanupResult,
    ExecuteResult,
)

__all__ = [
    # Email accounts
    "ProviderType",
    "StandardProviderSettings",
    "ProviderSettings",
    "PasswordCredentials",
    "Credentials",
    "EmailAccount",
    "EmailAccountSummary",
    "EmailAccountCreate",
    "EmailAccountUpdate",
    "EmailAccountValidationResult",
    # Email ingestion configs
    "FilterRule",
    "EmailIngestionConfig",
    "EmailIngestionConfigSummary",
    "EmailIngestionConfigWithAccount",
    "EmailIngestionConfigCreate",
    "EmailIngestionConfigUpdate",
    # Email
    "Email",
    "EmailCreate",
    # Email integrations (transient)
    "EmailMessage",
    "EmailAttachment",
    "ValidationResult",
    "SendEmailResult",
    # PDF files
    "PdfFile",
    "PdfFileCreate",
    # Module types
    "AllowedNodeType",
    "ModuleKind",
    "NodeTypeRule",
    "NodeGroup",
    "IOSideShape",
    "IOShape",
    "ModuleMeta",
    "Module",
    "ModuleCreate",
    "ModuleUpdate",
    # Pipeline execution (in-memory results)
    "PipelineExecutionStepResult",
    "PipelineExecutionResult",
    # Pending actions (new unified system)
    "PendingActionType",
    "PendingActionStatus",
    "OrderFieldDataType",
    "OrderFieldDef",
    "ORDER_FIELDS",
    "REQUIRED_ORDER_FIELDS",
    "VALID_ORDER_FIELD_NAMES",
    "LocationValue",
    "DimObject",
    "PendingActionCreate",
    "PendingActionUpdate",
    "PendingAction",
    "PendingActionFieldCreate",
    "PendingActionFieldUpdate",
    "PendingActionField",
    "PendingActionFieldView",
    "PendingActionListView",
    "PendingActionDetailView",
    "CleanupResult",
    "ExecuteResult",
]
