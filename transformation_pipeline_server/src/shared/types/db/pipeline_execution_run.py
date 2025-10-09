"""
Execution domain models
Models for tracking pipeline execution history
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import json

from shared.database.models import PipelineExecutionRunModel

class PipelineExecutionRunBase(BaseModel):
    """Base fields for pipeline execution run"""
    pipeline_definition_id: str = Field(..., description="Pipeline definition ID")
    entry_values: Dict[str, Any] = Field(..., description="Entry values")

class PipelineExecutionRun(PipelineExecutionRunBase):
    """Domain model for execution run"""
    id: int = Field(..., description="Run ID (auto-increment)")
    status: str = Field(..., description="Execution status")

    @classmethod
    def from_db_model(cls, db_model : PipelineExecutionRunModel) -> "PipelineExecutionRun":
        """Convert from SQLAlchemy model"""
        return cls(
            id=db_model.id,
            pipeline_definition_id=db_model.pipeline_definition_id,
            status=db_model.status,
            entry_values=json.loads(db_model.entry_values) if db_model.entry_values else {},
        )


class PipelineExecutionRunCreate(PipelineExecutionRunBase):
    """Model for creating execution run"""

    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        data = self.model_dump()
        data['entry_values'] = json.dumps(data['entry_values'])
        return data
