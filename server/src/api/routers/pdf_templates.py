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
    TestMultiTemplateMatchingResponse,
    TemplateMatchResult,
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
    Templates can be updated even when active (new version created automatically).

    Errors:
    - 404: Template not found
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
    api_response = convert_simulate_result_to_api(result)

    # Debug: Log what we're sending to frontend
    logger.info(f"API Response: status={api_response.pipeline_status}, error={api_response.pipeline_error}")
    logger.info(f"API Response steps: {len(api_response.pipeline_steps)} steps")
    for step in api_response.pipeline_steps:
        logger.info(f"  API Step {step.step_number} ({step.module_instance_id}): error={step.error}")

    return api_response


@router.post("/test-multi-match", response_model=TestMultiTemplateMatchingResponse)
async def test_multi_template_matching(
    pdf_file: UploadFile = File(...),
    template_service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service()),
    pdf_service: PdfFilesService = Depends(lambda: ServiceContainer.get_pdf_files_service())
) -> TestMultiTemplateMatchingResponse:
    """
    TEMPORARY TEST ENDPOINT - E2E test multi-template matching algorithm.

    Uploads a PDF, extracts objects, runs multi-template matching against active templates,
    and returns the matching results without creating ETO runs.

    Process:
    1. Upload and store PDF (with object extraction)
    2. Run match_templates_multi_page() against all active templates
    3. Return detailed matching results for inspection

    Use this to test the algorithm before integrating into full ETO workflow.
    """
    from shared.exceptions.service import ValidationError

    # Validate file type
    if not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
        raise ValidationError("Invalid file type - must be a PDF")

    # Read file bytes
    pdf_bytes = await pdf_file.read()

    # Store PDF (handles extraction automatically)
    logger.info(f"Uploading PDF: {pdf_file.filename}")
    pdf = pdf_service.store_pdf(
        file_bytes=pdf_bytes,
        filename=pdf_file.filename,
        email_id=None
    )
    logger.info(f"PDF stored: id={pdf.id}, pages={pdf.page_count}")

    # Run multi-template matching
    logger.info(f"Running multi-template matching for PDF {pdf.id}")
    matching_result = template_service.match_templates_multi_page(pdf)

    # Enrich matches with template/version names
    enriched_matches = []
    for match in matching_result.matches:
        template = template_service.get_template(match.template_id)
        version = template_service.get_version_by_id(match.version_id)
        enriched_matches.append(
            TemplateMatchResult(
                template_id=match.template_id,
                template_name=template.name,
                version_id=match.version_id,
                version_number=version.version_number,
                matched_pages=match.matched_pages
            )
        )

    logger.info(
        f"Matching complete: {len(enriched_matches)} matches, "
        f"{len(matching_result.unmatched_pages)} unmatched pages"
    )

    return TestMultiTemplateMatchingResponse(
        pdf_id=pdf.id,
        pdf_filename=pdf.original_filename,
        total_pages=pdf.page_count,
        matches=enriched_matches,
        unmatched_pages=matching_result.unmatched_pages
    )
