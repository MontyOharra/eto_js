from typing import List, Optional, Dict, Set, Any
from pydantic import BaseModel, Field
from enum import Enum

from .pipeline_state import ModuleInstance


class PipelineValidationErrorCode(str, Enum):
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


class PipelineValidationError(BaseModel):
    """Validation error data model with location information"""
    code: PipelineValidationErrorCode
    message: str
    where: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class PipelineValidationResult(BaseModel):
    """Result of pipeline validation"""
    valid: bool
    errors: List[PipelineValidationError] = Field(default_factory=list)
    reachable_modules: Set[str] = Field(default_factory=set)


class PinInfo(BaseModel):
    """Information about a pin for index lookups"""
    node_id: str
    type: str
    module_instance_id: Optional[str] = None
    direction: str  # "entry" | "in" | "out"
    name: str


class PipelineIndices(BaseModel):
    pin_by_id: Dict[str, PinInfo] = Field(default_factory=dict, description="PinInfo from pipeline")
    module_by_id: Dict[str, ModuleInstance] = Field(default_factory=dict, description="ModuleInstance from pipeline")
    input_to_upstream: Dict[str, str] = Field(default_factory=dict, description="Input pin → upstream output pin")
    