"""
ETO Runs Mappers
Convert between domain dataclasses and API Pydantic models
"""
import json
from typing import List, Optional, Any

from shared.types.eto_runs import EtoRunListView, EtoRun, EtoRunDetailView
from api.schemas.eto_runs import (
    EtoRunListItem,
    EtoPdfInfo,
    EtoSourceManual,
    EtoSourceEmail,
    EtoSource,
    EtoMatchedTemplate,
    CreateEtoRunResponse,
    EtoRunDetail,
    EtoStageTemplateMatching,
    EtoStageDataExtraction,
    EtoStagePipelineExecution,
)


def eto_run_list_view_to_api(run: EtoRunListView) -> EtoRunListItem:
    """
    Convert domain EtoRunListView to API EtoRunListItem schema.

    Handles:
    - Datetime to ISO 8601 string conversion
    - Nested model construction (PDF, source, template)
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
            sender_email=run.email_sender_email or "",  # Shouldn't be None if email_id exists
            received_date=run.email_received_date.isoformat() if run.email_received_date else "",
            subject=run.email_subject,
            folder_name=run.email_folder_name or "",  # Shouldn't be None if email_id exists
        )
    else:
        # Manual upload source
        source = EtoSourceManual(type="manual")

    # Build matched template (optional)
    matched_template: EtoMatchedTemplate | None = None
    if run.template_id is not None:
        matched_template = EtoMatchedTemplate(
            template_id=run.template_id,
            template_name=run.template_name or "",  # Shouldn't be None if template_id exists
            version_id=run.template_version_id or 0,  # Shouldn't be None if template_id exists
            version_num=run.template_version_num or 0,  # Shouldn't be None if template_id exists
        )

    # Build the main EtoRunListItem
    return EtoRunListItem(
        id=run.id,
        status=run.status,
        processing_step=run.processing_step,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error_type=run.error_type,
        error_message=run.error_message,
        pdf=pdf,
        source=source,
        matched_template=matched_template,
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


def eto_run_detail_to_api(detail: EtoRunDetailView) -> EtoRunDetail:
    """
    Convert domain EtoRunDetailView to EtoRunDetail API schema.

    Used for GET /eto-runs/{id} endpoint response.

    Handles:
    - Datetime to ISO 8601 string conversion
    - JSON string parsing for extracted_data and executed_actions
    - Nested model construction (PDF, source, stages)
    - Discriminated union for source (manual vs email)

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

    # Build stage data (optional - depends on run progress)
    stage_template_matching: Optional[EtoStageTemplateMatching] = None
    stage_data_extraction: Optional[EtoStageDataExtraction] = None
    stage_pipeline_execution: Optional[EtoStagePipelineExecution] = None

    # Stage 1: Template matching
    if detail.template_matching:
        stage_template_matching = EtoStageTemplateMatching(
            status=detail.template_matching.status,
            matched_template_version_id=detail.template_matching.matched_template_version_id,
            matched_template_name=detail.matched_template_name,
            matched_version_number=detail.matched_template_version_num,
            started_at=detail.template_matching.started_at.isoformat() if detail.template_matching.started_at else None,
            completed_at=detail.template_matching.completed_at.isoformat() if detail.template_matching.completed_at else None,
        )

    # Stage 2: Data extraction
    if detail.extraction:
        # Parse JSON string to dict
        extracted_data_dict: Optional[dict[str, Any]] = None
        if detail.extraction.extracted_data:
            try:
                extracted_data_dict = json.loads(detail.extraction.extracted_data)
            except json.JSONDecodeError:
                # If JSON parsing fails, leave as None
                extracted_data_dict = None

        stage_data_extraction = EtoStageDataExtraction(
            status=detail.extraction.status,
            extracted_data=extracted_data_dict,
            started_at=detail.extraction.started_at.isoformat() if detail.extraction.started_at else None,
            completed_at=detail.extraction.completed_at.isoformat() if detail.extraction.completed_at else None,
        )

    # Stage 3: Pipeline execution
    if detail.pipeline_execution:
        # Parse JSON string to dict
        executed_actions_dict: Optional[dict[str, Any]] = None
        if detail.pipeline_execution.executed_actions:
            try:
                executed_actions_dict = json.loads(detail.pipeline_execution.executed_actions)
            except json.JSONDecodeError:
                # If JSON parsing fails, leave as None
                executed_actions_dict = None

        stage_pipeline_execution = EtoStagePipelineExecution(
            status=detail.pipeline_execution.status,
            executed_actions=executed_actions_dict,
            started_at=detail.pipeline_execution.started_at.isoformat() if detail.pipeline_execution.started_at else None,
            completed_at=detail.pipeline_execution.completed_at.isoformat() if detail.pipeline_execution.completed_at else None,
        )

    # Build the main EtoRunDetail
    return EtoRunDetail(
        # Core run data
        id=detail.run.id,
        status=detail.run.status,
        processing_step=detail.run.processing_step,
        started_at=detail.run.started_at.isoformat() if detail.run.started_at else None,
        completed_at=detail.run.completed_at.isoformat() if detail.run.completed_at else None,
        error_type=detail.run.error_type,
        error_message=detail.run.error_message,
        error_details=detail.run.error_details,
        created_at=detail.run.created_at.isoformat(),
        # PDF and source
        pdf=pdf,
        source=source,
        # Stage data
        stage_template_matching=stage_template_matching,
        stage_data_extraction=stage_data_extraction,
        stage_pipeline_execution=stage_pipeline_execution,
    )
