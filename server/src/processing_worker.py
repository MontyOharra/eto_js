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
                    EtoRun.status == 'not_started'
                ).order_by(EtoRun.created_at).limit(5).all()  # Process 5 at a time
                
                return runs
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting pending ETO runs: {e}")
            return []
    
    def _process_eto_run(self, eto_run: EtoRun):
        """
        Process a single ETO run through the complete workflow:
        not_started -> processing (template_matching -> extracting_data -> transforming_data) -> success
        """
        logger.info(f"Starting ETO run {eto_run.id} processing workflow")
        
        # Step 1: Update status to 'processing' and start with template matching
        self._update_run_status(
            eto_run.id, 
            'processing', 
            processing_step='template_matching',
            started_at=datetime.now()
        )
        
        try:
            # Step 1: Template Matching
            template_id = self._process_template_matching_step(eto_run)
            if not template_id:
                # No template found - set to needs_template and stop
                return
            
            # Step 2: Data Extraction 
            self._process_data_extraction_step(eto_run.id, template_id)
            
            # Step 3: Data Transformation
            self._process_data_transformation_step(eto_run.id, template_id)
            
            # All steps completed successfully
            self._update_run_status(
                eto_run.id,
                'success',
                processing_step=None,  # Clear processing step on success
                completed_at=datetime.now()
            )
            
            logger.info(f"ETO run {eto_run.id} completed successfully")
                
        except Exception as e:
            logger.error(f"ETO run {eto_run.id} failed: {e}")
            self._mark_run_failed(eto_run.id, str(e))
    
    def _process_template_matching_step(self, eto_run: EtoRun) -> Optional[int]:
        """
        Process template matching step of the workflow.
        
        Reads PDF objects from pdf_files.objects_json and attempts to match against templates.
        Returns template_id if match found, None if no match (and sets status to 'needs_template').
        
        This follows the new workflow where PDF objects are stored in pdf_files table,
        not in eto_runs table.
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
            
            logger.info(f"Using {len(pdf_objects)} PDF objects from pdf_files.objects_json for template matching")
            
            # Perform template matching using the template matcher service
            match_result = self.template_matcher.find_best_template_match(pdf_objects)
            
            if match_result['matched']:
                # Template found - return the template ID so processing can continue
                template_id = match_result['template_id']
                template_name = match_result['template_name']
                
                logger.info(f"Template matched for run {eto_run.id}: '{template_name}' (ID: {template_id})")
                
                # Store the matched template ID in the ETO run
                self._update_run_status(
                    eto_run.id,
                    'processing',  # Keep in processing status
                    processing_step='template_matching',  # Still in template matching step
                    matched_template_id=template_id
                )
                
                return template_id
            else:
                # No template match - set status to needs_template and stop processing
                logger.info(f"No template match found for run {eto_run.id}, setting status to 'needs_template'")
                
                self._update_run_status(
                    eto_run.id,
                    'needs_template',
                    processing_step=None,  # Clear processing step
                    completed_at=datetime.now(),
                    extracted_data=None  # No data extracted since no template found
                )
                
                return None
                
        except Exception as e:
            logger.error(f"Template matching step failed for run {eto_run.id}: {e}")
            raise

    def _process_data_extraction_step(self, run_id: int, template_id: int):
        """
        Process data extraction step of the workflow.
        
        Updates processing step to 'extracting_data', reads PDF objects from pdf_files table,
        uses template's extraction_fields to extract data from spatial bounding boxes,
        and stores results in extracted_data column.
        
        This is the second step in the processing workflow: template_matching -> extracting_data -> transforming_data
        """
        logger.info(f"Starting data extraction step for ETO run {run_id}")
        
        # Update processing step to extracting_data
        self._update_run_status(
            run_id,
            'processing',
            processing_step='extracting_data'
        )
        
        try:
            # Get the ETO run to access pdf_file_id
            session = self.db_service.get_session()
            try:
                eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
                if not eto_run:
                    raise ValueError(f"ETO run not found: {run_id}")
                
                # Get PDF file record to access objects_json
                pdf_file = self._get_pdf_file(eto_run.pdf_file_id)
                if not pdf_file:
                    raise ValueError(f"PDF file not found: {eto_run.pdf_file_id}")
                
                # Parse PDF objects from the stored JSON
                if not pdf_file.objects_json:
                    raise ValueError(f"PDF objects not found for file {pdf_file.id} - objects_json is empty")
                
                try:
                    pdf_objects = json.loads(pdf_file.objects_json)
                except (json.JSONDecodeError, TypeError) as e:
                    raise ValueError(f"Invalid PDF objects JSON for file {pdf_file.id}: {e}")
                
                logger.info(f"Using {len(pdf_objects)} PDF objects from pdf_files.objects_json for data extraction")
                
            finally:
                session.close()
            
            # Use template matcher to extract field data using spatial bounding boxes
            # This uses the extraction_fields stored in the template to define what to extract
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
            
            # Store the base extracted data in the extracted_data column
            # This is the raw field data extracted from bounding boxes before any transformation
            base_extracted_data = {
                'extraction_status': extraction_status,
                'extracted_fields': extracted_fields,
                'template_id': template_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'pdf_object_count': len(pdf_objects)
            }
            
            # Update the run with the extracted data
            self._update_run_status(
                run_id,
                'processing',  # Keep in processing status
                processing_step='extracting_data',  # Still in extracting_data step
                extracted_data=json.dumps(base_extracted_data, default=str)
            )
            
            logger.info(f"Data extraction step completed successfully for run {run_id}")
            
        except Exception as e:
            logger.error(f"Data extraction step failed for run {run_id}: {e}")
            raise

    def _process_data_transformation_step(self, run_id: int, template_id: int):
        """
        Process data transformation step of the workflow.
        
        Updates processing step to 'transforming_data', reads extracted_data from previous step,
        applies any transformation rules associated with the template, creates audit trail,
        and stores final data in target_data column.
        
        This is the final step in the processing workflow: template_matching -> extracting_data -> transforming_data
        """
        logger.info(f"Starting data transformation step for ETO run {run_id}")
        
        # Update processing step to transforming_data
        self._update_run_status(
            run_id,
            'processing',
            processing_step='transforming_data'
        )
        
        try:
            # Get the current ETO run with extracted data
            session = self.db_service.get_session()
            try:
                eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
                if not eto_run:
                    raise ValueError(f"ETO run not found: {run_id}")
                
                # Parse the extracted data from the previous step
                if not eto_run.extracted_data:
                    raise ValueError(f"No extracted data found for run {run_id} - extraction step may have failed")
                
                try:
                    extracted_data_json = json.loads(eto_run.extracted_data)
                    extracted_fields = extracted_data_json.get('extracted_fields', {})
                except (json.JSONDecodeError, TypeError) as e:
                    raise ValueError(f"Invalid extracted data JSON for run {run_id}: {e}")
                
                logger.info(f"Processing transformation for {len(extracted_fields)} extracted fields")
                
            finally:
                session.close()
            
            # TODO: Check for extraction_rules and extraction_steps tables for transformation instructions
            # For now, this is a placeholder implementation that copies extracted_data to target_data
            # The full transformation system with rules and steps will be implemented later
            
            # Check if there are transformation rules associated with this template
            # This is where we would query extraction_rules and extraction_steps tables
            transformation_rules_exist = False  # Placeholder - will implement rule checking later
            
            if not transformation_rules_exist:
                # No transformation rules - copy extracted_data directly to target_data
                logger.info(f"No transformation rules found for template {template_id} - using extracted data as final target data")
                
                target_data = extracted_fields
                transformation_audit = {
                    'transformation_type': 'direct_copy',
                    'message': 'No transformation rules defined for template - extracted data copied directly to target data',
                    'steps_applied': 0,
                    'input_fields': list(extracted_fields.keys()),
                    'output_fields': list(extracted_fields.keys())
                }
                
            else:
                # TODO: Apply transformation rules and create detailed audit trail
                # This would involve:
                # 1. Query extraction_rules table for rules associated with template_id
                # 2. Query extraction_steps table for step definitions
                # 3. Apply each transformation step in sequence
                # 4. Create audit trail showing input/output for each step with rule IDs
                # 
                # Example transformation_audit structure:
                # {
                #     "transformation_type": "rules_applied",
                #     "steps": [
                #         {
                #             "step_id": 1,
                #             "extraction_rule_id": 2,
                #             "input": {"pu_address_and_date": "123 example st. 08/27/2025"},
                #             "output": {"pu_address": "123 example st", "pu_date": "08/27/2025"}
                #         }
                #     ]
                # }
                
                # Placeholder implementation
                target_data = extracted_fields
                transformation_audit = {
                    'transformation_type': 'rules_applied_placeholder',
                    'message': 'Transformation rules system not yet implemented - using extracted data as target data',
                    'steps_applied': 0
                }
                
                logger.warning("Transformation rules system not yet implemented - copying extracted data to target data")
            
            # Store transformation results and mark as successful
            self._update_run_status(
                run_id,
                'success',  # Final status - processing complete
                processing_step=None,  # Clear processing step on completion
                completed_at=datetime.now(),
                transformation_audit=json.dumps(transformation_audit, default=str),
                target_data=json.dumps(target_data, default=str)
            )
            
            logger.info(f"Data transformation step completed successfully for run {run_id}")
            logger.info(f"Final target data contains {len(target_data)} fields: {list(target_data.keys())}")
            
        except Exception as e:
            logger.error(f"Data transformation step failed for run {run_id}: {e}")
            raise

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
        
        self._update_run_status(
            eto_run.id,
            'needs_template',
            completed_at=datetime.now(),
            extracted_data=None  # No data extracted since no template found
        )
        
        logger.info(f"Run {eto_run.id} marked as needs_template")
    
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
                'failure',  # Updated to use new status value
                processing_step=None,  # Clear processing step on failure
                completed_at=datetime.now(),
                error_type='processing_error',
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Error marking run as failed: {e}")
    
    def process_single_run(self, run_id: int):
        """
        Process a single specific ETO run by ID.
        
        This method processes only the specified run through the complete workflow:
        not_started -> processing (template_matching -> extracting_data -> transforming_data) -> success
        
        Args:
            run_id (int): The ID of the ETO run to process
            
        Returns:
            bool: True if processing started successfully, False otherwise
        """
        try:
            session = self.db_service.get_session()
            try:
                # Get the specific ETO run
                eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
                if not eto_run:
                    logger.error(f"ETO run {run_id} not found for processing")
                    return False
                
                if eto_run.status != 'not_started':
                    logger.warning(f"ETO run {run_id} has status '{eto_run.status}', expected 'not_started'")
                    return False
                
                logger.info(f"Starting processing of single ETO run {run_id}")
                
                # Process this specific run
                self._process_eto_run(eto_run)
                
                logger.info(f"Successfully started processing of ETO run {run_id}")
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error processing single ETO run {run_id}: {e}")
            return False
    
    def reprocess_failed_runs(self):
        """
        Reprocess all failed and needs_template ETO runs.
        
        This method handles runs with status 'needs_template' (no template found) 
        and 'failure' (processing error), resetting them to 'not_started' so they
        go through the complete processing workflow again.
        
        Typically called when new templates are added or processing issues are resolved.
        """
        try:
            session = self.db_service.get_session()
            try:
                # Find all runs that need reprocessing: needs_template and failure
                failed_runs = session.query(EtoRun).filter(
                    EtoRun.status.in_(['needs_template', 'failure'])
                ).all()
                
                if not failed_runs:
                    logger.info("No failed runs found to reprocess")
                    return {"reprocessed": 0, "message": "No failed runs found to reprocess"}
                
                # Count by status for logging
                needs_template_count = len([r for r in failed_runs if r.status == 'needs_template'])
                failure_count = len([r for r in failed_runs if r.status == 'failure'])
                
                # Reset them to not_started so they get picked up by the worker
                reprocessed_count = 0
                for run in failed_runs:
                    self._update_run_status(
                        run.id, 
                        'not_started',  # Reset to initial status for new processing workflow
                        # Clear all previous processing results to start fresh
                        processing_step=None,
                        matched_template_id=None,
                        extracted_data=None,
                        transformation_audit=None,
                        target_data=None,
                        error_type=None,
                        error_message=None,
                        completed_at=None,
                        started_at=None
                    )
                    reprocessed_count += 1
                
                logger.info(f"Marked {reprocessed_count} failed runs for reprocessing:")
                logger.info(f"  - {needs_template_count} needs_template runs")
                logger.info(f"  - {failure_count} failure runs")
                
                return {
                    "reprocessed": reprocessed_count, 
                    "message": f"Marked {reprocessed_count} runs for reprocessing ({needs_template_count} needs_template, {failure_count} failure)",
                    "needs_template_count": needs_template_count,
                    "failure_count": failure_count
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error reprocessing failed runs: {e}")
            return {"reprocessed": 0, "error": str(e)}

    # Keep the old method name for backwards compatibility
    def reprocess_unrecognized_runs(self):
        """Legacy method name - calls reprocess_failed_runs()"""
        logger.warning("reprocess_unrecognized_runs() is deprecated - use reprocess_failed_runs() instead")
        return self.reprocess_failed_runs()

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
    """Trigger reprocessing of failed ETO runs (needs_template and failure status)"""
    if processing_worker is None:
        raise RuntimeError("Processing worker not initialized. Call init_processing_worker() first.")
    return processing_worker.reprocess_failed_runs()

def process_single_run(run_id: int):
    """Process a single specific ETO run by ID"""
    if processing_worker is None:
        raise RuntimeError("Processing worker not initialized. Call init_processing_worker() first.")
    return processing_worker.process_single_run(run_id)