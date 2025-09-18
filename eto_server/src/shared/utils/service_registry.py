"""
Service Registry Utility
Provides clean access to services stored in Flask app.config
"""
from typing import Optional, Any
from flask import current_app
import logging
import traceback

# Import service types for proper typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from features.pdf_processing.service import PdfProcessingService
    from features.eto_processing.service import EtoProcessingService
    from features.email_ingestion.service import EmailIngestionService
    from features.pdf_templates.service import PdfTemplateService
    from shared.database.connection import DatabaseConnectionManager
    from flask import Flask

logger = logging.getLogger(__name__)

# Global app reference for non-Flask context access
_app_instance: Optional['Flask'] = None

def initialize_service_registry(app: 'Flask') -> None:
    """Initialize service registry with Flask app reference for background thread access"""
    global _app_instance
    _app_instance = app
    logger.debug("Service registry initialized with app reference")

def _get_app_config() -> dict:
    """Get app config, trying current_app first, then fallback to stored app reference"""
    try:
        # Try current Flask context first (for normal web requests)
        return current_app.config
    except RuntimeError:
        # Fallback to stored app reference (for background threads)
        if _app_instance is not None:
            return _app_instance.config
        else:
            raise RuntimeError("No Flask app available - service registry not initialized")

# Service name constants to avoid magic strings
class ServiceNames:
    PDF_PROCESSING = 'PDF_PROCESSING_SERVICE'
    EMAIL_INGESTION = 'EMAIL_INGESTION_SERVICE'
    ETO_PROCESSING = 'ETO_PROCESSING_SERVICE'
    PDF_TEMPLATE = 'PDF_TEMPLATE_SERVICE'
    CONNECTION_MANAGER = 'CONNECTION_MANAGER'


def get_service(service_name: str) -> Optional[Any]:
    """
    Get a service from the Flask application registry.

    Args:
        service_name: Name of the service to retrieve (use ServiceNames constants)

    Returns:
        Service instance if found, None if not available

    Example:
        pdf_service = get_service(ServiceNames.PDF_PROCESSING)
        if pdf_service:
            pdf_service.process_file(file_path)
    """
    try:
        config = _get_app_config()
        service = config.get(service_name)
        if service is None:
            logger.error(f"Service '{service_name}' not found in registry")
        return service
    except RuntimeError as e:
        # No Flask app available
        logger.warning(f"Cannot access service '{service_name}' - no Flask app available")
        logger.error(f"Service registry error details: {str(e)}\nFull traceback:\n{traceback.format_exc()}")
        return None


def require_service(service_name: str) -> Any:
    """
    Get a service from the registry, raising an exception if not found.

    Args:
        service_name: Name of the service to retrieve

    Returns:
        Service instance

    Raises:
        RuntimeError: If service is not available

    Example:
        pdf_service = require_service(ServiceNames.PDF_PROCESSING)
        pdf_service.process_file(file_path)  # Safe to call - service guaranteed to exist
    """
    service = get_service(service_name)
    if service is None:
        raise RuntimeError(f"Required service '{service_name}' is not available")
    return service


def is_service_available(service_name: str) -> bool:
    """
    Check if a service is available in the registry.

    Args:
        service_name: Name of the service to check

    Returns:
        True if service is available, False otherwise
    """
    return get_service(service_name) is not None


def list_available_services() -> list[str]:
    """
    Get list of all available service names in the registry.

    Returns:
        List of service names that are currently registered
    """
    try:
        config = _get_app_config()
        service_keys = []
        for key, value in config.items():
            if key.endswith('_SERVICE') or key == 'CONNECTION_MANAGER':
                if value is not None:
                    service_keys.append(key)
        return service_keys
    except RuntimeError as e:
        logger.warning("Cannot list services - no Flask app available")
        return []


# === Type-Safe Individual Service Getters ===

def get_pdf_processing_service() -> Optional["PdfProcessingService"]:
    """Get PDF processing service with proper typing"""
    try:
        config = _get_app_config()
        return config.get('PDF_PROCESSING_SERVICE')
    except RuntimeError as e:
        logger.warning("Cannot access PDF processing service - no Flask app available")
        logger.error(f"Service registry error details: {str(e)}\nFull traceback:\n{traceback.format_exc()}")
        return None


def get_eto_processing_service() -> Optional["EtoProcessingService"]:
    """Get ETO processing service with proper typing"""
    try:
        config = _get_app_config()
        return config.get('ETO_PROCESSING_SERVICE')
    except RuntimeError:
        logger.warning("Cannot access ETO processing service - no Flask app available")
        return None


def get_email_ingestion_service() -> Optional["EmailIngestionService"]:
    """Get email ingestion service with proper typing"""
    try:
        config = _get_app_config()
        return config.get('EMAIL_INGESTION_SERVICE')
    except RuntimeError:
        logger.warning("Cannot access email ingestion service - no Flask app available")
        return None


def get_pdf_template_service() -> Optional["PdfTemplateService"]:
    """Get PDF template service with proper typing"""
    try:
        config = _get_app_config()
        return config.get('PDF_TEMPLATE_SERVICE')
    except RuntimeError:
        logger.warning("Cannot access PDF template service - no Flask app available")
        return None


def get_connection_manager() -> Optional["DatabaseConnectionManager"]:
    """Get database connection manager with proper typing"""
    try:
        config = _get_app_config()
        return config.get('CONNECTION_MANAGER')
    except RuntimeError:
        logger.warning("Cannot access connection manager - no Flask app available")
        return None