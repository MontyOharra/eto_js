"""
Module Catalog Repository
Repository for managing module catalog database operations
"""
import logging
from typing import Type

from shared.database.repositories.base import BaseRepository
from shared.database.models import ModuleCatalogModel
from shared.types import (
    ModuleCatalog,
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
)

from exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


class ModuleCatalogRepository(BaseRepository[ModuleCatalogModel]):
    """
    Repository for module catalog operations.
    Manages CRUD operations for transformation pipeline modules.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[ModuleCatalogModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return ModuleCatalogModel

    # ========== CRUD Operations ==========

    def create(self, module_create: ModuleCatalogCreate) -> ModuleCatalog:
        """
        Create new module catalog entry from frozen dataclass.

        Args:
            module_create: ModuleCatalogCreate dataclass with module data

        Returns:
            Created ModuleCatalog domain object
        """
        with self._get_session() as session:
            # Convert to database format with JSON serialization
            data = module_create.to_db_dict()

            # Create model instance
            model = self.model_class(**data)
            session.add(model)
            session.flush()  # Get ID before commit

            logger.info(f"Created module catalog: {model.id}:{model.version}")

            # Return domain object
            return ModuleCatalog.from_db_model(model)

    def update(
        self,
        module_id: str,
        version: str,
        module_update: ModuleCatalogUpdate
    ) -> ModuleCatalog:
        """
        Update existing module catalog entry from frozen dataclass.

        Args:
            module_id: Module ID
            version: Module version
            module_update: ModuleCatalogUpdate dataclass with fields to update

        Returns:
            Updated ModuleCatalog domain object

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

            # Get update dict with JSON serialization for modified fields only
            updates = module_update.to_db_dict()

            # Apply updates
            for key, value in updates.items():
                setattr(model, key, value)

            # Timestamp updated by onupdate=func.now() in model
            session.flush()

            logger.info(f"Updated module catalog: {module_id}:{version}")

            # Return updated domain object
            return ModuleCatalog.from_db_model(model)

    def get_by_id(self, module_id: str) -> ModuleCatalog | None:
        """
        Get module catalog entry by ID (returns latest active version).

        Args:
            module_id: Module ID to search for

        Returns:
            ModuleCatalog domain object or None if not found
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

            return ModuleCatalog.from_db_model(model)

    def get_by_module_ref(
        self,
        module_id: str,
        version: str
    ) -> ModuleCatalog | None:
        """
        Get module catalog entry by module reference (id:version).

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            ModuleCatalog domain object or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == module_id,
                self.model_class.version == version
            ).first()

            if not model:
                logger.debug(f"Module catalog not found: {module_id}:{version}")
                return None

            return ModuleCatalog.from_db_model(model)

    def get_all(self, only_active: bool = True) -> list[ModuleCatalog]:
        """
        Get all module catalog entries.

        Args:
            only_active: If True, only return active modules

        Returns:
            List of ModuleCatalog domain objects
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

            return [ModuleCatalog.from_db_model(model) for model in models]

    def get_by_kind(
        self,
        module_kind: str,
        only_active: bool = True
    ) -> list[ModuleCatalog]:
        """
        Get module catalog entries by kind.

        Args:
            module_kind: Module kind ("transform", "action", "logic", "comparator")
            only_active: If True, only return active modules

        Returns:
            List of ModuleCatalog domain objects
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

            return [ModuleCatalog.from_db_model(model) for model in models]

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

    def upsert(self, module_create: ModuleCatalogCreate) -> ModuleCatalog:
        """
        Create or update module catalog entry.

        Args:
            module_create: ModuleCatalogCreate dataclass with module data

        Returns:
            Created or updated ModuleCatalog domain object
        """
        # Check if exists
        existing = self.get_by_module_ref(module_create.id, module_create.version)

        if existing:
            # Update existing - convert create to update
            module_update = ModuleCatalogUpdate(
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
