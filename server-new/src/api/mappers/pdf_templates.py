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
    ListPdfTemplatesResponse,
    PdfTemplateDetail,
    TemplateVersionDetail,
    VersionIdSummary,
    PdfTemplateMetadataResponse,
    GetTemplateVersionsResponse,
    VersionListItem,
    CreatePdfTemplateRequest,
    CreatePdfTemplateResponse,
    UpdatePdfTemplateRequest,
    UpdatePdfTemplateResponse,
    ActivatePdfTemplateResponse,
    DeactivatePdfTemplateResponse,
    GetTemplateVersionResponse,
    ExtractionField as ExtractionFieldAPI,
)

# ========== Helper Functions ==========

def convert_pdf_objects_to_list(objects: PdfObjects) -> list[dict[str, Any]]:
    """
    Convert grouped PdfObjects to flat list with object_type field.

    Domain format: { "text_words": [...], "graphic_rects": [...] }
    API format: [ {..., "object_type": "text_words"}, {..., "object_type": "graphic_rects"} ]
    """
    signature_objects_dict = serialize_pdf_objects(objects)
    signature_objects_list = []

    for obj_type, objects_list in signature_objects_dict.items():
        for obj in objects_list:
            obj_with_type = {**obj, "object_type": obj_type}
            signature_objects_list.append(obj_with_type)

    return signature_objects_list


def convert_pdf_objects_from_list(objects_list: list[dict[str, Any]]) -> PdfObjects:
    """
    Convert flat list with object_type to grouped PdfObjects.

    API format: [ {..., "object_type": "text_words"}, {..., "object_type": "graphic_rects"} ]
    Domain format: { "text_words": [...], "graphic_rects": [...] }
    """
    signature_objects_grouped = {}

    for obj in objects_list:
        obj_copy = dict(obj)
        obj_type = obj_copy.pop("object_type")
        if obj_type not in signature_objects_grouped:
            signature_objects_grouped[obj_type] = []
        signature_objects_grouped[obj_type].append(obj_copy)

    return deserialize_pdf_objects(signature_objects_grouped)


def convert_extraction_fields_to_api(fields: list[ExtractionFieldDomain]) -> list[ExtractionFieldAPI]:
    """Convert domain extraction fields to API format (bound_box → bbox)"""
    return [
        ExtractionFieldAPI(
            name=field.name,
            description=field.description,
            bbox=field.bound_box,
            page=field.page
        )
        for field in fields
    ]


def convert_extraction_fields_to_domain(fields: list[ExtractionFieldAPI]) -> list[ExtractionFieldDomain]:
    """Convert API extraction fields to domain format (bbox → bound_box)"""
    return [
        ExtractionFieldDomain(
            name=field.name,
            description=field.description,
            bound_box=field.bbox,
            page=field.page
        )
        for field in fields
    ]


# ========== Domain → API (Response) Conversions ==========

def convert_template_metadata(template: PdfTemplate) -> PdfTemplateMetadataResponse:
    """Convert domain PdfTemplate to API metadata response"""
    return PdfTemplateMetadataResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        source_pdf_id=template.source_pdf_id,
        current_version_id=template.current_version_id,
        status=template.status,
        usage_count=template.usage_count,
        last_used_at=template.last_used_at.isoformat() if template.last_used_at else None,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


def convert_version_list(template_id: int, version_list: list[tuple[int, int]]) -> GetTemplateVersionsResponse:
    """Convert list of (version_id, version_number) tuples to API response"""
    return GetTemplateVersionsResponse(
        template_id=template_id,
        versions=[
            VersionListItem(version_id=vid, version_number=vnum)
            for vid, vnum in version_list
        ]
    )


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
) -> ListPdfTemplatesResponse:
    """Convert list of domain summaries to API response"""
    return ListPdfTemplatesResponse(
        items=[convert_template_summary(s) for s in summaries]
    )


def convert_template_detail(
    template_with_version: PdfTemplateWithVersion,
    total_versions: int,
    version_summaries: list[PdfVersionSummary]
) -> PdfTemplateDetail:
    """Convert domain template with version to API detail response"""
    template = template_with_version.template
    current_version = template_with_version.current_version

    if not current_version:
        raise ValueError("Template must have a current version")

    return PdfTemplateDetail(
        id=template.id,
        name=template.name,
        description=template.description,
        source_pdf_id=template.source_pdf_id,
        status=template.status,
        current_version_id=template.current_version_id or 0,
        current_version=TemplateVersionDetail(
            version_id=current_version.id,
            version_num=current_version.version_number,
            usage_count=0,
            last_used_at=None,
            signature_objects=convert_pdf_objects_to_list(current_version.signature_objects),
            extraction_fields=convert_extraction_fields_to_api(current_version.extraction_fields),
            pipeline_definition_id=current_version.pipeline_definition_id
        ),
        total_versions=total_versions,
        available_versions=[
            VersionIdSummary(
                version_id=vs.id,
                version_num=vs.version_number,
                created_at=vs.created_at.isoformat()
            )
            for vs in version_summaries
        ]
    )


def convert_create_template_response(
    template: PdfTemplate,
    version_num: int,
    pipeline_id: int
) -> CreatePdfTemplateResponse:
    """Convert created template metadata to API response"""
    return CreatePdfTemplateResponse(
        id=template.id,
        name=template.name,
        status=template.status,
        current_version_id=template.current_version_id or 0,
        current_version_num=version_num,
        pipeline_definition_id=pipeline_id
    )


def convert_activate_template_response(template: PdfTemplate) -> ActivatePdfTemplateResponse:
    """Convert activated template to API response"""
    return ActivatePdfTemplateResponse(
        id=template.id,
        status=template.status,
        current_version_id=template.current_version_id or 0
    )


def convert_deactivate_template_response(template: PdfTemplate) -> DeactivatePdfTemplateResponse:
    """Convert deactivated template to API response"""
    return DeactivatePdfTemplateResponse(
        id=template.id,
        status=template.status,
        current_version_id=template.current_version_id or 0
    )


def convert_template_version(
    version: PdfTemplateVersion,
    is_current: bool
) -> GetTemplateVersionResponse:
    """Convert domain template version to API response"""
    return GetTemplateVersionResponse(
        version_id=version.id,
        template_id=version.template_id,
        version_num=version.version_number,
        usage_count=0,
        last_used_at=None,
        is_current=is_current,
        signature_objects=convert_pdf_objects_to_list(version.signature_objects),
        extraction_fields=convert_extraction_fields_to_api(version.extraction_fields),
        pipeline_definition_id=version.pipeline_definition_id
    )


# ========== API (Request) → Domain Conversions ==========

def convert_create_template_request(request: CreatePdfTemplateRequest) -> PdfTemplateCreate:
    """Convert API create request to domain PdfTemplateCreate"""
    return PdfTemplateCreate(
        name=request.name,
        description=request.description,
        signature_objects=convert_pdf_objects_from_list(request.signature_objects),
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
        signature_objects=convert_pdf_objects_from_list(request.signature_objects) if request.signature_objects else None,
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields) if request.extraction_fields else None,
        pipeline_state=request.pipeline_state.model_dump() if request.pipeline_state else None,
        visual_state=request.visual_state.model_dump() if request.visual_state else None
    )


def convert_update_template_response(
    template: PdfTemplate,
    version_num: int,
    pipeline_id: int
) -> UpdatePdfTemplateResponse:
    """Convert updated template metadata to API response"""
    return UpdatePdfTemplateResponse(
        id=template.id,
        name=template.name,
        status=template.status,
        current_version_id=template.current_version_id or 0,
        current_version_num=version_num,
        pipeline_definition_id=pipeline_id
    )
