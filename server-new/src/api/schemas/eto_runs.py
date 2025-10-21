"""
ETO Runs API Schemas
Pydantic models for ETO processing endpoints
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# GET /eto-runs - List Response
class EtoRunPdfInfo(BaseModel):
    id: int
    original_filename: str
    file_size: Optional[int] = None


class EtoRunSourceInfo(BaseModel):
    type: Literal["manual", "email"]
    sender_email: Optional[str] = None
    received_date: Optional[str] = None  # ISO 8601
    subject: Optional[str] = None
    folder_name: Optional[str] = None


class EtoRunMatchedTemplate(BaseModel):
    template_id: int
    template_name: str
    version_id: int
    version_num: int


class EtoRunListItem(BaseModel):
    id: int
    status: Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
    processing_step: Optional[Literal["template_matching", "data_extraction", "data_transformation"]] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    pdf: EtoRunPdfInfo
    source: EtoRunSourceInfo
    matched_template: Optional[EtoRunMatchedTemplate] = None


class ListEtoRunsResponse(BaseModel):
    items: List[EtoRunListItem]
    total: int
    limit: int
    offset: int


# GET /eto-runs/{id} - Detail Response
class EtoRunPdfInfoDetail(BaseModel):
    id: int
    original_filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None


class EtoRunTemplateMatchingStage(BaseModel):
    status: Literal["not_started", "success", "failure", "skipped"]
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_message: Optional[str] = None
    matched_template: Optional[EtoRunMatchedTemplate] = None


class EtoRunDataExtractionStage(BaseModel):
    status: Literal["not_started", "success", "failure", "skipped"]
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


class PipelineStepPinValue(BaseModel):
    name: str
    value: Any
    type: str


class PipelineStepError(BaseModel):
    type: str
    message: str
    details: Optional[Any] = None


class PipelineExecutionStep(BaseModel):
    id: int
    step_number: int
    module_instance_id: str
    inputs: Optional[Dict[str, PipelineStepPinValue]] = None
    outputs: Optional[Dict[str, PipelineStepPinValue]] = None
    error: Optional[PipelineStepError] = None


class ExecutedAction(BaseModel):
    action_module_name: str
    inputs: Dict[str, Any]


class EtoRunPipelineExecutionStage(BaseModel):
    status: Literal["not_started", "success", "failure", "skipped"]
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_message: Optional[str] = None
    pipeline_definition_id: int
    executed_actions: Optional[List[ExecutedAction]] = None
    steps: List[PipelineExecutionStep]


class EtoRunDetail(BaseModel):
    id: int
    status: Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
    processing_step: Optional[Literal["template_matching", "data_extraction", "data_transformation"]] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    pdf: EtoRunPdfInfoDetail
    source: EtoRunSourceInfo
    template_matching: EtoRunTemplateMatchingStage
    data_extraction: EtoRunDataExtractionStage
    pipeline_execution: EtoRunPipelineExecutionStage


# POST /eto-runs/upload - Upload Response
class UploadPdfForProcessingResponse(BaseModel):
    id: int
    pdf_file_id: int
    status: Literal["not_started"]
    processing_step: None = None
    started_at: None = None
    completed_at: None = None


# POST /eto-runs/reprocess - Bulk Reprocess Request
class BulkReprocessRequest(BaseModel):
    run_ids: List[int]


# POST /eto-runs/skip - Bulk Skip Request
class BulkSkipRequest(BaseModel):
    run_ids: List[int]


# DELETE /eto-runs - Bulk Delete Request
class BulkDeleteRequest(BaseModel):
    run_ids: List[int]
