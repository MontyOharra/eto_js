"""Database repositories"""

from .base import BaseRepository
from .email_config import EmailConfigRepository
from .email import EmailRepository

__all__ = [
    'BaseRepository',
    'EmailConfigRepository',
    'EmailRepository',
]
