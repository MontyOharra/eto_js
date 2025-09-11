"""
Pipeline Types
Shared types for transformation pipeline processing
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import ProcessingStatus


@dataclass
class ModuleDefinition:
    """Transformation pipeline module definition"""
    id: str
    name: str
    description: Optional[str]
    version: str
    input_config: Dict[str, Any]
    output_config: Dict[str, Any]
    config_schema: Optional[Dict[str, Any]]
    service_endpoint: Optional[str]
    handler_name: Optional[str]
    color: str = '#3B82F6'
    category: str = 'Processing'
    is_active: bool = True


@dataclass 
class PipelineDefinition:
    """Transformation pipeline definition"""
    id: str
    name: str
    description: Optional[str]
    created_by_user: str
    pipeline_definition: Dict[str, Any]
    start_modules: List[str]
    end_modules: List[str]
    execution_metadata: Optional[Dict[str, Any]]
    status: str = 'draft'
    is_active: bool = True


@dataclass
class ExecutionResult:
    """Result of pipeline execution"""
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    output_data: Optional[Dict[str, Any]] = None