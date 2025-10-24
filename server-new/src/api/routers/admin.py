"""
Admin API Router
Administrative endpoints for system management
"""
import logging
import sys
from fastapi import APIRouter, Depends, status

from api.schemas.modules import SyncModulesResponse, ModuleSyncResult

from shared.utils.registry import get_registry, auto_discover_modules, ModuleSecurityValidator
from shared.database.repositories.module_catalog import ModuleCatalogRepository
from shared.types import ModuleCatalogCreate
from shared.services.service_container import ServiceContainer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.post("/sync-modules", response_model=SyncModulesResponse, status_code=status.HTTP_200_OK)
async def sync_modules(
    refresh: bool = False,
    connection_manager = Depends(lambda: ServiceContainer.get_connection_manager())
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
            from shared.database.models import ModuleCatalogModel

            try:
                with connection_manager.session() as session:
                    modules = session.query(ModuleCatalogModel).all()
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

        # Step 2: Clear Python's module cache for our modules
        logger.info("Clearing Python module cache...")
        modules_to_clear = [
            key for key in list(sys.modules.keys())
            if key.startswith("features.modules.") and
            not key.startswith("features.modules.core")
        ]
        for module_name in modules_to_clear:
            logger.debug(f"Removing {module_name} from Python cache")
            del sys.modules[module_name]

        # Step 3: Clear and re-populate registry
        logger.info("Clearing module registry...")
        registry = get_registry()
        registry.clear()

        # Step 4: Auto-discover modules
        logger.info("Auto-discovering modules...")
        packages_to_scan = [
            "features.modules.transform",
            "features.modules.action",
            "features.modules.logic",
            "features.modules.comparator",
        ]
        auto_discover_modules(packages_to_scan)

        # Get catalog entries from registry
        registry = get_registry()
        catalog_entries = registry.to_catalog_format()
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

        # Step 5: Create repository and sync modules
        module_repository = ModuleCatalogRepository(connection_manager=connection_manager)

        for entry in catalog_entries:
            try:
                # Validate handler_name
                if 'handler_name' in entry and entry['handler_name']:
                    is_valid, error_msg = ModuleSecurityValidator.validate_handler_path(entry['handler_name'])
                    if not is_valid:
                        logger.warning(f"Skipping module {entry['id']} due to security: {error_msg}")
                        results.append(ModuleSyncResult(
                            id=entry['id'],
                            name=entry['name'],
                            status="skipped",
                            message=f"Security validation failed: {error_msg}"
                        ))
                        continue

                # Convert to Pydantic model and upsert
                module_create = ModuleCatalogCreate(**entry)
                result = module_repository.upsert(module_create)

                logger.info(f"Synced module: {entry['id']} ({entry['name']})")
                results.append(ModuleSyncResult(
                    id=entry['id'],
                    name=entry['name'],
                    status="success",
                    message=None
                ))
                success_count += 1

            except Exception as e:
                logger.error(f"Failed to sync module {entry['id']}: {e}", exc_info=True)
                results.append(ModuleSyncResult(
                    id=entry['id'],
                    name=entry.get('name', 'Unknown'),
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
