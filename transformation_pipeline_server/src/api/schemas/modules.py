from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ModuleCatalogResponse(BaseModel):
    """Response model for module catalog"""
    modules: List[Dict[str, Any]]

class ModuleExecuteRequest(BaseModel):
    """Request model for module execution"""
    module_id: str = Field(..., description="Module ID from catalog")
    inputs: Dict[str, Any] = Field(..., description="Input values keyed by input node ID")
    config: Dict[str, Any] = Field(..., description="Module configuration parameters")
    use_cache: bool = Field(True, description="Whether to use cached module (faster)")


class ModuleExecuteResponse(BaseModel):
    """Response model for module execution"""
    success: bool
    module_id: str
    outputs: Dict[str, Any] = Field(..., description="Output values keyed by output node ID")
    error: Optional[str] = None
    performance_ms: float = Field(..., description="Execution time in milliseconds")
    cache_used: bool = Field(..., description="Whether module was loaded from cache")