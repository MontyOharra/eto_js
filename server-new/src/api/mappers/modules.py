"""
Modules API Mappers
Convert between domain types and API schemas
"""
from dataclasses import asdict

from shared.types.modules import Module
from api.schemas.modules import Module as ModulePydantic


def module_to_api(module: Module) -> ModulePydantic:
    """
    Convert domain Module to API Module schema

    Args:
        module: Module domain object

    Returns:
        ModulePydantic for API response
    """
    # Convert ModuleMeta dataclass to dict for API response
    meta_dict = asdict(module.meta)

    return ModulePydantic(
        id=module.id,
        version=module.version,
        name=module.name,
        description=module.description,
        module_kind=module.module_kind.value,  # Enum to string
        meta=meta_dict,
        config_schema=module.config_schema,  # Already a dict
        color=module.color,
        category=module.category
    )
