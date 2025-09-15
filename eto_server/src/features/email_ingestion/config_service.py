"""
Email Configuration Service
Manages email ingestion configuration with validation and admin operations
"""
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from jsonschema import validate as json_validate, ValidationError

from .types import EmailIngestionConfig, EmailConfigSummary, EmailConfigStats, EmailFilterRule
from ...shared.database import EmailIngestionConfigModel
from ...shared.database.repositories import EmailIngestionConfigRepository

logger = logging.getLogger(__name__)


class EmailIngestionConfigurationService:
    """Manages email ingestion configuration with validation and admin operations"""
    
    def __init__(self, config_repo: EmailIngestionConfigRepository):
        self.config_repo = config_repo
        self.logger = logging.getLogger(__name__)
        
        # JSON schema for configuration validation
        
        '''
        Example config:
        {
            "connection": {
                "email_address": "test@test.com",
                "folder_name": "test"
            },
            "filters": {
                "name": "Production Email Filter",
                "rules": [
                    {
                        "field": "sender_email",
                        "operation": "contains",
                        "value": "@supplier.com",
                        "case_sensitive": false
                    },
                    {
                        "field": "subject",
                        "operation": "contains",
                        "value": "invoice",
                        "case_sensitive": false
                    },
                    {
                        "field": "has_attachments",
                        "operation": "equals",
                        "value": "true",
                        "case_sensitive": false
                    }
                ],
            },
            "monitoring": {
                "poll_interval_seconds": 60,
                "pdf_only": True,
                "enabled": True
            }
        }
        '''
        
        self.config_schema = {
            "type": "object",
            "required": ["connection", "filters", "monitoring"],
            "properties": {
                "connection": {
                    "type": "object",
                    "required": ["email_address", "folder_name"],
                    "properties": {
                        "email_address": {"type": "string", "minLength": 1},
                        "folder_name": {"type": "string", "minLength": 1},
                        "polling_interval": {"type": "integer", "minimum": 10},
                        "max_hours_back": {"type": "integer", "minimum": 1}
                    }
                },
                "filters": {
                    "type": "object",
                    "required": ["name", "rules"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "rules": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["field", "operation", "value"],
                                "properties": {
                                    "field": {"type": "string", "enum": ["sender_email", "subject", "has_attachments", "received_date"]},
                                    "operation": {"type": "string", "enum": ["contains", "equals", "starts_with", "ends_with", "before", "after"]},
                                    "value": {"type": "string", "minLength": 1},
                                    "case_sensitive": {"type": "boolean"}
                                }
                            }
                        },
                        "require_attachments": {"type": "boolean"},
                        "pdf_only": {"type": "boolean"},
                        "enabled": {"type": "boolean"}
                    }
                },
                "monitoring": {
                    "type": "object",
                    "properties": {
                        "poll_interval_seconds": {"type": "integer", "minimum": 5},
                        "max_backlog_hours": {"type": "integer", "minimum": 1},
                        "error_retry_attempts": {"type": "integer", "minimum": 1}
                    }
                }
            }
        }

    # === High-Level API Methods ===
    
    def create_configuration(self, name: str, description: str, config_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Create new email ingestion configuration"""
        try:
            self.logger.info(f"Creating new email configuration: {name}")
            
            # Validate configuration structure  
            try:
                json_validate(config_data, self.config_schema)
            except ValidationError as e:
                raise Exception(f"Configuration validation failed: {str(e)}")
            
            # Convert to filter rules
            filter_rules = [
                EmailFilterRule(
                    field=rule["field"],
                    operation=rule["operation"],
                    value=rule["value"],
                    case_sensitive=rule.get("case_sensitive", False)
                )
                for rule in config_data["filters"]["rules"]
            ]
            
            # Serialize filter rules to JSON
            filter_rules_json = json.dumps([
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in filter_rules
            ])
            
            # Create configuration record and get ID
            config_id = self.config_repo.create_and_get_id({
                "name": name,
                "description": description,
                "email_address": config_data["connection"].get("email_address"),
                "folder_name": config_data["connection"]["folder_name"],
                "filter_rules": filter_rules_json,
                "poll_interval_seconds": config_data["monitoring"].get("poll_interval_seconds", 5),
                "max_backlog_hours": config_data["monitoring"].get("max_backlog_hours", 24),
                "error_retry_attempts": config_data["monitoring"].get("error_retry_attempts", 3),
                "is_active": False,  # New configs start inactive
                "is_running": False,
                "created_by": created_by,
                "emails_processed": 0,
                "pdfs_found": 0
            })
            
            self.logger.info(f"Created email configuration {name} with ID {config_id}")
            
            return {
                "success": True,
                "configuration_id": config_id,
                "name": name,
                "message": "Configuration created successfully"
            }
        
        except Exception as e:
            self.logger.exception(f"Error creating configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create configuration"
            }
    
    def update_configuration(self, config_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing email ingestion configuration"""
        try:
            self.logger.info(f"Updating email configuration ID {config_id}")
            
            # Validate configuration structure
            validation_result = self.validate_configuration(config_data)
            if not validation_result["valid"]:
                raise Exception(f"Configuration validation failed: {validation_result['errors']}")
            
            # Convert to filter rules and serialize
            filter_rules = [
                EmailFilterRule(
                    field=rule["field"],
                    operation=rule["operation"],
                    value=rule["value"],
                    case_sensitive=rule.get("case_sensitive", False)
                )
                for rule in config_data["filters"]["rules"]
            ]
            
            filter_rules_json = json.dumps([
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in filter_rules
            ])
            
            # Update configuration record
            config = self.config_repo.update(config_id, {
                "email_address": config_data["connection"].get("email_address"),
                "folder_name": config_data["connection"]["folder_name"],
                "filter_rules": filter_rules_json,
                "poll_interval_seconds": config_data["monitoring"].get("poll_interval_seconds", 5),
                "max_backlog_hours": config_data["monitoring"].get("max_backlog_hours", 24),
                "error_retry_attempts": config_data["monitoring"].get("error_retry_attempts", 3),
            })
            
            if not config:
                raise Exception(f"Configuration with ID {config_id} not found")
            
            # Extract name to avoid Column type issues
            config_name = config.name
            self.logger.info(f"Updated email configuration {config_name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config_name,
                "message": "Configuration updated successfully"
            }
        
        except Exception as e:
            self.logger.exception(f"Error updating configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update configuration"
            }
    
    def activate_configuration(self, config_id: int) -> Dict[str, Any]:
        """Activate an email ingestion configuration (deactivates all others)"""
        try:
            self.logger.info(f"Activating email configuration ID {config_id}")
            
            # Set this configuration as active
            config = self.config_repo.set_config_active(config_id)
            
            if not config:
                raise Exception(f"Configuration with ID {config_id} not found")
            
            # Extract name to avoid Column type issues
            config_name = config.name
            self.logger.info(f"Activated email configuration: {config_name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config_name,
                "message": "Configuration activated successfully"
            }
        
        except Exception as e:
            self.logger.exception(f"Error activating configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to activate configuration"
            }
    
    def get_active_configuration(self) -> Optional[EmailIngestionConfig]:
        """Get currently active email ingestion configuration as domain object"""
        try:
            config = self.config_repo.get_active_config()
            
            if not config:
                self.logger.warning("No active email configuration found")
                return None
            
            return config  # Repository now returns domain object directly
        
        except Exception as e:
            self.logger.exception(f"Error getting active configuration: {e}")
            return None
    
    def get_configuration(self, config_id: int) -> Optional[EmailIngestionConfig]:
        """Get specific email ingestion configuration by ID as domain object"""
        try:
            return self.config_repo.get_by_id(config_id)
        
        except Exception as e:
            self.logger.exception(f"Error getting configuration {config_id}: {e}")
            return None
    
    def list_configurations(self, order_by: Optional[str] = None, desc: bool = False) -> List[EmailIngestionConfig]:
        """List all email ingestion configurations with full details"""
        try:
            if order_by:
                # For custom ordering, would need to update repository to support this
                # For now, just use get_all_configs which returns domain objects
                configs = self.config_repo.get_all_configs()
            else:
                configs = self.config_repo.get_all_configs()
            
            # Repository now returns domain objects directly
            return configs
        
        except Exception as e:
            self.logger.exception(f"Error listing configurations: {e}")
            return []
    
    def delete_configuration(self, config_id: int) -> Dict[str, Any]:
        """Delete an email ingestion configuration"""
        try:
            self.logger.info(f"Deleting email configuration ID {config_id}")
            
            # Delegate to repository for atomic delete operation
            result = self.config_repo.delete_if_inactive(config_id)
            
            if not result["success"]:
                raise Exception(result["message"])
            
            self.logger.info(f"Deleted email configuration: {result['name']}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": result["name"],
                "message": "Configuration deleted successfully"
            }
        
        except Exception as e:
            self.logger.exception(f"Error deleting configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete configuration"
            }
    
    def update_runtime_status(self, config_id: int, is_running: bool) -> Dict[str, Any]:
        """Update runtime status of configuration"""
        try:
            self.logger.info(f"Updating runtime status for config {config_id} to: {'running' if is_running else 'stopped'}")
            
            config = self.config_repo.update_runtime_status(config_id, is_running)
            
            if not config:
                raise Exception(f"Configuration with ID {config_id} not found")
            
            # Extract name to avoid Column type issues
            config_name = config.name
            self.logger.info(f"Updated runtime status for config: {config_name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "config_name": config_name,
                "is_running": is_running,
                "message": f"Runtime status updated to {'running' if is_running else 'stopped'}"
            }
        
        except Exception as e:
            self.logger.exception(f"Error updating runtime status for config {config_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update runtime status"
            }
    
    def increment_processing_stats(self, config_id: int, emails: int, pdfs: int) -> Optional[EmailIngestionConfig]:
        """Increment processing statistics for configuration"""
        try:
            self.logger.debug(f"Incrementing stats for config {config_id}: +{emails} emails, +{pdfs} PDFs")
            
            config = self.config_repo.increment_processing_stats(config_id, emails, pdfs)
            
            if not config:
                self.logger.warning(f"Configuration with ID {config_id} not found for stats update")
                return None
            
            return config
        
        except Exception as e:
            self.logger.exception(f"Error incrementing processing stats for config {config_id}: {e}")
            return None

    # === Helper Methods ===
    
    # === Validation Methods ===
    
    def validate_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email ingestion configuration structure and data"""
        try:
            # Schema validation
            json_validate(config_data, self.config_schema)
            
            validation_errors = []
            warnings = []
            
            # Additional business logic validation
            connection = config_data.get("connection", {})
            filters = config_data.get("filters", {})
            monitoring = config_data.get("monitoring", {})
            
            # Connection validation
            email_address = connection.get("email_address", "").strip()
            if not email_address:
                validation_errors.append("Email address is required and cannot be empty")
            elif "@" not in email_address or "." not in email_address:
                validation_errors.append("Email address must be a valid email format")
            
            folder_name = connection.get("folder_name", "").strip()
            if not folder_name:
                validation_errors.append("Folder name cannot be empty")
            
            # Filter validation
            rules = filters.get("rules", [])
            if not rules:
                validation_errors.append("At least one filter rule is required")
            
            for i, rule in enumerate(rules):
                field = rule.get("field")
                value = rule.get("value", "").strip()
                operation = rule.get("operation", "contains")
                
                if not value:
                    validation_errors.append(f"Rule {i+1}: Value cannot be empty")
                
                if field == "received_date" and operation not in ["before", "after"]:
                    validation_errors.append(f"Rule {i+1}: Date rules must use 'before' or 'after' operation")
            
            # Monitoring validation
            poll_interval = monitoring.get("poll_interval_seconds", 5)
            if poll_interval < 5:
                validation_errors.append("Poll interval must be at least 5 seconds")
            elif poll_interval < 30:
                warnings.append("Poll intervals under 30 seconds may impact performance")
            
            max_attempts = monitoring.get("error_retry_attempts", 3)
            if max_attempts < 1:
                validation_errors.append("Error retry attempts must be at least 1")
            elif max_attempts > 10:
                warnings.append("High retry attempt values may cause extended processing delays")
            
            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings
            }
        
        except ValidationError as ve:
            return {
                "valid": False,
                "errors": [f"Schema validation failed: {ve.message}"],
                "warnings": []
            }
        
        except Exception as e:
            self.logger.exception(f"Error validating configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    def get_configuration_template(self) -> Dict[str, Any]:
        """Get a template configuration for creating new configs"""
        return {
            "connection": {
                "email_address": "user@example.com",  # Must specify email address
                "folder_name": "Inbox"
            },
            "filters": {
                "name": "Default Email Filter",
                "rules": [
                    {
                        "field": "has_attachments",
                        "operation": "equals",
                        "value": "true",
                        "case_sensitive": False
                    }
                ]
            },
            "monitoring": {
                "poll_interval_seconds": 60,
                "max_backlog_hours": 24,
                "error_retry_attempts": 3
            }
        }