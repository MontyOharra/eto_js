"""
ETO Processing Service
Background worker service that processes PDF files through the complete ETO pipeline:
template matching -> data extraction -> data transformation -> order creation
"""
import logging
import threading
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ...shared.database import get_connection_manager
from ...shared.database.repositories import EtoRunRepository
from ...shared.utils import get_service, ServiceNames

logger = logging.getLogger(__name__)


class EtoProcessingService:
    """Background worker service for processing ETO runs through the complete pipeline"""

    def __init__(self, poll_interval: int = 10, batch_size: int = 5):
        # Database infrastructure - get from service registry
        self.connection_manager = get_service(ServiceNames.CONNECTION_MANAGER)
        if not self.connection_manager:
            raise RuntimeError("Database connection manager is required")

        # Repository layer
        self.eto_run_repo = EtoRunRepository(self.connection_manager)

        # Worker configuration
        self.poll_interval = poll_interval  # seconds between queue checks
        self.batch_size = batch_size  # max runs to process per batch

        # Worker state
        self.running = False
        self.worker_thread = None
        self._lock = threading.Lock()

        logger.info("ETO Processing Service initialized")

    # === ETO Record Management ===

    def create_eto_run(self, pdf_id: int):
        """
        Create a new ETO record with status 'not_started' for a given PDF

        Args:
            pdf_id: PDF file ID to create ETO run for

        Returns:
            EtoRun: Created ETO run domain object
        """
        if pdf_id is None:
            raise ValueError("pdf_id is required")

        # Validate PDF exists and get its email_id using PDF processing service
        pdf_processing_service = get_service(ServiceNames.PDF_PROCESSING)
        if not pdf_processing_service:
            raise RuntimeError("PDF processing service is not available")

        pdf_file = pdf_processing_service.get_pdf_metadata(pdf_id)
        if not pdf_file:
            raise ValueError(f"PDF file {pdf_id} not found")

        # Check if ETO run already exists for this PDF
        existing_runs = self.eto_run_repo.get_by_pdf_id(pdf_id)
        if existing_runs:
            # Return existing run if it exists
            logger.info(f"ETO run already exists for PDF {pdf_id}: {existing_runs[0].id}")
            return existing_runs[0]

        # Create new ETO run record
        eto_run_data = {
            "email_id": pdf_file.email_id,
            "pdf_file_id": pdf_id,
            "status": "not_started"
        }

        eto_run = self.eto_run_repo.create(eto_run_data)
        logger.info(f"Created ETO run {eto_run.id} for PDF {pdf_id}")

        return eto_run

    # === Worker Process Management ===

    def start(self):
        """Start the background processing worker"""
        # TODO: Implement
        pass

    def stop(self):
        """Stop the background processing worker"""
        # TODO: Implement
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current processing status and statistics"""
        # TODO: Implement
        pass

    # === Core Processing Pipeline ===

    def _process_eto_run(self, eto_run):
        """
        Main orchestration method that handles the full pipeline:
        not_started -> processing (template_matching -> data_extraction -> data_transformation) -> success
        """
        # TODO: Implement
        pass

    def _process_template_matching_step(self, eto_run) -> Optional[int]:
        """
        Handle template matching step, update processing_status

        Returns:
            template_id if match found, None if no match or error
        """
        # TODO: Implement
        pass

    def _process_data_extraction_step(self, eto_run, template_id) -> Dict[str, Any]:
        """Handle data extraction step"""
        # TODO: Implement
        pass

    def _process_data_transformation_step(self, eto_run, template_id: int, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transformation step"""
        # TODO: Implement
        pass

    # === Error & Status Management ===

    def _mark_as_failed(self, run_id: int, error_message: str, error_type: str = None, error_details: dict = None):
        """Set status to 'failure' and end processing"""
        try:
            updated_run = self.eto_run_repo.mark_as_failed(
                run_id=run_id,
                error_message=error_message,
                error_type=error_type,
                error_details=error_details
            )

            if updated_run:
                logger.info(f"ETO run {run_id} marked as failed: {error_message}")
                return updated_run
            else:
                logger.error(f"Failed to mark ETO run {run_id} as failed")
                return None

        except Exception as e:
            logger.error(f"Error marking ETO run {run_id} as failed: {e}")
            raise

    def _mark_as_needs_template(self, run_id: int, suggested_new_template: bool = True):
        """Set status to 'needs_template' and end processing"""
        try:
            updated_run = self.eto_run_repo.update_status(
                run_id=run_id,
                status='needs_template',
                processing_step=None,  # Clear processing step
                suggested_new_template=suggested_new_template
            )

            if updated_run:
                logger.info(f"ETO run {run_id} marked as needs template")
                return updated_run
            else:
                logger.error(f"Failed to mark ETO run {run_id} as needs template")
                return None

        except Exception as e:
            logger.error(f"Error marking ETO run {run_id} as needs template: {e}")
            raise

    def _mark_as_success(self, run_id: int):
        """Set status to 'success', processing_step to null"""
        try:
            updated_run = self.eto_run_repo.update_status(
                run_id=run_id,
                status='success',
                processing_step=None  # Clear processing step on success
            )

            if updated_run:
                logger.info(f"ETO run {run_id} marked as successful")
                return updated_run
            else:
                logger.error(f"Failed to mark ETO run {run_id} as successful")
                return None

        except Exception as e:
            logger.error(f"Error marking ETO run {run_id} as successful: {e}")
            raise

    # === Utility Methods ===

    def process_single_run(self, run_id: int) -> bool:
        """Manual processing trigger for testing/debugging"""
        # TODO: Implement
        pass

    def get_pending_runs(self):
        """Get ETO runs with status 'not_started'"""
        # TODO: Implement
        pass

    def _get_processing_runs(self):
        """Get ETO runs currently in processing state"""
        # TODO: Implement
        pass

    def _get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics from repository"""
        # TODO: Implement
        pass

    def _worker_loop(self):
        """Background loop that polls and processes pending runs"""
        # TODO: Implement
        pass