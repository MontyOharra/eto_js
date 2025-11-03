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
from shared.database.repositories.eto_run_pipeline_execution_step import EtoRunPipelineExecutionStepRepository

from shared.events.eto_events import eto_event_manager

# Import worker
from .utils import EtoWorker

from shared.exceptions.service import ValidationError
# TODO: Import remaining repositories when implemented
# from shared.database.repositories.eto_run_pipeline_execution_step import EtoRunPipelineExecutionStepRepository

from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunListView,
    EtoRunDetailView,
)
from shared.types.eto_run_pipeline_executions import (
    EtoRunPipelineExecution,
    EtoRunPipelineExecutionCreate,
    EtoRunPipelineExecutionUpdate,
)
from shared.types.eto_run_pipeline_execution_steps import (
    EtoRunPipelineExecutionStep,
    EtoRunPipelineExecutionStepCreate,
    EtoRunPipelineExecutionStepUpdate,
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
        worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
        max_concurrent_runs = int(os.getenv('ETO_MAX_CONCURRENT_RUNS', '10'))
        polling_interval = int(os.getenv('ETO_POLLING_INTERVAL', '2'))  # seconds
        shutdown_timeout = int(os.getenv('ETO_SHUTDOWN_TIMEOUT', '30'))  # seconds

        # Initialize ETO worker
        logger.debug("Initializing ETO worker...")
        self.worker = EtoWorker(
            process_run_callback=self.process_run,
            get_pending_runs_callback=lambda limit: self.list_runs(status='not_started', limit=limit),
            reset_run_callback=self._reset_run_to_not_started,
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

            logger.monitor(f"Retrieved {len(runs)} ETO runs")  # type: ignore
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
            f"has_matching={detail.template_matching is not None}, "
            f"has_extraction={detail.extraction is not None}, "
            f"has_pipeline={detail.pipeline_execution is not None}"
        )
        return detail
    

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
        Execute ETO workflow for a run.
        Called by ETO worker for runs with status = "not_started".

        Workflow:
        1. Update status to "processing"
        2. Execute Stage 1: Template Matching
        3. Execute Stage 2: Data Extraction
        4. TODO: Execute Stage 3: Data Transformation (not yet implemented)
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
                match_result = self._process_template_matching(run_id)
                if match_result is None:
                    # No match found - run status already updated to "needs_template"
                    return False

                template_id, version_id = match_result

            except Exception as e:
                logger.error(f"Run {run_id}: Template matching stage error: {e}", exc_info=True)
                self._mark_run_failure(run_id, error=e, error_type="TemplateMatchingError")
                return False

            # Stage 2: Data Extraction
            try:
                extracted_data = self._process_data_extraction(run_id, version_id)
                logger.debug(f"Run {run_id}: Extracted data: {extracted_data}")

            except Exception as e:
                logger.error(f"Run {run_id}: Data extraction stage error: {e}", exc_info=True)
                self._mark_run_failure(run_id, error=e, error_type="DataExtractionError")
                return False

            # TODO: Stage 3: Data Transformation
            # For now, mark as success after extraction completes
            logger.info(f"Run {run_id}: Data transformation stage not yet implemented - marking as success")

            # All implemented stages completed successfully
            self._mark_run_success(run_id)
            logger.monitor(f"Run {run_id}: All stages completed successfully")  # type: ignore
            return True

        except Exception as e:
            # Catch unexpected errors not related to stage processing
            # (e.g., syntax errors, type errors, database connection issues)
            logger.error(f"Run {run_id}: Unexpected system error: {e}", exc_info=True)
            self._mark_run_failure(run_id, error=e, error_type="UnexpectedSystemError")
            return False

    # ==================== Core Processing Methods (Mirroring Simulate Logic) ====================

    def _extract_data_from_pdf(
        self,
        pdf_file_id: int,
        extraction_fields: list
    ) -> dict[str, str]:
        """
        Extract text from PDF using extraction fields.

        This is a thin wrapper around the shared extraction utility.
        The actual extraction logic is in features.eto_runs.utils.extraction

        Args:
            pdf_file_id: PDF file ID to extract from
            extraction_fields: List of ExtractionField domain objects

        Returns:
            Dict mapping field names to extracted text
        """
        from features.eto_runs.utils.extraction import extract_data_from_pdf

        return extract_data_from_pdf(
            pdf_file_service=self.pdf_files_service,
            pdf_file_id=pdf_file_id,
            extraction_fields=extraction_fields
        )

    def _process_template_matching(self, run_id: int) -> tuple[int, int] | None:
        """
        Stage 1: Template Matching

        Matches PDF to best template using signature objects.
        Creates and updates template_matching record with results.

        Args:
            run_id: ETO run ID

        Returns:
            Tuple of (template_id, version_id) if match found, None otherwise

        Raises:
            Exception: Propagated to caller for error handling
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
            return None

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
        return match_result

    def _process_data_extraction(self, run_id: int, template_version_id: int) -> dict[str, str]:
        """
        Stage 2: Data Extraction

        Extracts field values from PDF using matched template's extraction fields.
        Uses the SAME extraction logic as simulate endpoint.
        Creates and updates extraction record with results.

        Args:
            run_id: ETO run ID
            template_version_id: Matched template version ID

        Returns:
            Dict of extracted data (field name -> text value)

        Raises:
            Exception: Propagated to caller for error handling
        """
        logger.monitor(f"Run {run_id}: Executing data extraction stage")  # type: ignore

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
        started_at = datetime.now(timezone.utc)
        extraction = self.extraction_repo.create(
            EtoRunExtractionCreate(eto_run_id=run_id)
        )
        logger.debug(f"Run {run_id}: Created extraction record {extraction.id}")

        # Step 3: Get extraction fields from matched template version
        template_version = self.pdf_template_service.get_version_by_id(template_version_id)
        logger.debug(f"Run {run_id}: Retrieved template version {template_version_id} with {len(template_version.extraction_fields)} fields")

        # Step 4: Get PDF file ID from run
        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            raise ServiceError(f"Run {run_id} not found")

        # Step 5: CORE LOGIC - Extract data using same logic as simulate endpoint
        extracted_data = self._extract_data_from_pdf(
            pdf_file_id=run.pdf_file_id,
            extraction_fields=template_version.extraction_fields
        )

        logger.debug(f"Run {run_id}: Extracted {len(extracted_data)} fields from PDF")

        # Step 6: Update extraction record with results
        self.extraction_repo.update(
            extraction.id,
            EtoRunExtractionUpdate(
                status="success",
                extracted_data=json.dumps(extracted_data),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.monitor(f"Run {run_id}: Data extraction completed successfully")  # type: ignore
        return extracted_data

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

    def _reset_run_to_not_started(self, run_id: int) -> None:
        """
        Reset a run back to not_started status.
        Used by worker for cleaning up stuck runs.

        Args:
            run_id: ETO run ID to reset
        """
        try:
            self.eto_run_repo.update(
                run_id,
                EtoRunUpdate(
                    status='not_started',
                    processing_step=None,
                    started_at=None
                )
            )
            logger.debug(f"Reset run {run_id} to not_started")
        except Exception as e:
            logger.error(f"Failed to reset run {run_id}: {e}")

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