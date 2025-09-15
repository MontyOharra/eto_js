"""
ETO Processing Service
Background worker service that processes PDF files through the complete ETO pipeline:
template matching -> data extraction -> data transformation -> order creation
"""
import logging
import threading
import time
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ...shared.database import get_connection_manager
from ...shared.database.repositories import EtoRunRepository, PdfRepository, TemplateRepository
from ...features.pdf_processing.object_extraction_service import PdfObjectExtractionService

logger = logging.getLogger(__name__)


class EtoProcessingService:
    """Background worker service for processing ETO runs through the complete pipeline"""
    
    def __init__(self, connection_manager=None, poll_interval: int = 10, batch_size: int = 5):
        # Database infrastructure
        self.connection_manager = connection_manager or get_connection_manager()
        if not self.connection_manager:
            raise RuntimeError("Database connection manager is required")
        
        # Repository layer
        self.eto_run_repo = EtoRunRepository(self.connection_manager)
        self.pdf_repo = PdfRepository(self.connection_manager)
        self.template_repo = TemplateRepository(self.connection_manager)
        
        # Service dependencies (to be injected later)
        self.template_matching_service = None
        self.data_extraction_service = None
        self.transformation_service = None
        
        # Worker configuration
        self.poll_interval = poll_interval  # seconds between queue checks
        self.batch_size = batch_size  # max runs to process per batch
        
        # Worker state
        self.running = False
        self.worker_thread = None
        self._lock = threading.Lock()
        
        logger.info("ETO Processing Service initialized")
    
    def set_template_matching_service(self, service):
        """Inject template matching service dependency"""
        self.template_matching_service = service
        logger.info("Template matching service configured")
    
    def set_data_extraction_service(self, service):
        """Inject data extraction service dependency"""
        self.data_extraction_service = service
        logger.info("Data extraction service configured")
    
    def set_transformation_service(self, service):
        """Inject transformation service dependency"""
        self.transformation_service = service
        logger.info("Transformation service configured")
    
    def start(self):
        """Start the background processing worker"""
        with self._lock:
            if self.running:
                logger.warning("ETO processing worker is already running")
                return
            
            if not self._services_configured():
                logger.error("Cannot start worker: required services not configured")
                return
            
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("ETO processing worker started")
    
    def stop(self):
        """Stop the background processing worker"""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            logger.info("ETO processing worker stopping...")
            
            if self.worker_thread:
                self.worker_thread.join(timeout=30)
                if self.worker_thread.is_alive():
                    logger.warning("Worker thread did not stop gracefully")
                else:
                    logger.info("ETO processing worker stopped")
    
    def _services_configured(self) -> bool:
        """Check if all required services are configured"""
        return all([
            self.template_matching_service,
            self.data_extraction_service,
            self.transformation_service
        ])
    
    def _worker_loop(self):
        """Main worker loop - processes pending ETO runs"""
        logger.info("ETO processing worker loop started")
        
        while self.running:
            try:
                # Get pending ETO runs
                pending_runs = self.eto_run_repo.get_pending_runs(limit=self.batch_size)
                
                if pending_runs:
                    logger.info(f"Processing {len(pending_runs)} pending ETO runs")
                    
                    for eto_run in pending_runs:
                        if not self.running:
                            break
                        
                        try:
                            self._process_eto_run(eto_run)
                        except Exception as run_error:
                            logger.error(f"Error processing ETO run {eto_run.id}: {run_error}")
                            self.eto_run_repo.mark_as_failed(
                                eto_run.id, 
                                str(run_error),
                                error_type='processing_error'
                            )
                
                # Sleep before next poll
                if self.running:
                    time.sleep(self.poll_interval)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                if self.running:
                    time.sleep(self.poll_interval * 2)  # Back off on error
        
        logger.info("ETO processing worker loop ended")
    
    def _process_eto_run(self, eto_run):
        """
        Process a single ETO run through the complete workflow:
        not_started -> processing (template_matching -> data_extraction -> data_transformation) -> success
        """
        logger.info(f"Starting ETO run {eto_run.id} processing workflow")
        
        # Step 1: Update status to 'processing' and start with template matching
        self.eto_run_repo.update_processing_step(
            eto_run.id, 
            'processing', 
            'template_matching',
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Step 1: Template Matching
            template_id = self._process_template_matching_step(eto_run)
            if not template_id:
                # No template found - set to needs_template and stop
                return
            
            # Step 2: Data Extraction 
            extracted_data = self._process_data_extraction_step(eto_run.id, template_id)
            
            # Step 3: Data Transformation
            target_data = self._process_data_transformation_step(eto_run.id, template_id, extracted_data)
            
            # All steps completed successfully
            self.eto_run_repo.update_status(
                eto_run.id,
                'success',
                processing_step=None,  # Clear processing step on success
                completed_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"ETO run {eto_run.id} completed successfully")
                
        except Exception as e:
            logger.error(f"ETO run {eto_run.id} failed: {e}")
            self.eto_run_repo.mark_as_failed(
                eto_run.id, 
                str(e),
                error_type='pipeline_error'
            )
    
    def _process_template_matching_step(self, eto_run) -> Optional[int]:
        """
        Process template matching step of the workflow.
        
        Reads PDF objects from pdf_files.objects_json and attempts to match against templates.
        Returns template_id if match found, None if no match (sets status to 'needs_template').
        """
        logger.info(f"Starting template matching step for ETO run {eto_run.id}")
        
        try:
            # Get PDF file record to access objects_json
            pdf_file = self._get_pdf_file(eto_run.pdf_file_id)
            if not pdf_file:
                raise ValueError(f"PDF file not found: {eto_run.pdf_file_id}")
            
            # Check if PDF objects have been extracted and stored
            if not pdf_file.objects_json:
                raise ValueError(f"PDF objects not found for file {pdf_file.id} - objects_json is empty")
            
            # Parse the stored PDF objects JSON
            try:
                pdf_objects = json.loads(pdf_file.objects_json)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"Invalid PDF objects JSON for file {pdf_file.id}: {e}")
            
            logger.debug(f"Using {len(pdf_objects)} PDF objects from pdf_files.objects_json for template matching")
            
            # Perform template matching using the template matcher service
            match_result = self.template_matching_service.find_best_template_match(pdf_objects)
            
            if match_result and match_result.get('matched'):
                # Template found - return the template ID so processing can continue
                template_id = match_result['template_id']
                template_name = match_result.get('template_name', 'Unknown')
                
                logger.info(f"Template matched for run {eto_run.id}: '{template_name}' (ID: {template_id})")
                
                # Store the matched template ID in the ETO run
                self.eto_run_repo.update_processing_step(
                    eto_run.id,
                    'processing',  # Keep in processing status
                    'template_matching',  # Still in template matching step
                    matched_template_id=template_id,
                    template_match_coverage=match_result.get('coverage', 0.0),
                    unmatched_object_count=match_result.get('unmatched_objects', 0)
                )
                
                return template_id
            else:
                # No template match - set status to needs_template and stop processing
                logger.info(f"No template match found for run {eto_run.id}, setting status to 'needs_template'")
                
                self.eto_run_repo.update_status(
                    eto_run.id,
                    'needs_template',
                    processing_step=None,  # Clear processing step
                    completed_at=datetime.now(timezone.utc),
                    suggested_new_template=True
                )
                
                return None
                
        except Exception as e:
            logger.error(f"Template matching failed for run {eto_run.id}: {e}")
            raise
    
    def _process_data_extraction_step(self, run_id: int, template_id: int) -> Dict[str, Any]:
        """
        Process data extraction step using the matched template.
        Returns extracted data dictionary.
        """
        logger.info(f"Starting data extraction step for ETO run {run_id} with template {template_id}")
        
        # Update processing step
        self.eto_run_repo.update_processing_step(run_id, 'processing', 'extracting_data')
        
        try:
            # Get PDF objects for extraction
            eto_run = self.eto_run_repo.get_by_id(run_id)
            pdf_file = self._get_pdf_file(eto_run.pdf_file_id)
            pdf_objects = json.loads(pdf_file.objects_json)
            
            # Perform data extraction using the data extraction service
            extracted_data = self.data_extraction_service.extract_fields_from_pdf(pdf_objects, template_id)
            
            # Store extracted data in the run
            self.eto_run_repo.update(run_id, {'extracted_data': extracted_data})
            
            logger.info(f"Data extraction completed for run {run_id}, extracted {len(extracted_data)} fields")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Data extraction failed for run {run_id}: {e}")
            raise
    
    def _process_data_transformation_step(self, run_id: int, template_id: int, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data transformation step to convert extracted data to target format.
        Returns transformed target data dictionary.
        """
        logger.info(f"Starting data transformation step for ETO run {run_id}")
        
        # Update processing step
        self.eto_run_repo.update_processing_step(run_id, 'processing', 'transforming_data')
        
        try:
            # Perform data transformation using the transformation service
            transformation_result = self.transformation_service.transform_extracted_data(
                extracted_data, 
                template_id
            )
            
            target_data = transformation_result['target_data']
            audit_trail = transformation_result.get('audit_trail', {})
            
            # Store transformation results in the run
            self.eto_run_repo.update(run_id, {
                'target_data': target_data,
                'transformation_audit': audit_trail
            })
            
            logger.info(f"Data transformation completed for run {run_id}")
            return target_data
            
        except Exception as e:
            logger.error(f"Data transformation failed for run {run_id}: {e}")
            raise
    
    def _get_pdf_file(self, pdf_file_id: int):
        """Get PDF file by ID using repository"""
        pdf_files = self.pdf_repo.get_by_field('id', pdf_file_id)
        return pdf_files[0] if pdf_files else None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processing status and statistics"""
        return {
            'running': self.running,
            'poll_interval': self.poll_interval,
            'batch_size': self.batch_size,
            'services_configured': self._services_configured(),
            'pending_runs': len(self.eto_run_repo.get_pending_runs()),
            'processing_runs': len(self.eto_run_repo.get_processing_runs()),
            'statistics': self.eto_run_repo.get_processing_statistics()
        }
    
    def process_single_run(self, run_id: int) -> bool:
        """Process a single ETO run manually (for testing/debugging)"""
        try:
            eto_run = self.eto_run_repo.get_by_id(run_id)
            if not eto_run:
                logger.error(f"ETO run {run_id} not found")
                return False
            
            if not self._services_configured():
                logger.error("Cannot process run: required services not configured")
                return False
            
            self._process_eto_run(eto_run)
            return True
            
        except Exception as e:
            logger.error(f"Error processing single run {run_id}: {e}")
            return False


# Global service instance
_eto_processing_service: Optional[EtoProcessingService] = None


def get_eto_processing_service() -> Optional[EtoProcessingService]:
    """Get the global ETO processing service instance"""
    return _eto_processing_service


def init_eto_processing_service(connection_manager=None, **config) -> EtoProcessingService:
    """Initialize the global ETO processing service"""
    global _eto_processing_service
    
    if _eto_processing_service is not None:
        logger.warning("ETO processing service already initialized")
        return _eto_processing_service
    
    _eto_processing_service = EtoProcessingService(
        connection_manager=connection_manager,
        **config
    )
    
    logger.info("ETO processing service initialized")
    return _eto_processing_service


def start_eto_processing_service():
    """Start the background ETO processing worker"""
    if _eto_processing_service:
        _eto_processing_service.start()
    else:
        logger.error("ETO processing service not initialized")


def stop_eto_processing_service():
    """Stop the background ETO processing worker"""
    if _eto_processing_service:
        _eto_processing_service.stop()