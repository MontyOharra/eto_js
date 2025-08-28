import os
import logging
import json
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from .outlook_service import outlook_service
from .database import init_database, get_db_service
from .pdf_storage import init_pdf_storage, get_pdf_storage
from .pdf_objects import init_pdf_extractor, get_pdf_extractor
from .template_matching import init_template_matching, get_template_matcher
from .processing_worker import init_processing_worker, start_processing_worker, stop_processing_worker, get_processing_worker

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for frontend integration
CORS(app, origins=["http://localhost:5002", "http://localhost:3000"], 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Initialize database and storage systems
try:
    # Initialize database
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    init_database(database_url)
    logger.info("Database initialized successfully")
    
    # Initialize PDF storage
    storage_path = os.getenv('STORAGE_PATH', './storage')
    init_pdf_storage(storage_path)
    logger.info("PDF storage initialized successfully")
    
    # Initialize PDF object extractor
    init_pdf_extractor()
    logger.info("PDF object extractor initialized successfully")
    
    # Initialize template matching service
    init_template_matching(get_db_service())
    logger.info("Template matching service initialized successfully")
    
    # Initialize processing worker
    init_processing_worker(get_db_service(), get_pdf_extractor(), get_template_matcher())
    
    # Start the background processing worker
    start_processing_worker()
    logger.info("Processing worker started successfully")
    
    # Initialize Outlook service with database and storage
    outlook_service.set_database_service(get_db_service())
    outlook_service.set_pdf_storage(get_pdf_storage())
    logger.info("All services initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    logger.error("Server will start but email processing will be disabled")
    # Don't exit - allow app to start so we can see the error in health check


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }
    )


@app.post("/api/email/start")
def start_email_monitoring():
    """Start email monitoring - uses specific email if provided, otherwise defaults to first account"""
    try:
        # Check if service is already running
        if outlook_service.monitoring:
            logger.warning("Email monitoring start requested but service is already running")
            return jsonify({
                "error": "Email monitoring is already running",
                "current_status": {
                    "email": outlook_service.current_email,
                    "folder": outlook_service.current_folder,
                    "monitoring": outlook_service.monitoring
                }
            }), 409  # HTTP 409 Conflict
        
        data = request.get_json(silent=True)  # silent=True allows empty body
        email_address = data.get('email_address') if data else None
        folder_name = data.get('folder_name', 'Inbox') if data else 'Inbox'  # Default to 'Inbox'
        
        if email_address:
            logger.info(f"Starting email monitoring for: {email_address}, folder: {folder_name}")
            connection_result = outlook_service.connect(email_address, folder_name)
        else:
            logger.info(f"Starting email monitoring with default Outlook account, folder: {folder_name}")
            connection_result = outlook_service.connect_default(folder_name)
        
        # Start monitoring
        monitoring_result = outlook_service.start_monitoring()
        
        return jsonify({
            "connection": connection_result,
            "monitoring": monitoring_result
        })
        
    except Exception as e:
        logger.error(f"Error starting email monitoring: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/email/stop")
def stop_email_monitoring():
    """Stop email monitoring"""
    try:
        # Check if service is already stopped
        if not outlook_service.monitoring and not outlook_service.current_email:
            logger.warning("Email monitoring stop requested but service is already stopped")
            return jsonify({
                "warning": "Email monitoring is already stopped",
                "status": "not_running"
            }), 200  # HTTP 200 OK with warning
        
        logger.info("Stopping email monitoring")
        
        # Stop monitoring
        monitoring_result = outlook_service.stop_monitoring()
        
        # Disconnect from Outlook
        disconnect_result = outlook_service.disconnect()
        
        return jsonify({
            "monitoring": monitoring_result,
            "disconnection": disconnect_result
        })
        
    except Exception as e:
        logger.error(f"Error stopping email monitoring: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/email/status")
def get_email_status():
    """Get current email monitoring status"""
    try:
        status = outlook_service.get_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting email status: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/email/recent")
def get_recent_emails():
    """Get recent emails for testing"""
    try:
        limit = request.args.get('limit', 10, type=int)
        emails = outlook_service.get_recent_emails(limit)
        return jsonify({"emails": emails})
        
    except Exception as e:
        logger.error(f"Error getting recent emails: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/system/stats")
def get_system_stats():
    """Get system statistics"""
    try:
        db_service = get_db_service()
        pdf_storage = get_pdf_storage()
        
        # Get database statistics
        session = db_service.get_session()
        try:
            from .database import Email, PdfFile, EtoRun
            
            email_count = session.query(Email).count()
            pdf_count = session.query(PdfFile).count()
            pending_runs = session.query(EtoRun).filter(EtoRun.status == 'pending').count()
            completed_runs = session.query(EtoRun).filter(EtoRun.status == 'completed').count()
            failed_runs = session.query(EtoRun).filter(EtoRun.status == 'failed').count()
            needs_template_runs = session.query(EtoRun).filter(EtoRun.status == 'needs_template').count()
            
        finally:
            session.close()
        
        # Get storage statistics
        storage_stats = pdf_storage.get_storage_stats()
        
        return jsonify({
            "database": {
                "emails": email_count,
                "pdf_files": pdf_count,
                "eto_runs": {
                    "pending": pending_runs,
                    "completed": completed_runs,
                    "failed": failed_runs,
                    "needs_template": needs_template_runs
                }
            },
            "storage": storage_stats,
            "email_monitoring": {
                "active": outlook_service.monitoring,
                "current_email": outlook_service.current_email,
                "current_folder": outlook_service.current_folder
            },
            "processing_worker": get_processing_worker().get_worker_status() if get_processing_worker() else {"error": "not_initialized"}
        })
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/templates/stats") 
def get_template_stats():
    """Get template matching statistics"""
    try:
        template_matcher = get_template_matcher()
        stats = template_matcher.get_template_statistics()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting template stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/templates")
def get_templates():
    """Get PDF templates with optional filtering"""
    try:
        status_filter = request.args.get('status', None)  # 'active', 'archived', 'draft'
        limit = request.args.get('limit', 50, type=int)
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfTemplate
            
            query = session.query(PdfTemplate)
            
            if status_filter:
                query = query.filter(PdfTemplate.status == status_filter)
            
            # Get only current versions and order by usage
            templates = query.filter(PdfTemplate.is_current_version == True).order_by(
                PdfTemplate.usage_count.desc(), 
                PdfTemplate.updated_at.desc()
            ).limit(limit).all()
            
            templates_data = []
            for template in templates:
                # Calculate success rate from related ETO runs if available
                success_rate = None
                if template.eto_runs:
                    total_runs = len(template.eto_runs)
                    successful_runs = len([run for run in template.eto_runs if run.status == 'success'])
                    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
                
                templates_data.append({
                    "id": template.id,
                    "name": template.name,
                    "customer_name": template.customer_name,
                    "description": template.description,
                    "status": template.status,
                    "is_complete": template.is_complete,
                    "coverage_threshold": template.coverage_threshold,
                    "usage_count": template.usage_count or 0,
                    "last_used_at": template.last_used_at.isoformat() if template.last_used_at else None,
                    "success_rate": success_rate,
                    "version": template.version,
                    "created_by": template.created_by,
                    "created_at": template.created_at.isoformat() if template.created_at else None,
                    "updated_at": template.updated_at.isoformat() if template.updated_at else None,
                    "extraction_rules_count": len(template.extraction_rules) if template.extraction_rules else 0,
                    "signature_object_count": template.signature_object_count or 0
                })
                
            return jsonify({
                "templates": templates_data,
                "total": len(templates_data),
                "status_filter": status_filter
            })
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/templates")
def create_template():
    """Create a new PDF template"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('name'):
            return jsonify({"error": "Template name is required"}), 400
        
        if not data.get('selected_objects') or len(data.get('selected_objects', [])) == 0:
            return jsonify({"error": "At least one object must be selected"}), 400
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfTemplate
            import json
            
            # Create new template
            template = PdfTemplate(
                name=data['name'],
                description=data.get('description'),
                signature_objects=json.dumps(data['selected_objects']),
                signature_object_count=len(data['selected_objects']),
                created_by='system',  # TODO: Add user authentication
                status='active'  # Start as active for immediate template matching
            )
            
            session.add(template)
            session.commit()
            
            logger.info(f"Created template '{data['name']}' with ID {template.id}")
            
            # Trigger reprocessing of unrecognized runs
            try:
                from .processing_worker import trigger_reprocessing
                reprocess_result = trigger_reprocessing()
                logger.info(f"Template creation triggered reprocessing: {reprocess_result}")
                
                return jsonify({
                    "template_id": template.id,
                    "message": f"Template '{data['name']}' created successfully",
                    "reprocessing": reprocess_result
                }), 201
                
            except Exception as reprocess_error:
                logger.error(f"Template created but reprocessing failed: {reprocess_error}")
                return jsonify({
                    "template_id": template.id,
                    "message": f"Template '{data['name']}' created successfully",
                    "reprocessing_error": str(reprocess_error)
                }), 201
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/templates/reprocess")
def reprocess_unrecognized():
    """Manually trigger reprocessing of unrecognized ETO runs"""
    try:
        from .processing_worker import trigger_reprocessing
        
        result = trigger_reprocessing()
        
        return jsonify({
            "success": True,
            "result": result
        }), 200
        
    except Exception as e:
        logger.error(f"Error triggering reprocessing: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/test/template-match")
def test_template_match():
    """Test if a specific PDF matches a specific template - for debugging"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('pdf_id') or not data.get('template_id'):
            return jsonify({"error": "Both pdf_id and template_id are required"}), 400
        
        pdf_id = data.get('pdf_id')
        template_id = data.get('template_id')
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfFile, PdfTemplate, EtoRun
            import json
            
            # Get the PDF file and its objects
            pdf_file = session.query(PdfFile).filter(PdfFile.id == pdf_id).first()
            if not pdf_file:
                return jsonify({"error": f"PDF with ID {pdf_id} not found"}), 404
            
            # Get the template
            template = session.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()
            if not template:
                return jsonify({"error": f"Template with ID {template_id} not found"}), 404
            
            # Get PDF objects - check if they're in the ETO run or PDF file
            eto_run = session.query(EtoRun).filter(EtoRun.pdf_file_id == pdf_id).first()
            pdf_objects = []
            
            if eto_run and eto_run.extracted_data:
                try:
                    extracted_data = json.loads(eto_run.extracted_data)
                    if 'pdf_objects' in extracted_data:
                        pdf_objects = extracted_data['pdf_objects']
                except Exception as e:
                    logger.error(f"Error parsing extracted_data: {e}")
            
            if not pdf_objects:
                return jsonify({
                    "error": "No PDF objects found for this PDF",
                    "pdf_file": pdf_file.original_filename,
                    "eto_run_id": eto_run.id if eto_run else None,
                    "has_extracted_data": bool(eto_run and eto_run.extracted_data)
                }), 400
            
            # Get template objects
            template_objects = []
            if template.signature_objects:
                try:
                    template_objects = json.loads(template.signature_objects)
                except Exception as e:
                    return jsonify({"error": f"Error parsing template signature_objects: {e}"}), 500
            
            if not template_objects:
                return jsonify({
                    "error": "Template has no signature objects",
                    "template_name": template.name,
                    "template_status": template.status
                }), 400
            
            # Run the template matching algorithm (with image exclusion by default)
            template_matcher = get_template_matcher()
            match_result = template_matcher.find_best_template_match(pdf_objects)
            
            # Also do a direct comparison with detailed signature breakdown
            # No filtering by default - images now use geometric signatures
            exclude_types = []  # Can be modified for testing specific exclusions
            filtered_pdf_objects = [obj for obj in pdf_objects if obj.get('type') not in exclude_types] if exclude_types else pdf_objects
            filtered_template_objects = [obj for obj in template_objects if obj.get('type') not in exclude_types] if exclude_types else template_objects
            
            pdf_signatures = template_matcher._objects_to_signatures(filtered_pdf_objects)
            template_signatures = template_matcher._objects_to_signatures(filtered_template_objects)
            direct_match = template_matcher._check_exact_subset_match(pdf_signatures, template_signatures, template)
            
            # Create signature-to-object mapping for detailed analysis
            def create_signature_object_map(objects, signatures):
                signature_map = {}
                for i, (obj, sig) in enumerate(zip(objects, signatures)):
                    signature_map[sig] = {
                        'object_index': i,
                        'object_data': obj,
                        'signature_components': template_matcher._get_signature_components(obj)
                    }
                return signature_map
            
            pdf_sig_map = create_signature_object_map(filtered_pdf_objects, pdf_signatures)
            template_sig_map = create_signature_object_map(filtered_template_objects, template_signatures)
            
            # Enhanced debugging - compare object structures
            sample_pdf_obj = pdf_objects[0] if pdf_objects else {}
            sample_template_obj = template_objects[0] if template_objects else {}
            
            # Check if objects have same structure
            pdf_keys = set(sample_pdf_obj.keys()) if sample_pdf_obj else set()
            template_keys = set(sample_template_obj.keys()) if sample_template_obj else set()
            
            return jsonify({
                "test_results": {
                    "pdf_info": {
                        "id": pdf_id,
                        "filename": pdf_file.original_filename,
                        "object_count": len(pdf_objects),
                        "filtered_object_count": len(filtered_pdf_objects),
                        "excluded_types": exclude_types,
                        "eto_run_id": eto_run.id if eto_run else None
                    },
                    "template_info": {
                        "id": template_id,
                        "name": template.name,
                        "status": template.status,
                        "object_count": len(template_objects),
                        "filtered_object_count": len(filtered_template_objects),
                        "excluded_types": exclude_types
                    },
                    "signature_analysis": {
                        "pdf_signatures_count": len(pdf_signatures),
                        "template_signatures_count": len(template_signatures),
                        "pdf_signatures": pdf_signatures[:10],  # More samples for inspection
                        "template_signatures": template_signatures[:10]
                    },
                    "object_structure_comparison": {
                        "sample_pdf_object": sample_pdf_obj,
                        "sample_template_object": sample_template_obj,
                        "pdf_object_keys": sorted(list(pdf_keys)),
                        "template_object_keys": sorted(list(template_keys)),
                        "keys_only_in_pdf": sorted(list(pdf_keys - template_keys)),
                        "keys_only_in_template": sorted(list(template_keys - pdf_keys)),
                        "common_keys": sorted(list(pdf_keys & template_keys))
                    },
                    "direct_match_test": direct_match,
                    "full_matching_result": match_result,
                    "would_match": (
                        match_result.get("matched", False) and 
                        match_result.get("template_id") == template_id
                    ),
                    "debug_info": {
                        "matching_signatures": list(set(pdf_signatures) & set(template_signatures)),
                        "signature_overlap_count": len(set(pdf_signatures) & set(template_signatures)),
                        "template_missing_signatures": list(set(template_signatures) - set(pdf_signatures)),
                        "pdf_extra_signatures": list(set(pdf_signatures) - set(template_signatures))
                    },
                    "missing_signature_details": [
                        {
                            "signature_hash": missing_sig,
                            "template_object_data": template_sig_map[missing_sig]['object_data'],
                            "signature_components": template_sig_map[missing_sig]['signature_components'],
                            "object_index": template_sig_map[missing_sig]['object_index']
                        }
                        for missing_sig in list(set(template_signatures) - set(pdf_signatures))[:5]  # First 5 missing
                    ],
                    "matching_signature_details": [
                        {
                            "signature_hash": matching_sig,
                            "pdf_object_data": pdf_sig_map[matching_sig]['object_data'],
                            "template_object_data": template_sig_map[matching_sig]['object_data'],
                            "signature_components": template_sig_map[matching_sig]['signature_components']
                        }
                        for matching_sig in list(set(pdf_signatures) & set(template_signatures))[:3]  # First 3 matching
                    ],
                    "pdf_image_objects": [
                        {
                            "object_data": obj,
                            "signature_components": template_matcher._get_signature_components(obj)
                        }
                        for obj in filtered_pdf_objects if obj.get('type') == 'image'
                    ]
                }
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in template match test: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/processing/stats")
def get_processing_stats():
    """Get processing worker statistics"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import EtoRun
            
            # Get processing statistics
            total_runs = session.query(EtoRun).count()
            success_runs = session.query(EtoRun).filter(EtoRun.status == 'success').count()
            failure_runs = session.query(EtoRun).filter(EtoRun.status == 'failure').count()
            unrecognized_runs = session.query(EtoRun).filter(EtoRun.status == 'unrecognized').count()
            unprocessed_runs = session.query(EtoRun).filter(EtoRun.status == 'unprocessed').count()
            error_runs = session.query(EtoRun).filter(EtoRun.status == 'error').count()
            
            return jsonify({
                "total_runs": total_runs,
                "by_status": {
                    "success": success_runs,
                    "failure": failure_runs,
                    "unrecognized": unrecognized_runs,
                    "unprocessed": unprocessed_runs,
                    "error": error_runs
                },
                "worker_status": get_processing_worker().get_worker_status()
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting processing stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/eto-runs")
def get_eto_runs():
    """Get ETO processing runs"""
    try:
        status_filter = request.args.get('status', None)
        limit = request.args.get('limit', 20, type=int)
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import EtoRun, PdfFile, Email
            
            # Now that ETO runs are directly linked to emails, we can join directly
            query = session.query(EtoRun).join(Email).join(PdfFile)
            
            if status_filter:
                query = query.filter(EtoRun.status == status_filter)
            
            eto_runs = query.order_by(EtoRun.created_at.desc()).limit(limit).all()
            
            runs_data = []
            for run in eto_runs:
                runs_data.append({
                    "id": run.id,
                    "email_id": run.email_id,
                    "pdf_file_id": run.pdf_file_id,
                    "status": run.status,
                    "matched_template_id": run.matched_template_id,
                    "error_type": run.error_type,
                    "error_message": run.error_message,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "pdf_file": {
                        "original_filename": run.pdf_file.original_filename,
                        "sha256_hash": run.pdf_file.sha256_hash[:8] + "...",
                        "file_size": run.pdf_file.file_size
                    },
                    "email": {
                        "subject": run.email.subject,
                        "sender_email": run.email.sender_email,
                        "received_date": run.email.received_date.isoformat() if run.email.received_date else None
                    }
                })
                
            return jsonify({
                "eto_runs": runs_data,
                "total": len(runs_data),
                "status_filter": status_filter
            })
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error getting ETO runs: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/email/cursor")
def get_email_cursor():
    """Get email cursor information for current monitoring session"""
    try:
        if not outlook_service.current_email or not outlook_service.current_folder:
            return jsonify({
                "error": "No active email monitoring session"
            }), 400
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import EmailCursor
            
            cursor = session.query(EmailCursor).filter(
                EmailCursor.email_address == outlook_service.current_email,
                EmailCursor.folder_name == outlook_service.current_folder
            ).first()
            
            if cursor:
                return jsonify({
                    "email_address": cursor.email_address,
                    "folder_name": cursor.folder_name,
                    "last_processed_message_id": cursor.last_processed_message_id,
                    "last_processed_received_date": cursor.last_processed_received_date.isoformat() if cursor.last_processed_received_date else None,
                    "last_check_time": cursor.last_check_time.isoformat() if cursor.last_check_time else None,
                    "total_emails_processed": cursor.total_emails_processed,
                    "total_pdfs_found": cursor.total_pdfs_found,
                    "created_at": cursor.created_at.isoformat() if cursor.created_at else None,
                    "updated_at": cursor.updated_at.isoformat() if cursor.updated_at else None
                })
            else:
                return jsonify({
                    "error": "No cursor found for current session"
                }), 404
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error getting email cursor: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/emails")
def get_emails():
    """Get recent email records"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import Email, PdfFile
            
            emails = session.query(Email).order_by(Email.received_date.desc()).limit(limit).all()
            
            emails_data = []
            for email in emails:
                emails_data.append({
                    "id": email.id,
                    "subject": email.subject,
                    "sender_email": email.sender_email,
                    "received_date": email.received_date.isoformat() if email.received_date else None,
                    "folder_name": email.folder_name,
                    "has_pdf_attachments": email.has_pdf_attachments,
                    "attachment_count": email.attachment_count,
                    "pdf_files_count": len(email.pdf_files)
                })
                
            return jsonify({
                "emails": emails_data,
                "total": len(emails_data)
            })
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error getting emails: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/pdf/<int:pdf_id>/debug")
def debug_pdf_paths(pdf_id):
    """Debug PDF file paths"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfFile
            
            pdf_file = session.query(PdfFile).filter(PdfFile.id == pdf_id).first()
            if not pdf_file:
                return jsonify({"error": "PDF file not found"}), 404
            
            # Get current working directory and stored path
            cwd = os.getcwd()
            stored_path = pdf_file.file_path
            normalized_path = os.path.normpath(stored_path)
            
            # If we're running from src directory, go up one level to server root
            server_root = cwd
            if cwd.endswith('src'):
                server_root = os.path.dirname(cwd)
            
            # Build possible paths
            possible_paths = [
                os.path.join(cwd, stored_path),  # From current directory
                os.path.join(server_root, stored_path),  # From server root
            ]
            
            path_info = []
            for path in possible_paths:
                path_info.append({
                    'path': path,
                    'exists': os.path.exists(path),
                    'normalized': os.path.normpath(path)
                })
            
            return jsonify({
                'pdf_id': pdf_id,
                'current_working_directory': cwd,
                'stored_path': stored_path,
                'filename': pdf_file.original_filename,
                'possible_paths': path_info
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error debugging PDF file {pdf_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/pdf/<int:pdf_id>")
def get_pdf_file(pdf_id):
    """Serve PDF file by ID"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfFile
            
            pdf_file = session.query(PdfFile).filter(PdfFile.id == pdf_id).first()
            if not pdf_file:
                return jsonify({"error": "PDF file not found"}), 404
            
            # Try multiple path approaches based on current working directory
            cwd = os.getcwd()
            
            # If we're running from src directory, go up one level to server root
            server_root = cwd
            if cwd.endswith('src'):
                server_root = os.path.dirname(cwd)
            
            possible_paths = [
                os.path.join(cwd, pdf_file.file_path),  # From current directory
                os.path.join(server_root, pdf_file.file_path),  # From server root
            ]
            
            file_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    logger.info(f"Found PDF at: {file_path}")
                    break
            
            if not file_path:
                logger.error(f"PDF file not found. Tried paths: {possible_paths}")
                return jsonify({"error": "PDF file not found on disk", "tried_paths": possible_paths}), 404
            
            return send_file(
                file_path,
                as_attachment=False,
                download_name=pdf_file.original_filename,
                mimetype='application/pdf'
            )
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error serving PDF file {pdf_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/pdf/<int:pdf_id>/objects")
def get_pdf_objects(pdf_id):
    """Get extracted PDF objects by PDF ID"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfFile
            
            pdf_file = session.query(PdfFile).filter(PdfFile.id == pdf_id).first()
            if not pdf_file:
                return jsonify({"error": "PDF file not found"}), 404
            
            # Parse the objects JSON
            objects = []
            if pdf_file.objects_json:
                try:
                    objects = json.loads(pdf_file.objects_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing objects JSON for PDF {pdf_id}: {e}")
                    return jsonify({"error": "Invalid objects data"}), 500
            
            return jsonify({
                "pdf_id": pdf_id,
                "filename": pdf_file.original_filename,
                "page_count": pdf_file.page_count or 1,
                "object_count": pdf_file.object_count or 0,
                "objects": objects
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting PDF objects for {pdf_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/eto-run/<int:run_id>/pdf-data")
def get_eto_run_pdf_data(run_id):
    """Get complete PDF data (file + objects) for an ETO run"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import EtoRun, PdfFile, Email
            
            eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
            if not eto_run:
                return jsonify({"error": "ETO run not found"}), 404
            
            pdf_file = eto_run.pdf_file
            if not pdf_file:
                return jsonify({"error": "PDF file not found for ETO run"}), 404
            
            # Pass raw extracted_data to frontend for parsing
            raw_extracted_data = eto_run.extracted_data
            logger.info(f"ETO run {run_id} extracted_data: {raw_extracted_data is not None}")
            if raw_extracted_data:
                logger.info(f"ETO run {run_id} extracted_data length: {len(raw_extracted_data)}")
            else:
                logger.info(f"ETO run {run_id} has no extracted_data")
            
            return jsonify({
                "eto_run_id": run_id,
                "pdf_id": pdf_file.id,
                "filename": pdf_file.original_filename,
                "page_count": pdf_file.page_count or 1,
                "object_count": 0,  # Will be calculated on frontend
                "file_size": pdf_file.file_size,
                "raw_extracted_data": raw_extracted_data,
                "email": {
                    "subject": eto_run.email.subject,
                    "sender_email": eto_run.email.sender_email,
                    "received_date": eto_run.email.received_date.isoformat() if eto_run.email.received_date else None
                },
                "status": eto_run.status,
                "error_message": eto_run.error_message
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting PDF data for ETO run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
