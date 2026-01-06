"""
Output Channel Type Repository

Repository for managing output channel type catalog database operations.
"""
import logging

from shared.database.models import OutputChannelTypeModel
from shared.database.repositories.base import BaseRepository
from shared.exceptions.service import ObjectNotFoundError
from shared.types.output_channels import (
    OutputChannelType,
    OutputChannelTypeCreate,
    OutputChannelTypeUpdate,
)

logger = logging.getLogger(__name__)


class OutputChannelTypeRepository(BaseRepository[OutputChannelTypeModel]):
    """
    Repository for output channel type catalog operations.
    Manages CRUD operations for output channel type definitions.
    """

    @property
    def model_class(self) -> type[OutputChannelTypeModel]:
        """Return the SQLAlchemy model class this repository manages."""
        return OutputChannelTypeModel

    def _model_to_domain(self, model: OutputChannelTypeModel) -> OutputChannelType:
        """Convert SQLAlchemy model to domain object."""
        return OutputChannelType(
            id=model.id,
            name=model.name,
            label=model.label,
            data_type=model.data_type,
            description=model.description,
            is_required=model.is_required,
            category=model.category,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, channel_create: OutputChannelTypeCreate) -> OutputChannelType:
        """
        Create a new output channel type.

        Args:
            channel_create: OutputChannelTypeCreate with channel data

        Returns:
            Created OutputChannelType domain object
        """
        with self._get_session() as session:
            data = {
                "name": channel_create.name,
                "label": channel_create.label,
                "data_type": channel_create.data_type,
                "description": channel_create.description,
                "is_required": channel_create.is_required,
                "category": channel_create.category,
            }

            model = self.model_class(**data)
            session.add(model)
            session.flush()

            logger.info(f"Created output channel type: {model.name}")
            return self._model_to_domain(model)

    def update(self, name: str, channel_update: OutputChannelTypeUpdate) -> OutputChannelType:
        """
        Update an existing output channel type.

        Only fields explicitly set on the update model are updated.
        Uses Pydantic's model_fields_set to distinguish between:
        - Field not provided (not in model_fields_set): unchanged
        - Field set to None: set to NULL in database
        - Field set to value: updated to that value

        Args:
            name: Channel name to update
            channel_update: OutputChannelTypeUpdate with fields to update

        Returns:
            Updated OutputChannelType domain object

        Raises:
            ObjectNotFoundError: If channel not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.name == name
            ).first()

            if not model:
                raise ObjectNotFoundError(f"Output channel type '{name}' not found")

            # Update only fields that were explicitly set
            for field_name in channel_update.model_fields_set:
                value = getattr(channel_update, field_name)
                setattr(model, field_name, value)

            session.flush()
            logger.info(f"Updated output channel type: {name}")
            return self._model_to_domain(model)

    def get_by_name(self, name: str) -> OutputChannelType | None:
        """
        Get output channel type by name.

        Args:
            name: Channel name to find

        Returns:
            OutputChannelType domain object or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.name == name
            ).first()

            if not model:
                return None

            return self._model_to_domain(model)

    def get_all(self) -> list[OutputChannelType]:
        """
        Get all output channel types.

        Returns:
            List of OutputChannelType domain objects
        """
        with self._get_session() as session:
            models = session.query(self.model_class).order_by(
                self.model_class.category,
                self.model_class.name,
            ).all()

            return [self._model_to_domain(model) for model in models]

    def get_required(self) -> list[OutputChannelType]:
        """
        Get all required output channel types.

        Returns:
            List of required OutputChannelType domain objects
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter(
                self.model_class.is_required == True
            ).order_by(
                self.model_class.category,
                self.model_class.name,
            ).all()

            return [self._model_to_domain(model) for model in models]

    def get_by_category(self, category: str) -> list[OutputChannelType]:
        """
        Get output channel types by category.

        Args:
            category: Category to filter by

        Returns:
            List of OutputChannelType domain objects
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter(
                self.model_class.category == category
            ).order_by(
                self.model_class.name,
            ).all()

            return [self._model_to_domain(model) for model in models]

    def exists_by_name(self, name: str) -> bool:
        """
        Check if an output channel type exists by name.

        Args:
            name: Channel name to check

        Returns:
            True if exists, False otherwise
        """
        with self._get_session() as session:
            return session.query(self.model_class).filter(
                self.model_class.name == name
            ).first() is not None

    def upsert(self, channel_create: OutputChannelTypeCreate) -> OutputChannelType:
        """
        Create or update an output channel type.

        Args:
            channel_create: OutputChannelTypeCreate with channel data

        Returns:
            Created or updated OutputChannelType domain object
        """
        existing = self.get_by_name(channel_create.name)

        if existing:
            # Update existing
            channel_update = OutputChannelTypeUpdate(
                label=channel_create.label,
                data_type=channel_create.data_type,
                description=channel_create.description,
                is_required=channel_create.is_required,
                category=channel_create.category,
            )
            return self.update(channel_create.name, channel_update)
        else:
            # Create new
            return self.create(channel_create)

    def delete(self, name: str) -> bool:
        """
        Delete an output channel type.

        Args:
            name: Channel name to delete

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.name == name
            ).first()

            if not model:
                logger.warning(f"Output channel type not found for deletion: {name}")
                return False

            session.delete(model)
            session.flush()

            logger.info(f"Deleted output channel type: {name}")
            return True
