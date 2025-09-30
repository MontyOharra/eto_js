"""
Service Container - Singleton Pattern with Dependency Injection
Global service access for Transformation Pipeline Server using advanced DI container
"""
import logging
from typing import Optional
from .dependency_injection import DependencyInjectionContainer, initialize_container, get_container

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Singleton service container providing global access to all services.
    Uses advanced DI container for dependency resolution and lazy initialization.
    """
    _instance: Optional['ServiceContainer'] = None
    _services_initialized: bool = False
    _di_container: Optional[DependencyInjectionContainer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._di_container = None
            logger.info("ServiceContainer singleton instance created - services not yet initialized")
        return cls._instance

    def __init__(self):
        # __init__ is called every time, but we only want to initialize once
        pass

    def initialize(self, connection_manager):
        """
        Initialize all services with their dependencies using DI container.
        Should be called once during application startup.

        Args:
            connection_manager: Database connection manager
        """
        if ServiceContainer._services_initialized:
            logger.warning("ServiceContainer.initialize() called multiple times - ignoring")
            return

        try:
            logger.info("Starting ServiceContainer.initialize() with DI container...")

            # Initialize the DI container with all services
            self._di_container = initialize_container(connection_manager)

            # Store references for backward compatibility
            self.connection_manager = connection_manager

            logger.info("ServiceContainer initialization with DI completed successfully")
            ServiceContainer._services_initialized = True

            # Perform health checks on all services
            health_status = self._di_container.health_check()
            for service_name, is_healthy in health_status.items():
                if is_healthy:
                    logger.debug(f"Service '{service_name}' health check: OK")
                else:
                    logger.warning(f"Service '{service_name}' health check: FAILED")

        except Exception as e:
            import traceback
            logger.error(f"Failed to initialize ServiceContainer: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise

    def is_initialized(self) -> bool:
        """Check if the container has been initialized with services"""
        return ServiceContainer._services_initialized

    # === Service Getters (using DI container) ===

    @property
    def modules_service(self):
        """Get modules service via lazy loading from DI container"""
        if not self._di_container:
            raise RuntimeError("ServiceContainer not initialized - call initialize() first")
        return self._di_container.resolve('modules')

    def get_modules_service(self):
        """Get modules service - guaranteed to return valid service or crash"""
        return self.modules_service

    def get_connection_manager(self):
        """Get database connection manager - guaranteed to return valid manager or crash"""
        if not self.connection_manager:
            logger.error("Connection manager not initialized - ServiceContainer.initialize() was not called")
            raise RuntimeError("Database connection manager not available - application initialization failed")
        return self.connection_manager

    @classmethod
    def reset(cls):
        """Reset the service container (primarily for testing)"""
        cls._instance = None
        cls._services_initialized = False
        logger.info("ServiceContainer reset")


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


def get_modules_service():
    """Get modules service - global access function"""
    return _get_container().get_modules_service()


def get_connection_manager():
    """Get database connection manager - global access function"""
    return _get_container().get_connection_manager()


def is_service_container_initialized() -> bool:
    """Check if the service container has been initialized"""
    return ServiceContainer._services_initialized


def initialize_services(connection_manager):
    """Initialize all services - call during application startup"""
    container = _get_container()
    container.initialize(connection_manager)
    return container


def reset_service_container():
    """Reset the service container - for testing purposes"""
    global _service_container_instance
    _service_container_instance = None
    ServiceContainer.reset()
    logger.info("Global service container reset")