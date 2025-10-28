"""Shared domain types (dataclasses) for internal service/repository layer"""

# Email configuration types
from shared.types.email_configs import (
    FilterRule,
    EmailConfig,
    EmailConfigSummary,
    EmailConfigCreate,
    EmailConfigUpdate,
)

# Email types
from shared.types.email import (
    Email,
    EmailCreate,
)

# Email integration types (transient dataclasses from integrations)
from shared.types.email_integrations import (
    EmailAccount,
    EmailFolder,
    EmailMessage,
    ConnectionTestResult,
)

# PDF files types
from shared.types.pdf_files import (
    PdfMetadata,
    PdfCreate,
)

# Module types
from shared.types.modules import (
    AllowedModuleNodeTypes,
    ModuleKind,
    NodeTypeRule,
    NodeGroup,
    IOSideShape,
    IOShape,
    ModuleMeta,
    BaseModule,
    TransformModule,
    ActionModule,
    LogicModule,
    ComparatorModule,
    Module,
    ModuleCreate,
    ModuleUpdate
)

# Pipeline execution types
from shared.types.pipeline_execution import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
    PipelineExecutionStep,
    PipelineExecutionStepCreate,
    # Simulation types
    PipelineExecutionStepResult,
    ActionExecutionData,
    PipelineExecutionResult,
)

__all__ = [
    # Email configuration
    "FilterRule",
    "EmailConfig",
    "EmailConfigSummary",
    "EmailConfigCreate",
    "EmailConfigUpdate",
    # Email
    "Email",
    "EmailCreate",
    # Email integrations
    "EmailAccount",
    "EmailFolder",
    "EmailMessage",
    "ConnectionTestResult",
    # PDF files
    "PdfMetadata",
    "PdfCreate",
    # Module types
    "AllowedModuleNodeTypes",
    "ModuleKind",
    "NodeTypeRule",
    "NodeGroup",
    "IOSideShape",
    "IOShape",
    "ModuleMeta",
    "BaseModule",
    "TransformModule",
    "ActionModule",
    "LogicModule",
    "ComparatorModule",
    "Module",
    "ModuleCreate",
    "ModuleUpdate",
    # Pipeline execution
    "PipelineExecutionRun",
    "PipelineExecutionRunCreate",
    "PipelineExecutionStep",
    "PipelineExecutionStepCreate",
    # Simulation
    "PipelineExecutionStepResult",
    "ActionExecutionData",
    "PipelineExecutionResult",
]
