"""
Module Catalog Repository
Repository for managing module catalog database operations
"""
import logging
import json
from typing import Type
from dataclasses import asdict

from shared.database.repositories.base import BaseRepository
from shared.database.models import ModuleModel
from shared.types.modules import (
    Module,
    ModuleCreate,
    ModuleUpdate,
    ModuleMeta,
    ModuleKind,
    IOShape,
    IOSideShape,
    NodeGroup,
    NodeTypeRule,
)
from shared.exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


class ModuleRepository(BaseRepository[ModuleModel]):
    """
    Repository for module catalog operations.
    Manages CRUD operations for transformation pipeline modules.

    Supports dual-mode operation:P
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[ModuleModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return ModuleModel

    def _serialize_module_meta(self, meta: ModuleMeta) -> str:
        """Convert ModuleMeta dataclass to JSON string for DB storage"""
        # Recursively convert nested dataclasses to dicts
        return json.dumps(asdict(meta))

    def _deserialize_module_meta(self, json_str: str) -> ModuleMeta:
        """Convert JSON string from DB to ModuleMeta dataclass"""
        data = json.loads(json_str)

        # Reconstruct nested dataclasses from bottom up
        io_shape_data = data.get('io_shape', {})

        # Build inputs
        input_nodes = []
        for node_data in io_shape_data.get('inputs', {}).get('nodes', []):
            typing_data = node_data['typing']
            typing = NodeTypeRule(
                allowed_types=typing_data.get('allowed_types'),  # Already strings, no conversion needed
                type_var=typing_data.get('type_var')
            )
            input_nodes.append(NodeGroup(
                typing=typing,
                label=node_data['label'],
                min_count=node_data.get('min_count', 1),
                max_count=node_data.get('max_count', 1)
            ))

        # Build outputs (same pattern)
        output_nodes = []
        for node_data in io_shape_data.get('outputs', {}).get('nodes', []):
            typing_data = node_data['typing']
            typing = NodeTypeRule(
                allowed_types=typing_data.get('allowed_types'),  # Already strings, no conversion needed
                type_var=typing_data.get('type_var')
            )
            output_nodes.append(NodeGroup(
                typing=typing,
                label=node_data['label'],
                min_count=node_data.get('min_count', 1),
                max_count=node_data.get('max_count', 1)
            ))

        # Build IOShape
        io_shape = IOShape(
            inputs=IOSideShape(nodes=input_nodes),
            outputs=IOSideShape(nodes=output_nodes),
            type_params=io_shape_data.get('type_params', {})  # Already dict[str, list[str]], no conversion needed
        )

        return ModuleMeta(io_shape=io_shape)

    def _serialize_config_schema(self, config_schema: dict) -> str:
        """Convert config schema dict to JSON string for DB storage"""
        return json.dumps(config_schema)

    def _deserialize_config_schema(self, json_str: str) -> dict:
        """Convert JSON string from DB to config schema dict"""
        return json.loads(json_str)

    def _model_to_dataclass(self, model: ModuleModel) -> Module:
        """Convert SQLAlchemy model to Module domain object"""
        return Module(
            id=model.id,
            version=model.version,
            name=model.name,
            description=model.description,
            module_kind=ModuleKind(model.module_kind),
            meta=self._deserialize_module_meta(model.meta),
            config_schema=self._deserialize_config_schema(model.config_schema),
            handler_name=model.handler_name,
            color=model.color,
            category=model.category,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


    # ========== CRUD Operations ==========

    def create(self, module_create: ModuleCreate) -> Module:
        """
        Create new module catalog entry from frozen dataclass.

        Args:
            module_create: ModuleCreate dataclass with module data

        Returns:
            Created Module domain object
        """
        with self._get_session() as session:
            # Build database dict directly from dataclass fields
            # Serialize complex types to JSON strings for DB
            data = {
                'id': module_create.id,
                'version': module_create.version,
                'name': module_create.name,
                'description': module_create.description,
                'module_kind': module_create.module_kind.value,
                'meta': self._serialize_module_meta(module_create.meta),
                'config_schema': self._serialize_config_schema(module_create.config_schema),
                'handler_name': module_create.handler_name,
                'color': module_create.color,
                'category': module_create.category,
                'is_active': module_create.is_active,
            }

            # Create model instance
            model = self.model_class(**data)
            session.add(model)
            session.flush()  # Get ID before commit

            logger.info(f"Created module catalog: {model.id}:{model.version}")

            # Return domain object
            return self._model_to_dataclass(model)

    def update(
        self,
        module_id: str,
        version: str,
        module_update: ModuleUpdate
    ) -> Module:
        """
        Update existing module catalog entry from frozen dataclass.

        Args:
            module_id: Module ID
            version: Module version
            module_update: ModuleUpdate dataclass with fields to update

        Returns:
            Updated Module domain object

        Raises:
            ObjectNotFoundError: If module not found
        """
        with self._get_session() as session:
            # Find by composite key (id, version)
            model = session.query(self.model_class).filter(
                self.model_class.id == module_id,
                self.model_class.version == version
            ).first()

            if not model:
                raise ObjectNotFoundError(
                    f"Module catalog {module_id}:{version} not found"
                )

            # Build update dict directly from dataclass fields
            # Only include fields that are not None
            updates = {}
            if module_update.name is not None:
                updates['name'] = module_update.name
            if module_update.description is not None:
                updates['description'] = module_update.description
            if module_update.module_kind is not None:
                updates['module_kind'] = module_update.module_kind.value
            if module_update.meta is not None:
                updates['meta'] = self._serialize_module_meta(module_update.meta)
            if module_update.config_schema is not None:
                updates['config_schema'] = self._serialize_config_schema(module_update.config_schema)
            if module_update.handler_name is not None:
                updates['handler_name'] = module_update.handler_name
            if module_update.color is not None:
                updates['color'] = module_update.color
            if module_update.category is not None:
                updates['category'] = module_update.category
            if module_update.is_active is not None:
                updates['is_active'] = module_update.is_active

            # Apply updates
            for key, value in updates.items():
                setattr(model, key, value)

            # Timestamp updated by onupdate=func.now() in model
            session.flush()

            logger.info(f"Updated module catalog: {module_id}:{version}")

            # Return updated domain object
            return self._model_to_dataclass(model)

    def get_by_id(self, module_id: str) -> Module | None:
        """
        Get module catalog entry by ID (returns latest active version).

        Args:
            module_id: Module ID to search for

        Returns:
            Module domain object or None if not found
        """
        with self._get_session() as session:
            # Get latest active version of the module
            model = session.query(self.model_class).filter(
                self.model_class.id == module_id,
                self.model_class.is_active == True
            ).order_by(
                self.model_class.version.desc()
            ).first()

            if not model:
                logger.debug(f"Module catalog not found: {module_id}")
                return None

            return self._model_to_dataclass(model)

    def get_by_module_ref(
        self,
        module_id: str,
        version: str
    ) -> Module | None:
        """
        Get module catalog entry by module reference (id:version).

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            Module domain object or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == module_id,
                self.model_class.version == version
            ).first()

            if not model:
                logger.debug(f"Module catalog not found: {module_id}:{version}")
                return None

            return self._model_to_dataclass(model)

    def get_all(self, only_active: bool = True) -> list[Module]:
        """
        Get all module catalog entries.

        Args:
            only_active: If True, only return active modules

        Returns:
            List of Module domain objects
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

            if only_active:
                query = query.filter(self.model_class.is_active == True)

            query = query.order_by(
                self.model_class.category,
                self.model_class.name,
                self.model_class.version
            )

            models = query.all()

            return [self._model_to_dataclass(model) for model in models]

    def get_by_kind(
        self,
        module_kind: str,
        only_active: bool = True
    ) -> list[Module]:
        """
        Get module catalog entries by kind.

        Args:
            module_kind: Module kind ("transform", "action", "logic", "comparator")
            only_active: If True, only return active modules

        Returns:
            List of Module domain objects
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter(
                self.model_class.module_kind == module_kind
            )

            if only_active:
                query = query.filter(self.model_class.is_active == True)

            query = query.order_by(
                self.model_class.name,
                self.model_class.version
            )

            models = query.all()

            return [self._model_to_dataclass(model) for model in models]

    def exists_by_module_ref(self, module_id: str, version: str) -> bool:
        """
        Check if module catalog entry exists by module reference.

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            True if module exists
        """
        with self._get_session() as session:
            exists = session.query(self.model_class).filter(
                self.model_class.id == module_id,
                self.model_class.version == version
            ).first() is not None

            logger.debug(f"Module catalog exists check {module_id}:{version}: {exists}")
            return exists

    def upsert(self, module_create: ModuleCreate) -> Module:
        """
        Create or update module catalog entry.

        Args:
            module_create: ModuleCreate dataclass with module data

        Returns:
            Created or updated Module domain object
        """
        # Check if exists
        existing = self.get_by_module_ref(module_create.id, module_create.version)

        if existing:
            # Update existing - convert create to update
            module_update = ModuleUpdate(
                name=module_create.name,
                description=module_create.description,
                module_kind=module_create.module_kind,
                meta=module_create.meta,
                config_schema=module_create.config_schema,
                handler_name=module_create.handler_name,
                color=module_create.color,
                category=module_create.category,
                is_active=module_create.is_active,
            )
            return self.update(module_create.id, module_create.version, module_update)
        else:
            # Create new
            return self.create(module_create)

    def delete(self, module_id: str, version: str) -> bool:
        """
        Delete a module catalog entry (soft delete by setting is_active=False).

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == module_id,
                self.model_class.version == version
            ).first()

            if not model:
                logger.warning(f"Module catalog not found for deletion: {module_id}:{version}")
                return False

            # Soft delete
            model.is_active = False
            session.flush()

            logger.info(f"Soft deleted module catalog: {module_id}:{version}")
            return True
