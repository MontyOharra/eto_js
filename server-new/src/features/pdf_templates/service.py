"""
PDF Template Service
Outward-facing service for managing PDF template CRUD and lifecycle
"""
import logging
from typing import Literal, Any

from shared.database import DatabaseConnectionManager
from shared.database.repositories import (
    PdfTemplateRepository,
    PdfTemplateVersionRepository,
    PipelineDefinitionRepository,
)
from shared.types.pdf_templates import (
    PdfTemplateListView,
    PdfTemplate,
    PdfTemplateCreate,
    PdfTemplateUpdate,
    PdfTemplateVersion,
    PdfVersionSummary,
)
from shared.exceptions.service import ObjectNotFoundError, ConflictError, ServiceError
from features.pipelines.service import PipelineService

logger = logging.getLogger(__name__)


class PdfTemplateService:
    """
    PDF template management service.

    Handles CRUD operations and lifecycle management for PDF templates and versions.
    Manages template activation/deactivation and version history.
    """

    connection_manager: DatabaseConnectionManager
    template_repository: PdfTemplateRepository
    version_repository: PdfTemplateVersionRepository
    pipeline_repository: PipelineDefinitionRepository

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        pipeline_service: 'PipelineService'
    ) -> None:
        """
        Initialize PDF template service

        Args:
            connection_manager: Database connection manager
            pipeline_service: Pipeline service for pipeline operations
        """
        self.connection_manager = connection_manager
        self.template_repository = PdfTemplateRepository(connection_manager=connection_manager)
        self.version_repository = PdfTemplateVersionRepository(connection_manager=connection_manager)
        self.pipeline_repository = PipelineDefinitionRepository(connection_manager=connection_manager)
        self.pipeline_service = pipeline_service

    def list_templates(
        self,
        status: Literal["active", "inactive"] | None = None,
        sort_by: Literal["name", "status", "usage_count"] = "name",
        sort_order: Literal["asc", "desc"] = "asc"
    ) -> list[PdfTemplateListView]:
        """
        List PDF templates with filtering and sorting.

        Args:
            status: Filter by status ("active" or "inactive"), None for all
            sort_by: Field to sort by ("name", "status", "usage_count")
            sort_order: Sort direction ("asc" or "desc")

        Returns:
            List of PdfTemplateListView
        """
        # Parameters are validated by Pydantic at API layer
        # Just delegate to repository
        return self.template_repository.list_templates(
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )

    def get_template(self, template_id: int) -> PdfTemplate:
        """
        Get PDF template metadata by ID.

        Args:
            template_id: Template ID

        Returns:
            PdfTemplate dataclass or None if not found
        """
        result = self.template_repository.get_by_id(template_id)

        if not result:
            raise ObjectNotFoundError(f"Template {template_id} not found")
        
        return result

    def get_version_list(self, template_id: int) -> list[tuple[int, int]]:
        """
        Get list of all version IDs and version numbers for a template.

        Used by GET /api/pdf-templates/{template_id}/versions endpoint.

        Args:
            template_id: Template ID

        Returns:
            List of tuples (version_id, version_number) ordered by version_number ASC

        Raises:
            ObjectNotFoundError: If template not found
        """
        # Verify template exists
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Get version list from repository
        return self.version_repository.get_version_list_for_template(template_id)

    def get_version_by_id(self, version_id: int) -> PdfTemplateVersion:
        """
        Get specific version details by version ID.

        Used by GET /api/pdf-templates/versions/{version_id} endpoint.
        Called when viewing template details (current version) or switching versions.

        Args:
            version_id: Version record ID

        Returns:
            PdfTemplateVersion dataclass with full version details

        Raises:
            ObjectNotFoundError: If version not found
        """
        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ObjectNotFoundError(f"Version {version_id} not found")

        return version

    def update_template(
        self,
        template_id: int,
        update_data: PdfTemplateUpdate
    ) -> tuple[PdfTemplate, int, int]:
        """
        Update template with smart versioning logic.

        Flow:
        1. Simple Case: Only name/description changed
           → Update template table directly, return

        2. Version Case: signature_objects or extraction_fields changed (no pipeline)
           → Create new version with current pipeline_definition_id, return

        3. Complex Case: Pipeline fields changed
           → Validate/compile pipeline → Create pipeline_definition + compiled_plan + steps
           → Create new version with new pipeline_definition_id, return

        Args:
            template_id: Template ID to update
            update_data: Unified PdfTemplateUpdate with all possible fields

        Returns:
            Tuple of (updated_template, current_version_num, pipeline_definition_id)

        Raises:
            ObjectNotFoundError: Template not found
            ConflictError: Template is active and wizard data is being changed
            ValidationError: Pipeline validation fails
        """
        from shared.types.pdf_templates import PdfVersionCreate
        from shared.types.pipeline_definition import PipelineDefinitionCreate
        from shared.types.pipelines import PipelineState, VisualState

        # Get current template
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        if template.current_version_id:
            current_version = self.version_repository.get_by_id(template.current_version_id)

        assert current_version is not None

        # Detect what changed
        metadata_changed = update_data.name is not None or update_data.description is not None
        signature_changed = update_data.signature_objects is not None
        extraction_changed = update_data.extraction_fields is not None
        pipeline_changed = update_data.pipeline_state is not None or update_data.visual_state is not None

        wizard_data_changed = signature_changed or extraction_changed or pipeline_changed

        # Check: Cannot update wizard data while template is active
        if wizard_data_changed and template.status == "active":
            raise ConflictError(
                f"Template {template_id} is active. Deactivate first before updating wizard data."
            )

        # ==================== Case 1: Only Metadata Changed ====================
        if metadata_changed and not wizard_data_changed:
            updates = {}
            if update_data.name is not None:
                updates["name"] = update_data.name
            if update_data.description is not None:
                updates["description"] = update_data.description

            updated_template = self.template_repository.update(template_id, updates)
            if not updated_template:
                raise ServiceError(f"Failed to update template {template_id}")

            # Return current version info
            current_version_num = current_version.version_number
            pipeline_id = current_version.pipeline_definition_id
            return updated_template, current_version_num, pipeline_id

        # ==================== Case 2 & 3: Wizard Data Changed ====================
        with self.connection_manager.unit_of_work() as uow:
            pipeline_definition_id: int

            # Sub-case: Pipeline changed (Complex Case)
            if pipeline_changed:
                logger.info("Pipeline data changed - creating new pipeline definition")

                # Both pipeline_state and visual_state must be provided together
                if update_data.pipeline_state is None or update_data.visual_state is None:
                    raise ServiceError(
                        "Both pipeline_state and visual_state must be provided when updating pipeline"
                    )

                # Convert dicts to proper types
                pipeline_state_obj = PipelineState(**update_data.pipeline_state)
                visual_state_obj = VisualState(**update_data.visual_state)

                # Create pipeline definition (validation, compilation, creation all handled)
                pipeline_create_data = PipelineDefinitionCreate(
                    pipeline_state=pipeline_state_obj,
                    visual_state=visual_state_obj
                )

                pipeline_definition = self.pipeline_service.create_pipeline_definition(pipeline_create_data)
                pipeline_definition_id = pipeline_definition.id
                logger.info(f"Created pipeline definition {pipeline_definition_id}")

            else:
                # Sub-case: No pipeline change - reuse current pipeline_definition_id
                if not current_version:
                    raise ServiceError(
                        f"Template {template_id} has no current version - cannot determine pipeline_definition_id"
                    )

                pipeline_definition_id = current_version.pipeline_definition_id
                logger.info(f"Reusing pipeline definition {pipeline_definition_id}")

            # Calculate next version number
            next_version_num = (current_version.version_number + 1) if current_version else 1

            # Create new version
            version_data = PdfVersionCreate(
                template_id=template_id,
                version_number=next_version_num,
                source_pdf_id=template.source_pdf_id,
                signature_objects=(
                    update_data.signature_objects
                    if update_data.signature_objects is not None
                    else current_version.signature_objects
                ),
                extraction_fields=(
                    update_data.extraction_fields
                    if update_data.extraction_fields is not None
                    else current_version.extraction_fields
                ),
                pipeline_definition_id=pipeline_definition_id
            )

            new_version = uow.pdf_template_versions.create(version_data)
            logger.info(f"Created version {next_version_num} for template {template_id}")

            # Update template metadata and point to new version
            updates : dict[str, Any] = {"current_version_id": new_version.id}
            if update_data.name is not None:
                updates["name"] = update_data.name
            if update_data.description is not None:
                updates["description"] = update_data.description

            updated_template = uow.pdf_templates.update(template_id, updates)
            if not updated_template:
                raise ServiceError(f"Failed to update template {template_id}")

            # Transaction commits automatically
            logger.info(
                f"Template {template_id} updated successfully: "
                f"version {next_version_num}, pipeline {pipeline_definition_id}"
            )
            return updated_template, next_version_num, pipeline_definition_id

    def create_template(self, template_data: PdfTemplateCreate) -> tuple[PdfTemplate, int, int]:
        """
        Create new PDF template with initial version atomically.

        Creates template + version 1 + pipeline definition in a single transaction.
        Template starts with status="inactive".

        Args:
            template_data: PdfTemplateCreate dataclass with all wizard data

        Returns:
            Tuple of (created_template, version_number, pipeline_definition_id)

        Raises:
            ServiceError: If creation fails at any step
        """
        from shared.types.pdf_templates import PdfVersionCreate

        try:
            with self.connection_manager.unit_of_work() as uow:
                # TODO: Implement pipeline definition creation when pipeline database is built
                # For now, use placeholder ID
                logger.info("Create pipeline - placeholder (pipeline database not yet implemented)")
                pipeline_definition_id = 1  # Placeholder

                # Step 1: Create template record (status=inactive, current_version_id=None initially)
                template = uow.pdf_templates.create(
                    name=template_data.name,
                    description=template_data.description,
                    source_pdf_id=template_data.source_pdf_id,
                    status="inactive"
                )

                # Step 2: Create version 1 with signature objects, extraction fields, and pipeline ID
                version_data = PdfVersionCreate(
                    template_id=template.id,
                    version_number=1,
                    source_pdf_id=template_data.source_pdf_id,
                    signature_objects=template_data.signature_objects,
                    extraction_fields=template_data.extraction_fields,
                    pipeline_definition_id=pipeline_definition_id
                )

                version = uow.pdf_template_versions.create(version_data)

                # Step 3: Update template to point to version 1 as current version
                updated_template = uow.pdf_templates.update(
                    template.id,
                    {"current_version_id": version.id}
                )

                if not updated_template:
                    raise ServiceError(f"Failed to update template {template.id} with current_version_id")

                # Transaction commits automatically when exiting context manager
                return updated_template, 1, pipeline_definition_id

        except Exception as e:
            # UoW automatically rolls back on exception
            logger.error(f"Error creating template: {e}", exc_info=True)
            raise ServiceError(f"Failed to create template: {str(e)}")

    def activate_template(self, template_id: int) -> PdfTemplate:
        """
        Activate a PDF template for ETO matching.

        Args:
            template_id: Template ID to activate

        Returns:
            Updated template metadata with active status

        Raises:
            ObjectNotFoundError: Template not found
            ConflictError: Template has no current version (cannot activate)
        """
        # Verify template exists
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Verify template has a current version
        if template.current_version_id is None:
            raise ConflictError(
                f"Template {template_id} has no current version. Cannot activate template without a version."
            )

        # Update status to active
        updated_template = self.template_repository.update(template_id, {"status": "active"})
        if not updated_template:
            # This shouldn't happen since we verified it exists above
            raise ServiceError(f"Failed to activate template {template_id}")

        return updated_template

    def deactivate_template(self, template_id: int) -> PdfTemplate:
        """
        Deactivate a PDF template (stop using for ETO matching).

        Args:
            template_id: Template ID to deactivate

        Returns:
            Updated template metadata with inactive status

        Raises:
            ObjectNotFoundError: Template not found
        """
        # Verify template exists
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Update status to inactive
        updated_template = self.template_repository.update(template_id, {"status": "inactive"})
        if not updated_template:
            # This shouldn't happen since we verified it exists above
            raise ServiceError(f"Failed to deactivate template {template_id}")

        return updated_template
