"""
Email Ingestion API Blueprint
REST endpoints for managing email ingestion config
"""
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin, CORS
from pydantic import ValidationError
import logging
from typing import Dict, Any

from api.schemas.email_ingestion import (
    EmailConfigCreateRequest,
    EmailConfigSummaryResponse,
    EmailConfigActivateResponse
)
from api.schemas.common import APIResponse
from features.email_ingestion.service import EmailIngestionService
from shared.domain import EmailIngestionConnectionConfig, EmailIngestionConfigCreate, EmailFilterRule

logger = logging.getLogger(__name__)

# Service helper
def get_email_service() -> EmailIngestionService:
    """Get email ingestion service from app config"""
    email_service = current_app.config.get('EMAIL_INGESTION_SERVICE')
    if not email_service:
        raise RuntimeError("Email ingestion service not initialized")

    # Use isinstance instead of strict type equality to handle import path differences
    if not hasattr(email_service, 'start') or not hasattr(email_service, 'stop'):
        raise RuntimeError("Invalid email service object - missing required methods")

    return email_service


def handle_validation_error(e: ValidationError) -> Dict[str, Any]:
    """Convert Pydantic validation error to API response"""
    return {
        "success": False,
        "error": "Validation failed",
        "message": "Request data validation failed",
        "details": [
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "error": error["msg"],
                "value": error.get("input")
            }
            for error in e.errors()
        ]
    }


# Create blueprint
email_ingestion_bp = Blueprint('email_ingestion', __name__, url_prefix='/api/email-ingestion')

# Configure CORS for this blueprint specifically
CORS(email_ingestion_bp, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
        "supports_credentials": False
    }
})

# Add explicit OPTIONS handler for all routes
@email_ingestion_bp.route('/<path:path>', methods=['OPTIONS'])
@cross_origin()
def handle_options(path):
    """Handle preflight OPTIONS requests for all routes"""
    return '', 200


@email_ingestion_bp.route('/configs', methods=['GET'])
@cross_origin()
def list_email_configs():
    """List all email ingestion configs"""
    try:
        order_by = request.args.get('order_by')
        desc = request.args.get('desc', 'false').lower() == 'true'
        
        email_service = get_email_service()
        configs = email_service.config_service.list_configs(order_by=order_by, desc=desc)
        
        # Convert domain objects to response schemas
        config_responses = [
            EmailConfigSummaryResponse(
                id=config.id,
                name=config.name,
                folder_name=config.folder_name,
                is_active=config.is_active,
                is_running=config.is_running,
                emails_processed=config.emails_processed,
                pdfs_found=config.pdfs_found,
                last_used_at=config.last_used_at,
                created_at=config.created_at,
                updated_at=config.updated_at
            ) 
            for config in configs
        ]
        
        return jsonify({
            "success": True,
            "data": config_responses
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing configs: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to list configs"
        }), 500


@email_ingestion_bp.route('/configs', methods=['POST'])
@cross_origin()
def create_email_config():
    """Create new email ingestion config"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required",
                "message": "Missing config data"
            }), 400
        
        # Validate request data
        try:
            create_request = EmailConfigCreateRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Convert Pydantic filter rules to domain objects
        filter_rules = [
            EmailFilterRule(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            )
            for rule in create_request.filter_rules or []
        ]

        # Create domain object for creation (no ID)
        config_create = EmailIngestionConfigCreate(
            name=create_request.name,
            description=create_request.description or "",
            email_address=create_request.connection.email_address,
            folder_name=create_request.connection.folder_name,
            filter_rules=filter_rules,
            created_by=create_request.created_by,
            poll_interval_seconds=create_request.monitoring.poll_interval_seconds,
            max_backlog_hours=create_request.monitoring.max_backlog_hours,
            error_retry_attempts=create_request.monitoring.error_retry_attempts
        )

        email_service = get_email_service()
        created_config = email_service.config_service.create_config(config_create)

        # Convert domain object to API response
        return jsonify({
            "success": True,
            "data": {
                "id": created_config.id,
                "name": created_config.name,
                "message": "Configuration created successfully"
            }
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to create config"
        }), 400


@email_ingestion_bp.route('/configs/<int:config_id>/activate', methods=['POST'])
@cross_origin()
def activate_config(config_id: int):
    """Activate an email ingestion config with optional auto-start"""
    try:
        # Check if auto_start parameter is provided
        data = request.get_json() or {}
        auto_start = data.get('auto_start', False)
        
        # Activate the config
        email_service = get_email_service()
        activated_config = email_service.config_service.activate_config(config_id)
        
        # If auto_start is requested, try to start ingestion
        if auto_start:
            try:
                start_result = email_service.start()

                # Return combined response
                response = {
                    "success": True,
                    "config_id": activated_config.id,
                    "config_name": activated_config.name,
                    "message": f"Config activated and email ingestion started",
                    "activated": True,
                    "auto_started": start_result.success,
                    "start_message": start_result.message
                }

                if not start_result.success:
                    response["start_error"] = getattr(start_result, 'error', 'Unknown error')

                return jsonify(response), 200

            except Exception as e:
                logger.warning(f"Auto-start failed after activation: {e}")
                response = {
                    "success": True,
                    "config_id": activated_config.id,
                    "config_name": activated_config.name,
                    "message": f"Config activated but auto-start failed: {str(e)}",
                    "activated": True,
                    "auto_started": False,
                    "start_error": str(e)
                }
                return jsonify(response), 200

        # Standard activation response (no auto-start)
        response = EmailConfigActivateResponse(
            config_id=activated_config.id,
            config_name=activated_config.name,
            message="Configuration activated successfully",
            previous_active_config=None
        )
        return jsonify(response.dict()), 200
    
    except Exception as e:
        logger.error(f"Error activating config {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to activate config"
        }), 400

# === Service Control Endpoints ===

@email_ingestion_bp.route('/start', methods=['POST'])
@cross_origin()
def start_ingestion():
    """Start email ingestion service"""
    try:
        email_service = get_email_service()
        
        # Start the ingestion service
        result = email_service.start()

        if result.success:
            return jsonify(result.__dict__), 200
        else:
            return jsonify(result.__dict__), 400
    
    except Exception as e:
        logger.error(f"Error starting email ingestion: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to start email ingestion"
        }), 500


@email_ingestion_bp.route('/stop', methods=['POST'])
@cross_origin()
def stop_ingestion():
    """Stop email ingestion service"""
    try:
        email_service = get_email_service()
        
        # Stop the ingestion service
        result = email_service.stop()

        if result.success:
            return jsonify(result.__dict__), 200
        else:
            return jsonify(result.__dict__), 400
    
    except Exception as e:
        logger.error(f"Error stopping email ingestion: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to stop email ingestion"
        }), 500


@email_ingestion_bp.route('/test/folders', methods=['GET'])
@cross_origin()
def test_email_folders():
    """Test folder access for email address"""
    email_address = request.args.get('email_address')
    if not email_address:
        return jsonify({
            "success": False,
            "error": "email_address parameter is required",
            "message": "Must provide email_address query parameter"
        }), 400

    try:
        logger.info(f"Starting folder discovery for email: {email_address}")

        try:
            email_service = get_email_service()
            logger.info(f"Successfully retrieved email service")
        except Exception as service_error:
            logger.error(f"Failed to get email service: {service_error}")
            raise service_error

        # Test folder access for the email address
        logger.info(f"Calling test_folder_access for: {email_address}")
        folders = email_service.test_folder_access(email_address)
        logger.info(f"Successfully got {len(folders)} folders from service")

        return jsonify({
            "success": True,
            "data": {
                "folders": [
                    {
                        "account": email_address,
                        "folders": folders
                    }
                ],
                "total_accounts": 1
            }
        }), 200

    except Exception as e:
        logger.error(f"Error testing folder access for {email_address}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to test folder access for {email_address}"
        }), 500


@email_ingestion_bp.route('/discover/emails', methods=['GET'])
@cross_origin()
def discover_available_emails():
    """Discover all available email accounts from Outlook"""
    try:
        logger.info(f"Starting email account discovery")

        try:
            email_service = get_email_service()
            logger.info(f"Successfully retrieved email service for email discovery")

            # Discover available email accounts
            logger.info(f"Calling discover_available_emails")
            emails = email_service.discover_available_emails()
            logger.info(f"Successfully got {len(emails)} email accounts from service")

        except Exception as service_error:
            logger.error(f"Failed to get email service: {service_error}")
            logger.info(f"Using direct OutlookComService as fallback")

            # Direct fallback to OutlookComService if email service is not available
            from features.email_ingestion.integrations.outlook_com_service import OutlookComService
            outlook_service = OutlookComService()
            emails = outlook_service.discover_emails()
            logger.info(f"Successfully got {len(emails)} email accounts from direct OutlookComService")

        return jsonify({
            "success": True,
            "data": {
                "emails": emails,
                "total_accounts": len(emails)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error discovering email accounts: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to discover email accounts"
        }), 500


@email_ingestion_bp.route('/status', methods=['GET'])
@cross_origin()
def get_ingestion_status():
    """Get email ingestion service status"""
    try:
        logger.info(f"Getting email ingestion service status")

        try:
            email_service = get_email_service()
            logger.info(f"Successfully retrieved email service for status check")

            # Get comprehensive status from service
            status_response = email_service.get_ingestion_status()

            return jsonify({
                "success": True,
                "service_initialized": True,
                "data": status_response.__dict__
            }), 200

        except Exception as service_error:
            logger.error(f"Email service not initialized: {service_error}")

            # Return status indicating service is not initialized
            return jsonify({
                "success": True,
                "service_initialized": False,
                "message": "Email ingestion service is not initialized",
                "error": str(service_error),
                "data": {
                    "is_running": False,
                    "is_connected": False,
                    "current_config": None,
                    "connection_status": {
                        "is_connected": False,
                        "last_check": None,
                        "error_message": "Service not initialized"
                    }
                }
            }), 200

    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get ingestion status"
        }), 500

# === Error Handlers ===

@email_ingestion_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404


@email_ingestion_bp.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "success": False,
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405


@email_ingestion_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500




# Export the blueprint
__all__ = ['email_ingestion_bp']