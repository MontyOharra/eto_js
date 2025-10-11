"""
Pipeline Execution Types
All type definitions related to pipeline execution
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, List, Optional, Literal

class PipelineExecutionError(BaseModel):
    """Error information from pipeline execution"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    module_instance_id: Optional[str] = Field(None, description="Module that failed")


class PipelineExecutionRunResult(BaseModel):
    """Result of a pipeline execution"""
    status: Literal["success", "failed"]
    run_id: str
    started_at: str  # ISO format timestamp
    completed_at: str  # ISO format timestamp
    actions: List[Dict[str, Any]]  # Results from action modules
    errors: List[PipelineExecutionError]
    timings: Dict[str, float]  # module_instance_id -> elapsed_ms
    metadata: Optional[Dict[str, Any]] = None  # Additional execution metadata
