"""
Module Catalog Repository
Repository for managing module catalog database operations following ETO server patterns
"""
import logging
from sqlalchemy.exc import SQLAlchemyError

from typing import Optional, List
from shared.types import ModuleCatalog, ModuleCatalogCreate, ModuleCatalogUpdate

from shared.database.models import ModuleCatalogModel
from shared.exceptions import RepositoryError, ObjectNotFoundError

from .base import BaseRepository

logger = logging.getLogger(__name__)


class ModuleCatalogRepository(BaseRepository[ModuleCatalogModel]):
    """
    Repository for module catalog operations
    Manages CRUD operations for transformation pipeline modules
    """
    
    @property
    def model_class(self):
        return ModuleCatalogModel

    def _convert_to_domain_object(self, db_model: ModuleCatalogModel) -> ModuleCatalog:
        """Convert SQLAlchemy model to domain object"""
        return ModuleCatalog.from_db_model(db_model)

    # ========== CRUD Operations with Pydantic Types ==========

    def create(self, module_create: ModuleCatalogCreate) -> ModuleCatalog:
        """
        Create new module catalog entry from Pydantic model

        Args:
            module_create: ModuleCatalogCreate model with module data

        Returns:
            Created ModuleCatalog domain model
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Convert to database format with JSON serialization
                data = module_create.model_dump_for_db()

                # Create model instance
                model = self.model_class(**data)
                session.add(model)
                session.flush()  # Get ID before commit

                logger.debug(f"Created module catalog: {model.id}:{model.version}")

                # Return domain model
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating module catalog: {e}")
            raise RepositoryError(f"Failed to create module catalog: {e}") from e

    def update(self, module_id: str, version: str, module_update: ModuleCatalogUpdate) -> ModuleCatalog:
        """
        Update existing module catalog entry from Pydantic update model

        Args:
            module_id: Module ID
            version: Module version
            module_update: ModuleCatalogUpdate model with fields to update

        Returns:
            Updated ModuleCatalog

        Raises:
            ObjectNotFoundError: If module not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Find by composite key (id, version)
                model = session.query(self.model_class).filter(
                    self.model_class.id == module_id,
                    self.model_class.version == version
                ).first()

                if not model:
                    raise ObjectNotFoundError('ModuleCatalog', f"{module_id}:{version}")

                # Get update dict with JSON serialization for modified fields only
                updates = module_update.model_dump_for_db(exclude_unset=True)

                # Apply updates
                for key, value in updates.items():
                    setattr(model, key, value)

                # Timestamp updated by onupdate=func.now() in model
                session.flush()

                logger.debug(f"Updated module catalog: {module_id}:{version}")

                # Return updated domain model
                return self._convert_to_domain_object(model)

        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating module catalog {module_id}:{version}: {e}")
            raise RepositoryError(f"Failed to update module catalog: {e}") from e

    def get_by_id(self, module_id: str) -> Optional[ModuleCatalog]:
        """
        Get module catalog entry by ID (returns latest version)

        Args:
            module_id: Module ID to search for

        Returns:
            ModuleCatalog domain object or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Get latest version of the module
                model = session.query(self.model_class).filter(
                    self.model_class.id == module_id,
                    self.model_class.is_active == True
                ).order_by(
                    self.model_class.version.desc()
                ).first()

                if not model:
                    logger.debug(f"Module catalog not found: {module_id}")
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting module catalog {module_id}: {e}")
            raise RepositoryError(f"Failed to get module catalog: {e}") from e

    def get_by_module_ref(self, module_id: str, version: str) -> Optional[ModuleCatalog]:
        """
        Get module catalog entry by module reference (id:version)

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            ModuleCatalog domain object or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.id == module_id,
                    self.model_class.version == version
                ).first()

                if not model:
                    logger.debug(f"Module catalog not found: {module_id}:{version}")
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting module catalog {module_id}:{version}: {e}")
            raise RepositoryError(f"Failed to get module catalog: {e}") from e

    def get_all(self, only_active: bool = True) -> List[ModuleCatalog]:
        """
        Get all module catalog entries

        Args:
            only_active: If True, only return active modules

        Returns:
            List of ModuleCatalog domain objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)

                if only_active:
                    query = query.filter(self.model_class.is_active == True)

                query = query.order_by(
                    self.model_class.category,
                    self.model_class.name,
                    self.model_class.version
                )

                models = query.all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting all module catalogs: {e}")
            raise RepositoryError(f"Failed to get module catalogs: {e}") from e

    def get_by_kind(self, module_kind: str, only_active: bool = True) -> List[ModuleCatalog]:
        """
        Get module catalog entries by kind

        Args:
            module_kind: Module kind ("transform", "action", or "logic")
            only_active: If True, only return active modules

        Returns:
            List of ModuleCatalog domain objects
        """
        try:
            with self.connection_manager.session_scope() as session:
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

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting module catalogs by kind {module_kind}: {e}")
            raise RepositoryError(f"Failed to get module catalogs: {e}") from e

    def exists_by_module_ref(self, module_id: str, version: str) -> bool:
        """
        Check if module catalog entry exists by module reference

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            True if module exists
        """
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(self.model_class).filter(
                    self.model_class.id == module_id,
                    self.model_class.version == version
                ).first() is not None

                logger.debug(f"Module catalog exists check {module_id}:{version}: {exists}")
                return exists

        except SQLAlchemyError as e:
            logger.error(f"Error checking module catalog existence {module_id}:{version}: {e}")
            raise RepositoryError(f"Failed to check module catalog existence: {e}") from e

    def upsert(self, module_create: ModuleCatalogCreate) -> ModuleCatalog:
        """
        Create or update module catalog entry

        Args:
            module_create: ModuleCatalogCreate model with module data

        Returns:
            Created or updated ModuleCatalog domain model
        """
        try:
            # Check if exists
            existing = self.get_by_module_ref(module_create.id, module_create.version)

            if existing:
                # Update existing
                module_update = ModuleCatalogUpdate(**module_create.model_dump())
                return self.update(module_create.id, module_create.version, module_update)
            else:
                # Create new
                return self.create(module_create)

        except Exception as e:
            logger.error(f"Error upserting module catalog {module_create.id}:{module_create.version}: {e}")
            raise RepositoryError(f"Failed to upsert module catalog: {e}") from e

    def delete(self, module_id: str, version: str) -> bool:
        """
        Delete a module catalog entry (soft delete by setting is_active=False)

        Args:
            module_id: Module ID
            version: Module version

        Returns:
            True if deleted, False if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
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

                logger.debug(f"Soft deleted module catalog: {module_id}:{version}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting module catalog {module_id}:{version}: {e}")
            raise RepositoryError(f"Failed to delete module catalog: {e}") from e