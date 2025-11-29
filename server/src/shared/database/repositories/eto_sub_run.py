"""
ETO Sub-Run Repository
Repository for eto_sub_runs table with CRUD operations

Sub-runs represent page-set business logic units within a parent ETO run.
"""
import logging
import json
from typing import Type, Optional, List
from datetime import datetime

from shared.database.repositories.base import BaseRepository
from shared.database.models import (
    EtoSubRunModel,
    EtoRunModel,
    PdfFileModel,
    PdfTemplateModel,
    PdfTemplateVersionModel,
)
from shared.types.eto_sub_runs import (
    EtoSubRun,
    EtoSubRunCreate,
    EtoSubRunUpdate,
    EtoSubRunDetailView,
)
from shared.exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


class EtoSubRunRepository(BaseRepository[EtoSubRunModel]):
    """
    Repository for ETO sub-run CRUD operations.

    Handles:
    - Basic CRUD for eto_sub_runs table
    - Conversion between ORM models and domain dataclasses
    - Query operations (get by eto_run_id, status)
    - Detail view with joined template and stage data
    """

    @property
    def model_class(self) -> Type[EtoSubRunModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoSubRunModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoSubRunModel) -> EtoSubRun:
        """
        Convert ORM model to EtoSubRun dataclass.

        Status field is plain string (no enum conversion needed).
        matched_pages is kept as JSON string (parsed in detail views).
        """
        return EtoSubRun(
            id=model.id,
            eto_run_id=model.eto_run_id,
            matched_pages=model.matched_pages,
            template_version_id=model.template_version_id,
            status=model.status,
            error_type=model.error_type,
            error_message=model.error_message,
            error_details=model.error_details,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoSubRunCreate) -> EtoSubRun:
        """
        Create new ETO sub-run with status = "not_started".

        Args:
            data: EtoSubRunCreate with required fields

        Returns:
            Created EtoSubRun dataclass
        """
        with self._get_session() as session:
            # Create model
            model = self.model_class(
                eto_run_id=data.eto_run_id,
                matched_pages=data.matched_pages,
                template_version_id=data.template_version_id,
                # status defaults to "not_started" via model default
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, sub_run_id: int) -> Optional[EtoSubRun]:
        """
        Get ETO sub-run by ID.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            EtoSubRun dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, sub_run_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, sub_run_id: int, updates: EtoSubRunUpdate) -> EtoSubRun:
        """
        Update ETO sub-run. Only updates provided fields.

        Uses dict keys to distinguish between:
        - Field not provided (key absent) - field will not be updated
        - Field explicitly set to None (key present, value None) - field will be cleared in database
        - Field set to value (key present) - field will be updated to that value

        Args:
            sub_run_id: Sub-run ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated EtoSubRun dataclass

        Raises:
            ObjectNotFoundError: If sub-run not found
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, sub_run_id)

            if model is None:
                raise ObjectNotFoundError(f"ETO sub-run {sub_run_id} not found")

            # Update only provided fields (iterate over dict keys)
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for sub-run update: {field}")
                setattr(model, field, value)

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    def delete(self, sub_run_id: int) -> None:
        """
        Delete ETO sub-run by ID.
        Cascade deletes extraction and pipeline execution records.

        Args:
            sub_run_id: Sub-run ID

        Raises:
            ObjectNotFoundError: If sub-run not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, sub_run_id)

            if model is None:
                raise ObjectNotFoundError(f"ETO sub-run {sub_run_id} not found")

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted ETO sub-run {sub_run_id}")

    # ========== Query Operations ==========

    def get_by_eto_run_id(self, eto_run_id: int) -> List[EtoSubRun]:
        """
        Get all sub-runs for a parent ETO run, ordered by first page number.

        Args:
            eto_run_id: Parent ETO run ID

        Returns:
            List of EtoSubRun dataclasses, ordered by first page in matched_pages
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter_by(eto_run_id=eto_run_id)
                .order_by(self.model_class.created_at.asc())  # Fallback ordering
                .all()
            )

            # Sort by first page number in matched_pages JSON
            import json
            def get_first_page(model):
                try:
                    pages = json.loads(model.matched_pages)
                    return min(pages) if pages else float('inf')
                except:
                    return float('inf')

            models.sort(key=get_first_page)

            return [self._model_to_domain(model) for model in models]

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoSubRun]:
        """
        Get sub-runs by status.
        Used by worker to find sub-runs that need processing.

        Args:
            status: Status to filter by (e.g., "not_started", "processing")
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRun dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_by_status_no_template(self, status: str, limit: Optional[int] = None) -> List[EtoSubRun]:
        """
        Get sub-runs by status that have no template assigned.
        Used by worker Phase 1 to find sub-runs needing template matching.

        Args:
            status: Status to filter by (e.g., "not_started")
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRun dataclasses with template_version_id IS NULL
        """
        with self._get_session() as session:
            query = (
                session.query(self.model_class)
                .filter(
                    self.model_class.status == status,
                    self.model_class.template_version_id.is_(None)
                )
            )

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_by_status_with_template(self, status: str, limit: Optional[int] = None) -> List[EtoSubRun]:
        """
        Get sub-runs by status that have a template assigned.
        Used by worker Phase 2 to find sub-runs ready for extraction + pipeline.

        Args:
            status: Status to filter by (e.g., "matched")
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRun dataclasses with template_version_id IS NOT NULL
        """
        with self._get_session() as session:
            query = (
                session.query(self.model_class)
                .filter(
                    self.model_class.status == status,
                    self.model_class.template_version_id.isnot(None)
                )
            )

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_needs_template_for_run(self, eto_run_id: int) -> List[EtoSubRun]:
        """
        Get sub-runs that need templates for a parent ETO run.

        Args:
            eto_run_id: Parent ETO run ID

        Returns:
            List of EtoSubRun dataclasses with status='needs_template'
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter_by(eto_run_id=eto_run_id, status='needs_template')
                .all()
            )

            return [self._model_to_domain(model) for model in models]

    def get_detail_view(self, sub_run_id: int) -> Optional[EtoSubRunDetailView]:
        """
        Get complete sub-run detail with all stage data using SQLAlchemy joins.

        Performs single query with LEFT JOINs to fetch:
        - Core sub-run data
        - Template info (if template_version_id is not NULL)
        - PDF file info (from parent run)
        - Extraction stage (from eto_sub_run_extractions)
        - Pipeline execution stage (from eto_sub_run_pipeline_executions)

        Parses JSON fields and constructs detailed view dataclass.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            EtoSubRunDetailView with all data or None if sub-run not found
        """
        # TODO: Implement once eto_sub_run_extractions and eto_sub_run_pipeline_executions
        # tables exist and their repositories are created

        # For now, return basic sub-run data without stages
        with self._get_session() as session:
            # Get sub-run with template and PDF info
            row = (
                session.query(
                    # Sub-run fields
                    EtoSubRunModel.id,
                    EtoSubRunModel.eto_run_id,
                    EtoSubRunModel.matched_pages,
                    EtoSubRunModel.status,
                    EtoSubRunModel.template_version_id,
                    EtoSubRunModel.error_type,
                    EtoSubRunModel.error_message,
                    EtoSubRunModel.error_details,
                    EtoSubRunModel.started_at,
                    EtoSubRunModel.completed_at,
                    EtoSubRunModel.created_at,
                    EtoSubRunModel.updated_at,
                    # Template info (optional)
                    PdfTemplateModel.id.label("template_id"),
                    PdfTemplateModel.name.label("template_name"),
                    PdfTemplateVersionModel.version_num.label("template_version_num"),
                    # PDF file info
                    PdfFileModel.id.label("pdf_file_id"),
                    PdfFileModel.original_filename,
                    PdfFileModel.file_size,
                    PdfFileModel.page_count,
                )
                .outerjoin(
                    PdfTemplateVersionModel,
                    EtoSubRunModel.template_version_id == PdfTemplateVersionModel.id
                )
                .outerjoin(
                    PdfTemplateModel,
                    PdfTemplateVersionModel.pdf_template_id == PdfTemplateModel.id
                )
                # Join to parent EtoRun first, then to PdfFile
                .join(
                    EtoRunModel,
                    EtoSubRunModel.eto_run_id == EtoRunModel.id
                )
                .join(
                    PdfFileModel,
                    EtoRunModel.pdf_file_id == PdfFileModel.id
                )
                .filter(EtoSubRunModel.id == sub_run_id)
                .first()
            )

            if row is None:
                return None

            # Parse matched_pages JSON
            matched_pages_list = []
            try:
                matched_pages_list = json.loads(row.matched_pages)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse matched_pages for sub-run {sub_run_id}: {e}")

            # Build detail view
            return EtoSubRunDetailView(
                # Core sub-run data
                id=row.id,
                eto_run_id=row.eto_run_id,
                matched_pages=matched_pages_list,
                status=row.status,
                # Template info (None for unmatched)
                template_id=row.template_id,
                template_name=row.template_name,
                template_version_id=row.template_version_id,
                template_version_num=row.template_version_num,
                # PDF info
                pdf_file_id=row.pdf_file_id,
                pdf_original_filename=row.original_filename,
                pdf_file_size=row.file_size,
                pdf_page_count=row.page_count,
                # Stage data (TODO: fetch and add)
                extraction=None,
                pipeline_execution=None,
                # Error tracking
                error_type=row.error_type,
                error_message=row.error_message,
                error_details=row.error_details,
                # Timestamps
                started_at=row.started_at,
                completed_at=row.completed_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
