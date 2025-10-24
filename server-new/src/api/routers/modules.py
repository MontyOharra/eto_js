"""
Modules API Router
Endpoints for module catalog access
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from api.schemas.modules import ModulesListResponse
from api.mappers.modules import convert_module_catalog_list

from shared.services.service_container import ServiceContainer
from shared.database.repositories.module_catalog import ModuleCatalogRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modules",
    tags=["Modules"]
)


@router.get("", response_model=ModulesListResponse)
async def list_modules(
    kind: Optional[str] = Query(None, description="Filter by module kind (transform, action, logic, comparator)"),
    only_active: bool = Query(True, description="Only return active modules"),
    connection_manager = Depends(lambda: ServiceContainer.get_connection_manager())
) -> ModulesListResponse:
    """
    Get all module catalog entries.

    Returns modules available for use in pipelines, filtered by kind if specified.
    """
    # Create repository with connection manager
    module_repository = ModuleCatalogRepository(connection_manager=connection_manager)

    # Get modules based on filters
    if kind:
        modules = module_repository.get_by_kind(kind, only_active=only_active)
    else:
        modules = module_repository.get_all(only_active=only_active)

    # Convert to DTOs
    module_dtos = convert_module_catalog_list(modules)

    logger.info(f"Retrieved {len(modules)} modules (kind={kind}, only_active={only_active})")

    return ModulesListResponse(
        items=module_dtos,
        total=len(module_dtos)
    )
