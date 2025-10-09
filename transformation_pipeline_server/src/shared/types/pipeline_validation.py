from typing import List, Optional, Dict, Set
from pydantic import BaseModel, Field

from shared.exceptions import PipelineValidationError

from .pipeline_state import ModuleInstance

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
    