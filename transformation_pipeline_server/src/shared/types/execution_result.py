"""
Execution Result Models
Models for pipeline execution results and errors
"""
from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ExecutionError(BaseModel):
    """Error information from pipeline execution"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    module_instance_id: Optional[str] = Field(None, description="Module that failed")


class RunResult(BaseModel):
    """Result of a pipeline execution"""
    status: Literal["success", "failed"]
    run_id: str
    started_at: str  # ISO format timestamp
    completed_at: str  # ISO format timestamp
    actions: List[Dict[str, Any]]  # Results from action modules
    errors: List[ExecutionError]
    timings: Dict[str, float]  # module_instance_id -> elapsed_ms
    metadata: Optional[Dict[str, Any]] = None  # Additional execution metadata