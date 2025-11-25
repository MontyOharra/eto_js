"""
ETO Runs Mappers
Convert between domain dataclasses and API Pydantic models
"""
import json
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
    EtoSubRunExtraction,
    EtoSubRunPipelineExecution,
    EtoSubRunPipelineExecutionStep,
    CreateEtoRunResponse,
    EtoRunDetail,
)
from api.schemas.pdf_templates import ExtractedFieldResult


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
    if run.email_id is not None:
        # Email source
        source: EtoSource = EtoSourceEmail(
            type="email",
            sender_email=run.email_sender_email or "",
            received_date=run.email_received_date.isoformat() if run.email_received_date else "",
            subject=run.email_subject,
            folder_name=run.email_folder_name or "",
        )
    else:
        # Manual upload source
        source = EtoSourceManual(type="manual")

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

    Handles:
    - Template info construction
    - Extraction stage conversion
    - Pipeline execution stage conversion with steps

    Args:
        sub_run: EtoSubRunDetailView domain dataclass

    Returns:
        EtoSubRunDetail Pydantic model for API response
    """
    # Build template info (None for unmatched groups)
    template: Optional[EtoMatchedTemplate] = None
    if sub_run.template_id is not None:
        template = EtoMatchedTemplate(
            template_id=sub_run.template_id,
            template_name=sub_run.template_name or "",
            version_id=sub_run.template_version_id or 0,
            version_num=sub_run.template_version_num or 0,
        )

    # Build extraction stage (optional)
    extraction: Optional[EtoSubRunExtraction] = None
    if sub_run.extraction:
        # Convert extracted_data list to ExtractedFieldResult list
        extraction_results: Optional[List[ExtractedFieldResult]] = None
        if sub_run.extraction.extracted_data:
            extraction_results = [
                ExtractedFieldResult(
                    name=result.get("name", ""),
                    description=result.get("description"),
                    bbox=tuple(result.get("bbox", [0, 0, 0, 0])),  # type: ignore
                    page=result.get("page", 0),
                    extracted_value=result.get("extracted_value", "")
                )
                for result in sub_run.extraction.extracted_data
            ]

        extraction = EtoSubRunExtraction(
            id=0,  # TODO: Add id to EtoRunExtractionDetailView
            status=sub_run.extraction.status,
            extraction_results=extraction_results,
            error_message=None,  # TODO: Add error_message to EtoRunExtractionDetailView
            started_at=sub_run.extraction.started_at.isoformat() if sub_run.extraction.started_at else None,
            completed_at=sub_run.extraction.completed_at.isoformat() if sub_run.extraction.completed_at else None,
        )

    # Build pipeline execution stage (optional)
    pipeline_execution: Optional[EtoSubRunPipelineExecution] = None
    if sub_run.pipeline_execution:
        # Convert steps to API format
        steps_list: Optional[List[EtoSubRunPipelineExecutionStep]] = None
        if sub_run.pipeline_execution.steps:
            steps_list = [
                EtoSubRunPipelineExecutionStep(
                    id=step.id,
                    step_number=step.step_number,
                    module_instance_id=step.module_instance_id,
                    inputs=step.inputs,
                    outputs=step.outputs,
                    error=json.dumps(step.error) if step.error else None,
                )
                for step in sub_run.pipeline_execution.steps
            ]

        # executed_actions is already a dict, convert to list if needed
        executed_actions = None
        if sub_run.pipeline_execution.executed_actions:
            if isinstance(sub_run.pipeline_execution.executed_actions, list):
                executed_actions = sub_run.pipeline_execution.executed_actions
            elif isinstance(sub_run.pipeline_execution.executed_actions, dict):
                executed_actions = [sub_run.pipeline_execution.executed_actions]

        pipeline_execution = EtoSubRunPipelineExecution(
            id=0,  # TODO: Add id to EtoRunPipelineExecutionDetailView
            status=sub_run.pipeline_execution.status,
            executed_actions=executed_actions,
            error_message=None,  # TODO: Add error_message to EtoRunPipelineExecutionDetailView
            started_at=sub_run.pipeline_execution.started_at.isoformat() if sub_run.pipeline_execution.started_at else None,
            completed_at=sub_run.pipeline_execution.completed_at.isoformat() if sub_run.pipeline_execution.completed_at else None,
            steps=steps_list,
        )

    return EtoSubRunDetail(
        id=sub_run.id,
        sequence=None,  # TODO: Add sequence to EtoSubRunDetailView if needed
        status=sub_run.status,
        matched_pages=sub_run.matched_pages,
        is_unmatched_group=sub_run.is_unmatched_group,
        error_type=sub_run.error_type,
        error_message=sub_run.error_message,
        started_at=sub_run.started_at.isoformat() if sub_run.started_at else None,
        completed_at=sub_run.completed_at.isoformat() if sub_run.completed_at else None,
        template=template,
        extraction=extraction,
        pipeline_execution=pipeline_execution,
    )


def eto_run_detail_to_api(detail: EtoRunDetailView) -> EtoRunDetail:
    """
    Convert domain EtoRunDetailView to EtoRunDetail API schema.

    Used for GET /eto-runs/{id} endpoint response.

    Handles:
    - Datetime to ISO 8601 string conversion
    - Nested model construction (PDF, source)
    - Sub-run list conversion with full stage details

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
        page_count=detail.pdf_page_count,
    )

    # Build source (discriminated union: manual or email)
    if detail.email_id is not None:
        # Email source
        source: EtoSource = EtoSourceEmail(
            type="email",
            sender_email=detail.email_sender_email or "",
            received_date=detail.email_received_date.isoformat() if detail.email_received_date else "",
            subject=detail.email_subject,
            folder_name=detail.email_folder_name or "",
        )
    else:
        # Manual upload source
        source = EtoSourceManual(type="manual")

    # Convert all sub-runs to API format
    sub_runs = [eto_sub_run_detail_to_api(sub_run) for sub_run in detail.sub_runs]

    # Build the main EtoRunDetail
    return EtoRunDetail(
        id=detail.id,
        status=detail.status,
        processing_step=detail.processing_step,
        started_at=detail.started_at.isoformat() if detail.started_at else None,
        completed_at=detail.completed_at.isoformat() if detail.completed_at else None,
        error_type=detail.error_type,
        error_message=detail.error_message,
        error_details=detail.error_details,
        pdf=pdf,
        source=source,
        sub_runs=sub_runs,
    )
