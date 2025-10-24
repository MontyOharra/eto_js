"""
Storage configuration for PDF files and other file storage needs
"""
from dataclasses import dataclass

import os, logging

logger = logging.getLogger(__name__)

def get_storage_configuration() -> str:
    """
    Get PDF storage path with priority order:
    1. Environment variable (PDF_STORAGE_ROOT)
    2. Project-relative default (eto_server/storage/)

    Returns:
        str: Configured storage path
    """
    # Priority 1: Environment variable
    env_path = os.getenv('PDF_STORAGE_ROOT')
    if env_path:
        logger.info(f"Using environment variable storage path: {env_path}")
        return env_path

    # Priority 2: Project-relative default
    # Find the eto_server directory (where main.py is located)
    current_file = os.path.abspath(__file__)
    # Navigate: storage_config.py -> utils -> shared -> src -> eto_server
    eto_server_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    default_path = os.path.join(eto_server_dir, 'storage')

    logger.info(f"Using project-relative storage path: {default_path}")
    return default_path


@dataclass(frozen=True)
class StorageConfig:
    """
    Configuration for file storage paths.
    Used by services that handle file storage (PdfFilesService, etc.)
    """
    pdf_storage_path: str

    @classmethod
    def from_environment(cls) -> 'StorageConfig':
        """
        Create StorageConfig from environment variables.
        Uses get_storage_configuration() to determine the path.
        """
        return cls(pdf_storage_path=get_storage_configuration())
