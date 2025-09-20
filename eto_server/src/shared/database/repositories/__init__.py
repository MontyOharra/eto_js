"""
Database Repositories
Centralized access to all data repositories
"""
from .base import BaseRepository
from .email import EmailRepository
from .email_ingestion_config import EmailIngestionConfigRepository
from .email_ingestion_cursor import EmailIngestionCursorRepository  
from .eto_run import EtoRunRepository
from .pdf_file import PdfRepository
from .pdf_template import PdfTemplateRepository

__all__ = [
    'BaseRepository',
    'EmailRepository',
    'EmailIngestionConfigRepository',
    'EmailIngestionCursorRepository',
    'EtoRunRepository',
    'PdfRepository',
    'PdfTemplateRepository',
]