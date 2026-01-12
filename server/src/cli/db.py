"""
Database CLI commands.

Provides commands for database management including reset, create, and check.
Uses SQLAlchemy's create_all() for simple table creation from models.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

# Server root directory (parent of src/)
SERVER_ROOT = Path(__file__).parent.parent.parent


def get_database_url() -> str:
    """Load and return DATABASE_URL from .env file."""
    load_dotenv(SERVER_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise click.ClickException(
            "DATABASE_URL not found in .env file.\n"
            "Please configure DATABASE_URL in your .env file."
        )
    return database_url


def parse_database_name(database_url: str) -> str:
    """Extract database name from connection URL."""
    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip("/")
    if "?" in database_name:
        database_name = database_name.split("?")[0]
    if not database_name:
        raise click.ClickException("Database name is empty in URL")
    return database_name


def get_master_url(database_url: str) -> str:
    """Get URL for master database (for CREATE/DROP operations)."""
    database_name = parse_database_name(database_url)
    return database_url.replace(f"/{database_name}", "/master")


def database_exists(database_url: str) -> bool:
    """Check if the database exists."""
    database_name = parse_database_name(database_url)
    master_url = get_master_url(database_url)

    engine = create_engine(master_url, echo=False, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT database_id FROM sys.databases WHERE name = :db_name"),
                {"db_name": database_name}
            ).fetchone()
            return result is not None
    finally:
        engine.dispose()


def create_database(database_url: str) -> None:
    """Create the database if it doesn't exist."""
    database_name = parse_database_name(database_url)

    if database_exists(database_url):
        click.echo(f"  Database '{database_name}' already exists")
        return

    click.echo(f"  Creating database '{database_name}'...")
    master_url = get_master_url(database_url)
    engine = create_engine(master_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE [{database_name}]"))
        click.echo(f"  Database '{database_name}' created")
    finally:
        engine.dispose()


def drop_database(database_url: str) -> None:
    """Drop the database if it exists."""
    database_name = parse_database_name(database_url)

    if not database_exists(database_url):
        click.echo(f"  Database '{database_name}' doesn't exist")
        return

    click.echo(f"  Dropping database '{database_name}'...")
    master_url = get_master_url(database_url)
    engine = create_engine(master_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            # Force close existing connections
            conn.execute(text(f"""
                ALTER DATABASE [{database_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE
            """))
            conn.execute(text(f"DROP DATABASE [{database_name}]"))
        click.echo(f"  Database '{database_name}' dropped")
    except ProgrammingError:
        # Database might already be gone or inaccessible
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS [{database_name}]"))
    finally:
        engine.dispose()


def create_tables(database_url: str) -> None:
    """Create all tables from SQLAlchemy models using create_all()."""
    # Import models here to avoid circular imports at module load time
    from shared.database.models import BaseModel

    click.echo("  Creating tables from models...")
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        # Get table names before creation for logging
        table_names = list(BaseModel.metadata.tables.keys())
        click.echo(f"  Found {len(table_names)} tables to create")

        # Create all tables - SQLAlchemy handles FK ordering automatically
        BaseModel.metadata.create_all(bind=engine)

        # Verify tables were created
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        click.echo(f"  Created {len(created_tables)} tables")

    finally:
        engine.dispose()


def drop_tables(database_url: str) -> None:
    """Drop all tables defined in SQLAlchemy models."""
    from shared.database.models import BaseModel

    click.echo("  Dropping all tables...")
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        BaseModel.metadata.drop_all(bind=engine)
        click.echo("  All tables dropped")
    finally:
        engine.dispose()


@click.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def reset(confirm: bool):
    """
    Reset the database (destructive).

    Drops the existing database, creates a new one, and creates all tables.
    This is intended for development use only.
    """
    try:
        database_url = get_database_url()
        database_name = parse_database_name(database_url)
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(f"Failed to load configuration: {e}")

    if not confirm:
        click.echo(f"This will permanently delete database '{database_name}' and all data.")
        if not click.confirm("Continue?"):
            click.echo("Cancelled.")
            return

    click.echo(f"\nResetting database '{database_name}'...")
    click.echo("-" * 40)

    try:
        # Step 1: Drop database
        click.echo("\nStep 1: Dropping existing database...")
        drop_database(database_url)

        # Step 2: Create database
        click.echo("\nStep 2: Creating new database...")
        create_database(database_url)

        # Step 3: Create tables from models
        click.echo("\nStep 3: Creating tables...")
        create_tables(database_url)

        click.echo("-" * 40)
        click.echo(f"Database '{database_name}' reset complete!")

    except OperationalError as e:
        raise click.ClickException(f"Database connection error: {e}")
    except Exception as e:
        raise click.ClickException(f"Reset failed: {e}")


@db.command()
def check():
    """
    Check database status.

    Verifies database exists and connection is working.
    """
    try:
        database_url = get_database_url()
        database_name = parse_database_name(database_url)
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(f"Configuration error: {e}")

    click.echo(f"Checking database '{database_name}'...")

    try:
        # Check if database exists
        if not database_exists(database_url):
            click.echo(f"  Database '{database_name}' does not exist")
            click.echo("  Run 'db create' or 'db reset' to create it")
            sys.exit(1)

        click.echo(f"  Database '{database_name}' exists")

        # Test connection to actual database
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            click.echo("  Connection test passed")

            # List tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            click.echo(f"  Tables in database: {len(tables)}")
            for table in sorted(tables):
                click.echo(f"    - {table}")
        finally:
            engine.dispose()

    except OperationalError as e:
        raise click.ClickException(f"Connection failed: {e}")


@db.command()
def create():
    """
    Create database and tables.

    Creates the database if it doesn't exist, then creates all tables from models.
    """
    try:
        database_url = get_database_url()
        database_name = parse_database_name(database_url)
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(f"Configuration error: {e}")

    click.echo(f"Creating database '{database_name}'...")

    try:
        # Create database
        create_database(database_url)

        # Create tables
        click.echo("\nCreating tables...")
        create_tables(database_url)

        click.echo(f"\nDatabase '{database_name}' ready!")

    except OperationalError as e:
        raise click.ClickException(f"Database connection error: {e}")
