"""
ETO Processing Service with Integrated Background Worker
Main orchestration service for the complete ETO (Extract, Transform, Order) pipeline.
Coordinates template matching, data extraction, transformation, and order creation.
Includes continuous background worker for automatic processing.
"""
import asyncio
import json
import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from shared.database.connection import DatabaseConnectionManager
from shared.database.repositories.eto_run import EtoRunRepository
from shared.exceptions import ServiceError, ObjectNotFoundError, EtoProcessingError, EtoStatusValidationError, EtoTemplateMatchingError, EtoDataExtractionError, EtoTransformationError
from shared.services import get_pdf_processing_service, get_pdf_template_service
from shared.models import (
    EtoRun, EtoRunCreate, EtoRunStatus, EtoProcessingStep, EtoErrorType,
    EtoRunStatusUpdate, EtoRunTemplateMatchUpdate, EtoRunDataExtractionUpdate,
    EtoRunTransformationUpdate, EtoRunOrderUpdate, PdfObjects, EtoRunWithPdfData,
)
from shared.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class EtoProcessingService:
    """
    ETO Processing Service with integrated background worker

    Responsibilities:
    - Orchestrate the complete ETO pipeline
    - Run continuous background processing worker
    - Coordinate between PDF processing, template matching, and data extraction
    - Handle processing state management and error tracking
    - Provide user-facing operations (reprocessing, skipping, etc.)
    """

    def __init__(self, connection_manager: DatabaseConnectionManager):
        """
        Initialize ETO processing service with integrated worker

        Args:
            connection_manager: Database connection manager
            pdf_service: PDF processing service instance
            template_service: PDF template service instance
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.pdf_service = get_pdf_processing_service()
        self.template_service = get_pdf_template_service()
        self.eto_run_repository = EtoRunRepository(connection_manager)

        # Worker configuration and state
        self.worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
        self.worker_running = False
        self.worker_paused = False
        self.max_concurrent_runs = int(os.getenv('ETO_MAX_CONCURRENT_RUNS', '10'))
        self.polling_interval = int(os.getenv('ETO_POLLING_INTERVAL', '2'))
        self.shutdown_timeout = int(os.getenv('ETO_SHUTDOWN_TIMEOUT', '30'))
        self.worker_task = None
        self.currently_processing_runs = set()

        logger.info(f"ETO Processing Service initialized - worker_enabled: {self.worker_enabled}")

    # ========== Worker Management ==========

    async def start_worker(self):
        """Start the background processing worker"""
        if not self.worker_enabled:
            logger.info("ETO worker is disabled by configuration")
            return False

        if self.worker_running:
            logger.warning("ETO worker is already running")
            return False

        self.worker_running = True
        self.worker_paused = False
        self.worker_task = asyncio.create_task(self._continuous_processing_loop())
        logger.info("ETO background worker started")
        return True

    async def stop_worker(self, graceful: bool = True):
        """Stop the background processing worker with graceful shutdown"""
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
                logger.warning(f"ETO worker shutdown timeout after {self.shutdown_timeout}s - forcing stop")
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

        # Reset any runs that were being processed
        await self._reset_processing_runs()
        self.worker_task = None
        return True

    def pause_worker(self):
        """Pause the background worker (emergency stop)"""
        if not self.worker_running:
            logger.warning("Cannot pause - ETO worker is not running")
            return False

        self.worker_paused = True
        logger.warning("ETO background worker PAUSED - processing stopped")
        return True

    def resume_worker(self):
        """Resume the background worker from pause"""
        if not self.worker_running:
            logger.warning("Cannot resume - ETO worker is not running")
            return False

        self.worker_paused = False
        logger.info("ETO background worker RESUMED - processing restarted")
        return True

    def get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status"""
        pending_count = 0
        processing_count = len(self.currently_processing_runs)

        try:
            pending_runs = self.get_runs_by_status(EtoRunStatus.NOT_STARTED, limit=100)
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
            "currently_processing_count": processing_count,
            "worker_task_active": self.worker_task is not None and not self.worker_task.done()
        }

    async def _reset_processing_runs(self):
        """Reset any runs stuck in 'processing' status back to 'not_started'"""
        try:
            processing_runs = self.get_runs_by_status(EtoRunStatus.PROCESSING)
            if processing_runs:
                logger.warning(f"Resetting {len(processing_runs)} stuck processing runs to not_started")

                for run_summary in processing_runs:
                    try:
                        # Get full run object and reset
                        full_run = self.eto_run_repository.get_by_id(run_summary.id)
                        if full_run:
                            self.eto_run_repository.reset_single_run_for_reprocessing(run_summary.id)
                            logger.debug(f"Reset run {run_summary.id} to not_started")
                    except Exception as e:
                        logger.error(f"Failed to reset run {run_summary.id}: {e}")

                logger.info(f"Reset {len(processing_runs)} processing runs to not_started")
        except Exception as e:
            logger.error(f"Error resetting processing runs: {e}")

    # ========== Background Worker Loop ==========

    async def _continuous_processing_loop(self):
        """Main continuous processing loop - runs until stopped"""
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
                logger.error(f"Error in ETO processing loop: {e}")
                # Wait longer on error to avoid tight error loops
                await asyncio.sleep(self.polling_interval * 2)

        logger.info("ETO continuous processing loop stopped")

    async def _process_pending_runs_batch(self):
        """Process a batch of pending not_started runs concurrently"""
        try:
            # Get pending runs
            pending_runs = self.get_runs_by_status(
                EtoRunStatus.NOT_STARTED,
                self.max_concurrent_runs
            )

            if not pending_runs:
                return  # No work to do

            logger.info(f"Processing batch of {len(pending_runs)} ETO runs concurrently")

            # Convert summaries to full EtoRun objects
            full_runs = []
            for summary in pending_runs:
                full_run = self.eto_run_repository.get_by_id(summary.id)
                if full_run:
                    full_runs.append(full_run)

            # Process all runs concurrently (each maintains sequential steps internally)
            tasks = [
                self._process_single_run_async(run)
                for run in full_runs
            ]

            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log batch results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            if failed > 0:
                logger.warning(f"Batch completed: {successful} successful, {failed} failed")
                # Log specific failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Run {full_runs[i].id} failed: {result}")
            else:
                logger.info(f"Batch completed successfully: {successful} runs processed")

        except Exception as e:
            logger.error(f"Error processing pending runs batch: {e}")

    # ========== Core Async Processing Pipeline ==========

    async def _process_single_run_async(self, eto_run: EtoRun) -> EtoRun:
        """
        Process a single ETO run with strict sequential steps.
        Each step MUST complete before the next begins.
        """
        self.currently_processing_runs.add(eto_run.id)
        try:
            logger.debug(f"Starting async processing for ETO run {eto_run.id}")

            # Step 1: Start processing (mark as processing)
            eto_run = await self._start_processing_async(eto_run)

            # Step 2: Template matching - MUST complete first
            eto_run = await self._perform_template_matching_async(eto_run)

            if eto_run.status == EtoRunStatus.NEEDS_TEMPLATE:
                logger.info(f"ETO run {eto_run.id} needs template - stopping pipeline")
                return eto_run

            # Step 3: Data extraction - CANNOT start until matching is done
            eto_run = await self._perform_data_extraction_async(eto_run)

            # Step 4: Data transformation - CANNOT start until extraction is done
            eto_run = await self._perform_data_transformation_async(eto_run)

            # Step 5: Order creation - CANNOT start until transformation is done
            eto_run = await self._perform_order_creation_async(eto_run)

            logger.info(f"Successfully completed async processing for ETO run {eto_run.id}")
            return eto_run

        except Exception as e:
            logger.error(f"Error in async processing for ETO run {eto_run.id}: {e}")
            # Handle error and mark run as failed
            return await self._handle_processing_error_async(eto_run, e)
        finally:
            self.currently_processing_runs.discard(eto_run.id)

    async def _start_processing_async(self, eto_run: EtoRun) -> EtoRun:
        """Async version of start processing"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.eto_run_repository.start_processing, eto_run.id)

    async def _perform_template_matching_async(self, eto_run: EtoRun) -> EtoRun:
        """Async version of template matching"""
        def sync_template_matching():
            # Validate status and prerequisites
            self._validate_status_for_step(eto_run, EtoProcessingStep.TEMPLATE_MATCHING)

            # Get PDF objects
            pdf_objects = self._get_pdf_objects(eto_run.pdf_file_id)
            if not pdf_objects:
                raise EtoTemplateMatchingError(
                    eto_run.id, "No PDF objects found for template matching"
                )

            # Find best template match using nested structure
            match_result = self.template_service.find_best_template_match(pdf_objects)

            if not match_result.template_found:
                # No template found - mark as needs template
                return self.eto_run_repository.set_needs_template(
                    eto_run.id, "No matching template found for this PDF"
                )

            # Template found - get match data with type safety
            template_id, template_version = match_result.get_match_data()
            template_update = EtoRunTemplateMatchUpdate(
                matched_template_id=template_id,
                matched_template_version=template_version
            )

            logger.info(f"Template match found for ETO run {eto_run.id}: template {template_id}")
            return self.eto_run_repository.set_template_match_and_advance(eto_run.id, template_update)

        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_template_matching)

    async def _perform_data_extraction_async(self, eto_run: EtoRun) -> EtoRun:
        """Async version of data extraction"""
        def sync_data_extraction():
            # Validate status and prerequisites
            self._validate_status_for_step(eto_run, EtoProcessingStep.EXTRACTING_DATA)
            self._validate_prerequisites_for_extraction(eto_run)

            # Get PDF objects (already in nested PdfObjects format)
            pdf_objects = self._get_pdf_objects(eto_run.pdf_file_id)
            if not pdf_objects:
                raise EtoDataExtractionError(
                    eto_run.id, "No PDF objects found for data extraction"
                )

            # Extract data using template with nested PdfObjects structure
            if eto_run.matched_template_id is None:
                raise EtoDataExtractionError(eto_run.id, "No matched template ID available for data extraction")

            extracted_data = self.template_service.extract_data_using_template(
                eto_run.matched_template_id, pdf_objects
            )

            # Store extracted data
            extraction_update = EtoRunDataExtractionUpdate(extracted_data=extracted_data)
            logger.info(f"Data extraction completed for ETO run {eto_run.id}")
            return self.eto_run_repository.set_extracted_data_and_advance(eto_run.id, extraction_update)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_data_extraction)

    async def _perform_data_transformation_async(self, eto_run: EtoRun) -> EtoRun:
        """Async version of data transformation"""
        def sync_data_transformation():
            # Validate status and prerequisites
            self._validate_status_for_step(eto_run, EtoProcessingStep.TRANSFORMING_DATA)
            self._validate_prerequisites_for_transformation(eto_run)

            # Get extracted data
            extraction_result = eto_run.get_data_extraction_result()
            raw_data = extraction_result.extracted_data

            # Perform transformation (placeholder implementation)
            transformed_data = {
                "order_data": raw_data,
                "processed_at": DateTimeUtils.utc_now().isoformat(),
                "transformation_version": "1.0"
            }

            audit_data = {
                "steps": ["data_validation", "field_mapping", "business_rules"],
                "validation_results": {"valid": True, "warnings": []},
                "processing_time_ms": 50  # placeholder
            }

            # Store transformation results
            transformation_update = EtoRunTransformationUpdate(
                target_data=transformed_data,
                transformation_audit=audit_data,
                step_execution_log=None
            )

            logger.info(f"Data transformation completed for ETO run {eto_run.id}")
            return self.eto_run_repository.set_transformed_data_and_complete(eto_run.id, transformation_update)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_data_transformation)

    async def _perform_order_creation_async(self, eto_run: EtoRun) -> EtoRun:
        """Async version of order creation"""
        def sync_order_creation():
            # Validate prerequisites for order creation
            self._validate_prerequisites_for_order_creation(eto_run)

            # Create order (placeholder implementation)
            logger.info(f"Order creation step for ETO run {eto_run.id} (placeholder implementation)")

            # Simulate order creation
            order_id = 12345  # placeholder order ID

            # Store order reference
            order_update = EtoRunOrderUpdate(order_id=order_id)
            logger.info(f"Order creation completed for ETO run {eto_run.id}, order ID: {order_id}")
            return self.eto_run_repository.set_order_integration(eto_run.id, order_update)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_order_creation)

    async def _handle_processing_error_async(self, eto_run: EtoRun, error: Exception) -> EtoRun:
        """Handle processing errors in async context"""
        def sync_error_handling():
            # Convert to appropriate ETO error type and handle
            if isinstance(error, EtoProcessingError):
                return self._handle_centralized_processing_error(eto_run, error, "async_processing")
            else:
                # Create system error for unexpected exceptions
                system_error = EtoProcessingError(
                    message=f"Async processing error: {str(error)}",
                    eto_run_id=eto_run.id,
                    error_type=EtoErrorType.SYSTEM_ERROR,
                    processing_step=EtoProcessingStep.TEMPLATE_MATCHING,
                    original_exception=error
                )
                return self._handle_centralized_processing_error(eto_run, system_error, "async_processing")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_error_handling)

    # ========== API Entry Points (Create Runs and Set to not_started) ==========

    def process_pdf(self, pdf_file_id: int) -> EtoRun:
        """
        Create ETO run for a PDF and queue it for background processing

        Args:
            pdf_file_id: PDF file ID to process

        Returns:
            EtoRun with not_started status (will be processed by background worker)

        Raises:
            ServiceError: If run creation fails
        """
        try:
            # Create ETO run record with not_started status
            eto_run = self._create_eto_run(pdf_file_id)
            logger.info(f"Created ETO run {eto_run.id} for PDF {pdf_file_id} - queued for background processing")
            return eto_run

        except Exception as e:
            logger.error(f"Failed to create ETO run for PDF {pdf_file_id}: {e}")
            raise ServiceError(f"Failed to create ETO run: {str(e)}")

    def reprocess_run(self, eto_run_id: int, force: bool = False) -> EtoRun:
        """
        Reset an existing ETO run for reprocessing by background worker

        Args:
            eto_run_id: ETO run ID to reprocess
            force: Force reprocessing even if already successful

        Returns:
            EtoRun with not_started status (will be processed by background worker)

        Raises:
            ObjectNotFoundError: If ETO run doesn't exist
            ServiceError: If reset fails
        """
        try:
            # Get existing run
            eto_run = self.eto_run_repository.get_by_id(eto_run_id)
            if not eto_run:
                raise ObjectNotFoundError("EtoRun", eto_run_id)

            # Check if reprocessing is allowed
            if not force and eto_run.status == EtoRunStatus.SUCCESS:
                logger.warning(f"ETO run {eto_run_id} already successful, use force=True to reprocess")
                return eto_run

            if not eto_run.can_be_reprocessed() and not force:
                logger.warning(f"ETO run {eto_run_id} cannot be reprocessed (status: {eto_run.status})")
                return eto_run

            # Reset for reprocessing (sets status to not_started)
            eto_run = self.eto_run_repository.reset_single_run_for_reprocessing(eto_run_id)

            logger.info(f"Reset ETO run {eto_run_id} for reprocessing - queued for background processing")
            return eto_run

        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error reprocessing ETO run {eto_run_id}: {e}")
            raise ServiceError(f"Failed to reprocess ETO run: {str(e)}")

    # ========== Status Validation Framework ==========

    def _validate_status_for_step(self, eto_run: EtoRun, expected_step: EtoProcessingStep) -> None:
        """
        Validate that EtoRun is in correct status for the given processing step

        Args:
            eto_run: ETO run to validate
            expected_step: Expected processing step

        Raises:
            EtoStatusValidationError: If status validation fails
        """
        # Check overall status
        if eto_run.status != EtoRunStatus.PROCESSING:
            raise EtoStatusValidationError(
                eto_run_id=eto_run.id,
                processing_step=expected_step,
                current_status=eto_run.status.value,
                expected_status=EtoRunStatus.PROCESSING.value
            )

        # Check processing step matches
        if eto_run.processing_step != expected_step.value:
            raise EtoStatusValidationError(
                eto_run_id=eto_run.id,
                processing_step=expected_step,
                current_status=f"processing/{eto_run.processing_step or 'unknown'}",
                expected_status=f"processing/{expected_step.value}"
            )

    def _validate_prerequisites_for_extraction(self, eto_run: EtoRun) -> None:
        """
        Validate prerequisites for data extraction step

        Args:
            eto_run: ETO run to validate

        Raises:
            EtoStatusValidationError: If prerequisites not met
        """
        if not eto_run.matched_template_id:
            raise EtoStatusValidationError(
                eto_run_id=eto_run.id,
                processing_step=EtoProcessingStep.EXTRACTING_DATA,
                current_status=eto_run.status.value,
                expected_status=EtoRunStatus.PROCESSING.value,
                additional_requirements="matched_template_id must be set"
            )

    def _validate_prerequisites_for_transformation(self, eto_run: EtoRun) -> None:
        """
        Validate prerequisites for data transformation step

        Args:
            eto_run: ETO run to validate

        Raises:
            EtoStatusValidationError: If prerequisites not met
        """
        extraction_result = eto_run.get_data_extraction_result()
        if not extraction_result.has_extracted_data():
            raise EtoStatusValidationError(
                eto_run_id=eto_run.id,
                processing_step=EtoProcessingStep.TRANSFORMING_DATA,
                current_status=eto_run.status.value,
                expected_status=EtoRunStatus.PROCESSING.value,
                additional_requirements="extracted_data must be present"
            )

    def _validate_prerequisites_for_order_creation(self, eto_run: EtoRun) -> None:
        """
        Validate prerequisites for order creation step

        Args:
            eto_run: ETO run to validate

        Raises:
            EtoStatusValidationError: If prerequisites not met
        """
        transformation_result = eto_run.get_transformation_result()
        if not transformation_result.has_transformed_data():
            raise EtoStatusValidationError(
                eto_run_id=eto_run.id,
                processing_step=EtoProcessingStep.TRANSFORMING_DATA,  # Still in transformation conceptually
                current_status=eto_run.status.value,
                expected_status=EtoRunStatus.PROCESSING.value,
                additional_requirements="target_data must be present from transformation"
            )

    # ========== Individual Pipeline Steps ==========

    def _create_eto_run(self, pdf_file_id: int) -> EtoRun:
        """Create new ETO run record"""
        eto_run_create = EtoRunCreate(pdf_file_id=pdf_file_id)
        return self.eto_run_repository.create(eto_run_create)

    def _start_processing(self, eto_run: EtoRun) -> EtoRun:
        """Start processing and update status"""
        return self.eto_run_repository.start_processing(eto_run.id)

    def _perform_template_matching(self, eto_run: EtoRun) -> EtoRun:
        """Perform template matching step"""
        # Validate status and prerequisites
        self._validate_status_for_step(eto_run, EtoProcessingStep.TEMPLATE_MATCHING)

        # Get PDF objects
        pdf_objects = self._get_pdf_objects(eto_run.pdf_file_id)
        if not pdf_objects:
            raise EtoTemplateMatchingError(
                eto_run.id, "No PDF objects found for template matching"
            )

        # Find best template match using nested structure
        pdf_template_service = self.template_service
        match_result = pdf_template_service.find_best_template_match(pdf_objects)

        if not match_result.template_found:
            # No template found - mark as needs template
            return self.eto_run_repository.set_needs_template(
                eto_run.id, "No matching template found for this PDF"
            )

        # Template found - get match data with type safety
        template_id, template_version = match_result.get_match_data()
        template_update = EtoRunTemplateMatchUpdate(
            matched_template_id=template_id,
            matched_template_version=template_version
        )

        logger.info(f"Template match found for ETO run {eto_run.id}: template {template_id}")
        return self.eto_run_repository.set_template_match_and_advance(eto_run.id, template_update)

    def _perform_data_extraction(self, eto_run: EtoRun) -> EtoRun:
        """Perform data extraction step"""
        # Validate status and prerequisites
        self._validate_status_for_step(eto_run, EtoProcessingStep.EXTRACTING_DATA)
        self._validate_prerequisites_for_extraction(eto_run)

        # Get PDF objects (already in nested PdfObjects format)
        pdf_objects = self._get_pdf_objects(eto_run.pdf_file_id)
        if not pdf_objects:
            raise EtoDataExtractionError(
                eto_run.id, "No PDF objects found for data extraction"
            )

        # Extract data using template with nested PdfObjects structure
        pdf_template_service = self.template_service

        # Ensure we have a matched template ID (validated in prerequisites, but type safety)
        if eto_run.matched_template_id is None:
            raise EtoDataExtractionError(eto_run.id, "No matched template ID available for data extraction")

        extracted_data = pdf_template_service.extract_data_using_template(
            eto_run.matched_template_id, pdf_objects
        )

        # Store extracted data
        extraction_update = EtoRunDataExtractionUpdate(extracted_data=extracted_data)
        logger.info(f"Data extraction completed for ETO run {eto_run.id}")
        return self.eto_run_repository.set_extracted_data_and_advance(eto_run.id, extraction_update)

    def _perform_data_transformation(self, eto_run: EtoRun) -> EtoRun:
        """Perform data transformation step"""
        # Validate status and prerequisites
        self._validate_status_for_step(eto_run, EtoProcessingStep.TRANSFORMING_DATA)
        self._validate_prerequisites_for_transformation(eto_run)

        # Get extracted data
        extraction_result = eto_run.get_data_extraction_result()
        raw_data = extraction_result.extracted_data

        # Perform transformation (placeholder implementation)
        # This would typically involve applying business rules, validations, and data mapping
        transformed_data = {
            "order_data": raw_data,
            "processed_at": DateTimeUtils.utc_now().isoformat(),
            "transformation_version": "1.0"
        }

        audit_data = {
            "steps": ["data_validation", "field_mapping", "business_rules"],
            "validation_results": {"valid": True, "warnings": []},
            "processing_time_ms": 50  # placeholder
        }

        # Store transformation results
        transformation_update = EtoRunTransformationUpdate(
            target_data=transformed_data,
            transformation_audit=audit_data,
            step_execution_log=None  # No pipeline execution log for simple transformation
        )

        logger.info(f"Data transformation completed for ETO run {eto_run.id}")
        return self.eto_run_repository.set_transformed_data_and_complete(eto_run.id, transformation_update)

    def _perform_order_creation(self, eto_run: EtoRun) -> EtoRun:
        """Perform order creation step (placeholder)"""
        # Validate prerequisites for order creation
        self._validate_prerequisites_for_order_creation(eto_run)

        # Create order (placeholder implementation)
        # This would typically integrate with an order management system
        logger.info(f"Order creation step for ETO run {eto_run.id} (placeholder implementation)")

        # Simulate order creation
        order_id = 12345  # placeholder order ID

        # Store order reference
        order_update = EtoRunOrderUpdate(order_id=order_id)
        logger.info(f"Order creation completed for ETO run {eto_run.id}, order ID: {order_id}")
        return self.eto_run_repository.set_order_integration(eto_run.id, order_update)

    def _complete_processing(self, eto_run: EtoRun) -> EtoRun:
        """Complete processing and mark as successful"""
        # The set_transformed_data_and_complete method should already mark as success
        # If not, we can add a separate completion method to the repository
        logger.info(f"Processing completed for ETO run {eto_run.id}")
        return eto_run

    def _continue_processing(self, eto_run: EtoRun) -> EtoRun:
        """Continue processing from current state (for reprocessing)"""
        current_step = "reprocessing_initialization"

        try:
            # Start processing from template matching
            current_step = "restart_processing"
            eto_run = self._start_processing(eto_run)

            # Continue with template matching
            current_step = "template_matching"
            eto_run = self._perform_template_matching(eto_run)

            if eto_run.status == EtoRunStatus.NEEDS_TEMPLATE:
                logger.info(f"ETO run {eto_run.id} needs template during reprocessing - stopping pipeline")
                return eto_run

            # Continue with rest of pipeline
            current_step = "data_extraction"
            eto_run = self._perform_data_extraction(eto_run)

            current_step = "data_transformation"
            eto_run = self._perform_data_transformation(eto_run)

            current_step = "order_creation"
            eto_run = self._perform_order_creation(eto_run)

            current_step = "complete_processing"
            eto_run = self._complete_processing(eto_run)

            logger.info(f"Successfully completed ETO run reprocessing {eto_run.id}")
            return eto_run

        except EtoProcessingError as e:
            # Handle ETO-specific processing errors during reprocessing
            logger.error(f"ETO reprocessing failed at step '{current_step}' for run {eto_run.id}: {e}")
            return self._handle_centralized_processing_error(eto_run, e, current_step)

        except Exception as e:
            # Handle unexpected system errors during reprocessing
            logger.error(f"Unexpected error during reprocessing at step '{current_step}' for run {eto_run.id}: {e}")
            system_error = EtoProcessingError(
                message=f"Unexpected system error during reprocessing at {current_step}: {str(e)}",
                eto_run_id=eto_run.id,
                error_type=EtoErrorType.SYSTEM_ERROR,
                processing_step=EtoProcessingStep.TEMPLATE_MATCHING,  # Default step
                original_exception=e
            )
            return self._handle_centralized_processing_error(eto_run, system_error, current_step)

    # ========== User-Facing Operations ==========

    def skip_run(self, eto_run_id: int) -> EtoRun:
        """
        Skip an ETO run with reason

        Args:
            eto_run_id: ETO run ID to skip
            reason: Reason for skipping

        Returns:
            Updated ETO run

        Raises:
            ObjectNotFoundError: If ETO run doesn't exist
        """
        logger.info(f"Skipped ETO run {eto_run_id}")
        return self.eto_run_repository.mark_as_skipped(eto_run_id)

    def delete_run(self, eto_run_id: int) -> EtoRun:
        """
        Delete an ETO run

        Args:
            eto_run_id: ETO run ID to delete

        Returns:
            The deleted ETO run object

        Raises:
            ObjectNotFoundError: If ETO run doesn't exist
        """
        deleted_run = self.eto_run_repository.delete_skipped_run(eto_run_id)
        logger.info(f"Deleted ETO run {eto_run_id}")
        return deleted_run

    def get_runs_by_status(self, status: EtoRunStatus, limit: Optional[int] = None):
        """Get ETO runs by status"""
        return self.eto_run_repository.get_runs_with_filters(status=status, limit=limit)

    def get_run_by_id(self, eto_run_id: int) -> Optional[EtoRun]:
        """Get ETO run by ID"""
        return self.eto_run_repository.get_by_id(eto_run_id)

    def get_run_with_pdf_data(self, eto_run_id: int) -> Optional['EtoRunWithPdfData']:
        """Get ETO run with joined PDF file and email data for API response"""
        try:
            eto_run_data = self.eto_run_repository.get_eto_run_with_pdf_data(eto_run_id)
            if not eto_run_data:
                return None

            logger.debug(f"Retrieved ETO run {eto_run_id} with PDF and email data")
            return eto_run_data

        except Exception as e:
            logger.error(f"Error getting ETO run with PDF data {eto_run_id}: {e}")
            raise ServiceError(f"Failed to get ETO run with PDF data: {e}") from e

    def get_runs(self,
                 status: Optional[str] = None,
                 limit: Optional[int] = None,
                 offset: Optional[int] = None,
                 order_by: str = "created_at",
                 order_direction: str = "desc",
                 since_date: Optional[datetime] = None):
        """
        Get ETO runs with filtering, pagination, and ordering.
        Includes email information when available.

        Args:
            status: Filter by processing status (must be valid EtoRunStatus value)
            limit: Maximum number of results (max 1000)
            offset: Number of results to skip (min 0)
            order_by: Field to order by (created_at, started_at, completed_at)
            order_direction: Sort direction (asc, desc)
            since_date: Only include runs created after this date

        Returns:
            List of EtoRunSummary objects with email information when available

        Raises:
            ServiceError: If invalid parameters provided
        """
        try:
            # Validate status parameter
            status_enum = None
            if status:
                try:
                    status_enum = EtoRunStatus(status)
                except ValueError:
                    valid_statuses = [s.value for s in EtoRunStatus]
                    raise ServiceError(f"Invalid status '{status}'. Valid values: {valid_statuses}")

            # Validate limit
            if limit is not None:
                if limit < 1 or limit > 1000:
                    raise ServiceError("Limit must be between 1 and 1000")

            # Validate offset
            if offset is not None:
                if offset < 0:
                    raise ServiceError("Offset must be >= 0")

            # Validate order_by
            valid_order_fields = ["created_at", "started_at", "completed_at"]
            if order_by not in valid_order_fields:
                raise ServiceError(f"Invalid order_by '{order_by}'. Valid values: {valid_order_fields}")

            # Validate order_direction
            if order_direction.lower() not in ["asc", "desc"]:
                raise ServiceError("Order direction must be 'asc' or 'desc'")

            # Validate since_date
            if since_date:
                since_date = DateTimeUtils.ensure_utc_aware(since_date)

            # Call repository method
            return self.eto_run_repository.get_runs_with_filters(
                status=status_enum,
                limit=limit,
                offset=offset,
                order_by=order_by,
                order_direction=order_direction,
                since_date=since_date
            )

        except ServiceError:
            # Re-raise ServiceErrors as-is
            raise
        except Exception as e:
            logger.error(f"Error getting ETO runs with filters: {e}")
            raise ServiceError(f"Failed to get ETO runs: {str(e)}")

    # ========== Helper Methods ==========

    def _get_pdf_objects(self, pdf_file_id: int) -> PdfObjects:
        """
        Get PDF objects for template matching and data extraction

        Args:
            pdf_file_id: PDF file ID to get objects for

        Returns:
            PDF objects organized by type

        Raises:
            ServiceError: If PDF file not found or no objects extracted
        """
        try:
            pdf_processing_service = self.pdf_service
            pdf_file = pdf_processing_service.get_pdf(pdf_file_id)
            if not pdf_file:
                raise ServiceError(f"PDF file {pdf_file_id} not found")

            if not pdf_file.pdf_objects or pdf_file.pdf_objects.get_total_count() == 0:
                raise ServiceError(f"No objects extracted for PDF {pdf_file_id}")

            return pdf_file.pdf_objects

        except Exception as e:
            # Re-raise as ServiceError to be caught by main processing method
            if isinstance(e, ServiceError):
                raise
            raise ServiceError(f"Failed to retrieve PDF objects for file {pdf_file_id}: {str(e)}")

    def _handle_centralized_processing_error(self, eto_run: EtoRun, error: EtoProcessingError, current_step: str) -> EtoRun:
        """
        Centralized error handling for ETO processing failures

        Args:
            eto_run: ETO run that encountered the error
            error: ETO processing error with context
            current_step: Current step when error occurred

        Returns:
            Updated ETO run with failure status and error details
        """
        # Build comprehensive error details
        error_details = {
            "timestamp": DateTimeUtils.utc_now().isoformat(),
            "error_context": "eto_processing_pipeline",
            "failed_step": current_step,
            "processing_step": error.processing_step.value,
            "eto_run_id": error.eto_run_id,
            "original_exception": str(error.original_exception) if error.original_exception else None,
            "error_class": error.__class__.__name__
        }

        # Add validation-specific details for status errors
        if isinstance(error, EtoStatusValidationError):
            error_details.update({
                "current_status": error.current_status,
                "expected_status": error.expected_status,
                "additional_requirements": error.additional_requirements
            })

        logger.error(
            f"ETO processing failed for run {eto_run.id} at step '{current_step}': "
            f"{error.error_type.value} - {error}"
        )

        return self.eto_run_repository.set_failure_with_error(
            eto_run.id, error.error_type, str(error), error_details
        )

    def _handle_processing_error(self, eto_run: EtoRun, error_type: EtoErrorType, error_message: str) -> EtoRun:
        """Legacy error handler - deprecated, use _handle_centralized_processing_error instead"""
        error_details = {
            "timestamp": DateTimeUtils.utc_now().isoformat(),
            "error_context": "eto_processing_pipeline_legacy"
        }

        return self.eto_run_repository.set_failure_with_error(
            eto_run.id, error_type, error_message, error_details
        )

    def is_healthy(self) -> bool:
        """
        Check if the ETO processing service is healthy including worker status

        Returns:
            True if service is operational, False otherwise
        """
        try:
            # Check repository access
            # Note: EtoRunRepository doesn't have count() method, using get_by_id as a test
            test_run = self.eto_run_repository.get_by_id(1)  # Just test DB access

            # Check dependent services
            if not self.pdf_service.is_healthy():
                logger.warning("PDF service is not healthy")
                return False

            if not self.template_service.is_healthy():
                logger.warning("PDF template service is not healthy")
                return False

            # Check worker status if enabled
            if self.worker_enabled and not self.worker_running:
                logger.warning("Worker is enabled but not running")
                return False

            return True

        except Exception as e:
            logger.error(f"ETO processing service health check failed: {e}")
            return False