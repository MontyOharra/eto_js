"""
Common Types
Basic types and enums used across all features
"""
from enum import Enum
from typing import Literal

class Status(str, Enum):
    """General status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DRAFT = "draft"

class ProcessingStatus(str, Enum):
    """Processing status for various operations"""
    NOT_STARTED = "not_started"
    PROCESSING = "processing" 
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    NEEDS_TEMPLATE = "needs_template"

# Type aliases for common patterns
OptionalString = str | None
EntityId = int