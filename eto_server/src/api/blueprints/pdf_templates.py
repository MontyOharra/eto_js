"""
Templates API Blueprint
REST endpoints for PDF template creation, management, and versioning
"""
import json
import logging
from flask import Blueprint, request
from flask_cors import cross_origin
from typing import Dict, Any
from pydantic import ValidationError

from shared.services import get_pdf_template_service, get_pdf_processing_service
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


def convert_query_params(args_dict: Dict[str, str]) -> Dict[str, Any]:
    """Convert string query parameters to appropriate types for Pydantic validation"""
    converted = {}
    for key, value in args_dict.items():
        if key in ['page', 'limit']:
            # Convert to int
            try:
                converted[key] = int(value)
            except ValueError:
                converted[key] = value  # Let Pydantic handle the validation error
        elif key == 'desc':
            # Convert string to boolean
            converted[key] = value.lower() in ('true', '1', 'yes', 'on')
        else:
            # Keep as string
            converted[key] = value
    return converted


# Create blueprint
pdf_templates_bp = Blueprint('templates', __name__, url_prefix='/api/pdf_templates')


@pdf_templates_bp.route('/', methods=['POST'])
@cross_origin()
def create_template():
    """
    Create a new PDF template

    Expected JSON payload:
    {
        "name": str,
        "description": str (optional),
        "source_pdf_id": int,
        "selected_objects": [...],  // PDF objects for template matching
        "extraction_fields": [...]  // fields to extract from matching PDFs
    }
    """
    try:
        # Validate request with Pydantic
        try:
            request_data = PdfTemplateCreateRequest(**request.get_json())
        except ValidationError as e:
            return ErrorResponse(
                error="Validation error",
                message=f"Request validation failed: {e.errors()}"
            ).model_dump_json(), 400
        except Exception as e:
            return ErrorResponse(
                error="Invalid JSON",
                message="Request body must be valid JSON"
            ).model_dump_json(), 400

        # Get PDF template service
        template_service = get_pdf_template_service()
        if not template_service:
            return ErrorResponse(
                error="Template service not available",
                message="PDF template service is not available"
            ).model_dump_json(), 500
            
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
            return ErrorResponse(
                error="No valid signature objects",
                message="At least one valid signature object is required"
            ).model_dump_json(), 400

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
            return ErrorResponse(
                error="No valid extraction fields",
                message="At least one valid extraction field is required"
            ).model_dump_json(), 400

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
        ).model_dump_json(), 201

    except ValueError as e:
        logger.warning(f"Value error in create_template: {e}")
        return ErrorResponse(
            error="Invalid parameter",
            message=str(e)
        ).model_dump_json(), 400

    except Exception as e:
        logger.error(f"Error creating template: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while creating the template"
        ).model_dump_json(), 500




@pdf_templates_bp.route('/<int:template_id>/versions', methods=['POST'])
@cross_origin()
def create_template_version(template_id: int):
    """
    Create a new version of a PDF template

    Expected JSON payload:
    {
        "signature_objects": [...],  // signature objects for template matching
        "extraction_fields": [...]  // fields to extract from matching PDFs
    }
    """
    try:
        # Validate request with Pydantic
        try:
            request_data = PdfTemplateVersionCreateRequest(**request.get_json())
        except ValidationError as e:
            return ErrorResponse(
                error="Validation error",
                message=f"Request validation failed: {e.errors()}"
            ).model_dump_json(), 400
        except Exception as e:
            return ErrorResponse(
                error="Invalid JSON",
                message="Request body must be valid JSON"
            ).model_dump_json(), 400

        template_service = get_pdf_template_service()
        if not template_service:
            return ErrorResponse(
                error="Template service not available",
                message="PDF template service is not available"
            ).model_dump_json(), 500

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
        ).model_dump_json(), 201
            
    except ValueError as e:
        logger.warning(f"Value error in create_template_version: {e}")
        return ErrorResponse(
            error="Invalid parameter",
            message=str(e)
        ).model_dump_json(), 400

    except Exception as e:
        logger.error(f"Error creating template version: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while creating the template version"
        ).model_dump_json(), 500


@pdf_templates_bp.route('/', methods=['GET'])
@cross_origin()
def list_templates():
    """
    List PDF templates with filtering and pagination

    Query parameters:
    - status: Filter by template status (active/inactive)
    - order_by: Field to order by (default: created_at)
    - desc: Sort in descending order (default: false)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    - include: Include version data (current/all)
    """
    try:
        # Validate query parameters with Pydantic
        try:
            request_data = TemplateListRequest(**request.args.to_dict())
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid query parameters",
                message=f"Validation failed: {e.errors()}"
            ).model_dump_json(), 400

        # TODO: Implement template listing service functionality
        # TODO: Call template_service.list_templates() with validated parameters
        # TODO: Return appropriate response with templates and pagination data

        return {"TODO": "Implement list_templates service call"}, 200

    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while listing templates"
        ).model_dump_json(), 500


@pdf_templates_bp.route('/<int:template_id>', methods=['GET'])
@cross_origin()
def get_template(template_id: int):
    """
    Get single PDF template by ID

    Query parameters:
    - include: Include version data (current/all)
    """
    try:
        # Validate query parameters with Pydantic
        try:
            request_data = TemplateGetRequest(**request.args.to_dict())
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid query parameters",
                message=f"Validation failed: {e.errors()}"
            ).model_dump_json(), 400

        # TODO: Implement get template service functionality
        # TODO: Call template_service.get_template(template_id, include=request_data.include)
        # TODO: Handle template not found case
        # TODO: Return appropriate response with template data

        return {"TODO": f"Implement get_template service call for template {template_id}"}, 200

    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while getting template"
        ).model_dump_json(), 500


@pdf_templates_bp.route('/<int:template_id>/versions/<int:version_id>', methods=['GET'])
@cross_origin()
def get_template_version(template_id: int, version_id: int):
    """
    Get specific template version
    """
    try:
        # Validate query parameters (likely empty)
        try:
            request_data = TemplateVersionGetRequest(**request.args.to_dict())
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid query parameters",
                message=f"Validation failed: {e.errors()}"
            ).model_dump_json(), 400

        # TODO: Implement get template version service functionality
        # TODO: Call template_service.get_template_version(template_id, version_id)
        # TODO: Handle template/version not found cases
        # TODO: Return appropriate response with version data

        return {"TODO": f"Implement get_template_version service call for template {template_id}, version {version_id}"}, 200

    except Exception as e:
        logger.error(f"Error getting template version {template_id}/{version_id}: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while getting template version"
        ).model_dump_json(), 500


@pdf_templates_bp.route('/<int:template_id>', methods=['PATCH'])
@cross_origin()
def update_template(template_id: int):
    """
    Update PDF template fields

    Expected JSON payload:
    {
        "name": str (optional),
        "description": str (optional),
        "status": str (optional, active/inactive)
    }
    """
    try:
        # Validate request with Pydantic
        try:
            request_data = TemplateUpdateRequest(**request.get_json())
        except ValidationError as e:
            return ErrorResponse(
                error="Validation error",
                message=f"Request validation failed: {e.errors()}"
            ).model_dump_json(), 400
        except Exception as e:
            return ErrorResponse(
                error="Invalid JSON",
                message="Request body must be valid JSON"
            ).model_dump_json(), 400

        # TODO: Implement template update service functionality
        # TODO: Call template_service.update_template(template_id, update_data)
        # TODO: Handle template not found case
        # TODO: Return appropriate response with updated template data

        return {"TODO": f"Implement update_template service call for template {template_id}"}, 200

    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while updating template"
        ).model_dump_json(), 500


@pdf_templates_bp.route('/<int:template_id>/current-version', methods=['PUT'])
@cross_origin()
def set_current_version(template_id: int):
    """
    Set current template version

    Expected JSON payload:
    {
        "version_id": int
    }
    """
    try:
        # Validate request with Pydantic
        try:
            request_data = TemplateSetCurrentVersionRequest(**request.get_json())
        except ValidationError as e:
            return ErrorResponse(
                error="Validation error",
                message=f"Request validation failed: {e.errors()}"
            ).model_dump_json(), 400
        except Exception as e:
            return ErrorResponse(
                error="Invalid JSON",
                message="Request body must be valid JSON"
            ).model_dump_json(), 400

        # TODO: Implement set current version service functionality
        # TODO: Call template_service.set_current_version(template_id, request_data.version_id)
        # TODO: Handle template/version not found cases
        # TODO: Validate that version belongs to template
        # TODO: Return appropriate response with updated template data

        return {"TODO": f"Implement set_current_version service call for template {template_id}, version {request_data.version_id}"}, 200

    except Exception as e:
        logger.error(f"Error setting current version for template {template_id}: {e}", exc_info=True)
        return ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred while setting current version"
        ).model_dump_json(), 500


# Export the blueprint
__all__ = ['pdf_templates_bp']