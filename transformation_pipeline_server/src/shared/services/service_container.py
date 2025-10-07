"""
Service Container - Simplified Singleton Pattern with Lazy Loading
Handles service dependencies and circular references elegantly
"""
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from features.modules.service import ModulesService
    from features.pipeline import PipelineService
    from shared.database.connection import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class ServiceProxy:
    """
    Proxy to handle service dependencies including potential circular references.
    Delays service resolution until the service is actually accessed.
    """
    def __init__(self, container: 'ServiceContainer', service_name: str):
        self._container = container
        self._service_name = service_name
        self._resolved = None

    def __getattr__(self, name):
        # Resolve the actual service when first accessed
        if self._resolved is None:
            self._resolved = self._container.get(self._service_name)
        return getattr(self._resolved, name)

    def __repr__(self):
        return f"<ServiceProxy for '{self._service_name}'>"


class ServiceContainer:
    """
    Singleton service container with lazy loading and dependency injection.

    Features:
    - True singleton pattern (single instance across entire application)
    - Lazy service instantiation (created only when first accessed)
    - Support for service-to-service dependencies
    - Circular dependency support via ServiceProxy
    - Single place for all service definitions
    - Simple API similar to database connection manager
    """

    _instance: Optional['ServiceContainer'] = None
    _initialized: bool = False
    _services: Dict[str, Any] = {}  # Cache for instantiated services
    _service_definitions: Dict[str, Dict[str, Any]] = {}  # Service configurations
    _connection_manager = None
    _resolving: List[str] = []  # Track services being resolved to detect circular deps

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._service_definitions = {}
            cls._instance._resolving = []
            logger.info("ServiceContainer singleton instance created")
        return cls._instance

    @classmethod
    def initialize(cls, connection_manager, **kwargs):
        """
        Initialize the service container with required dependencies.
        Can be called multiple times safely (will only initialize once).

        Args:
            connection_manager: Database connection manager
            **kwargs: Additional configuration parameters

        Returns:
            ServiceContainer: The singleton instance
        """
        instance = cls()

        if cls._initialized:
            logger.warning("ServiceContainer already initialized - returning existing instance")
            return instance

        # Store core dependencies
        instance._connection_manager = connection_manager

        # Store any additional configuration
        for key, value in kwargs.items():
            setattr(instance, f"_{key}", value)

        # Register all service definitions
        instance._register_service_definitions()

        cls._initialized = True
        logger.info("ServiceContainer initialized successfully")

        return instance

    def _register_service_definitions(self):
        """
        Single place to define all services and their dependencies.
        This is the ONLY place where services need to be defined.
        """
        self._service_definitions = {
            'modules': {
                'class': 'features.modules.service.ModulesService',
                'args': [self._connection_manager],  # Direct args, not names
                'singleton': True,
                'description': 'Module management and execution service'
            },
            'pipeline': {
                'class': 'features.pipeline.PipelineService',
                'args': [self._connection_manager],
                'singleton': True,
                'description': 'Pipeline creation and management service'
            },
            # Add more services here as needed
            # Example with service dependencies:
            # 'compiler': {
            #     'class': 'features.pipeline.compilation.CompilerService',
            #     'args': ['_service:modules', self._connection_manager],
            #     'singleton': True
            # }
        }

        logger.debug(f"Registered {len(self._service_definitions)} service definitions")

    def get(self, service_name: str) -> Any:
        """
        Get a service by name, creating it lazily if needed.

        Args:
            service_name: The name of the service to retrieve

        Returns:
            The service instance

        Raises:
            ValueError: If service is not registered
            RuntimeError: If circular dependency is detected
        """
        # Return cached instance if available
        if service_name in self._services:
            logger.debug(f"Returning cached service '{service_name}'")
            return self._services[service_name]

        # Check if service is registered
        if service_name not in self._service_definitions:
            available = ', '.join(self._service_definitions.keys())
            raise ValueError(f"Service '{service_name}' not registered. Available: {available}")

        # Check for circular dependencies
        if service_name in self._resolving:
            cycle = ' -> '.join(self._resolving) + f' -> {service_name}'
            raise RuntimeError(f"Circular dependency detected: {cycle}")

        # Create the service
        self._resolving.append(service_name)
        try:
            service = self._create_service(service_name)

            # Cache if singleton
            if self._service_definitions[service_name].get('singleton', True):
                self._services[service_name] = service
                logger.info(f"Created and cached singleton service '{service_name}'")
            else:
                logger.debug(f"Created transient service '{service_name}'")

            return service
        finally:
            self._resolving.remove(service_name)

    def _create_service(self, service_name: str) -> Any:
        """
        Create a service instance with dependency resolution.

        Args:
            service_name: The name of the service to create

        Returns:
            The created service instance
        """
        definition = self._service_definitions[service_name]

        # Import the class dynamically
        module_path, class_name = definition['class'].rsplit('.', 1)
        try:
            # Handle both absolute and relative imports
            if module_path.startswith('.'):
                # Relative import
                from importlib import import_module
                module = import_module(module_path, package='src')
            else:
                # Absolute import
                module = __import__(f'src.{module_path}', fromlist=[class_name])

            service_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import service class {definition['class']}: {e}")
            raise RuntimeError(f"Cannot create service '{service_name}': {e}")

        # Resolve arguments
        resolved_args = []
        for arg in definition.get('args', []):
            if isinstance(arg, str) and arg.startswith('_service:'):
                # This is a service dependency
                dep_service_name = arg.replace('_service:', '')
                # Use ServiceProxy for lazy resolution
                resolved_args.append(ServiceProxy(self, dep_service_name))
            else:
                # Direct argument (like connection_manager)
                resolved_args.append(arg)

        # Create the service instance
        try:
            service = service_class(*resolved_args)
            logger.debug(f"Successfully created service '{service_name}'")
            return service
        except Exception as e:
            logger.error(f"Failed to create service '{service_name}': {e}")
            raise RuntimeError(f"Cannot create service '{service_name}': {e}")

    def is_initialized(self) -> bool:
        """Check if the container has been initialized"""
        return ServiceContainer._initialized

    def reset(self):
        """
        Reset the service container (primarily for testing).
        Clears all cached services and marks as uninitialized.
        """
        ServiceContainer._instance = None
        ServiceContainer._initialized = False
        logger.info("ServiceContainer reset")

    # === Convenience Methods ===
    # These provide direct access to commonly used services

    def get_modules_service(self) -> 'ModulesService':
        """Get the modules service"""
        return self.get('modules')

    def get_pipeline_service(self) -> 'PipelineService':
        """Get the pipeline service"""
        return self.get('pipeline')

    def get_connection_manager(self) -> 'DatabaseConnectionManager':
        """Get the database connection manager"""
        if not self._connection_manager:
            raise RuntimeError("Connection manager not available - ServiceContainer not initialized")
        return self._connection_manager

    def get_all_services(self) -> List[str]:
        """Get names of all registered services"""
        return list(self._service_definitions.keys())

    def get_cached_services(self) -> List[str]:
        """Get names of all currently cached services"""
        return list(self._services.keys())

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all cached services.
        Only checks services that have been instantiated.

        Returns:
            Dict mapping service names to health status
        """
        health_status = {}

        for name, service in self._services.items():
            try:
                # Check if service has is_healthy method
                if hasattr(service, 'is_healthy') and callable(service.is_healthy):
                    health_status[name] = service.is_healthy()
                else:
                    # Assume healthy if no health check method
                    health_status[name] = True
            except Exception as e:
                logger.error(f"Health check failed for service '{name}': {e}")
                health_status[name] = False

        return health_status


# === Global Access Functions ===
# These provide a simple API similar to the database connection manager pattern

_container: Optional[ServiceContainer] = None


def initialize_services(connection_manager, **kwargs) -> ServiceContainer:
    """
    Initialize the global service container.
    Safe to call multiple times (will only initialize once).

    Args:
        connection_manager: Database connection manager
        **kwargs: Additional configuration parameters

    Returns:
        ServiceContainer: The initialized container
    """
    global _container
    logger.debug(f"initialize_services called, _container before: {_container}")
    logger.debug(f"_container id before: {id(_container) if _container else 'None'}")

    # Use the class method to get or create and initialize the singleton
    _container = ServiceContainer.initialize(connection_manager, **kwargs)

    logger.debug(f"initialize_services done, _container after: {_container}")
    logger.debug(f"_container id after: {id(_container) if _container else 'None'}")
    logger.info(f"Global _container set to instance ID: {id(_container)}")

    return _container


def get_service_container() -> ServiceContainer:
    """
    Get the global service container instance.

    Returns:
        ServiceContainer: The singleton instance

    Raises:
        RuntimeError: If container is not initialized
    """
    # Instead of relying on module-level _container, use the singleton instance
    if ServiceContainer._instance is None or not ServiceContainer._initialized:
        logger.error("ServiceContainer._instance is None or not initialized!")
        raise RuntimeError(
            "Service container not initialized. "
            "Call initialize_services() first."
        )

    logger.debug(f"get_service_container returning instance ID: {id(ServiceContainer._instance)}")
    return ServiceContainer._instance


def get_modules_service() -> 'ModulesService':
    """Convenience function to get modules service directly"""
    return get_service_container().get_modules_service()


def get_pipeline_service() -> 'PipelineService':
    """Convenience function to get pipeline service directly"""
    return get_service_container().get_pipeline_service()


def get_connection_manager() -> 'DatabaseConnectionManager':
    """Convenience function to get connection manager directly"""
    return get_service_container().get_connection_manager()


def is_service_container_initialized() -> bool:
    """Check if the service container has been initialized"""
    return ServiceContainer._instance is not None and ServiceContainer._initialized


def reset_service_container():
    """Reset the service container (for testing)"""
    global _container
    if _container:
        _container.reset()
    _container = None
    logger.info("Global service container reset")