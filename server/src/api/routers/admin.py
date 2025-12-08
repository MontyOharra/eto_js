"""
Admin API Router
Administrative endpoints for system management
"""
import logging
import sys
from fastapi import APIRouter, Depends, status

from api.schemas.modules import SyncModulesResponse, ModuleSyncResult
from api.schemas.output_channels import SyncOutputChannelsResponse

from shared.services.service_container import ServiceContainer
from features.modules.service import ModulesService
from features.pipeline_results.service import PipelineResultService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.post("/sync-modules", response_model=SyncModulesResponse, status_code=status.HTTP_200_OK)
async def sync_modules(
    refresh: bool = False,
    modules_service: ModulesService = Depends(lambda: ServiceContainer.get_modules_service())
) -> SyncModulesResponse:
    """
    Sync module definitions from code to database catalog.

    This endpoint auto-discovers modules from known packages and syncs them to the database.
    Use the `refresh` parameter to clear existing modules before syncing.

    Args:
        refresh: If True, clear all existing modules before syncing

    Returns:
        SyncModulesResponse with sync results
    """
    results: list[ModuleSyncResult] = []
    success_count = 0
    error_count = 0

    try:
        logger.info("Starting module sync process via API...")

        # Step 1: Clear catalog if refresh requested
        if refresh:
            logger.info("Clearing module catalog...")
            from shared.database.models import ModuleModel

            try:
                with modules_service.connection_manager.session() as session:
                    modules = session.query(ModuleModel).all()
                    count = len(modules)
                    for module in modules:
                        session.delete(module)
                    logger.info(f"Cleared {count} modules from catalog")
            except Exception as e:
                logger.error(f"Failed to clear catalog: {e}", exc_info=True)
                return SyncModulesResponse(
                    success=False,
                    modules_discovered=0,
                    modules_synced=0,
                    modules_failed=0,
                    results=[],
                    message=f"Failed to clear catalog: {str(e)}"
                )

        # Step 2: Get already-registered modules from service registry
        logger.info("Getting registered modules from service...")
        catalog_entries = modules_service._registry.to_catalog_entries()
        logger.info(f"Found {len(catalog_entries)} modules to sync")

        if not catalog_entries:
            logger.warning("No modules found to sync")
            return SyncModulesResponse(
                success=True,
                modules_discovered=0,
                modules_synced=0,
                modules_failed=0,
                results=[],
                message="No modules found to sync. Check module packages and decorators."
            )

        # Step 3: Sync modules to database and track results
        for module_create in catalog_entries:
            try:
                modules_service.module_repository.upsert(module_create)

                logger.info(f"Synced module: {module_create.id} ({module_create.name})")
                results.append(ModuleSyncResult(
                    id=module_create.id,
                    name=module_create.name,
                    status="success",
                    message=None
                ))
                success_count += 1

            except Exception as e:
                logger.error(f"Failed to sync module {module_create.id}: {e}", exc_info=True)
                results.append(ModuleSyncResult(
                    id=module_create.id,
                    name=module_create.name,
                    status="error",
                    message=str(e)
                ))
                error_count += 1

        # Summary
        logger.info(f"Sync complete: {success_count} succeeded, {error_count} failed")

        return SyncModulesResponse(
            success=error_count == 0,
            modules_discovered=len(catalog_entries),
            modules_synced=success_count,
            modules_failed=error_count,
            results=results,
            message=f"Successfully synced {success_count} modules, {error_count} failed"
        )

    except Exception as e:
        logger.error(f"Fatal error during sync: {e}", exc_info=True)
        return SyncModulesResponse(
            success=False,
            modules_discovered=0,
            modules_synced=success_count,
            modules_failed=error_count,
            results=results,
            message=f"Fatal error: {str(e)}"
        )


@router.post("/sync-output-channels", response_model=SyncOutputChannelsResponse, status_code=status.HTTP_200_OK)
async def sync_output_channels(
    pipeline_result_service: PipelineResultService = Depends(lambda: ServiceContainer.get_pipeline_result_service())
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

        result = pipeline_result_service.sync_output_channel_types()

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
