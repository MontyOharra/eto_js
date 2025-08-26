import os
import logging
from flask import Flask, jsonify, request
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
            pending_runs = session.query(EtoRun).filter(EtoRun.status == 'pending').count()
            processing_runs = session.query(EtoRun).filter(EtoRun.status == 'processing').count()
            completed_runs = session.query(EtoRun).filter(EtoRun.status == 'completed').count()
            failed_runs = session.query(EtoRun).filter(EtoRun.status == 'failed').count()
            needs_template_runs = session.query(EtoRun).filter(EtoRun.status == 'needs_template').count()
            
            # Template matching stats
            template_match_runs = session.query(EtoRun).filter(EtoRun.run_type == 'template_match').count()
            data_extract_runs = session.query(EtoRun).filter(EtoRun.run_type == 'data_extract').count()
            
            return jsonify({
                "total_runs": total_runs,
                "by_status": {
                    "pending": pending_runs,
                    "processing": processing_runs,
                    "completed": completed_runs,
                    "failed": failed_runs,
                    "needs_template": needs_template_runs
                },
                "by_type": {
                    "template_match": template_match_runs,
                    "data_extract": data_extract_runs
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
                    "run_type": run.run_type,
                    "status": run.status,
                    "template_id": run.template_id,
                    "is_duplicate_pdf": run.is_duplicate_pdf,
                    "duplicate_handling_result": run.duplicate_handling_result,
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
