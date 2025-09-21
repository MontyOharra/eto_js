"""
Service Container - Singleton Pattern
Global service access without Flask dependency
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Singleton service container providing global access to all services.
    Services are initialized once and can be accessed from anywhere without Flask context.
    """
    _instance: Optional['ServiceContainer'] = None
    _services_initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize all service references to None
            cls._instance.connection_manager = None
            cls._instance.pdf_service = None
            cls._instance.email_service = None
            cls._instance.eto_service = None
            cls._instance.pdf_template_service = None
            cls._instance.email_config_service = None
            logger.info("ServiceContainer singleton instance created - services not yet initialized")
        return cls._instance

    def __init__(self):
        # __init__ is called every time, but we only want to initialize once
        pass

    def initialize(self, connection_manager, pdf_storage_path: str):
        """
        Initialize all services with their dependencies.
        Should be called once during application startup.

        Args:
            connection_manager: Database connection manager
            pdf_storage_path: Path for PDF file storage
        """
        if ServiceContainer._services_initialized:
            logger.warning("ServiceContainer.initialize() called multiple times - ignoring")
            return

        try:
            logger.info("Starting ServiceContainer.initialize() - initializing all services...")

            # Store connection manager
            self.connection_manager = connection_manager
            logger.info(f"Connection manager stored: {type(connection_manager)}")

            # Import services here to avoid circular imports
            from features.pdf_processing import PdfProcessingService
            from features.email_ingestion.service import EmailIngestionService
            from features.email_ingestion.config_service import EmailIngestionConfigService
            from features.eto_processing import EtoProcessingService
            from features.pdf_templates.service import PdfTemplateService
            from shared.database.repositories import EmailIngestionConfigRepository

            # Initialize PDF service first (other services may depend on it)
            self.pdf_service = PdfProcessingService(pdf_storage_path, connection_manager)
            logger.debug("PDF processing service initialized")

            # Initialize PDF template service
            self.pdf_template_service = PdfTemplateService(connection_manager)
            logger.debug("PDF template service initialized")

            # Initialize email ingestion service
            self.email_service = EmailIngestionService(connection_manager)
            logger.debug("Email ingestion service initialized")
            
            # Initialize email config service
            email_config_repo = EmailIngestionConfigRepository(connection_manager)
            self.email_config_service = EmailIngestionConfigService(email_config_repo)
            logger.debug("Email config service initialized")
        
            # Initialize ETO processing service
            self.eto_service = EtoProcessingService(connection_manager)
            logger.debug("ETO processing service initialized")

            logger.info("ServiceContainer initialization completed successfully")
            ServiceContainer._services_initialized = True

        except Exception as e:
            import traceback
            logger.error(f"Failed to initialize ServiceContainer: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise

    def is_initialized(self) -> bool:
        """Check if the container has been initialized with services"""
        return ServiceContainer._services_initialized

    # === Service Getters ===

    def get_pdf_service(self):
        """Get PDF processing service - guaranteed to return valid service or crash"""
        if not self.pdf_service:
            logger.error(f"PDF service not initialized - ServiceContainer.initialize() was not called")
            logger.error(f"ServiceContainer state: pdf_service={self.pdf_service}, connection_manager={self.connection_manager}")
            logger.error(f"ServiceContainer._services_initialized={ServiceContainer._services_initialized}")
            logger.error(f"ServiceContainer instance ID: {id(self)}")
            raise RuntimeError("PDF processing service not available - application initialization failed")
        return self.pdf_service

    def get_email_service(self):
        """Get email ingestion service - guaranteed to return valid service or crash"""
        if not self.email_service:
            logger.error("Email service not initialized - ServiceContainer.initialize() was not called")
            raise RuntimeError("Email ingestion service not available - application initialization failed")
        return self.email_service

    def get_eto_service(self):
        """Get ETO processing service - guaranteed to return valid service or crash"""
        if not self.eto_service:
            logger.error("ETO service not initialized - ServiceContainer.initialize() was not called")
            raise RuntimeError("ETO processing service not available - application initialization failed")
        return self.eto_service

    def get_connection_manager(self):
        """Get database connection manager - guaranteed to return valid manager or crash"""
        if not self.connection_manager:
            logger.error("Connection manager not initialized - ServiceContainer.initialize() was not called")
            raise RuntimeError("Database connection manager not available - application initialization failed")
        return self.connection_manager

    def get_pdf_template_service(self):
        """Get PDF template service - guaranteed to return valid service or crash"""
        if not self.pdf_template_service:
            logger.error("PDF template service not initialized - ServiceContainer.initialize() was not called")
            raise RuntimeError("PDF template service not available - application initialization failed")
        return self.pdf_template_service
    
    def get_email_config_service(self):
        """Get email config service - guaranteed to return valid service or crash"""
        if not self.email_config_service:
            logger.error("Email config service not initialized - ServiceContainer.initialize() was not called")
            raise RuntimeError("Email config service not available - application initialization failed")
        return self.email_config_service


# === Global Service Access Functions ===
# These provide the same interface as the old service registry

# Store singleton instance at module level to ensure consistency
_service_container_instance = None

def _get_container():
    """Get the singleton container instance"""
    global _service_container_instance
    if _service_container_instance is None:
        logger.info("Creating new ServiceContainer instance via _get_container()")
        _service_container_instance = ServiceContainer()
        logger.info(f"_get_container() created instance ID: {id(_service_container_instance)}")
    else:
        logger.debug(f"_get_container() returning existing instance ID: {id(_service_container_instance)}")
    return _service_container_instance


def get_pdf_processing_service():
    """Get PDF processing service - global access function"""
    return _get_container().get_pdf_service()


def get_email_ingestion_service():
    """Get email ingestion service - global access function"""
    return _get_container().get_email_service()


def get_eto_processing_service():
    """Get ETO processing service - global access function"""
    return _get_container().get_eto_service()


def get_connection_manager():
    """Get database connection manager - global access function"""
    return _get_container().get_connection_manager()


def get_pdf_template_service():
    """Get PDF template service - global access function"""
    return _get_container().get_pdf_template_service()


def get_email_config_service():
    """Get email config service - global access function"""
    return _get_container().get_email_config_service()


def is_service_container_initialized() -> bool:
    """Check if the service container has been initialized"""
    return _get_container().is_initialized()