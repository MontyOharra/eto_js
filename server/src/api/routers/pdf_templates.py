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
    GetCustomersResponse,
    Customer,
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

    # Batch fetch customer names for all templates with customer_id
    customer_ids = [s.customer_id for s in summaries if s.customer_id is not None]
    customer_names = service._get_customer_names(customer_ids) if customer_ids else {}

    return convert_template_summary_list(summaries, customer_names)


@router.get("/customers", response_model=GetCustomersResponse)
async def get_customers(
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> GetCustomersResponse:
    """
    Get list of customers for template dropdown.

    Fetches active customers from the Access database (HTC300_G030_T010 Customers table).
    Returns customers sorted by name.
    """
    customers_data = service.list_customers()

    customers = [
        Customer(id=c["id"], name=c["name"])
        for c in customers_data
    ]

    return GetCustomersResponse(customers=customers)


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
    customer_name = service._get_customer_name(template.customer_id)
    return convert_pdf_template(template, version_list, customer_name)


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
    customer_name = template_service._get_customer_name(template.customer_id)
    return convert_pdf_template(template, version_list, customer_name)


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
    customer_name = service._get_customer_name(template.customer_id)
    return convert_pdf_template(template, version_list, customer_name)


@router.post("/{id}/activate", response_model=PdfTemplate)
async def activate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """Activate template for ETO matching"""
    template = service.activate_template(id)

    # Fetch version list for response
    version_list = service.get_version_list(id)
    customer_name = service._get_customer_name(template.customer_id)
    return convert_pdf_template(template, version_list, customer_name)


@router.post("/{id}/deactivate", response_model=PdfTemplate)
async def deactivate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """Deactivate template (stop using for ETO matching)"""
    template = service.deactivate_template(id)

    # Fetch version list for response
    version_list = service.get_version_list(id)
    customer_name = service._get_customer_name(template.customer_id)
    return convert_pdf_template(template, version_list, customer_name)


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