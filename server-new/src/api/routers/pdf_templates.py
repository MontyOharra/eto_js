"""
PDF Templates FastAPI Router
REST endpoints for PDF template creation, management, and versioning
"""
import json
import logging
from typing import Optional, Literal
from fastapi import APIRouter, Query, status, Depends, File, UploadFile, Form

from api.schemas.pdf_templates import (
    PdfTemplate,
    TemplateListItem,
    VersionListItem,
    CreatePdfTemplateRequest,
    UpdatePdfTemplateRequest,
    GetTemplateVersionResponse,
    SimulateTemplateRequest,
    SimulateTemplateResponse,
    ExtractedFieldResult,
)
from api.mappers.pdf_templates import (
    convert_template_summary_list,
    convert_pdf_template,
    convert_version_list,
    convert_create_template_request,
    convert_update_template_request,
    convert_template_version,
    convert_simulate_request,
    convert_simulate_result_to_api,
)

from shared.services.service_container import ServiceContainer
from shared.exceptions.service import ValidationError
from features.pdf_templates import PdfTemplateService
from features.pdf_files.service import PdfFilesService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pdf-templates",
    tags=["PDF Templates"]
)


@router.get("", response_model=list[TemplateListItem])
async def list_pdf_templates(
    status_filter: Optional[Literal["active", "inactive"]] = Query(None, description="Filter by status"),
    sort_by: Literal["name", "status", "usage_count"] = Query("name", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> list[TemplateListItem]:
    """List all PDF templates with filtering and sorting"""
    summaries = service.list_templates(
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return convert_template_summary_list(summaries)


@router.get("/{id}", response_model=PdfTemplate)
async def get_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """
    Get template metadata with version navigation.

    Returns template metadata including all version IDs/numbers for navigation.
    Frontend can then fetch specific version details via GET /api/pdf-templates/versions/{version_id}
    """
    template = service.get_template(id)
    version_list = service.get_version_list(id)
    return convert_pdf_template(template, version_list)


@router.post("", response_model=PdfTemplate, status_code=status.HTTP_201_CREATED)
async def create_pdf_template(
    request: CreatePdfTemplateRequest,
    template_service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """
    Create new PDF template with wizard data (template + version 1 atomically).

    Prerequisites:
    - PDF must already be uploaded via POST /api/pdf-files
    - Use the returned pdf_id as source_pdf_id in this request

    Creates:
    - Pipeline definition (with hash-based deduplication)
    - Compiled plan + steps (if pipeline hash is new)
    - Template record
    - Template version 1

    Returns created template with status="inactive"
    """
    # Convert API request to domain type (mapper handles all nested conversions)
    template_create_data = convert_create_template_request(request)

    # Create template (service orchestrates all database operations)
    template, version_num, pipeline_id = template_service.create_template(template_create_data)

    logger.info(
        f"Created template {template.id} (version {version_num}, pipeline {pipeline_id})"
    )

    # Fetch version list and convert to API response
    version_list = template_service.get_version_list(template.id)
    return convert_pdf_template(template, version_list)


@router.put("/{id}", response_model=PdfTemplate, status_code=status.HTTP_200_OK)
async def update_pdf_template(
    id: int,
    request: UpdatePdfTemplateRequest,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
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

    # Fetch version list for response
    version_list = service.get_version_list(id)
    return convert_pdf_template(template, version_list)


@router.post("/{id}/activate", response_model=PdfTemplate)
async def activate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """Activate template for ETO matching"""
    template = service.activate_template(id)

    # Fetch version list for response
    version_list = service.get_version_list(id)
    return convert_pdf_template(template, version_list)


@router.post("/{id}/deactivate", response_model=PdfTemplate)
async def deactivate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """Deactivate template (stop using for ETO matching)"""
    template = service.deactivate_template(id)

    # Fetch version list for response
    version_list = service.get_version_list(id)
    return convert_pdf_template(template, version_list)


@router.get("/versions/{version_id}", response_model=GetTemplateVersionResponse)
async def get_template_version(
    version_id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> GetTemplateVersionResponse:
    """
    Get specific version details by version ID.

    Used when:
    1. Viewing template details (fetch current version)
    2. Switching between versions (fetch selected version)

    Returns full version object with signature_objects, extraction_fields, pipeline_definition_id.
    """
    version = service.get_version_by_id(version_id)
    template = service.get_template(version.template_id)
    is_current = template.current_version_id == version.id
    return convert_template_version(version, is_current)


@router.post("/simulate", response_model=SimulateTemplateResponse)
async def simulate_template(
    request: SimulateTemplateRequest,
    template_service: PdfTemplateService = Depends(
        lambda: ServiceContainer.get_pdf_template_service()
    )
) -> SimulateTemplateResponse:
    """
    Simulate template processing without persistence.

    Used during template creation/editing to test extraction and transformation.
    Client must provide PDF objects (from /pdf-files/process-objects or stored PDF).

    Returns:
    - Simulation results with:
      - Data extraction results with bbox info
      - Pipeline execution results (status, steps, actions)
    """
    # Convert to domain
    simulate_data = convert_simulate_request(request)

    # Run simulation
    result = template_service.simulate(simulate_data)

    # Convert to API response
    return convert_simulate_result_to_api(result)
