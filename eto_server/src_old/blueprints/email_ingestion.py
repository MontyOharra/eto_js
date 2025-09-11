"""
Email Ingestion API Blueprint
Provides REST endpoints for managing email ingestion configuration and monitoring
"""
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
import asyncio
from typing import Dict, Any

from ..services.email_ingestion_service import EmailIngestionService
from ..services.email_config_service import EmailConfigService

logger = logging.getLogger(__name__)

# Create blueprint
email_ingestion_bp = Blueprint('email_ingestion', __name__, url_prefix='/api/email-ingestion')

# Initialize services (these will be singletons)
ingestion_service = EmailIngestionService()
config_service = EmailConfigService()


# === Service Management Endpoints ===
@email_ingestion_bp.route('/health', methods=['GET'])
@cross_origin()
def get_service_health():
    """Get basic service health check"""
    try:
        health = asyncio.run(ingestion_service.get_health_status())
        
        return jsonify({
            "success": True,
            "data": {
                "is_running": health.is_running,
                "is_connected": health.is_connected,
                "configuration_loaded": health.configuration_loaded,
                "last_error": health.last_error,
                "uptime_seconds": health.stats.uptime_seconds,
                "emails_processed": health.stats.emails_processed
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting service health: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get service health"
        }), 500

@email_ingestion_bp.route('/status', methods=['GET'])
@cross_origin()
def get_service_status():
    """Get comprehensive email ingestion service status"""
    try:
        status = asyncio.run(ingestion_service.get_detailed_status())
        return jsonify({
            "success": True,
            "data": status
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get service status"
        }), 500

@email_ingestion_bp.route('/start', methods=['POST'])
@cross_origin()
def start_service():
    """Start the email ingestion service"""
    try:
        result = asyncio.run(ingestion_service.start_service())
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to start service"
        }), 500


@email_ingestion_bp.route('/stop', methods=['POST'])
@cross_origin()
async def stop_service():
    """Stop the email ingestion service"""
    try:
        result = await ingestion_service.stop_service()
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to stop service"
        }), 500


@email_ingestion_bp.route('/restart', methods=['POST'])
@cross_origin()
async def restart_service():
    """Restart the email ingestion service"""
    try:
        result = await ingestion_service.restart_service()
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to restart service"
        }), 500


@email_ingestion_bp.route('/reload-config', methods=['POST'])
@cross_origin()
async def reload_configuration():
    """Reload active configuration without restarting service"""
    try:
        result = await ingestion_service.reload_configuration()
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to reload configuration"
        }), 500


# === Configuration Management Endpoints ===

@email_ingestion_bp.route('/configurations', methods=['GET'])
@cross_origin()
def list_configurations():
    """List all email ingestion configurations"""
    try:
        configurations = config_service.list_configurations()
        
        return jsonify({
            "success": True,
            "data": configurations
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing configurations: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to list configurations"
        }), 500


@email_ingestion_bp.route('/configurations', methods=['POST'])
@cross_origin()
def create_configuration():
    """Create new email ingestion configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required",
                "message": "Missing configuration data"
            }), 400
        
        name = data.get('name')
        config_data = data.get('configuration')
        
        if not name or not config_data:
            return jsonify({
                "success": False,
                "error": "Both 'name' and 'configuration' fields are required",
                "message": "Missing required fields"
            }), 400
        
        result = config_service.create_configuration(name, config_data)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error creating configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to create configuration"
        }), 500


@email_ingestion_bp.route('/configurations/<int:config_id>', methods=['GET'])
@cross_origin()
def get_configuration(config_id: int):
    """Get specific email ingestion configuration"""
    try:
        config_data = config_service.get_configuration(config_id)
        
        if not config_data:
            return jsonify({
                "success": False,
                "error": "Configuration not found",
                "message": f"Configuration with ID {config_id} does not exist"
            }), 404
        
        # Convert dataclasses to dict for JSON serialization
        result = {
            "connection": {
                "email_address": config_data.connection.email_address,
                "folder_name": config_data.connection.folder_name,
                "polling_interval": config_data.connection.polling_interval,
                "max_hours_back": config_data.connection.max_hours_back
            },
            "filters": {
                "name": config_data.filters.name,
                "rules": [
                    {
                        "type": rule.type,
                        "pattern": rule.pattern,
                        "operation": rule.operation
                    }
                    for rule in config_data.filters.rules
                ],
                "require_attachments": config_data.filters.require_attachments,
                "pdf_only": config_data.filters.pdf_only,
                "enabled": config_data.filters.enabled
            },
            "monitoring": {
                "auto_reconnect": config_data.monitoring.auto_reconnect,
                "max_reconnect_attempts": config_data.monitoring.max_reconnect_attempts,
                "connection_timeout": config_data.monitoring.connection_timeout,
                "health_check_interval": config_data.monitoring.health_check_interval
            },
            "metadata": {
                "created_at": config_data.created_at.isoformat(),
                "updated_at": config_data.updated_at.isoformat()
            }
        }
        
        return jsonify({
            "success": True,
            "data": result
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get configuration"
        }), 500


@email_ingestion_bp.route('/configurations/<int:config_id>', methods=['PUT'])
@cross_origin()
def update_configuration(config_id: int):
    """Update existing email ingestion configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required",
                "message": "Missing configuration data"
            }), 400
        
        result = config_service.update_configuration(config_id, data)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error updating configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to update configuration"
        }), 500


@email_ingestion_bp.route('/configurations/<int:config_id>', methods=['DELETE'])
@cross_origin()
def delete_configuration(config_id: int):
    """Delete email ingestion configuration"""
    try:
        result = config_service.delete_configuration(config_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error deleting configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to delete configuration"
        }), 500


@email_ingestion_bp.route('/configurations/<int:config_id>/activate', methods=['POST'])
@cross_origin()
def activate_configuration(config_id: int):
    """Activate an email ingestion configuration"""
    try:
        result = config_service.activate_configuration(config_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error activating configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to activate configuration"
        }), 500


@email_ingestion_bp.route('/configurations/active', methods=['GET'])
@cross_origin()
def get_active_configuration():
    """Get currently active email ingestion configuration"""
    try:
        config_data = config_service.get_active_configuration()
        
        if not config_data:
            return jsonify({
                "success": False,
                "error": "No active configuration found",
                "message": "No configuration is currently active"
            }), 404
        
        # Convert dataclasses to dict for JSON serialization
        result = {
            "connection": {
                "email_address": config_data.connection.email_address,
                "folder_name": config_data.connection.folder_name,
                "polling_interval": config_data.connection.polling_interval,
                "max_hours_back": config_data.connection.max_hours_back
            },
            "filters": {
                "name": config_data.filters.name,
                "rules": [
                    {
                        "type": rule.type,
                        "pattern": rule.pattern,
                        "operation": rule.operation
                    }
                    for rule in config_data.filters.rules
                ],
                "require_attachments": config_data.filters.require_attachments,
                "pdf_only": config_data.filters.pdf_only,
                "enabled": config_data.filters.enabled
            },
            "monitoring": {
                "auto_reconnect": config_data.monitoring.auto_reconnect,
                "max_reconnect_attempts": config_data.monitoring.max_reconnect_attempts,
                "connection_timeout": config_data.monitoring.connection_timeout,
                "health_check_interval": config_data.monitoring.health_check_interval
            },
            "metadata": {
                "created_at": config_data.created_at.isoformat(),
                "updated_at": config_data.updated_at.isoformat()
            }
        }
        
        return jsonify({
            "success": True,
            "data": result
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting active configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get active configuration"
        }), 500


# === Validation and Template Endpoints ===

@email_ingestion_bp.route('/configurations/validate', methods=['POST'])
@cross_origin()
def validate_configuration():
    """Validate email ingestion configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required",
                "message": "Missing configuration data"
            }), 400
        
        result = config_service.validate_configuration(data)
        
        return jsonify({
            "success": True,
            "data": result
        }), 200
    
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to validate configuration"
        }), 500


@email_ingestion_bp.route('/configurations/template', methods=['GET'])
@cross_origin()
def get_configuration_template():
    """Get configuration template for creating new configurations"""
    try:
        template = config_service.get_configuration_template()
        
        return jsonify({
            "success": True,
            "data": template
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting configuration template: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get configuration template"
        }), 500


# === Statistics and Monitoring Endpoints ===

@email_ingestion_bp.route('/statistics', methods=['GET'])
@cross_origin()
def get_statistics():
    """Get email processing statistics"""
    try:
        config_id = request.args.get('config_id')
        
        if config_id:
            try:
                config_id = int(config_id)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": "Invalid config_id parameter",
                    "message": "config_id must be an integer"
                }), 400
        
        stats = config_service.get_configuration_stats(config_id)
        
        return jsonify({
            "success": True,
            "data": stats
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get statistics"
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


# === Simple Configuration Management ===

@email_ingestion_bp.route('/config', methods=['POST'])
@cross_origin()
def create_simple_config():
    """Create a simple email configuration from email_address and folder_name"""
    try:
        data = request.get_json() or {}
        email_address = data.get('email_address')
        folder_name = data.get('folder_name', 'Inbox')
        name = data.get('name', f"{email_address}_{folder_name}")
        
        if not email_address:
            return jsonify({
                "success": False,
                "error": "email_address is required",
                "message": "Must provide email_address in request body"
            }), 400
        
        # Create default configuration structure
        config_data = {
            "connection": {
                "email_address": email_address,
                "folder_name": folder_name,
                "polling_interval": 60,
                "max_hours_back": 24
            },
            "filters": {
                "name": "Default Filter",
                "rules": [
                    {
                        "type": "attachment",
                        "pattern": "pdf",
                        "operation": "contains"
                    }
                ],
                "require_attachments": True,
                "pdf_only": True,
                "enabled": True
            },
            "monitoring": {
                "auto_reconnect": True,
                "max_reconnect_attempts": 5,
                "connection_timeout": 30,
                "health_check_interval": 60
            }
        }
        
        # Create configuration
        result = config_service.create_configuration(name, config_data)
        
        if result["success"]:
            config_id = result.get("configuration_id")
            if config_id:
                # Activate the configuration
                activate_result = config_service.activate_configuration(config_id)
                result["activation"] = activate_result
            
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error creating simple configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to create configuration"
        }), 500


# === Service Initialization Hook ===
# Note: Automatic startup removed for Flask 2.2+ compatibility
# Service will be started manually via /api/email-ingestion/start endpoint


# Export the blueprint
__all__ = ['email_ingestion_bp']