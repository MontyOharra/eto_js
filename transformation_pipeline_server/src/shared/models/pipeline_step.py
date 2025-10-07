"""
Strongly-typed pipeline domain models
These models define the structure of transformation pipelines following CRUD patterns
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
import json

from .modules import ModuleKind

class PipelineStepBase(BaseModel):
    """Base fields for a compiled pipeline step"""
    plan_checksum: str = Field(..., description="SHA-256 checksum of the pipeline structure")
    module_instance_id: str = Field(..., description="Module instance ID from pipeline")
    module_ref: str = Field(..., description="Module reference (name:version)")
    module_kind: ModuleKind = Field(..., description="Module type")
    module_config: Dict[str, Any] = Field(..., description="Module configuration")
    input_field_mappings: Dict[str, str] = Field(..., description="Maps input pin IDs to source node IDs")
    output_display_names: Dict[str, str] = Field(default_factory=dict, description="Display names for outputs")
    step_number: int = Field(..., description="Execution order (topological layer)")

    class Config:
        from_attributes = True


class PipelineStepCreate(PipelineStepBase):
    """Model for creating new pipeline step"""

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump()
        # Convert dicts to JSON strings for database storage
        data['module_config'] = json.dumps(data['module_config'])
        data['input_field_mappings'] = json.dumps(data['input_field_mappings'])
        data['output_display_names'] = json.dumps(data['output_display_names'])
        return data

    class Config:
        from_attributes = True


class PipelineStep(PipelineStepBase):
    """Full pipeline step model retrieved from database"""
    id: int = Field(..., description="Step ID (auto-increment)")

    @classmethod
    def from_db_model(cls, db_model) -> "PipelineStep":
        """
        Convert SQLAlchemy model to Pydantic model

        Args:
            db_model: PipelineStepModel instance from database

        Returns:
            PipelineStep Pydantic model
        """
        # Parse JSON fields back to Python objects
        module_config_data = json.loads(db_model.module_config) if isinstance(db_model.module_config, str) else db_model.module_config
        input_mappings_data = json.loads(db_model.input_field_mappings) if isinstance(db_model.input_field_mappings, str) else db_model.input_field_mappings
        output_names_data = json.loads(db_model.output_display_names) if isinstance(db_model.output_display_names, str) else db_model.output_display_names or {}

        return cls(
            id=db_model.id,
            plan_checksum=db_model.plan_checksum,
            module_instance_id=db_model.module_instance_id,
            module_ref=db_model.module_ref,
            module_kind=db_model.module_kind,
            module_config=module_config_data,
            input_field_mappings=input_mappings_data,
            output_display_names=output_names_data,
            step_number=db_model.step_number
        )

    class Config:
        from_attributes = True