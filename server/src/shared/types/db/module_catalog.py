"""
Module Catalog Domain Models
Pydantic models for module catalog operations based on modules.md specification
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from shared.database.models import ModuleCatalogModel

from ..enums import ModuleKind
from ..modules import ModuleMeta


class ModuleCatalogCreate(BaseModel):
    """Model for creating new module catalog entries"""
    id: str = Field(..., min_length=1, max_length=100, description="Module ID")
    version: str = Field(..., min_length=1, max_length=50, description="Module version")
    name: str = Field(..., min_length=1, max_length=255, description="Module display name")
    description: Optional[str] = Field(None, description="Module description")
    module_kind: ModuleKind = Field(..., description="Module type")
    meta: ModuleMeta = Field(..., description="Module I/O metadata")
    config_schema: Dict[str, Any] = Field(..., description="Pydantic JSON Schema with x-ui extensions")
    handler_name: str = Field(..., min_length=1, max_length=255, description="Python handler path")
    color: str = Field("#3B82F6", description="UI color")
    category: str = Field("Processing", description="Module category")
    is_active: bool = Field(True, description="Whether module is active")

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump()
        # Convert complex objects to JSON strings for database storage
        data['meta'] = json.dumps(data['meta'])
        data['config_schema'] = json.dumps(data['config_schema'])
        # UI hints are part of config_schema, not separate
        return data

    class Config:
        from_attributes = True


class ModuleCatalogUpdate(BaseModel):
    """Model for updating module catalog entries"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    module_kind: Optional[ModuleKind] = None
    meta: Optional[ModuleMeta] = None
    config_schema: Optional[Dict[str, Any]] = None
    handler_name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

    def model_dump_for_db(self, exclude_unset: bool = True) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump(exclude_unset=exclude_unset)
        # Convert complex objects to JSON strings if present
        if 'meta' in data and data['meta'] is not None:
            data['meta'] = json.dumps(data['meta'])
        if 'config_schema' in data and data['config_schema'] is not None:
            data['config_schema'] = json.dumps(data['config_schema'])
        return data

    class Config:
        from_attributes = True


class ModuleCatalog(BaseModel):
    """Full module catalog model retrieved from database"""
    id: str
    version: str
    name: str
    description: Optional[str]
    module_kind: ModuleKind
    meta: ModuleMeta
    config_schema: Dict[str, Any]
    handler_name: str
    color: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_model(cls, db_model : ModuleCatalogModel) -> "ModuleCatalog":
        """
        Convert SQLAlchemy model to Pydantic model

        Args:
            db_model: ModuleCatalogModel instance from database

        Returns:
            ModuleCatalog Pydantic model
        """
        # Parse JSON fields back to Python objects
        meta_data = json.loads(db_model.meta)
        config_schema_data = json.loads(db_model.config_schema)

        return cls(
            id=db_model.id,
            version=db_model.version,
            name=db_model.name,
            description=db_model.description,
            module_kind=db_model.module_kind, # type: ignore
            meta=ModuleMeta.model_validate(meta_data),  # Use model_validate for new IOShape structure
            config_schema=config_schema_data,
            handler_name=db_model.handler_name,
            color=db_model.color,
            category=db_model.category,
            is_active=db_model.is_active,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )

    class Config:
        from_attributes = True