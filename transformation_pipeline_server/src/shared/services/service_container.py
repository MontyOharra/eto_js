"""
Service Container - Pure Class-Based Singleton Pattern
Handles service dependencies and circular references elegantly
"""
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from features.modules.service import ModulesService
    from features.pipeline import PipelineService
    from features.pipeline_execution.service import PipelineExecutionService
    from shared.utils.registry import ModuleRegistry
    from shared.database.connection import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class ServiceProxy:
    """
    Proxy to handle service dependencies including potential circular references.
    Delays service resolution until the service is actually accessed.
    """
    def __init__(self, service_name: str):
        self._service_name = service_name
        self._resolved = None

    def __getattr__(self, name):
        # Resolve the actual service when first accessed
        if self._resolved is None:
            self._resolved = ServiceContainer.get(self._service_name)
        return getattr(self._resolved, name)

    def __repr__(self):
        return f"<ServiceProxy for '{self._service_name}'>"


class ServiceContainer:
    """
    Pure class-based singleton service container.

    The class itself IS the singleton - no instances are created.
    All access is through class methods.

    Features:
    - Class acts as singleton (no instance creation)
    - Lazy service instantiation
    - Support for service-to-service dependencies
    - Circular dependency support via ServiceProxy
    - Single place for all service definitions
    """

    # Class-level state - shared across all imports
    _initialized: bool = False
    _services: Dict[str, Any] = {}
    _service_definitions: Dict[str, Dict[str, Any]] = {}
    _connection_manager: Optional['DatabaseConnectionManager'] = None
    _resolving: List[str] = []

    @classmethod
    def initialize(cls, connection_manager: 'DatabaseConnectionManager', **kwargs) -> None:
        """
        Initialize the service container.
        Can be called multiple times safely (will only initialize once).

        Args:
            connection_manager: Database connection manager
            **kwargs: Additional configuration parameters
        """
        if cls._initialized:
            logger.warning("ServiceContainer already initialized")
            return

        logger.info("Initializing ServiceContainer...")

        # Store core dependencies
        cls._connection_manager = connection_manager

        # Store any additional configuration
        for key, value in kwargs.items():
            setattr(cls, f"_{key}", value)

        # Register all service definitions
        cls._register_service_definitions()

        cls._initialized = True
        logger.info("ServiceContainer initialized successfully")

    @classmethod
    def _register_service_definitions(cls) -> None:
        """
        Single place to define all services and their dependencies.
        """
        cls._service_definitions = {
            'modules': {
                'class': 'features.modules.service.ModulesService',
                'args': [cls._connection_manager],
                'singleton': True,
                'description': 'Module management and execution service'
            },
            'pipeline': {
                'class': 'features.pipeline.PipelineService',
                'args': [cls._connection_manager],
                'singleton': True,
                'description': 'Pipeline creation and management service'
            },
            'module_registry': {
                'class': 'shared.utils.registry.ModuleRegistry',
                'args': [],
                'singleton': True,
                'description': 'Module handler registry'
            },
            'pipeline_execution': {
                'class': 'features.pipeline_execution.service.PipelineExecutionService',
                'args': [cls._connection_manager, '_service:module_registry'],
                'singleton': True,
                'description': 'Pipeline execution service with Dask orchestration'
            },
            # Add more services here as needed
        }

        logger.debug(f"Registered {len(cls._service_definitions)} service definitions")

    @classmethod
    def get(cls, service_name: str) -> Any:
        """
        Get a service by name, creating it lazily if needed.

        Args:
            service_name: The name of the service to retrieve

        Returns:
            The service instance

        Raises:
            RuntimeError: If not initialized
            ValueError: If service is not registered
        """
        logger.debug(f"ServiceContainer.get called for '{service_name}'")
        logger.debug(f"Class ID: {id(cls)}, _initialized: {cls._initialized}")

        if not cls._initialized:
            logger.error(f"ServiceContainer not initialized! Class ID: {id(cls)}")
            raise RuntimeError("ServiceContainer not initialized. Call ServiceContainer.initialize() first.")

        # Return cached instance if available
        if service_name in cls._services:
            logger.debug(f"Returning cached service '{service_name}'")
            return cls._services[service_name]

        # Check if service is registered
        if service_name not in cls._service_definitions:
            available = ', '.join(cls._service_definitions.keys())
            raise ValueError(f"Service '{service_name}' not registered. Available: {available}")

        # Check for circular dependencies
        if service_name in cls._resolving:
            cycle = ' -> '.join(cls._resolving) + f' -> {service_name}'
            raise RuntimeError(f"Circular dependency detected: {cycle}")

        # Create the service
        cls._resolving.append(service_name)
        try:
            service = cls._create_service(service_name)

            # Cache if singleton
            if cls._service_definitions[service_name].get('singleton', True):
                cls._services[service_name] = service
                logger.info(f"Created and cached singleton service '{service_name}'")
            else:
                logger.debug(f"Created transient service '{service_name}'")

            return service
        finally:
            cls._resolving.remove(service_name)

    @classmethod
    def _create_service(cls, service_name: str) -> Any:
        """
        Create a service instance with dependency resolution.
        """
        definition = cls._service_definitions[service_name]

        # Import the class dynamically
        module_path, class_name = definition['class'].rsplit('.', 1)
        try:
            # Handle both absolute and relative imports
            if module_path.startswith('.'):
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
                resolved_args.append(ServiceProxy(dep_service_name))
            else:
                # Direct argument
                resolved_args.append(arg)

        # Create the service instance
        try:
            service = service_class(*resolved_args)
            logger.debug(f"Successfully created service '{service_name}'")
            return service
        except Exception as e:
            logger.error(f"Failed to create service '{service_name}': {e}")
            raise RuntimeError(f"Cannot create service '{service_name}': {e}")

    # === Convenience Methods ===

    @classmethod
    def get_modules_service(cls) -> 'ModulesService':
        """Get the modules service"""
        return cls.get('modules')

    @classmethod
    def get_pipeline_service(cls) -> 'PipelineService':
        """Get the pipeline service"""
        return cls.get('pipeline')

    @classmethod
    def get_pipeline_execution_service(cls) -> 'PipelineExecutionService':
        """Get the pipeline execution service"""
        return cls.get('pipeline_execution')

    @classmethod
    def get_module_registry(cls) -> 'ModuleRegistry':
        """Get the module registry"""
        return cls.get('module_registry')

    @classmethod
    def get_connection_manager(cls) -> 'DatabaseConnectionManager':
        """Get the database connection manager"""
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")
        if not cls._connection_manager:
            raise RuntimeError("Connection manager not available")
        return cls._connection_manager

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the container has been initialized"""
        return cls._initialized

    @classmethod
    def reset(cls) -> None:
        """
        Reset the service container (primarily for testing).
        Clears all cached services and marks as uninitialized.
        """
        cls._initialized = False
        cls._services = {}
        cls._service_definitions = {}
        cls._connection_manager = None
        cls._resolving = []
        logger.info("ServiceContainer reset")

    @classmethod
    def get_all_services(cls) -> List[str]:
        """Get names of all registered services"""
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")
        return list(cls._service_definitions.keys())

    @classmethod
    def get_cached_services(cls) -> List[str]:
        """Get names of all currently cached services"""
        return list(cls._services.keys())

    @classmethod
    def health_check(cls) -> Dict[str, bool]:
        """
        Check health of all cached services.
        Only checks services that have been instantiated.
        """
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")

        health_status = {}

        for name, service in cls._services.items():
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