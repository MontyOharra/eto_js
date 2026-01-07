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
    BaseModule,
    TransformModule,
    LogicModule,
    MiscModule,
    OutputModule,
    ComparatorModule,
    Module,
    ModuleCreate,
    ModuleUpdate
)

# Pipeline execution types (in-memory results, no persistence)
from shared.types.pipeline_execution import (
    PipelineExecutionStepResult,
    PipelineExecutionResult,
)

# Pending orders types
from shared.types.pending_orders import (
    PendingOrderStatus,
    PendingUpdateStatus,
    FieldState,
    REQUIRED_FIELDS,
    VALID_FIELD_NAMES,
    PendingOrder,
    PendingOrderCreate,
    PendingOrderUpdate,
    PendingOrderHistory,
    PendingOrderHistoryCreate,
    PendingOrderHistoryUpdate,
    PendingUpdate,
    PendingUpdateCreate,
    PendingUpdateUpdate,
    PendingUpdateHistory,
    PendingUpdateHistoryCreate,
    PendingUpdateHistoryUpdate,
    FieldSource,
    FieldStateEmpty,
    FieldStateSet,
    FieldStateConfirmed,
    FieldStateConflict,
    FieldStateResult,
    ProcessingResult,
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
    "BaseModule",
    "TransformModule",
    "LogicModule",
    "ComparatorModule",
    "MiscModule",
    "OutputModule",
    "Module",
    "ModuleCreate",
    "ModuleUpdate",
    # Pipeline execution (in-memory results)
    "PipelineExecutionStepResult",
    "PipelineExecutionResult",
    # Pending orders
    "PendingOrderStatus",
    "PendingUpdateStatus",
    "FieldState",
    "REQUIRED_FIELDS",
    "VALID_FIELD_NAMES",
    "PendingOrder",
    "PendingOrderCreate",
    "PendingOrderUpdate",
    "PendingOrderHistory",
    "PendingOrderHistoryCreate",
    "PendingOrderHistoryUpdate",
    "PendingUpdate",
    "PendingUpdateCreate",
    "PendingUpdateUpdate",
    "PendingUpdateHistory",
    "PendingUpdateHistoryCreate",
    "PendingUpdateHistoryUpdate",
    "FieldSource",
    "FieldStateEmpty",
    "FieldStateSet",
    "FieldStateConfirmed",
    "FieldStateConflict",
    "FieldStateResult",
    "ProcessingResult",
]
