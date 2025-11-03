"""
Email Integrations Package
Provides registry-based email provider integrations with dataclass types
"""
from .registry import IntegrationRegistry
from .base_integration import BaseEmailIntegration

# Import all integration implementations to trigger auto-registration
from .outlook_com import OutlookComIntegration

__all__ = [
    'IntegrationRegistry',
    'BaseEmailIntegration',
    'OutlookComIntegration',
]
