"""
Service Container - Pure Class-Based Singleton Pattern
Handles service dependencies and circular references elegantly
"""
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from features.modules.service import ModulesService
    from features.email_configs.service import EmailConfigService
    from features.email_ingestion.service import EmailIngestionService
    from features.pdf_files.service import PdfFilesService
    from features.pdf_templates.service import PdfTemplateService
    from features.pipelines.service import PipelineService
    from features.pipeline_execution.service import PipelineExecutionService
    from features.eto_runs.service import EtoRunsService
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
    _connection_manager: Optional['DatabaseConnectionManager'] = None  # Primary 'main' connection
    _connection_managers: Dict[str, 'DatabaseConnectionManager'] = {}  # All named connections
    _pdf_storage_path: Optional[str] = None
    _resolving: List[str] = []

    @classmethod
    def initialize(cls, connection_manager: 'DatabaseConnectionManager', pdf_storage_path: str, connection_managers: Optional[Dict[str, 'DatabaseConnectionManager']] = None, **kwargs) -> None:
        """
        Initialize the service container.
        Can be called multiple times safely (will only initialize once).

        Args:
            connection_manager: Primary database connection manager (backward compatibility)
            pdf_storage_path: Path for PDF file storage
            connection_managers: Optional dict of named database connection managers
                                 e.g., {'main': manager1, 'orders_db': manager2}
            **kwargs: Additional configuration parameters
        """
        if cls._initialized:
            logger.warning("ServiceContainer already initialized")
            return

        logger.info("Initializing ServiceContainer...")

        # Store core dependencies
        cls._connection_manager = connection_manager
        cls._pdf_storage_path = pdf_storage_path

        # Store all connection managers
        if connection_managers:
            cls._connection_managers = connection_managers
            logger.info(f"Registered {len(connection_managers)} database connections: {', '.join(connection_managers.keys())}")
        else:
            # If not provided, just register the main connection manager
            cls._connection_managers = {'main': connection_manager}
            logger.info("Registered single 'main' database connection")

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
            'storage_config': {
                'factory': 'shared.config.storage.StorageConfig.from_environment',
                'args': [],
                'singleton': True,
                'description': 'Storage configuration (filesystem paths)'
            },
            'modules': {
                'class': 'features.modules.service.ModulesService',
                'args': [cls._connection_manager],
                'singleton': True,
                'description': 'Module catalog and auto-discovery service'
            },
            'pdf_files': {
                'class': 'features.pdf_files.service.PdfFilesService',
                'args': [cls._connection_manager, '_service:storage_config'],
                'singleton': True,
                'description': 'PDF files service with extraction and storage'
            },
            'email_ingestion': {
                'class': 'features.email_ingestion.service.EmailIngestionService',
                'args': [cls._connection_manager, '_service:pdf_files', '_service:eto_runs'],
                'singleton': True,
                'description': 'Email ingestion service with PDF processing and ETO integration'
            },
            'email_configs': {
                'class': 'features.email_configs.service.EmailConfigService',
                'args': [cls._connection_manager, '_service:email_ingestion'],
                'singleton': True,
                'description': 'Email configuration management service'
            },
            'pipeline_execution': {
                'class': 'features.pipeline_execution.service.PipelineExecutionService',
                'args': [cls._connection_manager],
                'singleton': True,
                'description': 'Pipeline execution service for running compiled pipelines'
            },
            'pipelines': {
                'class': 'features.pipelines.service.PipelineService',
                'args': [cls._connection_manager, '_service:pipeline_execution'],
                'singleton': True,
                'description': 'Pipeline compilation and execution service'
            },
            'pdf_templates': {
                'class': 'features.pdf_templates.service.PdfTemplateService',
                'args': [cls._connection_manager, '_service:pipelines', '_service:pdf_files', '_service:pipeline_execution'],
                'singleton': True,
                'description': 'PDF template service with versioning and pipeline integration'
            },
            'eto_runs': {
                'class': 'features.eto_runs.service.EtoRunsService',
                'args': [cls._connection_manager, '_service:pdf_templates', '_service:pdf_files', '_service:pipeline_execution'],
                'singleton': True,
                'description': 'ETO runs service for processing lifecycle management'
            },
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
        Supports both 'class' (constructor) and 'factory' (function) patterns.
        """
        definition = cls._service_definitions[service_name]

        # Check if this is a factory function or a class constructor
        if 'factory' in definition:
            # Factory pattern - call a function to get the service
            # Supports both module.function and module.Class.method patterns
            factory_path = definition['factory']
            parts = factory_path.split('.')

            try:
                # Try module.Class.method pattern first (3+ parts)
                # For 'shared.config.storage.StorageConfig.from_environment':
                # - module: 'shared.config.storage'
                # - class: 'StorageConfig'
                # - method: 'from_environment'
                if len(parts) >= 3:
                    # Try importing as module.Class.method
                    module_path = '.'.join(parts[:-2])  # 'shared.config.storage'
                    class_name = parts[-2]  # 'StorageConfig'
                    method_name = parts[-1]  # 'from_environment'

                    try:
                        # Import the module
                        module = __import__(f'src.{module_path}', fromlist=[class_name])
                        # Get the class
                        factory_class = getattr(module, class_name)
                        # Get the method from the class
                        factory_func = getattr(factory_class, method_name)
                    except (ImportError, AttributeError):
                        # Fall back to module.function pattern
                        module_path, function_name = factory_path.rsplit('.', 1)
                        module = __import__(f'src.{module_path}', fromlist=[function_name])
                        factory_func = getattr(module, function_name)
                else:
                    # module.function pattern
                    module_path, function_name = factory_path.rsplit('.', 1)
                    module = __import__(f'src.{module_path}', fromlist=[function_name])
                    factory_func = getattr(module, function_name)

            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to import factory function {factory_path}: {e}")
                raise RuntimeError(f"Cannot create service '{service_name}': {e}")

            # Resolve arguments
            resolved_args = []
            for arg in definition.get('args', []):
                if isinstance(arg, str) and arg.startswith('_service:'):
                    dep_service_name = arg.replace('_service:', '')
                    resolved_args.append(ServiceProxy(dep_service_name))
                else:
                    resolved_args.append(arg)

            # Call factory function
            try:
                service = factory_func(*resolved_args)
                logger.debug(f"Successfully created service '{service_name}' via factory")
                return service
            except Exception as e:
                logger.error(f"Failed to create service '{service_name}' via factory: {e}")
                raise RuntimeError(f"Cannot create service '{service_name}': {e}")

        else:
            # Class constructor pattern
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

                # Post-creation hook: inject ServiceContainer reference for specific services
                if service_name == 'pipeline_execution' and hasattr(service, 'services'):
                    service.services = cls
                    logger.debug(f"Injected ServiceContainer reference into '{service_name}'")

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
    def get_email_config_service(cls) -> 'EmailConfigService':
        """Get the email config service"""
        return cls.get('email_configs')

    @classmethod
    def get_email_ingestion_service(cls) -> 'EmailIngestionService':
        """Get the email ingestion service"""
        return cls.get('email_ingestion')

    @classmethod
    def get_pdf_files_service(cls) -> 'PdfFilesService':
        """Get the PDF processing service"""
        return cls.get('pdf_files')

    @classmethod
    def get_pdf_template_service(cls) -> 'PdfTemplateService':
        """Get the PDF template service"""
        return cls.get('pdf_templates')

    @classmethod
    def get_pipeline_service(cls) -> 'PipelineService':
        """Get the pipeline service"""
        return cls.get('pipelines')

    @classmethod
    def get_pipeline_execution_service(cls) -> 'PipelineExecutionService':
        """Get the pipeline execution service"""
        return cls.get('pipeline_execution')

    @classmethod
    def get_eto_runs_service(cls) -> 'EtoRunsService':
        """Get the ETO runs service"""
        return cls.get('eto_runs')

    @classmethod
    def get_connection_manager(cls) -> 'DatabaseConnectionManager':
        """Get the primary database connection manager (backward compatibility)"""
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")
        if not cls._connection_manager:
            raise RuntimeError("Connection manager not available")
        return cls._connection_manager

    @classmethod
    def get_connection(cls, name: str) -> 'DatabaseConnectionManager':
        """
        Get a named database connection manager.

        Args:
            name: Connection name (e.g., 'main', 'orders_db')

        Returns:
            DatabaseConnectionManager for the requested connection

        Raises:
            RuntimeError: If ServiceContainer not initialized
            ValueError: If connection name not found

        Example:
            # In a module's run() method:
            orders_db = context.services.get_connection('orders_db')
            with orders_db.session() as session:
                # Use session for HTC database operations
                ...
        """
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")

        if name not in cls._connection_managers:
            available = ', '.join(cls._connection_managers.keys())
            raise ValueError(
                f"Database connection '{name}' not found. "
                f"Available connections: {available}"
            )

        return cls._connection_managers[name]

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