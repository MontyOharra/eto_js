"""API routers for Transformation Pipeline Server"""

from .email_accounts import router as email_accounts_router
from .email_ingestion_configs import router as email_ingestion_configs_router
from .pdf_files import router as pdf_files_router
from .pdf_templates import router as pdf_templates_router
from .pipelines import router as pipelines_router
from .modules import router as modules_router
from .admin import router as admin_router
from .eto_runs import router as eto_runs_router
from .order_management import router as order_management_router
from .htc_integration import router as htc_integration_router
from .system_settings import router as system_settings_router

__all__ = [
    'email_accounts_router',
    'email_ingestion_configs_router',
    'pdf_files_router',
    'pdf_templates_router',
    'pipelines_router',
    'modules_router',
    'admin_router',
    'eto_runs_router',
    'order_management_router',
    'htc_integration_router',
    'system_settings_router',
]