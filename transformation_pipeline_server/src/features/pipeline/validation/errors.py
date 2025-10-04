"""
Validation error models and types
Defines error codes, error models, and validation results for pipeline validation
"""
from enum import Enum
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ValidationErrorCode(str, Enum):
    """Error codes for pipeline validation"""

    # Schema errors (§2.1)
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    DUPLICATE_NODE_ID = "DUPLICATE_NODE_ID"

    # Edge errors (§2.3)
    MISSING_UPSTREAM = "MISSING_UPSTREAM"
    MULTIPLE_UPSTREAMS = "MULTIPLE_UPSTREAMS"
    EDGE_TYPE_MISMATCH = "EDGE_TYPE_MISMATCH"
    SELF_LOOP = "SELF_LOOP"

    # Graph errors (§2.4)
    CYCLE = "CYCLE"

    # Module errors (§2.5)
    MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
    GROUP_CARDINALITY = "GROUP_CARDINALITY"
    TYPEVAR_MISMATCH = "TYPEVAR_MISMATCH"
    INVALID_CONFIG = "INVALID_CONFIG"

    # Reachability errors (§2.6)
    NO_ACTIONS = "NO_ACTIONS"

    # Runtime errors
    RUNTIME_ERROR = "RUNTIME_ERROR"


class ValidationError(BaseModel):
    """Validation error with location information"""
    code: ValidationErrorCode
    message: str
    where: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of pipeline validation"""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
