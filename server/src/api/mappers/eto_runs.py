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
)


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

    # Calculate sub-runs summary from counts
    total_count = (
        run.sub_run_success_count +
        run.sub_run_failure_count +
        run.sub_run_needs_template_count +
        run.sub_run_skipped_count
    )

    # Matched = has template (success + failure + processing)
    # For now, we estimate matched as total - needs_template
    matched_count = total_count - run.sub_run_needs_template_count

    # Calculate page counts from page arrays
    pages_matched_count = len(run.pages_matched)
    pages_unmatched_count = len(run.pages_unmatched)

    sub_runs_summary = EtoSubRunsSummary(
        total_count=total_count,
        matched_count=matched_count,
        needs_template_count=run.sub_run_needs_template_count,
        success_count=run.sub_run_success_count,
        failure_count=run.sub_run_failure_count,
        processing_count=0,  # TODO: Add processing count to EtoRunListView
        not_started_count=0,  # TODO: Add not_started count to EtoRunListView
        pages_matched_count=pages_matched_count,
        pages_unmatched_count=pages_unmatched_count,
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


def eto_sub_run_detail_to_api(sub_run: EtoSubRunDetailView) -> EtoSubRunDetail:
    """
    Convert domain EtoSubRunDetailView to API EtoSubRunDetail schema.

    Simplified version - only includes data needed for detail view UI.

    Args:
        sub_run: EtoSubRunDetailView domain dataclass

    Returns:
        EtoSubRunDetail Pydantic model for API response
    """
    # Build template info (None for needs_template sub-runs)
    template: Optional[EtoSubRunTemplate] = None
    if sub_run.template_id is not None:
        template = EtoSubRunTemplate(
            id=sub_run.template_id,
            name=sub_run.template_name or "",
        )

    return EtoSubRunDetail(
        id=sub_run.id,
        status=sub_run.status,
        matched_pages=sub_run.matched_pages,
        template=template,
        transform_results=[],  # Empty for now - future functionality
        error_message=sub_run.error_message,
    )


def eto_run_detail_to_api(detail: EtoRunDetailView) -> EtoRunDetail:
    """
    Convert domain EtoRunDetailView to EtoRunDetail API schema.

    Used for GET /eto-runs/{id} endpoint response.

    Handles:
    - Datetime to ISO 8601 string conversion
    - Nested model construction (PDF, source, overview, page_statuses)
    - Sub-run list conversion

    Args:
        detail: EtoRunDetailView domain dataclass with all related data

    Returns:
        EtoRunDetail Pydantic model for API response
    """
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

    # Convert all sub-runs to API format
    sub_runs = [eto_sub_run_detail_to_api(sub_run) for sub_run in detail.sub_runs]

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


def eto_sub_run_full_detail_to_api(sub_run: EtoSubRunDetailView) -> EtoSubRunFullDetail:
    """
    Convert domain EtoSubRunDetailView to API EtoSubRunFullDetail schema.

    Used for GET /eto-runs/sub-runs/{id} endpoint response.
    This is the full detail view including extraction and pipeline execution data.

    Args:
        sub_run: EtoSubRunDetailView domain dataclass with all stage data

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
                    error_data = PipelineExecutionStepError(
                        type=error.get("type", ""),
                        message=error.get("message", ""),
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
