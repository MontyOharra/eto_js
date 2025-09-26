"""
Advanced Dependency Injection Container
Handles circular dependencies, lazy initialization, and service lifecycles
"""
from typing import Dict, Any, Callable, List, Optional, Set, Union, TypeVar, Type
from enum import Enum
import inspect
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"      # One instance for app lifetime
    SCOPED = "scoped"            # One instance per request/scope
    TRANSIENT = "transient"      # New instance every time


class ServiceDescriptor:
    """Describes how to create a service"""
    def __init__(self,
                 service_type: type,
                 factory: Callable,
                 lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                 dependencies: Optional[List[str]] = None):
        self.service_type = service_type
        self.factory = factory
        self.lifetime = lifetime
        self.dependencies = dependencies or []


class CircularDependencyError(Exception):
    """Raised when circular dependency is detected"""
    pass


class ServiceNotFoundError(Exception):
    """Raised when requested service is not registered"""
    pass


class ServiceResolutionError(Exception):
    """Raised when service resolution fails"""
    pass


class DependencyInjectionContainer:
    """
    Advanced DI Container with:
    - Lazy initialization
    - Circular dependency detection
    - Service lifetimes (singleton, scoped, transient)
    - Auto-wiring based on type hints
    - Service health checks
    """

    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._singletons: Dict[str, Any] = {}
        self._resolving: Set[str] = set()
        self._scoped_instances: Dict[str, Any] = {}
        self._initialized = False

    def register(self,
                 name: str,
                 factory: Union[type, Callable],
                 lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                 dependencies: Optional[List[str]] = None):
        """
        Register a service with the container

        Args:
            name: Service identifier
            factory: Class or factory function to create the service
            lifetime: Service lifetime scope
            dependencies: Explicit dependency names (auto-detected if not provided)
        """
        # Auto-detect dependencies if not provided
        if dependencies is None and inspect.isclass(factory):
            dependencies = self._detect_dependencies(factory)

        descriptor = ServiceDescriptor(
            service_type=factory if inspect.isclass(factory) else type(None),
            factory=factory,
            lifetime=lifetime,
            dependencies=dependencies
        )

        self._services[name] = descriptor
        logger.debug(f"Registered service '{name}' with lifetime {lifetime.value} and dependencies {dependencies}")

    def register_instance(self, name: str, instance: Any):
        """Register an already-created instance as a singleton"""
        self._services[name] = ServiceDescriptor(
            service_type=type(instance),
            factory=lambda: instance,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=[]
        )
        self._singletons[name] = instance
        logger.debug(f"Registered singleton instance '{name}' of type {type(instance).__name__}")

    def _detect_dependencies(self, cls: type) -> List[str]:
        """Auto-detect constructor dependencies based on type hints"""
        dependencies = []

        try:
            sig = inspect.signature(cls.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Try to map parameter name to service name
                service_name = self._param_to_service_name(param_name)
                if service_name in self._services:
                    dependencies.append(service_name)

        except Exception as e:
            logger.warning(f"Could not auto-detect dependencies for {cls}: {e}")

        return dependencies

    def _param_to_service_name(self, param_name: str) -> str:
        """Map parameter name to service name"""
        # Example mappings - customize based on your naming conventions
        mappings = {
            'connection_manager': 'db',
            'pdf_service': 'pdf_processing',
            'template_service': 'pdf_template',
            'email_service': 'email_ingestion',
            'eto_service': 'eto_processing',
        }
        return mappings.get(param_name, param_name)

    def resolve(self, name: str) -> Any:
        """
        Resolve and return a service instance

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If service is not registered
            CircularDependencyError: If circular dependency is detected
        """
        if name not in self._services:
            raise ServiceNotFoundError(f"Service '{name}' is not registered")

        descriptor = self._services[name]

        # Handle different lifetimes
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if name in self._singletons:
                return self._singletons[name]
            instance = self._create_instance(name, descriptor)
            self._singletons[name] = instance
            return instance

        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if name in self._scoped_instances:
                return self._scoped_instances[name]
            instance = self._create_instance(name, descriptor)
            self._scoped_instances[name] = instance
            return instance

        else:  # TRANSIENT
            return self._create_instance(name, descriptor)

    def resolve_by_type(self, service_type: Type[T]) -> T:
        """Resolve a service by its type"""
        for name, descriptor in self._services.items():
            if descriptor.service_type == service_type:
                return self.resolve(name)
        raise ServiceNotFoundError(f"No service registered for type {service_type.__name__}")

    def _create_instance(self, name: str, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance with dependency resolution"""
        # Check for circular dependencies
        if name in self._resolving:
            cycle = ' -> '.join(self._resolving) + f' -> {name}'
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")

        self._resolving.add(name)

        try:
            # Resolve dependencies
            resolved_deps = {}
            for dep_name in descriptor.dependencies:
                # Handle lazy resolution - service can reference container
                if dep_name == 'container':
                    resolved_deps['container'] = self
                else:
                    resolved_deps[dep_name] = self.resolve(dep_name)

            # Create instance
            if inspect.isclass(descriptor.factory):
                # It's a class - instantiate with resolved dependencies
                instance = descriptor.factory(**resolved_deps)
            else:
                # It's a factory function - call with resolved dependencies
                instance = descriptor.factory(**resolved_deps)

            logger.debug(f"Created instance of service '{name}'")
            return instance

        except Exception as e:
            logger.exception(f"Failed to create instance of service '{name}': {e}")
            raise ServiceResolutionError(f"Failed to resolve service '{name}': {str(e)}")

        finally:
            self._resolving.remove(name)

    def resolve_all(self, service_type: type) -> List[Any]:
        """Resolve all services of a given type"""
        instances = []
        for name, descriptor in self._services.items():
            if descriptor.service_type == service_type:
                instances.append(self.resolve(name))
        return instances

    def create_scope(self) -> 'DependencyInjectionContainer':
        """Create a scoped container for request-scoped services"""
        scoped_container = DependencyInjectionContainer()
        scoped_container._services = self._services
        scoped_container._singletons = self._singletons  # Share singletons
        return scoped_container

    def clear_scoped(self):
        """Clear scoped instances (call at end of request)"""
        self._scoped_instances.clear()

    def is_registered(self, name: str) -> bool:
        """Check if a service is registered"""
        return name in self._services

    def get_dependencies(self, name: str) -> List[str]:
        """Get the dependencies of a registered service"""
        if name not in self._services:
            return []
        return self._services[name].dependencies.copy()

    def get_all_services(self) -> List[str]:
        """Get names of all registered services"""
        return list(self._services.keys())

    def health_check(self) -> Dict[str, bool]:
        """Check health of all singleton services"""
        health_status = {}

        for name in self._singletons:
            try:
                service = self._singletons[name]
                # Check if service has is_healthy method
                if hasattr(service, 'is_healthy') and callable(service.is_healthy):
                    health_status[name] = service.is_healthy()
                else:
                    health_status[name] = True  # Assume healthy if no health check
            except Exception as e:
                logger.error(f"Health check failed for service '{name}': {e}")
                health_status[name] = False

        return health_status


class ServiceProvider(ABC):
    """Abstract base class for services that need lazy dependency resolution"""

    def __init__(self, container: DependencyInjectionContainer):
        self._container = container

    def _get_service(self, name: str) -> Any:
        """Lazily resolve a service dependency"""
        return self._container.resolve(name)

    @abstractmethod
    def is_healthy(self) -> bool:
        """Health check for the service"""
        pass


def configure_services(container: DependencyInjectionContainer,
                      connection_manager,
                      pdf_storage_path: str):
    """
    Configure all services for the ETO application

    This function sets up the dependency injection container with all
    required services and their dependencies.
    """
    from features.pdf_processing import PdfProcessingService
    from features.email_ingestion import EmailIngestionService
    from features.eto_processing import EtoProcessingService
    from features.pdf_templates import PdfTemplateService

    logger.info("Configuring services in DI container...")

    # Register database connection as singleton instance
    container.register_instance('db', connection_manager)

    # Register PDF processing service
    container.register(
        name='pdf_processing',
        factory=lambda db: PdfProcessingService(pdf_storage_path, db),
        lifetime=ServiceLifetime.SINGLETON,
        dependencies=['db']
    )

    # Register PDF template service
    container.register(
        name='pdf_template',
        factory=lambda db: PdfTemplateService(db),
        lifetime=ServiceLifetime.SINGLETON,
        dependencies=['db']
    )

    # Register ETO service - with proper dependency injection
    container.register(
        name='eto_processing',
        factory=lambda db, pdf_processing, pdf_template: EtoProcessingService(db, pdf_processing, pdf_template),
        lifetime=ServiceLifetime.SINGLETON,
        dependencies=['db', 'pdf_processing', 'pdf_template']
    )

    # Register Email ingestion service - with proper dependency injection
    container.register(
        name='email_ingestion',
        factory=lambda db, pdf_processing, eto_processing: EmailIngestionService(db, pdf_processing, eto_processing),
        lifetime=ServiceLifetime.SINGLETON,
        dependencies=['db', 'pdf_processing', 'eto_processing']
    )

    logger.info(f"Registered {len(container.get_all_services())} services")

    # Log dependency graph
    for service_name in container.get_all_services():
        deps = container.get_dependencies(service_name)
        if deps:
            logger.debug(f"  {service_name} -> {deps}")
        else:
            logger.debug(f"  {service_name} (no dependencies)")

    return container


# Global container instance
_global_container: Optional[DependencyInjectionContainer] = None


def get_container() -> DependencyInjectionContainer:
    """Get the global DI container instance"""
    global _global_container
    if _global_container is None:
        _global_container = DependencyInjectionContainer()
    return _global_container


def initialize_container(connection_manager, pdf_storage_path: str) -> DependencyInjectionContainer:
    """Initialize the global DI container with all services"""
    container = get_container()
    configure_services(container, connection_manager, pdf_storage_path)
    return container