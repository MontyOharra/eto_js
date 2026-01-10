"""
Module Catalog Repository

Repository for managing module catalog database operations.
"""
import json
import logging
from typing import Any

from shared.database.models import ModuleModel
from shared.database.repositories.base import BaseRepository
from shared.exceptions.service import ObjectNotFoundError
from shared.types.modules import (
    Module,
    ModuleCreate,
    ModuleKind,
    ModuleMeta,
    ModuleUpdate,
)

logger = logging.getLogger(__name__)


class ModuleRepository(BaseRepository[ModuleModel]):
    """
    Repository for module catalog operations.
    Manages CRUD operations for transformation pipeline modules.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> type[ModuleModel]:
        """Return the SQLAlchemy model class this repository manages."""
        return ModuleModel

    # ========== Serialization ==========

    def _serialize_module_meta(self, meta: ModuleMeta) -> str:
        """Convert ModuleMeta Pydantic model to JSON string for DB storage."""
        return json.dumps(meta.model_dump())

    def _deserialize_module_meta(self, json_str: str) -> ModuleMeta:
        """Convert JSON string from DB to ModuleMeta Pydantic model."""
        data = json.loads(json_str)
        return ModuleMeta.model_validate(data)

    def _serialize_config_schema(self, config_schema: dict[str, Any]) -> str:
        """Convert config schema dict to JSON string for DB storage."""
        return json.dumps(config_schema)

    def _deserialize_config_schema(self, json_str: str) -> dict[str, Any]:
        """Convert JSON string from DB to config schema dict."""
        return json.loads(json_str)

    def _model_to_domain(self, model: ModuleModel) -> Module:
        """Convert SQLAlchemy model to Module domain object."""
        return Module(
            id=model.id,
            identifier=model.identifier,
            version=model.version,
            name=model.name,
            description=model.description,
            module_kind=model.module_kind,
            meta=self._deserialize_module_meta(model.meta),
            config_schema=self._deserialize_config_schema(model.config_schema),
            handler_name=model.handler_name,
            color=model.color,
            category=model.category,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, module_create: ModuleCreate) -> Module:
        """
        Create new module catalog entry.

        Args:
            module_create: ModuleCreate with module data

        Returns:
            Created Module domain object
        """
        with self._get_session() as session:
            model = self.model_class(
                identifier=module_create.identifier,
                version=module_create.version,
                name=module_create.name,
                description=module_create.description,
                module_kind=module_create.module_kind,
                meta=self._serialize_module_meta(module_create.meta),
                config_schema=self._serialize_config_schema(module_create.config_schema),
                handler_name=module_create.handler_name,
                color=module_create.color,
                category=module_create.category,
                is_active=module_create.is_active,                                     
            )
            session.add(model)
            session.flush()

            logger.info(f"Created module: {model.identifier}:{model.version} (id={model.id})")

            return self._model_to_domain(model)

    def update(self, id: int, module_update: ModuleUpdate) -> Module:
        """
        Update existing module catalog entry by primary key.

        Only fields explicitly set on the update model are updated.
        Uses Pydantic's model_fields_set to distinguish between:
        - Field not provided (not in model_fields_set): unchanged
        - Field set to None: set to NULL in database
        - Field set to value: updated to that value

        Args:
            id: Module primary key (int)
            module_update: ModuleUpdate with fields to update

        Returns:
            Updated Module domain object

        Raises:
            ObjectNotFoundError: If module not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()

            if not model:
                raise ObjectNotFoundError(f"Module with id={id} not found")

            # Update only fields that were explicitly set
            for field_name in module_update.model_fields_set:
                value = getattr(module_update, field_name)

                # Handle serialization for JSON fields
                if field_name == 'meta' and value is not None:
                    value = self._serialize_module_meta(value)
                elif field_name == 'config_schema' and value is not None:
                    value = self._serialize_config_schema(value)
                # Note: module_kind is now a Literal string, no conversion needed

                setattr(model, field_name, value)

            session.flush()

            logger.info(f"Updated module: {model.identifier}:{model.version} (id={model.id})")

            return self._model_to_domain(model)

    def get_by_id(self, id: int) -> Module | None:
        """
        Get module by primary key.

        Args:
            id: Module primary key (int)

        Returns:
            Module domain object or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()

            if not model:
                logger.debug(f"Module not found: id={id}")
                return None

            return self._model_to_domain(model)

    def get_by_identifier(self, identifier: str) -> Module | None:
        """
        Get latest active version of a module by identifier.

        Args:
            identifier: Module identifier (e.g., "text_cleaner")

        Returns:
            Module domain object or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.identifier == identifier,
                self.model_class.is_active == True
            ).order_by(
                self.model_class.version.desc()
            ).first()

            if not model:
                logger.debug(f"Module not found: identifier={identifier}")
                return None

            return self._model_to_domain(model)

    def get_by_identifier_version(
        self,
        identifier: str,
        version: str
    ) -> Module | None:
        """
        Get specific version of a module by identifier and version.

        Args:
            identifier: Module identifier (e.g., "text_cleaner")
            version: Module version (e.g., "1.0.0")

        Returns:
            Module domain object or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.identifier == identifier,
                self.model_class.version == version
            ).first()

            if not model:
                logger.debug(f"Module not found: {identifier}:{version}")
                return None

            return self._model_to_domain(model)

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

            return [self._model_to_domain(model) for model in models]

    def get_latest_versions(self, only_active: bool = True) -> list[Module]:
        """
        Get only the latest version of each module (for frontend catalog).

        Args:
            only_active: If True, only return active modules

        Returns:
            List of Module domain objects (one per identifier, latest version)
        """
        with self._get_session() as session:
            # Get all modules first
            query = session.query(self.model_class)

            if only_active:
                query = query.filter(self.model_class.is_active == True)

            query = query.order_by(
                self.model_class.identifier,
                self.model_class.version.desc()
            )

            models = query.all()

            # Keep only the first (latest) version per identifier
            seen_identifiers: set[str] = set()
            latest_modules: list[Module] = []

            for model in models:
                if model.identifier not in seen_identifiers:
                    seen_identifiers.add(model.identifier)
                    latest_modules.append(self._model_to_domain(model))

            return latest_modules

    def get_by_kind(
        self,
        module_kind: str,
        only_active: bool = True
    ) -> list[Module]:
        """
        Get module catalog entries by kind.

        Args:
            module_kind: Module kind ("transform", "logic", "comparator", "misc", "output")
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

            return [self._model_to_domain(model) for model in models]

    def exists_by_identifier_version(self, identifier: str, version: str) -> bool:
        """
        Check if module exists by identifier and version.

        Args:
            identifier: Module identifier
            version: Module version

        Returns:
            True if module exists
        """
        with self._get_session() as session:
            exists = session.query(self.model_class).filter(
                self.model_class.identifier == identifier,
                self.model_class.version == version
            ).first() is not None

            logger.debug(f"Module exists check {identifier}:{version}: {exists}")
            return exists

    def upsert(self, module_create: ModuleCreate) -> Module:
        """
        Create or update module catalog entry.

        Uses identifier + version as the logical key for upsert.

        Args:
            module_create: ModuleCreate with module data

        Returns:
            Created or updated Module domain object
        """
        existing = self.get_by_identifier_version(
            module_create.identifier,
            module_create.version
        )

        if existing:
            # Update existing
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
            return self.update(existing.id, module_update)
        else:
            # Create new
            return self.create(module_create)

    def delete(self, id: int) -> bool:
        """
        Soft delete a module by primary key (sets is_active=False).

        Args:
            id: Module primary key (int)

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()

            if not model:
                logger.warning(f"Module not found for deletion: id={id}")
                return False

            model.is_active = False
            session.flush()

            logger.info(f"Soft deleted module: {model.identifier}:{model.version} (id={id})")
            return True

    def delete_by_identifier_version(self, identifier: str, version: str) -> bool:
        """
        Soft delete a module by identifier and version.

        Args:
            identifier: Module identifier
            version: Module version

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.identifier == identifier,
                self.model_class.version == version
            ).first()

            if not model:
                logger.warning(f"Module not found for deletion: {identifier}:{version}")
                return False

            model.is_active = False
            session.flush()

            logger.info(f"Soft deleted module: {identifier}:{version}")
            return True
