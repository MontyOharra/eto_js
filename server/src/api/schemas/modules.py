"""
Modules API Schemas
Request/response models for module catalog endpoints
"""
from typing import Any

from pydantic import BaseModel

from shared.types.output_channels import OutputChannelCategory, OutputChannelDataType


# ============================================================================
# Module Catalog Response
# ============================================================================

class ModuleResponse(BaseModel):
    """Module catalog entry for API responses."""
    identifier: str  # e.g., "text_cleaner"
    version: str
    name: str
    description: str | None = None
    module_kind: str  # "transform", "logic", "comparator", "misc", "output"
    meta: dict[str, Any]  # Module I/O metadata
    config_schema: dict[str, Any]  # JSON schema for module configuration
    color: str
    category: str


# ============================================================================
# Output Channel Response
# ============================================================================

class OutputChannel(BaseModel):
    """Output channel type definition for API responses."""
    name: str
    label: str
    data_type: OutputChannelDataType
    category: OutputChannelCategory
    description: str | None = None
    is_required: bool
