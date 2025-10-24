"""
Module Catalog Domain Types
Frozen dataclasses for module catalog operations
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import json

from shared.types.modules import ModuleMeta, ModuleKind


@dataclass(frozen=True)
class ModuleCatalogCreate:
    """Domain type for creating new module catalog entries"""
    id: str
    version: str
    name: str
    description: Optional[str]
    module_kind: ModuleKind
    meta: ModuleMeta
    config_schema: Dict[str, Any]
    handler_name: str
    color: str = "#3B82F6"
    category: str = "Processing"
    is_active: bool = True

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        return {
            'id': self.id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'module_kind': self.module_kind.value if isinstance(self.module_kind, ModuleKind) else self.module_kind,
            'meta': json.dumps(self.meta.model_dump(exclude_none=False)),
            'config_schema': json.dumps(self.config_schema),
            'handler_name': self.handler_name,
            'color': self.color,
            'category': self.category,
            'is_active': self.is_active,
        }


@dataclass(frozen=True)
class ModuleCatalogUpdate:
    """Domain type for updating module catalog entries"""
    name: Optional[str] = None
    description: Optional[str] = None
    module_kind: Optional[ModuleKind] = None
    meta: Optional[ModuleMeta] = None
    config_schema: Optional[Dict[str, Any]] = None
    handler_name: Optional[str] = None
    color: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = {}
        if self.name is not None:
            data['name'] = self.name
        if self.description is not None:
            data['description'] = self.description
        if self.module_kind is not None:
            data['module_kind'] = self.module_kind.value if isinstance(self.module_kind, ModuleKind) else self.module_kind
        if self.meta is not None:
            data['meta'] = json.dumps(self.meta.model_dump(exclude_none=False))
        if self.config_schema is not None:
            data['config_schema'] = json.dumps(self.config_schema)
        if self.handler_name is not None:
            data['handler_name'] = self.handler_name
        if self.color is not None:
            data['color'] = self.color
        if self.category is not None:
            data['category'] = self.category
        if self.is_active is not None:
            data['is_active'] = self.is_active
        return data


@dataclass(frozen=True)
class ModuleCatalog:
    """Full module catalog domain object retrieved from database"""
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

    @staticmethod
    def from_db_model(db_model) -> "ModuleCatalog":
        """
        Convert SQLAlchemy model to domain object

        Args:
            db_model: ModuleCatalogModel instance from database

        Returns:
            ModuleCatalog domain object
        """
        # Parse JSON fields back to Python objects
        meta_data = json.loads(db_model.meta)
        config_schema_data = json.loads(db_model.config_schema)

        return ModuleCatalog(
            id=db_model.id,
            version=db_model.version,
            name=db_model.name,
            description=db_model.description,
            module_kind=ModuleKind(db_model.module_kind),
            meta=ModuleMeta.model_validate(meta_data),
            config_schema=config_schema_data,
            handler_name=db_model.handler_name,
            color=db_model.color,
            category=db_model.category,
            is_active=db_model.is_active,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )
