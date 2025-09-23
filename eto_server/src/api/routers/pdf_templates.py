"""
PDF Templates FastAPI Router
REST endpoints for PDF template creation, management, and versioning
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse

from shared.services.service_container import ServiceContainer, get_service_container
from shared.models import PdfTemplate, PdfTemplateVersion, PdfTemplateCreate, PdfTemplateUpdate, PdfTemplateVersionCreate, ServiceStatusResponse, ServiceHealth
from shared.exceptions import ObjectNotFoundError
from api.schemas import (
    PdfTemplateVersionCreateRequest,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/pdf_templates",
    tags=["PDF Templates"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post("/",
             response_model=PdfTemplate,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new PDF template",
             description="Create a new PDF template with signature objects and extraction fields")
def create_template(
    template_create: PdfTemplateCreate,
    container: ServiceContainer = Depends(get_service_container)
) -> PdfTemplate:
    """
    Create a new PDF template

    - **name**: Template name (required)
    - **description**: Template description (optional)
    - **pdf_id**: ID of the source PDF file (required)
    - **initial_signature_objects**: PDF objects for template matching (required, min 1)
    - **initial_extraction_fields**: Fields to extract from matching PDFs (optional)
    """
    try:
        # Get PDF template service
        template_service = container.get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Validate required fields (Pydantic already handles basic validation)
        if not template_create.initial_signature_objects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one signature object is required"
            )

        if not template_create.initial_extraction_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one extraction field is required"
            )

        # Create the template directly using the domain create model
        template = template_service.create_template(template_create)

        logger.info(f"Created template {template.id}: '{template.name}' with {len(template_create.initial_signature_objects)} signature objects and {len(template_create.initial_extraction_fields)} extraction fields")

        return template

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except ValueError as e:
        logger.warning(f"Value error in create_template: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the template"
        )


@router.post("/{template_id}/versions",
             response_model=PdfTemplateVersion,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new version of a PDF template",
             description="Create a new version of an existing PDF template with updated signature objects and extraction fields")
def create_template_version(
    template_id: int,
    request_data: PdfTemplateVersionCreateRequest,
    container: ServiceContainer = Depends(get_service_container)
) -> PdfTemplateVersion:
    """
    Create a new version of a PDF template

    - **template_id**: ID of the existing template (from path)
    - **signature_objects**: PDF objects for template matching (required, min 1)
    - **extraction_fields**: Fields to extract from matching PDFs (optional)
    """
    try:
        template_service = container.get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Create domain model, adding pdf_template_id from URL parameter
        version_create = PdfTemplateVersionCreate(
            pdf_template_id=template_id,
            signature_objects=request_data.signature_objects,
            extraction_fields=request_data.extraction_fields,
            signature_object_count=request_data.signature_object_count
        )

        # Create the template version using the create model
        version = template_service.create_template_version(version_create)

        logger.info(f"Created version {version.version_num} for template {template_id} with {len(version.signature_objects)} signature objects and {len(version.extraction_fields)} extraction fields")

        return version

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except ObjectNotFoundError as e:
        logger.warning(f"Template not found in create_template_version: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Value error in create_template_version: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating template version: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the template version"
        )


@router.get("/",
            response_model=List[PdfTemplate],
            summary="List PDF templates",
            description="List PDF templates with filtering and pagination")
def list_templates(
    template_status: Optional[str] = Query(None, pattern="^(active|inactive)$", description="Filter by template status"),
    order_by: str = Query("created_at", description="Field to order by"),
    desc: bool = Query(False, description="Sort in descending order"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> List[PdfTemplate]:
    """
    List PDF templates with filtering and pagination

    Query parameters:
    - **status**: Filter by template status (active/inactive)
    - **order_by**: Field to order by (default: created_at)
    - **desc**: Sort in descending order (default: false)
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    """
    try:
        # Get PDF template service
        template_service = container.get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Calculate offset from page and limit
        offset = (page - 1) * limit

        # Get templates with filtering and pagination
        templates = template_service.get_templates(
            status=template_status,
            order_by=order_by,
            desc=desc,
            limit=limit,
            offset=offset
        )

        logger.info(f"Retrieved {len(templates)} templates with filters: status={template_status}, order_by={order_by}, desc={desc}")
        
        return templates

    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing templates"
        )


@router.get("/{template_id}",
            response_model=PdfTemplate,
            summary="Get single PDF template",
            description="Get single PDF template by ID")
def get_template(template_id: int) -> PdfTemplate:
    """
    Get single PDF template by ID

    - **template_id**: ID of the template to retrieve (from path)
    """
    try:
        # Get PDF template service
        template_service = container.get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Get template by ID
        template = template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )

        logger.info(f"Retrieved template {template_id}: '{template.name}'")
        return template

    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting template"
        )


@router.get("/{template_id}/versions/{version_id}",
            response_model=PdfTemplateVersion,
            summary="Get specific template version",
            description="Get specific template version by template ID and version ID")
def get_template_version(
    template_id: int,
    version_id: int
) -> PdfTemplateVersion:
    """
    Get specific template version

    - **template_id**: ID of the template (from path)
    - **version_id**: ID of the version (from path)
    """
    try:
        # Get PDF template service
        template_service = container.get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Get the specific template version
        version = template_service.get_template_version(template_id, version_id)
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} version {version_id} not found"
            )

        logger.info(f"Retrieved template {template_id} version {version_id} (version number {version.version_num})")
        return version

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting template version {template_id}/{version_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting template version"
        )


@router.patch("/{template_id}",
              response_model=PdfTemplate,
              summary="Update PDF template",
              description="Update PDF template fields (name, description, status)")
def update_template(
    template_id: int,
    update_data: PdfTemplateUpdate
) -> PdfTemplate:
    """
    Update PDF template fields

    - **template_id**: ID of the template to update (from path)
    - **name**: New template name (optional)
    - **description**: New template description (optional)
    - **status**: New template status - active/inactive (optional)
    """
    try:
        # Get PDF template service
        template_service = container.get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Update the template
        updated_template = template_service.update_template(template_id, update_data)
        if not updated_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )

        logger.info(f"Updated template {template_id}: '{updated_template.name}'")
        return updated_template

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating template"
        )


@router.get("/status",
            response_model=ServiceStatusResponse,
            summary="Get PDF templates service status",
            description="Check if the PDF templates service is healthy and operational")
def get_pdf_templates_status() -> ServiceStatusResponse:
    """
    Get PDF templates service status

    Returns health status of the PDF templates service including database connectivity
    """
    try:
        template_service = container.get_pdf_template_service()
        if not template_service:
            return ServiceStatusResponse(
                service="pdf_templates",
                status=ServiceHealth.DOWN,
                message="PDF templates service is not available"
            )

        is_healthy = template_service.is_healthy()

        return ServiceStatusResponse(
            service="pdf_templates",
            status=ServiceHealth.UP if is_healthy else ServiceHealth.DOWN,
            message="Service is operational" if is_healthy else "Service is not operational"
        )

    except Exception as e:
        logger.error(f"Error checking PDF templates service status: {e}")
        return ServiceStatusResponse(
            service="pdf_templates",
            status=ServiceHealth.DOWN,
            message=f"Service health check failed: {str(e)}"
        )