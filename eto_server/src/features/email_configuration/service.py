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
from ...shared.database import get_connection_manager, EmailIngestionConfigModel
from ...shared.database.repositories import EmailConfigRepository

logger = logging.getLogger(__name__)


class EmailConfigurationService:
    """Manages email ingestion configuration with validation and admin operations"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
        assert self.connection_manager is not None
        
        self.config_repo = EmailConfigRepository(self.connection_manager)
        self.logger = logging.getLogger(__name__)
        
        # JSON schema for configuration validation
        self.config_schema = {
            "type": "object",
            "required": ["connection", "filters", "monitoring"],
            "properties": {
                "connection": {
                    "type": "object",
                    "required": ["folder_name"],
                    "properties": {
                        "email_address": {"type": ["string", "null"]},
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
            self.logger.error(f"Error creating configuration: {e}")
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
            
            self.logger.info(f"Updated email configuration {config.name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config.name,
                "message": "Configuration updated successfully"
            }
        
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
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
            
            self.logger.info(f"Activated email configuration: {config.name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config.name,
                "message": "Configuration activated successfully"
            }
        
        except Exception as e:
            self.logger.error(f"Error activating configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to activate configuration"
            }
    
    def get_active_configuration(self) -> Optional[EmailIngestionConfig]:
        """Get currently active email ingestion configuration as domain object"""
        try:
            config_model = self.config_repo.get_active_config()
            
            if not config_model:
                self.logger.warning("No active email configuration found")
                return None
            
            return self._convert_to_domain_object(config_model)
        
        except Exception as e:
            self.logger.error(f"Error getting active configuration: {e}")
            return None
    
    def get_configuration(self, config_id: int) -> Optional[EmailIngestionConfig]:
        """Get specific email ingestion configuration by ID as domain object"""
        try:
            config_model = self.config_repo.get_by_id(config_id)
            
            if not config_model:
                return None
            
            return self._convert_to_domain_object(config_model)
        
        except Exception as e:
            self.logger.error(f"Error getting configuration {config_id}: {e}")
            return None
    
    def list_configurations(self, order_by: Optional[str] = None, desc: bool = False) -> List[EmailConfigSummary]:
        """List all email ingestion configurations with summary info"""
        try:
            if order_by:
                configs = self.config_repo.get_all(order_by=order_by, desc=desc)
            else:
                configs = self.config_repo.get_all_configs()
            
            return [
                EmailConfigSummary(
                    id=config.id,
                    name=config.name,
                    folder_name=config.folder_name,
                    is_active=config.is_active,
                    is_running=config.is_running,
                    emails_processed=config.emails_processed,
                    pdfs_found=config.pdfs_found,
                    last_used_at=config.last_used_at
                )
                for config in configs
            ]
        
        except Exception as e:
            self.logger.error(f"Error listing configurations: {e}")
            return []
    
    def delete_configuration(self, config_id: int) -> Dict[str, Any]:
        """Delete an email ingestion configuration"""
        try:
            self.logger.info(f"Deleting email configuration ID {config_id}")
            
            # Check if configuration exists and is not active
            config = self.config_repo.get_by_id(config_id)
            
            if not config:
                raise Exception(f"Configuration with ID {config_id} not found")
            
            if config.is_active:
                raise Exception("Cannot delete active configuration. Please activate another configuration first.")
            
            config_name = config.name  # Store name before deletion
            
            # Delete configuration
            success = self.config_repo.delete(config_id)
            
            if not success:
                raise Exception("Failed to delete configuration")
            
            self.logger.info(f"Deleted email configuration: {config_name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config_name,
                "message": "Configuration deleted successfully"
            }
        
        except Exception as e:
            self.logger.error(f"Error deleting configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete configuration"
            }

    # === Helper Methods ===
    
    def _convert_to_domain_object(self, config_model: EmailIngestionConfigModel) -> EmailIngestionConfig:
        """Convert database model to domain object"""
        # Parse filter rules from JSON
        filter_rules_data = json.loads(config_model.filter_rules)
        filter_rules = [
            EmailFilterRule(
                field=rule["field"],
                operation=rule["operation"],
                value=rule["value"],
                case_sensitive=rule.get("case_sensitive", False)
            )
            for rule in filter_rules_data
        ]
        
        return EmailIngestionConfig(
            id=config_model.id,
            name=config_model.name,
            description=config_model.description,
            email_address=config_model.email_address,
            folder_name=config_model.folder_name,
            filter_rules=filter_rules,
            poll_interval_seconds=config_model.poll_interval_seconds,
            max_backlog_hours=config_model.max_backlog_hours,
            error_retry_attempts=config_model.error_retry_attempts,
            is_active=config_model.is_active,
            is_running=config_model.is_running,
            created_by=config_model.created_by,
            created_at=config_model.created_at,
            updated_at=config_model.updated_at,
            last_used_at=config_model.last_used_at,
            emails_processed=config_model.emails_processed,
            pdfs_found=config_model.pdfs_found,
            last_error_message=config_model.last_error_message,
            last_error_at=config_model.last_error_at
        )

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
            self.logger.error(f"Error validating configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    def get_configuration_template(self) -> Dict[str, Any]:
        """Get a template configuration for creating new configs"""
        return {
            "connection": {
                "email_address": None,  # Use default Outlook account
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