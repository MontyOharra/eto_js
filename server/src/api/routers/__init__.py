"""API routers for Transformation Pipeline Server"""

from .email_configs import router as email_configs_router
from .eto import router as eto_router
from .health import router as health_router
from .modules import router as modules_router
from .pdf_templates import router as pdf_templates_router
from .pipelines import router as pipelines_router

__all__ = [
    'email_configs_router',
    'eto_router',
    'health_router',
    'modules_router',
    'pdf_templates_router',
    'pipelines_router'
]