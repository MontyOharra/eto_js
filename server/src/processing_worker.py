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
                    EtoRun.status == 'pending'
                ).order_by(EtoRun.created_at).limit(5).all()  # Process 5 at a time
                
                return runs
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting pending ETO runs: {e}")
            return []
    
    def _process_eto_run(self, eto_run: EtoRun):
        """Process a single ETO run"""
        logger.info(f"Processing ETO run {eto_run.id} (type: {eto_run.run_type})")
        
        # Mark as processing
        self._update_run_status(eto_run.id, 'processing', started_at=datetime.now())
        
        try:
            if eto_run.run_type == 'template_match':
                self._process_template_matching(eto_run)
            elif eto_run.run_type == 'data_extract':
                self._process_data_extraction(eto_run)
            else:
                raise ValueError(f"Unknown run type: {eto_run.run_type}")
                
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
        
        # Update run with match results
        self._update_run_status(
            eto_run.id,
            'completed',
            completed_at=datetime.now(),
            template_id=template_id,
            template_match_result='matched',
            template_match_confidence=match_result['confidence'],
            extracted_data=json.dumps({
                'pdf_objects': pdf_objects,
                'match_details': match_result['match_details']
            }, default=str)
        )
        
        # Create data extraction run
        self._create_data_extraction_run(eto_run.email_id, eto_run.pdf_file_id, template_id)
        
        logger.info(f"Template matching completed for run {eto_run.id}, queued for data extraction")
    
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
            'needs_template',
            completed_at=datetime.now(),
            template_match_result='no_match',
            template_match_confidence=0.0,
            extracted_data=json.dumps(extracted_data, default=str)
        )
        
        logger.info(f"Run {eto_run.id} marked as needs_template with {len(pdf_objects)} objects stored")
    
    def _process_data_extraction(self, eto_run: EtoRun):
        """Process data extraction from matched template (placeholder for future implementation)"""
        logger.info(f"Data extraction not yet implemented for run {eto_run.id}")
        
        # For now, just mark as completed
        self._update_run_status(
            eto_run.id,
            'completed',
            completed_at=datetime.now(),
            extracted_data=json.dumps({
                'status': 'data_extraction_not_implemented',
                'message': 'Data extraction will be implemented in next phase'
            })
        )
    
    def _create_data_extraction_run(self, email_id: int, pdf_file_id: int, template_id: int):
        """Create a new ETO run for data extraction"""
        try:
            eto_run_data = {
                "email_id": email_id,
                "pdf_file_id": pdf_file_id,
                "template_id": template_id,
                "run_type": "data_extract",
                "status": "pending"
            }
            
            self.db_service.create_eto_run(eto_run_data)
            logger.info(f"Created data extraction run for PDF {pdf_file_id} with template {template_id}")
            
        except Exception as e:
            logger.error(f"Error creating data extraction run: {e}")
    
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
                'failed',
                completed_at=datetime.now(),
                extraction_errors=json.dumps({'error': error_message})
            )
        except Exception as e:
            logger.error(f"Error marking run as failed: {e}")
    
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