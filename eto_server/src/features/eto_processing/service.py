"""
ETO Processing Service
Main orchestration service for the complete ETO (Extract, Transform, Order) pipeline.
Coordinates template matching, data extraction, transformation, and order creation.
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from shared.database.connection import DatabaseConnectionManager
from shared.database.repositories.eto_run import EtoRunRepository
from shared.exceptions import ServiceError, ObjectNotFoundError, EtoProcessingError, EtoStatusValidationError, EtoTemplateMatchingError, EtoDataExtractionError, EtoTransformationError
from shared.services import get_pdf_processing_service, get_pdf_template_service
from shared.models.eto_processing import (
    EtoRun, EtoRunCreate, EtoRunStatus, EtoProcessingStep, EtoErrorType,
    EtoRunStatusUpdate, EtoRunTemplateMatchUpdate, EtoRunDataExtractionUpdate,
    EtoRunTransformationUpdate, EtoRunOrderUpdate
)
from shared.models.pdf_processing import PdfObject
from shared.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class EtoProcessingService:
    """
    ETO Processing Service for complete pipeline orchestration

    Responsibilities:
    - Orchestrate the complete ETO pipeline
    - Coordinate between PDF processing, template matching, and data extraction
    - Handle processing state management and error tracking
    - Provide user-facing operations (reprocessing, skipping, etc.)
    """

    def __init__(self, connection_manager: DatabaseConnectionManager):
        """
        Initialize ETO processing service

        Args:
            connection_manager: Database connection manager
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager

        # Repository layer
        self.eto_run_repository = EtoRunRepository(connection_manager)

        logger.info("ETO Processing Service initialized")

    # ========== Main Pipeline Orchestration ==========

    def process_pdf(self, pdf_file_id: int) -> EtoRun:
        """
        Main entry point for processing a PDF through the complete ETO pipeline

        Args:
            pdf_file_id: PDF file ID to process

        Returns:
            EtoRun with final processing results

        Raises:
            ServiceError: If processing fails at any stage
        """
        eto_run = None
        current_step = "initialization"

        try:
            # Step 1: Create ETO run record
            current_step = "create_eto_run"
            eto_run = self._create_eto_run(pdf_file_id)
            logger.info(f"Created ETO run {eto_run.id} for PDF {pdf_file_id}")

            # Step 2: Start processing
            current_step = "start_processing"
            eto_run = self._start_processing(eto_run)

            # Step 3: Template matching
            current_step = "template_matching"
            eto_run = self._perform_template_matching(eto_run)

            if eto_run.status == EtoRunStatus.NEEDS_TEMPLATE:
                logger.info(f"ETO run {eto_run.id} needs template - stopping pipeline")
                return eto_run

            # Step 4: Data extraction
            current_step = "data_extraction"
            eto_run = self._perform_data_extraction(eto_run)

            # Step 5: Data transformation
            current_step = "data_transformation"
            eto_run = self._perform_data_transformation(eto_run)

            # Step 6: Order creation (placeholder for now)
            current_step = "order_creation"
            eto_run = self._perform_order_creation(eto_run)

            # Step 7: Complete processing
            current_step = "complete_processing"
            eto_run = self._complete_processing(eto_run)

            logger.info(f"Successfully completed ETO run {eto_run.id}")
            return eto_run

        except EtoProcessingError as e:
            # Handle ETO-specific processing errors
            logger.error(f"ETO processing failed at step '{current_step}' for PDF {pdf_file_id}: {e}")
            if eto_run:
                return self._handle_centralized_processing_error(eto_run, e, current_step)
            raise ServiceError(f"Failed to process PDF at {current_step}: {str(e)}")

        except Exception as e:
            # Handle unexpected system errors
            logger.error(f"Unexpected error processing PDF {pdf_file_id} at step '{current_step}': {e}")
            if eto_run:
                # Create a system error for unexpected exceptions
                system_error = EtoProcessingError(
                    message=f"Unexpected system error at {current_step}: {str(e)}",
                    eto_run_id=eto_run.id,
                    error_type=EtoErrorType.SYSTEM_ERROR,
                    processing_step=EtoProcessingStep.TEMPLATE_MATCHING,  # Default step
                    original_exception=e
                )
                return self._handle_centralized_processing_error(eto_run, system_error, current_step)
            raise ServiceError(f"Failed to process PDF at {current_step}: {str(e)}")

    def reprocess_run(self, eto_run_id: int, force: bool = False) -> EtoRun:
        """
        Reprocess an existing ETO run

        Args:
            eto_run_id: ETO run ID to reprocess
            force: Force reprocessing even if already successful

        Returns:
            EtoRun with updated processing results

        Raises:
            ObjectNotFoundError: If ETO run doesn't exist
            ServiceError: If reprocessing fails
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

            # Reset for reprocessing
            eto_run = self.eto_run_repository.reset_single_run_for_reprocessing(eto_run_id)

            logger.info(f"Reset ETO run {eto_run_id} for reprocessing")

            # Process the PDF using existing file
            return self._continue_processing(eto_run)

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

        # Find best template match
        pdf_template_service = get_pdf_template_service()
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

        # Get PDF objects
        pdf_objects = self._get_pdf_objects(eto_run.pdf_file_id)
        if not pdf_objects:
            raise EtoDataExtractionError(
                eto_run.id, "No PDF objects found for data extraction"
            )

        # Extract data using template
        pdf_template_service = get_pdf_template_service()

        # Ensure we have a matched template ID (validated in prerequisites, but type safety)
        if eto_run.matched_template_id is None:
            raise EtoDataExtractionError(eto_run.id, "No matched template ID available for data extraction")

        extracted_data = pdf_template_service.extract_data_from_template(
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

    def skip_run(self, eto_run_id: int, reason: str) -> EtoRun:
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
        logger.info(f"Skipped ETO run {eto_run_id}: {reason}")
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
        return self.eto_run_repository.get_runs_by_status(status, limit)

    def get_run_by_id(self, eto_run_id: int) -> Optional[EtoRun]:
        """Get ETO run by ID"""
        return self.eto_run_repository.get_by_id(eto_run_id)

    # ========== Helper Methods ==========

    def _get_pdf_objects(self, pdf_file_id: int) -> List[PdfObject]:
        """
        Get PDF objects for template matching and data extraction

        Args:
            pdf_file_id: PDF file ID to get objects for

        Returns:
            List of PDF objects

        Raises:
            ServiceError: If PDF file not found or no objects extracted
        """
        try:
            pdf_processing_service = get_pdf_processing_service()
            pdf_file = pdf_processing_service.get_pdf(pdf_file_id)
            if not pdf_file:
                raise ServiceError(f"PDF file {pdf_file_id} not found")

            if not pdf_file.objects_json:
                raise ServiceError(f"No objects extracted for PDF {pdf_file_id}")

            return pdf_file.objects_json

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
        Check if the ETO processing service is healthy

        Returns:
            True if service is operational, False otherwise
        """
        try:
            # Check repository access
            # Note: EtoRunRepository doesn't have count() method, using get_by_id as a test
            test_run = self.eto_run_repository.get_by_id(1)  # Just test DB access

            # Check dependent services
            pdf_processing_service = get_pdf_processing_service()
            if not pdf_processing_service.is_healthy():
                return False

            pdf_template_service = get_pdf_template_service()
            if not pdf_template_service.is_healthy():
                return False

            return True

        except Exception as e:
            logger.error(f"ETO processing service health check failed: {e}")
            return False