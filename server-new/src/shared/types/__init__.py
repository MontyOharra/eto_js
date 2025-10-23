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
]