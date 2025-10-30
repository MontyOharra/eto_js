"""
ETO Runs Service
Business logic for ETO run lifecycle and orchestration
"""
import asyncio
import json
import logging
import os
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone

from shared.database import DatabaseConnectionManager
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_run_pipeline_execution import EtoRunPipelineExecutionRepository
from shared.database.repositories.eto_run_template_matching import EtoRunTemplateMatchingRepository
from shared.database.repositories.eto_run_extraction import EtoRunExtractionRepository
from shared.events.eto_events import eto_event_manager
# TODO: Import remaining repositories when implemented
# from shared.database.repositories.eto_run_pipeline_execution_step import EtoRunPipelineExecutionStepRepository

from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunStatus,
    EtoProcessingStep,
    EtoRunListView,
)
from shared.types.eto_run_pipeline_executions import (
    EtoRunPipelineExecution,
    EtoRunPipelineExecutionCreate,
    EtoRunPipelineExecutionUpdate,
)
from shared.types.eto_run_template_matchings import (
    EtoRunTemplateMatching,
    EtoRunTemplateMatchingCreate,
    EtoRunTemplateMatchingUpdate,
)
from shared.types.eto_run_extractions import (
    EtoRunExtraction,
    EtoRunExtractionCreate,
    EtoRunExtractionUpdate,
    EtoStepStatus,
)

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

logger = logging.getLogger(__name__)


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
    pipeline_execution_repo: EtoRunPipelineExecutionRepository
    template_matching_repo: EtoRunTemplateMatchingRepository
    extraction_repo: EtoRunExtractionRepository
    # TODO: Add remaining repositories when implemented
    # pipeline_execution_step_repo: EtoRunPipelineExecutionStepRepository

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
        self.pipeline_execution_repo: EtoRunPipelineExecutionRepository = EtoRunPipelineExecutionRepository(connection_manager=connection_manager)
        self.template_matching_repo: EtoRunTemplateMatchingRepository = EtoRunTemplateMatchingRepository(connection_manager=connection_manager)
        self.extraction_repo: EtoRunExtractionRepository = EtoRunExtractionRepository(connection_manager=connection_manager)

        # TODO: Initialize remaining repositories when implemented
        # self.pipeline_execution_step_repo = EtoRunPipelineExecutionStepRepository(connection_manager=connection_manager)

        # Worker configuration from environment
        self.worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
        self.max_concurrent_runs = int(os.getenv('ETO_MAX_CONCURRENT_RUNS', '10'))
        self.polling_interval = int(os.getenv('ETO_POLLING_INTERVAL', '2'))  # seconds
        self.shutdown_timeout = int(os.getenv('ETO_SHUTDOWN_TIMEOUT', '30'))  # seconds

        # Worker state
        self.worker_running = False
        self.worker_paused = False
        self.worker_task: Optional[asyncio.Task] = None
        self.currently_processing_runs: Set[int] = set()

        logger.info(
            f"EtoRunsService initialized successfully - "
            f"worker_enabled: {self.worker_enabled}, "
            f"polling_interval: {self.polling_interval}s, "
            f"max_concurrent: {self.max_concurrent_runs}"
        )

    # ==================== Public API Methods ====================

    def create_run(self, pdf_file_id: int) -> EtoRun:
        """
        Create new ETO run with status = "not_started".
        Called by email ingestion service when new PDF is received.

        Args:
            pdf_file_id: ID of PDF file to process

        Returns:
            Created EtoRun dataclass

        Raises:
            ObjectNotFoundError: If PDF file doesn't exist
            ServiceError: If run creation fails
        """
        logger.info(f"Creating ETO run for PDF file {pdf_file_id}")

        try:
            # Validate PDF file exists
            pdf_file = self.pdf_files_service.get_pdf_file(pdf_file_id)
            logger.debug(f"Validated PDF file {pdf_file_id} exists (hash: {pdf_file.file_hash})")

            # Create run with status = "not_started"
            run = self.eto_run_repo.create(EtoRunCreate(pdf_file_id=pdf_file_id))

            # Broadcast creation event to all connected SSE clients
            eto_event_manager.broadcast_sync(
                "run_created",
                {
                    "id": run.id,
                    "pdf_file_id": run.pdf_file_id,
                    "status": run.status,
                    "processing_step": run.processing_step,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                }
            )

            logger.info(f"Created ETO run {run.id} for PDF {pdf_file_id}")
            return run

        except ObjectNotFoundError:
            # Re-raise 404 errors as-is
            logger.warning(f"Cannot create ETO run: PDF file {pdf_file_id} not found")
            raise

        except Exception as e:
            logger.error(f"Failed to create ETO run for PDF {pdf_file_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to create ETO run: {str(e)}") from e

    def list_runs(
        self,
        status: Optional[EtoRunStatus] = None,
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

            logger.monitor(f"Retrieved {len(runs)} ETO runs")  # type: ignore
            return runs

        except Exception as e:
            logger.error(f"Failed to list ETO runs: {e}", exc_info=True)
            raise ServiceError(f"Failed to list ETO runs: {str(e)}") from e

    def list_runs_with_relations(
        self,
        status: Optional[EtoRunStatus] = None,
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

            logger.monitor(f"Retrieved {len(runs)} ETO runs with relations")  # type: ignore
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

    def get_run_detail(self, run_id: int) -> "EtoRunDetailView":
        """
        Get ETO run with all related data for detailed view.

        Fetches:
        - Core run data
        - PDF file info and email source (if applicable)
        - Stage 1: Template matching data (if exists)
        - Stage 2: Data extraction data (if exists)
        - Stage 3: Pipeline execution data (if exists)
        - Matched template info (denormalized for convenience)

        Args:
            run_id: ETO run ID

        Returns:
            EtoRunDetailView with all related data

        Raises:
            ObjectNotFoundError: If run not found
        """
        from shared.types.eto_runs import EtoRunDetailView

        logger.debug(f"Getting detailed view for ETO run {run_id}")

        # 1. Get core run data
        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            raise ObjectNotFoundError(f"ETO run {run_id} not found")

        # 2. Get PDF file info
        pdf_file = self.pdf_files_service.get_pdf_file(run.pdf_file_id)

        # 3. Get email source info (if applicable)
        email_id = None
        email_sender = None
        email_received_date = None
        email_subject = None
        email_folder = None

        if pdf_file.email_id:
            # PDF was from email ingestion
            from shared.services.service_container import ServiceContainer
            email_service = ServiceContainer.get_email_service()
            email = email_service.get_email(pdf_file.email_id)
            if email:
                email_id = email.id
                email_sender = email.sender_email
                email_received_date = email.received_date
                email_subject = email.subject
                email_folder = email.folder_name

        # 4. Get stage data (if exists)
        template_matching = self.template_matching_repo.get_by_eto_run_id(run_id)
        extraction = self.extraction_repo.get_by_eto_run_id(run_id)
        pipeline_execution = self.pipeline_execution_repo.get_by_eto_run_id(run_id)

        # 5. Get matched template info (if template matching succeeded)
        matched_template_id = None
        matched_template_name = None
        matched_template_version_id = None
        matched_template_version_num = None

        if template_matching and template_matching.matched_template_version_id:
            # Get template version to find template ID
            template_version = self.pdf_template_service.get_version(
                template_matching.matched_template_version_id
            )
            if template_version:
                matched_template_version_id = template_version.id
                matched_template_version_num = template_version.version_number

                # Get template to get name
                template = self.pdf_template_service.get_template(template_version.template_id)
                if template:
                    matched_template_id = template.id
                    matched_template_name = template.name

        # 6. Compose the detailed view
        detail_view = EtoRunDetailView(
            run=run,
            # PDF file info
            pdf_file_id=pdf_file.id,
            pdf_original_filename=pdf_file.original_filename,
            pdf_file_size=pdf_file.file_size,
            pdf_page_count=pdf_file.page_count,
            # Email source info
            email_id=email_id,
            email_sender_email=email_sender,
            email_received_date=email_received_date,
            email_subject=email_subject,
            email_folder_name=email_folder,
            # Stage data
            template_matching=template_matching,
            extraction=extraction,
            pipeline_execution=pipeline_execution,
            # Matched template info
            matched_template_id=matched_template_id,
            matched_template_name=matched_template_name,
            matched_template_version_id=matched_template_version_id,
            matched_template_version_num=matched_template_version_num,
        )

        logger.debug(f"Retrieved detailed view for ETO run {run_id}")
        return detail_view

    # ==================== Bulk Operation Methods ====================

    def reprocess_runs(self, run_ids: list[int]) -> None:
        """
        Reprocess failed or skipped ETO runs (bulk operation).

        Workflow (for each run):
        1. Verify run exists and status is "failure" or "skipped"
        2. Delete all stage records (template_matching, extraction, pipeline_execution)
        3. Reset run to "not_started" status
        4. Clear error fields
        5. Worker will automatically pick up and reprocess from beginning

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

            if run.status not in ("failure", "skipped"):
                raise ValidationError(
                    f"Cannot reprocess run {run_id} with status '{run.status}'. "
                    f"Only 'failure' and 'skipped' runs can be reprocessed."
                )

        # Reprocess each run
        for run_id in run_ids:
            logger.debug(f"Reprocessing run {run_id}")

            # Delete stage records (cascade delete should handle related records)
            # Template matching
            matching = self.template_matching_repo.get_by_eto_run_id(run_id)
            if matching:
                self.template_matching_repo.delete(matching.id)
                logger.debug(f"Deleted template_matching record for run {run_id}")

            # Extraction
            extraction = self.extraction_repo.get_by_eto_run_id(run_id)
            if extraction:
                self.extraction_repo.delete(extraction.id)
                logger.debug(f"Deleted extraction record for run {run_id}")

            # Pipeline execution (and steps)
            pipeline_execution = self.pipeline_execution_repo.get_by_eto_run_id(run_id)
            if pipeline_execution:
                self.pipeline_execution_repo.delete(pipeline_execution.id)
                logger.debug(f"Deleted pipeline_execution record for run {run_id}")

            # Reset run to not_started status
            self.eto_run_repo.update(
                run_id,
                EtoRunUpdate(
                    status="not_started",
                    processing_step=None,
                    error_type=None,
                    error_message=None,
                    error_details=None,
                    started_at=None,
                    completed_at=None,
                )
            )

            # Broadcast status change
            eto_event_manager.broadcast_sync(
                "run_updated",
                {
                    "id": run_id,
                    "status": "not_started",
                }
            )

            logger.monitor(f"Run {run_id}: Reset to not_started for reprocessing")  # type: ignore

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

            logger.monitor(f"Run {run_id}: Marked as skipped")  # type: ignore

        logger.info(f"Successfully skipped {len(run_ids)} ETO runs")

    def delete_runs(self, run_ids: list[int]) -> None:
        """
        Permanently delete ETO runs (bulk operation).

        Workflow (for each run):
        1. Verify run exists and status is "skipped"
        2. Delete all stage records (cascade delete)
        3. Delete run record
        4. Note: PDF file is NOT deleted (may be referenced elsewhere)

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

        # Delete each run
        for run_id in run_ids:
            logger.debug(f"Deleting run {run_id}")

            # Delete stage records first (explicit cascade)
            # Template matching
            matching = self.template_matching_repo.get_by_eto_run_id(run_id)
            if matching:
                self.template_matching_repo.delete(matching.id)
                logger.debug(f"Deleted template_matching record for run {run_id}")

            # Extraction
            extraction = self.extraction_repo.get_by_eto_run_id(run_id)
            if extraction:
                self.extraction_repo.delete(extraction.id)
                logger.debug(f"Deleted extraction record for run {run_id}")

            # Pipeline execution (and steps)
            pipeline_execution = self.pipeline_execution_repo.get_by_eto_run_id(run_id)
            if pipeline_execution:
                self.pipeline_execution_repo.delete(pipeline_execution.id)
                logger.debug(f"Deleted pipeline_execution record for run {run_id}")

            # Delete the run itself
            self.eto_run_repo.delete(run_id)

            # Broadcast deletion event
            eto_event_manager.broadcast_sync(
                "run_deleted",
                {
                    "id": run_id,
                }
            )

            logger.monitor(f"Run {run_id}: Permanently deleted")  # type: ignore

        logger.info(f"Successfully deleted {len(run_ids)} ETO runs")

    # ==================== Processing Methods (Worker) ====================

    def process_run(self, run_id: int) -> bool:
        """
        Execute full 3-stage ETO workflow for a run.
        Called by ETO worker for runs with status = "not_started".

        Workflow:
        1. Update status to "processing"
        2. Execute Stage 1: Template Matching (with error handling)
        3. Execute Stage 2: Data Extraction (with error handling)
        4. Execute Stage 3: Data Transformation (with error handling)
        5. Update status to "success" or "failure"

        Error Handling:
        - Each stage wrapped in try-except to catch stage-specific errors
        - Stage errors marked with specific error_type (TemplateMatchingError, etc.)
        - Outer try-except catches unexpected errors (syntax, type errors, etc.)
        - All errors update run status to "failure" with error details

        Args:
            run_id: ETO run ID to process

        Returns:
            True if successful, False if failed
        """
        logger.monitor(f"Starting ETO processing for run {run_id}")  # type: ignore

            # Get run and validate existence
        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            logger.error(f"ETO run {run_id} not found")
            raise ObjectNotFoundError(f"ETO run {run_id} not found")


        try:
            # Update to processing status
            started_at = datetime.now(timezone.utc)
            self.eto_run_repo.update(
                run_id,
                EtoRunUpdate(
                    status="processing",
                    started_at=started_at
                )
            )

            # Broadcast status change to SSE clients
            eto_event_manager.broadcast_sync(
                "run_updated",
                {
                    "id": run_id,
                    "status": "processing",
                    "started_at": started_at.isoformat(),
                }
            )

            # Stage 1: Template Matching
            try:
                logger.monitor(f"Run {run_id}: Starting template matching stage")  # type: ignore
                if not self._execute_template_matching(run_id):
                    # Stage method returned False (handled its own error internally)
                    return False
            except Exception as e:
                logger.error(f"Run {run_id}: Template matching stage error: {e}", exc_info=True)
                self._mark_run_failure(run_id, error=e, error_type="TemplateMatchingError")
                return False

            # Stage 2: Data Extraction
            try:
                logger.monitor(f"Run {run_id}: Starting data extraction stage")  # type: ignore
                if not self._execute_data_extraction(run_id):
                    # Stage method returned False (handled its own error internally)
                    return False
            except Exception as e:
                logger.error(f"Run {run_id}: Data extraction stage error: {e}", exc_info=True)
                self._mark_run_failure(run_id, error=e, error_type="DataExtractionError")
                return False

            # Stage 3: Data Transformation
            try:
                logger.monitor(f"Run {run_id}: Starting data transformation stage")  # type: ignore
                if not self._execute_data_transformation(run_id):
                    # Stage method returned False (handled its own error internally)
                    return False
            except Exception as e:
                logger.error(f"Run {run_id}: Data transformation stage error: {e}", exc_info=True)
                self._mark_run_failure(run_id, error=e, error_type="DataTransformationError")
                return False

            # All stages completed successfully
            self._mark_run_success(run_id)
            logger.monitor(f"Run {run_id}: All stages completed successfully")  # type: ignore
            return True

        except Exception as e:
            # Catch unexpected errors not related to stage processing
            # (e.g., syntax errors, type errors, database connection issues)
            logger.error(f"Run {run_id}: Unexpected system error: {e}", exc_info=True)
            self._mark_run_failure(run_id, error=e, error_type="UnexpectedSystemError")
            return False

    def _execute_template_matching(self, run_id: int) -> bool:
        """
        Execute Stage 1: Template Matching.

        Process:
        1. Update run processing_step to "template_matching"
        2. Create template_matching record with status="processing"
        3. Get PDF objects from PDF file
        4. Call PDF template service to match PDF
        5. Update template_matching record with result
        6. If no match: update run status to "needs_template"

        Args:
            run_id: ETO run ID

        Returns:
            True if match found and successful, False if no match or needs_template

        Raises:
            Exception: If unexpected error occurs (caught by process_run)
        """
        logger.monitor(f"Run {run_id}: Executing template matching stage")  # type: ignore

        # Step 1: Update run processing_step
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(processing_step="template_matching")
        )
        logger.debug(f"Run {run_id}: Updated processing_step to template_matching")

        # Broadcast processing step change
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "processing_step": "template_matching",
            }
        )

        # Step 2: Create template_matching record with status="processing"
        started_at = datetime.now(timezone.utc)
        template_matching = self.template_matching_repo.create(
            EtoRunTemplateMatchingCreate(eto_run_id=run_id)
        )
        logger.debug(f"Run {run_id}: Created template_matching record {template_matching.id}")

        # Step 2b: Update with started_at timestamp
        template_matching = self.template_matching_repo.update(
            template_matching.id,
            EtoRunTemplateMatchingUpdate(started_at=started_at)
        )
        logger.debug(f"Run {run_id}: Set template_matching started_at")

        try:
            # Step 3: Get PDF objects from PDF file
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                raise ServiceError(f"Run {run_id} not found")

            pdf_objects = self.pdf_files_service.get_pdf_objects(run.pdf_file_id)
            logger.debug(f"Run {run_id}: Retrieved PDF objects from file {run.pdf_file_id}")

            # Step 4: Call template matching service
            match_result = self.pdf_template_service.match_template(pdf_objects)

            # Step 5: Handle match result
            if match_result is None:
                # No template matched
                logger.monitor(f"Run {run_id}: No template match found")  # type: ignore

                # Update template_matching record to failure
                self.template_matching_repo.update(
                    template_matching.id,
                    EtoRunTemplateMatchingUpdate(
                        status="failure",
                        completed_at=datetime.now(timezone.utc)
                    )
                )

                # Update run status to "needs_template"
                completed_at = datetime.now(timezone.utc)
                self.eto_run_repo.update(
                    run_id,
                    EtoRunUpdate(
                        status="needs_template",
                        completed_at=completed_at,
                        error_type="NoTemplateMatch",
                        error_message="No matching template found for this PDF"
                    )
                )

                # Broadcast status change
                eto_event_manager.broadcast_sync(
                    "run_updated",
                    {
                        "id": run_id,
                        "status": "needs_template",
                        "completed_at": completed_at.isoformat(),
                        "error_type": "NoTemplateMatch",
                        "error_message": "No matching template found for this PDF"
                    }
                )

                logger.warning(f"Run {run_id}: Set status to needs_template - no template match")
                return False

            # Match found!
            template_id, version_id = match_result
            logger.monitor(f"Run {run_id}: Template match found - template {template_id}, version {version_id}")  # type: ignore

            # Update template_matching record to success
            self.template_matching_repo.update(
                template_matching.id,
                EtoRunTemplateMatchingUpdate(
                    status="success",
                    matched_template_version_id=version_id,
                    completed_at=datetime.now(timezone.utc)
                )
            )

            logger.monitor(f"Run {run_id}: Template matching completed successfully")  # type: ignore
            return True

        except Exception as e:
            # Error during template matching
            logger.error(f"Run {run_id}: Template matching error: {e}", exc_info=True)

            # Update template_matching record to failure
            self.template_matching_repo.update(
                template_matching.id,
                EtoRunTemplateMatchingUpdate(
                    status="failure",
                    completed_at=datetime.now(timezone.utc)
                )
            )

            # Re-raise to be caught by process_run's error handling
            raise

    def _execute_data_extraction(self, run_id: int) -> bool:
        """
        Execute Stage 2: Data Extraction (STUB FOR TESTING).

        Creates extraction record with FAKE data to allow end-to-end testing
        of template matching stage.

        Process:
        1. Update run processing_step to "data_extraction"
        2. Create extraction record with status="processing"
        3. Populate with fake extracted data
        4. Update extraction record to success

        Args:
            run_id: ETO run ID

        Returns:
            True (always succeeds with fake data)
        """
        logger.monitor(f"Run {run_id}: Executing data extraction stage (STUB - FAKE DATA)")  # type: ignore

        # Step 1: Update run processing_step
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(processing_step="data_extraction")
        )
        logger.debug(f"Run {run_id}: Updated processing_step to data_extraction")

        # Broadcast processing step change
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "processing_step": "data_extraction",
            }
        )

        # Step 2: Create extraction record
        extraction = self.extraction_repo.create(
            EtoRunExtractionCreate(eto_run_id=run_id)
        )
        logger.debug(f"Run {run_id}: Created extraction record {extraction.id}")

        # Step 3: Generate fake extracted data
        fake_extracted_data = {
            "invoice_number": "FAKE-INV-12345",
            "invoice_date": "2025-10-29",
            "vendor_name": "Test Vendor Inc.",
            "total_amount": "1234.56",
            "line_items": [
                {"description": "Test Item 1", "quantity": "2", "price": "500.00"},
                {"description": "Test Item 2", "quantity": "1", "price": "234.56"}
            ]
        }

        # Step 4: Update extraction record with fake data
        self.extraction_repo.update(
            extraction.id,
            EtoRunExtractionUpdate(
                status="success",
                extracted_data=json.dumps(fake_extracted_data),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.monitor(f"Run {run_id}: Data extraction completed (STUB - FAKE DATA)")  # type: ignore
        return True

    def _execute_data_transformation(self, run_id: int) -> bool:
        """
        Execute Stage 3: Data Transformation (STUB FOR TESTING).

        Creates pipeline execution record with FAKE data to allow end-to-end
        testing of template matching stage.

        Process:
        1. Update run processing_step to "data_transformation"
        2. Create pipeline_execution record with status="processing"
        3. Populate with fake executed actions
        4. Update pipeline_execution record to success

        Args:
            run_id: ETO run ID

        Returns:
            True (always succeeds with fake data)
        """
        logger.monitor(f"Run {run_id}: Executing data transformation stage (STUB - FAKE DATA)")  # type: ignore

        # Step 1: Update run processing_step
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(processing_step="data_transformation")
        )
        logger.debug(f"Run {run_id}: Updated processing_step to data_transformation")

        # Broadcast processing step change
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "processing_step": "data_transformation",
            }
        )

        # Step 2: Create pipeline_execution record
        pipeline_execution = self.pipeline_execution_repo.create(
            EtoRunPipelineExecutionCreate(
                eto_run_id=run_id,
                started_at=datetime.now(timezone.utc)
            )
        )
        logger.debug(f"Run {run_id}: Created pipeline_execution record {pipeline_execution.id}")

        # Step 3: Generate fake executed actions
        fake_executed_actions = {
            "steps_executed": [
                {"step": "validate_invoice", "status": "success", "output": "Invoice validated"},
                {"step": "transform_format", "status": "success", "output": "Format transformed"},
                {"step": "calculate_totals", "status": "success", "output": "Totals calculated"}
            ],
            "total_steps": 3,
            "successful_steps": 3,
            "failed_steps": 0
        }

        # Step 4: Update pipeline_execution record with fake data
        self.pipeline_execution_repo.update(
            pipeline_execution.id,
            EtoRunPipelineExecutionUpdate(
                status="success",
                executed_actions=json.dumps(fake_executed_actions),
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.monitor(f"Run {run_id}: Data transformation completed (STUB - FAKE DATA)")  # type: ignore
        return True

    # ==================== Helper Methods ====================

    def _mark_run_success(self, run_id: int) -> None:
        """
        Mark ETO run as successfully completed.

        Args:
            run_id: ETO run ID
        """
        completed_at = datetime.now(timezone.utc)
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(
                status="success",
                completed_at=completed_at
            )
        )

        # Broadcast success status
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "status": "success",
                "completed_at": completed_at.isoformat(),
            }
        )

        logger.monitor(f"Run {run_id}: Marked as success")  # type: ignore

    def _mark_run_failure(self, run_id: int, error: Exception, error_type: Optional[str] = None) -> None:
        """
        Mark ETO run as failed and record error details.

        Args:
            run_id: ETO run ID
            error: Exception that caused failure
            error_type: Error category (optional, inferred from exception if not provided)
        """
        # Infer error type if not provided
        if error_type is None:
            error_type = type(error).__name__

        completed_at = datetime.now(timezone.utc)
        error_message = str(error)

        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(
                status="failure",
                completed_at=completed_at,
                error_type=error_type,
                error_message=error_message,
                error_details=None  # TODO: Add stack trace or additional context if needed
            )
        )

        # Broadcast failure status
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "status": "failure",
                "completed_at": completed_at.isoformat(),
                "error_type": error_type,
                "error_message": error_message,
            }
        )

        logger.warning(f"Run {run_id}: Marked as failure - {error_type}: {error}")

    # ==================== Background Worker Lifecycle ====================

    async def startup(self) -> bool:
        """
        Start the background processing worker.
        Called during application startup.

        Returns:
            True if worker started, False if disabled or already running
        """
        if not self.worker_enabled:
            logger.info("ETO worker is disabled by configuration (ETO_WORKER_ENABLED=false)")
            return False

        if self.worker_running:
            logger.warning("ETO worker is already running")
            return False

        self.worker_running = True
        self.worker_paused = False
        self.worker_task = asyncio.create_task(self._continuous_processing_loop())
        logger.info("ETO background worker started")
        return True

    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Stop the background processing worker.
        Called during application shutdown.

        Args:
            graceful: If True, wait for current batch to complete

        Returns:
            True if stopped successfully
        """
        if not self.worker_running:
            logger.warning("ETO worker is not running")
            return False

        logger.info(f"Stopping ETO worker (graceful={graceful})...")
        self.worker_running = False

        if graceful and self.worker_task:
            # Give current batch time to finish
            try:
                await asyncio.wait_for(self.worker_task, timeout=self.shutdown_timeout)
                logger.info("ETO worker stopped gracefully - current batch completed")
            except asyncio.TimeoutError:
                logger.warning(
                    f"ETO worker shutdown timeout after {self.shutdown_timeout}s - forcing stop"
                )
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
        elif self.worker_task:
            # Force immediate stop
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            logger.info("ETO worker stopped immediately")

        # Reset any runs stuck in processing
        await self._reset_stuck_runs()
        self.worker_task = None
        return True

    def pause_worker(self) -> bool:
        """
        Pause the worker (emergency stop without shutting down).
        Processing will halt but worker remains active.

        Returns:
            True if paused successfully
        """
        if not self.worker_running:
            logger.warning("Cannot pause - ETO worker is not running")
            return False

        self.worker_paused = True
        logger.warning("ETO background worker PAUSED - processing stopped")
        return True

    def resume_worker(self) -> bool:
        """
        Resume the worker from paused state.

        Returns:
            True if resumed successfully
        """
        if not self.worker_running:
            logger.warning("Cannot resume - ETO worker is not running")
            return False

        self.worker_paused = False
        logger.info("ETO background worker RESUMED - processing restarted")
        return True

    def get_worker_status(self) -> Dict[str, Any]:
        """
        Get current worker status and metrics.

        Returns:
            Dictionary with worker state and statistics
        """
        pending_count = 0
        try:
            pending_runs = self.list_runs(status='not_started', limit=100)
            pending_count = len(pending_runs)
        except Exception as e:
            logger.error(f"Error getting pending count: {e}")

        return {
            "worker_enabled": self.worker_enabled,
            "worker_running": self.worker_running,
            "worker_paused": self.worker_paused,
            "max_concurrent_runs": self.max_concurrent_runs,
            "polling_interval": self.polling_interval,
            "pending_runs_count": pending_count,
            "currently_processing_count": len(self.currently_processing_runs),
            "worker_task_active": self.worker_task is not None and not self.worker_task.done()
        }

    # ==================== Worker Polling Loop ====================

    async def _continuous_processing_loop(self):
        """
        Main continuous processing loop - runs until stopped.
        Polls database every polling_interval seconds for pending runs.
        """
        logger.info("ETO continuous processing loop started")

        while self.worker_running:
            try:
                if self.worker_paused:
                    # Worker is paused - don't process anything
                    await asyncio.sleep(self.polling_interval)
                    continue

                # Find and process pending runs
                await self._process_pending_runs_batch()

                # Wait before next cycle
                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                logger.info("ETO processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in ETO processing loop: {e}", exc_info=True)
                # Wait longer on error to avoid tight error loops
                await asyncio.sleep(self.polling_interval * 2)

        logger.info("ETO continuous processing loop stopped")

    async def _process_pending_runs_batch(self):
        """
        Process a batch of pending not_started runs concurrently.
        Fetches up to max_concurrent_runs and processes them in parallel.
        """
        try:
            # Get pending runs
            pending_runs = self.list_runs(
                status='not_started',
                limit=self.max_concurrent_runs
            )

            if not pending_runs:
                return  # No work to do

            logger.monitor(f"Processing batch of {len(pending_runs)} ETO runs concurrently")  # type: ignore

            # Process all runs concurrently
            tasks = [
                self._process_run_async(run.id)
                for run in pending_runs
            ]

            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log batch results
            successful = sum(1 for r in results if not isinstance(r, Exception) and r is True)
            failed = len(results) - successful

            if failed > 0:
                logger.warning(f"Batch completed: {successful} successful, {failed} failed")
                # Log specific failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Run {pending_runs[i].id} failed: {result}")
            else:
                logger.monitor(f"Batch completed successfully: {successful} runs processed")  # type: ignore

        except Exception as e:
            logger.error(f"Error processing pending runs batch: {e}", exc_info=True)

    async def _process_run_async(self, run_id: int) -> bool:
        """
        Async wrapper for processing a single run.
        Runs the synchronous process_run() in a thread pool to avoid blocking.

        Args:
            run_id: ETO run ID to process

        Returns:
            True if successful, False if failed
        """
        self.currently_processing_runs.add(run_id)
        try:
            logger.debug(f"Starting async processing for ETO run {run_id}")

            # Run synchronous processing in thread pool
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.process_run,
                run_id
            )

            logger.debug(f"Completed async processing for ETO run {run_id}: success={success}")
            return success

        except Exception as e:
            logger.error(f"Error in async processing for ETO run {run_id}: {e}", exc_info=True)
            return False
        finally:
            self.currently_processing_runs.discard(run_id)

    async def _reset_stuck_runs(self):
        """
        Reset any runs stuck in 'processing' status back to 'not_started'.
        Called during worker shutdown to clean up orphaned runs.
        """
        try:
            processing_runs = self.list_runs(status='processing')
            if processing_runs:
                logger.warning(
                    f"Resetting {len(processing_runs)} stuck processing runs to not_started"
                )

                for run in processing_runs:
                    try:
                        # Reset status to not_started
                        self.eto_run_repo.update(
                            run.id,
                            EtoRunUpdate(
                                status='not_started',
                                processing_step=None,
                                started_at=None
                            )
                        )
                        logger.debug(f"Reset run {run.id} to not_started")
                    except Exception as e:
                        logger.error(f"Failed to reset run {run.id}: {e}")

                logger.info(f"Reset {len(processing_runs)} processing runs to not_started")
        except Exception as e:
            logger.error(f"Error resetting processing runs: {e}")

    # ==================== Bulk Operations ====================

    def reprocess_runs(self, run_ids: List[int]) -> None:
        """
        Reset runs to "not_started" status for reprocessing.
        Allows worker to pick them up again.

        Args:
            run_ids: List of ETO run IDs to reprocess
        """
        # TODO: Implement bulk reprocess
        # - Reset status to "not_started"
        # - Clear error fields
        # - Clear started_at/completed_at
        logger.info(f"Reprocessing {len(run_ids)} runs")
        raise NotImplementedError("Reprocess not yet implemented")

    def skip_runs(self, run_ids: List[int]) -> None:
        """
        Mark runs as "skipped" to prevent processing.

        Args:
            run_ids: List of ETO run IDs to skip
        """
        # TODO: Implement bulk skip
        # - Update status to "skipped"
        logger.info(f"Skipping {len(run_ids)} runs")
        raise NotImplementedError("Skip not yet implemented")

    def delete_runs(self, run_ids: List[int]) -> None:
        """
        Delete runs and all related stage data.
        Use with caution - this is permanent.

        Args:
            run_ids: List of ETO run IDs to delete
        """
        # TODO: Implement bulk delete
        # - Delete stage records (cascade should handle this)
        # - Delete run records
        logger.info(f"Deleting {len(run_ids)} runs")
        raise NotImplementedError("Delete not yet implemented")
