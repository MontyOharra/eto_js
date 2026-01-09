"""
PDF Template Types
Domain types for template management, versioning, and wizard data
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .pdf_files import PdfObjects
from .pipelines import PipelineState
from .pipeline_execution import PipelineExecutionResult


# =========================
# Status Type
# =========================

PdfTemplateStatus = Literal["active", "inactive"]


class ExtractionField(BaseModel):
    """
    Field definition for data extraction from PDF.

    Note: page is 1-indexed (page 1 = first page)
    """
    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    bbox: tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int  # 1-indexed


# ========== Template Version Types ==========

class PdfTemplateVersion(BaseModel):
    """
    Immutable version snapshot of template wizard data.

    Stores complete wizard configuration (signature objects, extraction fields,
    pipeline reference) at a specific point in time. Once created, versions
    never change.

    signature_objects is a PdfObjects instance - a subset of the objects
    extracted from source_pdf_id, containing only the objects selected for matching.

    pipeline_definition_id is nullable for autoskip templates (no pipeline needed).
    """
    model_config = ConfigDict(frozen=True)

    id: int
    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: PdfObjects  # Subset of extracted PDF objects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int | None  # Nullable for autoskip templates
    created_at: datetime


class PdfTemplateVersionCreate(BaseModel):
    """
    Data needed to create new template version.
    Used by create_template and update_template service methods.

    signature_objects is a PdfObjects instance - a subset of the objects
    extracted from source_pdf_id, containing only the objects selected for matching.

    pipeline_definition_id is nullable for autoskip templates (no pipeline needed).
    """
    model_config = ConfigDict(frozen=True)

    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: PdfObjects  # Subset of extracted PDF objects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int | None  # Nullable for autoskip templates


class PdfTemplateVersionSummary(BaseModel):
    """
    Lightweight version info for history/list views.
    Used by list_versions service method.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    version_number: int
    created_at: datetime
    is_current: bool


# ========== Template Metadata Types ==========

class PdfTemplate(BaseModel):
    """
    Complete template metadata (database record).

    Points to current version via current_version_id. Template status
    controls whether template is used for ETO matching.

    is_autoskip: If True, pages matching this template are automatically
    skipped during ETO processing (useful for cover pages, safety forms, etc.)
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None = None
    customer_id: int | None = None  # References external Access DB
    status: PdfTemplateStatus
    is_autoskip: bool
    source_pdf_id: int
    current_version_id: int | None = None
    created_at: datetime
    updated_at: datetime


class PdfTemplateListView(BaseModel):
    """
    Template list view with version info for list endpoints.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None = None
    customer_id: int | None = None  # References external Access DB
    status: PdfTemplateStatus
    is_autoskip: bool
    source_pdf_id: int
    current_version_id: int | None = None
    current_version_number: int | None = None
    version_usage_count: int | None = None
    version_count: int | None = None
    updated_at: datetime


# ========== Template CRUD Types ==========

class PdfTemplateCreate(BaseModel):
    """
    Data needed to create new template + initial version.

    Used by create_template service method. Creates both template
    record and version 1 atomically.

    signature_objects is a PdfObjects instance - a subset of the objects
    extracted from source_pdf_id, containing only the objects selected for matching.

    pipeline_state and visual_state are the wizard Step 3 data, which the service
    will use to create a new pipeline_definition record.

    is_autoskip: If True, pages matching this template are automatically
    skipped during ETO processing (useful for cover pages, safety forms, etc.)
    """
    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    customer_id: int | None = None  # References external Access DB
    signature_objects: PdfObjects  # Subset of extracted PDF objects
    extraction_fields: list[ExtractionField]
    pipeline_state: PipelineState  # Pipeline graph structure from wizard
    visual_state: dict[str, Any]  # Node positions from wizard
    source_pdf_id: int
    is_autoskip: bool = False  # Default to normal processing


class PdfTemplateUpdate(BaseModel):
    """
    Unified update data for templates - all possible fields in one place.

    SMART UPDATE LOGIC:
    - If ONLY name/description/customer_id/is_autoskip change: Update template metadata only (no new version)
    - If signature_objects, extraction_fields, OR pipeline fields change: Create new version
    - If pipeline fields specifically included: Run full validation/compilation/creation

    All wizard data fields (signature_objects, extraction_fields, pipeline_state, visual_state)
    trigger version creation when provided.
    """
    model_config = ConfigDict(frozen=True)

    # Template metadata fields (can update without version)
    name: str | None = None
    description: str | None = None
    customer_id: int | None = None  # References external Access DB
    is_autoskip: bool | None = None  # Update autoskip without new version

    # Wizard data fields (trigger version creation)
    signature_objects: PdfObjects | None = None
    extraction_fields: list[ExtractionField] | None = None
    pipeline_state: PipelineState | None = None  # Pipeline graph structure
    visual_state: dict[str, Any] | None = None  # Node positions


# ========== Template Simulation Types ==========

class TemplateSimulateData(BaseModel):
    """
    Data for template simulation (testing/preview).

    Used by simulate endpoint to test extraction and pipeline execution
    without persistence.
    """
    model_config = ConfigDict(frozen=True)

    pdf_objects: PdfObjects
    extraction_fields: list[ExtractionField]
    pipeline_state: PipelineState


class TemplateSimulateResult(BaseModel):
    """
    Result of template simulation.

    Contains extraction results, extracted data, and pipeline execution result.
    """
    model_config = ConfigDict(frozen=True)

    extraction_fields: list[ExtractionField]
    extracted_data: dict[str, str]
    execution_result: PipelineExecutionResult


# ========== Multi-Template Matching Types ==========

class TemplateMatch(BaseModel):
    """
    Single template match for a consecutive page range.

    Represents pages that matched a specific template version.
    matched_pages is always consecutive (e.g., [1, 2, 3] or [5, 6]).
    """
    model_config = ConfigDict(frozen=True)

    template_id: int
    version_id: int
    matched_pages: list[int]  # Consecutive pages, 1-indexed


class TemplateMatchingResult(BaseModel):
    """
    Complete multi-template matching result for entire PDF.

    Contains all matched template ranges and any unmatched pages.
    Used to create EtoSubRuns after template matching stage.

    matches: Ordered by page appearance (first match has lowest page numbers)
    unmatched_pages: All pages that didn't match any template (can be non-consecutive)
    """
    model_config = ConfigDict(frozen=True)

    matches: list[TemplateMatch]
    unmatched_pages: list[int]  # Can be non-consecutive, 1-indexed
