from typing import List
from pydantic import BaseModel

from shared.types import (
    PipelineDefinition,
    PipelineDefinitionCreate,
    PipelineDefinitionSummary,
    PipelineState,
)


class PipelineListResponse(BaseModel):
    """Response model for pipeline listing"""

    pipelines: List[PipelineDefinition]
    total_count: int


class PipelineSummaryListResponse(BaseModel):
    """Response model for pipeline summary listing"""

    pipelines: List[PipelineDefinitionSummary]
    total_count: int


class ValidatePipelineRequest(BaseModel):
    """Request model for pipeline validation"""

    pipeline_json: PipelineState


class TestUploadResponse(BaseModel):
    """Response model for test upload"""

    success: bool
    message: str
