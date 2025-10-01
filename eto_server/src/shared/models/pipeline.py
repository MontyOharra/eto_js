"""
Pipeline Models for Transformation Pipeline System
Integrated with ETO system for template-based pipeline execution
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PipelineStateBase(BaseModel):
    """Base pipeline state containing execution data"""
    entry_points: list[Dict[str, Any]] = Field(default_factory=list, description="Pipeline entry points")
    modules: list[Dict[str, Any]] = Field(default_factory=list, description="Module instances")
    connections: list[Dict[str, Any]] = Field(default_factory=list, description="Node connections")


class VisualStateBase(BaseModel):
    """Base visual state containing UI positioning"""
    modules: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Module positions")
    entryPoints: Optional[Dict[str, Dict[str, float]]] = Field(default=None, description="Entry point positions")


class PipelineBase(BaseModel):
    """Base pipeline model with common fields"""
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    template_id: Optional[str] = Field(None, description="Associated PDF template ID for ETO integration")
    schema_version: str = Field(default="1.0", description="Pipeline schema version")
    pipeline_json: PipelineStateBase = Field(..., description="Pipeline execution state")
    visual_json: VisualStateBase = Field(..., description="Pipeline visual layout")


class PipelineCreate(PipelineBase):
    """Pipeline creation model - no updates allowed, only creates"""
    pass


class Pipeline(PipelineBase):
    """Pipeline model with database fields"""
    id: str = Field(..., description="Pipeline unique identifier")
    plan_checksum: Optional[str] = Field(None, description="Compiled plan checksum")
    compiled_at: Optional[str] = Field(None, description="ISO datetime when pipeline was compiled")
    created_at: str = Field(..., description="ISO datetime when pipeline was created")
    is_active: bool = Field(default=True, description="Whether pipeline is active")


class PipelineSummary(BaseModel):
    """Pipeline summary for listing operations"""
    id: str
    name: str
    description: Optional[str]
    template_id: Optional[str]
    created_at: str
    is_active: bool
    module_count: int = Field(..., description="Number of modules in pipeline")
    connection_count: int = Field(..., description="Number of connections in pipeline")


class PipelineExecutionRequest(BaseModel):
    """Request model for pipeline execution"""
    pipeline_id: str = Field(..., description="Pipeline to execute")
    entry_values: Dict[str, Any] = Field(..., description="Input values for entry points")
    execution_id: Optional[str] = Field(None, description="Optional execution ID for tracking")


class PipelineExecutionResult(BaseModel):
    """Result model for pipeline execution"""
    execution_id: str
    pipeline_id: str
    status: str = Field(..., description="success, failed, or timeout")
    result_values: Optional[Dict[str, Any]] = Field(None, description="Output values if successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    started_at: str = Field(..., description="ISO datetime when execution started")
    completed_at: Optional[str] = Field(None, description="ISO datetime when execution completed")