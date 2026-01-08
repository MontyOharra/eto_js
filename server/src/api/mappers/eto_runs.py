"""
ETO Runs Mappers
Convert between domain dataclasses and API Pydantic models
"""
from typing import List, Optional

from shared.types.eto_runs import EtoRunListView, EtoRun, EtoRunDetailView
from shared.types.eto_sub_runs import EtoSubRunDetailView
from api.schemas.eto_runs import (
    EtoRunListItem,
    EtoPdfInfo,
    EtoSourceManual,
    EtoSourceEmail,
    EtoSource,
    EtoMatchedTemplate,
    EtoSubRunsSummary,
    EtoSubRunListItem,
    EtoSubRunDetail,
    EtoSubRunTemplate,
    EtoRunOverview,
    PageStatus,
    CreateEtoRunResponse,
    EtoRunDetail,
    EtoSubRunFullDetail,
    EtoSubRunExtractionDetail,
    EtoSubRunPipelineExecutionDetail,
    ExtractionResult,
    PipelineExecutionStep,
    PipelineExecutionStepError,
    TransformResult,
)

from features.modules.output_channel_definitions import get_channel_by_name

def eto_run_list_view_to_api(run: EtoRunListView) -> EtoRunListItem:
    """
    Convert domain EtoRunListView to API EtoRunListItem schema.

    Handles:
    - Datetime to ISO 8601 string conversion
    - Nested model construction (PDF, source, sub-runs summary)
    - Discriminated union for source (manual vs email)

    Args:
        run: EtoRunListView domain dataclass

    Returns:
        EtoRunListItem Pydantic model for API response
    """
    # Build PDF info
    pdf = EtoPdfInfo(
        id=run.pdf_file_id,
        original_filename=run.pdf_original_filename,
        file_size=run.pdf_file_size,
        page_count=run.pdf_page_count,
    )

    # Build source (discriminated union: manual or email)
    # Use source_type field instead of checking email_id
    if run.source_type == 'email':
        # Email source
        source: EtoSource = EtoSourceEmail(
            type="email",
            sender_email=run.email_sender_email or "",
            received_at=run.email_received_date.isoformat() if run.email_received_date else "",
            subject=run.email_subject,
            folder_name=run.email_folder_name or "",
        )
    else:
        # Manual upload source
        source = EtoSourceManual(
            type="manual",
            created_at=run.created_at.isoformat(),
        )

    # Build sub-runs summary with status counts
    sub_runs_summary = EtoSubRunsSummary(
        status_counts={
            "success": run.sub_run_success_count,
            "failure": run.sub_run_failure_count,
            "needs_template": run.sub_run_needs_template_count,
            "skipped": run.sub_run_skipped_count,
        }
    )

    # Build the main EtoRunListItem
    return EtoRunListItem(
        id=run.id,
        status=run.status,
        processing_step=run.processing_step,
        is_read=run.is_read,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        updated_at=run.updated_at.isoformat() if run.updated_at else None,
        last_processed_at=run.last_processed_at.isoformat() if run.last_processed_at else None,
        error_type=run.error_type,
        error_message=run.error_message,
        pdf=pdf,
        source=source,
        sub_runs_summary=sub_runs_summary,
        sub_runs=None,  # Not included in list view by default
    )


def eto_run_list_to_api(runs: List[EtoRunListView]) -> List[EtoRunListItem]:
    """
    Convert list of domain EtoRunListView to list of API EtoRunListItem.

    Args:
        runs: List of EtoRunListView domain dataclasses

    Returns:
        List of EtoRunListItem Pydantic models for API response
    """
    return [eto_run_list_view_to_api(run) for run in runs]


def eto_run_to_create_response(run: EtoRun) -> CreateEtoRunResponse:
    """
    Convert domain EtoRun to CreateEtoRunResponse API schema.

    Used for POST /eto-runs endpoint response.

    Args:
        run: EtoRun domain dataclass (newly created)

    Returns:
        CreateEtoRunResponse Pydantic model for API response
    """
    return CreateEtoRunResponse(
        id=run.id,
        status=run.status,
        pdf_file_id=run.pdf_file_id,
        started_at=run.started_at.isoformat() if run.started_at else None,
        created_at=run.created_at.isoformat(),
    )


def eto_sub_run_detail_to_api(
    sub_run: EtoSubRunDetailView,
    customer_name: Optional[str] = None
) -> EtoSubRunDetail:
    """
    Convert domain EtoSubRunDetailView to API EtoSubRunDetail schema.

    Simplified version - only includes data needed for detail view UI.

    Args:
        sub_run: EtoSubRunDetailView domain dataclass
        customer_name: Customer name from Access DB (optional)

    Returns:
        EtoSubRunDetail Pydantic model for API response
    """

    # Build template info (None for needs_template sub-runs)
    template: Optional[EtoSubRunTemplate] = None
    if sub_run.template_id is not None:
        template = EtoSubRunTemplate(
            id=sub_run.template_id,
            name=sub_run.template_name or "",
            customer_name=customer_name,
        )

    # Convert output channel data to transform results
    transform_results: List[TransformResult] = []
    if sub_run.output_channel_data:
        # Build results with hawb first, then other fields
        data = sub_run.output_channel_data

        # Add hawb first if present
        if "hawb" in data and data["hawb"]:
            channel = get_channel_by_name("hawb")
            label = channel.label if channel else "HAWB"
            transform_results.append(TransformResult(
                field_name=label,
                value=str(data["hawb"])
            ))

        # Add remaining fields (excluding hawb)
        for field_name, value in data.items():
            if field_name == "hawb" or value is None or value == "":
                continue
            channel = get_channel_by_name(field_name)
            label = channel.label if channel else field_name.replace("_", " ").title()
            transform_results.append(TransformResult(
                field_name=label,
                value=str(value)
            ))

    return EtoSubRunDetail(
        id=sub_run.id,
        status=sub_run.status,
        matched_pages=sub_run.matched_pages,
        template=template,
        transform_results=transform_results,
        error_message=sub_run.error_message,
    )


def eto_run_detail_to_api(
    detail: EtoRunDetailView,
    customer_names: Optional[dict] = None
) -> EtoRunDetail:
    """
    Convert domain EtoRunDetailView to EtoRunDetail API schema.

    Used for GET /eto-runs/{id} endpoint response.

    Handles:
    - Datetime to ISO 8601 string conversion
    - Nested model construction (PDF, source, overview, page_statuses)
    - Sub-run list conversion

    Args:
        detail: EtoRunDetailView domain dataclass with all related data
        customer_names: Dict mapping customer_id to customer_name (from Access DB)

    Returns:
        EtoRunDetail Pydantic model for API response
    """
    customer_names = customer_names or {}

    # Build PDF info
    pdf = EtoPdfInfo(
        id=detail.pdf_file_id,
        original_filename=detail.pdf_original_filename,
        file_size=detail.pdf_file_size,
        page_count=detail.pdf_page_count or 0,
    )

    # Build source (discriminated union: manual or email)
    # Use source_type field instead of checking email_id
    if detail.source_type == 'email':
        # Email source
        source: EtoSource = EtoSourceEmail(
            type="email",
            sender_email=detail.email_sender_email or "",
            received_at=detail.email_received_date.isoformat() if detail.email_received_date else "",
            subject=detail.email_subject,
            folder_name=detail.email_folder_name or "",
        )
    else:
        # Manual upload source
        source = EtoSourceManual(
            type="manual",
            created_at=detail.created_at.isoformat(),
        )

    # Convert all sub-runs to API format with customer names
    sub_runs = [
        eto_sub_run_detail_to_api(
            sub_run,
            customer_names.get(sub_run.template_customer_id) if sub_run.template_customer_id else None
        )
        for sub_run in detail.sub_runs
    ]

    # Compute overview stats
    unique_template_ids = set(
        sr.template_id for sr in detail.sub_runs if sr.template_id is not None
    )
    processing_time_ms = None
    if detail.started_at and detail.completed_at:
        delta = detail.completed_at - detail.started_at
        processing_time_ms = int(delta.total_seconds() * 1000)

    overview = EtoRunOverview(
        templates_matched_count=len(unique_template_ids),
        processing_time_ms=processing_time_ms,
    )

    # Build page statuses from sub-runs
    page_statuses: List[PageStatus] = []
    for sr in detail.sub_runs:
        for page in sr.matched_pages:
            page_statuses.append(PageStatus(
                page_number=page,
                status=sr.status,
                sub_run_id=sr.id,
            ))
    # Sort by page number
    page_statuses.sort(key=lambda p: p.page_number)

    # Build the main EtoRunDetail
    return EtoRunDetail(
        id=detail.id,
        status=detail.status,
        processing_step=detail.processing_step,
        started_at=detail.started_at.isoformat() if detail.started_at else None,
        completed_at=detail.completed_at.isoformat() if detail.completed_at else None,
        error_type=detail.error_type,
        error_message=detail.error_message,
        pdf=pdf,
        source=source,
        overview=overview,
        sub_runs=sub_runs,
        page_statuses=page_statuses,
    )


def eto_sub_run_full_detail_to_api(
    sub_run: EtoSubRunDetailView,
    customer_name: Optional[str] = None
) -> EtoSubRunFullDetail:
    """
    Convert domain EtoSubRunDetailView to API EtoSubRunFullDetail schema.

    Used for GET /eto-runs/sub-runs/{id} endpoint response.
    This is the full detail view including extraction and pipeline execution data.

    Args:
        sub_run: EtoSubRunDetailView domain dataclass with all stage data
        customer_name: Customer name from Access DB (optional)

    Returns:
        EtoSubRunFullDetail Pydantic model for API response
    """
    # Build PDF info
    pdf = EtoPdfInfo(
        id=sub_run.pdf_file_id,
        original_filename=sub_run.pdf_original_filename,
        file_size=sub_run.pdf_file_size,
        page_count=sub_run.pdf_page_count or 0,
    )

    # Build template info (None for needs_template sub-runs)
    template: Optional[EtoSubRunTemplate] = None
    if sub_run.template_id is not None:
        template = EtoSubRunTemplate(
            id=sub_run.template_id,
            name=sub_run.template_name or "",
            customer_name=customer_name,
        )

    # Build extraction stage detail (if exists)
    extraction_detail: Optional[EtoSubRunExtractionDetail] = None
    if sub_run.extraction:
        # Convert extracted_data to ExtractionResult list
        extraction_results: List[ExtractionResult] = []
        if sub_run.extraction.extracted_data:
            for field_data in sub_run.extraction.extracted_data:
                extraction_results.append(ExtractionResult(
                    name=field_data.get("name", ""),
                    description=field_data.get("description"),
                    bbox=field_data.get("bbox", [0, 0, 0, 0]),
                    page=field_data.get("page", 1),
                    extracted_value=field_data.get("extracted_value", ""),
                ))

        extraction_detail = EtoSubRunExtractionDetail(
            status=sub_run.extraction.status,
            started_at=sub_run.extraction.started_at.isoformat() if sub_run.extraction.started_at else None,
            completed_at=sub_run.extraction.completed_at.isoformat() if sub_run.extraction.completed_at else None,
            extraction_results=extraction_results,
        )

    # Build pipeline execution stage detail (if exists)
    pipeline_detail: Optional[EtoSubRunPipelineExecutionDetail] = None
    if sub_run.pipeline_execution:
        # Convert steps to API format
        steps = []
        if sub_run.pipeline_execution.steps:
            for step in sub_run.pipeline_execution.steps:
                error_data = None
                error = step.error
                if error:
                    # Error is stored as a string like "ExceptionType: message"
                    # Parse it into type and message components
                    if isinstance(error, str):
                        if ": " in error:
                            error_type, error_message = error.split(": ", 1)
                        else:
                            error_type = "Error"
                            error_message = error
                        error_data = PipelineExecutionStepError(
                            type=error_type,
                            message=error_message,
                            details=None,
                        )
                    elif isinstance(error, dict):
                        # Handle dict format if it exists (for future compatibility)
                        error_data = PipelineExecutionStepError(
                            type=error.get("type", "Error"),
                            message=error.get("message", str(error)),
                            details=error.get("details"),
                        )
                steps.append(PipelineExecutionStep(
                    id=step.id,
                    step_number=step.step_number,
                    module_instance_id=step.module_instance_id,
                    inputs=step.inputs,
                    outputs=step.outputs,
                    error=error_data,
                ))

        pipeline_detail = EtoSubRunPipelineExecutionDetail(
            status=sub_run.pipeline_execution.status,
            started_at=sub_run.pipeline_execution.started_at.isoformat() if sub_run.pipeline_execution.started_at else None,
            completed_at=sub_run.pipeline_execution.completed_at.isoformat() if sub_run.pipeline_execution.completed_at else None,
            pipeline_definition_id=sub_run.pipeline_execution.pipeline_definition_id,
            steps=steps,
        )

    # Build the main EtoSubRunFullDetail
    return EtoSubRunFullDetail(
        id=sub_run.id,
        eto_run_id=sub_run.eto_run_id,
        status=sub_run.status,
        matched_pages=sub_run.matched_pages,
        template=template,
        template_version_id=sub_run.template_version_id,
        error_type=sub_run.error_type,
        error_message=sub_run.error_message,
        error_details=sub_run.error_details,
        started_at=sub_run.started_at.isoformat() if sub_run.started_at else None,
        completed_at=sub_run.completed_at.isoformat() if sub_run.completed_at else None,
        pdf=pdf,
        stage_data_extraction=extraction_detail,
        stage_pipeline_execution=pipeline_detail,
    )
