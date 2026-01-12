"""
Modules API Router
Endpoints for module catalog and output channel access
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from api.schemas.modules import ModuleResponse, OutputChannel
from shared.services.service_container import ServiceContainer
from features.modules.service import ModulesService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modules",
    tags=["Modules"]
)


@router.get("", response_model=list[ModuleResponse])
async def list_modules(
    kind: Optional[str] = Query(None, description="Filter by module kind (transform, action, logic, comparator)"),
    only_active: bool = Query(True, description="Only return active modules"),
    modules_service: ModulesService = Depends(lambda: ServiceContainer.get_modules_service())
) -> list[ModuleResponse]:
    """
    Get all module catalog entries.

    Returns modules available for use in pipelines, filtered by kind if specified.
    """
    modules = modules_service.list_modules(kind=kind, only_active=only_active)

    logger.info(f"Retrieved {len(modules)} modules (kind={kind}, only_active={only_active})")

    return [
        ModuleResponse(
            id=m.id,
            identifier=m.identifier,
            version=m.version,
            name=m.name,
            description=m.description,
            module_kind=m.module_kind,
            meta=m.meta,
            config_schema=m.config_schema,
            color=m.color,
            category=m.category,
        )
        for m in modules
    ]


@router.get("/output-channels", response_model=list[OutputChannel])
async def list_output_channels(
    modules_service: ModulesService = Depends(lambda: ServiceContainer.get_modules_service())
) -> list[OutputChannel]:
    """
    Get all output channel type definitions from the database.

    Returns the catalog of available output channel types that can be
    placed in pipelines to collect data for the pending orders system.

    Note: Output channels must be synced via POST /admin/sync-output-channels first.
    """
    channels = modules_service.list_output_channel_types()

    logger.info(f"Retrieved {len(channels)} output channel types")

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
