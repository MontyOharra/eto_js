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
    
    # Initialize Outlook service with database, storage, and PDF extractor
    outlook_service.set_database_service(get_db_service())
    outlook_service.set_pdf_storage(get_pdf_storage())
    outlook_service.set_pdf_extractor(get_pdf_extractor())
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
            
            # Updated to use new status values from the workflow
            not_started_runs = session.query(EtoRun).filter(EtoRun.status == 'not_started').count()
            processing_runs = session.query(EtoRun).filter(EtoRun.status == 'processing').count()
            success_runs = session.query(EtoRun).filter(EtoRun.status == 'success').count()
            failure_runs = session.query(EtoRun).filter(EtoRun.status == 'failure').count()
            needs_template_runs = session.query(EtoRun).filter(EtoRun.status == 'needs_template').count()
            skipped_runs = session.query(EtoRun).filter(EtoRun.status == 'skipped').count()
            
        finally:
            session.close()
        
        # Get storage statistics
        storage_stats = pdf_storage.get_storage_stats()
        
        return jsonify({
            "database": {
                "emails": email_count,
                "pdf_files": pdf_count,
                "eto_runs": {
                    "not_started": not_started_runs,
                    "processing": processing_runs,
                    "success": success_runs,
                    "failure": failure_runs,
                    "needs_template": needs_template_runs,
                    "skipped": skipped_runs,
                    "total": not_started_runs + processing_runs + success_runs + failure_runs + needs_template_runs + skipped_runs
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
                extraction_fields=json.dumps(data.get('extraction_fields', [])),  # Store spatial extraction field definitions
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


@app.get("/api/templates/<int:template_id>/view")
def get_template_view_data(template_id):
    """Get detailed template data for viewing, including PDF and object information"""
    logger.info(f"Loading template view data for template {template_id}")
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfTemplate, PdfFile, EtoRun
            import json
            
            # Get the template
            logger.info(f"Querying for template {template_id}")
            template = session.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()
            if not template:
                logger.error(f"Template {template_id} not found")
                return jsonify({"error": f"Template {template_id} not found"}), 404
            
            logger.info(f"Found template: {template.name}")
            
            # Get a sample PDF that this template was created from
            # Look for the first ETO run that used this template successfully
            logger.info(f"Looking for ETO runs that used template {template_id}")
            sample_run = session.query(EtoRun).filter(
                EtoRun.matched_template_id == template_id,
                EtoRun.status == 'success'
            ).first()
            
            # If no successful run found, look for any run that matched this template
            if not sample_run:
                logger.info(f"No successful runs found, looking for any run with template {template_id}")
                sample_run = session.query(EtoRun).filter(
                    EtoRun.matched_template_id == template_id
                ).first()
            
            if not sample_run:
                logger.error(f"No sample PDF found for template {template_id}")
                return jsonify({"error": "No sample PDF found for this template"}), 404
            
            logger.info(f"Found sample run {sample_run.id} with PDF file {sample_run.pdf_file_id}")
            
            # Get the PDF file
            pdf_file = session.query(PdfFile).filter(PdfFile.id == sample_run.pdf_file_id).first()
            if not pdf_file:
                logger.error(f"PDF file {sample_run.pdf_file_id} not found for sample run")
                return jsonify({"error": "Sample PDF file not found"}), 404
            
            logger.info(f"Found PDF file: {pdf_file.original_filename}")
            
            # Parse template data
            logger.info(f"Parsing template data")
            try:
                signature_objects = json.loads(template.signature_objects) if template.signature_objects else []
                logger.info(f"Parsed {len(signature_objects)} signature objects")
            except Exception as e:
                logger.error(f"Error parsing signature_objects: {e}")
                signature_objects = []
                
            try:
                extraction_fields = json.loads(template.extraction_fields) if template.extraction_fields else []
                logger.info(f"Parsed {len(extraction_fields)} extraction fields")
            except Exception as e:
                logger.error(f"Error parsing extraction_fields: {e}")
                extraction_fields = []
                
            try:
                pdf_objects = json.loads(pdf_file.objects_json) if pdf_file.objects_json else []
                logger.info(f"Parsed {len(pdf_objects)} PDF objects")
            except Exception as e:
                logger.error(f"Error parsing PDF objects: {e}")
                pdf_objects = []
            
            # Build response
            logger.info(f"Building response data")
            try:
                template_data = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "status": template.status,
                    "is_complete": template.is_complete,
                    "coverage_threshold": template.coverage_threshold,
                    "usage_count": getattr(template, 'usage_count', 0),
                    "last_used_at": template.last_used_at.isoformat() if getattr(template, 'last_used_at', None) else None,
                    "success_rate": getattr(template, 'success_rate', None),
                    "version": getattr(template, 'version', 1),
                    "created_by": getattr(template, 'created_by', None),
                    "created_at": template.created_at.isoformat() if getattr(template, 'created_at', None) else None,
                    "updated_at": template.updated_at.isoformat() if getattr(template, 'updated_at', None) else None,
                    "extraction_rules_count": len(extraction_fields),
                    "signature_object_count": len(signature_objects),
                    
                    # PDF data
                    "sample_pdf_id": pdf_file.id,
                    "sample_pdf_filename": pdf_file.original_filename,
                    "sample_pdf_page_count": getattr(pdf_file, 'page_count', 1),
                    "pdf_objects": pdf_objects,
                    "signature_objects": signature_objects,
                    "extraction_fields": extraction_fields
                }
                logger.info(f"Template data built successfully")
                
            except Exception as e:
                logger.error(f"Error building template data: {e}")
                logger.error(f"Template fields available: {dir(template)}")
                return jsonify({"error": f"Error building template data: {str(e)}"}), 500
            
            logger.info(f"Retrieved template view data for template {template_id}")
            return jsonify({
                "success": True,
                "result": template_data
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting template view data for {template_id}: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/test/extract-fields")
def test_field_extraction():
    """Test field extraction from a specific PDF using a specific template"""
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
            from .database import PdfFile, PdfTemplate
            
            # Get PDF file
            pdf_file = session.query(PdfFile).filter(PdfFile.id == pdf_id).first()
            if not pdf_file:
                return jsonify({"error": f"PDF file {pdf_id} not found"}), 404
            
            # Get template
            template = session.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()
            if not template:
                return jsonify({"error": f"Template {template_id} not found"}), 404
            
            # Get PDF objects
            if not pdf_file.objects_json:
                return jsonify({"error": "PDF file has no extracted objects"}), 400
            
            pdf_objects = json.loads(pdf_file.objects_json)
            
            # Perform field extraction
            template_matcher = get_template_matcher()
            extracted_fields = template_matcher.extract_fields_from_pdf(pdf_objects, template_id)
            
            return jsonify({
                "pdf_id": pdf_id,
                "template_id": template_id,
                "template_name": template.name,
                "pdf_filename": pdf_file.original_filename,
                "total_pdf_objects": len(pdf_objects),
                "extracted_fields": extracted_fields,
                "extraction_field_count": len(extracted_fields)
            })
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error in field extraction test: {e}")
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
            
            # Get PDF objects from pdf_files.objects_json (new workflow)
            pdf_objects = []
            if pdf_file.objects_json:
                try:
                    pdf_objects = json.loads(pdf_file.objects_json)
                    logger.info(f"Loaded {len(pdf_objects)} PDF objects from pdf_files.objects_json")
                except Exception as e:
                    logger.error(f"Error parsing pdf_file.objects_json: {e}")
            
            if not pdf_objects:
                return jsonify({
                    "error": "No PDF objects found for this PDF - objects may not have been extracted yet",
                    "pdf_file": pdf_file.original_filename,
                    "has_objects_json": bool(pdf_file.objects_json),
                    "objects_json_length": len(pdf_file.objects_json) if pdf_file.objects_json else 0
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
                        "objects_source": "pdf_files.objects_json"
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
            
            # Get processing statistics using new status values
            total_runs = session.query(EtoRun).count()
            not_started_runs = session.query(EtoRun).filter(EtoRun.status == 'not_started').count()
            processing_runs = session.query(EtoRun).filter(EtoRun.status == 'processing').count()
            success_runs = session.query(EtoRun).filter(EtoRun.status == 'success').count()
            failure_runs = session.query(EtoRun).filter(EtoRun.status == 'failure').count()
            needs_template_runs = session.query(EtoRun).filter(EtoRun.status == 'needs_template').count()
            skipped_runs = session.query(EtoRun).filter(EtoRun.status == 'skipped').count()
            
            # Get processing step breakdown for runs currently in processing
            processing_steps = {}
            if processing_runs > 0:
                template_matching_runs = session.query(EtoRun).filter(
                    EtoRun.status == 'processing',
                    EtoRun.processing_step == 'template_matching'
                ).count()
                extracting_data_runs = session.query(EtoRun).filter(
                    EtoRun.status == 'processing',
                    EtoRun.processing_step == 'extracting_data'
                ).count()
                transforming_data_runs = session.query(EtoRun).filter(
                    EtoRun.status == 'processing',
                    EtoRun.processing_step == 'transforming_data'
                ).count()
                
                processing_steps = {
                    "template_matching": template_matching_runs,
                    "extracting_data": extracting_data_runs,
                    "transforming_data": transforming_data_runs
                }
            
            return jsonify({
                "total_runs": total_runs,
                "by_status": {
                    "not_started": not_started_runs,
                    "processing": processing_runs,
                    "success": success_runs,
                    "failure": failure_runs,
                    "needs_template": needs_template_runs,
                    "skipped": skipped_runs
                },
                "processing_steps": processing_steps,
                "success_rate": (success_runs / total_runs * 100) if total_runs > 0 else 0,
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
                    "processing_step": run.processing_step,
                    "matched_template_id": run.matched_template_id,
                    "has_extracted_data": bool(run.extracted_data),
                    "has_transformation_audit": bool(run.transformation_audit),
                    "has_target_data": bool(run.target_data),
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
            
            # Parse extracted_data, transformation_audit, and target_data from new workflow
            extracted_data = None
            transformation_audit = None
            target_data = None
            pdf_objects = []
            
            if eto_run.extracted_data:
                try:
                    extracted_data = json.loads(eto_run.extracted_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing extracted_data for run {run_id}: {e}")
            
            if eto_run.transformation_audit:
                try:
                    transformation_audit = json.loads(eto_run.transformation_audit)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing transformation_audit for run {run_id}: {e}")
            
            if eto_run.target_data:
                try:
                    target_data = json.loads(eto_run.target_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing target_data for run {run_id}: {e}")
            
            # Get PDF objects from pdf_files.objects_json (new workflow)
            if pdf_file.objects_json:
                try:
                    pdf_objects = json.loads(pdf_file.objects_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing pdf objects for run {run_id}: {e}")
            
            return jsonify({
                "eto_run_id": run_id,
                "pdf_id": pdf_file.id,
                "filename": pdf_file.original_filename,
                "page_count": pdf_file.page_count or 1,
                "object_count": len(pdf_objects),
                "file_size": pdf_file.file_size,
                "pdf_objects": pdf_objects,  # PDF objects from pdf_files table
                "status": eto_run.status,
                "processing_step": eto_run.processing_step,
                "matched_template_id": eto_run.matched_template_id,
                "extracted_data": extracted_data,  # Structured extracted field data
                "transformation_audit": transformation_audit,  # Transformation audit trail
                "target_data": target_data,  # Final transformed data
                "email": {
                    "subject": eto_run.email.subject,
                    "sender_email": eto_run.email.sender_email,
                    "received_date": eto_run.email.received_date.isoformat() if eto_run.email.received_date else None
                },
                "timestamps": {
                    "created_at": eto_run.created_at.isoformat() if eto_run.created_at else None,
                    "started_at": eto_run.started_at.isoformat() if eto_run.started_at else None,
                    "completed_at": eto_run.completed_at.isoformat() if eto_run.completed_at else None
                },
                "error_info": {
                    "error_type": eto_run.error_type,
                    "error_message": eto_run.error_message
                }
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting PDF data for ETO run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/eto-runs/<int:run_id>/processing-details")
def get_eto_run_processing_details(run_id):
    """Get detailed processing information for an ETO run"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import EtoRun, PdfTemplate
            
            eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
            if not eto_run:
                return jsonify({"error": "ETO run not found"}), 404
            
            # Get template info if matched
            template_info = None
            if eto_run.matched_template_id:
                template = session.query(PdfTemplate).filter(PdfTemplate.id == eto_run.matched_template_id).first()
                if template:
                    template_info = {
                        "id": template.id,
                        "name": template.name,
                        "customer_name": template.customer_name,
                        "description": template.description
                    }
            
            # Parse extracted data details
            extracted_fields = {}
            extraction_status = None
            if eto_run.extracted_data:
                try:
                    extracted_data = json.loads(eto_run.extracted_data)
                    extracted_fields = extracted_data.get('extracted_fields', {})
                    extraction_status = extracted_data.get('extraction_status', 'unknown')
                except json.JSONDecodeError:
                    pass
            
            # Parse transformation details
            transformation_details = {}
            if eto_run.transformation_audit:
                try:
                    transformation_details = json.loads(eto_run.transformation_audit)
                except json.JSONDecodeError:
                    pass
            
            # Parse target data
            target_data = {}
            if eto_run.target_data:
                try:
                    target_data = json.loads(eto_run.target_data)
                except json.JSONDecodeError:
                    pass
            
            return jsonify({
                "run_id": run_id,
                "status": eto_run.status,
                "processing_step": eto_run.processing_step,
                "template_info": template_info,
                "extraction_info": {
                    "status": extraction_status,
                    "fields_extracted": len(extracted_fields),
                    "field_names": list(extracted_fields.keys()),
                    "extracted_fields": extracted_fields
                },
                "transformation_info": transformation_details,
                "target_data": target_data,
                "processing_times": {
                    "started_at": eto_run.started_at.isoformat() if eto_run.started_at else None,
                    "completed_at": eto_run.completed_at.isoformat() if eto_run.completed_at else None,
                    "duration_seconds": (
                        (eto_run.completed_at - eto_run.started_at).total_seconds() 
                        if eto_run.started_at and eto_run.completed_at 
                        else None
                    )
                }
            })
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error getting processing details for run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500



@app.post("/api/eto-runs/<int:run_id>/skip")
def skip_eto_run(run_id):
    """Skip an ETO run (mark as skipped status)"""
    try:
        from .database import EtoRun
        from datetime import datetime
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            # Get the ETO run
            eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
            
            if not eto_run:
                return jsonify({"error": "ETO run not found"}), 404
            
            # Only allow skipping of runs that aren't already processed successfully
            if eto_run.status == 'success':
                return jsonify({
                    "error": f"Cannot skip run with status '{eto_run.status}'. Successfully processed runs cannot be skipped."
                }), 400
            
            old_status = eto_run.status
            
            # Set run to skipped status
            eto_run.status = 'skipped'
            eto_run.processing_step = None  # Clear processing step
            eto_run.error_type = None  # Clear any error info
            eto_run.error_message = None
            eto_run.error_details = None
            eto_run.updated_at = datetime.utcnow()
            
            session.commit()
            
            logger.info(f"ETO run {run_id} marked as skipped (was '{old_status}')")
            
            return jsonify({
                "success": True,
                "message": f"ETO run {run_id} marked as skipped",
                "run_id": run_id,
                "old_status": old_status,
                "new_status": "skipped"
            })
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error skipping ETO run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.delete("/api/eto-runs/<int:run_id>")
def delete_eto_run(run_id):
    """Permanently delete an ETO run and associated data"""
    try:
        from .database import EtoRun
        
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            # Get the ETO run
            eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
            if not eto_run:
                return jsonify({"error": f"ETO run {run_id} not found"}), 404
            
            # Only allow deletion of skipped runs for safety
            if eto_run.status != 'skipped':
                return jsonify({
                    "error": f"Cannot delete run with status '{eto_run.status}'. Only skipped runs can be permanently deleted."
                }), 400
            
            # Delete the ETO run (cascading should handle related data)
            session.delete(eto_run)
            session.commit()
            
            logger.info(f"ETO run {run_id} permanently deleted")
            
            return jsonify({
                "message": f"ETO run {run_id} permanently deleted"
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error deleting ETO run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/eto-runs/<int:run_id>/reprocess")
def reprocess_eto_run(run_id):
    """Reprocess a skipped ETO run (reset to not_started status)"""
    logger.info(f"Reprocess request received for ETO run {run_id}")
    
    try:
        from .database import EtoRun
        logger.info(f"Successfully imported EtoRun for run {run_id}")
        
        db_service = get_db_service()
        session = db_service.get_session()
        logger.info(f"Got database session for run {run_id}")
        
        try:
            # Get the ETO run
            logger.info(f"Querying for ETO run {run_id}")
            eto_run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
            if not eto_run:
                logger.error(f"ETO run {run_id} not found in database")
                return jsonify({"error": f"ETO run {run_id} not found"}), 404
            
            old_status = eto_run.status
            logger.info(f"Found ETO run {run_id} with status: {old_status}")
            
            # Only allow reprocessing of skipped runs
            if eto_run.status != 'skipped':
                logger.error(f"Cannot reprocess run {run_id} with status '{eto_run.status}'")
                return jsonify({
                    "error": f"Cannot reprocess run with status '{eto_run.status}'. Only skipped runs can be reprocessed."
                }), 400
            
            # Reset run to not_started status and clear any previous processing data
            logger.info(f"Resetting ETO run {run_id} data fields")
            eto_run.status = 'not_started'
            eto_run.processing_step = None
            eto_run.matched_template_id = None
            eto_run.extracted_data = None
            eto_run.transformation_audit = None
            eto_run.target_data = None
            eto_run.error_type = None
            eto_run.error_message = None
            eto_run.started_at = None
            eto_run.completed_at = None
            
            logger.info(f"Committing changes for ETO run {run_id}")
            session.commit()
            
            logger.info(f"ETO run {run_id} reset for reprocessing (was '{old_status}')")
            
            # Process this specific run
            try:
                logger.info(f"Attempting to process specific ETO run {run_id}")
                from .processing_worker import process_single_run
                success = process_single_run(run_id)
                if success:
                    logger.info(f"Successfully started processing of ETO run {run_id}")
                else:
                    logger.warning(f"Failed to start processing of ETO run {run_id}")
            except Exception as e:
                logger.warning(f"Failed to start processing: {e}")
            
            logger.info(f"Returning success response for ETO run {run_id} reprocessing")
            return jsonify({
                "message": f"ETO run {run_id} reset for reprocessing",
                "new_status": "not_started"
            })
            
        finally:
            logger.info(f"Closing database session for ETO run {run_id}")
            session.close()
            
    except Exception as e:
        logger.error(f"Error reprocessing ETO run {run_id}: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/pdf-files/<int:pdf_id>/download")
def download_pdf_file(pdf_id):
    """Download a PDF file by its ID"""
    try:
        db_service = get_db_service()
        session = db_service.get_session()
        
        try:
            from .database import PdfFile
            from flask import send_file
            import os
            from pathlib import Path
            
            # Get the PDF file record
            pdf_file = session.query(PdfFile).filter(PdfFile.id == pdf_id).first()
            if not pdf_file:
                return jsonify({"error": f"PDF file {pdf_id} not found"}), 404
            
            # First try the stored file path as-is
            file_path = pdf_file.file_path
            logger.info(f"PDF download requested for ID {pdf_id}: stored path = {file_path}")
            
            # Always resolve paths to the correct storage location
            # Extract the hash-based path structure from the stored path
            stored_path = Path(file_path)
            
            # Get just the hash-based directory structure (last 3 parts: hash[:2]/hash[2:4]/hash.pdf)
            if len(stored_path.parts) >= 3:
                hash_structure = Path(*stored_path.parts[-3:])  # e.g., "87/d9/87d9dc...pdf"
                
                # Always use the correct storage location: C:\apps\eto\server\storage\pdfs\
                correct_path = Path("C:/apps/eto/server/storage/pdfs") / hash_structure
                file_path = str(correct_path)
                
                if not os.path.exists(file_path):
                    # If hash structure fails, try using the SHA256 hash directly
                    if pdf_file.sha256_hash:
                        hash_val = pdf_file.sha256_hash
                        rebuilt_path = Path("C:/apps/eto/server/storage/pdfs") / hash_val[:2] / hash_val[2:4] / f"{hash_val}.pdf"
                        if rebuilt_path.exists():
                            file_path = str(rebuilt_path)
                            logger.info(f"Rebuilt PDF path using hash: {file_path}")
                        else:
                            return jsonify({"error": f"PDF file not found in storage: {rebuilt_path}"}), 404
                    else:
                        return jsonify({"error": f"PDF file not found in storage: {file_path}"}), 404
            else:
                return jsonify({"error": f"Invalid stored path structure: {file_path}"}), 404
            
            # Serve the file
            return send_file(
                file_path,
                as_attachment=False,  # Display in browser rather than force download
                download_name=pdf_file.original_filename,
                mimetype='application/pdf'
            )
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error downloading PDF file {pdf_id}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
