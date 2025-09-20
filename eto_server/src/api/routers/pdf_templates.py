"""
PDF Templates FastAPI Router
REST endpoints for PDF template creation, management, and versioning
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse

from shared.services import get_pdf_template_service
from shared.domain import ExtractionField, PdfObject
from api.schemas import (
    PdfTemplateCreateRequest,
    PdfTemplateVersionCreateRequest,
    PdfTemplateCreateResponse,
    PdfTemplateVersionCreateResponse,
    TemplateListRequest,
    TemplateGetRequest,
    TemplateVersionGetRequest,
    TemplateUpdateRequest,
    TemplateSetCurrentVersionRequest,
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


def convert_query_params_to_template_list_request(
    status_filter: Optional[str] = Query(None, regex="^(active|inactive)$", description="Filter by template status"),
    order_by: Optional[str] = Query("created_at", description="Field to order by"),
    desc: bool = Query(False, description="Sort in descending order"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include: Optional[str] = Query(None, regex="^(current|all)$", description="Include version data")
) -> TemplateListRequest:
    """Convert query parameters to TemplateListRequest model"""
    return TemplateListRequest(
        status=status_filter,
        order_by=order_by,
        desc=desc,
        page=page,
        limit=limit,
        include=include
    )


def convert_query_params_to_template_get_request(
    include: Optional[str] = Query(None, regex="^(current|all)$", description="Include version data")
) -> TemplateGetRequest:
    """Convert query parameters to TemplateGetRequest model"""
    return TemplateGetRequest(include=include)


@router.post("/",
             response_model=PdfTemplateCreateResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new PDF template",
             description="Create a new PDF template with signature objects and extraction fields")
async def create_template(request_data: PdfTemplateCreateRequest) -> PdfTemplateCreateResponse:
    """
    Create a new PDF template

    - **name**: Template name (required)
    - **description**: Template description (optional)
    - **source_pdf_id**: ID of the source PDF file (required)
    - **selected_objects**: PDF objects for template matching (required, min 1)
    - **extraction_fields**: Fields to extract from matching PDFs (optional)
    """
    try:
        # Get PDF template service
        template_service = get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Convert selected objects to PdfObject domain objects
        signature_objects = []
        for obj_data in request_data.selected_objects:
            try:
                pdf_obj = PdfObject(
                    type=obj_data.type,
                    page=obj_data.page,
                    text=obj_data.text,
                    x=obj_data.x,
                    y=obj_data.y,
                    width=obj_data.width,
                    height=obj_data.height,
                    bbox=obj_data.bbox,
                    font_name=obj_data.font_name,
                    font_size=obj_data.font_size,
                    char_count=obj_data.char_count
                )
                signature_objects.append(pdf_obj)
            except Exception as e:
                logger.warning(f"Failed to convert object to PdfObject: {e}")
                continue

        if not signature_objects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one valid signature object is required"
            )

        # Convert extraction fields to ExtractionField domain objects
        extraction_fields = []
        for field_data in request_data.extraction_fields:
            try:
                extraction_field = ExtractionField(
                    label=field_data.label,
                    bounding_box=field_data.boundingBox,
                    page=field_data.page,
                    required=field_data.required,
                    validation_regex=field_data.validationRegex,
                    description=field_data.description
                )
                extraction_fields.append(extraction_field)
            except Exception as e:
                logger.warning(f"Failed to convert extraction field: {e}")
                continue

        if not extraction_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one valid extraction field is required"
            )

        # Create the template using individual parameters
        template = template_service.create_template(
            name=request_data.name,
            description=request_data.description,
            pdf_id=request_data.source_pdf_id,
            signature_objects=signature_objects,
            extraction_fields=extraction_fields
        )

        logger.info(f"Created template {template.id}: '{template.name}' with {len(signature_objects)} signature objects and {len(extraction_fields)} extraction fields")

        return PdfTemplateCreateResponse(
            success=True,
            template_id=template.id,
            message=f"Template '{template.name}' created successfully",
            signature_object_count=len(signature_objects),
            extraction_field_count=len(extraction_fields)
        )

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
             response_model=PdfTemplateVersionCreateResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new version of a PDF template",
             description="Create a new version of an existing PDF template with updated signature objects and extraction fields")
async def create_template_version(
    template_id: int,
    request_data: PdfTemplateVersionCreateRequest
) -> PdfTemplateVersionCreateResponse:
    """
    Create a new version of a PDF template

    - **template_id**: ID of the existing template (from path)
    - **signature_objects**: PDF objects for template matching (required, min 1)
    - **extraction_fields**: Fields to extract from matching PDFs (optional)
    """
    try:
        template_service = get_pdf_template_service()
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Convert signature objects to PdfObject domain objects
        signature_objects = []
        for obj_data in request_data.signature_objects:
            try:
                pdf_obj = PdfObject(
                    type=obj_data.type,
                    page=obj_data.page,
                    text=obj_data.text,
                    x=obj_data.x,
                    y=obj_data.y,
                    width=obj_data.width,
                    height=obj_data.height,
                    bbox=obj_data.bbox,
                    font_name=obj_data.font_name,
                    font_size=obj_data.font_size,
                    char_count=obj_data.char_count
                )
                signature_objects.append(pdf_obj)
            except Exception as e:
                logger.warning(f"Failed to convert object to PdfObject: {e}")
                continue

        # Convert extraction fields to ExtractionField domain objects
        extraction_fields = []
        for field_data in request_data.extraction_fields:
            try:
                extraction_field = ExtractionField(
                    label=field_data.label,
                    bounding_box=field_data.boundingBox,
                    page=field_data.page,
                    required=field_data.required,
                    validation_regex=field_data.validationRegex,
                    description=field_data.description
                )
                extraction_fields.append(extraction_field)
            except Exception as e:
                logger.warning(f"Failed to convert extraction field: {e}")
                continue

        # Create the template version using individual parameters
        version = template_service.create_template_version(
            pdf_template_id=template_id,
            signature_objects=signature_objects,
            extraction_fields=extraction_fields
        )

        logger.info(f"Created version {version.version} for template {template_id} with {len(signature_objects)} signature objects and {len(extraction_fields)} extraction fields")

        return PdfTemplateVersionCreateResponse(
            success=True,
            template_id=template_id,
            version_id=version.id,
            version_number=version.version,
            message=f"Template version {version.version} created successfully",
            signature_object_count=len(signature_objects),
            extraction_field_count=len(extraction_fields)
        )

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
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
            summary="List PDF templates",
            description="List PDF templates with filtering and pagination")
async def list_templates(
    query_params: TemplateListRequest = Depends(convert_query_params_to_template_list_request)
):
    """
    List PDF templates with filtering and pagination

    Query parameters:
    - **status**: Filter by template status (active/inactive)
    - **order_by**: Field to order by (default: created_at)
    - **desc**: Sort in descending order (default: false)
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    - **include**: Include version data (current/all)
    """
    try:
        # TODO: Implement template listing service functionality
        # TODO: Call template_service.list_templates() with validated parameters
        # TODO: Return appropriate response with templates and pagination data

        return {"TODO": "Implement list_templates service call", "params": query_params.model_dump()}

    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing templates"
        )


@router.get("/{template_id}",
            summary="Get single PDF template",
            description="Get single PDF template by ID with optional version data")
async def get_template(
    template_id: int,
    query_params: TemplateGetRequest = Depends(convert_query_params_to_template_get_request)
):
    """
    Get single PDF template by ID

    - **template_id**: ID of the template to retrieve (from path)
    - **include**: Include version data (current/all) (from query)
    """
    try:
        # TODO: Implement get template service functionality
        # TODO: Call template_service.get_template(template_id, include=query_params.include)
        # TODO: Handle template not found case
        # TODO: Return appropriate response with template data

        return {"TODO": f"Implement get_template service call for template {template_id}", "params": query_params.model_dump()}

    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting template"
        )


@router.get("/{template_id}/versions/{version_id}",
            summary="Get specific template version",
            description="Get specific template version by template ID and version ID")
async def get_template_version(
    template_id: int,
    version_id: int,
    query_params: TemplateVersionGetRequest = Depends(lambda: TemplateVersionGetRequest())
):
    """
    Get specific template version

    - **template_id**: ID of the template (from path)
    - **version_id**: ID of the version (from path)
    """
    try:
        # TODO: Implement get template version service functionality
        # TODO: Call template_service.get_template_version(template_id, version_id)
        # TODO: Handle template/version not found cases
        # TODO: Return appropriate response with version data

        return {"TODO": f"Implement get_template_version service call for template {template_id}, version {version_id}"}

    except Exception as e:
        logger.error(f"Error getting template version {template_id}/{version_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting template version"
        )


@router.patch("/{template_id}",
              summary="Update PDF template",
              description="Update PDF template fields (name, description, status)")
async def update_template(
    template_id: int,
    request_data: TemplateUpdateRequest
):
    """
    Update PDF template fields

    - **template_id**: ID of the template to update (from path)
    - **name**: New template name (optional)
    - **description**: New template description (optional)
    - **status**: New template status - active/inactive (optional)
    """
    try:
        # TODO: Implement template update service functionality
        # TODO: Call template_service.update_template(template_id, update_data)
        # TODO: Handle template not found case
        # TODO: Return appropriate response with updated template data

        return {"TODO": f"Implement update_template service call for template {template_id}", "data": request_data.model_dump(exclude_none=True)}

    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating template"
        )


@router.put("/{template_id}/current-version",
            summary="Set current template version",
            description="Set the current active version for a PDF template")
async def set_current_version(
    template_id: int,
    request_data: TemplateSetCurrentVersionRequest
):
    """
    Set current template version

    - **template_id**: ID of the template (from path)
    - **version_id**: ID of the version to set as current (from body)
    """
    try:
        # TODO: Implement set current version service functionality
        # TODO: Call template_service.set_current_version(template_id, request_data.version_id)
        # TODO: Handle template/version not found cases
        # TODO: Validate that version belongs to template
        # TODO: Return appropriate response with updated template data

        return {"TODO": f"Implement set_current_version service call for template {template_id}, version {request_data.version_id}"}

    except Exception as e:
        logger.error(f"Error setting current version for template {template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while setting current version"
        )