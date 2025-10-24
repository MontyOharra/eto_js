"""
PDF Templates FastAPI Router
REST endpoints for PDF template creation, management, and versioning
"""
import logging
from typing import Optional, Union, Literal
from fastapi import APIRouter, Query, status, Depends

from api.schemas.pdf_templates import (
    ListPdfTemplatesResponse,
    CreatePdfTemplateRequest,
    CreatePdfTemplateResponse,
    UpdatePdfTemplateRequest,
    UpdatePdfTemplateResponse,
    PdfTemplateDetail,
    ActivatePdfTemplateResponse,
    DeactivatePdfTemplateResponse,
    GetTemplateVersionResponse,
    SimulateTemplateResponse,
    SimulateTemplateRequestStored,
    SimulateTemplateRequestUpload,
)
from api.mappers.pdf_templates import (
    convert_template_summary_list,
    convert_template_detail,
    convert_create_template_request,
    convert_create_template_response,
    convert_update_template_request,
    convert_update_template_response,
    convert_activate_template_response,
    convert_deactivate_template_response,
    convert_template_version,
)

from shared.services.service_container import ServiceContainer
from features.pdf_templates import PdfTemplateService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pdf-templates",
    tags=["PDF Templates"]
)


@router.get("", response_model=ListPdfTemplatesResponse)
def list_pdf_templates(
    status_filter: Optional[Literal["active", "inactive"]] = Query(None, description="Filter by status"),
    sort_by: Literal["name", "status", "usage_count"] = Query("name", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> ListPdfTemplatesResponse:
    """List all PDF templates with filtering and sorting"""
    summaries = service.list_templates(
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return convert_template_summary_list(summaries)


@router.get("/{id}")
def get_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
):
    """
    Get template metadata (name, description, source_pdf_id, current_version_id).

    Frontend will use this to:
    1. Get source_pdf_id → fetch PDF bytes via GET /api/pdf-files/{source_pdf_id}/download
    2. Get current_version_id → fetch version details via GET /api/pdf-templates/versions/{current_version_id}
    3. Call GET /api/pdf-templates/{id}/versions to get version list for navigation
    """
    template = service.get_template(id)

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "source_pdf_id": template.source_pdf_id,
        "current_version_id": template.current_version_id,
        "status": template.status,
        "usage_count": template.usage_count,
        "last_used_at": template.last_used_at.isoformat() if template.last_used_at else None,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat()
    }


@router.get("/{id}/versions")
def get_template_versions(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
):
    """
    Get list of all version IDs and version numbers for a template.

    Returns list of tuples: [(version_id, version_number), ...]
    Used by frontend for version navigation (e.g., "Version 1 of 3", "Version 2 of 3")
    """
    version_list = service.get_version_list(id)

    return {
        "template_id": id,
        "versions": [
            {"version_id": vid, "version_number": vnum}
            for vid, vnum in version_list
        ]
    }


@router.post("", response_model=CreatePdfTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_pdf_template(
    request: CreatePdfTemplateRequest,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> CreatePdfTemplateResponse:
    """Create new PDF template with wizard data (template + version 1 atomically)"""
    template_create_data = convert_create_template_request(request)
    template, version_num, pipeline_id = service.create_template(template_create_data)
    return convert_create_template_response(template, version_num, pipeline_id)


@router.put("/{id}", response_model=UpdatePdfTemplateResponse, status_code=status.HTTP_200_OK)
def update_pdf_template(
    id: int,
    request: UpdatePdfTemplateRequest,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> UpdatePdfTemplateResponse:
    """
    Update template with smart versioning logic.

    Flow:
    1. Simple Case: Only name/description → Update metadata only (no new version)
    2. Version Case: signature_objects or extraction_fields → Create new version
    3. Complex Case: Pipeline fields → Validate/compile/create pipeline → Create new version

    All updates are atomic using unit-of-work pattern.

    Errors:
    - 404: Template not found
    - 409: Template is active (deactivate first to update wizard data)
    - 400: Pipeline validation fails
    """
    update_data = convert_update_template_request(request)
    template, version_num, pipeline_id = service.update_template(id, update_data)
    return convert_update_template_response(template, version_num, pipeline_id)


@router.post("/{id}/activate", response_model=ActivatePdfTemplateResponse)
def activate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> ActivatePdfTemplateResponse:
    """Activate template for ETO matching"""
    template = service.activate_template(id)
    return convert_activate_template_response(template)


@router.post("/{id}/deactivate", response_model=DeactivatePdfTemplateResponse)
def deactivate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> DeactivatePdfTemplateResponse:
    """Deactivate template (stop using for ETO matching)"""
    template = service.deactivate_template(id)
    return convert_deactivate_template_response(template)


@router.get("/versions/{version_id}")
def get_template_version(
    version_id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
):
    """
    Get specific version details by version ID.

    Used when:
    1. Viewing template details (fetch current version)
    2. Switching between versions (fetch selected version)

    Returns full version object with signature_objects, extraction_fields, pipeline_definition_id.
    """
    version = service.get_version_by_id(version_id)

    from shared.types.pdf_files import serialize_pdf_objects
    from shared.types.pdf_templates import serialize_extraction_fields

    return {
        "id": version.id,
        "template_id": version.template_id,
        "version_number": version.version_number,
        "source_pdf_id": version.source_pdf_id,
        "signature_objects": serialize_pdf_objects(version.signature_objects),
        "extraction_fields": serialize_extraction_fields(version.extraction_fields),
        "pipeline_definition_id": version.pipeline_definition_id,
        "created_at": version.created_at.isoformat()
    }


@router.post("/simulate", response_model=SimulateTemplateResponse, status_code=status.HTTP_200_OK)
def simulate_template(
    request: Union[SimulateTemplateRequestStored, SimulateTemplateRequestUpload]
) -> SimulateTemplateResponse:
    """
    Simulate template processing without persistence.

    Used during template creation/editing to test extraction and transformation logic.

    Two modes:
    1. Stored PDF: Uses existing PDF file from database (pdf_source: "stored", pdf_file_id)
    2. Uploaded PDF: Uses PDF from multipart upload (pdf_source: "upload", file in form data)

    Request Body (Stored):
    - pdf_source: "stored"
    - pdf_file_id: ID of stored PDF file
    - signature_objects: Objects to match
    - extraction_fields: Fields to extract
    - pipeline_state: Transformation pipeline

    Request Body (Upload):
    - pdf_source: "upload"
    - signature_objects: Objects to match
    - extraction_fields: Fields to extract
    - pipeline_state: Transformation pipeline
    - PDF file in multipart form data

    Returns:
    - Simulation results with:
      - Template matching status
      - Data extraction results with validation
      - Pipeline execution results (action modules simulated, not executed)

    Errors:
    - 400: Invalid request or simulation failed
    - 404: Referenced PDF file not found (for stored mode)
    """
    pass
