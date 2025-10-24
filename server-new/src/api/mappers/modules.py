"""
Modules API Mappers
Convert between domain types and API schemas
"""
import json
from shared.types import ModuleCatalog
from api.schemas.modules import ModuleCatalogDTO


def convert_module_catalog_to_dto(module: ModuleCatalog) -> ModuleCatalogDTO:
    """
    Convert domain ModuleCatalog to API ModuleCatalogDTO

    Args:
        module: ModuleCatalog domain object

    Returns:
        ModuleCatalogDTO for API response
    """
    # Parse meta if it's a JSON string
    if isinstance(module.meta, str):
        meta_dict = json.loads(module.meta)
    elif hasattr(module.meta, 'to_dict'):
        meta_dict = module.meta.to_dict()
    else:
        meta_dict = module.meta

    # Parse config_schema if it's a JSON string
    if isinstance(module.config_schema, str):
        config_schema_dict = json.loads(module.config_schema)
    else:
        config_schema_dict = module.config_schema

    return ModuleCatalogDTO(
        id=module.id,
        version=module.version,
        name=module.name,
        description=module.description,
        module_kind=module.module_kind.value if hasattr(module.module_kind, 'value') else module.module_kind,
        meta=meta_dict,
        config_schema=config_schema_dict,
        handler_name=module.handler_name,
        color=module.color,
        category=module.category,
        is_active=module.is_active,
        created_at=module.created_at.isoformat(),
        updated_at=module.updated_at.isoformat()
    )


def convert_module_catalog_list(modules: list[ModuleCatalog]) -> list[ModuleCatalogDTO]:
    """
    Convert list of domain ModuleCatalog to list of DTOs

    Args:
        modules: List of ModuleCatalog domain objects

    Returns:
        List of ModuleCatalogDTO for API response
    """
    return [convert_module_catalog_to_dto(module) for module in modules]
