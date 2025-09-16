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


# Service helper function
def get_email_ingestion_service():
    """Get email ingestion service from app config"""
    from flask import current_app
    return current_app.config.get('EMAIL_INGESTION_SERVICE')


@pdf_viewing_bp.route('/<int:pdf_id>', methods=['GET'])
@cross_origin()
def get_pdf_metadata(pdf_id: int):
    """
    Get PDF metadata by ID
    
    Returns:
        JSON response with PDF metadata
    """
    try:
        email_service = get_email_ingestion_service()
        if not email_service:
            return jsonify({"error": "Email ingestion service not available"}), 500
        
        pdf_data = email_service.get_pdf_metadata(pdf_id)
        if not pdf_data:
            return jsonify({"error": "PDF not found"}), 404
        
        logger.info(f"Retrieved PDF metadata for {pdf_id}: {pdf_data.get('filename')}")
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
        email_service = get_email_ingestion_service()
        if not email_service:
            return jsonify({"error": "Email ingestion service not available"}), 500
        
        # Get PDF metadata first
        pdf_data = email_service.get_pdf_metadata(pdf_id)
        if not pdf_data:
            return jsonify({"error": "PDF not found"}), 404
        
        # Get PDF content
        pdf_content = email_service.get_pdf_content(pdf_id)
        if not pdf_content:
            logger.error(f"PDF content not found for {pdf_id}")
            return jsonify({"error": "PDF file not found on disk"}), 404
        
        # Create response with proper headers for PDF viewing
        response = current_app.response_class(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{pdf_data["original_filename"]}"',
                'Content-Length': str(len(pdf_content)),
                'Cache-Control': 'public, max-age=3600'  # Cache for 1 hour
            }
        )
        
        logger.info(f"Served PDF content for {pdf_id}: {pdf_data['filename']} ({len(pdf_content)} bytes)")
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
        email_service = get_email_ingestion_service()
        if not email_service:
            return jsonify({"error": "Email ingestion service not available"}), 500
        
        pdf_data = email_service.get_pdf_metadata(pdf_id)
        if not pdf_data:
            return jsonify({"error": "PDF not found"}), 404
        
        # Basic PDF information (already in the right format from service)
        pdf_info = pdf_data.copy()
        
        # Add processing status information
        # Note: We'd need to add this to the service method if needed
        pdf_info["processing_status"] = {
            "has_extracted_objects": False,  # Would need service method to check this
            "objects_json_size": 0
        }
        
        # Add storage information
        storage_info = email_service.get_pdf_storage_info()
        pdf_info["storage_info"] = storage_info
        
        logger.info(f"Retrieved detailed PDF info for {pdf_id}: {pdf_data['filename']}")
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
        email_service = get_email_ingestion_service()
        if not email_service:
            return jsonify({"error": "Email ingestion service not available"}), 500
        
        pdf_list = email_service.get_pdfs_by_email(email_id)
        
        # PDF list is already in the right format from service
        
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
        email_service = get_email_ingestion_service()
        if not email_service:
            return jsonify({"error": "Email ingestion service not available"}), 500
        
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
            all_pdfs = email_service.get_pdfs_by_email(email_id)
            # Simple in-memory pagination for email-specific results
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            pdf_list = all_pdfs[start_idx:end_idx]
            total_count = len(all_pdfs)
        else:
            # For now, return an error since we don't have a "get all PDFs" service method
            # In production, we'd implement proper pagination in the service layer
            return jsonify({"error": "Global PDF listing not implemented. Please specify email_id parameter."}), 400
        
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