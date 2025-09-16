"""
Simple storage configuration utility
Handles PDF storage path configuration for development and deployment
"""
import os
import logging

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


def get_fallback_storage() -> str:
    """
    Get fallback storage path for when primary storage fails

    Returns:
        str: Fallback storage path
    """
    fallback_path = "C:/Users/Owner/Software_projects/eto_js/eto_server/storage/fallback_pdf/"
    logger.info(f"Using fallback storage path: {fallback_path}")
    return fallback_path