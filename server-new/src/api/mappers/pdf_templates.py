"""
PDF Templates Mappers
Convert between domain dataclasses and API Pydantic models
"""
from typing import Any
from shared.types.pdf_templates import (
    PdfTemplateListView,
    PdfTemplate,
    PdfTemplateVersion,
    PdfTemplateCreate,
    PdfTemplateUpdate,
    PdfVersionSummary,
    ExtractionField as ExtractionFieldDomain,
)
from shared.types.pdf_files import PdfObjects, serialize_pdf_objects, deserialize_pdf_objects
from api.schemas.pdf_templates import (
    TemplateListItem,
    TemplateVersionSummary,
    PdfTemplate as PdfTemplateAPI,
    VersionListItem,
    CreatePdfTemplateRequest,
    UpdatePdfTemplateRequest,
    GetTemplateVersionResponse,
    ExtractionField as ExtractionFieldAPI,
)

# ========== Helper Functions ==========

def convert_pdf_objects_to_api(objects: PdfObjects) -> dict[str, list[dict[str, Any]]]:
    """
    Convert domain PdfObjects to API format (both use grouped dict).

    Format: {"text_words": [...], "graphic_rects": [...]}
    """
    return serialize_pdf_objects(objects)


def convert_pdf_objects_to_domain(objects_dict: dict[str, list[dict[str, Any]]]) -> PdfObjects:
    """
    Convert API grouped dict to domain PdfObjects.

    Format: {"text_words": [...], "graphic_rects": [...]}
    """
    return deserialize_pdf_objects(objects_dict)


def convert_extraction_fields_to_api(fields: list[ExtractionFieldDomain]) -> list[ExtractionFieldAPI]:
    """Convert domain extraction fields to API format"""
    return [
        ExtractionFieldAPI(
            name=field.name,
            description=field.description,
            bbox=field.bbox,
            page=field.page
        )
        for field in fields
    ]


def convert_extraction_fields_to_domain(fields: list[ExtractionFieldAPI]) -> list[ExtractionFieldDomain]:
    """Convert API extraction fields to domain format"""
    return [
        ExtractionFieldDomain(
            name=field.name,
            description=field.description,
            bbox=field.bbox,
            page=field.page
        )
        for field in fields
    ]


# ========== Domain → API (Response) Conversions ==========

def convert_pdf_template(template: PdfTemplate) -> PdfTemplateAPI:
    """Convert domain PdfTemplate to API PdfTemplate"""
    return PdfTemplateAPI(
        id=template.id,
        name=template.name,
        description=template.description,
        status=template.status,
        source_pdf_id=template.source_pdf_id,
        current_version_id=template.current_version_id,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


def convert_version_list(version_list: list[tuple[int, int]]) -> list[VersionListItem]:
    """Convert list of (version_id, version_number) tuples to API list"""
    return [
        VersionListItem(version_id=vid, version_number=vnum)
        for vid, vnum in version_list
    ]


def convert_template_summary(summary: PdfTemplateListView) -> TemplateListItem:
    """Convert domain PdfTemplateSummary to API TemplateListItem"""
    return TemplateListItem(
        id=summary.id,
        name=summary.name,
        description=summary.description,
        status=summary.status,
        source_pdf_id=summary.source_pdf_id,
        current_version=TemplateVersionSummary(
            version_id=summary.current_version_id or 0,
            version_num=summary.current_version_number or 0,
            usage_count=summary.version_usage_count or 0
        ) if summary.current_version_id else TemplateVersionSummary(
            version_id=0,
            version_num=0,
            usage_count=0
        ),
        total_versions=summary.version_count
    )


def convert_template_summary_list(
    summaries: list[PdfTemplateListView]
) -> list[TemplateListItem]:
    """Convert list of domain summaries to API list"""
    return [convert_template_summary(s) for s in summaries]




def convert_template_version(
    version: PdfTemplateVersion,
    is_current: bool
) -> GetTemplateVersionResponse:
    """Convert domain template version to API response"""
    return GetTemplateVersionResponse(
        version_id=version.id,
        template_id=version.template_id,
        version_num=version.version_number,
        source_pdf_id=version.source_pdf_id,
        is_current=is_current,
        signature_objects=convert_pdf_objects_to_api(version.signature_objects),
        extraction_fields=convert_extraction_fields_to_api(version.extraction_fields),
        pipeline_definition_id=version.pipeline_definition_id,
        created_at=version.created_at.isoformat()
    )


# ========== API (Request) → Domain Conversions ==========

def convert_create_template_request(request: CreatePdfTemplateRequest) -> PdfTemplateCreate:
    """Convert API create request to domain PdfTemplateCreate"""
    return PdfTemplateCreate(
        name=request.name,
        description=request.description,
        signature_objects=convert_pdf_objects_to_domain(request.signature_objects),
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields),
        pipeline_state=request.pipeline_state.model_dump(),
        visual_state=request.visual_state.model_dump(),
        source_pdf_id=request.source_pdf_id or 0
    )


def convert_update_template_request(request: UpdatePdfTemplateRequest) -> PdfTemplateUpdate:
    """
    Convert API update request to unified domain PdfTemplateUpdate.

    All fields (metadata + wizard data + pipeline) are included in a single object.
    Service layer will detect what changed and handle versioning/pipeline creation accordingly.
    """
    return PdfTemplateUpdate(
        name=request.name,
        description=request.description,
        signature_objects=convert_pdf_objects_to_domain(request.signature_objects) if request.signature_objects else None,
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields) if request.extraction_fields else None,
        pipeline_state=request.pipeline_state.model_dump() if request.pipeline_state else None,
        visual_state=request.visual_state.model_dump() if request.visual_state else None
    )


