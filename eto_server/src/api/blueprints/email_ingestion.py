"""
Email Ingestion API Blueprint
REST endpoints for managing email ingestion configuration
"""
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from pydantic import ValidationError
import logging
from typing import Dict, Any

from src.api.schemas.email_ingestion import (
    CreateEmailConfigRequest,
    EmailConfigSummaryResponse,
    ActivateConfigResponse
)
from src.api.schemas.common import APIResponse
from src.features.email_ingestion.service import EmailIngestionService

logger = logging.getLogger(__name__)

# Create blueprint
email_ingestion_bp = Blueprint('email_ingestion', __name__, url_prefix='/api/email-ingestion')

# Service helper
def get_email_service() -> EmailIngestionService:
    """Get email ingestion service from app config"""
    email_service = current_app.config.get('EMAIL_INGESTION_SERVICE')
    if not email_service:
        raise RuntimeError("Email ingestion service not initialized")
    
    assert type(email_service) == EmailIngestionService 
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


@email_ingestion_bp.route('/configurations', methods=['GET'])
@cross_origin()
def list_configurations():
    """List all email ingestion configurations"""
    try:
        order_by = request.args.get('order_by')
        desc = request.args.get('desc', 'false').lower() == 'true'
        
        email_service = get_email_service()
        configs = email_service.config_service.list_configurations(order_by=order_by, desc=desc)
        
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
            ).dict() if config.id is not None else None
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
        
        # Validate request data
        try:
            create_request = CreateEmailConfigRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Convert schema filter rules to domain objects
        filter_rules_data = []
        if create_request.filter_rules:
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
                "name": f"Filter for {create_request.name}",
                "rules": filter_rules_data
            },
            "monitoring": {
                "poll_interval_seconds": create_request.monitoring.poll_interval_seconds,
                "max_backlog_hours": create_request.monitoring.max_backlog_hours,
                "error_retry_attempts": create_request.monitoring.error_retry_attempts
            }
        }
        
        email_service = get_email_service()
        result = email_service.config_service.create_configuration(
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




@email_ingestion_bp.route('/configurations/<int:config_id>/activate', methods=['POST'])
@cross_origin()
def activate_configuration(config_id: int):
    """Activate an email ingestion configuration with optional auto-start"""
    try:
        # Check if auto_start parameter is provided
        data = request.get_json() or {}
        auto_start = data.get('auto_start', False)
        
        # Activate the configuration
        email_service = get_email_service()
        result = email_service.config_service.activate_configuration(config_id)
        
        if not result["success"]:
            return jsonify(result), 400
        
        # If auto_start is requested, try to start ingestion
        if auto_start:
            try:
                start_result = email_service.start_ingestion()
                
                # Return combined response
                response = {
                    "success": True,
                    "config_id": result["config_id"],
                    "config_name": result["name"],
                    "message": f"Configuration activated and email ingestion started",
                    "activated": True,
                    "auto_started": start_result.get("success", False),
                    "start_message": start_result.get("message", "")
                }
                
                if not start_result.get("success"):
                    response["start_error"] = start_result.get("error", "Unknown error")
                
                return jsonify(response), 200
                
            except Exception as e:
                logger.warning(f"Auto-start failed after activation: {e}")
                response = {
                    "success": True,
                    "config_id": result["config_id"],
                    "config_name": result["name"],
                    "message": f"Configuration activated but auto-start failed: {str(e)}",
                    "activated": True,
                    "auto_started": False,
                    "start_error": str(e)
                }
                return jsonify(response), 200
        
        # Standard activation response (no auto-start)
        response = ActivateConfigResponse(
            config_id=result["config_id"],
            config_name=result["name"],
            message=result["message"],
            previous_active_config=None
        )
        return jsonify(response.dict()), 200
    
    except Exception as e:
        logger.error(f"Error activating configuration {config_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to activate configuration"
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


# === Service Control Endpoints ===

@email_ingestion_bp.route('/start', methods=['POST'])
@cross_origin()
def start_ingestion():
    """Start email ingestion service"""
    try:
        email_service = get_email_service()
        
        # Start the ingestion service
        result = email_service.start_ingestion()
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
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
        result = email_service.stop_ingestion()
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error stopping email ingestion: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to stop email ingestion"
        }), 500


@email_ingestion_bp.route('/status', methods=['GET'])
@cross_origin()
def get_ingestion_status():
    """Get email ingestion service status"""
    try:
        email_service = get_email_service()
        
        # Get service status
        status = {
            "success": True,
            "data": {
                "is_running": email_service.is_running,
                "is_connected": email_service.is_connected,
                "current_config_id": email_service.current_config.id if email_service.current_config else None,
                "current_config_name": email_service.current_config.name if email_service.current_config else None,
                "stats": {
                    "emails_processed": email_service.stats.emails_processed,
                    "pdfs_found": email_service.stats.pdfs_found,
                    "processing_errors": email_service.stats.processing_errors,
                    "last_processed_at": email_service.stats.last_processed_at.isoformat() if email_service.stats.last_processed_at else None,
                    "uptime_seconds": email_service.stats.uptime_seconds,
                    "reconnections": email_service.stats.reconnections
                }
            }
        }
        
        return jsonify(status), 200
    
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get ingestion status"
        }), 500


@email_ingestion_bp.route('/test/folders', methods=['GET'])
@cross_origin()
def list_outlook_folders():
    """Test endpoint to list available Outlook folders for a given email"""
    try:
        email_address = request.args.get('email_address')
        
        # Get email service and create temporary connection
        email_service = get_email_service()
        outlook_service = email_service.outlook_service
        
        # Test connection to get folder list
        from ...features.email_ingestion.types import EmailConnectionConfig
        test_config = EmailConnectionConfig(
            email_address=email_address,
            folder_name="Inbox"  # Use Inbox as default for connection test
        )
        
        # Initialize COM and get namespace
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            
            folders = []
            
            def get_all_folders(parent_folder, path="", max_depth=3, current_depth=0):
                """Recursively get all folders including subfolders"""
                folder_list = []
                if current_depth >= max_depth:
                    return folder_list
                
                try:
                    for folder in parent_folder.Folders:
                        try:
                            folder_path = f"{path}/{folder.Name}" if path else folder.Name
                            folder_info = {
                                "name": folder.Name,
                                "path": folder_path,
                                "type": "folder",
                                "count": folder.Items.Count if hasattr(folder, 'Items') else 0
                            }
                            folder_list.append(folder_info)
                            
                            # Get subfolders recursively
                            if hasattr(folder, 'Folders') and folder.Folders.Count > 0:
                                subfolders = get_all_folders(folder, folder_path, max_depth, current_depth + 1)
                                folder_list.extend(subfolders)
                                
                        except Exception as e:
                            logger.debug(f"Error accessing folder: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Error enumerating folders: {e}")
                
                return folder_list
            
            # Get all accounts and their folders
            for account in namespace.Accounts:
                if not email_address or account.SmtpAddress.lower() == email_address.lower():
                    account_folders = {
                        "account": account.SmtpAddress,
                        "folders": []
                    }
                    
                    try:
                        # Get the delivery store for this account
                        delivery_store = account.DeliveryStore
                        if delivery_store:
                            # Get root folder for this account's store
                            root_folder = delivery_store.GetRootFolder()
                            
                            # Add standard folders first
                            for folder_name, folder_id in outlook_service.folder_mapping.items():
                                try:
                                    folder = namespace.GetDefaultFolder(folder_id)
                                    # Check if this folder belongs to the current account
                                    if folder.Store == delivery_store:
                                        account_folders["folders"].append({
                                            "name": folder_name,
                                            "display_name": folder.Name,
                                            "path": folder.Name,
                                            "type": "standard",
                                            "count": folder.Items.Count
                                        })
                                except:
                                    continue
                            
                            # Get all custom folders recursively from this account's store
                            custom_folders = get_all_folders(root_folder)
                            
                            # Filter out standard folders we already added
                            standard_names = [f["display_name"] for f in account_folders["folders"]]
                            for custom_folder in custom_folders:
                                if custom_folder["name"] not in standard_names:
                                    custom_folder["type"] = "custom"
                                    account_folders["folders"].append(custom_folder)
                    
                    except Exception as e:
                        logger.warning(f"Error accessing account {account.SmtpAddress}: {e}")
                        # Fallback to namespace folders if account-specific access fails
                        try:
                            all_folders = get_all_folders(namespace)
                            account_folders["folders"] = all_folders
                        except:
                            pass
                    
                    folders.append(account_folders)
                    
                    if email_address:  # If specific email requested, only get that one
                        break
            
            return jsonify({
                "success": True,
                "data": {
                    "folders": folders,
                    "total_accounts": len(folders)
                }
            }), 200
            
        finally:
            pythoncom.CoUninitialize()
    
    except Exception as e:
        logger.error(f"Error listing Outlook folders: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to list Outlook folders"
        }), 500


# Export the blueprint
__all__ = ['email_ingestion_bp']