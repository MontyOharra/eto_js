"""
FastAPI Routers Package
REST API routers for the Unified ETO Server
"""
from .pdf_templates import router as pdf_templates_router

# Export all routers for easy registration
ROUTERS = [
    pdf_templates_router,
    # TODO: Add other routers as they are converted from Flask blueprints
    # health_router,
    # email_ingestion_router,
    # eto_processing_router,
    # pdf_viewing_router
]

__all__ = [
    'ROUTERS',
    'pdf_templates_router'
]