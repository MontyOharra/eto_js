"""
Modules API Router
Endpoints for module catalog and output channel access
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from api.schemas.modules import Module, OutputChannel
from api.mappers.modules import module_to_api

from shared.services.service_container import ServiceContainer
from shared.database.repositories import OutputChannelTypeRepository
from features.modules.service import ModulesService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modules",
    tags=["Modules"]
)


@router.get("", response_model=list[Module])
async def list_modules(
    kind: Optional[str] = Query(None, description="Filter by module kind (transform, action, logic, comparator)"),
    only_active: bool = Query(True, description="Only return active modules"),
    modules_service: ModulesService = Depends(lambda: ServiceContainer.get_modules_service())
) -> list[Module]:
    """
    Get all module catalog entries.

    Returns modules available for use in pipelines, filtered by kind if specified.
    """
    # Get modules from service (handles both registry and repository)
    modules = modules_service.list_modules(kind=kind, only_active=only_active)

    logger.info(f"Retrieved {len(modules)} modules (kind={kind}, only_active={only_active})")

    # List comprehension inline - no separate list conversion function
    return [module_to_api(m) for m in modules]


@router.get("/output-channels", response_model=list[OutputChannel])
async def list_output_channels() -> list[OutputChannel]:
    """
    Get all output channel type definitions from the database.

    Returns the catalog of available output channel types that can be
    placed in pipelines to collect data for the pending orders system.

    Note: Output channels must be synced via POST /admin/sync-output-channels first.
    """
    # Get repository with connection manager
    repo = OutputChannelTypeRepository(
        connection_manager=ServiceContainer.get_connection_manager()
    )

    # Fetch from database
    channels = repo.get_all()

    logger.info(f"Retrieved {len(channels)} output channel types from database")

    # Convert domain objects to API schema
    return [
        OutputChannel(
            name=ch.name,
            label=ch.label,
            data_type=ch.data_type,
            category=ch.category,
            description=ch.description,
            is_required=ch.is_required,
        )
        for ch in channels
    ]
