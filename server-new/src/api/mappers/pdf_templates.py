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
    ExtractionField,
)
from shared.types.pdf_files import PdfObjects, TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table
from api.schemas.pdf_templates import (
    TemplateListItem,
    TemplateVersionSummary,
    PdfTemplate as PdfTemplatePydantic,
    VersionListItem,
    CreatePdfTemplateRequest,
    UpdatePdfTemplateRequest,
    GetTemplateVersionResponse,
    ExtractionField as ExtractionFieldPydantic,
)
from api.schemas.pdf_files import (
    PdfObjects as PdfObjectsPydantic,
    TextWord as TextWordPydantic,
    TextLine as TextLinePydantic,
    GraphicRect as GraphicRectPydantic,
    GraphicLine as GraphicLinePydantic,
    GraphicCurve as GraphicCurvePydantic,
    Image as ImagePydantic,
    Table as TablePydantic,
)

# ========== Helper Functions ==========

def convert_pdf_objects_to_api(objects: PdfObjects) -> PdfObjectsPydantic:
    """Convert domain PdfObjects dataclass to API PdfObjects Pydantic schema"""
    return PdfObjectsPydantic(
        text_words=[
            TextWordPydantic(
                page=obj.page,
                bbox=obj.bbox,
                text=obj.text,
                fontname=obj.fontname,
                fontsize=obj.fontsize
            )
            for obj in objects.text_words
        ],
        text_lines=[
            TextLinePydantic(page=obj.page, bbox=obj.bbox)
            for obj in objects.text_lines
        ],
        graphic_rects=[
            GraphicRectPydantic(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_rects
        ],
        graphic_lines=[
            GraphicLinePydantic(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_lines
        ],
        graphic_curves=[
            GraphicCurvePydantic(
                page=obj.page,
                bbox=obj.bbox,
                points=list(obj.points),
                linewidth=obj.linewidth
            )
            for obj in objects.graphic_curves
        ],
        images=[
            ImagePydantic(
                page=obj.page,
                bbox=obj.bbox,
                format=obj.format,
                colorspace=obj.colorspace,
                bits=obj.bits
            )
            for obj in objects.images
        ],
        tables=[
            TablePydantic(
                page=obj.page,
                bbox=obj.bbox,
                rows=obj.rows,
                cols=obj.cols
            )
            for obj in objects.tables
        ],
    )


def convert_pdf_objects_to_domain(objects_schema: PdfObjectsPydantic) -> PdfObjects:
    """Convert API PdfObjects Pydantic schema to domain PdfObjects dataclass"""
    return PdfObjects(
        text_words=[
            TextWord(
                page=obj.page,
                bbox=obj.bbox,
                text=obj.text,
                fontname=obj.fontname,
                fontsize=obj.fontsize
            )
            for obj in objects_schema.text_words
        ],
        text_lines=[
            TextLine(page=obj.page, bbox=obj.bbox)
            for obj in objects_schema.text_lines
        ],
        graphic_rects=[
            GraphicRect(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects_schema.graphic_rects
        ],
        graphic_lines=[
            GraphicLine(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects_schema.graphic_lines
        ],
        graphic_curves=[
            GraphicCurve(
                page=obj.page,
                bbox=obj.bbox,
                points=obj.points,
                linewidth=obj.linewidth
            )
            for obj in objects_schema.graphic_curves
        ],
        images=[
            Image(
                page=obj.page,
                bbox=obj.bbox,
                format=obj.format,
                colorspace=obj.colorspace,
                bits=obj.bits
            )
            for obj in objects_schema.images
        ],
        tables=[
            Table(page=obj.page, bbox=obj.bbox, rows=obj.rows, cols=obj.cols)
            for obj in objects_schema.tables
        ],
    )


def convert_extraction_fields_to_api(fields: list[ExtractionField]) -> list[ExtractionFieldPydantic]:
    """Convert domain extraction fields to API format"""
    return [
        ExtractionFieldPydantic(
            name=field.name,
            description=field.description,
            bbox=field.bbox,
            page=field.page
        )
        for field in fields
    ]


def convert_extraction_fields_to_domain(fields: list[ExtractionFieldPydantic]) -> list[ExtractionField]:
    """Convert API extraction fields to domain format"""
    return [
        ExtractionField(
            name=field.name,
            description=field.description,
            bbox=field.bbox,
            page=field.page
        )
        for field in fields
    ]


# ========== Domain → API (Response) Conversions ==========

def convert_pdf_template(
    template: PdfTemplate,
    version_list: list[tuple[int, int]]
) -> PdfTemplatePydantic:
    """Convert domain PdfTemplate to API PdfTemplate with version navigation (excludes audit timestamps)"""
    return PdfTemplatePydantic(
        id=template.id,
        name=template.name,
        description=template.description,
        status=template.status,
        source_pdf_id=template.source_pdf_id,
        current_version_id=template.current_version_id,
        versions=convert_version_list(version_list)
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
        total_versions=summary.version_count or 0
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
    """Convert domain template version to API response (excludes audit timestamps)"""
    return GetTemplateVersionResponse(
        version_id=version.id,
        template_id=version.template_id,
        version_num=version.version_number,
        source_pdf_id=version.source_pdf_id,
        is_current=is_current,
        signature_objects=convert_pdf_objects_to_api(version.signature_objects),
        extraction_fields=convert_extraction_fields_to_api(version.extraction_fields),
        pipeline_definition_id=version.pipeline_definition_id
    )


# ========== API (Request) → Domain Conversions ==========

def convert_create_template_request(request: CreatePdfTemplateRequest) -> PdfTemplateCreate:
    """Convert API create request to domain PdfTemplateCreate"""
    # Convert visual_state Dict[str, Position] to dict with plain dicts
    visual_state_dict = {
        node_id: {"x": pos.x, "y": pos.y}
        for node_id, pos in request.visual_state.items()
    }

    return PdfTemplateCreate(
        name=request.name,
        description=request.description,
        signature_objects=convert_pdf_objects_to_domain(request.signature_objects),
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields),
        pipeline_state=request.pipeline_state.model_dump(),
        visual_state=visual_state_dict,
        source_pdf_id=request.source_pdf_id or 0
    )


def convert_update_template_request(request: UpdatePdfTemplateRequest) -> PdfTemplateUpdate:
    """
    Convert API update request to unified domain PdfTemplateUpdate.

    All fields (metadata + wizard data + pipeline) are included in a single object.
    Service layer will detect what changed and handle versioning/pipeline creation accordingly.
    """
    # Convert visual_state if present
    visual_state_dict = None
    if request.visual_state is not None:
        visual_state_dict = {
            node_id: {"x": pos.x, "y": pos.y}
            for node_id, pos in request.visual_state.items()
        }

    return PdfTemplateUpdate(
        name=request.name,
        description=request.description,
        signature_objects=convert_pdf_objects_to_domain(request.signature_objects) if request.signature_objects else None,
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields) if request.extraction_fields else None,
        pipeline_state=request.pipeline_state.model_dump() if request.pipeline_state else None,
        visual_state=visual_state_dict
    )


# ========== Simulation Conversions ==========

def convert_simulate_request(request) -> Any:
    """Convert API SimulateTemplateRequest to domain TemplateSimulateData"""
    from shared.types.pdf_templates import TemplateSimulateData
    from api.mappers.pipelines import convert_pipeline_state_to_domain

    return TemplateSimulateData(
        pdf_objects=convert_pdf_objects_to_domain(request.pdf_objects),
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields),
        pipeline_state=convert_pipeline_state_to_domain(request.pipeline_state)
    )


def convert_simulate_result_to_api(result: Any):
    """Convert domain TemplateSimulateResult to API SimulateTemplateResponse"""
    from api.schemas.pdf_templates import SimulateTemplateResponse, ExtractedFieldResult

    # Build extraction results with bbox info for visual display
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

    # Convert domain PipelineExecutionStepResult to API ExecutionStepResult
    from api.schemas.pipelines import ExecutionStepResult

    pipeline_steps = [
        ExecutionStepResult(
            module_instance_id=step.module_instance_id,
            step_number=step.step_number,
            inputs=step.inputs,
            outputs=step.outputs,
            error=step.error
        )
        for step in result.execution_result.steps
    ]

    return SimulateTemplateResponse(
        extraction_results=extraction_results,
        pipeline_status=result.execution_result.status,
        pipeline_steps=pipeline_steps,
        pipeline_actions=result.execution_result.executed_actions,
        pipeline_error=result.execution_result.error
    )


