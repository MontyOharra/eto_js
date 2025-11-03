# The ServiceContainer is now accessed directly via class methods
# Import it where needed: from shared.services.service_container import ServiceContainer

from .service_container import ServiceContainer

__all__ = [
    'ServiceContainer'
]