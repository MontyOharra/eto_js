"""Shared domain types (dataclasses) for internal service/repository layer"""

# Email account types
from shared.types.email_accounts import (
    StandardProviderSettings,
    ProviderSettings,
    PasswordCredentials,
    OAuthCredentials,
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
    EmailAccountInfo,
    EmailFolder,
    EmailMessage,
    ConnectionTestResult,
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

# Pipeline execution types
from shared.types.pipeline_execution import (
    PipelineExecutionStep,
    PipelineExecutionStepCreate,
    # Simulation types
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
    "StandardProviderSettings",
    "ProviderSettings",
    "PasswordCredentials",
    "OAuthCredentials",
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
    "EmailAccountInfo",
    "EmailFolder",
    "EmailMessage",
    "ConnectionTestResult",
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
    # Pipeline execution
    "PipelineExecutionStep",
    "PipelineExecutionStepCreate",
    # Simulation
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
    "FieldSource",
    "FieldStateEmpty",
    "FieldStateSet",
    "FieldStateConfirmed",
    "FieldStateConflict",
    "FieldStateResult",
    "ProcessingResult",
]
