from typing import List
from pydantic import BaseModel, Field

from shared.exceptions import PipelineValidationError

class PipelineValidationResult(BaseModel):
    """Result of pipeline validation"""
    valid: bool
    errors: List[PipelineValidationError] = Field(default_factory=list)
