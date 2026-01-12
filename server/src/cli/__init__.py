"""
CLI module for the Transformation Pipeline Server.

Provides command-line tools for database management and other operations.

Usage:
    python -m src.cli db reset
    python -m src.cli db migrate
    python -m src.cli db check
"""
from .db import db

__all__ = ["db"]
