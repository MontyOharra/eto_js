"""
FastAPI Routers Package
REST API routers for the Unified ETO Server
"""
from .pdf_templates import router as pdf_templates_router
from .email_configs import router as email_configs_router
from .health import router as health_router

# Export all routers for easy registration
ROUTERS = [
    health_router,
    pdf_templates_router,
    email_configs_router
]

__all__ = [
    'ROUTERS',
    'health_router',
    'pdf_templates_router',
    'email_configs_router'
]