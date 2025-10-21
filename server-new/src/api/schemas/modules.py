"""
Modules API Schemas
Pydantic models for module catalog endpoints
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# GET /modules - List Modules Response
class ModuleInputPin(BaseModel):
    id: str
    name: str
    type: List[str]  # Allowed types (e.g., ["string", "number"])
    required: bool
    description: str


class ModuleOutputPin(BaseModel):
    id: str
    name: str
    type: List[str]  # Output types
    description: str


class ModuleMeta(BaseModel):
    inputs: List[ModuleInputPin]
    outputs: List[ModuleOutputPin]


class ModuleCatalogItem(BaseModel):
    id: str  # Module identifier
    version: str  # Module version (e.g., "1.0.0")
    name: str  # Display name
    description: str  # User-facing description
    color: str  # UI display color (hex code)
    category: str  # e.g., "Text Processing", "Actions", "Logic"
    module_kind: Literal["transform", "action", "logic", "entry_point"]
    meta: ModuleMeta
    config_schema: Dict[str, Any]  # JSON Schema for configuration UI


class ListModulesResponse(BaseModel):
    __root__: List[ModuleCatalogItem]
