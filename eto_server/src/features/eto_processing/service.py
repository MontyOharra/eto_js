"""
ETO Processing Service
Background worker service that processes PDF files through the complete ETO pipeline:
template matching -> data extraction -> data transformation -> order creation
"""
import json
import logging
import threading
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from shared.database import get_connection_manager
from shared.database.repositories import EtoRunRepository
from shared.utils.service_registry import get_pdf_processing_service, get_pdf_template_service
from shared.domain import EtoErrorType, EtoRunStatus, EtoProcessingStep, PdfObject

logger = logging.getLogger(__name__)


class EtoProcessingService:
    """Background worker service for processing ETO runs through the complete pipeline"""

    def __init__(self,poll_interval: int = 10, batch_size: int = 5):
        
        self.connection_manager = get_connection_manager()

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
        pdf_processing_service = get_pdf_processing_service()
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
            "email_id": pdf_file['email_id'],
            "pdf_file_id": pdf_id,
            "status": "not_started"
        }

        eto_run = self.eto_run_repo.create(eto_run_data)
        logger.info(f"Created ETO run {eto_run.id} for PDF {pdf_id}")

        return eto_run

    # === Worker Process Management ===

    def start(self):
        """Start the background processing worker"""
        with self._lock:
            if self.running:
                logger.warning("ETO processing worker is already running")
                return

            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info(f"ETO processing worker started (poll interval: {self.poll_interval}s, batch size: {self.batch_size})")

    def stop(self):
        """Stop the background processing worker"""
        with self._lock:
            if not self.running:
                logger.warning("ETO processing worker is not running")
                return

            self.running = False
            logger.info("ETO processing worker stop requested")

        # Wait for worker thread to finish (outside the lock)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)  # Wait max 10 seconds
            if self.worker_thread.is_alive():
                logger.warning("ETO processing worker did not stop within timeout")
            else:
                logger.info("ETO processing worker stopped successfully")

    def get_status(self) -> Dict[str, Any]:
        """Get current processing status and statistics"""
        try:
            stats = None

            return {
                "worker_running": self.running,
                "poll_interval": self.poll_interval,
                "batch_size": self.batch_size,
                "processing_statistics": stats,
                "pending_runs_count": len(self.get_pending_runs()),
                "processing_runs_count": len(self._get_processing_runs())
            }
        except Exception as e:
            logger.error(f"Error getting ETO processing status: {e}")
            return {
                "worker_running": self.running,
                "error": str(e)
            }

    # === Core Processing Pipeline ===

    def _process_eto_run(self, eto_run):
        """
        Main orchestration method that handles the full pipeline:
        not_started -> processing (template_matching -> data_extraction -> data_transformation) -> success
        """
        try:
            logger.info(f"Starting ETO processing for run {eto_run.id}")

            # Update status to processing and set initial step
            self.eto_run_repo.update_processing_step(
                run_id=eto_run.id,
                status="processing",
                processing_step="template_matching"
            )

            # Step 1: Template Matching
            template_id = self._process_template_matching_step(eto_run)
            if template_id is None:
                # Template matching failed or no template found - already handled
                return

            # Step 2: Data Extraction
            extracted_data = self._process_data_extraction_step(eto_run, template_id)
            if not extracted_data:
                # Data extraction failed - already handled
                return

            # Step 3: Data Transformation
            transformed_data = self._process_data_transformation_step(eto_run, template_id, extracted_data)
            if not transformed_data:
                # Data transformation failed - already handled
                return

            logger.info(f"ETO processing completed successfully for run {eto_run.id}")

        except Exception as e:
            logger.error(f"Unexpected error in ETO processing for run {eto_run.id}: {e}")
            self._mark_as_failed(
                eto_run.id,
                f"Processing pipeline failed: {str(e)}",
                error_type="pipeline_error",
                error_details={"error": str(e), "step": "pipeline_orchestration"}
            )

    def _process_template_matching_step(self, eto_run) -> Optional[int]:
        """
        Handle template matching step using PDF Template Service

        Args:
            eto_run: EtoRun domain object

        Returns:
            template_id if match found, None if no match or error
        """
        try:
            # 1. Get PDF Template Service
            pdf_template_service = get_pdf_template_service()
            if not pdf_template_service:
                # Create PDF template service with our connection manager
                from features.pdf_templates.service import PdfTemplateService
                pdf_template_service = PdfTemplateService()

            # 2. Get PDF objects from PDF Processing Service
            pdf_processing_service = get_pdf_processing_service()
            if not pdf_processing_service:
                raise RuntimeError("PDF processing service not available")

            if not (pdf_file := pdf_processing_service.get_pdf_by_id(eto_run.pdf_file_id)) or not (objects_json := pdf_file.objects_json):
                logger.warning(f"No PDF objects found for PDF {eto_run.pdf_file_id}")
                self._mark_as_needs_template(eto_run.id)
                return None

            # Parse JSON and convert to PdfObject instances
            try:
                objects_data = json.loads(objects_json)
                pdf_objects = [PdfObject(**obj_data) for obj_data in objects_data]
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.error(f"Failed to parse PDF objects JSON for PDF {eto_run.pdf_file_id}: {e}")
                self._mark_as_failed(
                    eto_run.id,
                    f"Invalid PDF objects data: {str(e)}",
                    error_type="template_matching_error",
                    error_details={"error": str(e), "step": "json_parsing"}
                )
                return None

            # 3. Perform template matching
            match_result = pdf_template_service.find_best_template_match(pdf_objects)

            # 4. Handle results and update ETO run accordingly
            if match_result.template_found:
                # SUCCESS: Update with template match and move to data extraction
                self.eto_run_repo.update_status(
                    id=eto_run.id,
                    status="processing",
                    processing_step="extracting_data",  # Move to next step
                    matched_template_id=match_result.template_id,
                    template_version=match_result.template_version,
                    template_match_coverage=match_result.coverage_percentage
                )

                logger.info(f"Template match found for ETO run {eto_run.id}: "
                           f"template {match_result.template_id} with {match_result.coverage_percentage:.2f}% coverage")

                return match_result.template_id
            else:
                # NO MATCH: Mark as needs_template
                self._mark_as_needs_template(eto_run.id)
                logger.info(f"No template match found for ETO run {eto_run.id}")
                return None

        except Exception as e:
            logger.error(f"Error in template matching for ETO run {eto_run.id}: {e}")
            self._mark_as_failed(
                eto_run.id,
                f"Template matching failed: {str(e)}",
                error_type="template_matching_error",
                error_details={"error": str(e), "step": "template_matching"}
            )
            return None

    def _process_data_extraction_step(self, eto_run, template_id) -> Dict[str, Any]:
        """Handle data extraction step (stub implementation)"""
        try:
            # Update status to show we're in transformation step
            self.eto_run_repo.update_processing_step(
                run_id=eto_run.id,
                status="processing",
                processing_step="transforming_data"
            )

            # Stub: Return dummy extracted data
            extracted_data = {
                "customer_name": "Sample Customer",
                "order_date": "2024-01-15",
                "total_amount": "1234.56",
                "order_items": [
                    {"item": "Product A", "quantity": 2, "price": "500.00"},
                    {"item": "Product B", "quantity": 1, "price": "234.56"}
                ]
            }

            # Store extracted data in ETO run
            self.eto_run_repo.update_status(
                id=eto_run.id,
                status="processing",
                extracted_data=json.dumps(extracted_data)
            )

            logger.info(f"Data extraction completed for ETO run {eto_run.id} (stub implementation)")
            return extracted_data

        except Exception as e:
            logger.error(f"Error in data extraction for ETO run {eto_run.id}: {e}")
            self._mark_as_failed(
                eto_run.id,
                f"Data extraction failed: {str(e)}",
                error_type="data_extraction_error",
                error_details={"error": str(e), "step": "data_extraction"}
            )
            raise

    def _process_data_transformation_step(self, eto_run, template_id: int, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transformation step (stub implementation)"""
        try:
            # Stub: Transform extracted data to target format
            transformed_data = {
                "order": {
                    "customer": {
                        "name": extracted_data.get("customer_name", "Unknown"),
                        "id": "CUST_001"
                    },
                    "order_date": extracted_data.get("order_date"),
                    "total": float(extracted_data.get("total_amount", "0.00")),
                    "currency": "USD",
                    "items": [
                        {
                            "sku": f"SKU_{i}",
                            "name": item.get("item"),
                            "quantity": int(item.get("quantity", 0)),
                            "unit_price": float(item.get("price", "0.00"))
                        }
                        for i, item in enumerate(extracted_data.get("order_items", []), 1)
                    ],
                    "source": {
                        "template_id": template_id,
                        "processing_method": "eto_automated"
                    }
                }
            }

            # Create transformation audit trail
            transformation_audit = {
                "input_data": extracted_data,
                "output_data": transformed_data,
                "transformation_rules": ["customer_mapping", "item_standardization", "price_formatting"],
                "processed_at": datetime.now(timezone.utc).isoformat()
            }

            # Mark as successful and store final data
            self.eto_run_repo.update_status(
                id=eto_run.id,
                status="success",
                processing_step=None,  # Clear processing step on success
                target_data=json.dumps(transformed_data),
                transformation_audit=json.dumps(transformation_audit)
            )

            logger.info(f"Data transformation completed for ETO run {eto_run.id} (stub implementation)")
            return transformed_data

        except Exception as e:
            logger.error(f"Error in data transformation for ETO run {eto_run.id}: {e}")
            self._mark_as_failed(
                eto_run.id,
                f"Data transformation failed: {str(e)}",
                error_type="transformation_error",
                error_details={"error": str(e), "step": "data_transformation"}
            )
            raise

    # === Error & Status Management ===

    def _mark_as_failed(self, id: int, error_message: str, error_type: EtoErrorType, error_details: dict):
        """Set status to 'failure' and end processing"""
        try:
            updated_run = self.eto_run_repo.mark_as_failed(
                id=id,
                error_message=error_message,
                error_type=error_type,
                error_details=error_details
            )

            if updated_run:
                logger.info(f"ETO run {id} marked as failed: {error_message}")
                return updated_run
            else:
                logger.error(f"Failed to mark ETO run {id} as failed")
                return None

        except Exception as e:
            logger.error(f"Error marking ETO run {id} as failed: {e}")
            raise

    def _mark_as_needs_template(self, id: int):
        """Set status to 'needs_template' and end processing"""
        try:
            updated_run = self.eto_run_repo.update_status(
                id=id,
                status="needs_template",
                processing_step=None  # Clear processing step
            )

            if updated_run:
                logger.info(f"ETO run {id} marked as needs template")
                return updated_run
            else:
                logger.error(f"Failed to mark ETO run {id} as needs template")
                return None

        except Exception as e:
            logger.error(f"Error marking ETO run {id} as needs template: {e}")
            raise

    def _mark_as_success(self, id: int):
        """Set status to 'success', processing_step to null"""
        try:
            updated_run = self.eto_run_repo.update_status(
                id=id,
                status="success",
                processing_step=None  # Clear processing step on success
            )

            if updated_run:
                logger.info(f"ETO run {id} marked as successful")
                return updated_run
            else:
                logger.error(f"Failed to mark ETO run {id} as successful")
                return None

        except Exception as e:
            logger.error(f"Error marking ETO run {id} as successful: {e}")
            raise

    # === Utility Methods ===

    def process_single_run(self, run_id: int) -> bool:
        """Manual processing trigger for testing/debugging"""
        try:
            eto_run = self.eto_run_repo.get_by_id(run_id)
            if not eto_run:
                logger.error(f"ETO run {run_id} not found")
                return False

            if eto_run.status not in ["not_started", "failure"]:
                logger.warning(f"ETO run {run_id} is not in a processable state (status: {eto_run.status})")
                return False

            self._process_eto_run(eto_run)
            return True

        except Exception as e:
            logger.error(f"Error processing single ETO run {run_id}: {e}")
            return False

    def get_pending_runs(self):
        """Get ETO runs with status 'not_started'"""
        return self.eto_run_repo.get_by_status("not_started")

    def _get_processing_runs(self):
        """Get ETO runs currently in processing state"""
        return self.eto_run_repo.get_by_status("processing")

    def _worker_loop(self):
        """Background loop that polls and processes pending runs"""
        logger.info("ETO processing worker loop started")

        while self.running:
            try:
                # Get pending runs
                pending_runs = self.eto_run_repo.get_by_status("not_started", limit=self.batch_size)

                if pending_runs:
                    logger.info(f"Processing {len(pending_runs)} pending ETO runs")

                    for eto_run in pending_runs:
                        if not self.running:  # Check if we should stop
                            break

                        try:
                            self._process_eto_run(eto_run)
                        except Exception as e:
                            logger.error(f"Error processing ETO run {eto_run.id}: {e}")
                            # Individual run errors are handled within _process_eto_run
                            continue

                # Sleep before next poll
                if self.running:  # Only sleep if still running
                    time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in ETO processing worker loop: {e}")
                if self.running:
                    time.sleep(self.poll_interval)  # Wait before retrying

        logger.info("ETO processing worker loop ended")