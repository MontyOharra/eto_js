"""
Email Integrations
Provider-specific email integration implementations
"""
from .base_integration import BaseEmailIntegration
from .outlook_com import OutlookComIntegration
from .factory import EmailIntegrationFactory

__all__ = [
    'BaseEmailIntegration',
    'OutlookComIntegration',
    'EmailIntegrationFactory',
]