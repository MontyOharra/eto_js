"""
API Blueprints Package
Flask blueprints for all API endpoints
"""
from .health import health_bp
from .email_ingestion import email_ingestion_bp
from .eto_processing import eto_processing_bp
from .eto_service import eto_service_bp
from .pdf_viewing import pdf_viewing_bp
from .pdf_templates import templates_bp

__all__ = [
    'health_bp',
    'email_ingestion_bp',
    'eto_processing_bp',
    'eto_service_bp',
    'pdf_viewing_bp',
    'templates_bp'
]