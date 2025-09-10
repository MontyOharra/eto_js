"""
Email Configuration Service
Manages email ingestion configuration with validation and admin operations
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from jsonschema import validate as json_validate, ValidationError
from dataclasses import dataclass

from ..database import get_connection_manager, EmailIngestionConfig
from ..database.repositories import EmailConfigRepository

logger = logging.getLogger(__name__)


@dataclass
class ConnectionSettings:
    """Connection settings data structure"""
    email_address: Optional[str]
    folder_name: str
    polling_interval: int = 60
    max_hours_back: int = 24


@dataclass
class FilterRule:
    """Individual filter rule data structure"""
    type: str  # 'sender', 'subject', 'attachment', 'date'
    pattern: str
    operation: str = 'contains'  # 'contains', 'equals', 'regex', 'before', 'after'


@dataclass
class FilterConfig:
    """Complete filter configuration data structure"""
    name: str
    rules: List[FilterRule]
    require_attachments: bool = True
    pdf_only: bool = True
    enabled: bool = True


@dataclass
class MonitoringSettings:
    """Monitoring and recovery settings"""
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    connection_timeout: int = 30
    health_check_interval: int = 300


@dataclass
class ConfigurationData:
    """Complete configuration data structure"""
    connection: ConnectionSettings
    filters: FilterConfig
    monitoring: MonitoringSettings
    created_at: datetime
    updated_at: datetime


class EmailConfigService:
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
                                "required": ["type", "pattern"],
                                "properties": {
                                    "type": {"type": "string", "enum": ["sender", "subject", "attachment", "date"]},
                                    "pattern": {"type": "string", "minLength": 1},
                                    "operation": {"type": "string", "enum": ["contains", "equals", "regex", "before", "after"]}
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
                        "auto_reconnect": {"type": "boolean"},
                        "max_reconnect_attempts": {"type": "integer", "minimum": 1},
                        "connection_timeout": {"type": "integer", "minimum": 5},
                        "health_check_interval": {"type": "integer", "minimum": 30}
                    }
                }
            }
        }

    # === High-Level API Methods ===
    
    def create_configuration(self, name: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new email ingestion configuration"""
        try:
            self.logger.info(f"Creating new email configuration: {name}")
            
            # Validate configuration structure  
            try:
                json_validate(config_data, self.config_schema)
                validation_result = {"valid": True}
            except ValidationError as e:
                validation_result = {"valid": False, "errors": [str(e)]}
            if not validation_result["valid"]:
                raise Exception(f"Configuration validation failed: {validation_result['errors']}")
            
            # Serialize configuration to JSON
            config_json = json.dumps(config_data, indent=2, default=str)
            
            # Create configuration record and get ID
            config_id = self.config_repo.create_and_get_id({
                "name": name,
                "filter_rules": config_json,
                "is_active": False,  # New configs start inactive
                "emails_processed": 0,
                "created_by": "api",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
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
            validation_result = self.validate_configuration_sync(config_data)
            if not validation_result["valid"]:
                raise Exception(f"Configuration validation failed: {validation_result['errors']}")
            
            # Serialize configuration to JSON
            config_json = json.dumps(config_data, indent=2, default=str)
            
            # Update configuration record
            config = self.config_repo.update(config_id, {
                "filter_rules": config_json,
                "updated_at": datetime.now(timezone.utc)
            })
            
            if not config:
                raise Exception(f"Configuration with ID {config_id} not found")
            
            # Get the name while we still have the object (though it might be detached)
            try:
                config_name = config.name
            except:
                # Fallback if name access fails due to session issues
                config_name = f"Config {config_id}"
            
            self.logger.info(f"Updated email configuration {config_name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config_name,
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
            
            # Set this configuration as active and get its name
            config_name = self.config_repo.set_config_active_and_get_name(config_id)
            
            if not config_name:
                raise Exception(f"Configuration with ID {config_id} not found")
            
            self.logger.info(f"Activated email configuration: {config_name}")
            
            return {
                "success": True,
                "config_id": config_id,
                "name": config_name,
                "message": "Configuration activated successfully"
            }
        
        except Exception as e:
            self.logger.error(f"Error activating configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to activate configuration"
            }
    
    def get_active_configuration(self) -> Optional[ConfigurationData]:
        """Get currently active email ingestion configuration"""
        try:
            config_data_raw = self.config_repo.get_active_config_data()
            
            if not config_data_raw:
                self.logger.warning("No active email configuration found")
                return None
            
            # Parse configuration JSON
            config_data = json.loads(config_data_raw["filter_rules"])
            
            return ConfigurationData(
                connection=ConnectionSettings(**config_data["connection"]),
                filters=FilterConfig(
                    name=config_data["filters"]["name"],
                    rules=[FilterRule(**rule) for rule in config_data["filters"]["rules"]],
                    require_attachments=config_data["filters"].get("require_attachments", True),
                    pdf_only=config_data["filters"].get("pdf_only", True),
                    enabled=config_data["filters"].get("enabled", True)
                ),
                monitoring=MonitoringSettings(**config_data["monitoring"]),
                created_at=config_data_raw["created_at"],
                updated_at=config_data_raw["updated_at"]
            )
        
        except Exception as e:
            self.logger.error(f"Error getting active configuration: {e}")
            return None
    
    def get_configuration(self, config_id: int) -> Optional[ConfigurationData]:
        """Get specific email ingestion configuration by ID"""
        try:
            config = self.config_repo.get_by_id(config_id)
            
            if not config:
                return None
            
            # Parse configuration JSON
            config_data = json.loads(config.filter_rules)
            
            return ConfigurationData(
                connection=ConnectionSettings(**config_data["connection"]),
                filters=FilterConfig(
                    name=config_data["filters"]["name"],
                    rules=[FilterRule(**rule) for rule in config_data["filters"]["rules"]],
                    require_attachments=config_data["filters"].get("require_attachments", True),
                    pdf_only=config_data["filters"].get("pdf_only", True),
                    enabled=config_data["filters"].get("enabled", True)
                ),
                monitoring=MonitoringSettings(**config_data["monitoring"]),
                created_at=config.created_at,
                updated_at=config.updated_at
            )
        
        except Exception as e:
            self.logger.error(f"Error getting configuration {config_id}: {e}")
            return None
    
    def list_configurations(self) -> List[Dict[str, Any]]:
        """List all email ingestion configurations with summary info"""
        try:
            configs = self.config_repo.get_all()
            
            config_summaries = []
            for config in configs:
                try:
                    # Parse basic info from JSON
                    config_data = json.loads(config.filter_rules)
                    
                    config_summaries.append({
                        "id": config.id,
                        "name": config.name,
                        "is_active": config.is_active,
                        "connection": {
                            "email_address": config_data["connection"].get("email_address"),
                            "folder_name": config_data["connection"]["folder_name"]
                        },
                        "filter_name": config_data["filters"]["name"],
                        "emails_processed": config.emails_processed,
                        "last_used_at": config.last_used_at,
                        "created_at": config.created_at,
                        "updated_at": config.updated_at
                    })
                
                except Exception as parse_error:
                    self.logger.warning(f"Error parsing config {config.id}: {parse_error}")
                    config_summaries.append({
                        "id": config.id,
                        "name": config.name,
                        "is_active": config.is_active,
                        "error": "Configuration parsing failed"
                    })
            
            return config_summaries
        
        except Exception as e:
            self.logger.error(f"Error listing configurations: {e}")
            return []
    
    async def delete_configuration(self, config_id: int) -> Dict[str, Any]:
        """Delete an email ingestion configuration"""
        try:
            self.logger.info(f"Deleting email configuration ID {config_id}")
            
            async with self.connection_manager.get_session() as session:
                # Check if configuration exists and is not active
                config = await self.config_repo.get_by_id(session, config_id)
                
                if not config:
                    raise Exception(f"Configuration with ID {config_id} not found")
                
                if config.is_active:
                    raise Exception("Cannot delete active configuration. Please activate another configuration first.")
                
                # Delete configuration
                success = await self.config_repo.delete(session, config_id)
                
                if not success:
                    raise Exception("Failed to delete configuration")
                
                self.logger.info(f"Deleted email configuration: {config.name}")
                
                return {
                    "success": True,
                    "config_id": config_id,
                    "name": config.name,
                    "message": "Configuration deleted successfully"
                }
        
        except Exception as e:
            self.logger.error(f"Error deleting configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete configuration"
            }

    # === Validation Methods ===
    
    def validate_configuration_sync(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email ingestion configuration structure and data (synchronous version)"""
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
            
            polling_interval = connection.get("polling_interval", 60)
            if polling_interval < 10:
                validation_errors.append("Polling interval must be at least 10 seconds")
            elif polling_interval < 30:
                warnings.append("Polling intervals under 30 seconds may impact performance")
            
            # Filter validation
            rules = filters.get("rules", [])
            if not rules:
                validation_errors.append("At least one filter rule is required")
            
            for i, rule in enumerate(rules):
                rule_type = rule.get("type")
                pattern = rule.get("pattern", "").strip()
                operation = rule.get("operation", "contains")
                
                if not pattern:
                    validation_errors.append(f"Rule {i+1}: Pattern cannot be empty")
                
                if rule_type == "date" and operation not in ["before", "after"]:
                    validation_errors.append(f"Rule {i+1}: Date rules must use 'before' or 'after' operation")
                
                if operation == "regex":
                    try:
                        import re
                        re.compile(pattern)
                    except re.error as regex_error:
                        validation_errors.append(f"Rule {i+1}: Invalid regex pattern: {regex_error}")
            
            # Monitoring validation
            max_attempts = monitoring.get("max_reconnect_attempts", 5)
            if max_attempts < 1:
                validation_errors.append("Max reconnect attempts must be at least 1")
            elif max_attempts > 10:
                warnings.append("High reconnect attempt values may cause extended downtime")
            
            timeout = monitoring.get("connection_timeout", 30)
            if timeout < 5:
                validation_errors.append("Connection timeout must be at least 5 seconds")
            
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
    
    async def validate_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email ingestion configuration structure and data"""
        try:
            # Schema validation
            validate(config_data, self.config_schema)
            
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
            
            polling_interval = connection.get("polling_interval", 60)
            if polling_interval < 10:
                validation_errors.append("Polling interval must be at least 10 seconds")
            elif polling_interval < 30:
                warnings.append("Polling intervals under 30 seconds may impact performance")
            
            # Filter validation
            rules = filters.get("rules", [])
            if not rules:
                validation_errors.append("At least one filter rule is required")
            
            for i, rule in enumerate(rules):
                rule_type = rule.get("type")
                pattern = rule.get("pattern", "").strip()
                operation = rule.get("operation", "contains")
                
                if not pattern:
                    validation_errors.append(f"Rule {i+1}: Pattern cannot be empty")
                
                if rule_type == "date" and operation not in ["before", "after"]:
                    validation_errors.append(f"Rule {i+1}: Date rules must use 'before' or 'after' operation")
                
                if operation == "regex":
                    try:
                        import re
                        re.compile(pattern)
                    except re.error as regex_error:
                        validation_errors.append(f"Rule {i+1}: Invalid regex pattern: {regex_error}")
            
            # Monitoring validation
            max_attempts = monitoring.get("max_reconnect_attempts", 5)
            if max_attempts < 1:
                validation_errors.append("Max reconnect attempts must be at least 1")
            elif max_attempts > 10:
                warnings.append("High reconnect attempt values may cause extended downtime")
            
            timeout = monitoring.get("connection_timeout", 30)
            if timeout < 5:
                validation_errors.append("Connection timeout must be at least 5 seconds")
            
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
    
    async def get_configuration_template(self) -> Dict[str, Any]:
        """Get a template configuration for creating new configs"""
        return {
            "connection": {
                "email_address": None,  # Use default Outlook account
                "folder_name": "Inbox",
                "polling_interval": 60,
                "max_hours_back": 24
            },
            "filters": {
                "name": "Default Email Filter",
                "rules": [
                    {
                        "type": "attachment",
                        "pattern": "*.pdf",
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
                "health_check_interval": 300
            }
        }

    # === Statistics and Health Methods ===
    
    async def get_configuration_stats(self, config_id: Optional[int] = None) -> Dict[str, Any]:
        """Get processing statistics for configuration(s)"""
        try:
            async with self.connection_manager.get_session() as session:
                if config_id:
                    # Get stats for specific configuration
                    config = await self.config_repo.get_by_id(session, config_id)
                    if not config:
                        return {"error": "Configuration not found"}
                    
                    return {
                        "config_id": config.id,
                        "name": config.name,
                        "is_active": config.is_active,
                        "emails_processed": config.emails_processed,
                        "last_used_at": config.last_used_at,
                        "created_at": config.created_at,
                        "updated_at": config.updated_at
                    }
                else:
                    # Get stats for all configurations
                    configs = await self.config_repo.get_all(session)
                    
                    stats = {
                        "total_configs": len(configs),
                        "active_configs": sum(1 for c in configs if c.is_active),
                        "total_emails_processed": sum(c.emails_processed for c in configs),
                        "configurations": []
                    }
                    
                    for config in configs:
                        stats["configurations"].append({
                            "id": config.id,
                            "name": config.name,
                            "is_active": config.is_active,
                            "emails_processed": config.emails_processed,
                            "last_used_at": config.last_used_at
                        })
                    
                    return stats
        
        except Exception as e:
            self.logger.error(f"Error getting configuration stats: {e}")
            return {"error": str(e)}