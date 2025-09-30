"""
Modules Router - API endpoints for module management
Provides endpoints for module discovery and catalog access
"""
import logging
from typing import List, Dict, Any, Optional
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...shared.services import get_modules_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ModuleCatalogResponse(BaseModel):
    """Response model for module catalog"""
    modules: List[Dict[str, Any]]
    total_count: int
    stats: Dict[str, Any]


class ModuleStatsResponse(BaseModel):
    """Response model for module statistics"""
    stats: Dict[str, Any]


class ModuleExecuteRequest(BaseModel):
    """Request model for module execution"""
    module_id: str = Field(..., description="Module ID from catalog")
    inputs: Dict[str, Any] = Field(..., description="Input values keyed by input node ID")
    config: Dict[str, Any] = Field(..., description="Module configuration parameters")
    use_cache: bool = Field(True, description="Whether to use cached module (faster)")


class ModuleExecuteResponse(BaseModel):
    """Response model for module execution"""
    success: bool
    module_id: str
    outputs: Dict[str, Any] = Field(..., description="Output values keyed by output node ID")
    error: Optional[str] = None
    performance_ms: float = Field(..., description="Execution time in milliseconds")
    cache_used: bool = Field(..., description="Whether module was loaded from cache")


@router.get("/modules", response_model=ModuleCatalogResponse)
async def get_module_catalog():
    """
    Get catalog of all available modules
    Returns metadata for all registered modules
    """
    logger.info("Module catalog requested")

    try:
        # Get the singleton registry directly to ensure we have the same instance
        from ...features.modules.core.registry import get_registry
        registry = get_registry()

        # Get all modules from registry
        all_modules = registry.get_all()
        logger.info(f"Registry has {len(all_modules)} modules")

        # Convert to catalog format
        catalog = []
        for module_id, module_class in all_modules.items():
            try:
                meta = module_class.meta()
                catalog_entry = {
                    "module_ref": f"{module_class.id}:{getattr(module_class, 'version', '1.0.0')}",
                    "id": module_class.id,
                    "version": getattr(module_class, 'version', '1.0.0'),
                    "title": module_class.title,
                    "description": module_class.description,
                    "kind": module_class.kind,
                    "meta": meta.model_dump(),
                    "config_schema": module_class.config_schema(),
                    "category": getattr(module_class, 'category', 'Processing'),
                    "color": getattr(module_class, 'color', '#3B82F6')
                }
                catalog.append(catalog_entry)
            except Exception as e:
                logger.error(f"Error converting module {module_id} to catalog format: {e}")

        # Get stats
        stats = {
            "total_modules": len(catalog),
            "transform_modules": len([m for m in catalog if m['kind'] == 'transform']),
            "action_modules": len([m for m in catalog if m['kind'] == 'action']),
            "logic_modules": len([m for m in catalog if m['kind'] == 'logic']),
            "module_refs": [m['module_ref'] for m in catalog]
        }

        response = ModuleCatalogResponse(
            modules=catalog,
            total_count=len(catalog),
            stats=stats
        )

        logger.info(f"Returned {len(catalog)} modules in catalog")
        return response

    except Exception as e:
        logger.error(f"Failed to get module catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve module catalog")


@router.get("/modules/stats", response_model=ModuleStatsResponse)
async def get_module_stats():
    """
    Get statistics about registered modules
    """
    logger.info("Module stats requested")

    try:
        modules_service = get_modules_service()
        stats = modules_service.get_module_stats()

        response = ModuleStatsResponse(stats=stats)

        logger.info("Module stats retrieved successfully")
        return response

    except Exception as e:
        logger.error(f"Failed to get module stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve module stats")


@router.get("/modules/cache/stats")
async def get_module_cache_stats():
    """
    Get cache performance statistics
    """
    try:
        modules_service = get_modules_service()

        # Get cache stats from registry
        from ...features.modules.core.registry import get_registry
        registry = get_registry()
        cache_stats = registry.get_cache_stats()

        logger.info("Module cache stats retrieved successfully")
        return cache_stats

    except Exception as e:
        logger.error(f"Failed to get module cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")


@router.get("/modules/{module_ref}")
async def get_module_info(module_ref: str):
    """
    Get detailed information about a specific module

    Args:
        module_ref: Module reference in format "id:version"
    """
    logger.info(f"Module info requested for: {module_ref}")

    try:
        modules_service = get_modules_service()
        module_class = modules_service.get_module_by_ref(module_ref)

        if module_class is None:
            raise HTTPException(status_code=404, detail=f"Module not found: {module_ref}")

        # Get detailed module information
        meta = module_class.meta()

        module_info = {
            "module_ref": module_ref,
            "id": module_class.id,
            "version": module_class.version,
            "title": module_class.title,
            "description": module_class.description,
            "kind": module_class.kind,
            "meta": meta.model_dump(),
            "config_schema": module_class.ConfigModel.model_json_schema()
        }

        logger.info(f"Module info retrieved for: {module_ref}")
        return module_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get module info for {module_ref}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve module information")


@router.post("/modules/execute", response_model=ModuleExecuteResponse)
async def execute_module(request: ModuleExecuteRequest):
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
        # Get registry directly for better control
        from ...features.modules.core.registry import get_registry, ModuleCache
        from ...shared.database.repositories.module_catalog import ModuleCatalogRepository
        from ...shared.database import get_connection_manager

        registry = get_registry()

        # Try to get module from registry first (fast path)
        module_class = registry.get(request.module_id)
        cache_used = True

        if module_class is None and not request.use_cache:
            # Clear cache and try again if requested
            registry._cache = ModuleCache()
            cache_used = False

        if module_class is None:
            # Try to load from database
            cache_used = False
            connection_manager = get_connection_manager()
            if connection_manager:
                try:
                    module_repo = ModuleCatalogRepository(connection_manager)
                    catalog_entry = module_repo.get_by_id(request.module_id)

                    if catalog_entry:
                        # Try to resolve using handler_name if available
                        handler_name = catalog_entry.handler_name
                        if handler_name:
                            module_class = registry.load_module_from_handler(handler_name)
                except Exception as db_error:
                    logger.warning(f"Could not load from database: {db_error}")

        if module_class is None:
            raise HTTPException(
                status_code=404,
                detail=f"Module '{request.module_id}' not found in registry or database"
            )

        # Create module instance
        try:
            module_instance = module_class()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create module instance: {str(e)}"
            )

        # Validate configuration
        try:
            validated_config = module_class.ConfigModel(**request.config)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid configuration: {str(e)}"
            )

        # Execute module
        try:
            # Create a simple context for execution
            context = type('Context', (), {
                'instance_ordered_outputs': [{"node_id": "output_1"}],
                'instance_ordered_inputs': [(k, v) for k, v in request.inputs.items()]
            })()

            outputs = module_instance.run(
                inputs=request.inputs,
                cfg=validated_config,
                context=context
            )

            execution_time_ms = (time.time() - start_time) * 1000

            response = ModuleExecuteResponse(
                success=True,
                module_id=request.module_id,
                outputs=outputs,
                error=None,
                performance_ms=execution_time_ms,
                cache_used=cache_used
            )

            logger.info(
                f"Module {request.module_id} executed successfully in {execution_time_ms:.2f}ms "
                f"(cache: {cache_used})"
            )

            return response

        except Exception as e:
            logger.error(f"Module execution failed: {e}")
            execution_time_ms = (time.time() - start_time) * 1000

            return ModuleExecuteResponse(
                success=False,
                module_id=request.module_id,
                outputs={},
                error=str(e),
                performance_ms=execution_time_ms,
                cache_used=cache_used
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during module execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )