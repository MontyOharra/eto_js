"""
PDF Viewing API Blueprint
REST endpoints for PDF retrieval and client viewing
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_cors import cross_origin, CORS
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create blueprint
pdf_viewing_bp = Blueprint('pdf_viewing', __name__, url_prefix='/api/pdfs')

# Configure CORS for this blueprint
CORS(pdf_viewing_bp, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
        "supports_credentials": False
    }
})

# Add explicit OPTIONS handler for all routes
@pdf_viewing_bp.route('/<path:path>', methods=['OPTIONS'])
@cross_origin()
def handle_options(path):
    """Handle preflight OPTIONS requests for all routes"""
    return '', 200


# Service helper functions
def get_pdf_storage_service():
    """Get PDF storage service from app config"""
    from flask import current_app
    return current_app.config.get('PDF_STORAGE_SERVICE')

def get_pdf_repository():
    """Get PDF repository from app config"""
    from flask import current_app
    return current_app.config.get('PDF_REPOSITORY')


@pdf_viewing_bp.route('/<int:pdf_id>', methods=['GET'])
@cross_origin()
def get_pdf_metadata(pdf_id: int):
    """
    Get PDF metadata by ID
    
    Returns:
        JSON response with PDF metadata
    """
    try:
        pdf_repo = get_pdf_repository()
        if not pdf_repo:
            return jsonify({"error": "PDF repository not available"}), 500
        
        pdf_file = pdf_repo.get_by_id(pdf_id)
        if not pdf_file:
            return jsonify({"error": "PDF not found"}), 404
        
        # Convert domain object to JSON-serializable dict
        pdf_data = {
            "id": pdf_file.id,
            "email_id": pdf_file.email_id,
            "filename": pdf_file.filename,
            "original_filename": pdf_file.original_filename,
            "file_size": pdf_file.file_size,
            "sha256_hash": pdf_file.sha256_hash,
            "mime_type": pdf_file.mime_type,
            "page_count": pdf_file.page_count,
            "object_count": pdf_file.object_count,
            "created_at": pdf_file.created_at.isoformat() if pdf_file.created_at else None,
            "updated_at": pdf_file.updated_at.isoformat() if pdf_file.updated_at else None
        }
        
        logger.info(f"Retrieved PDF metadata for {pdf_id}: {pdf_file.filename}")
        return jsonify(pdf_data), 200
        
    except Exception as e:
        logger.error(f"Error getting PDF metadata {pdf_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@pdf_viewing_bp.route('/<int:pdf_id>/content', methods=['GET'])
@cross_origin()
def download_pdf_content(pdf_id: int):
    """
    Download PDF file content for client viewing
    
    Returns:
        PDF file content with proper headers
    """
    try:
        pdf_repo = get_pdf_repository()
        pdf_storage = get_pdf_storage_service()
        
        if not pdf_repo or not pdf_storage:
            return jsonify({"error": "PDF services not available"}), 500
        
        # Get PDF metadata
        pdf_file = pdf_repo.get_by_id(pdf_id)
        if not pdf_file:
            return jsonify({"error": "PDF not found"}), 404
        
        # Retrieve PDF content from storage
        try:
            pdf_content = pdf_storage.retrieve_pdf_content(pdf_file.file_path)
        except FileNotFoundError:
            logger.error(f"PDF file not found on disk: {pdf_file.file_path}")
            return jsonify({"error": "PDF file not found on disk"}), 404
        
        # Create response with proper headers for PDF viewing
        response = current_app.response_class(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{pdf_file.original_filename}"',
                'Content-Length': str(len(pdf_content)),
                'Cache-Control': 'public, max-age=3600'  # Cache for 1 hour
            }
        )
        
        logger.info(f"Served PDF content for {pdf_id}: {pdf_file.filename} ({len(pdf_content)} bytes)")
        return response
        
    except Exception as e:
        logger.error(f"Error serving PDF content {pdf_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@pdf_viewing_bp.route('/<int:pdf_id>/info', methods=['GET'])
@cross_origin()
def get_pdf_info(pdf_id: int):
    """
    Get detailed PDF information including processing status
    
    Returns:
        JSON response with detailed PDF information
    """
    try:
        pdf_repo = get_pdf_repository()
        pdf_storage = get_pdf_storage_service()
        
        if not pdf_repo:
            return jsonify({"error": "PDF repository not available"}), 500
        
        pdf_file = pdf_repo.get_by_id(pdf_id)
        if not pdf_file:
            return jsonify({"error": "PDF not found"}), 404
        
        # Basic PDF information
        pdf_info = {
            "id": pdf_file.id,
            "email_id": pdf_file.email_id,
            "filename": pdf_file.filename,
            "original_filename": pdf_file.original_filename,
            "file_size": pdf_file.file_size,
            "sha256_hash": pdf_file.sha256_hash,
            "mime_type": pdf_file.mime_type,
            "page_count": pdf_file.page_count,
            "object_count": pdf_file.object_count,
            "created_at": pdf_file.created_at.isoformat() if pdf_file.created_at else None,
            "updated_at": pdf_file.updated_at.isoformat() if pdf_file.updated_at else None,
            "processing_status": {
                "has_extracted_objects": pdf_file.objects_json is not None and pdf_file.objects_json != '',
                "objects_json_size": len(pdf_file.objects_json) if pdf_file.objects_json else 0
            }
        }
        
        # Check file existence on disk
        if pdf_storage and pdf_file.file_path:
            try:
                import os
                pdf_info["file_status"] = {
                    "exists_on_disk": os.path.exists(pdf_file.file_path),
                    "file_path": pdf_file.file_path
                }
            except Exception as e:
                logger.warning(f"Error checking file status for PDF {pdf_id}: {e}")
                pdf_info["file_status"] = {"exists_on_disk": None, "file_path": pdf_file.file_path}
        
        logger.info(f"Retrieved detailed PDF info for {pdf_id}: {pdf_file.filename}")
        return jsonify(pdf_info), 200
        
    except Exception as e:
        logger.error(f"Error getting PDF info {pdf_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Email-related PDF endpoints
@pdf_viewing_bp.route('/by-email/<int:email_id>', methods=['GET'])
@cross_origin()
def get_email_pdfs(email_id: int):
    """
    Get list of all PDFs attached to a specific email
    
    Args:
        email_id: Email ID to get PDFs for
        
    Returns:
        JSON response with list of PDF metadata
    """
    try:
        pdf_repo = get_pdf_repository()
        if not pdf_repo:
            return jsonify({"error": "PDF repository not available"}), 500
        
        pdf_files = pdf_repo.get_by_email_id(email_id)
        
        # Convert domain objects to JSON-serializable dicts
        pdf_list = []
        for pdf_file in pdf_files:
            pdf_data = {
                "id": pdf_file.id,
                "email_id": pdf_file.email_id,
                "filename": pdf_file.filename,
                "original_filename": pdf_file.original_filename,
                "file_size": pdf_file.file_size,
                "sha256_hash": pdf_file.sha256_hash,
                "mime_type": pdf_file.mime_type,
                "page_count": pdf_file.page_count,
                "object_count": pdf_file.object_count,
                "created_at": pdf_file.created_at.isoformat() if pdf_file.created_at else None,
                "updated_at": pdf_file.updated_at.isoformat() if pdf_file.updated_at else None
            }
            pdf_list.append(pdf_data)
        
        logger.info(f"Retrieved {len(pdf_list)} PDFs for email {email_id}")
        return jsonify({
            "email_id": email_id,
            "pdf_count": len(pdf_list),
            "pdfs": pdf_list
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting PDFs for email {email_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@pdf_viewing_bp.route('/', methods=['GET'])
@cross_origin()
def list_pdfs():
    """
    List PDFs with pagination and filtering
    
    Query Parameters:
        page: Page number (default: 1)
        limit: Items per page (default: 50, max: 100)
        email_id: Filter by email ID
        
    Returns:
        JSON response with paginated PDF list
    """
    try:
        pdf_repo = get_pdf_repository()
        if not pdf_repo:
            return jsonify({"error": "PDF repository not available"}), 500
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 50, type=int), 100)  # Max 100 items per page
        email_id = request.args.get('email_id', type=int)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1:
            limit = 50
        
        # Get PDFs based on filters
        if email_id:
            # Filter by specific email
            pdf_files = pdf_repo.get_by_email_id(email_id)
            # Simple in-memory pagination for email-specific results
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_files = pdf_files[start_idx:end_idx]
            total_count = len(pdf_files)
        else:
            # For now, we'll use a simple approach since we don't have pagination in repository
            # In a production system, we'd implement proper database pagination
            all_files = pdf_repo.get_all()  # This would need to be implemented
            total_count = len(all_files) if all_files else 0
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_files = all_files[start_idx:end_idx] if all_files else []
        
        # Convert domain objects to JSON-serializable dicts
        pdf_list = []
        for pdf_file in paginated_files:
            pdf_data = {
                "id": pdf_file.id,
                "email_id": pdf_file.email_id,
                "filename": pdf_file.filename,
                "original_filename": pdf_file.original_filename,
                "file_size": pdf_file.file_size,
                "sha256_hash": pdf_file.sha256_hash,
                "mime_type": pdf_file.mime_type,
                "page_count": pdf_file.page_count,
                "object_count": pdf_file.object_count,
                "created_at": pdf_file.created_at.isoformat() if pdf_file.created_at else None,
                "updated_at": pdf_file.updated_at.isoformat() if pdf_file.updated_at else None
            }
            pdf_list.append(pdf_data)
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        response_data = {
            "pdfs": pdf_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "filters": {
                "email_id": email_id
            }
        }
        
        logger.info(f"Listed {len(pdf_list)} PDFs (page {page}, limit {limit}, email_id={email_id})")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error listing PDFs: {e}")
        return jsonify({"error": "Internal server error"}), 500