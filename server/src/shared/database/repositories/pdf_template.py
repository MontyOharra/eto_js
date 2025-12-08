"""
PDF Template Repository
Repository for pdf_templates table with CRUD operations
"""
import logging
from typing import Type, Any
from sqlalchemy import func, case, desc, asc
from sqlalchemy.orm import joinedload, selectinload

from shared.database.repositories.base import BaseRepository
from shared.database.models import PdfTemplateModel, PdfTemplateVersionModel
from shared.types.pdf_templates import (
    PdfTemplate,
    PdfTemplateListView
)
from shared.exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


class PdfTemplateRepository(BaseRepository[PdfTemplateModel]):
    """
    Repository for PDF template CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[PdfTemplateModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PdfTemplateModel

    # ========== Helper Methods ==========

    def _model_to_template(self, model: PdfTemplateModel) -> PdfTemplate:
        """Convert ORM model to PdfTemplateMetadata dataclass"""
        return PdfTemplate(
            id=model.id,
            name=model.name,
            description=model.description,
            customer_id=model.customer_id,
            status=model.status,  # Convert enum to string
            source_pdf_id=model.source_pdf_id,
            current_version_id=model.current_version_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== Query Operations ==========

    def list_templates(
        self,
        status: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None
    ) -> list[PdfTemplateListView]:
        """
        List templates with filtering and sorting.

        Complex query that:
        - Joins with current_version to get version_num and usage_count
        - Counts total versions per template via subquery
        - Filters by status if provided
        - Sorts dynamically based on parameters

        Args:
            status: Filter by status ("active" or "inactive"), None for all
            sort_by: Field to sort by ("name", "status", "usage_count")
            sort_order: Sort direction ("asc" or "desc")

        Returns:
            List of PdfTemplateSummary
        """
        with self._get_session() as session:
            # Subquery to count versions per template
            version_count_subquery = (
                session.query(
                    PdfTemplateVersionModel.pdf_template_id,
                    func.count(PdfTemplateVersionModel.id).label('version_count')
                )
                .group_by(PdfTemplateVersionModel.pdf_template_id)
                .subquery()
            )

            # Main query
            query = (
                session.query(
                    PdfTemplateModel,
                    PdfTemplateVersionModel.version_num,
                    PdfTemplateVersionModel.usage_count,
                    version_count_subquery.c.version_count
                )
                .outerjoin(
                    PdfTemplateVersionModel,
                    PdfTemplateModel.current_version_id == PdfTemplateVersionModel.id
                )
                .outerjoin(
                    version_count_subquery,
                    PdfTemplateModel.id == version_count_subquery.c.pdf_template_id
                )
            )

            # Apply status filter
            if status:
                query = query.filter(PdfTemplateModel.status == status)

            if not sort_by:
                sort_by = "name"
            if not sort_order:
                sort_order = "desc"

            # Apply sorting
            sort_column = {
                "name": PdfTemplateModel.name,
                "status": PdfTemplateModel.status,
                "usage_count": PdfTemplateVersionModel.usage_count
            }.get(sort_by, PdfTemplateModel.name)

            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

            # Execute query
            results = query.all()

            # Convert to PdfTemplateSummary objects
            summaries = [
                PdfTemplateListView(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    customer_id=template.customer_id,
                    status=template.status,  # Convert enum to string
                    source_pdf_id=template.source_pdf_id,
                    current_version_id=template.current_version_id,
                    current_version_number=version_num,
                    version_usage_count=usage_count or 0,  # Default to 0 if None
                    version_count=version_count or 0,  # Default to 0 if None
                    updated_at=template.updated_at
                )
                for template, version_num, usage_count, version_count in results
            ]

            return summaries

    def get_by_id(self, template_id: int) -> PdfTemplate | None:
        """
        Get template metadata by ID.

        Args:
            template_id: Template record ID

        Returns:
            PdfTemplateMetadata dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, template_id)

            if model is None:
                return None

            return self._model_to_template(model)

    # ========== Update Operations ==========

    def create(
        self,
        name: str,
        description: str | None,
        customer_id: int | None,
        source_pdf_id: int,
        status: str = "inactive"
    ) -> PdfTemplate:
        """
        Create new template record.

        Args:
            name: Template name
            description: Template description (optional)
            customer_id: Customer ID from external Access DB (optional)
            source_pdf_id: Source PDF file ID
            status: Template status (default: "inactive")

        Returns:
            Created PdfTemplateMetadata
        """
        with self._get_session() as session:
            # Create ORM model
            template = self.model_class(
                name=name,
                description=description,
                customer_id=customer_id,
                source_pdf_id=source_pdf_id,
                status=status,
                current_version_id=None  # Will be set after version is created
            )

            session.add(template)
            session.commit()
            session.refresh(template)

            return self._model_to_template(template)

    def update(self, template_id: int, updates: dict[str, Any]) -> PdfTemplate:
        """
        Update template with provided field values.

        Generic update method that applies any field updates to the template.
        Handles enum conversion for status field.

        Args:
            template_id: Template ID to update
            updates: Dictionary of field names to new values

        Returns:
            Updated PdfTemplateMetadata or None if template not found
        """
        with self._get_session() as session:
            # Fetch template
            template = session.get(self.model_class, template_id)

            if template is None:
                raise ObjectNotFoundError(f"Template {template_id} not found")

            # Apply updates
            for field, value in updates.items():
                setattr(template, field, value)

            # Commit changes
            session.commit()
            session.refresh(template)

            return self._model_to_template(template)
