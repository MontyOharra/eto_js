# API Schema Definitions - Phase 4

## Status: In Progress

**Phase:** Phase 4 - Schema Definitions

---

## Overview

This document defines all Pydantic request and response schemas for the 35 API endpoints. Schemas use plain Python types initially (no custom types) to establish the baseline structure. Common patterns will be refactored into reusable types later.

## Design Principles

1. **Plain types only**: Use `str`, `int`, `bool`, `list`, `dict`, etc. - no custom types yet
2. **Explicit field definitions**: Every field fully specified with type and constraints
3. **Pydantic v2**: Using Pydantic v2 syntax (`Field()`, `ConfigDict`, etc.)
4. **No inheritance initially**: Each schema standalone to see full structure
5. **Validation rules**: All constraints defined (min/max, regex, enums via Literal)
6. **Optional vs Required**: Clear distinction using `Optional[]` and default values

---

## Router 1: `/email-configs` - Email Ingestion Configuration

### Request Schemas

#### `EmailConfigCreateRequest`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class EmailFilterRuleRequest(BaseModel):
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str = Field(..., min_length=1)
    case_sensitive: bool = False

class EmailConfigCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    email_address: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    folder_name: str = Field(..., min_length=1)
    filter_rules: List[EmailFilterRuleRequest] = Field(default_factory=list)
    poll_interval_seconds: int = Field(5, ge=5, le=300)
    max_backlog_hours: int = Field(24, ge=1)
    error_retry_attempts: int = Field(3, ge=1, le=10)
```

#### `EmailConfigUpdateRequest`

```python
class EmailConfigUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    filter_rules: Optional[List[EmailFilterRuleRequest]] = None
    poll_interval_seconds: Optional[int] = Field(None, ge=5, le=300)
    max_backlog_hours: Optional[int] = Field(None, ge=1)
    error_retry_attempts: Optional[int] = Field(None, ge=1, le=10)
```

#### `EmailConfigValidateRequest`

```python
class EmailConfigValidateRequest(BaseModel):
    email_address: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    folder_name: str = Field(..., min_length=1)
```

---

### Response Schemas

#### `EmailConfigSummaryResponse`

```python
class EmailConfigSummaryResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    last_check_time: Optional[str] = None  # ISO 8601 datetime string
```

#### `EmailFilterRuleResponse`

```python
class EmailFilterRuleResponse(BaseModel):
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: bool
```

#### `EmailConfigDetailResponse`

```python
class EmailConfigDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[EmailFilterRuleResponse]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    activated_at: Optional[str] = None  # ISO 8601
    is_running: bool
    last_check_time: Optional[str] = None  # ISO 8601
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None  # ISO 8601
```

#### `EmailAccountResponse`

```python
class EmailAccountResponse(BaseModel):
    email_address: str
    display_name: Optional[str] = None
```

#### `EmailFolderResponse`

```python
class EmailFolderResponse(BaseModel):
    folder_name: str
    folder_path: str
```

#### `EmailConfigValidateResponse`

```python
class EmailConfigValidateResponse(BaseModel):
    email_address: str
    folder_name: str
    message: str
```

---

## Router 2: `/eto-runs` - ETO Processing Control

### Request Schemas

#### `EtoRunsReprocessRequest`

```python
class EtoRunsReprocessRequest(BaseModel):
    run_ids: List[int] = Field(..., min_length=1)
```

#### `EtoRunsSkipRequest`

```python
class EtoRunsSkipRequest(BaseModel):
    run_ids: List[int] = Field(..., min_length=1)
```

#### `EtoRunsDeleteRequest`

```python
class EtoRunsDeleteRequest(BaseModel):
    run_ids: List[int] = Field(..., min_length=1)
```

---

### Response Schemas

#### `EtoRunPdfInfo`

```python
class EtoRunPdfInfo(BaseModel):
    id: int
    original_filename: str
    file_size: Optional[int] = None
```

#### `EtoRunPdfInfoDetailed`

```python
class EtoRunPdfInfoDetailed(BaseModel):
    id: int
    original_filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None  # Included in detail view
```

#### `EtoRunSourceManual`

```python
class EtoRunSourceManual(BaseModel):
    type: Literal["manual"]
```

#### `EtoRunSourceEmail`

```python
class EtoRunSourceEmail(BaseModel):
    type: Literal["email"]
    sender_email: str
    received_date: str  # ISO 8601
    subject: Optional[str] = None
    folder_name: str
```

#### `EtoRunMatchedTemplate`

```python
class EtoRunMatchedTemplate(BaseModel):
    template_id: int
    template_name: str
    version_id: int
    version_num: int
```

#### `EtoRunSummaryResponse`

```python
from typing import Union

class EtoRunSummaryResponse(BaseModel):
    id: int
    status: Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
    processing_step: Optional[Literal["template_matching", "data_extraction", "data_transformation"]] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    pdf: EtoRunPdfInfo
    source: Union[EtoRunSourceManual, EtoRunSourceEmail]
    matched_template: Optional[EtoRunMatchedTemplate] = None
```

#### `EtoRunTemplateMatchingStage`

```python
class EtoRunTemplateMatchingStage(BaseModel):
    status: Literal["not_started", "success", "failure", "skipped"]
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_message: Optional[str] = None
    matched_template: Optional[EtoRunMatchedTemplate] = None
```

#### `EtoRunDataExtractionStage`

```python
from typing import Dict, Any

class EtoRunDataExtractionStage(BaseModel):
    status: Literal["not_started", "success", "failure", "skipped"]
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None  # Dynamic keys based on template
```

#### `EtoRunExecutedAction`

```python
class EtoRunExecutedAction(BaseModel):
    action_module_name: str
    inputs: Dict[str, Any]
```

#### `EtoRunPipelineStepInputOutput`

```python
class EtoRunPipelineStepInputOutput(BaseModel):
    value: Any
    type: str  # e.g., "string", "number", "object"
```

#### `EtoRunPipelineStep`

```python
class EtoRunPipelineStep(BaseModel):
    id: int
    step_number: int
    module_instance_id: str
    inputs: Optional[Dict[str, EtoRunPipelineStepInputOutput]] = None
    outputs: Optional[Dict[str, EtoRunPipelineStepInputOutput]] = None
    error: Optional[Dict[str, Any]] = None
```

#### `EtoRunPipelineExecutionStage`

```python
class EtoRunPipelineExecutionStage(BaseModel):
    status: Literal["not_started", "success", "failure", "skipped"]
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_message: Optional[str] = None
    executed_actions: Optional[List[EtoRunExecutedAction]] = None
    steps: List[EtoRunPipelineStep]
```

#### `EtoRunDetailResponse`

```python
class EtoRunDetailResponse(BaseModel):
    id: int
    status: Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
    processing_step: Optional[Literal["template_matching", "data_extraction", "data_transformation"]] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    pdf: EtoRunPdfInfoDetailed
    source: Union[EtoRunSourceManual, EtoRunSourceEmail]

    template_matching: EtoRunTemplateMatchingStage
    data_extraction: EtoRunDataExtractionStage
    pipeline_execution: EtoRunPipelineExecutionStage
```

#### `EtoRunsListResponse`

```python
class EtoRunsListResponse(BaseModel):
    items: List[EtoRunSummaryResponse]
    total: int
    limit: int
    offset: int
```

#### `EtoRunUploadResponse`

```python
class EtoRunUploadResponse(BaseModel):
    id: int
    pdf_file_id: int
    status: Literal["not_started"]
    processing_step: None = None
    started_at: None = None
    completed_at: None = None
```

---

## Router 3: `/pdf-files` - PDF File Access

### Response Schemas

#### `PdfFileMetadataResponse`

```python
class PdfFileMetadataResponse(BaseModel):
    id: int
    email_id: Optional[int] = None
    filename: str
    original_filename: str
    relative_path: str
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    page_count: Optional[int] = None
```

#### `PdfTextWordObject`

```python
class PdfTextWordObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    text: str
    fontname: str
    fontsize: float
```

#### `PdfTextLineObject`

```python
class PdfTextLineObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
```

#### `PdfGraphicRectObject`

```python
class PdfGraphicRectObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    linewidth: float
```

#### `PdfGraphicLineObject`

```python
class PdfGraphicLineObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    linewidth: float
```

#### `PdfGraphicCurveObject`

```python
class PdfGraphicCurveObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    points: List[List[float]]  # Array of [x, y] coordinate pairs
    linewidth: float
```

#### `PdfImageObject`

```python
class PdfImageObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    format: str  # e.g., "JPEG", "PNG"
    colorspace: str  # e.g., "RGB", "CMYK"
    bits: int
```

#### `PdfTableObject`

```python
class PdfTableObject(BaseModel):
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    rows: int
    cols: int
```

#### `PdfObjectsResponse`

```python
class PdfObjectsResponse(BaseModel):
    pdf_file_id: int
    page_count: int
    objects: Dict[str, List[Any]]  # Will be more specific below

    # More specific typing:
    # objects: {
    #     "text_words": List[PdfTextWordObject],
    #     "text_lines": List[PdfTextLineObject],
    #     "graphic_rects": List[PdfGraphicRectObject],
    #     "graphic_lines": List[PdfGraphicLineObject],
    #     "graphic_curves": List[PdfGraphicCurveObject],
    #     "images": List[PdfImageObject],
    #     "tables": List[PdfTableObject]
    # }
```

**Note:** The `objects` field uses a dict structure. Here's the detailed version:

```python
class PdfObjectsGrouped(BaseModel):
    text_words: List[PdfTextWordObject]
    text_lines: List[PdfTextLineObject]
    graphic_rects: List[PdfGraphicRectObject]
    graphic_lines: List[PdfGraphicLineObject]
    graphic_curves: List[PdfGraphicCurveObject]
    images: List[PdfImageObject]
    tables: List[PdfTableObject]

class PdfObjectsResponse(BaseModel):
    pdf_file_id: int
    page_count: int
    objects: PdfObjectsGrouped
```

---

## Router 4: `/pdf-templates` - PDF Template Management

### Request Schemas

#### `SignatureObjectRequest`

```python
class SignatureObjectRequest(BaseModel):
    object_type: Literal["text_word", "text_line", "graphic_rect", "graphic_line", "graphic_curve", "image", "table"]
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    # Additional properties would go here (varies by object_type)
    # Using Dict[str, Any] for flexibility initially
```

**Note:** Signature objects should match the structure from PDF extraction. For now using flexible dict.

#### `ExtractionFieldRequest`

```python
class ExtractionFieldRequest(BaseModel):
    field_id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    description: Optional[str] = None
    page: int = Field(..., ge=1)
    bbox: List[float] = Field(..., min_length=4, max_length=4)  # [x0, y0, x1, y1]
    required: bool = False
    validation_regex: Optional[str] = None
```

#### `PipelineEntryPointRequest`

```python
class PipelineEntryPointRequest(BaseModel):
    id: str
    label: str
    field_reference: str
```

#### `PipelineNodeRequest`

```python
class PipelineNodeRequest(BaseModel):
    node_id: str
    name: str
    type: List[str]
```

#### `PipelineModuleRequest`

```python
class PipelineModuleRequest(BaseModel):
    instance_id: str
    module_id: str
    config: Dict[str, Any]
    inputs: List[PipelineNodeRequest]
    outputs: List[PipelineNodeRequest]
```

#### `PipelineConnectionRequest`

```python
class PipelineConnectionRequest(BaseModel):
    from_node_id: str
    to_node_id: str
```

#### `PipelineStateRequest`

```python
class PipelineStateRequest(BaseModel):
    entry_points: List[PipelineEntryPointRequest]
    modules: List[PipelineModuleRequest]
    connections: List[PipelineConnectionRequest]
```

#### `PipelineVisualStateRequest`

```python
class PipelinePositionRequest(BaseModel):
    x: float
    y: float

class PipelineVisualStateRequest(BaseModel):
    positions: Dict[str, PipelinePositionRequest]  # entry_point_id or module_instance_id -> position
```

#### `TemplateCreateRequest`

```python
class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: int

    signature_objects: List[Dict[str, Any]] = Field(..., min_length=1)  # Flexible for different object types
    extraction_fields: List[ExtractionFieldRequest] = Field(..., min_length=1)
    pipeline_state: PipelineStateRequest
    visual_state: PipelineVisualStateRequest
```

#### `TemplateUpdateRequest`

```python
class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    signature_objects: List[Dict[str, Any]] = Field(..., min_length=1)
    extraction_fields: List[ExtractionFieldRequest] = Field(..., min_length=1)
    pipeline_state: PipelineStateRequest
    visual_state: PipelineVisualStateRequest
```

#### `TemplateSimulateRequest`

```python
class TemplateSimulateRequest(BaseModel):
    pdf_file_id: int
    signature_objects: List[Dict[str, Any]] = Field(..., min_length=1)
    extraction_fields: List[ExtractionFieldRequest] = Field(..., min_length=1)
    pipeline_state: PipelineStateRequest
```

---

### Response Schemas

#### `TemplateCurrentVersionSummary`

```python
class TemplateCurrentVersionSummary(BaseModel):
    version_id: int
    version_num: int
    usage_count: int
```

#### `TemplateSummaryResponse`

```python
class TemplateSummaryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: Literal["draft", "active", "inactive"]
    source_pdf_id: int
    current_version: TemplateCurrentVersionSummary
    total_versions: int
```

#### `TemplatesListResponse`

```python
class TemplatesListResponse(BaseModel):
    items: List[TemplateSummaryResponse]
    total: int
    limit: int
    offset: int
```

#### `ExtractionFieldResponse`

```python
class ExtractionFieldResponse(BaseModel):
    field_id: str
    label: str
    description: Optional[str] = None
    page: int
    bbox: List[float]  # [x0, y0, x1, y1]
    required: bool
    validation_regex: Optional[str] = None
```

#### `TemplateVersionDetail`

```python
class TemplateVersionDetail(BaseModel):
    version_id: int
    version_num: int
    usage_count: int
    last_used_at: Optional[str] = None  # ISO 8601
    signature_objects: List[Dict[str, Any]]  # Flexible structure matching PDF objects
    extraction_fields: List[ExtractionFieldResponse]
    pipeline_definition_id: int
```

#### `TemplateDetailResponse`

```python
class TemplateDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    source_pdf_id: int
    status: Literal["draft", "active", "inactive"]
    current_version_id: int
    current_version: TemplateVersionDetail
    total_versions: int
```

#### `TemplateCreateResponse`

```python
class TemplateCreateResponse(BaseModel):
    id: int
    name: str
    status: Literal["draft"]
    current_version_id: int
    current_version_num: int
    pipeline_definition_id: int
```

#### `TemplateUpdateResponse`

```python
class TemplateUpdateResponse(BaseModel):
    id: int
    name: str
    status: Literal["draft", "active", "inactive"]
    current_version_id: int
    current_version_num: int
    pipeline_definition_id: int
```

#### `TemplateActivationResponse`

```python
class TemplateActivationResponse(BaseModel):
    id: int
    status: Literal["active"]
    current_version_id: int
```

#### `TemplateDeactivationResponse`

```python
class TemplateDeactivationResponse(BaseModel):
    id: int
    status: Literal["inactive"]
    current_version_id: int
```

#### `TemplateVersionSummary`

```python
class TemplateVersionSummary(BaseModel):
    version_id: int
    version_num: int
    usage_count: int
    last_used_at: Optional[str] = None  # ISO 8601
    is_current: bool
```

#### `TemplateVersionDetailResponse`

```python
class TemplateVersionDetailResponse(BaseModel):
    version_id: int
    template_id: int
    version_num: int
    usage_count: int
    last_used_at: Optional[str] = None  # ISO 8601
    is_current: bool
    signature_objects: List[Dict[str, Any]]
    extraction_fields: List[ExtractionFieldResponse]
    pipeline_definition_id: int
```

#### `TemplateSimulationValidationResult`

```python
class TemplateSimulationValidationResult(BaseModel):
    field_label: str
    required: bool
    has_value: bool
    regex_valid: Optional[bool] = None  # null if no regex
    error: Optional[str] = None
```

#### `TemplateSimulationTemplateMatching`

```python
class TemplateSimulationTemplateMatching(BaseModel):
    status: Literal["success"]
    message: str = "Simulation mode - template matching skipped"
```

#### `TemplateSimulationDataExtraction`

```python
class TemplateSimulationDataExtraction(BaseModel):
    status: Literal["success", "failure"]
    extracted_data: Optional[Dict[str, str]] = None  # field_label -> extracted text
    error_message: Optional[str] = None
    validation_results: List[TemplateSimulationValidationResult]
```

#### `TemplateSimulationPipelineStep`

```python
class TemplateSimulationPipelineStep(BaseModel):
    step_number: int
    module_instance_id: str
    module_name: str
    inputs: Dict[str, Dict[str, Any]]  # node_name -> {value, type}
    outputs: Dict[str, Dict[str, Any]]  # node_name -> {value, type}
    error: Optional[Dict[str, Any]] = None
```

#### `TemplateSimulationAction`

```python
class TemplateSimulationAction(BaseModel):
    action_module_name: str
    inputs: Dict[str, Any]
    simulation_note: str = "Action not executed - simulation mode"
```

#### `TemplateSimulationPipelineExecution`

```python
class TemplateSimulationPipelineExecution(BaseModel):
    status: Literal["success", "failure"]
    error_message: Optional[str] = None
    steps: List[TemplateSimulationPipelineStep]
    simulated_actions: List[TemplateSimulationAction]
```

#### `TemplateSimulateResponse`

```python
class TemplateSimulateResponse(BaseModel):
    template_matching: TemplateSimulationTemplateMatching
    data_extraction: TemplateSimulationDataExtraction
    pipeline_execution: TemplateSimulationPipelineExecution
```

---

## Router 5: `/modules` - Module Catalog Viewing

### Response Schemas

#### `ModuleInputNode`

```python
class ModuleInputNode(BaseModel):
    id: str
    name: str
    type: List[str]  # Allowed types
    required: bool
    description: str
```

#### `ModuleOutputNode`

```python
class ModuleOutputNode(BaseModel):
    id: str
    name: str
    type: List[str]  # Output types
    description: str
```

#### `ModuleMeta`

```python
class ModuleMeta(BaseModel):
    inputs: List[ModuleInputNode]
    outputs: List[ModuleOutputNode]
    # Future: additional metadata fields
```

#### `ModuleResponse`

```python
class ModuleResponse(BaseModel):
    id: str
    version: str
    name: str
    description: str
    color: str  # Hex color code
    category: str
    module_kind: Literal["transform", "action", "logic", "entry_point"]
    meta: ModuleMeta
    config_schema: Dict[str, Any]  # JSON Schema for dynamic form generation
```

---

## Router 6: `/pipelines` - Pipeline Management (Dev/Testing)

### Request Schemas

#### `PipelineCreateRequest`

```python
class PipelineCreateRequest(BaseModel):
    pipeline_state: PipelineStateRequest
    visual_state: PipelineVisualStateRequest
```

#### `PipelineUpdateRequest`

```python
class PipelineUpdateRequest(BaseModel):
    pipeline_state: PipelineStateRequest
    visual_state: PipelineVisualStateRequest
```

---

### Response Schemas

#### `PipelineSummaryResponse`

```python
class PipelineSummaryResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None
    created_at: str  # ISO 8601 (included for dev convenience)
    updated_at: str  # ISO 8601 (included for dev convenience)
```

#### `PipelinesListResponse`

```python
class PipelinesListResponse(BaseModel):
    items: List[PipelineSummaryResponse]
    total: int
    limit: int
    offset: int
```

#### `PipelineEntryPointResponse`

```python
class PipelineEntryPointResponse(BaseModel):
    id: str
    label: str
    field_reference: str
```

#### `PipelineNodeResponse`

```python
class PipelineNodeResponse(BaseModel):
    node_id: str
    name: str
    type: List[str]
```

#### `PipelineModuleResponse`

```python
class PipelineModuleResponse(BaseModel):
    instance_id: str
    module_id: str
    config: Dict[str, Any]
    inputs: List[PipelineNodeResponse]
    outputs: List[PipelineNodeResponse]
```

#### `PipelineConnectionResponse`

```python
class PipelineConnectionResponse(BaseModel):
    from_node_id: str
    to_node_id: str
```

#### `PipelineStateResponse`

```python
class PipelineStateResponse(BaseModel):
    entry_points: List[PipelineEntryPointResponse]
    modules: List[PipelineModuleResponse]
    connections: List[PipelineConnectionResponse]
```

#### `PipelinePositionResponse`

```python
class PipelinePositionResponse(BaseModel):
    x: float
    y: float
```

#### `PipelineVisualStateResponse`

```python
class PipelineVisualStateResponse(BaseModel):
    positions: Dict[str, PipelinePositionResponse]
```

#### `PipelineDetailResponse`

```python
class PipelineDetailResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None
    pipeline_state: PipelineStateResponse
    visual_state: PipelineVisualStateResponse
```

#### `PipelineCreateResponse`

```python
class PipelineCreateResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None
```

#### `PipelineUpdateResponse`

```python
class PipelineUpdateResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None
```

---

## Router 7: `/health` - System Health Monitoring

### Response Schemas

#### `HealthServiceStatus`

```python
class HealthServiceStatus(BaseModel):
    status: Literal["healthy", "unhealthy"]
    message: Optional[str] = None  # Optional error message if unhealthy
```

#### `HealthServerStatus`

```python
class HealthServerStatus(BaseModel):
    status: Literal["up"]  # If server responds, always "up"
```

#### `HealthResponse`

```python
class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    server: HealthServerStatus
    services: Dict[str, HealthServiceStatus]  # service_name -> status

    # Example services:
    # {
    #     "email_ingestion": HealthServiceStatus(...),
    #     "eto_processing": HealthServiceStatus(...),
    #     "pdf_processing": HealthServiceStatus(...),
    #     "database": HealthServiceStatus(...)
    # }
```

---

## Summary

**Total Schemas Defined:**
- **Request Schemas**: ~25 schemas
- **Response Schemas**: ~70 schemas
- **Supporting/Nested Schemas**: ~30 schemas

**Total**: ~125 Pydantic models covering all 35 endpoints

**Next Steps:**
1. Review schemas for consistency
2. Identify common patterns for refactoring into reusable types
3. Add validation examples and edge cases
4. Create mapper functions between API schemas and DTOs

---
