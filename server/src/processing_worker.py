"""
ETO Processing Worker Service
Handles background processing of PDFs for template matching and data extraction
"""

import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .database import get_db_service, EtoRun, PdfFile
from .pdf_objects import get_pdf_extractor
from .template_matching import get_template_matcher

logger = logging.getLogger(__name__)

class EtoProcessingWorker:
    """Background worker service for processing ETO runs"""
    
    def __init__(self):
        self.running = False
        self.worker_thread = None
        self.db_service = None
        self.pdf_extractor = None
        self.template_matcher = None
        self.poll_interval = 10  # seconds between queue checks
        self._lock = threading.Lock()
    
    def set_services(self, db_service, pdf_extractor, template_matcher):
        """Set required services for processing"""
        self.db_service = db_service
        self.pdf_extractor = pdf_extractor
        self.template_matcher = template_matcher
        logger.info("Processing worker services configured")
    
    def start(self):
        """Start the background processing worker"""
        with self._lock:
            if self.running:
                logger.warning("Processing worker is already running")
                return
            
            if not all([self.db_service, self.pdf_extractor, self.template_matcher]):
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
    
    def _worker_loop(self):
        """Main worker loop - processes pending ETO runs"""
        logger.info("Processing worker loop started")
        
        while self.running:
            try:
                # Get pending ETO runs
                pending_runs = self._get_pending_eto_runs()
                
                if pending_runs:
                    logger.info(f"Processing {len(pending_runs)} pending ETO runs")
                    
                    for eto_run in pending_runs:
                        if not self.running:
                            break
                        
                        try:
                            self._process_eto_run(eto_run)
                        except Exception as run_error:
                            logger.error(f"Error processing ETO run {eto_run.id}: {run_error}")
                            self._mark_run_failed(eto_run.id, str(run_error))
                
                # Sleep before next poll
                if self.running:
                    time.sleep(self.poll_interval)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                if self.running:
                    time.sleep(self.poll_interval * 2)  # Back off on error
        
        logger.info("Processing worker loop ended")
    
    def _get_pending_eto_runs(self) -> list:
        """Get pending ETO runs from database"""
        try:
            session = self.db_service.get_session()
            try:
                runs = session.query(EtoRun).filter(
                    EtoRun.status == 'unprocessed'
                ).order_by(EtoRun.created_at).limit(5).all()  # Process 5 at a time
                
                return runs
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting pending ETO runs: {e}")
            return []
    
    def _process_eto_run(self, eto_run: EtoRun):
        """Process a single ETO run"""
        logger.info(f"Processing ETO run {eto_run.id} (status: {eto_run.status})")
        
        # Mark as processing  
        self._update_run_status(eto_run.id, 'processing', started_at=datetime.now())
        
        try:
            # For now, all runs go through template matching first
            self._process_template_matching(eto_run)
                
        except Exception as e:
            logger.error(f"Failed to process ETO run {eto_run.id}: {e}")
            self._mark_run_failed(eto_run.id, str(e))
    
    def _process_template_matching(self, eto_run: EtoRun):
        """Process template matching for a PDF"""
        try:
            # Get PDF file info
            pdf_file = self._get_pdf_file(eto_run.pdf_file_id)
            if not pdf_file:
                raise ValueError(f"PDF file not found: {eto_run.pdf_file_id}")
            
            logger.info(f"Extracting objects from PDF: {pdf_file.original_filename}")
            
            # Extract PDF objects
            extraction_result = self.pdf_extractor.extract_objects_from_file_path(pdf_file.file_path)
            
            if not extraction_result['success']:
                raise ValueError(f"PDF object extraction failed: {extraction_result.get('error', 'Unknown error')}")
            
            pdf_objects = extraction_result['objects']
            signature_hash = extraction_result['signature_hash']
            
            logger.info(f"Extracted {len(pdf_objects)} objects with signature {signature_hash[:8]}...")
            
            # Find template match
            match_result = self.template_matcher.find_best_template_match(pdf_objects)
            
            if match_result['matched']:
                # Template matched - mark as completed and queue for data extraction
                self._handle_template_matched(eto_run, match_result, pdf_objects, signature_hash)
            else:
                # No template match - mark as needs template
                self._handle_no_template_match(eto_run, match_result, pdf_objects, signature_hash)
                
        except Exception as e:
            logger.error(f"Template matching failed for run {eto_run.id}: {e}")
            raise
    
    def _handle_template_matched(self, eto_run: EtoRun, match_result: Dict[str, Any], 
                                pdf_objects: list, signature_hash: str):
        """Handle successful template match"""
        template_id = match_result['template_id']
        template_name = match_result['template_name']
        
        logger.info(f"Template matched for run {eto_run.id}: '{template_name}' (ID: {template_id})")
        
        # Update run status to extracting_data and start extraction
        self._update_run_status(
            eto_run.id,
            'extracting_data',
            matched_template_id=template_id
        )
        
        # Process base data extraction
        logger.info(f"Starting base data extraction for run {eto_run.id}")
        self._extract_base_data(eto_run.id, template_id)
        
        logger.info(f"Template matching and base extraction initiated for run {eto_run.id}")
    
    def _handle_no_template_match(self, eto_run: EtoRun, match_result: Dict[str, Any], 
                                 pdf_objects: list, signature_hash: str):
        """Handle no template match - needs manual template creation"""
        logger.info(f"No template match for run {eto_run.id}, marking as needs_template")
        
        # Store PDF objects for template creation by client
        extracted_data = {
            'pdf_objects': pdf_objects,
            'signature_hash': signature_hash,
            'match_details': match_result.get('match_details', {}),
            'candidates_checked': len(match_result.get('candidates', []))
        }
        
        self._update_run_status(
            eto_run.id,
            'unrecognized',
            completed_at=datetime.now(),
            extracted_data=json.dumps(extracted_data, default=str)
        )
        
        logger.info(f"Run {eto_run.id} marked as unrecognized with {len(pdf_objects)} objects stored")
    
    def _process_data_extraction(self, eto_run: EtoRun):
        """Process data extraction from matched template using spatial bounding boxes"""
        logger.info(f"Starting data extraction for run {eto_run.id}")
        
        try:
            # Get PDF objects from the previously extracted data
            if not eto_run.extracted_data:
                raise ValueError("No extracted data found for template-matched run")
            
            stored_data = json.loads(eto_run.extracted_data)
            pdf_objects = stored_data.get('pdf_objects', [])
            
            if not pdf_objects:
                raise ValueError("No PDF objects found in extracted data")
            
            if not eto_run.matched_template_id:
                raise ValueError("No matched template ID for data extraction")
            
            logger.info(f"Extracting fields using template {eto_run.matched_template_id} from {len(pdf_objects)} PDF objects")
            
            # Use template matcher to extract field data using spatial bounding boxes
            extracted_fields = self.template_matcher.extract_fields_from_pdf(
                pdf_objects, 
                eto_run.matched_template_id
            )
            
            if not extracted_fields:
                logger.warning(f"No fields extracted for run {eto_run.id} - template may have no extraction fields defined")
                extraction_status = 'no_fields_defined'
            else:
                extraction_status = 'success'
                logger.info(f"Successfully extracted {len(extracted_fields)} fields: {list(extracted_fields.keys())}")
            
            # Store extracted field data
            final_extracted_data = {
                'extraction_status': extraction_status,
                'extracted_fields': extracted_fields,
                'template_id': eto_run.matched_template_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'pdf_object_count': len(pdf_objects)
            }
            
            # Mark run as completed with extracted field data
            self._update_run_status(
                eto_run.id,
                'success',
                completed_at=datetime.now(),
                extracted_data=json.dumps(final_extracted_data, default=str)
            )
            
            logger.info(f"Data extraction completed successfully for run {eto_run.id}")
            
        except Exception as e:
            logger.error(f"Data extraction failed for run {eto_run.id}: {e}")
            
            # Mark run as failed with error details
            self._update_run_status(
                eto_run.id,
                'error',
                completed_at=datetime.now(),
                error_type='data_extraction_error',
                error_message=str(e)
            )
            raise
    
    def _process_data_extraction_with_objects(self, run_id: int, template_id: int, pdf_objects: list):
        """Process data extraction using provided PDF objects (bypasses database read)"""
        logger.info(f"Starting data extraction for run {run_id} with {len(pdf_objects)} objects")
        
        try:
            if not pdf_objects:
                raise ValueError("No PDF objects provided for data extraction")
            
            if not template_id:
                raise ValueError("No template ID provided for data extraction")
            
            logger.info(f"Extracting fields using template {template_id} from {len(pdf_objects)} PDF objects")
            
            # Use template matcher to extract field data using spatial bounding boxes
            extracted_fields = self.template_matcher.extract_fields_from_pdf(
                pdf_objects, 
                template_id
            )
            
            if not extracted_fields:
                logger.warning(f"No fields extracted for run {run_id} - template may have no extraction fields defined")
                extraction_status = 'no_fields_defined'
            else:
                extraction_status = 'success'
                logger.info(f"Successfully extracted {len(extracted_fields)} fields: {list(extracted_fields.keys())}")
            
            # Store extracted field data
            final_extracted_data = {
                'extraction_status': extraction_status,
                'extracted_fields': extracted_fields,
                'template_id': template_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'pdf_object_count': len(pdf_objects)
            }
            
            # Mark run as completed with extracted field data
            self._update_run_status(
                run_id,
                'success',
                completed_at=datetime.now(),
                extracted_data=json.dumps(final_extracted_data, default=str)
            )
            
            logger.info(f"Data extraction completed successfully for run {run_id}")
            
        except Exception as e:
            logger.error(f"Data extraction failed for run {run_id}: {e}")
            
            # Mark run as failed with error details
            self._update_run_status(
                run_id,
                'error',
                completed_at=datetime.now(),
                error_type='data_extraction_error',
                error_message=str(e)
            )
            raise
    
    def _create_data_extraction_run(self, email_id: int, pdf_file_id: int, template_id: int):
        """Create a new ETO run for data extraction - DEPRECATED: Now processing inline"""
        # This method is no longer used - data extraction is processed immediately
        # after template matching to avoid infinite loops
        logger.warning("_create_data_extraction_run called but is deprecated - processing should be inline")
        pass
    
    def _get_pdf_file(self, pdf_file_id: int) -> Optional[PdfFile]:
        """Get PDF file by ID"""
        session = self.db_service.get_session()
        try:
            return session.query(PdfFile).filter(PdfFile.id == pdf_file_id).first()
        finally:
            session.close()
    
    def _update_run_status(self, run_id: int, status: str, **kwargs):
        """Update ETO run status and other fields"""
        try:
            self.db_service.update_eto_run_status(run_id, status, **kwargs)
        except Exception as e:
            logger.error(f"Error updating run status: {e}")
    
    def _mark_run_failed(self, run_id: int, error_message: str):
        """Mark ETO run as failed"""
        try:
            self._update_run_status(
                run_id,
                'error',
                completed_at=datetime.now(),
                error_type='processing_error',
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Error marking run as failed: {e}")
    
    def reprocess_unrecognized_runs(self):
        """Reprocess all unrecognized ETO runs - typically called when new templates are added"""
        try:
            session = self.db_service.get_session()
            try:
                # Find all unrecognized runs
                unrecognized_runs = session.query(EtoRun).filter(
                    EtoRun.status == 'unrecognized'
                ).all()
                
                if not unrecognized_runs:
                    logger.info("No unrecognized runs found to reprocess")
                    return {"reprocessed": 0, "message": "No unrecognized runs found"}
                
                # Mark them as unprocessed so they get picked up by the worker
                reprocessed_count = 0
                for run in unrecognized_runs:
                    self._update_run_status(
                        run.id, 
                        'unprocessed',
                        # Clear previous results to start fresh
                        matched_template_id=None,
                        extracted_data=None,
                        error_type=None,
                        error_message=None,
                        completed_at=None
                    )
                    reprocessed_count += 1
                
                logger.info(f"Marked {reprocessed_count} unrecognized runs for reprocessing")
                return {"reprocessed": reprocessed_count, "message": f"Marked {reprocessed_count} runs for reprocessing"}
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error reprocessing unrecognized runs: {e}")
            return {"reprocessed": 0, "error": str(e)}

    def get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status"""
        return {
            "running": self.running,
            "poll_interval": self.poll_interval,
            "thread_alive": self.worker_thread.is_alive() if self.worker_thread else False,
            "services_configured": all([self.db_service, self.pdf_extractor, self.template_matcher])
        }

# Global processing worker instance
processing_worker = None

def init_processing_worker(db_service, pdf_extractor, template_matcher):
    """Initialize the processing worker"""
    global processing_worker
    processing_worker = EtoProcessingWorker()
    processing_worker.set_services(db_service, pdf_extractor, template_matcher)
    logger.info("ETO processing worker initialized")
    return processing_worker

def get_processing_worker():
    """Get the global processing worker instance"""
    if processing_worker is None:
        raise RuntimeError("Processing worker not initialized. Call init_processing_worker() first.")
    return processing_worker

def start_processing_worker():
    """Start the processing worker if not already running"""
    worker = get_processing_worker()
    worker.start()

def stop_processing_worker():
    """Stop the processing worker"""
    if processing_worker:
        processing_worker.stop()

def trigger_reprocessing():
    """Trigger reprocessing of unrecognized ETO runs"""
    if processing_worker is None:
        raise RuntimeError("Processing worker not initialized. Call init_processing_worker() first.")
    return processing_worker.reprocess_unrecognized_runs()