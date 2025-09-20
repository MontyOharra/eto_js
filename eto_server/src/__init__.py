"""
Unified ETO Server - Feature-Based Architecture
Main package for the unified Email-to-Order processing server
"""
from importlib import import_module
_app = import_module('.app', package=__name__)
create_app = _app.create_app

__version__ = '2.0.0'
__description__ = 'Unified Email-to-Order processing server with feature-based architecture'

__all__ = [
    'create_app',
]