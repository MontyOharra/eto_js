"""
PDF Templates FastAPI Router
REST endpoints for PDF template creation, management, and versioning
"""
import logging
from typing import Literal

from fastapi import APIRouter, Query, status, Depends, UploadFile, File

from api.schemas.pdf_templates import (
    PdfTemplateResponse,
    PaginatedTemplateListResponse,
    CreatePdfTemplateRequest,
    UpdatePdfTemplateRequest,
    GetTemplateVersionResponse,
    SimulateTemplateRequest,
    SimulateTemplateResponse,
    GetCustomersResponse,
    Customer,
    DebugMatchResponse,
)
from api.mappers.pdf_templates import (
    build_template_list,
    build_template_response,
    to_template_create,
    to_template_update,
    build_version_response,
    to_simulate_data,
    build_simulate_response,
)

from shared.services.service_container import ServiceContainer
from features.pdf_templates import PdfTemplateService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pdf-templates",
    tags=["PDF Templates"]
)


@router.get("", response_model=PaginatedTemplateListResponse)
async def list_pdf_templates(
    status_filter: Literal["active", "inactive"] | None = Query(None, description="Filter by status"),
    customer_id: int | None = Query(None, description="Filter by customer ID"),
    autoskip_filter: Literal["all", "processable", "skip"] | None = Query(None, description="Filter by autoskip"),
    sort_by: Literal["name", "status", "usage_count"] = Query("name", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PaginatedTemplateListResponse:
    """List PDF templates with filtering, sorting, and pagination"""
    summaries, total = service.list_templates(
        status=status_filter,
        customer_id=customer_id,
        autoskip_filter=autoskip_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

    # Batch fetch customer names for all templates with customer_id
    customer_ids = [s.customer_id for s in summaries if s.customer_id is not None]
    customer_names = service._get_customer_names(customer_ids) if customer_ids else {}

    items = build_template_list(summaries, customer_names)
    return PaginatedTemplateListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/customers", response_model=GetCustomersResponse)
async def get_customers(
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> GetCustomersResponse:
    """
    Get list of customers for template dropdown.

    Fetches active customers from the Access database.
    Returns customers sorted by name.
    """
    customers_data = service.list_customers()

    customers = [
        Customer(id=c["id"], name=c["name"])
        for c in customers_data
    ]

    return GetCustomersResponse(customers=customers)


@router.get("/{id}", response_model=PdfTemplateResponse)
async def get_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplateResponse:
    """
    Get template metadata with version navigation.

    Returns template metadata including all version IDs/numbers for navigation.
    Frontend can then fetch specific version details via GET /api/pdf-templates/versions/{version_id}
    """
    template = service.get_template(id)
    version_list = service.get_version_list(id)
    customer_name = service._get_customer_name(template.customer_id)
    return build_template_response(template, version_list, customer_name)


@router.post("", response_model=PdfTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_pdf_template(
    request: CreatePdfTemplateRequest,
    template_service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplateResponse:
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
    template_create_data = to_template_create(request)

    template, version_num, pipeline_id = template_service.create_template(template_create_data)

    logger.info(
        f"Created template {template.id} (version {version_num}, pipeline {pipeline_id})"
    )

    version_list = template_service.get_version_list(template.id)
    customer_name = template_service._get_customer_name(template.customer_id)
    return build_template_response(template, version_list, customer_name)


@router.put("/{id}", response_model=PdfTemplateResponse, status_code=status.HTTP_200_OK)
async def update_pdf_template(
    id: int,
    request: UpdatePdfTemplateRequest,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplateResponse:
    """
    Update template with smart versioning logic.

    Flow:
    1. Simple Case: Only name/description -> Update metadata only (no new version)
    2. Version Case: signature_objects or extraction_fields -> Create new version
    3. Complex Case: Pipeline fields -> Validate/compile/create pipeline -> Create new version

    All updates are atomic using unit-of-work pattern.
    Templates can be updated even when active (new version created automatically).
    """
    update_data = to_template_update(request)
    template, version_num, pipeline_id = service.update_template(id, update_data)

    version_list = service.get_version_list(id)
    customer_name = service._get_customer_name(template.customer_id)
    return build_template_response(template, version_list, customer_name)


@router.post("/{id}/activate", response_model=PdfTemplateResponse)
async def activate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplateResponse:
    """Activate template for ETO matching"""
    template = service.activate_template(id)

    version_list = service.get_version_list(id)
    customer_name = service._get_customer_name(template.customer_id)
    return build_template_response(template, version_list, customer_name)


@router.post("/{id}/deactivate", response_model=PdfTemplateResponse)
async def deactivate_pdf_template(
    id: int,
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplateResponse:
    """Deactivate template (stop using for ETO matching)"""
    template = service.deactivate_template(id)

    version_list = service.get_version_list(id)
    customer_name = service._get_customer_name(template.customer_id)
    return build_template_response(template, version_list, customer_name)


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
    return build_version_response(version, is_current)


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

    Returns simulation results with extraction and pipeline execution details.
    """
    simulate_data = to_simulate_data(request)
    result = template_service.simulate(simulate_data)
    api_response = build_simulate_response(result)

    logger.debug(f"Simulation: status={api_response.pipeline_status}, steps={len(api_response.pipeline_steps)}")

    return api_response


@router.post("/versions/{version_id}/debug-match", response_model=DebugMatchResponse)
async def debug_match_template(
    version_id: int,
    pdf_file: UploadFile = File(...),
    service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> DebugMatchResponse:
    """
    Debug template matching against a test PDF.

    Tests each signature object from the template version against the uploaded PDF
    and returns detailed match results for diagnostic purposes.

    Used to understand why a PDF does or doesn't match a template.
    """
    # Read PDF bytes
    pdf_bytes = await pdf_file.read()

    # Call service method
    result = service.debug_match_template(version_id, pdf_bytes)

    return result
