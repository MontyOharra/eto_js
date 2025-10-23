"""
Storage configuration for PDF files and other file storage needs
"""
from dataclasses import dataclass
from shared.utils.storage_config import get_storage_configuration


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
