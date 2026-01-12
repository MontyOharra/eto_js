"""
CLI entry point for the Transformation Pipeline Server.

Usage:
    python -m src.cli db reset
    python -m src.cli db migrate
    python -m src.cli db check
"""
import click

from .db import db


@click.group()
def cli():
    """Transformation Pipeline Server CLI."""
    pass


# Register command groups
cli.add_command(db)


if __name__ == "__main__":
    cli()
