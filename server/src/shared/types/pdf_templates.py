"""
PDF Template Types
Dataclasses for template management, versioning, and wizard data
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Any

# Import PDF object types - signature objects are just a subset of extracted objects
from .pdf_files import PdfObjects
from .pipelines import PipelineState
from .pipeline_execution import PipelineExecutionResult

@dataclass(frozen=True)
class ExtractionField:
    """
    Field definition for data extraction from PDF.

    Domain model for extraction fields - simple structure for storage.
    API layer has matching ExtractionField Pydantic model with same structure.

    Note: page is 1-indexed (page 1 = first page)
    """
    name: str
    description: str | None
    bbox: tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int  # 1-indexed


# ========== Template Version Dataclasses ==========

@dataclass(frozen=True)
class PdfTemplateVersion:
    """
    Immutable version snapshot of template wizard data.

    Stores complete wizard configuration (signature objects, extraction fields,
    pipeline reference) at a specific point in time. Once created, versions
    never change.

    signature_objects is a PdfObjects instance - a subset of the objects
    extracted from source_pdf_id, containing only the objects selected for matching.
    """
    id: int
    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: PdfObjects  # Subset of extracted PDF objects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int
    created_at: datetime


@dataclass(frozen=True)
class PdfVersionCreate:
    """
    Data needed to create new template version.
    Used by create_template and update_template service methods.

    signature_objects is a PdfObjects instance - a subset of the objects
    extracted from source_pdf_id, containing only the objects selected for matching.
    """
    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: PdfObjects  # Subset of extracted PDF objects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int


@dataclass(frozen=True)
class PdfVersionSummary:
    """
    Lightweight version info for history/list views.
    Used by list_versions service method.
    """
    id: int
    version_number: int
    created_at: datetime
    is_current: bool


# ========== Template Metadata Dataclasses ==========

@dataclass(frozen=True)
class PdfTemplate:
    """
    Complete template metadata (database record).

    Points to current version via current_version_id. Template status
    controls whether template is used for ETO matching.
    """
    id: int
    name: str
    description: str | None
    status: str
    source_pdf_id: int
    current_version_id: int | None
    created_at: datetime
    updated_at: datetime
    
    
@dataclass(frozen=True)
class PdfTemplateListView:
    id: int
    name: str
    description: str | None
    status: str
    source_pdf_id: int
    current_version_id: int | None
    current_version_number: int | None
    version_usage_count: int | None
    version_count: int | None
    updated_at: datetime
        
        
# ========== Template CRUD Dataclasses ==========

@dataclass(frozen=True)
class PdfTemplateCreate:
    """
    Data needed to create new template + initial version.

    Used by create_template service method. Creates both template
    record and version 1 atomically.

    signature_objects is a PdfObjects instance - a subset of the objects
    extracted from source_pdf_id, containing only the objects selected for matching.

    pipeline_state and visual_state are the wizard Step 3 data, which the service
    will use to create a new pipeline_definition record.
    """
    name: str
    description: str | None
    signature_objects: PdfObjects  # Subset of extracted PDF objects
    extraction_fields: list[ExtractionField]
    pipeline_state: dict[str, Any]  # Pipeline graph structure from wizard
    visual_state: dict[str, Any]  # Node positions from wizard
    source_pdf_id: int


@dataclass(frozen=True)
class PdfTemplateUpdate:
    """
    Unified update data for templates - all possible fields in one place.

    SMART UPDATE LOGIC:
    - If ONLY name/description change: Update template metadata only (no new version)
    - If signature_objects, extraction_fields, OR pipeline fields change: Create new version
    - If pipeline fields specifically included: Run full validation/compilation/creation

    All wizard data fields (signature_objects, extraction_fields, pipeline_state, visual_state)
    trigger version creation when provided.
    """
    # Template metadata fields (can update without version)
    name: str | None = None
    description: str | None = None

    # Wizard data fields (trigger version creation)
    signature_objects: PdfObjects | None = None
    extraction_fields: list[ExtractionField] | None = None
    pipeline_state: dict[str, Any] | None = None  # Pipeline graph structure
    visual_state: dict[str, Any] | None = None  # Node positions


# ========== Template Simulation Dataclasses ==========

@dataclass(frozen=True)
class TemplateSimulateData:
    """
    Data for template simulation (testing/preview).

    Used by simulate endpoint to test extraction and pipeline execution
    without persistence.
    """
    pdf_objects: PdfObjects
    extraction_fields: list[ExtractionField]
    pipeline_state: PipelineState


@dataclass(frozen=True)
class TemplateSimulateResult:
    """
    Result of template simulation.

    Contains extraction results, extracted data, and pipeline execution result.
    """
    extraction_fields: list[ExtractionField]
    extracted_data: dict[str, str]
    execution_result: PipelineExecutionResult