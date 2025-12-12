"""
Email Integrations Package
Provides registry-based email provider integrations with dataclass types
"""
from .registry import IntegrationRegistry
from .base_integration import BaseEmailIntegration

# Import all integration implementations to trigger auto-registration
from .standard_integration import StandardEmailIntegration

__all__ = [
    'IntegrationRegistry',
    'BaseEmailIntegration',
    'StandardEmailIntegration',
]
