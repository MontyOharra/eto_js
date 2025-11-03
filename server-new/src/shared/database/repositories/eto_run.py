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
    EtoRunTemplateMatchingModel,
    EtoRunExtractionModel,
    EtoRunPipelineExecutionModel,
    PdfTemplateVersionModel,
    PdfTemplateModel,
)
from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunListView,
    EtoRunDetailView,
    EtoRunTemplateMatchingDetailView,
    EtoRunExtractionDetailView,
    EtoRunPipelineExecutionDetailView,
)

from shared.types.pdf_templates import ExtractionField

logger = logging.getLogger(__name__)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """
    Repository for ETO run CRUD operations.

    Handles:
    - Basic CRUD for eto_runs table
    - Conversion between ORM models and domain dataclasses
    - Query operations for worker (finding not_started runs)

    Note: Stage-specific data managed by separate repositories:
    - EtoRunTemplateMatchingRepository
    - EtoRunExtractionRepository
    - EtoRunPipelineExecutionRepository
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
            status=model.status,
            processing_step=model.processing_step,
            error_type=model.error_type,
            error_message=model.error_message,
            error_details=model.error_details,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunCreate) -> EtoRun:
        """
        Create new ETO run with status = "not_started".

        Args:
            data: EtoRunCreate with pdf_file_id

        Returns:
            Created EtoRun dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                pdf_file_id=data.pdf_file_id,
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
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[EtoRunListView]:
        """
        Get all ETO runs with all related data in a single query.

        Performs LEFT JOINs to collect data from:
        - pdf_files (required)
        - emails (optional - NULL for manual uploads)
        - eto_run_template_matchings (optional - NULL if no match)
        - pdf_template_versions (optional - NULL if no version)
        - pdf_templates (optional - NULL if no template)

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            order_by: Field to order by (default: created_at)
            desc: Sort descending if True (default: True - newest first)

        Returns:
            List of EtoRunListView dataclasses with all joined data
        """
        with self._get_session() as session:
            # Build query with LEFT JOINs
            query = (
                session.query(
                    # ETO run fields
                    EtoRunModel.id,
                    EtoRunModel.status,
                    EtoRunModel.processing_step,
                    EtoRunModel.started_at,
                    EtoRunModel.completed_at,
                    EtoRunModel.error_type,
                    EtoRunModel.error_message,
                    # PDF file fields
                    PdfFileModel.id.label("pdf_file_id"),
                    PdfFileModel.original_filename,
                    PdfFileModel.file_size,
                    PdfFileModel.page_count,
                    # Email fields (optional)
                    EmailModel.id.label("email_id"),
                    EmailModel.sender_email,
                    EmailModel.received_date,
                    EmailModel.subject,
                    EmailModel.folder_name,
                    # Template matching fields (optional)
                    PdfTemplateModel.id.label("template_id"),
                    PdfTemplateModel.name.label("template_name"),
                    PdfTemplateVersionModel.id.label("template_version_id"),
                    PdfTemplateVersionModel.version_num,
                )
                .join(PdfFileModel, EtoRunModel.pdf_file_id == PdfFileModel.id)
                .outerjoin(EmailModel, PdfFileModel.email_id == EmailModel.id)
                .outerjoin(
                    EtoRunTemplateMatchingModel,
                    EtoRunModel.id == EtoRunTemplateMatchingModel.eto_run_id
                )
                .outerjoin(
                    PdfTemplateVersionModel,
                    EtoRunTemplateMatchingModel.matched_template_version_id == PdfTemplateVersionModel.id
                )
                .outerjoin(
                    PdfTemplateModel,
                    PdfTemplateVersionModel.pdf_template_id == PdfTemplateModel.id
                )
            )

            # Apply status filter if provided
            if status is not None:
                query = query.filter(EtoRunModel.status == status)

            # Apply ordering
            if hasattr(EtoRunModel, order_by):
                order_column = getattr(EtoRunModel, order_by)
                if desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            else:
                logger.warning(f"Field '{order_by}' does not exist on EtoRunModel, using created_at")
                query = query.order_by(EtoRunModel.created_at.desc())

            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            # Execute query
            rows = query.all()

            # Convert rows to EtoRunListView dataclasses
            return [
                EtoRunListView(
                    # Core ETO run fields
                    id=row.id,
                    status=row.status,  # Enum to string
                    processing_step=row.processing_step if row.processing_step else None,  # Enum to string
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
                    # Matched template info (all None if no successful match)
                    template_id=row.template_id,
                    template_name=row.template_name,
                    template_version_id=row.template_version_id,
                    template_version_num=row.version_num,
                )
                for row in rows
            ]

    def get_detail_with_stages(self, run_id: int) -> Optional[EtoRunDetailView]:
        """
        Get complete ETO run detail with all stage data using SQLAlchemy joins.

        Performs single query with LEFT JOINs to fetch:
        - Core ETO run data
        - PDF file (required)
        - Email (optional)
        - Template matching stage (optional)
        - Extraction stage (optional)
        - Pipeline execution stage (optional)
        - Template name/version for denormalization (optional)

        Parses JSON fields and constructs detailed view dataclasses.

        Args:
            run_id: ETO run ID

        Returns:
            EtoRunDetailView with all data or None if run not found
        """
        with self._get_session() as session:
            row = (
                session.query(
                    # ETO run fields
                    EtoRunModel.id,
                    EtoRunModel.status,
                    EtoRunModel.processing_step,
                    EtoRunModel.started_at,
                    EtoRunModel.completed_at,
                    EtoRunModel.error_type,
                    EtoRunModel.error_message,
                    EtoRunModel.error_details,
                    EtoRunModel.created_at,
                    # PDF file fields
                    PdfFileModel.id.label("pdf_file_id"),
                    PdfFileModel.original_filename,
                    PdfFileModel.file_size,
                    PdfFileModel.page_count,
                    # Email fields (optional)
                    EmailModel.id.label("email_id"),
                    EmailModel.sender_email,
                    EmailModel.received_date,
                    EmailModel.subject,
                    EmailModel.folder_name,
                    # Template matching fields (optional)
                    EtoRunTemplateMatchingModel.status.label("tm_status"),
                    EtoRunTemplateMatchingModel.matched_template_version_id,
                    EtoRunTemplateMatchingModel.started_at.label("tm_started_at"),
                    EtoRunTemplateMatchingModel.completed_at.label("tm_completed_at"),
                    # Template denormalization fields (optional)
                    PdfTemplateModel.name.label("template_name"),
                    PdfTemplateVersionModel.version_num.label("template_version_num"),
                    # Extraction fields (optional)
                    EtoRunExtractionModel.status.label("ex_status"),
                    EtoRunExtractionModel.extracted_data,
                    EtoRunExtractionModel.started_at.label("ex_started_at"),
                    EtoRunExtractionModel.completed_at.label("ex_completed_at"),
                    # Pipeline execution fields (optional)
                    EtoRunPipelineExecutionModel.status.label("pe_status"),
                    EtoRunPipelineExecutionModel.executed_actions,
                    EtoRunPipelineExecutionModel.started_at.label("pe_started_at"),
                    EtoRunPipelineExecutionModel.completed_at.label("pe_completed_at"),
                )
                .join(PdfFileModel, EtoRunModel.pdf_file_id == PdfFileModel.id)
                .outerjoin(EmailModel, PdfFileModel.email_id == EmailModel.id)
                .outerjoin(
                    EtoRunTemplateMatchingModel,
                    EtoRunTemplateMatchingModel.eto_run_id == EtoRunModel.id
                )
                .outerjoin(
                    PdfTemplateVersionModel,
                    PdfTemplateVersionModel.id == EtoRunTemplateMatchingModel.matched_template_version_id
                )
                .outerjoin(
                    PdfTemplateModel,
                    PdfTemplateModel.id == PdfTemplateVersionModel.pdf_template_id
                )
                .outerjoin(
                    EtoRunExtractionModel,
                    EtoRunExtractionModel.eto_run_id == EtoRunModel.id
                )
                .outerjoin(
                    EtoRunPipelineExecutionModel,
                    EtoRunPipelineExecutionModel.eto_run_id == EtoRunModel.id
                )
                .filter(EtoRunModel.id == run_id)
                .first()
            )

            if row is None:
                return None

            # Build template matching detail view if stage exists
            template_matching_detail = None
            if row.tm_status:
                template_matching_detail = EtoRunTemplateMatchingDetailView(
                    status=row.tm_status,
                    matched_template_version_id=row.matched_template_version_id,
                    started_at=row.tm_started_at,
                    completed_at=row.tm_completed_at,
                    matched_template_name=row.template_name,
                    matched_version_number=row.template_version_num,
                )

            # Build extraction detail view if stage exists
            extraction_detail = None
            if row.ex_status:
                # Parse extracted_data JSON string to dict
                extracted_dict = None
                if row.extracted_data:
                    try:
                        extracted_dict = json.loads(row.extracted_data)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(
                            f"Failed to parse extracted_data for run {run_id}: {e}"
                        )

                extraction_detail = EtoRunExtractionDetailView(
                    status=row.ex_status,
                    started_at=row.ex_started_at,
                    completed_at=row.ex_completed_at,
                    extracted_data=extracted_dict,
                )

            # Build pipeline execution detail view if stage exists
            pipeline_execution_detail = None
            if row.pe_status:
                # Parse executed_actions JSON string to dict
                actions_dict = None
                if row.executed_actions:
                    try:
                        actions_dict = json.loads(row.executed_actions)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(
                            f"Failed to parse executed_actions for run {run_id}: {e}"
                        )

                pipeline_execution_detail = EtoRunPipelineExecutionDetailView(
                    status=row.pe_status,
                    started_at=row.pe_started_at,
                    completed_at=row.pe_completed_at,
                    executed_actions=actions_dict,
                )

            # Build final EtoRunDetailView
            return EtoRunDetailView(
                # Core run data
                id=row.id,
                status=row.status,
                processing_step=row.processing_step if row.processing_step else None,
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
                # Stage data (optional)
                template_matching=template_matching_detail,
                extraction=extraction_detail,
                pipeline_execution=pipeline_execution_detail,
                # Denormalized template info at root level (convenience)
                matched_template_id=row.matched_template_version_id,
                matched_template_name=row.template_name,
                matched_template_version_id=row.matched_template_version_id,
                matched_template_version_num=row.template_version_num,
            )
            
            
    def get_matched_template_extraction_fields(self, run_if: int) -> Optional[List[ExtractionField]]:
        with self._get_session() as session:
            row = (
                
            )