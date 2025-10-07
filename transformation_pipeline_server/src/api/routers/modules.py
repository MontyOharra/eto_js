"""
Modules Router - API endpoints for module management
Provides endpoints for module discovery and catalog access
"""
import logging
import time

from fastapi import APIRouter, HTTPException, Depends, status

from shared.services import get_modules_service
from api.schemas import ModuleCatalogResponse, ModuleExecuteRequest, ModuleExecuteResponse
from features.modules.service import ModuleNotFoundError, ModuleLoadError, ModuleExecutionError, ModulesService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modules",
    tags=["Modules"]
)


@router.get("", response_model=ModuleCatalogResponse)
async def get_module_catalog(
    modules_service : ModulesService = Depends(get_modules_service)
):
    """
    Get catalog of all available modules from database
    Returns metadata for all active modules
    """
    logger.info("Module catalog requested")

    try:
        # Get modules from service (which queries database)
        modules = modules_service.get_module_catalog(only_active=True)

        logger.info(f"Retrieved {len(modules)} modules from catalog")

        # Convert to API response format
        catalog = []
        for module in modules:
            try:
                catalog_entry = {
                    "module_ref": f"{module.id}:{module.version}",
                    "id": module.id,
                    "version": module.version,
                    "title": module.name,  # Using name field from DB
                    "description": module.description,
                    "kind": module.module_kind,
                    "meta": module.meta if module.meta else {},
                    "config_schema": module.config_schema if module.config_schema else {},
                    "category": module.category if hasattr(module, 'category') else 'Processing',
                    "color": module.color if hasattr(module, 'color') else '#3B82F6'
                }
                catalog.append(catalog_entry)
            except Exception as e:
                logger.error(f"Error converting module {module.id} to response format: {e}")

        response = ModuleCatalogResponse(
            modules=catalog
        )

        logger.info(f"Returned {len(catalog)} modules in catalog")
        return response

    except Exception as e:
        logger.error(f"Failed to get module catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve module catalog")


@router.get("/{module_id}")
async def get_module_info(
    module_id: str,
    modules_service: ModulesService = Depends(get_modules_service)
):
    """
    Get detailed information about a specific module

    Args:
        module_id: Module ID
    """
    logger.info(f"Module info requested for: {module_id}")

    try:
        module_info = modules_service.get_module_info(module_id)

        if module_info is None:
            raise HTTPException(status_code=404, detail=f"Module not found: {module_id}")

        # Convert to API response format
        response = {
            "module_ref": f"{module_info.id}:{module_info.version}",
            "id": module_info.id,
            "version": module_info.version,
            "title": module_info.name,
            "description": module_info.description,
            "kind": module_info.module_kind,
            "meta": module_info.meta if module_info.meta else {},
            "config_schema": module_info.config_schema if module_info.config_schema else {},
            "category": module_info.category if hasattr(module_info, 'category') else 'Processing',
            "color": module_info.color if hasattr(module_info, 'color') else '#3B82F6',
            "is_active": module_info.is_active
        }

        logger.info(f"Module info retrieved for: {module_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get module info for {module_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve module information")


@router.post("/execute", response_model=ModuleExecuteResponse)
async def execute_module(
    request: ModuleExecuteRequest,
    modules_service: ModulesService = Depends(get_modules_service)
):
    """
    Execute a module with given inputs and configuration

    This endpoint allows you to test any module by providing:
    - module_id: The ID of the module to execute
    - inputs: Dictionary of input values
    - config: Module configuration parameters

    Example:
    ```
    curl -X POST http://localhost:8090/api/modules/execute \
      -H "Content-Type: application/json" \
      -d '{
        "module_id": "basic_text_cleaner",
        "inputs": {"input_1": "  Hello   World!  "},
        "config": {
          "strip_whitespace": true,
          "normalize_spaces": true,
          "to_lowercase": false
        }
      }'
    ```
    """
    logger.info(f"Module execution requested for: {request.module_id}")
    start_time = time.time()

    try:

        # Execute module through service
        outputs = modules_service.execute_module(
            module_id=request.module_id,
            inputs=request.inputs,
            config=request.config,
            context=None  # Service will create default context
        )

        execution_time_ms = (time.time() - start_time) * 1000

        response = ModuleExecuteResponse(
            success=True,
            module_id=request.module_id,
            outputs=outputs,
            error=None,
            performance_ms=execution_time_ms,
            cache_used=True  # Service handles caching internally
        )

        logger.info(
            f"Module {request.module_id} executed successfully in {execution_time_ms:.2f}ms"
        )

        return response

    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except ModuleLoadError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load module: {str(e)}"
        )
    except ModuleExecutionError as e:
        logger.error(f"Module execution failed: {e}")
        execution_time_ms = (time.time() - start_time) * 1000

        return ModuleExecuteResponse(
            success=False,
            module_id=request.module_id,
            outputs={},
            error=str(e),
            performance_ms=execution_time_ms,
            cache_used=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during module execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )