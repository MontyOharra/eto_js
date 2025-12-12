"""
ETO Runs Service
Business logic for ETO run lifecycle and orchestration
"""
import asyncio
import json
import os
from typing import Optional, List, Dict, Any, Set, Literal
from datetime import datetime, timezone

from shared.logging import get_logger

from shared.database import DatabaseConnectionManager
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.eto_sub_run_extraction import EtoSubRunExtractionRepository
from shared.database.repositories.eto_sub_run_pipeline_execution import EtoSubRunPipelineExecutionRepository
from shared.database.repositories.eto_sub_run_pipeline_execution_step import EtoSubRunPipelineExecutionStepRepository
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository

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
    EtoSubRunDetailView,
)
from shared.types.eto_runs import EtoRunExtractionDetailView, EtoRunPipelineExecutionDetailView, EtoRunPipelineExecutionStepDetailView
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
from shared.types.eto_sub_run_output_executions import (
    EtoSubRunOutputExecution,
    EtoSubRunOutputExecutionCreate,
    EtoSubRunOutputExecutionUpdate,
)
from shared.types.pdf_templates import TemplateMatchingResult
from shared.types.pipeline_execution import PipelineExecutionResult

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
    from src.features.pipeline_execution.service import PipelineExecutionService
    from features.output_processing.service import OutputProcessingService

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
    output_processing_service: 'OutputProcessingService'

    # ==================== Repositories ====================

    eto_run_repo: EtoRunRepository
    sub_run_repo: EtoSubRunRepository
    sub_run_extraction_repo: EtoSubRunExtractionRepository
    sub_run_pipeline_execution_repo: EtoSubRunPipelineExecutionRepository
    sub_run_pipeline_execution_step_repo: EtoSubRunPipelineExecutionStepRepository
    sub_run_output_execution_repo: EtoSubRunOutputExecutionRepository

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        pdf_template_service: 'PdfTemplateService',
        pdf_files_service: 'PdfFilesService',
        pipeline_execution_service: 'PipelineExecutionService',
        output_processing_service: 'OutputProcessingService'
    ) -> None:
        """
        Initialize ETO Runs Service.

        Args:
            connection_manager: Database connection manager
            pdf_template_service: Service for template matching
            pdf_files_service: Service for PDF file access
            pipeline_execution_service: Service for pipeline execution
            output_processing_service: Service for processing output channels into pending orders
        """
        logger.debug("Initializing EtoRunsService...")

        # Store service dependencies
        self.connection_manager: DatabaseConnectionManager = connection_manager
        self.pdf_template_service: 'PdfTemplateService' = pdf_template_service
        self.pdf_files_service: 'PdfFilesService' = pdf_files_service
        self.pipeline_execution_service: 'PipelineExecutionService' = pipeline_execution_service
        self.output_processing_service: 'OutputProcessingService' = output_processing_service

        # Initialize repositories
        self.eto_run_repo: EtoRunRepository = EtoRunRepository(connection_manager=connection_manager)
        self.sub_run_repo: EtoSubRunRepository = EtoSubRunRepository(connection_manager=connection_manager)
        self.sub_run_extraction_repo: EtoSubRunExtractionRepository = EtoSubRunExtractionRepository(connection_manager=connection_manager)
        self.sub_run_pipeline_execution_repo: EtoSubRunPipelineExecutionRepository = EtoSubRunPipelineExecutionRepository(connection_manager=connection_manager)
        self.sub_run_pipeline_execution_step_repo: EtoSubRunPipelineExecutionStepRepository = EtoSubRunPipelineExecutionStepRepository(connection_manager=connection_manager)
        self.sub_run_output_execution_repo: EtoSubRunOutputExecutionRepository = EtoSubRunOutputExecutionRepository(connection_manager=connection_manager)

        # Worker configuration from environment
        worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
        max_concurrent_runs = int(os.getenv('ETO_MAX_CONCURRENT_RUNS', '10'))
        polling_interval = int(os.getenv('ETO_POLLING_INTERVAL', '2'))  # seconds
        shutdown_timeout = int(os.getenv('ETO_SHUTDOWN_TIMEOUT', '30'))  # seconds

        # Initialize ETO worker with two-phase callbacks
        logger.debug("Initializing ETO worker (two-phase processing)...")
        self.worker = EtoWorker(
            # Phase 1: Template Matching (not_started + no template)
            process_template_matching_callback=self.process_sub_run_template_matching,
            get_pending_template_matching_callback=lambda limit: self.sub_run_repo.get_by_status_no_template('not_started', limit=limit),
            # Phase 2: Extraction + Pipeline (matched status)
            process_extraction_pipeline_callback=self.process_sub_run_extraction_pipeline,
            get_pending_extraction_pipeline_callback=lambda limit: self.sub_run_repo.get_by_status('matched', limit=limit),
            # Reset callback
            reset_run_callback=self._reset_sub_run_to_not_started,
            # Configuration
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

    def create_run(
        self,
        pdf_file_id: int,
        source_type: Literal['email', 'manual'] = 'manual',
        source_email_id: Optional[int] = None
    ) -> EtoRun:
        """
        Create ETO run with a single initial sub-run containing all pages.
        Worker will pick up the sub-run and perform template matching.

        New Architecture:
        - Creates ONE sub-run with all pages, status="not_started", no template
        - Worker Phase 1 handles template matching
        - Worker Phase 2 handles extraction + pipeline

        Args:
            pdf_file_id: ID of PDF file to process
            source_type: 'email' for email ingestion, 'manual' for manual uploads
            source_email_id: Email ID if source_type='email', None otherwise

        Returns:
            Created EtoRun with status="processing"

        Raises:
            ObjectNotFoundError: If PDF file doesn't exist
            ServiceError: If creation fails
        """
        logger.info(f"Creating ETO run for PDF file {pdf_file_id}")

        try:
            # 1. Validate PDF file exists and get page count
            pdf_file = self.pdf_files_service.get_pdf_file(pdf_file_id)
            if pdf_file.page_count is None:
                raise ServiceError(f"PDF file {pdf_file_id} has no page count")
            logger.debug(f"Validated PDF file {pdf_file_id} exists with {pdf_file.page_count} pages")

            # 2. Create parent run with status="processing"
            run = self.eto_run_repo.create(EtoRunCreate(
                pdf_file_id=pdf_file_id,
                source_type=source_type,
                source_email_id=source_email_id
            ))
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

            # 3. Create single initial sub-run with ALL pages
            # Worker Phase 1 will perform template matching and split into
            # matched/unmatched sub-runs
            all_pages = list(range(1, pdf_file.page_count + 1))
            self.sub_run_repo.create(EtoSubRunCreate(
                eto_run_id=run.id,
                matched_pages=json.dumps(all_pages),
                template_version_id=None,  # No template yet - worker will match
                # status defaults to "not_started" - Worker Phase 1 will pick up
            ))

            logger.info(
                f"Created ETO run {run.id} with initial sub-run for {pdf_file.page_count} pages"
            )

            return run

        except ObjectNotFoundError:
            # Re-raise 404 errors as-is
            logger.warning(f"Cannot create ETO run: PDF file {pdf_file_id} not found")
            raise

        except Exception as e:
            # Critical error during creation - mark parent run as failed if it exists
            logger.error(f"Critical error creating run for PDF {pdf_file_id}: {e}", exc_info=True)

            if 'run' in locals():
                self.eto_run_repo.update(run.id, {
                    "status": "failure",
                    "completed_at": datetime.now(timezone.utc),
                    "error_type": "RunCreationError",
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
        is_read: Optional[bool] = None,
        has_sub_run_status: Optional[str] = None,
        search_query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "last_processed_at",
        desc: bool = True
    ) -> List[EtoRunListView]:
        """
        List ETO runs with all related data for API list view.

        Uses repository-level SQL joins to efficiently fetch all related data
        (PDF files, emails, template matchings, templates) in a single query.

        Args:
            is_read: Filter by read status (optional)
            has_sub_run_status: Filter runs with sub-runs having this status (optional)
            search_query: Search in filename, email sender, subject (optional)
            date_from: Filter runs created on or after this date (optional)
            date_to: Filter runs created on or before this date (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            order_by: Field to order by (default: last_processed_at)
            desc: Sort descending if True (default: True)

        Returns:
            List of EtoRunListView dataclasses with all joined data flattened
        """
        logger.debug(f"Listing ETO runs with relations: is_read={is_read}, has_sub_run_status={has_sub_run_status}, search={search_query}, limit={limit}, offset={offset}")

        try:
            # Repository method performs all joins in a single SQL query
            runs = self.eto_run_repo.get_all_with_relations(
                is_read=is_read,
                has_sub_run_status=has_sub_run_status,
                search_query=search_query,
                date_from=date_from,
                date_to=date_to,
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

    def update_run(self, run_id: int, updates: EtoRunUpdate) -> EtoRun:
        """
        Update an ETO run.

        Currently supports updating:
        - is_read: Mark run as read/unread

        Args:
            run_id: ETO run ID
            updates: Dict of fields to update

        Returns:
            Updated EtoRun dataclass

        Raises:
            ObjectNotFoundError: If run not found
        """
        logger.debug(f"Updating ETO run {run_id}: {updates}")

        run = self.eto_run_repo.update(run_id, updates)

        logger.info(f"Updated ETO run {run_id}")
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

    def get_sub_run_detail(self, sub_run_id: int) -> EtoSubRunDetailView:
        """
        Get complete sub-run detail with all stage data.

        Fetches sub-run with template, PDF (via parent run), extraction stage,
        and pipeline execution stage data.

        Args:
            sub_run_id: ETO sub-run ID

        Returns:
            EtoSubRunDetailView dataclass with all stage data

        Raises:
            ObjectNotFoundError: If sub-run not found
        """
        logger.debug(f"Getting sub-run detail for sub-run {sub_run_id}")

        # Get sub-run
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if not sub_run:
            raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

        # Get parent run to get PDF info
        run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
        if not run:
            raise ObjectNotFoundError(f"Parent run {sub_run.eto_run_id} not found")

        # Get PDF file info
        pdf_file = self.pdf_files_service.get_pdf_file(run.pdf_file_id)

        # Get template info if available
        template_id = None
        template_name = None
        template_version_num = None
        template_version = None
        if sub_run.template_version_id:
            # Get template version and template info from pdf_template_service
            try:
                template_version = self.pdf_template_service.get_version_by_id(sub_run.template_version_id)
                template = self.pdf_template_service.get_template(template_version.template_id)
                template_id = template.id
                template_name = template.name
                template_version_num = template_version.version_number
            except Exception as e:
                logger.warning(f"Failed to get template info for sub-run {sub_run_id}: {e}")

        # Parse matched pages from JSON string
        matched_pages = []
        try:
            matched_pages = json.loads(sub_run.matched_pages)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse matched_pages for sub-run {sub_run_id}: {e}")

        # Get extraction stage data (if exists)
        extraction_detail: Optional[EtoRunExtractionDetailView] = None
        extraction = self.sub_run_extraction_repo.get_by_sub_run_id(sub_run_id)
        if extraction:
            extraction_detail = EtoRunExtractionDetailView(
                status=extraction.status, #type: ignore
                started_at=extraction.started_at,
                completed_at=extraction.completed_at,
                extracted_data=extraction.extracted_data,
            )

        # Get pipeline execution stage data (if exists)
        pipeline_detail: Optional[EtoRunPipelineExecutionDetailView] = None
        pipeline_exec = self.sub_run_pipeline_execution_repo.get_by_sub_run_id(sub_run_id)
        if pipeline_exec:
            # Get pipeline definition ID from template version (already fetched above)
            pipeline_def_id = template_version.pipeline_definition_id if template_version else None

            # Fetch execution steps
            steps_data = self.sub_run_pipeline_execution_step_repo.get_by_pipeline_execution_id(pipeline_exec.id)
            steps = []
            for step in steps_data:
                # Parse JSON fields
                inputs = None
                outputs = None
                error = None
                if step.inputs:
                    try:
                        inputs = json.loads(step.inputs)
                    except (json.JSONDecodeError, TypeError):
                        pass
                if step.outputs:
                    try:
                        outputs = json.loads(step.outputs)
                    except (json.JSONDecodeError, TypeError):
                        pass
                if step.error:
                    try:
                        error = json.loads(step.error)
                    except (json.JSONDecodeError, TypeError):
                        # Error is stored as plain string, not JSON - keep as-is
                        error = step.error

                steps.append(EtoRunPipelineExecutionStepDetailView(
                    id=step.id,
                    step_number=step.step_number,
                    module_instance_id=step.module_instance_id,
                    inputs=inputs,
                    outputs=outputs,
                    error=error,
                ))

            pipeline_detail = EtoRunPipelineExecutionDetailView(
                status=pipeline_exec.status, #type: ignore
                started_at=pipeline_exec.started_at,
                completed_at=pipeline_exec.completed_at,
                pipeline_definition_id=pipeline_def_id,
                steps=steps,
            )

        # Build and return detail view
        return EtoSubRunDetailView(
            id=sub_run.id,
            eto_run_id=sub_run.eto_run_id,
            matched_pages=matched_pages,
            status=sub_run.status,
            template_id=template_id,
            template_name=template_name,
            template_version_id=sub_run.template_version_id,
            template_version_num=template_version_num,
            pdf_file_id=pdf_file.id,
            pdf_original_filename=pdf_file.original_filename,
            pdf_file_size=pdf_file.file_size_bytes,
            pdf_page_count=pdf_file.page_count,
            extraction=extraction_detail,
            pipeline_execution=pipeline_detail,
            error_type=sub_run.error_type,
            error_message=sub_run.error_message,
            error_details=sub_run.error_details,
            started_at=sub_run.started_at,
            completed_at=sub_run.completed_at,
            created_at=sub_run.created_at,
            updated_at=sub_run.updated_at,
        )

    # ==================== Worker Processing Methods ====================

    def process_sub_run(self, sub_run_id: int) -> bool:
        """
        Execute extraction + pipeline for a single sub-run.
        Called by worker for sub-runs with status="not_started".

        Workflow:
        1. Update sub-run to "processing"
        2. Execute Stage 1: Data Extraction (for this sub-run's pages only)
        3. Execute Stage 2: Pipeline Execution (with this sub-run's data)
        4. Execute Stage 3: Output Execution (if has output channels)
        5. Update sub-run to "success" or "failure"
        6. Update parent run status based on all sub-runs

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

        # Get customer_id from template (via template_version)
        customer_id: Optional[int] = None
        if sub_run.template_version_id:
            template_version = self.pdf_template_service.get_version_by_id(sub_run.template_version_id)
            template = self.pdf_template_service.get_template(template_version.template_id)
            customer_id = template.customer_id
            logger.debug(f"Sub-run {sub_run_id}: Retrieved customer_id={customer_id} from template {template.id}")

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
                pipeline_result = self._process_sub_run_pipeline(sub_run_id, extracted_data)

            except Exception as e:
                logger.error(f"Sub-run {sub_run_id}: Pipeline error: {e}", exc_info=True)
                self._mark_sub_run_failure(sub_run_id, error=e, error_type="PipelineExecutionError")
                self._update_parent_run_status(sub_run.eto_run_id)
                return False

            # Stage 3: Output Execution (if pipeline has output channel values)
            output_channel_values = pipeline_result.output_channel_values or {}
            if output_channel_values and customer_id is not None:
                try:
                    self._process_sub_run_output_execution(
                        sub_run_id=sub_run_id,
                        output_channel_values=output_channel_values,
                        customer_id=customer_id,
                    )

                except Exception as e:
                    logger.error(f"Sub-run {sub_run_id}: Output execution error: {e}", exc_info=True)
                    self._mark_sub_run_failure(sub_run_id, error=e, error_type="OutputExecutionError")
                    self._update_parent_run_status(sub_run.eto_run_id)
                    return False
            elif output_channel_values and customer_id is None:
                logger.warning(f"Sub-run {sub_run_id}: Has output channels but no customer_id on template, skipping output execution")
            else:
                logger.debug(f"Sub-run {sub_run_id}: No output channels in pipeline, skipping output execution")

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

    def process_sub_run_template_matching(self, sub_run_id: int) -> bool:
        """
        Execute template matching for a single sub-run (Worker Phase 1).
        Called by worker for sub-runs with status="not_started" AND no template.

        Workflow:
        1. Get sub-run and its parent run's PDF file
        2. Parse matched_pages to get page numbers
        3. Call template matching on those pages
        4. For each match: create new sub-run with status='matched' and template
        5. For unmatched pages: create new sub-run with status='needs_template'
        6. Delete the original sub-run
        7. Update parent run status

        Args:
            sub_run_id: ETO sub-run ID to process

        Returns:
            True if successful, False if failed
        """
        logger.monitor(f"Starting template matching for sub-run {sub_run_id}")

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

            # Get parent run for PDF file ID
            parent_run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
            if not parent_run:
                raise ObjectNotFoundError(f"Parent run {sub_run.eto_run_id} not found")

            # Get PDF file
            pdf_file = self.pdf_files_service.get_pdf_file(parent_run.pdf_file_id)

            # Parse matched_pages from JSON
            matched_pages = json.loads(sub_run.matched_pages)
            logger.debug(f"Sub-run {sub_run_id}: Template matching for pages {matched_pages}")

            # Run template matching on these pages
            match_result = self.pdf_template_service.match_templates_multi_page(
                pdf_file,
                page_numbers=matched_pages
            )

            logger.debug(
                f"Sub-run {sub_run_id}: Template matching complete - "
                f"{len(match_result.matches)} matches, "
                f"{len(match_result.unmatched_pages)} unmatched pages"
            )

            # Create new sub-runs for matched page sets
            for match in match_result.matches:
                new_sub_run = self.sub_run_repo.create(EtoSubRunCreate(
                    eto_run_id=sub_run.eto_run_id,
                    matched_pages=json.dumps(match.matched_pages),
                    template_version_id=match.version_id,
                ))

                # Check if template is marked as autoskip
                template = self.pdf_template_service.get_template(match.template_id)
                if template.is_autoskip:
                    # Autoskip template - mark as skipped, no further processing needed
                    self.sub_run_repo.update(new_sub_run.id, {"status": "skipped"})
                    logger.info(
                        f"Sub-run {sub_run_id}: Created skipped sub-run {new_sub_run.id} "
                        f"for pages {match.matched_pages} (autoskip template '{template.name}')"
                    )
                else:
                    # Normal template - mark as matched, ready for extraction + pipeline
                    self.sub_run_repo.update(new_sub_run.id, {"status": "matched"})
                    logger.debug(
                        f"Sub-run {sub_run_id}: Created matched sub-run {new_sub_run.id} "
                        f"for pages {match.matched_pages} with template version {match.version_id}"
                    )

            # Create new sub-run for unmatched pages if any
            if match_result.unmatched_pages:
                unmatched_sub_run = self.sub_run_repo.create(EtoSubRunCreate(
                    eto_run_id=sub_run.eto_run_id,
                    matched_pages=json.dumps(match_result.unmatched_pages),
                    template_version_id=None,
                ))
                self.sub_run_repo.update(unmatched_sub_run.id, {"status": "needs_template"})
                logger.debug(
                    f"Sub-run {sub_run_id}: Created needs_template sub-run {unmatched_sub_run.id} "
                    f"for pages {match_result.unmatched_pages}"
                )

            # Delete the original sub-run (it has been split into new sub-runs)
            self.sub_run_repo.delete(sub_run_id)
            logger.debug(f"Sub-run {sub_run_id}: Deleted original sub-run after splitting")

            # Update parent run status
            self._update_parent_run_status(sub_run.eto_run_id)

            logger.monitor(
                f"Sub-run {sub_run_id}: Template matching completed - "
                f"created {len(match_result.matches)} matched + "
                f"{1 if match_result.unmatched_pages else 0} needs_template sub-runs"
            )
            return True

        except Exception as e:
            logger.error(f"Sub-run {sub_run_id}: Template matching error: {e}", exc_info=True)
            self._mark_sub_run_failure(sub_run_id, error=e, error_type="TemplateMatchingError")
            self._update_parent_run_status(sub_run.eto_run_id)
            return False

    def process_sub_run_extraction_pipeline(self, sub_run_id: int) -> bool:
        """
        Execute extraction + pipeline for a single sub-run (Worker Phase 2).
        Called by worker for sub-runs with status="matched".

        This is the renamed version of process_sub_run() for clarity.
        The implementation delegates to the existing process_sub_run() method.

        Args:
            sub_run_id: ETO sub-run ID to process

        Returns:
            True if successful, False if failed
        """
        return self.process_sub_run(sub_run_id)

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

    def _process_sub_run_pipeline(self, sub_run_id: int, extracted_data: list) -> PipelineExecutionResult:
        """
        Execute pipeline execution stage for a single sub-run.

        Executes the pipeline with extracted data, persisting step results and actions.
        Uses PRODUCTION mode (execute_actions=True) - actions actually execute.

        Args:
            sub_run_id: Sub-run ID
            extracted_data: Extracted data from previous stage (list of field dicts)

        Returns:
            PipelineExecutionResult containing output module data if present

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
        if template_version.pipeline_definition_id is None:
            raise ServiceError(
                f"Template version {sub_run.template_version_id} has no pipeline definition"
            )
        pipeline_definition = self.pipeline_execution_service.pipeline_repo.get_by_id(
            template_version.pipeline_definition_id
        )
        if not pipeline_definition:
            raise ServiceError(
                f"Pipeline definition {template_version.pipeline_definition_id} not found "
                f"for template version {sub_run.template_version_id}"
            )
        logger.debug(
            f"Sub-run {sub_run_id}: Retrieved pipeline definition {pipeline_definition.id}"
        )

        # Step 5: Get compiled steps
        compiled_steps = self.pipeline_execution_service.step_repo.get_steps_by_definition_id(
            pipeline_definition.id
        )
        if not compiled_steps:
            raise ServiceError(
                f"No compiled steps found for pipeline {pipeline_definition.id}"
            )
        logger.debug(
            f"Sub-run {sub_run_id}: Retrieved {len(compiled_steps)} compiled steps "
            f"for pipeline {pipeline_definition.id}"
        )

        # Step 6: Convert extracted_data list to dict format for pipeline execution
        # Pipeline expects: {field_name: extracted_value}
        extracted_data_dict = {
            result["name"]: result["extracted_value"]
            for result in extracted_data
        }

        # Step 7: Execute pipeline with PRODUCTION mode (execute_actions=True)
        execution_result: PipelineExecutionResult = self.pipeline_execution_service.execute_pipeline(
            steps=compiled_steps,  # type: ignore[arg-type]
            entry_values_by_name=extracted_data_dict,
            pipeline_state=pipeline_definition.pipeline_state
        )
        logger.debug(
            f"Sub-run {sub_run_id}: Pipeline execution completed with status={execution_result.status}, "
            f"{len(execution_result.steps)} steps"
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

        # Step 8b: Record output channel steps (pseudo-modules for visualization)
        # These indicate that data flowed out of the pipeline through these channels
        output_channel_values = execution_result.output_channel_values or {}
        if pipeline_definition.pipeline_state.output_channels and output_channel_values:
            # Calculate next step number after all module steps
            max_step_number = max((s.step_number for s in execution_result.steps), default=-1)
            output_channel_step_number = max_step_number + 1

            for output_channel in pipeline_definition.pipeline_state.output_channels:
                channel_type = output_channel.channel_type
                if channel_type in output_channel_values:
                    # Build input data for this output channel
                    collected_value = output_channel_values[channel_type]
                    input_pin = output_channel.inputs[0] if output_channel.inputs else None

                    # Serialize the collected value, handling datetime objects
                    inputs_data = {
                        input_pin.node_id if input_pin else "value": {
                            "name": input_pin.name if input_pin else "value",
                            "value": collected_value.isoformat() if hasattr(collected_value, 'isoformat') else collected_value,
                            "type": input_pin.type if input_pin else "str"
                        }
                    }

                    self.sub_run_pipeline_execution_step_repo.create(
                        EtoSubRunPipelineExecutionStepCreate(
                            pipeline_execution_id=pipeline_execution.id,
                            module_instance_id=output_channel.output_channel_instance_id,
                            step_number=output_channel_step_number,
                            inputs=json.dumps(inputs_data),
                            outputs=None,  # Output channels have no outputs
                            error=None
                        )
                    )

            logger.debug(f"Sub-run {sub_run_id}: Recorded {len(output_channel_values)} output channel steps")

        # Step 9: Update pipeline_execution record with final status and transformed_data
        completed_at = datetime.now(timezone.utc)
        final_status = "success" if execution_result.status == "success" else "failure"

        # Serialize output_channel_values as transformed_data JSON
        # Handle datetime objects by converting to ISO format strings
        def serialize_value(v):
            if hasattr(v, 'isoformat'):
                return v.isoformat()
            return v

        transformed_data_json = None
        if output_channel_values:
            transformed_data_dict = {k: serialize_value(v) for k, v in output_channel_values.items()}
            transformed_data_json = json.dumps(transformed_data_dict)

        self.sub_run_pipeline_execution_repo.update(
            pipeline_execution.id,
            {
                "status": final_status,
                "completed_at": completed_at,
                "transformed_data": transformed_data_json
            }
        )
        logger.debug(
            f"Sub-run {sub_run_id}: Updated pipeline_execution record to status={final_status}, "
            f"transformed_data keys: {list(output_channel_values.keys()) if output_channel_values else []}"
        )

        # Step 10: If pipeline failed, raise error to mark sub-run as failed
        if execution_result.status != "success":
            error_msg = execution_result.error or "Pipeline execution failed"
            logger.error(f"Sub-run {sub_run_id}: Pipeline execution failed: {error_msg}")
            raise ServiceError(f"Pipeline execution failed: {error_msg}")

        logger.monitor(f"Sub-run {sub_run_id}: Pipeline execution completed successfully")

        # Return execution result for output module processing
        return execution_result

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

    def _process_sub_run_output_execution(
        self,
        sub_run_id: int,
        output_channel_values: Dict[str, Any],
        customer_id: int,
    ) -> None:
        """
        Execute output channel processing stage for a single sub-run.

        Creates output execution record(s) for each HAWB and calls the
        OutputProcessingService to process them.

        Args:
            sub_run_id: Sub-run ID
            output_channel_values: Output channel values from pipeline execution
            customer_id: Customer ID from the template

        Raises:
            Exception: If output execution fails
        """
        logger.monitor(f"Sub-run {sub_run_id}: Executing output channel processing stage")

        # Step 1: Extract HAWB(s) from output channel values
        hawbs = self._extract_hawbs(output_channel_values)
        if not hawbs:
            logger.warning(f"Sub-run {sub_run_id}: No HAWB found in output channels, skipping output execution")
            return

        logger.debug(f"Sub-run {sub_run_id}: Found {len(hawbs)} HAWB(s) to process: {hawbs}")

        # Step 2: For each HAWB, create output execution record and process
        for hawb in hawbs:
            # Create output execution record with status="pending" (crash-safe)
            output_execution = self.sub_run_output_execution_repo.create(
                EtoSubRunOutputExecutionCreate(
                    sub_run_id=sub_run_id,
                    customer_id=customer_id,
                    hawb=str(hawb),
                    output_channel_data=output_channel_values,
                )
            )
            logger.debug(f"Sub-run {sub_run_id}: Created output_execution record {output_execution.id} for HAWB {hawb}")

            # Process via OutputProcessingService
            self.output_processing_service.process(output_execution.id)

        logger.monitor(f"Sub-run {sub_run_id}: Output execution completed for {len(hawbs)} HAWB(s)")

    def _extract_hawbs(self, output_channel_values: Dict[str, Any]) -> List[str]:
        """
        Extract HAWB value(s) from output channel values.

        Handles both single string and list of strings.

        Args:
            output_channel_values: Output channel values dict

        Returns:
            List of HAWB strings (may be empty if no HAWB found)
        """
        hawb_value = output_channel_values.get("hawb")

        if hawb_value is None:
            return []

        # Handle list of HAWBs
        if isinstance(hawb_value, list):
            return [str(h) for h in hawb_value if h]

        # Handle single HAWB string
        return [str(hawb_value)] if hawb_value else []

    # ==================== Helper Methods (Sub-Run) ====================

    def _mark_sub_run_success(self, sub_run_id: int) -> None:
        """
        Mark sub-run as successfully completed.

        Updates status to "success" and sets completed_at timestamp.

        Args:
            sub_run_id: Sub-run ID
        """
        logger.info(f"Sub-run {sub_run_id}: Marking as success")

        completed_at = datetime.now(timezone.utc)
        self.sub_run_repo.update(sub_run_id, {
            "status": "success",
            "completed_at": completed_at
        })

        # Get parent run ID for broadcast
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if sub_run:
            eto_event_manager.broadcast_sync("sub_run_updated", {
                "id": sub_run_id,
                "eto_run_id": sub_run.eto_run_id,
                "status": "success",
                "completed_at": completed_at.isoformat(),
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

        # Get parent run ID for broadcast
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if sub_run:
            eto_event_manager.broadcast_sync("sub_run_updated", {
                "id": sub_run_id,
                "eto_run_id": sub_run.eto_run_id,
                "status": "failure",
                "error_type": error_type,
                "error_message": error_message,
                "completed_at": completed_at.isoformat(),
            })

    def _update_parent_run_status(self, run_id: int) -> None:
        """
        Update parent run status based on all sub-run statuses.

        Status logic:
        - "processing": Has any sub-runs still being processed
          (status in: not_started, matched, processing)
        - "skipped": All sub-runs are in "skipped" status
        - "success": All sub-runs reached a terminal state
          (success, failure, needs_template, skipped) but not all skipped

        Note: Parent "failure" status is ONLY set for critical system errors,
        not for individual sub-run failures. Individual failures are tracked
        at the sub-run level.

        Side effect: When status changes, is_read is reset to False so users
        are notified of changes to runs they've already reviewed.

        Args:
            run_id: Parent ETO run ID
        """
        logger.debug(f"Run {run_id}: Updating parent status based on sub-runs")

        # Get current run status for comparison
        current_run = self.eto_run_repo.get_by_id(run_id)
        if not current_run:
            logger.warning(f"Run {run_id}: Run not found")
            return
        old_status = current_run.status

        # Get all sub-runs for parent
        sub_runs = self.sub_run_repo.get_by_eto_run_id(run_id)

        if not sub_runs:
            # No sub-runs - should not happen in normal flow
            logger.warning(f"Run {run_id}: No sub-runs found")
            return

        # Check if any sub-runs are still active (not yet at terminal state)
        # Active statuses: still being processed by worker
        # - not_started: waiting for Phase 1 (template matching)
        # - matched: waiting for Phase 2 (extraction + pipeline)
        # - processing: currently being processed
        active_statuses = {"not_started", "matched", "processing"}
        has_active = any(sub.status in active_statuses for sub in sub_runs)

        # Determine new status
        if has_active:
            new_status = "processing"
            completed_at = None
        else:
            # All sub-runs at terminal state - check if ALL are skipped
            all_skipped = all(sub.status == "skipped" for sub in sub_runs)
            if all_skipped:
                new_status = "skipped"
            else:
                new_status = "success"
            completed_at = datetime.now(timezone.utc)

        # Only update and broadcast if status changed
        if new_status != old_status:
            update_data: EtoRunUpdate = {"status": new_status}
            if completed_at:
                update_data["completed_at"] = completed_at
                # Set last_processed_at for stable list sorting (Item #5)
                # Only updated when run reaches terminal state, not during processing
                update_data["last_processed_at"] = completed_at

            # Reset is_read to False when status changes (Item #4)
            # This ensures users are notified of changes to runs they've reviewed
            if current_run.is_read:
                update_data["is_read"] = False
                logger.debug(f"Run {run_id}: Resetting is_read to False due to status change")

            self.eto_run_repo.update(run_id, update_data)

            # Broadcast run status change
            event_data = {
                "id": run_id,
                "status": new_status,
            }
            if completed_at:
                event_data["completed_at"] = completed_at.isoformat()

            eto_event_manager.broadcast_sync("run_updated", event_data)

            if new_status == "skipped":
                logger.info(f"Run {run_id}: All sub-runs skipped - marked as skipped")
            elif new_status == "success":
                logger.info(f"Run {run_id}: All sub-runs completed - marked as success")
            else:
                logger.debug(f"Run {run_id}: Status changed to '{new_status}'")

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
        Reprocess ETO runs (bulk operation at run level).

        New Architecture Workflow (for each run):
        1. Verify run exists
        2. Delete all existing sub-runs and their stage records
        3. Create a single new sub-run with all pages (status=not_started, no template)
        4. Reset parent run to "processing" status
        5. Worker Phase 1 will re-run template matching

        This is a "full reset" - starts from scratch with template matching.

        Args:
            run_ids: List of ETO run IDs to reprocess

        Raises:
            ObjectNotFoundError: If one or more runs not found
        """
        logger.info(f"Reprocessing {len(run_ids)} ETO runs: {run_ids}")

        # Validate all runs exist
        for run_id in run_ids:
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                raise ObjectNotFoundError(f"ETO run {run_id} not found")

        # Reprocess each run
        for run_id in run_ids:
            logger.debug(f"Reprocessing run {run_id}")

            # Get all sub-runs for this parent run
            sub_runs = self.sub_run_repo.get_by_eto_run_id(run_id)

            # Get PDF file to know total page count
            run = self.eto_run_repo.get_by_id(run_id)
            pdf_file = self.pdf_files_service.get_pdf_file(run.pdf_file_id)  # type: ignore

            # Delete all existing sub-runs (cascade deletes extraction/pipeline records)
            for sub_run in sub_runs:
                # Delete extraction record
                extraction = self.sub_run_extraction_repo.get_by_sub_run_id(sub_run.id)
                if extraction:
                    self.sub_run_extraction_repo.delete(extraction.id)

                # Delete pipeline execution record (cascade deletes steps)
                pipeline_execution = self.sub_run_pipeline_execution_repo.get_by_sub_run_id(sub_run.id)
                if pipeline_execution:
                    self.sub_run_pipeline_execution_repo.delete(pipeline_execution.id)

                # Delete the sub-run itself
                self.sub_run_repo.delete(sub_run.id)
                logger.debug(f"Deleted sub-run {sub_run.id}")

            # Create fresh sub-run with all pages (like create_run does)
            all_pages = list(range(1, (pdf_file.page_count or 0) + 1))
            self.sub_run_repo.create(EtoSubRunCreate(
                eto_run_id=run_id,
                matched_pages=json.dumps(all_pages),
                template_version_id=None,  # No template - Worker Phase 1 will match
            ))
            logger.debug(f"Created fresh sub-run for run {run_id} with {len(all_pages)} pages")

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

    # ==================== Run-Level Aggregated Operations ====================

    def reprocess_run(self, run_id: int) -> Optional[int]:
        """
        Reprocess all failed/needs_template sub-runs for a run by aggregating them into one new sub-run.

        Workflow:
        1. Get all sub-runs with status 'failure' or 'needs_template'
        2. Collect all their pages into a single list
        3. Clean up pending order contributions from those sub-runs
        4. Delete those sub-runs (with their child extraction/pipeline records)
        5. Create one new sub-run with all pages, status=not_started, no template
        6. Update parent run status to 'processing'

        The worker will pick up the new sub-run and run template matching (Phase 1).

        Args:
            run_id: ID of the ETO run to reprocess

        Returns:
            ID of the newly created sub-run, or None if no eligible sub-runs found

        Raises:
            ObjectNotFoundError: If run not found
        """
        logger.info(f"Reprocessing run {run_id} (aggregating failed/needs_template sub-runs)")

        # Validate run exists
        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            raise ObjectNotFoundError(f"ETO run {run_id} not found")

        # Get all sub-runs for this run
        all_sub_runs = self.sub_run_repo.get_by_eto_run_id(run_id)

        # Filter to only failure or needs_template sub-runs
        eligible_sub_runs = [
            sr for sr in all_sub_runs
            if sr.status in ("failure", "needs_template")
        ]

        if not eligible_sub_runs:
            logger.info(f"Run {run_id}: No eligible sub-runs to reprocess")
            return None

        # Collect all pages from eligible sub-runs
        all_pages: List[int] = []
        for sub_run in eligible_sub_runs:
            pages = json.loads(sub_run.matched_pages)
            all_pages.extend(pages)

        # Sort and dedupe pages
        all_pages = sorted(set(all_pages))
        logger.debug(f"Run {run_id}: Collected {len(all_pages)} pages from {len(eligible_sub_runs)} sub-runs")

        # Clean up pending order contributions BEFORE deleting the sub-runs
        for sub_run in eligible_sub_runs:
            cleanup_result = self.output_processing_service.cleanup_sub_run_contributions(sub_run.id)
            if cleanup_result["deleted_history_count"] > 0:
                logger.debug(f"Sub-run {sub_run.id} pending order cleanup: {cleanup_result}")

        # Use Unit of Work for atomic transaction
        with self.connection_manager.unit_of_work() as uow:
            # Delete all eligible sub-runs and their child records
            for sub_run in eligible_sub_runs:
                # Delete extraction record if exists
                extraction = uow.eto_sub_run_extractions.get_by_sub_run_id(sub_run.id)
                if extraction:
                    uow.eto_sub_run_extractions.delete(extraction.id)

                # Delete pipeline execution record if exists (cascade deletes steps)
                pipeline_execution = uow.eto_sub_run_pipeline_executions.get_by_sub_run_id(sub_run.id)
                if pipeline_execution:
                    uow.eto_sub_run_pipeline_executions.delete(pipeline_execution.id)

                # Delete the sub-run
                uow.eto_sub_runs.delete(sub_run.id)
                logger.debug(f"Deleted sub-run {sub_run.id}")

            # Create new sub-run with all collected pages, no template
            new_sub_run = uow.eto_sub_runs.create(EtoSubRunCreate(
                eto_run_id=run_id,
                matched_pages=json.dumps(all_pages),
                template_version_id=None,  # No template - Worker Phase 1 will match
            ))
            logger.debug(f"Created new sub-run {new_sub_run.id} with {len(all_pages)} pages")

        # Update parent run status
        self._update_parent_run_status(run_id)

        # Broadcast event
        eto_event_manager.broadcast_sync("run_reprocessed", {
            "run_id": run_id,
            "new_sub_run_id": new_sub_run.id,
            "pages_count": len(all_pages),
            "deleted_sub_run_count": len(eligible_sub_runs),
        })

        logger.monitor(
            f"Run {run_id}: Reprocessed {len(eligible_sub_runs)} sub-runs into new sub-run {new_sub_run.id} "
            f"with {len(all_pages)} pages"
        )
        return new_sub_run.id

    def skip_run(self, run_id: int) -> Optional[int]:
        """
        Skip all failed/needs_template sub-runs for a run by aggregating them into one skipped sub-run.

        Workflow:
        1. Get all sub-runs with status 'failure' or 'needs_template'
        2. Collect all their pages into a single list
        3. Clean up pending order contributions from those sub-runs
        4. Delete those sub-runs (with their child extraction/pipeline records)
        5. Create one new sub-run with all pages, status='skipped'
        6. Update parent run status

        Args:
            run_id: ID of the ETO run to skip

        Returns:
            ID of the newly created skipped sub-run, or None if no eligible sub-runs found

        Raises:
            ObjectNotFoundError: If run not found
        """
        logger.info(f"Skipping run {run_id} (aggregating failed/needs_template sub-runs)")

        # Validate run exists
        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            raise ObjectNotFoundError(f"ETO run {run_id} not found")

        # Get all sub-runs for this run
        all_sub_runs = self.sub_run_repo.get_by_eto_run_id(run_id)

        # Filter to only failure or needs_template sub-runs
        eligible_sub_runs = [
            sr for sr in all_sub_runs
            if sr.status in ("failure", "needs_template")
        ]

        if not eligible_sub_runs:
            logger.info(f"Run {run_id}: No eligible sub-runs to skip")
            return None

        # Collect all pages from eligible sub-runs
        all_pages: List[int] = []
        for sub_run in eligible_sub_runs:
            pages = json.loads(sub_run.matched_pages)
            all_pages.extend(pages)

        # Sort and dedupe pages
        all_pages = sorted(set(all_pages))
        logger.debug(f"Run {run_id}: Collected {len(all_pages)} pages from {len(eligible_sub_runs)} sub-runs")

        # Clean up pending order contributions BEFORE deleting the sub-runs
        for sub_run in eligible_sub_runs:
            cleanup_result = self.output_processing_service.cleanup_sub_run_contributions(sub_run.id)
            if cleanup_result["deleted_history_count"] > 0:
                logger.debug(f"Sub-run {sub_run.id} pending order cleanup: {cleanup_result}")

        # Use Unit of Work for atomic transaction
        with self.connection_manager.unit_of_work() as uow:
            # Delete all eligible sub-runs and their child records
            for sub_run in eligible_sub_runs:
                # Delete extraction record if exists
                extraction = uow.eto_sub_run_extractions.get_by_sub_run_id(sub_run.id)
                if extraction:
                    uow.eto_sub_run_extractions.delete(extraction.id)

                # Delete pipeline execution record if exists (cascade deletes steps)
                pipeline_execution = uow.eto_sub_run_pipeline_executions.get_by_sub_run_id(sub_run.id)
                if pipeline_execution:
                    uow.eto_sub_run_pipeline_executions.delete(pipeline_execution.id)

                # Delete the sub-run
                uow.eto_sub_runs.delete(sub_run.id)
                logger.debug(f"Deleted sub-run {sub_run.id}")

            # Create new sub-run with all collected pages, status=skipped
            new_sub_run = uow.eto_sub_runs.create(EtoSubRunCreate(
                eto_run_id=run_id,
                matched_pages=json.dumps(all_pages),
                template_version_id=None,
            ))
            # Update status to skipped
            uow.eto_sub_runs.update(new_sub_run.id, {"status": "skipped"})
            logger.debug(f"Created new skipped sub-run {new_sub_run.id} with {len(all_pages)} pages")

        # Update parent run status
        self._update_parent_run_status(run_id)

        # Broadcast event
        eto_event_manager.broadcast_sync("run_skipped", {
            "run_id": run_id,
            "new_sub_run_id": new_sub_run.id,
            "pages_count": len(all_pages),
            "deleted_sub_run_count": len(eligible_sub_runs),
        })

        logger.monitor(
            f"Run {run_id}: Skipped {len(eligible_sub_runs)} sub-runs into new sub-run {new_sub_run.id} "
            f"with {len(all_pages)} pages"
        )
        return new_sub_run.id

    # ==================== Sub-Run Level Operations ====================

    def reprocess_sub_run(self, sub_run_id: int) -> int:
        """
        Reprocess a single sub-run by deleting it and creating a new one with the same pages.

        Uses Unit of Work pattern for atomic transaction:
        1. Clean up pending order contributions from this sub-run
        2. Get sub-run to retrieve pages and parent run ID
        3. Delete extraction record if exists
        4. Delete pipeline execution record if exists
        5. Delete the sub-run itself
        6. Create new sub-run with same pages, status=not_started, no template
        7. Update parent run status

        The worker will pick up the new sub-run and run template matching (Phase 1).

        Args:
            sub_run_id: ID of sub-run to reprocess

        Returns:
            ID of the newly created sub-run

        Raises:
            ObjectNotFoundError: If sub-run not found
        """
        logger.info(f"Reprocessing sub-run {sub_run_id}")

        # First get the sub-run outside UoW to validate it exists
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if not sub_run:
            raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

        parent_run_id = sub_run.eto_run_id
        matched_pages = sub_run.matched_pages  # Already JSON string

        # Clean up pending order contributions BEFORE deleting the sub-run
        # This ensures history records are properly cleaned up while sub_run_id still exists
        cleanup_result = self.output_processing_service.cleanup_sub_run_contributions(sub_run_id)
        logger.debug(f"Pending order cleanup result: {cleanup_result}")

        # Use Unit of Work for atomic transaction
        with self.connection_manager.unit_of_work() as uow:
            # Delete extraction record if exists
            extraction = uow.eto_sub_run_extractions.get_by_sub_run_id(sub_run_id)
            if extraction:
                uow.eto_sub_run_extractions.delete(extraction.id)
                logger.debug(f"Deleted extraction record for sub-run {sub_run_id}")

            # Delete pipeline execution record if exists (cascade deletes steps)
            pipeline_execution = uow.eto_sub_run_pipeline_executions.get_by_sub_run_id(sub_run_id)
            if pipeline_execution:
                uow.eto_sub_run_pipeline_executions.delete(pipeline_execution.id)
                logger.debug(f"Deleted pipeline execution record for sub-run {sub_run_id}")

            # Delete the sub-run
            uow.eto_sub_runs.delete(sub_run_id)
            logger.debug(f"Deleted sub-run {sub_run_id}")

            # Create new sub-run with same pages, no template
            new_sub_run = uow.eto_sub_runs.create(EtoSubRunCreate(
                eto_run_id=parent_run_id,
                matched_pages=matched_pages,
                template_version_id=None,  # No template - Worker Phase 1 will match
            ))
            logger.debug(f"Created new sub-run {new_sub_run.id} with pages {matched_pages}")

        # Update parent run status (outside UoW - uses separate transaction)
        self._update_parent_run_status(parent_run_id)

        # Broadcast event
        eto_event_manager.broadcast_sync("sub_run_reprocessed", {
            "old_sub_run_id": sub_run_id,
            "new_sub_run_id": new_sub_run.id,
            "eto_run_id": parent_run_id,
        })

        logger.monitor(f"Sub-run {sub_run_id}: Reprocessed as new sub-run {new_sub_run.id}")
        return new_sub_run.id

    def skip_sub_run(self, sub_run_id: int) -> int:
        """
        Skip a single sub-run by deleting it and creating a new one with status='skipped'.

        Uses Unit of Work pattern for atomic transaction:
        1. Clean up pending order contributions from this sub-run
        2. Get sub-run to retrieve pages and parent run ID
        3. Delete extraction record if exists
        4. Delete pipeline execution record if exists
        5. Delete the sub-run itself
        6. Create new sub-run with same pages, status='skipped'
        7. Update parent run status

        Args:
            sub_run_id: ID of sub-run to skip

        Returns:
            ID of the newly created skipped sub-run

        Raises:
            ObjectNotFoundError: If sub-run not found
            ValidationError: If sub-run has invalid status for skipping
        """
        logger.info(f"Skipping sub-run {sub_run_id}")

        # First get the sub-run outside UoW to validate it exists
        sub_run = self.sub_run_repo.get_by_id(sub_run_id)
        if not sub_run:
            raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

        # Validate status - can only skip failure or needs_template sub-runs
        if sub_run.status not in ("failure", "needs_template"):
            raise ValidationError(
                f"Cannot skip sub-run {sub_run_id} with status '{sub_run.status}'. "
                f"Only 'failure' and 'needs_template' sub-runs can be skipped."
            )

        parent_run_id = sub_run.eto_run_id
        matched_pages = sub_run.matched_pages  # Already JSON string

        # Clean up pending order contributions BEFORE deleting the sub-run
        cleanup_result = self.output_processing_service.cleanup_sub_run_contributions(sub_run_id)
        logger.debug(f"Pending order cleanup result: {cleanup_result}")

        # Use Unit of Work for atomic transaction
        with self.connection_manager.unit_of_work() as uow:
            # Delete extraction record if exists
            extraction = uow.eto_sub_run_extractions.get_by_sub_run_id(sub_run_id)
            if extraction:
                uow.eto_sub_run_extractions.delete(extraction.id)
                logger.debug(f"Deleted extraction record for sub-run {sub_run_id}")

            # Delete pipeline execution record if exists (cascade deletes steps)
            pipeline_execution = uow.eto_sub_run_pipeline_executions.get_by_sub_run_id(sub_run_id)
            if pipeline_execution:
                uow.eto_sub_run_pipeline_executions.delete(pipeline_execution.id)
                logger.debug(f"Deleted pipeline execution record for sub-run {sub_run_id}")

            # Delete the sub-run
            uow.eto_sub_runs.delete(sub_run_id)
            logger.debug(f"Deleted sub-run {sub_run_id}")

            # Create new sub-run with same pages, status=skipped
            new_sub_run = uow.eto_sub_runs.create(EtoSubRunCreate(
                eto_run_id=parent_run_id,
                matched_pages=matched_pages,
                template_version_id=None,
            ))
            # Update status to skipped
            uow.eto_sub_runs.update(new_sub_run.id, {"status": "skipped"})
            logger.debug(f"Created new skipped sub-run {new_sub_run.id} with pages {matched_pages}")

        # Update parent run status (outside UoW - uses separate transaction)
        self._update_parent_run_status(parent_run_id)

        # Broadcast event
        eto_event_manager.broadcast_sync("sub_run_skipped", {
            "old_sub_run_id": sub_run_id,
            "new_sub_run_id": new_sub_run.id,
            "eto_run_id": parent_run_id,
        })

        logger.monitor(f"Sub-run {sub_run_id}: Skipped as new sub-run {new_sub_run.id}")
        return new_sub_run.id

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