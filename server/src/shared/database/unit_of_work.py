"""
Unit of Work Pattern
Manages database transactions and provides repository access within a transaction context
"""
import logging
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Session

# Import repository classes (will be created)
# Using TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from shared.database.repositories.email_config import EmailConfigRepository
    from shared.database.repositories.email import EmailRepository
    from shared.database.repositories.pdf_template import PdfTemplateRepository
    from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository
    from shared.database.repositories.pipeline_definition import PipelineDefinitionRepository
    from shared.database.repositories.pipeline_compiled_plan import PipelineCompiledPlanRepository
    from shared.database.repositories.pipeline_definition_step import PipelineDefinitionStepRepository
    from shared.database.repositories.module import ModuleRepository
    # Add other repositories as they're created

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work manages a database transaction and provides repository access.

    All repositories within this UoW share the same session, ensuring
    that operations are part of a single atomic transaction.

    Usage:
        with connection_manager.unit_of_work() as uow:
            config = uow.email_configs.create(config_data)
            email = uow.emails.create(email_data)
            # Both commit together automatically

    Repositories are lazy-loaded - only instantiated when accessed.
    """

    def __init__(self, session: Session):
        """
        Initialize Unit of Work with a session.

        Args:
            session: Session instance for this transaction
        """
        self.session = session

        # Lazy-loaded repository instances
        # These are created on first access via properties
        self._email_config_repository: Optional['EmailConfigRepository'] = None
        self._email_repository: Optional['EmailRepository'] = None
        self._pdf_template_repository: Optional['PdfTemplateRepository'] = None
        self._pdf_template_version_repository: Optional['PdfTemplateVersionRepository'] = None
        self._pipeline_definition_repository: Optional['PipelineDefinitionRepository'] = None
        self._pipeline_compiled_plan_repository: Optional['PipelineCompiledPlanRepository'] = None
        self._pipeline_definition_step_repository: Optional['PipelineDefinitionStepRepository'] = None
        self._module_repository: Optional['ModuleRepository'] = None
        # Add other repositories as needed

        logger.debug("UnitOfWork initialized")

    @property
    def email_configs(self) -> 'EmailConfigRepository':
        """
        Access to email config repository within this transaction.

        Returns:
            EmailConfigRepository instance using this UoW's session
        """
        if not self._email_config_repository:
            from shared.database.repositories.email_config import EmailConfigRepository
            self._email_config_repository = EmailConfigRepository(session=self.session)
            logger.debug("EmailConfigRepository loaded in UoW")
        return self._email_config_repository

    @property
    def emails(self) -> 'EmailRepository':
        """
        Access to email repository within this transaction.

        Returns:
            EmailRepository instance using this UoW's session
        """
        if not self._email_repository:
            from shared.database.repositories.email import EmailRepository
            self._email_repository = EmailRepository(session=self.session)
            logger.debug("EmailRepository loaded in UoW")
        return self._email_repository

    @property
    def pdf_templates(self) -> 'PdfTemplateRepository':
        """
        Access to PDF template repository within this transaction.

        Returns:
            PdfTemplateRepository instance using this UoW's session
        """
        if not self._pdf_template_repository:
            from shared.database.repositories.pdf_template import PdfTemplateRepository
            self._pdf_template_repository = PdfTemplateRepository(session=self.session)
            logger.debug("PdfTemplateRepository loaded in UoW")
        return self._pdf_template_repository

    @property
    def pdf_template_versions(self) -> 'PdfTemplateVersionRepository':
        """
        Access to PDF template version repository within this transaction.

        Returns:
            PdfTemplateVersionRepository instance using this UoW's session
        """
        if not self._pdf_template_version_repository:
            from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository
            self._pdf_template_version_repository = PdfTemplateVersionRepository(session=self.session)
            logger.debug("PdfTemplateVersionRepository loaded in UoW")
        return self._pdf_template_version_repository

    @property
    def pipeline_definitions(self) -> 'PipelineDefinitionRepository':
        """
        Access to pipeline definition repository within this transaction.

        Returns:
            PipelineDefinitionRepository instance using this UoW's session
        """
        if not self._pipeline_definition_repository:
            from shared.database.repositories.pipeline_definition import PipelineDefinitionRepository
            self._pipeline_definition_repository = PipelineDefinitionRepository(session=self.session)
            logger.debug("PipelineDefinitionRepository loaded in UoW")
        return self._pipeline_definition_repository

    @property
    def pipeline_compiled_plans(self) -> 'PipelineCompiledPlanRepository':
        """
        Access to pipeline compiled plan repository within this transaction.

        Returns:
            PipelineCompiledPlanRepository instance using this UoW's session
        """
        if not self._pipeline_compiled_plan_repository:
            from shared.database.repositories.pipeline_compiled_plan import PipelineCompiledPlanRepository
            self._pipeline_compiled_plan_repository = PipelineCompiledPlanRepository(session=self.session)
            logger.debug("PipelineCompiledPlanRepository loaded in UoW")
        return self._pipeline_compiled_plan_repository

    @property
    def pipeline_definition_steps(self) -> 'PipelineDefinitionStepRepository':
        """
        Access to pipeline definition step repository within this transaction.

        Returns:
            PipelineDefinitionStepRepository instance using this UoW's session
        """
        if not self._pipeline_definition_step_repository:
            from shared.database.repositories.pipeline_definition_step import PipelineDefinitionStepRepository
            self._pipeline_definition_step_repository = PipelineDefinitionStepRepository(session=self.session)
            logger.debug("PipelineDefinitionStepRepository loaded in UoW")
        return self._pipeline_definition_step_repository

    @property
    def module_catalog(self) -> 'ModuleRepository':
        """
        Access to module catalog repository within this transaction.

        Returns:
            ModuleRepository instance using this UoW's session
        """
        if not self._module_repository:
            from shared.database.repositories.module import ModuleRepository
            self._module_repository = ModuleRepository(session=self.session)
            logger.debug("ModuleRepository loaded in UoW")
        return self._module_repository

    # ========== Transaction Control ==========
    # Usually not needed - context manager handles commit/rollback
    # These are provided for manual control if needed

    def commit(self):
        """
        Manually commit the transaction.

        Note: Usually not needed - the context manager commits automatically.
        """
        self.session.commit()
        logger.debug("UoW transaction committed manually")

    def rollback(self):
        """
        Manually rollback the transaction.

        Note: Usually not needed - the context manager rolls back on exception.
        """
        self.session.rollback()
        logger.debug("UoW transaction rolled back manually")
