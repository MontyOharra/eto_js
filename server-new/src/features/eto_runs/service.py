"""
ETO Processing Service
Orchestrates the 3-stage ETO (Email-to-Order) workflow
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from shared.database import DatabaseConnectionManager
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_run_pipeline_execution import EtoRunPipelineExecutionRepository
# TODO: Import remaining repositories when implemented
# from shared.database.repositories.eto_run_template_matching import EtoRunTemplateMatchingRepository
# from shared.database.repositories.eto_run_extraction import EtoRunExtractionRepository
# from shared.database.repositories.eto_run_pipeline_execution_step import EtoRunPipelineExecutionStepRepository

from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunStatus,
    EtoProcessingStep,
)
from shared.types.eto_run_pipeline_executions import (
    EtoRunPipelineExecution,
    EtoRunPipelineExecutionCreate,
    EtoRunPipelineExecutionUpdate,
    EtoStepStatus,
)
# TODO: Import remaining domain types when implemented
# from shared.types.eto_run_template_matchings import ...
# from shared.types.eto_run_extractions import ...

from shared.exceptions.service import ObjectNotFoundError, ServiceError

# TYPE_CHECKING imports to avoid circular dependencies
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from features.pdf_templates.service import PdfTemplateService
    from features.pdf_files.service import PdfFilesService
    from features.pipeline_execution.service import PipelineExecutionService

logger = logging.getLogger(__name__)


class EtoProcessingService:
    """
    ETO Processing Service - Main orchestrator for Email-to-Order workflow.

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
    # TODO: Add remaining repositories when implemented
    # template_matching_repo: EtoRunTemplateMatchingRepository
    # extraction_repo: EtoRunExtractionRepository
    # pipeline_execution_step_repo: EtoRunPipelineExecutionStepRepository

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        pdf_template_service: 'PdfTemplateService',
        pdf_files_service: 'PdfFilesService',
        pipeline_execution_service: 'PipelineExecutionService'
    ) -> None:
        """
        Initialize ETO Processing Service.

        Args:
            connection_manager: Database connection manager
            pdf_template_service: Service for template matching
            pdf_files_service: Service for PDF file access
            pipeline_execution_service: Service for pipeline execution
        """
        logger.debug("Initializing EtoProcessingService...")

        # Store service dependencies
        self.connection_manager = connection_manager
        self.pdf_template_service = pdf_template_service
        self.pdf_files_service = pdf_files_service
        self.pipeline_execution_service = pipeline_execution_service

        # Initialize repositories
        self.eto_run_repo = EtoRunRepository(connection_manager=connection_manager)
        self.pipeline_execution_repo = EtoRunPipelineExecutionRepository(connection_manager=connection_manager)

        # TODO: Initialize remaining repositories when implemented
        # self.template_matching_repo = EtoRunTemplateMatchingRepository(connection_manager=connection_manager)
        # self.extraction_repo = EtoRunExtractionRepository(connection_manager=connection_manager)
        # self.pipeline_execution_step_repo = EtoRunPipelineExecutionStepRepository(connection_manager=connection_manager)

        logger.info("EtoProcessingService initialized successfully")

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
            ServiceError: If PDF file doesn't exist or creation fails
        """
        logger.info(f"Creating ETO run for PDF file {pdf_file_id}")

        try:
            # TODO: Validate PDF file exists
            # pdf_file = self.pdf_files_service.get_file(pdf_file_id)
            # if not pdf_file:
            #     raise ObjectNotFoundError(f"PDF file {pdf_file_id} not found")

            # Create run with status = "not_started"
            run = self.eto_run_repo.create(EtoRunCreate(pdf_file_id=pdf_file_id))

            logger.info(f"Created ETO run {run.id} for PDF {pdf_file_id}")
            return run

        except Exception as e:
            logger.error(f"Failed to create ETO run for PDF {pdf_file_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to create ETO run: {str(e)}") from e

    def list_runs(
        self,
        status: Optional[EtoRunStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[EtoRun]:
        """
        List ETO runs with optional filtering.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)

        Returns:
            List of EtoRun dataclasses
        """
        # TODO: Implement list functionality
        # This will be called by API endpoints for dashboard views
        logger.debug(f"Listing ETO runs: status={status}, limit={limit}, offset={offset}")
        raise NotImplementedError("List runs not yet implemented")

    def get_run_detail(self, run_id: int) -> EtoRun:
        """
        Get detailed ETO run information including all stage data.

        Args:
            run_id: ETO run ID

        Returns:
            EtoRun dataclass with related stage data

        Raises:
            ObjectNotFoundError: If run not found
        """
        logger.debug(f"Getting ETO run detail for run {run_id}")

        run = self.eto_run_repo.get_by_id(run_id)
        if not run:
            raise ObjectNotFoundError(f"ETO run {run_id} not found")

        # TODO: Load related stage data
        # - template_matching record
        # - extraction record
        # - pipeline_execution record + steps

        return run

    # ==================== Processing Methods (Worker) ====================

    def process_run(self, run_id: int) -> bool:
        """
        Execute full 3-stage ETO workflow for a run.
        Called by ETO worker for runs with status = "not_started".

        Workflow:
        1. Update status to "processing"
        2. Execute Stage 1: Template Matching
        3. Execute Stage 2: Data Extraction
        4. Execute Stage 3: Data Transformation
        5. Update status to "success" or "failure"

        Args:
            run_id: ETO run ID to process

        Returns:
            True if successful, False if failed
        """
        logger.info(f"Starting ETO processing for run {run_id}")

        try:
            # Get run and validate
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                logger.error(f"ETO run {run_id} not found")
                return False

            # Update to processing status
            self.eto_run_repo.update(
                run_id,
                EtoRunUpdate(
                    status="processing",
                    started_at=datetime.now(timezone.utc)
                )
            )

            # Stage 1: Template Matching
            logger.info(f"Run {run_id}: Starting template matching")
            if not self._execute_template_matching(run_id):
                logger.error(f"Run {run_id}: Template matching failed")
                return False

            # Stage 2: Data Extraction
            logger.info(f"Run {run_id}: Starting data extraction")
            if not self._execute_data_extraction(run_id):
                logger.error(f"Run {run_id}: Data extraction failed")
                return False

            # Stage 3: Data Transformation
            logger.info(f"Run {run_id}: Starting data transformation")
            if not self._execute_data_transformation(run_id):
                logger.error(f"Run {run_id}: Data transformation failed")
                return False

            # Mark run as success
            self._mark_run_success(run_id)
            logger.info(f"Run {run_id}: Completed successfully")
            return True

        except Exception as e:
            logger.error(f"Run {run_id}: Unexpected error: {e}", exc_info=True)
            self._mark_run_failure(run_id, error=e)
            return False

    def _execute_template_matching(self, run_id: int) -> bool:
        """
        Execute Stage 1: Template Matching.

        Process:
        1. Update run processing_step to "template_matching"
        2. Create template_matching record with status="processing"
        3. Call PDF template service to match PDF
        4. Update template_matching record with result
        5. If no match: update run status to "needs_template"

        Args:
            run_id: ETO run ID

        Returns:
            True if successful, False if failed
        """
        logger.info(f"Run {run_id}: Executing template matching stage")

        # TODO: Implement template matching stage
        # 1. Update run processing_step
        # 2. Create template_matching record
        # 3. Get PDF data
        # 4. Call pdf_template_service.match_template()
        # 5. Update records based on result

        raise NotImplementedError("Template matching not yet implemented")

    def _execute_data_extraction(self, run_id: int) -> bool:
        """
        Execute Stage 2: Data Extraction.

        Process:
        1. Update run processing_step to "data_extraction"
        2. Create extraction record with status="processing"
        3. Get matched template's extraction fields
        4. Extract text from PDF using bounding boxes
        5. Update extraction record with extracted data

        Args:
            run_id: ETO run ID

        Returns:
            True if successful, False if failed
        """
        logger.info(f"Run {run_id}: Executing data extraction stage")

        # TODO: Implement data extraction stage
        # 1. Update run processing_step
        # 2. Create extraction record
        # 3. Get template version and extraction_fields
        # 4. Extract data from PDF
        # 5. Update extraction record with results

        raise NotImplementedError("Data extraction not yet implemented")

    def _execute_data_transformation(self, run_id: int) -> bool:
        """
        Execute Stage 3: Data Transformation (Pipeline Execution).

        Process:
        1. Update run processing_step to "data_transformation"
        2. Create pipeline_execution record with status="processing"
        3. Get extracted data and pipeline definition
        4. Execute pipeline with entry point values
        5. Update pipeline_execution record with results
        6. Create execution step records for audit trail

        Args:
            run_id: ETO run ID

        Returns:
            True if successful, False if failed
        """
        logger.info(f"Run {run_id}: Executing data transformation stage")

        # TODO: Implement data transformation stage
        # 1. Update run processing_step
        # 2. Create pipeline_execution record
        # 3. Get extraction data and pipeline definition
        # 4. Call pipeline_execution_service.execute_pipeline()
        # 5. Update pipeline_execution record
        # 6. Create step records

        raise NotImplementedError("Data transformation not yet implemented")

    # ==================== Helper Methods ====================

    def _mark_run_success(self, run_id: int) -> None:
        """
        Mark ETO run as successfully completed.

        Args:
            run_id: ETO run ID
        """
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(
                status="success",
                completed_at=datetime.now(timezone.utc)
            )
        )
        logger.info(f"Run {run_id}: Marked as success")

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

        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(
                status="failure",
                completed_at=datetime.now(timezone.utc),
                error_type=error_type,
                error_message=str(error),
                error_details=None  # TODO: Add stack trace or additional context if needed
            )
        )
        logger.error(f"Run {run_id}: Marked as failure - {error_type}: {error}")

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
