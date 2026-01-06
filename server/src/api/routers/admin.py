"""
Admin API Router
Administrative endpoints for system management
"""
import logging
from fastapi import APIRouter, Depends, Query, status

from api.schemas.admin import SyncModulesResponse, ModuleSyncResult, SyncOutputChannelsResponse

from shared.services.service_container import ServiceContainer
from features.modules.service import ModulesService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.post("/sync-modules", response_model=SyncModulesResponse, status_code=status.HTTP_200_OK)
async def sync_modules(
    refresh: bool = Query(False, description="Re-scan codebase for new modules before syncing"),
    modules_service: ModulesService = Depends(lambda: ServiceContainer.get_modules_service())
) -> SyncModulesResponse:
    """
    Sync module definitions from code to database catalog.

    This endpoint syncs registered modules to the database.
    Use the `refresh` parameter to re-scan the codebase for new modules/versions.

    Args:
        refresh: If True, re-discover modules from codebase before syncing

    Returns:
        SyncModulesResponse with sync results
    """
    logger.info(f"Starting module sync via API (refresh={refresh})...")

    result = modules_service.sync_modules(refresh=refresh)

    # Convert results dicts to ModuleSyncResult objects
    sync_results = [
        ModuleSyncResult(
            id=r["id"],
            name=r["name"],
            status=r["status"],
            message=r["message"]
        )
        for r in result["results"]
    ]

    return SyncModulesResponse(
        success=result["success"],
        modules_discovered=result["modules_discovered"],
        modules_synced=result["modules_synced"],
        modules_failed=result["modules_failed"],
        results=sync_results,
        message=result["message"]
    )


@router.post("/sync-output-channels", response_model=SyncOutputChannelsResponse, status_code=status.HTTP_200_OK)
async def sync_output_channels(
    modules_service: ModulesService = Depends(lambda: ServiceContainer.get_modules_service())
) -> SyncOutputChannelsResponse:
    """
    Sync output channel type definitions from code to database catalog.

    This endpoint reads the static OUTPUT_CHANNEL_DEFINITIONS and syncs them
    to the output_channel_types table.

    Returns:
        SyncOutputChannelsResponse with sync results
    """
    try:
        logger.info("Starting output channel types sync via API...")

        result = modules_service.sync_output_channel_types()

        return SyncOutputChannelsResponse(
            success=True,
            total=result["total"],
            created=result["created"],
            updated=result["updated"],
            channel_names=result["channel_names"],
            message=f"Successfully synced {result['total']} output channel types ({result['created']} created, {result['updated']} updated)"
        )

    except Exception as e:
        logger.error(f"Error during output channel sync: {e}", exc_info=True)
        return SyncOutputChannelsResponse(
            success=False,
            total=0,
            created=0,
            updated=0,
            channel_names=[],
            message=f"Error: {str(e)}"
        )
