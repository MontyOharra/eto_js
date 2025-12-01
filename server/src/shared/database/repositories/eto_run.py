"""
ETO Run Repository
Repository for eto_runs table with CRUD operations
"""
import logging
import json
from typing import Type, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload

from shared.database.repositories.base import BaseRepository
from shared.exceptions.service import ObjectNotFoundError
from shared.database.models import (
    EtoRunModel,
    PdfFileModel,
    EmailModel,
    EtoSubRunModel,
    PdfTemplateVersionModel,
    PdfTemplateModel,
)
from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunListView,
    EtoRunDetailView,
)
from shared.types.eto_sub_runs import EtoSubRunDetailView

logger = logging.getLogger(__name__)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """
    Repository for ETO run CRUD operations.

    Handles:
    - Basic CRUD for eto_runs table (parent orchestration level)
    - Conversion between ORM models and domain dataclasses
    - Query operations for worker (finding not_started runs)
    - Aggregating sub-run data for list and detail views

    Note: Sub-run data managed by separate repositories:
    - EtoSubRunRepository (for sub-runs and their page sets)
    - EtoSubRunExtractionRepository
    - EtoSubRunPipelineExecutionRepository
    """

    @property
    def model_class(self) -> Type[EtoRunModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoRunModel) -> EtoRun:
        """
        Convert ORM model to EtoRun dataclass.

        Status fields are plain strings (no enum conversion needed).
        """
        return EtoRun(
            id=model.id,
            pdf_file_id=model.pdf_file_id,
            source_type=model.source_type,
            source_email_id=model.source_email_id,
            status=model.status,
            processing_step=model.processing_step,
            is_read=model.is_read,
            error_type=model.error_type,
            error_message=model.error_message,
            error_details=model.error_details,
            started_at=model.started_at,
            completed_at=model.completed_at,
            last_processed_at=model.last_processed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunCreate) -> EtoRun:
        """
        Create new ETO run with status = "not_started".

        Args:
            data: EtoRunCreate with pdf_file_id, source_type, and source_email_id

        Returns:
            Created EtoRun dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                pdf_file_id=data.pdf_file_id,
                source_type=data.source_type,
                source_email_id=data.source_email_id,
                # status defaults to NOT_STARTED via model default
                # processing_step defaults to None
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, run_id: int) -> Optional[EtoRun]:
        """
        Get ETO run by ID.

        Args:
            run_id: ETO run ID

        Returns:
            EtoRun dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, run_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, run_id: int, updates: EtoRunUpdate) -> EtoRun:
        """
        Update ETO run. Only updates provided fields.

        Uses dict keys to distinguish between:
        - Field not provided (key absent) - field will not be updated
        - Field explicitly set to None (key present, value None) - field will be cleared in database
        - Field set to value (key present) - field will be updated to that value

        Args:
            run_id: ETO run ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated EtoRun dataclass

        Raises:
            ObjectNotFoundError: If run with given ID does not exist
            ValueError: If invalid field name provided

        Example:
            update(1, {"status": "success"})
            update(1, {"processing_step": None, "error_type": None})
        """
        with self._get_session() as session:
            model = session.get(self.model_class, run_id)

            if model is None:
                raise ObjectNotFoundError(f"ETO run {run_id} not found")

            # Update only provided fields (iterate over dict keys)
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for ETO run update: {field}")
                setattr(model, field, value)

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_all(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[EtoRun]:
        """
        Get all ETO runs with optional filtering, pagination, and sorting.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            order_by: Field to order by (default: created_at)
            desc: Sort descending if True (default: True - newest first)

        Returns:
            List of EtoRun dataclasses
        """
        with self._get_session() as session:
            # Build base query
            query = session.query(self.model_class)

            # Apply status filter if provided
            if status is not None:
                query = query.filter_by(status=status)

            # Apply ordering
            if hasattr(self.model_class, order_by):
                order_column = getattr(self.model_class, order_by)
                if desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            else:
                logger.warning(f"Field '{order_by}' does not exist on {self.model_class.__name__}, using created_at")
                query = query.order_by(self.model_class.created_at.desc())

            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            # Execute and convert
            models = query.all()
            return [self._model_to_domain(model) for model in models]

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoRun]:
        """
        Get ETO runs by status.
        Used by worker to find runs that need processing.

        Args:
            status: Status to filter by (e.g., "not_started")
            limit: Optional limit on number of results

        Returns:
            List of EtoRun dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def delete(self, run_id: int) -> None:
        """
        Delete ETO run by ID.

        Args:
            run_id: ETO run ID

        Raises:
            ObjectNotFoundError: If run with given ID does not exist
        """
        with self._get_session() as session:
            model = session.get(self.model_class, run_id)

            if model is None:
                raise ObjectNotFoundError(f"ETO run {run_id} not found")

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted ETO run {run_id}")

    def get_all_with_relations(
        self,
        is_read: Optional[bool] = None,
        has_sub_run_status: Optional[str] = None,
        search_query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "last_processed_at",
        desc: bool = True
    ) -> List[EtoRunListView]:
        """
        Get all ETO runs with aggregated sub-run data.

        Performs JOINs and aggregates to collect:
        - pdf_files (required)
        - emails (optional - NULL for manual uploads)
        - eto_sub_runs (aggregated counts and page arrays)

        Args:
            is_read: Filter by read status (optional)
            has_sub_run_status: Filter runs that have at least one sub-run with this status
                               (e.g., "needs_template", "failure")
            search_query: Search in filename, email sender, and subject (optional)
            date_from: Filter runs created on or after this date (optional)
            date_to: Filter runs created on or before this date (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            order_by: Field to order by (default: last_processed_at)
            desc: Sort descending if True (default: True - newest first)

        Returns:
            List of EtoRunListView dataclasses with aggregated sub-run data
        """
        from sqlalchemy import func, case, exists, and_, or_, select

        with self._get_session() as session:
            # First, get base run data with PDF and email info
            base_query = (
                session.query(
                    # ETO run fields
                    EtoRunModel.id,
                    EtoRunModel.source_type,
                    EtoRunModel.source_email_id,
                    EtoRunModel.status,
                    EtoRunModel.processing_step,
                    EtoRunModel.is_read,
                    EtoRunModel.started_at,
                    EtoRunModel.completed_at,
                    EtoRunModel.last_processed_at,
                    EtoRunModel.error_type,
                    EtoRunModel.error_message,
                    EtoRunModel.created_at,
                    EtoRunModel.updated_at,
                    # PDF file fields
                    PdfFileModel.id.label("pdf_file_id"),
                    PdfFileModel.original_filename,
                    PdfFileModel.file_size,
                    PdfFileModel.page_count,
                    # Email fields (optional) - now joined via eto_runs.source_email_id
                    EmailModel.id.label("email_id"),
                    EmailModel.sender_email,
                    EmailModel.received_date,
                    EmailModel.subject,
                    EmailModel.folder_name,
                )
                .join(PdfFileModel, EtoRunModel.pdf_file_id == PdfFileModel.id)
                .outerjoin(EmailModel, EtoRunModel.source_email_id == EmailModel.id)
            )

            # Apply is_read filter
            if is_read is not None:
                base_query = base_query.filter(EtoRunModel.is_read == is_read)

            # Apply sub-run status filter (runs that have at least one sub-run with this status)
            if has_sub_run_status is not None:
                exists_subquery = exists().where(
                    and_(
                        EtoSubRunModel.eto_run_id == EtoRunModel.id,
                        EtoSubRunModel.status == has_sub_run_status
                    )
                )
                base_query = base_query.filter(exists_subquery)

            # Apply search filter
            if search_query:
                search_pattern = f"%{search_query}%"
                base_query = base_query.filter(
                    or_(
                        PdfFileModel.original_filename.ilike(search_pattern),
                        EmailModel.sender_email.ilike(search_pattern),
                        EmailModel.subject.ilike(search_pattern),
                    )
                )

            # Apply date range filters (on created_at)
            if date_from is not None:
                base_query = base_query.filter(EtoRunModel.created_at >= date_from)
            if date_to is not None:
                base_query = base_query.filter(EtoRunModel.created_at <= date_to)

            # Apply ordering - handle special sort fields from joined tables
            if order_by == "pdf_filename":
                order_column = PdfFileModel.original_filename
            elif order_by == "received_at":
                # Use email received_date if available, otherwise fall back to created_at
                order_column = func.coalesce(EmailModel.received_date, EtoRunModel.created_at)
            elif hasattr(EtoRunModel, order_by):
                order_column = getattr(EtoRunModel, order_by)
            else:
                logger.warning(f"Field '{order_by}' does not exist on EtoRunModel, using last_processed_at")
                order_column = EtoRunModel.last_processed_at

            if desc:
                base_query = base_query.order_by(order_column.desc())
            else:
                base_query = base_query.order_by(order_column)

            # Apply pagination
            if offset is not None:
                base_query = base_query.offset(offset)
            if limit is not None:
                base_query = base_query.limit(limit)

            # Execute query
            rows = base_query.all()

            # For each run, fetch and aggregate sub-run data
            result = []
            for row in rows:
                # Query sub-runs for this run to get aggregations
                sub_runs = (
                    session.query(EtoSubRunModel)
                    .filter(EtoSubRunModel.eto_run_id == row.id)
                    .all()
                )

                # Aggregate sub-run counts
                sub_run_success_count = sum(1 for sr in sub_runs if sr.status == "success")
                sub_run_failure_count = sum(1 for sr in sub_runs if sr.status == "failure")
                sub_run_needs_template_count = sum(1 for sr in sub_runs if sr.status == "needs_template")
                sub_run_skipped_count = sum(1 for sr in sub_runs if sr.status == "skipped")

                # Aggregate page arrays
                pages_matched = []
                pages_unmatched = []
                pages_skipped = []

                for sr in sub_runs:
                    # Parse matched_pages JSON string
                    try:
                        pages = json.loads(sr.matched_pages) if sr.matched_pages else []

                        if sr.status == "skipped":
                            pages_skipped.extend(pages)
                        elif sr.status == "needs_template":
                            pages_unmatched.extend(pages)
                        else:  # Has template (success, failure, matched, processing, not_started)
                            pages_matched.extend(pages)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse matched_pages for sub-run {sr.id}: {e}")

                result.append(EtoRunListView(
                    # Core ETO run fields
                    id=row.id,
                    source_type=row.source_type,
                    source_email_id=row.source_email_id,
                    status=row.status,
                    processing_step=row.processing_step,
                    is_read=row.is_read,
                    started_at=row.started_at,
                    completed_at=row.completed_at,
                    error_type=row.error_type,
                    error_message=row.error_message,
                    # PDF file info
                    pdf_file_id=row.pdf_file_id,
                    pdf_original_filename=row.original_filename,
                    pdf_file_size=row.file_size,
                    pdf_page_count=row.page_count,
                    # Source info (email fields - all None if manual upload)
                    email_id=row.email_id,
                    email_sender_email=row.sender_email,
                    email_received_date=row.received_date,
                    email_subject=row.subject,
                    email_folder_name=row.folder_name,
                    # Sub-run aggregations
                    sub_run_success_count=sub_run_success_count,
                    sub_run_failure_count=sub_run_failure_count,
                    sub_run_needs_template_count=sub_run_needs_template_count,
                    sub_run_skipped_count=sub_run_skipped_count,
                    # Page arrays
                    pages_matched=pages_matched,
                    pages_unmatched=pages_unmatched,
                    pages_skipped=pages_skipped,
                    # Timestamps
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    last_processed_at=row.last_processed_at,
                ))

            return result

    def get_detail_with_stages(self, run_id: int) -> Optional[EtoRunDetailView]:
        """
        Get complete ETO run detail with all sub-runs.

        Fetches:
        - Core ETO run data
        - PDF file (required)
        - Email (optional)
        - All sub-runs with their complete detail views (template, extraction, pipeline stages)

        Args:
            run_id: ETO run ID

        Returns:
            EtoRunDetailView with all sub-run data or None if run not found
        """
        with self._get_session() as session:
            # Get base run data with PDF and email
            row = (
                session.query(
                    # ETO run fields
                    EtoRunModel.id,
                    EtoRunModel.source_type,
                    EtoRunModel.source_email_id,
                    EtoRunModel.status,
                    EtoRunModel.processing_step,
                    EtoRunModel.is_read,
                    EtoRunModel.started_at,
                    EtoRunModel.completed_at,
                    EtoRunModel.error_type,
                    EtoRunModel.error_message,
                    EtoRunModel.error_details,
                    EtoRunModel.created_at,
                    EtoRunModel.updated_at,
                    # PDF file fields
                    PdfFileModel.id.label("pdf_file_id"),
                    PdfFileModel.original_filename,
                    PdfFileModel.file_size,
                    PdfFileModel.page_count,
                    # Email fields (optional) - now joined via eto_runs.source_email_id
                    EmailModel.id.label("email_id"),
                    EmailModel.sender_email,
                    EmailModel.received_date,
                    EmailModel.subject,
                    EmailModel.folder_name,
                )
                .join(PdfFileModel, EtoRunModel.pdf_file_id == PdfFileModel.id)
                .outerjoin(EmailModel, EtoRunModel.source_email_id == EmailModel.id)
                .filter(EtoRunModel.id == run_id)
                .first()
            )

            if row is None:
                return None

            # Fetch all sub-runs for this run using the sub-run repository
            from shared.database.repositories.eto_sub_run import EtoSubRunRepository
            sub_run_repo = EtoSubRunRepository(session)

            # Get all sub-runs (will be sorted by page number by sub_run_repo)
            sub_run_models = (
                session.query(EtoSubRunModel)
                .filter(EtoSubRunModel.eto_run_id == run_id)
                .order_by(EtoSubRunModel.created_at.asc())  # Fallback ordering
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

            sub_run_models.sort(key=get_first_page)

            # Convert each sub-run to detail view using the repository method
            sub_runs_detail = []
            for sub_run_model in sub_run_models:
                sub_run_detail = sub_run_repo.get_detail_view(sub_run_model.id)
                if sub_run_detail:
                    sub_runs_detail.append(sub_run_detail)

            # Build final EtoRunDetailView
            return EtoRunDetailView(
                # Core run data
                id=row.id,
                source_type=row.source_type,
                source_email_id=row.source_email_id,
                status=row.status,
                processing_step=row.processing_step,
                is_read=row.is_read,
                started_at=row.started_at,
                completed_at=row.completed_at,
                error_type=row.error_type,
                error_message=row.error_message,
                error_details=row.error_details,
                # PDF file info
                pdf_file_id=row.pdf_file_id,
                pdf_original_filename=row.original_filename,
                pdf_file_size=row.file_size,
                pdf_page_count=row.page_count,
                # Email info (optional)
                email_id=row.email_id,
                email_sender_email=row.sender_email,
                email_received_date=row.received_date,
                email_subject=row.subject,
                email_folder_name=row.folder_name,
                # Sub-runs (list of all sub-runs with their stages)
                sub_runs=sub_runs_detail,
                # Timestamps
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            
            
    def mark_as_read(self, run_id: int) -> None:
        """
        Mark an ETO run as read.

        Args:
            run_id: ETO run ID

        Raises:
            ObjectNotFoundError: If run not found
        """
        self.update(run_id, {"is_read": True})
        logger.debug(f"Marked ETO run {run_id} as read")

    def mark_as_unread(self, run_id: int) -> None:
        """
        Mark an ETO run as unread.

        Args:
            run_id: ETO run ID

        Raises:
            ObjectNotFoundError: If run not found
        """
        self.update(run_id, {"is_read": False})
        logger.debug(f"Marked ETO run {run_id} as unread")