from typing import List
from pydantic import BaseModel

from shared.models.pipeline import Pipeline, PipelineCreate, PipelineSummary, PipelineState


class PipelineListResponse(BaseModel):
    """Response model for pipeline listing"""
    pipelines: List[Pipeline]
    total_count: int


class PipelineSummaryListResponse(BaseModel):
    """Response model for pipeline summary listing"""
    pipelines: List[PipelineSummary]
    total_count: int


class ValidatePipelineRequest(BaseModel):
    """Request model for pipeline validation"""
    pipeline_json: PipelineState


class TestUploadResponse(BaseModel):
    """Response model for test upload"""
    success: bool
    message: str
