"""
Execution domain models
Models for tracking pipeline execution step history
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import json

from shared.database.models import PipelineExecutionStepModel

class PipelineExecutionStepBase(BaseModel):
    """Domain model for execution step"""
    run_id: int = Field(..., description="Run ID")
    module_instance_id: str = Field(..., description="Module instance ID")
    step_number: int = Field(..., description="Step number")
    inputs: Dict[str, Any] = Field(..., description="Input values")
    outputs: Dict[str, Any] = Field(..., description="Output values")
    error: Optional[str] = Field(None, description="Error message")
    
    
class PipelineExecutionStepCreate(PipelineExecutionStepBase):
    """Model for creating execution step"""

    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        data = self.model_dump()
        data['inputs'] = json.dumps(data['inputs'])
        data['outputs'] = json.dumps(data['outputs'])
        return data
    
    
class PipelineExecutionStep(PipelineExecutionStepBase):
    """Domain model for execution step"""
    id: int = Field(..., description="Step ID (auto-increment)")

    @classmethod
    def from_db_model(cls, db_model : PipelineExecutionStepModel) -> "PipelineExecutionStep":
        """Convert from SQLAlchemy model"""
        return cls(
            id=db_model.id,
            run_id=db_model.run_id,
            module_instance_id=db_model.module_instance_id,
            step_number=db_model.step_number,
            inputs=json.loads(db_model.inputs) if db_model.inputs else {},
            outputs=json.loads(db_model.outputs) if db_model.outputs else {},
            error=db_model.error,
        )