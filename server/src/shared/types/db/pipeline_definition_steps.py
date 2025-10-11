"""
Strongly-typed pipeline domain models
These models define the structure of transformation pipelines following CRUD patterns
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import json

from shared.database.models import PipelineDefinitionStepModel

from ..modules import ModuleKind
from ..pipeline_state import InstanceNodePin

class PipelineDefinitionStepBase(BaseModel):
    """Base fields for a compiled pipeline step"""
    plan_checksum: str = Field(..., description="SHA-256 checksum of the pipeline structure")
    module_instance_id: str = Field(..., description="Module instance ID from pipeline")
    module_ref: str = Field(..., description="Module reference (name:version)")
    module_kind: ModuleKind = Field(..., description="Module type")
    module_config: Dict[str, Any] = Field(..., description="Module configuration")
    input_field_mappings: Dict[str, str] = Field(..., description="Maps input pin IDs to source node IDs")
    node_metadata: Dict[str, List[InstanceNodePin]] = Field(None, description="Node metadata with input/output pin information")
    step_number: int = Field(..., description="Execution order (topological layer)")

    class Config:
        from_attributes = True


class PipelineDefinitionStepCreate(PipelineDefinitionStepBase):
    """Model for creating new pipeline step"""

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump()
        # Convert dicts to JSON strings for database storage
        data['module_config'] = json.dumps(data['module_config'])
        data['input_field_mappings'] = json.dumps(data['input_field_mappings'])


        metadata_dict = {}
        for key, pins in data['node_metadata'].items():
            # Handle both InstanceNodePin objects and dicts
            if pins and len(pins) > 0:
                if hasattr(pins[0], 'model_dump'):
                    # pins are InstanceNodePin objects
                    metadata_dict[key] = [pin.model_dump() for pin in pins]
                else:
                    # pins are already dicts
                    metadata_dict[key] = pins
            else:
                metadata_dict[key] = []

        data['node_metadata'] = json.dumps(metadata_dict)

        return data

    class Config:
        from_attributes = True


class PipelineDefinitionStep(PipelineDefinitionStepBase):
    """Full pipeline step model retrieved from database"""
    id: int = Field(..., description="Step ID (auto-increment)")

    @classmethod
    def from_db_model(cls, db_model : PipelineDefinitionStepModel) -> "PipelineDefinitionStep":
        """
        Convert SQLAlchemy model to Pydantic model

        Args:
            db_model: PipelineStepModel instance from database

        Returns:
            PipelineStep Pydantic model
        """
        # Parse JSON fields back to Python objects
        module_config_data = json.loads(db_model.module_config)
        input_mappings_data = json.loads(db_model.input_field_mappings)

        node_metadata = {
            str(key): [InstanceNodePin(**pin) for pin in pins]
            for key, pins in json.loads(db_model.node_metadata).items()
        }

        return cls(
            id=db_model.id,
            plan_checksum=db_model.plan_checksum,
            module_instance_id=db_model.module_instance_id,
            module_ref=db_model.module_ref,
            module_kind=db_model.module_kind,  # type: ignore
            module_config=module_config_data,
            input_field_mappings=input_mappings_data,
            node_metadata=node_metadata,
            step_number=db_model.step_number
        )

    class Config:
        from_attributes = True