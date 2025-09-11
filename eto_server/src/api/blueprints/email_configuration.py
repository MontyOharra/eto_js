"""
Email Configuration API Blueprint
REST endpoints for managing email ingestion configuration
"""
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from pydantic import ValidationError
import logging
from typing import Dict, Any

from ..schemas.email_configuration import (
    CreateEmailConfigRequest,
    UpdateEmailConfigRequest,
    ValidateConfigRequest,
    EmailConfigSummaryResponse,
    EmailConfigDetailResponse,
    ConfigTemplateResponse,
    ActivateConfigResponse
)
from ..schemas.common import APIResponse, ValidationResponse
from ...features.email_configuration import EmailConfigurationService

logger = logging.getLogger(__name__)

# Create blueprint
email_config_bp = Blueprint('email_configuration', __name__, url_prefix='/api/email-configuration')

# Initialize service
config_service = EmailConfigurationService()


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


@email_config_bp.route('/configurations', methods=['GET'])
@cross_origin()
def list_configurations():
    """List all email ingestion configurations"""
    try:
        order_by = request.args.get('order_by')
        desc = request.args.get('desc', 'false').lower() == 'true'
        
        configs = config_service.list_configurations(order_by=order_by, desc=desc)
        
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
            ).dict()
            for config in configs
        ]
        
        return jsonify({
            "success": True,
            "data": config_responses
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing configurations: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to list configurations"
        }), 500


@email_config_bp.route('/configurations', methods=['POST'])
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
        
        # Validate request data
        try:
            create_request = CreateEmailConfigRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Convert schema filter rules to domain objects
        filter_rules_data = [
            {
                "field": rule.field,
                "operation": rule.operation,
                "value": rule.value,
                "case_sensitive": rule.case_sensitive
            }
            for rule in create_request.filter_rules
        ]
        
        # Build configuration data for service
        config_data = {
            "connection": {
                "email_address": create_request.connection.email_address,
                "folder_name": create_request.connection.folder_name
            },
            "filters": {
                "rules": filter_rules_data
            },
            "monitoring": {
                "poll_interval_seconds": create_request.monitoring.poll_interval_seconds,
                "max_backlog_hours": create_request.monitoring.max_backlog_hours,
                "error_retry_attempts": create_request.monitoring.error_retry_attempts
            }
        }
        
        result = config_service.create_configuration(
            name=create_request.name,
            description=create_request.description or "",
            config_data=config_data,
            created_by=create_request.created_by
        )
        
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


@email_config_bp.route('/configurations/<int:config_id>', methods=['GET'])
@cross_origin()
def get_configuration(config_id: int):
    """Get specific email ingestion configuration"""
    try:
        config = config_service.get_configuration(config_id)
        
        if not config:
            return jsonify({
                "success": False,
                "error": "Configuration not found",
                "message": f"Configuration with ID {config_id} does not exist"
            }), 404
        
        # Convert domain object to response schema
        config_response = EmailConfigDetailResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            connection={
                "email_address": config.email_address,
                "folder_name": config.folder_name
            },
            filter_rules=[
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in config.filter_rules
            ],
            monitoring={
                "poll_interval_seconds": config.poll_interval_seconds,
                "max_backlog_hours": config.max_backlog_hours,
                "error_retry_attempts": config.error_retry_attempts
            },
            is_active=config.is_active,
            is_running=config.is_running,
            emails_processed=config.emails_processed,
            pdfs_found=config.pdfs_found,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at,
            created_by=config.created_by,
            created_at=config.created_at,
            updated_at=config.updated_at,
            last_used_at=config.last_used_at
        )
        
        return jsonify({
            "success": True,
            "data": config_response.dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get configuration"
        }), 500


@email_config_bp.route('/configurations/<int:config_id>', methods=['PUT'])
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
        
        # Validate request data
        try:
            update_request = UpdateEmailConfigRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Build configuration data for service (only include provided fields)
        config_data = {}
        
        if update_request.connection:
            config_data["connection"] = {
                "email_address": update_request.connection.email_address,
                "folder_name": update_request.connection.folder_name
            }
        
        if update_request.filter_rules:
            config_data["filters"] = {
                "rules": [
                    {
                        "field": rule.field,
                        "operation": rule.operation,
                        "value": rule.value,
                        "case_sensitive": rule.case_sensitive
                    }
                    for rule in update_request.filter_rules
                ]
            }
        
        if update_request.monitoring:
            config_data["monitoring"] = {
                "poll_interval_seconds": update_request.monitoring.poll_interval_seconds,
                "max_backlog_hours": update_request.monitoring.max_backlog_hours,
                "error_retry_attempts": update_request.monitoring.error_retry_attempts
            }
        
        result = config_service.update_configuration(config_id, config_data)
        
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


@email_config_bp.route('/configurations/<int:config_id>', methods=['DELETE'])
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


@email_config_bp.route('/configurations/<int:config_id>/activate', methods=['POST'])
@cross_origin()
def activate_configuration(config_id: int):
    """Activate an email ingestion configuration"""
    try:
        result = config_service.activate_configuration(config_id)
        
        if result["success"]:
            response = ActivateConfigResponse(
                config_id=result["config_id"],
                config_name=result["name"],
                message=result["message"]
            )
            return jsonify(response.dict()), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error activating configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to activate configuration"
        }), 500


@email_config_bp.route('/configurations/active', methods=['GET'])
@cross_origin()
def get_active_configuration():
    """Get currently active email ingestion configuration"""
    try:
        config = config_service.get_active_configuration()
        
        if not config:
            return jsonify({
                "success": False,
                "error": "No active configuration found",
                "message": "No configuration is currently active"
            }), 404
        
        # Convert domain object to response schema
        config_response = EmailConfigDetailResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            connection={
                "email_address": config.email_address,
                "folder_name": config.folder_name
            },
            filter_rules=[
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in config.filter_rules
            ],
            monitoring={
                "poll_interval_seconds": config.poll_interval_seconds,
                "max_backlog_hours": config.max_backlog_hours,
                "error_retry_attempts": config.error_retry_attempts
            },
            is_active=config.is_active,
            is_running=config.is_running,
            emails_processed=config.emails_processed,
            pdfs_found=config.pdfs_found,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at,
            created_by=config.created_by,
            created_at=config.created_at,
            updated_at=config.updated_at,
            last_used_at=config.last_used_at
        )
        
        return jsonify({
            "success": True,
            "data": config_response.dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting active configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get active configuration"
        }), 500


@email_config_bp.route('/configurations/validate', methods=['POST'])
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
        
        # Validate request schema first
        try:
            validate_request = ValidateConfigRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Build configuration data for service validation
        config_data = {
            "connection": {
                "email_address": validate_request.connection.email_address,
                "folder_name": validate_request.connection.folder_name
            },
            "filters": {
                "rules": [
                    {
                        "field": rule.field,
                        "operation": rule.operation,
                        "value": rule.value,
                        "case_sensitive": rule.case_sensitive
                    }
                    for rule in validate_request.filter_rules
                ]
            },
            "monitoring": {
                "poll_interval_seconds": validate_request.monitoring.poll_interval_seconds,
                "max_backlog_hours": validate_request.monitoring.max_backlog_hours,
                "error_retry_attempts": validate_request.monitoring.error_retry_attempts
            }
        }
        
        result = config_service.validate_configuration(config_data)
        
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


@email_config_bp.route('/configurations/template', methods=['GET'])
@cross_origin()
def get_configuration_template():
    """Get configuration template for creating new configurations"""
    try:
        template = config_service.get_configuration_template()
        
        # Convert to response schema
        template_response = ConfigTemplateResponse(
            connection={
                "email_address": template["connection"]["email_address"],
                "folder_name": template["connection"]["folder_name"]
            },
            filter_rules=[
                {
                    "field": rule["field"],
                    "operation": rule["operation"],
                    "value": rule["value"],
                    "case_sensitive": rule.get("case_sensitive", False)
                }
                for rule in template["filters"]["rules"]
            ],
            monitoring={
                "poll_interval_seconds": template["monitoring"]["poll_interval_seconds"],
                "max_backlog_hours": template["monitoring"]["max_backlog_hours"],
                "error_retry_attempts": template["monitoring"]["error_retry_attempts"]
            }
        )
        
        return jsonify({
            "success": True,
            "data": template_response.dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting configuration template: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get configuration template"
        }), 500


# === Error Handlers ===

@email_config_bp.errorhandler(404)
def handle_not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404


@email_config_bp.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "success": False,
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405


@email_config_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


# Export the blueprint
__all__ = ['email_config_bp']