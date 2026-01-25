"""
PDF Templates Mappers

Helper functions for building API responses from domain types.
Since domain and API types are both Pydantic, most conversions are trivial.
These mappers primarily handle:
- Adding enriched fields (customer_name from Access DB)
- Building response types from multiple domain sources
"""
from shared.types.pdf_templates import (
    PdfTemplateListView,
    PdfTemplate,
    PdfTemplateVersion,
    PdfTemplateCreate,
    PdfTemplateUpdate,
    TemplateSimulateData,
    TemplateSimulateResult,
)
from api.schemas.pdf_templates import (
    TemplateListItem,
    TemplateVersionSummary,
    PdfTemplateResponse,
    VersionListItem,
    CreatePdfTemplateRequest,
    UpdatePdfTemplateRequest,
    GetTemplateVersionResponse,
    SimulateTemplateRequest,
    SimulateTemplateResponse,
    ExtractedFieldResult,
)


# ========== Response Builders ==========

def build_template_response(
    template: PdfTemplate,
    version_list: list[tuple[int, int]],
    customer_name: str | None = None
) -> PdfTemplateResponse:
    """Build API template response with version navigation"""
    return PdfTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        customer_id=template.customer_id,
        customer_name=customer_name,
        status=template.status,
        is_autoskip=template.is_autoskip,
        source_pdf_id=template.source_pdf_id,
        current_version_id=template.current_version_id,
        versions=[
            VersionListItem(version_id=vid, version_number=vnum)
            for vid, vnum in version_list
        ]
    )


def build_template_list_item(
    summary: PdfTemplateListView,
    customer_name: str | None = None
) -> TemplateListItem:
    """Build API list item from domain summary"""
    return TemplateListItem(
        id=summary.id,
        name=summary.name,
        description=summary.description,
        customer_id=summary.customer_id,
        customer_name=customer_name,
        status=summary.status,
        is_autoskip=summary.is_autoskip,
        source_pdf_id=summary.source_pdf_id,
        page_count=summary.page_count,
        current_version=TemplateVersionSummary(
            version_id=summary.current_version_id or 0,
            version_num=summary.current_version_number or 0,
            usage_count=summary.version_usage_count or 0
        ),
        total_versions=summary.version_count or 0
    )


def build_template_list(
    summaries: list[PdfTemplateListView],
    customer_names: dict[int, str] | None = None
) -> list[TemplateListItem]:
    """Build API list from domain summaries with customer names"""
    customer_names = customer_names or {}
    return [
        build_template_list_item(s, customer_names.get(s.customer_id) if s.customer_id else None)
        for s in summaries
    ]


def build_version_response(
    version: PdfTemplateVersion,
    is_current: bool
) -> GetTemplateVersionResponse:
    """Build API version response from domain version"""
    return GetTemplateVersionResponse(
        version_id=version.id,
        template_id=version.template_id,
        version_num=version.version_number,
        source_pdf_id=version.source_pdf_id,
        is_current=is_current,
        signature_objects=version.signature_objects,
        extraction_fields=version.extraction_fields,
        pipeline_definition_id=version.pipeline_definition_id
    )


# ========== Request Converters ==========

def to_template_create(request: CreatePdfTemplateRequest) -> PdfTemplateCreate:
    """Convert API create request to domain type"""
    return PdfTemplateCreate(
        name=request.name,
        description=request.description,
        customer_id=request.customer_id,
        signature_objects=request.signature_objects,
        extraction_fields=list(request.extraction_fields),
        pipeline_state=request.pipeline_state,
        visual_state=request.visual_state,
        source_pdf_id=request.source_pdf_id,
        is_autoskip=request.is_autoskip
    )


def to_template_update(request: UpdatePdfTemplateRequest) -> PdfTemplateUpdate:
    """Convert API update request to domain type"""
    return PdfTemplateUpdate(
        name=request.name,
        description=request.description,
        customer_id=request.customer_id,
        is_autoskip=request.is_autoskip,
        signature_objects=request.signature_objects,
        extraction_fields=list(request.extraction_fields) if request.extraction_fields else None,
        pipeline_state=request.pipeline_state,
        visual_state=request.visual_state
    )


def to_simulate_data(request: SimulateTemplateRequest) -> TemplateSimulateData:
    """Convert API simulate request to domain type"""
    return TemplateSimulateData(
        pdf_objects=request.pdf_objects,
        extraction_fields=list(request.extraction_fields),
        pipeline_state=request.pipeline_state
    )


def build_simulate_response(result: TemplateSimulateResult) -> SimulateTemplateResponse:
    """Build API simulate response from domain result"""
    extraction_results = [
        ExtractedFieldResult(
            name=field.name,
            description=field.description,
            bbox=field.bbox,
            page=field.page,
            extracted_value=result.extracted_data.get(field.name, "")
        )
        for field in result.extraction_fields
    ]

    return SimulateTemplateResponse(
        extraction_results=extraction_results,
        pipeline_status=result.execution_result.status,
        pipeline_steps=list(result.execution_result.steps),
        output_channel_values=result.execution_result.output_channel_values,
        pipeline_error=result.execution_result.error
    )
