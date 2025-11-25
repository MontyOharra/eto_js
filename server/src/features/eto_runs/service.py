"""
ETO Runs Service
Business logic for ETO run lifecycle and orchestration
"""
import asyncio
import json
import os
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone

from shared.logging import get_logger

from shared.database import DatabaseConnectionManager
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.eto_sub_run_extraction import EtoSubRunExtractionRepository
from shared.database.repositories.eto_sub_run_pipeline_execution import EtoSubRunPipelineExecutionRepository
from shared.database.repositories.eto_sub_run_pipeline_execution_step import EtoSubRunPipelineExecutionStepRepository

from shared.events.eto_events import eto_event_manager

# Import worker
from .utils import EtoWorker

from shared.exceptions.service import ValidationError

from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunListView,
    EtoRunDetailView,
)
from shared.types.eto_sub_runs import (
    EtoSubRun,
    EtoSubRunCreate,
    EtoSubRunUpdate,
)
from shared.types.eto_sub_run_extractions import (
    EtoSubRunExtraction,
    EtoSubRunExtractionCreate,
    EtoSubRunExtractionUpdate,
)
from shared.types.eto_sub_run_pipeline_executions import (
    EtoSubRunPipelineExecution,
    EtoSubRunPipelineExecutionCreate,
    EtoSubRunPipelineExecutionUpdate,
)
from shared.types.eto_sub_run_pipeline_execution_steps import (
    EtoSubRunPipelineExecutionStep,
    EtoSubRunPipelineExecutionStepCreate,
    EtoSubRunPipelineExecutionStepUpdate,
)
from shared.types.pdf_templates import TemplateMatchingResult

from shared.exceptions.service import ObjectNotFoundError, ServiceError

# Import domain types for list_runs_with_relations return type
from shared.types.pdf_files import PdfFile
from shared.types.pdf_templates import PdfTemplate, PdfTemplateVersion
from shared.types.email import Email

# TYPE_CHECKING imports to avoid circular dependencies
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from features.pdf_templates.service import PdfTemplateService
    from features.pdf_files.service import PdfFilesService
    from features.pipeline_execution.service import PipelineExecutionService

logger = get_logger(__name__)


class EtoRunsService:
    """
    ETO Runs Service - Main orchestrator for Email-to-Order workflow.

    Responsibilities:
    - Create ETO runs from PDF files
    - Orchestrate 3-stage processing workflow:
      1. Template Matching - Match PDF to best template
      2. Data Extraction - Extract field values from PDF
      3. Data Transformation - Execute pipeline with extracted data
    - Manage run lifecycle and status transitions
    - Provide query operations for runs
    - Handle errors and record failure details

    This service is called by:
    - Email Ingestion Service (creates initial runs)
    - ETO Worker (processes runs in background)
    - API endpoints (query operations, manual triggers)
    """

    # ==================== Dependencies ====================

    connection_manager: DatabaseConnectionManager
    pdf_template_service: 'PdfTemplateService'
    pdf_files_service: 'PdfFilesService'
    pipeline_execution_service: 'PipelineExecutionService'

    # ==================== Repositories ====================

    eto_run_repo: EtoRunRepository
    sub_run_repo: EtoSubRunRepository
    sub_run_extraction_repo: EtoSubRunExtractionRepository
    sub_run_pipeline_execution_repo: EtoSubRunPipelineExecutionRepository
    sub_run_pipeline_execution_step_repo: EtoSubRunPipelineExecutionStepRepository

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        pdf_template_service: 'PdfTemplateService',
        pdf_files_service: 'PdfFilesService',
        pipeline_execution_service: 'PipelineExecutionService'
    ) -> None:
        """
        Initialize ETO Runs Service.

        Args:
            connection_manager: Database connection manager
            pdf_template_service: Service for template matching
            pdf_files_service: Service for PDF file access
            pipeline_execution_service: Service for pipeline execution
        """
        logger.debug("Initializing EtoRunsService...")

        # Store service dependencies
        self.connection_manager: DatabaseConnectionManager = connection_manager
        self.pdf_template_service: 'PdfTemplateService' = pdf_template_service
        self.pdf_files_service: 'PdfFilesService' = pdf_files_service
        self.pipeline_execution_service: 'PipelineExecutionService' = pipeline_execution_service

        # Initialize repositories
        self.eto_run_repo: EtoRunRepository = EtoRunRepository(connection_manager=connection_manager)
        self.sub_run_repo: EtoSubRunRepository = EtoSubRunRepository(connection_manager=connection_manager)
        self.sub_run_extraction_repo: EtoSubRunExtractionRepository = EtoSubRunExtractionRepository(connection_manager=connection_manager)
        self.sub_run_pipeline_execution_repo: EtoSubRunPipelineExecutionRepository = EtoSubRunPipelineExecutionRepository(connection_manager=connection_manager)
        self.sub_run_pipeline_execution_step_repo: EtoSubRunPipelineExecutionStepRepository = EtoSubRunPipelineExecutionStepRepository(connection_manager=connection_manager)

        # Worker configuration from environment
        worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
        max_concurrent_runs = int(os.getenv('ETO_MAX_CONCURRENT_RUNS', '10'))
        polling_interval = int(os.getenv('ETO_POLLING_INTERVAL', '2'))  # seconds
        shutdown_timeout = int(os.getenv('ETO_SHUTDOWN_TIMEOUT', '30'))  # seconds

        # Initialize ETO worker
        logger.debug("Initializing ETO worker...")
        self.worker = EtoWorker(
            process_run_callback=self.process_sub_run,
            get_pending_runs_callback=lambda limit: self.sub_run_repo.get_by_status('not_started', limit=limit),
            reset_run_callback=self._reset_sub_run_to_not_started,
            enabled=worker_enabled,
            max_concurrent_runs=max_concurrent_runs,
            polling_interval=polling_interval,
            shutdown_timeout=shutdown_timeout
        )

        logger.info(
            f"EtoRunsService initialized successfully - "
            f"worker_enabled: {self.worker.enabled}, "
            f"polling_interval: {self.worker.polling_interval}s, "
            f"max_concurrent: {self.worker.max_concurrent_runs}"
        )

    # ==================== Public API Methods ====================

    def create_run(self, pdf_file_id: int) -> EtoRun:
        """
        Create ETO run and immediately perform multi-template matching.
        Creates sub-runs that worker will pick up for processing.

        Args:
            pdf_file_id: ID of PDF file to process

        Returns:
            Created EtoRun with status="processing"

        Raises:
            ObjectNotFoundError: If PDF file doesn't exist
            ServiceError: If template matching fails (critical error)
        """
        logger.info(f"Creating ETO run for PDF file {pdf_file_id}")

        try:
            # 1. Validate PDF file exists
            pdf_file = self.pdf_files_service.get_pdf_file(pdf_file_id)
            logger.debug(f"Validated PDF file {pdf_file_id} exists")

            # 2. Create parent run with status="processing"
            run = self.eto_run_repo.create(EtoRunCreate(pdf_file_id=pdf_file_id))
            self.eto_run_repo.update(run.id, {
                "status": "processing",
                "started_at": datetime.now(timezone.utc)
            })

            # Broadcast creation event
            eto_event_manager.broadcast_sync(
                "run_created",
                {
                    "id": run.id,
                    "pdf_file_id": run.pdf_file_id,
                    "status": "processing",
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                }
            )

            # 3. Run multi-template matching (FAST operation)
            logger.debug(f"Run {run.id}: Starting multi-template matching")
            match_result: TemplateMatchingResult = self.pdf_template_service.match_templates_multi_page(pdf_file)

            logger.debug(
                f"Run {run.id}: Template matching complete - "
                f"{len(match_result.matches)} matches, "
                f"{len(match_result.unmatched_pages)} unmatched pages"
            )

            # 4. Create sub-runs for matched page sets
            for match in match_result.matches:
                self.sub_run_repo.create(EtoSubRunCreate(
                    eto_run_id=run.id,
                    matched_pages=json.dumps(match.matched_pages),
                    template_version_id=match.version_id,
                    is_unmatched_group=False
                    # status defaults to "not_started" - worker will pick up
                ))
                logger.debug(
                    f"Run {run.id}: Created sub-run for pages {match.matched_pages} "
                    f"with template version {match.version_id}"
                )

            # 5. Create unmatched sub-run if needed
            if match_result.unmatched_pages:
                unmatched_sub_run = self.sub_run_repo.create(EtoSubRunCreate(
                    eto_run_id=run.id,
                    matched_pages=json.dumps(match_result.unmatched_pages),
                    template_version_id=None,
                    is_unmatched_group=True
                ))
                # Update status to needs_template
                self.sub_run_repo.update(unmatched_sub_run.id, {"status": "needs_template"})

                logger.debug(
                    f"Run {run.id}: Created unmatched sub-run for pages {match_result.unmatched_pages}"
                )

            logger.info(
                f"Created ETO run {run.id} with {len(match_result.matches)} matched sub-runs "
                f"and {1 if match_result.unmatched_pages else 0} unmatched sub-run"
            )

            # 6. Update parent run status based on sub-runs
            # This handles cases where all pages are unmatched (no work for worker to do)
            self._update_parent_run_status(run.id)

            return run

        except ObjectNotFoundError:
            # Re-raise 404 errors as-is
            logger.warning(f"Cannot create ETO run: PDF file {pdf_file_id} not found")
            raise

        except Exception as e:
            # Critical error during template matching - mark parent run as failed
            logger.error(f"Critical error creating run for PDF {pdf_file_id}: {e}", exc_info=True)

            if 'run' in locals():
                self.eto_run_repo.update(run.id, {
                    "status": "failure",
                    "completed_at": datetime.now(timezone.utc),
                    "error_type": "TemplateMatchingSystemError",
                    "error_message": str(e)
                })

            raise ServiceError(f"Failed to create ETO run: {str(e)}") from e

    def list_runs(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[EtoRun]:
        """
        List ETO runs with optional filtering, pagination, and sorting.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (optional, default: no limit)
            offset: Number of results to skip (optional, default: 0)
            order_by: Field to order by (default: created_at)
            desc: Sort descending if True (default: True - newest first)

        Returns:
            List of EtoRun dataclasses
        """
        logger.debug(f"Listing ETO runs: status={status}, limit={limit}, offset={offset}, order_by={order_by}, desc={desc}")

        try:
            runs = self.eto_run_repo.get_all(
                status=status,
                limit=limit,
                offset=offset,
                order_by=order_by,
                desc=desc
            )

            logger.monitor(f"Retrieved {len(runs)} ETO runs")
            return runs

        except Exception as e:
            logger.error(f"Failed to list ETO runs: {e}", exc_info=True)
            raise ServiceError(f"Failed to list ETO runs: {str(e)}") from e

    def list_runs_with_relations(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[EtoRunListView]:
        """
        List ETO runs with all related data for API list view.

        Uses repository-level SQL joins to efficiently fetch all related data
        (PDF files, emails, template matchings, templates) in a single query.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            order_by: Field to order by (default: created_at)
            desc: Sort descending if True (default: True)

        Returns:
            List of EtoRunListView dataclasses with all joined data flattened
        """
        logger.debug(f"Listing ETO runs with relations: status={status}, limit={limit}, offset={offset}")

        try:
            # Repository method performs all joins in a single SQL query
            runs = self.eto_run_repo.get_all_with_relations(
                status=status,
                limit=limit,
                offset=offset,
                order_by=order_by,
                desc=desc
            )

            logger.monitor(f"Retrieved {len(runs)} ETO runs with relations")
            return runs

        except Exception as e:
            logger.error(f"Failed to list ETO runs with relations: {e}", exc_info=True)
            raise ServiceError(f"Failed to list ETO runs with relations: {str(e)}") from e

    def get_run(self, run_id: int) -> EtoRun:
        """
        Get ETO run by ID.

        Returns only the ETO run model. Related stage data (template matching,
        extraction, pipeline execution) should be fetched separately and combined
        at the API layer if needed for detailed views.

        Args:
            run_id: ETO run ID

        Returns:
            EtoRun dataclass

        Raises:
            ObjectNotFoundError: If run not found
        """
        logger.debug(f"Getting ETO run {run_id}")

        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            raise ObjectNotFoundError(f"ETO run {run_id} not found")

        logger.debug(f"Retrieved ETO run {run_id}: status={run.status}, processing_step={run.processing_step}")
        return run

    def get_run_detail(self, run_id: int) -> EtoRunDetailView:
        """
        Get complete ETO run detail with all stage data.

        Fetches run with PDF, email, template matching, extraction, and pipeline
        execution data. Uses repository-level SQLAlchemy joins to efficiently
        fetch and parse all related data in a single query.

        Args:
            run_id: ETO run ID

        Returns:
            EtoRunDetailView dataclass with all stage data

        Raises:
            ObjectNotFoundError: If run not found
        """
        logger.debug(f"Getting ETO run detail for run {run_id}")

        # Repository uses SQLAlchemy joins to fetch all data efficiently
        detail = self.eto_run_repo.get_detail_with_stages(run_id)

        if not detail:
            raise ObjectNotFoundError(f"ETO run {run_id} not found")

        logger.debug(
            f"Retrieved ETO run detail {run_id}: status={detail.status}, "
            f"sub_runs={len(detail.sub_runs)}"
        )
        return detail

    # ==================== Worker Processing Methods ====================

    def process_sub_run(self, sub_run_id: int) -> bool:
        """
        Execute extraction + pipeline for a single sub-run.
        Called by worker for sub-runs with status="not_started".

        Workflow:
        1. Update sub-run to "processing"
        2. Execute Stage 1: Data Extraction (for this sub-run's pages only)
        3. Execute Stage 2: Pipeline Execution (with this sub-run's data)
        4. Update sub-run to "success" or "failure"
        5. Update parent run status based on all sub-runs

        Args:
            sub_run_id: ETO sub-run ID to process

        Returns:
            True if successful, False if failed
        """
        logger.monitor(f"Starting sub-run processing for sub-run {sub_run_id}")

        # Get sub-run and validate
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if not sub_run:
            logger.error(f"Sub-run {sub_run_id} not found")
            raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

        try:
            # Update to processing status
            started_at = datetime.now(timezone.utc)
            self.sub_run_repo.update(sub_run_id, {
                "status": "processing",
                "started_at": started_at
            })

            # Broadcast status change
            eto_event_manager.broadcast_sync("sub_run_updated", {
                "id": sub_run_id,
                "eto_run_id": sub_run.eto_run_id,
                "status": "processing",
                "started_at": started_at.isoformat(),
            })

            # Stage 1: Data Extraction
            try:
                extracted_data = self._process_sub_run_extraction(sub_run_id)
                logger.debug(f"Sub-run {sub_run_id}: Extracted {len(extracted_data)} fields")

            except Exception as e:
                logger.error(f"Sub-run {sub_run_id}: Extraction error: {e}", exc_info=True)
                self._mark_sub_run_failure(sub_run_id, error=e, error_type="DataExtractionError")
                self._update_parent_run_status(sub_run.eto_run_id)
                return False

            # Stage 2: Pipeline Execution
            try:
                self._process_sub_run_pipeline(sub_run_id, extracted_data)

            except Exception as e:
                logger.error(f"Sub-run {sub_run_id}: Pipeline error: {e}", exc_info=True)
                self._mark_sub_run_failure(sub_run_id, error=e, error_type="PipelineExecutionError")
                self._update_parent_run_status(sub_run.eto_run_id)
                return False

            # All stages completed successfully
            self._mark_sub_run_success(sub_run_id)
            self._update_parent_run_status(sub_run.eto_run_id)
            logger.monitor(f"Sub-run {sub_run_id}: All stages completed successfully")
            return True

        except Exception as e:
            # Unexpected error
            logger.error(f"Sub-run {sub_run_id}: Unexpected system error: {e}", exc_info=True)
            self._mark_sub_run_failure(sub_run_id, error=e, error_type="UnexpectedSystemError")
            self._update_parent_run_status(sub_run.eto_run_id)
            return False

    # ==================== Stage Processing Methods (Sub-Run) ====================

    def _process_sub_run_extraction(self, sub_run_id: int) -> list:
        """
        Execute data extraction stage for a single sub-run.

        Extracts data only from pages that belong to this sub-run using the
        template version associated with this sub-run.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            List of extracted data records (one per page in sub-run)

        Raises:
            Exception: If extraction fails
        """
        logger.info(f"Sub-run {sub_run_id}: Starting extraction stage")

        # Get sub-run with template info
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if not sub_run:
            raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

        if not sub_run.template_version_id:
            raise ValidationError(f"Sub-run {sub_run_id} has no template version (unmatched group)")

        # Get parent run for PDF file ID
        parent_run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
        if not parent_run:
            raise ObjectNotFoundError(f"Parent run {sub_run.eto_run_id} not found")

        # Get template version for extraction fields
        template_version = self.pdf_template_service.get_version_by_id(sub_run.template_version_id)

        # Parse matched pages from JSON
        matched_pages = json.loads(sub_run.matched_pages)

        # Extract data from sub-run's pages only
        extracted_data = self._extract_data_from_pdf_pages(
            pdf_file_id=parent_run.pdf_file_id,
            extraction_fields=template_version.extraction_fields,
            page_numbers=matched_pages
        )

        # Create extraction record
        extraction = self.sub_run_extraction_repo.create(
            EtoSubRunExtractionCreate(sub_run_id=sub_run_id)
        )

        # Update with results (repository handles JSON serialization)
        self.sub_run_extraction_repo.update(extraction.id, {
            "status": "success",
            "extracted_data": extracted_data,
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc)
        })

        logger.info(f"Sub-run {sub_run_id}: Extraction completed - {len(extracted_data)} pages extracted")

        return extracted_data

    def _process_sub_run_pipeline(self, sub_run_id: int, extracted_data: list) -> None:
        """
        Execute pipeline execution stage for a single sub-run.

        Executes the pipeline with extracted data, persisting step results and actions.
        Uses PRODUCTION mode (execute_actions=True) - actions actually execute.

        Args:
            sub_run_id: Sub-run ID
            extracted_data: Extracted data from previous stage (list of field dicts)

        Raises:
            Exception: If pipeline execution fails
        """
        logger.monitor(f"Sub-run {sub_run_id}: Executing pipeline execution stage")

        # Step 1: Get sub-run with template info
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if not sub_run:
            raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

        if not sub_run.template_version_id:
            raise ValidationError(f"Sub-run {sub_run_id} has no template version (unmatched group)")

        # Step 2: Create pipeline_execution record
        started_at = datetime.now(timezone.utc)
        pipeline_execution = self.sub_run_pipeline_execution_repo.create(
            EtoSubRunPipelineExecutionCreate(
                sub_run_id=sub_run_id,
                started_at=started_at
            )
        )
        logger.debug(f"Sub-run {sub_run_id}: Created pipeline_execution record {pipeline_execution.id}")

        # Step 3: Get template version with pipeline_definition_id
        template_version = self.pdf_template_service.get_version_by_id(sub_run.template_version_id)
        logger.debug(
            f"Sub-run {sub_run_id}: Retrieved template version {sub_run.template_version_id} "
            f"with pipeline_definition_id {template_version.pipeline_definition_id}"
        )

        # Step 4: Get pipeline definition with pipeline_state
        pipeline_definition = self.pipeline_execution_service.pipeline_repo.get_by_id(
            template_version.pipeline_definition_id
        )
        if not pipeline_definition:
            raise ServiceError(
                f"Pipeline definition {template_version.pipeline_definition_id} not found "
                f"for template version {sub_run.template_version_id}"
            )
        logger.debug(
            f"Sub-run {sub_run_id}: Retrieved pipeline definition {pipeline_definition.id} "
            f"with compiled plan {pipeline_definition.compiled_plan_id}"
        )

        # Step 5: Get compiled steps
        if not pipeline_definition.compiled_plan_id:
            raise ServiceError(
                f"Pipeline definition {pipeline_definition.id} is not compiled. "
                f"Cannot execute uncompiled pipeline."
            )

        compiled_steps = self.pipeline_execution_service.step_repo.get_steps_by_plan_id(
            pipeline_definition.compiled_plan_id
        )
        if not compiled_steps:
            raise ServiceError(
                f"No compiled steps found for pipeline {pipeline_definition.id} "
                f"(plan {pipeline_definition.compiled_plan_id})"
            )
        logger.debug(
            f"Sub-run {sub_run_id}: Retrieved {len(compiled_steps)} compiled steps "
            f"from plan {pipeline_definition.compiled_plan_id}"
        )

        # Step 6: Convert extracted_data list to dict format for pipeline execution
        # Pipeline expects: {field_name: extracted_value}
        extracted_data_dict = {
            result["name"]: result["extracted_value"]
            for result in extracted_data
        }

        # Step 7: Execute pipeline with PRODUCTION mode (execute_actions=True)
        from shared.types.pipeline_execution import PipelineExecutionResult

        execution_result: PipelineExecutionResult = self.pipeline_execution_service.execute_pipeline(
            steps=compiled_steps,  # type: ignore[arg-type]
            entry_values_by_name=extracted_data_dict,
            pipeline_state=pipeline_definition.pipeline_state
        )
        logger.debug(
            f"Sub-run {sub_run_id}: Pipeline execution completed with status={execution_result.status}, "
            f"{len(execution_result.steps)} steps, {len(execution_result.executed_actions)} actions"
        )

        # Step 8: Persist ALL step results to database (batch after completion)
        for step_result in execution_result.steps:
            # Serialize step inputs/outputs to JSON strings
            inputs_json = json.dumps(step_result.inputs) if step_result.inputs else None
            outputs_json = json.dumps(step_result.outputs) if step_result.outputs else None

            # Create step record
            self.sub_run_pipeline_execution_step_repo.create(
                EtoSubRunPipelineExecutionStepCreate(
                    pipeline_execution_id=pipeline_execution.id,
                    module_instance_id=step_result.module_instance_id,
                    step_number=step_result.step_number,
                    inputs=inputs_json,
                    outputs=outputs_json,
                    error=step_result.error
                )
            )

        logger.debug(f"Sub-run {sub_run_id}: Persisted {len(execution_result.steps)} step results to database")

        # Step 9: Store executed_actions as JSON
        executed_actions_json = json.dumps(execution_result.executed_actions) if execution_result.executed_actions else None

        # Step 10: Update pipeline_execution record with final status
        completed_at = datetime.now(timezone.utc)
        final_status = "success" if execution_result.status == "success" else "failure"

        self.sub_run_pipeline_execution_repo.update(
            pipeline_execution.id,
            {
                "status": final_status,
                "executed_actions": executed_actions_json,
                "completed_at": completed_at
            }
        )
        logger.debug(
            f"Sub-run {sub_run_id}: Updated pipeline_execution record to status={final_status}"
        )

        # Step 11: If pipeline failed, raise error to mark sub-run as failed
        if execution_result.status != "success":
            error_msg = execution_result.error or "Pipeline execution failed"
            logger.error(f"Sub-run {sub_run_id}: Pipeline execution failed: {error_msg}")
            raise ServiceError(f"Pipeline execution failed: {error_msg}")

        logger.monitor(f"Sub-run {sub_run_id}: Pipeline execution completed successfully")

    def _extract_data_from_pdf_pages(
        self,
        pdf_file_id: int,
        extraction_fields: list,
        page_numbers: list[int]
    ) -> list:
        """
        Wrapper for PDF extraction that filters results to specific pages only.

        Calls the utility function to extract data from all pages, then filters
        to only the pages specified for this sub-run.

        Args:
            pdf_file_id: PDF file ID
            extraction_fields: List of field definitions for extraction
            page_numbers: List of page numbers to include (1-indexed)

        Returns:
            List of extracted data records for specified pages only
        """
        from features.eto_runs.utils.extraction import extract_data_from_pdf_pages

        return extract_data_from_pdf_pages(
            pdf_file_service=self.pdf_files_service,
            pdf_file_id=pdf_file_id,
            extraction_fields=extraction_fields,
            page_numbers=page_numbers
        )

    # ==================== Helper Methods (Sub-Run) ====================

    def _mark_sub_run_success(self, sub_run_id: int) -> None:
        """
        Mark sub-run as successfully completed.

        Updates status to "success" and sets completed_at timestamp.

        Args:
            sub_run_id: Sub-run ID
        """
        logger.info(f"Sub-run {sub_run_id}: Marking as success")

        self.sub_run_repo.update(sub_run_id, {
            "status": "success",
            "completed_at": datetime.now(timezone.utc)
        })

    def _mark_sub_run_failure(
        self,
        sub_run_id: int,
        error: Exception,
        error_type: Optional[str] = None
    ) -> None:
        """
        Mark sub-run as failed and record error details.

        Updates status to "failure", sets error fields, and sets completed_at timestamp.

        Args:
            sub_run_id: Sub-run ID
            error: Exception that caused the failure
            error_type: Optional error type classification (inferred from exception if not provided)
        """
        # Infer error type if not provided
        if error_type is None:
            error_type = type(error).__name__

        error_message = str(error)
        completed_at = datetime.now(timezone.utc)

        logger.error(f"Sub-run {sub_run_id}: Marking as failure - {error_type}: {error}")

        self.sub_run_repo.update(sub_run_id, {
            "status": "failure",
            "error_type": error_type,
            "error_message": error_message,
            "error_details": None,  # TODO: Add stack trace or additional context if needed
            "completed_at": completed_at
        })

    def _update_parent_run_status(self, run_id: int) -> None:
        """
        Update parent run status based on all sub-run statuses.

        Status logic:
        - "processing": Has any sub-runs with status "not_started" or "processing"
        - "success": All sub-runs completed (regardless of individual success/failure)

        Note: Parent "failure" status is ONLY set for critical template matching errors,
        not for individual sub-run failures.

        Args:
            run_id: Parent ETO run ID
        """
        logger.debug(f"Run {run_id}: Updating parent status based on sub-runs")

        # Get all sub-runs for parent
        sub_runs = self.sub_run_repo.get_by_eto_run_id(run_id)

        if not sub_runs:
            # No sub-runs - should not happen in normal flow
            logger.warning(f"Run {run_id}: No sub-runs found")
            return

        # Check if any sub-runs are still active
        active_statuses = {"not_started", "processing"}
        has_active = any(sub.status in active_statuses for sub in sub_runs)

        if has_active:
            # Keep parent in "processing" status
            self.eto_run_repo.update(run_id, {"status": "processing"})
            logger.debug(f"Run {run_id}: Status remains 'processing' (has active sub-runs)")
        else:
            # All sub-runs completed - mark parent as success
            self.eto_run_repo.update(run_id, {
                "status": "success",
                "completed_at": datetime.now(timezone.utc)
            })
            logger.info(f"Run {run_id}: All sub-runs completed - marked as success")

    def _reset_sub_run_to_not_started(self, sub_run_id: int) -> None:
        """
        Reset a sub-run back to not_started status.

        Used by worker cleanup when a sub-run crashes during processing.
        Clears processing timestamps and error fields.

        Args:
            sub_run_id: Sub-run ID
        """
        logger.info(f"Sub-run {sub_run_id}: Resetting to not_started")

        self.sub_run_repo.update(sub_run_id, {
            "status": "not_started",
            "started_at": None,
            "completed_at": None,
            "error_type": None,
            "error_message": None,
            "error_details": None
        })

    # ==================== Bulk Operation Methods ====================

    def reprocess_runs(self, run_ids: list[int]) -> None:
        """
        Reprocess failed or skipped ETO runs (bulk operation).

        Workflow (for each run):
        1. Verify run exists and status is "failure", "skipped", or "needs_template"
        2. Get all sub-runs for the parent run
        3. Delete sub-run stage records (extraction, pipeline_execution)
        4. Reset each sub-run to "not_started" status
        5. Reset parent run to "processing" status
        6. Clear error fields
        7. Worker will automatically pick up sub-runs and reprocess

        Args:
            run_ids: List of ETO run IDs to reprocess

        Raises:
            ObjectNotFoundError: If one or more runs not found
            ValidationError: If one or more runs have invalid status
        """
        logger.info(f"Reprocessing {len(run_ids)} ETO runs: {run_ids}")

        # Validate all runs exist and have valid status
        for run_id in run_ids:
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                raise ObjectNotFoundError(f"ETO run {run_id} not found")

            if run.status not in ("failure", "skipped", "needs_template"):
                raise ValidationError(
                    f"Cannot reprocess run {run_id} with status '{run.status}'. "
                    f"Only 'failure', 'skipped', and 'needs_template' runs can be reprocessed."
                )

        # Reprocess each run
        for run_id in run_ids:
            logger.debug(f"Reprocessing run {run_id}")

            # Get all sub-runs for this parent run
            sub_runs = self.sub_run_repo.get_by_eto_run_id(run_id)

            # Delete stage records for each sub-run
            for sub_run in sub_runs:
                # Delete extraction record
                extraction = self.sub_run_extraction_repo.get_by_sub_run_id(sub_run.id)
                if extraction:
                    self.sub_run_extraction_repo.delete(extraction.id)
                    logger.debug(f"Deleted extraction record for sub-run {sub_run.id}")

                # Delete pipeline execution record (cascade deletes steps)
                pipeline_execution = self.sub_run_pipeline_execution_repo.get_by_sub_run_id(sub_run.id)
                if pipeline_execution:
                    self.sub_run_pipeline_execution_repo.delete(pipeline_execution.id)
                    logger.debug(f"Deleted pipeline_execution record for sub-run {sub_run.id}")

                # Reset sub-run to not_started status
                self.sub_run_repo.update(sub_run.id, {
                    "status": "not_started",
                    "error_type": None,
                    "error_message": None,
                    "error_details": None,
                    "started_at": None,
                    "completed_at": None,
                })
                logger.debug(f"Reset sub-run {sub_run.id} to not_started")

            # Reset parent run to processing status
            self.eto_run_repo.update(
                run_id,
                EtoRunUpdate(
                    status="processing",
                    error_type=None,
                    error_message=None,
                    error_details=None,
                    started_at=datetime.now(timezone.utc),
                    completed_at=None,
                )
            )

            # Broadcast status change
            eto_event_manager.broadcast_sync(
                "run_updated",
                {
                    "id": run_id,
                    "status": "processing",
                }
            )

            logger.monitor(f"Run {run_id}: Reset to processing for reprocessing ({len(sub_runs)} sub-runs)")

        logger.info(f"Successfully reprocessed {len(run_ids)} ETO runs")

    def skip_runs(self, run_ids: list[int]) -> None:
        """
        Mark ETO runs as skipped (bulk operation).

        Workflow (for each run):
        1. Verify run exists and status is "failure" or "needs_template"
        2. Set status to "skipped"
        3. Preserves all stage data for historical reference

        Purpose:
        - Exclude from bulk reprocessing operations
        - Indicate intentional decision to not process this PDF
        - Can be reprocessed or deleted later

        Args:
            run_ids: List of ETO run IDs to skip

        Raises:
            ObjectNotFoundError: If one or more runs not found
            ValidationError: If one or more runs have invalid status
        """
        logger.info(f"Skipping {len(run_ids)} ETO runs: {run_ids}")

        # Validate all runs exist and have valid status
        for run_id in run_ids:
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                raise ObjectNotFoundError(f"ETO run {run_id} not found")

            if run.status not in ("failure", "needs_template"):
                raise ValidationError(
                    f"Cannot skip run {run_id} with status '{run.status}'. "
                    f"Only 'failure' and 'needs_template' runs can be skipped."
                )

        # Skip each run
        for run_id in run_ids:
            logger.debug(f"Skipping run {run_id}")

            # Update status to skipped (preserving all other data)
            self.eto_run_repo.update(
                run_id,
                EtoRunUpdate(status="skipped")
            )

            # Broadcast status change
            eto_event_manager.broadcast_sync(
                "run_updated",
                {
                    "id": run_id,
                    "status": "skipped",
                }
            )

            logger.monitor(f"Run {run_id}: Marked as skipped")

        logger.info(f"Successfully skipped {len(run_ids)} ETO runs")

    def delete_runs(self, run_ids: list[int]) -> None:
        """
        Permanently delete ETO runs (bulk operation).

        Workflow (for each run):
        1. Verify run exists and status is "skipped"
        2. Delete run record (cascade delete handles sub-runs and their stage records)
        3. Note: PDF file is NOT deleted (may be referenced elsewhere)

        Database cascade chain:
        - eto_runs → eto_sub_runs (CASCADE)
        - eto_sub_runs → eto_sub_run_extractions (CASCADE)
        - eto_sub_runs → eto_sub_run_pipeline_executions (CASCADE)
        - eto_sub_run_pipeline_executions → eto_sub_run_pipeline_execution_steps (CASCADE)

        Restrictions:
        - Can only delete runs with status="skipped"
        - Deletion is permanent (no recovery)

        Args:
            run_ids: List of ETO run IDs to delete

        Raises:
            ObjectNotFoundError: If one or more runs not found
            ValidationError: If one or more runs have invalid status
        """
        logger.info(f"Deleting {len(run_ids)} ETO runs: {run_ids}")

        # Validate all runs exist and have valid status
        for run_id in run_ids:
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                raise ObjectNotFoundError(f"ETO run {run_id} not found")

            if run.status != "skipped":
                raise ValidationError(
                    f"Cannot delete run {run_id} with status '{run.status}'. "
                    f"Only 'skipped' runs can be deleted."
                )

        # Delete each run (cascade handles sub-runs and stage records)
        for run_id in run_ids:
            logger.debug(f"Deleting run {run_id}")

            # Delete the run (cascade deletes sub-runs and all related records)
            self.eto_run_repo.delete(run_id)

            # Broadcast deletion event
            eto_event_manager.broadcast_sync(
                "run_deleted",
                {
                    "id": run_id,
                }
            )

            logger.monitor(f"Run {run_id}: Permanently deleted")

        logger.info(f"Successfully deleted {len(run_ids)} ETO runs")

    # ==================== Background Worker Lifecycle ====================

    async def startup(self) -> bool:
        """
        Start the background processing worker.
        Called during application startup.

        Returns:
            True if worker started, False if disabled or already running
        """
        return await self.worker.startup()

    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Stop the background processing worker.
        Called during application shutdown.

        Args:
            graceful: If True, wait for current batch to complete

        Returns:
            True if stopped successfully
        """
        return await self.worker.shutdown(graceful=graceful)

    def pause_worker(self) -> bool:
        """
        Pause the worker (emergency stop without shutting down).
        Processing will halt but worker remains active.

        Returns:
            True if paused successfully
        """
        return self.worker.pause()

    def resume_worker(self) -> bool:
        """
        Resume the worker from paused state.

        Returns:
            True if resumed successfully
        """
        return self.worker.resume()

    def get_worker_status(self) -> Dict[str, Any]:
        """
        Get current worker status and metrics.

        Returns:
            Dictionary with worker state and statistics
        """
        return self.worker.get_status()