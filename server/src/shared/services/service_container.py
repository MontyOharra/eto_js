"""
Service Container - Pure Class-Based Singleton Pattern
Handles service dependencies and circular references elegantly
"""
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from features.modules.service import ModulesService
    from features.email.service import EmailService
    from features.pdf_files.service import PdfFilesService
    from features.pdf_templates.service import PdfTemplateService
    from features.pipelines.service import PipelineService
    from features.pipeline_execution.service import PipelineExecutionService
    from features.htc_integration.service import HtcIntegrationService
    from features.output_processing_old.service import OutputProcessingService
    from features.order_management_old.service import OrderManagementService
    from features.eto_runs.service import EtoRunsService
    from features.auth.service import AuthService
    from shared.database.connection import DatabaseConnectionManager
    from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)


class ServiceProxy:
    """
    Proxy to handle service dependencies including potential circular references.
    Delays service resolution until the service is actually accessed.
    """
    def __init__(self, service_name: str) -> None:
        self._service_name = service_name
        self._resolved: Any = None

    def __getattr__(self, name: str) -> Any:
        # Resolve the actual service when first accessed
        if self._resolved is None:
            self._resolved = ServiceContainer.get(self._service_name)
        return getattr(self._resolved, name)

    def __repr__(self) -> str:
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
    _services: dict[str, Any] = {}
    _service_definitions: dict[str, dict[str, Any]] = {}
    _main_connection: 'DatabaseConnectionManager | None' = None  # SQL Server system database
    _access_connection_manager: 'AccessConnectionManager | None' = None  # Access databases
    _pdf_storage_path: str | None = None
    _resolving: list[str] = []

    @classmethod
    def initialize(
        cls,
        main_connection: 'DatabaseConnectionManager',
        pdf_storage_path: str,
        access_connection_manager: 'AccessConnectionManager | None' = None,
        **kwargs
    ) -> None:
        """
        Initialize the service container.
        Can be called multiple times safely (will only initialize once).

        Args:
            main_connection: SQL Server database connection manager (system/meta DB)
            pdf_storage_path: Path for PDF file storage
            access_connection_manager: AccessConnectionManager for Access databases
            **kwargs: Additional configuration parameters
        """
        if cls._initialized:
            logger.warning("ServiceContainer already initialized")
            return

        logger.info("Initializing ServiceContainer...")

        # Store core dependencies
        cls._main_connection = main_connection
        cls._pdf_storage_path = pdf_storage_path
        cls._access_connection_manager = access_connection_manager

        if access_connection_manager:
            databases = access_connection_manager.list_databases()
            logger.info(f"AccessConnectionManager registered with {len(databases)} database(s): {', '.join(databases)}")

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
                'args': [cls._main_connection],
                'singleton': True,
                'description': 'Module catalog and auto-discovery service'
            },
            'email': {
                'class': 'features.email.service.EmailService',
                'args': [cls._main_connection, '_service:pdf_files', '_service:eto_runs'],
                'singleton': True,
                'description': 'Email service for account management, operations, and PDF processing'
            },
            'pdf_files': {
                'class': 'features.pdf_files.service.PdfFilesService',
                'args': [cls._main_connection, '_service:storage_config'],
                'singleton': True,
                'description': 'PDF files service with extraction and storage'
            },
            'pipeline_execution': {
                'class': 'features.pipeline_execution.service.PipelineExecutionService',
                'args': [cls._main_connection, cls._access_connection_manager],
                'singleton': True,
                'description': 'Pipeline execution service for running compiled pipelines'
            },
            'htc_integration': {
                'class': 'features.htc_integration.service.HtcIntegrationService',
                'args': [cls._access_connection_manager, cls._main_connection],
                'singleton': True,
                'description': 'HTC Access database integration service for order operations'
            },
            'output_processing': {
                'class': 'features.output_processing.service.OutputProcessingService',
                'args': [cls._main_connection, '_service:htc_integration'],
                'singleton': True,
                'description': 'Output processing service for routing pipeline data to pending orders/updates'
            },
            'order_management': {
                'class': 'features.order_management.service.OrderManagementService',
                'args': [cls._main_connection, '_service:htc_integration', '_service:email'],
                'singleton': True,
                'description': 'Order management service with worker and email notifications'
            },
            'pipelines': {
                'class': 'features.pipelines.service.PipelineService',
                'args': [cls._main_connection, '_service:pipeline_execution', '_service:modules', cls._access_connection_manager],
                'singleton': True,
                'description': 'Pipeline compilation and execution service'
            },
            'pdf_templates': {
                'class': 'features.pdf_templates.service.PdfTemplateService',
                'args': [cls._main_connection, '_service:pipelines', '_service:pdf_files', '_service:pipeline_execution', cls._access_connection_manager],
                'singleton': True,
                'description': 'PDF template service with versioning and pipeline integration'
            },
            'eto_runs': {
                'class': 'features.eto_runs.service.EtoRunsService',
                'args': [cls._main_connection, '_service:pdf_templates', '_service:pdf_files', '_service:pipeline_execution', '_service:output_processing'],
                'singleton': True,
                'description': 'ETO runs service for processing lifecycle management'
            },
            'auth': {
                'class': 'features.auth.service.AuthService',
                'args': [cls._access_connection_manager],
                'singleton': True,
                'description': 'Authentication service for user login via HTC Staff database'
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
                        module = __import__(module_path, fromlist=[class_name])
                        # Get the class
                        factory_class = getattr(module, class_name)
                        # Get the method from the class
                        factory_func = getattr(factory_class, method_name)
                    except (ImportError, AttributeError):
                        # Fall back to module.function pattern
                        module_path, function_name = factory_path.rsplit('.', 1)
                        module = __import__(module_path, fromlist=[function_name])
                        factory_func = getattr(module, function_name)
                else:
                    # module.function pattern
                    module_path, function_name = factory_path.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[function_name])
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
                    module = import_module(module_path, package='shared')
                else:
                    # Absolute import
                    module = __import__(module_path, fromlist=[class_name])

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
    def get_email_service(cls) -> 'EmailService':
        """Get the email service"""
        return cls.get('email')
    
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
    def get_htc_integration_service(cls) -> 'HtcIntegrationService':
        """Get the HTC integration service"""
        return cls.get('htc_integration')

    @classmethod
    def get_output_processing_service(cls) -> 'OutputProcessingService':
        """Get the output processing service"""
        return cls.get('output_processing')

    @classmethod
    def get_order_management_service(cls) -> 'OrderManagementService':
        """Get the order management service"""
        return cls.get('order_management')

    @classmethod
    def get_eto_runs_service(cls) -> 'EtoRunsService':
        """Get the ETO runs service"""
        return cls.get('eto_runs')

    @classmethod
    def get_auth_service(cls) -> 'AuthService':
        """Get the authentication service"""
        return cls.get('auth')

    @classmethod
    def get_main_connection(cls) -> 'DatabaseConnectionManager':
        """Get the main SQL Server database connection manager"""
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")
        if not cls._main_connection:
            raise RuntimeError("Main connection not available")
        return cls._main_connection

    @classmethod
    def get_access_connection_manager(cls) -> 'AccessConnectionManager':
        """Get the Access database connection manager"""
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")
        if not cls._access_connection_manager:
            raise RuntimeError("Access connection manager not available")
        return cls._access_connection_manager

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
        cls._main_connection = None
        cls._access_connection_manager = None
        cls._resolving = []
        logger.info("ServiceContainer reset")

    @classmethod
    def get_all_services(cls) -> list[str]:
        """Get names of all registered services"""
        if not cls._initialized:
            raise RuntimeError("ServiceContainer not initialized")
        return list(cls._service_definitions.keys())

    @classmethod
    def get_cached_services(cls) -> list[str]:
        """Get names of all currently cached services"""
        return list(cls._services.keys())

    @classmethod
    def health_check(cls) -> dict[str, bool]:
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