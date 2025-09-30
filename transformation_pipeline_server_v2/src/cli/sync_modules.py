"""
Module Sync Command
CLI command to sync registered modules to the database catalog
"""
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.features.modules.core.registry import get_registry, auto_discover_modules, ModuleSecurityValidator
from src.shared.database import DatabaseConnectionManager
from src.shared.database.repositories.module_catalog import ModuleCatalogRepository
from src.shared.models.module_catalog import ModuleCatalogCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_modules_to_database():
    """
    Sync all registered modules to the database catalog
    This function:
    1. Auto-discovers modules from known packages
    2. Converts them to catalog format
    3. Upserts them into the database
    """
    try:
        logger.info("Starting module sync process...")

        # Clear the registry and module cache to force fresh reload
        logger.info("Clearing module registry and cache...")
        registry = get_registry()
        registry.clear()

        # Also clear Python's module cache for our modules
        import sys
        modules_to_clear = [
            key for key in sys.modules.keys()
            if key.startswith("src.features.modules.")
        ]
        for module_name in modules_to_clear:
            logger.debug(f"Removing {module_name} from Python cache")
            del sys.modules[module_name]

        # Step 1: Auto-discover modules (will now import fresh)
        logger.info("Auto-discovering modules...")
        packages_to_scan = [
            "src.features.modules.transform",
            "src.features.modules.action",
            "src.features.modules.logic",
            # Add more packages as needed
        ]
        auto_discover_modules(packages_to_scan)

        # Get registry and convert to catalog format
        registry = get_registry()
        catalog_entries = registry.to_catalog_format()
        logger.info(f"Found {len(catalog_entries)} modules to sync")

        if not catalog_entries:
            logger.warning("No modules found to sync. Check module packages and decorators.")
            return

        # Step 2: Initialize database connection
        logger.info("Initializing database connection...")
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            sys.exit(1)

        connection_manager = DatabaseConnectionManager(database_url)
        connection_manager.initialize_connection()  # Initialize the connection
        module_repository = ModuleCatalogRepository(connection_manager)

        # Step 3: Sync each module to database
        success_count = 0
        error_count = 0

        for entry in catalog_entries:
            try:
                # Validate handler_name if present
                if 'handler_name' in entry and entry['handler_name']:
                    is_valid, error_msg = ModuleSecurityValidator.validate_handler_path(entry['handler_name'])
                    if not is_valid:
                        logger.warning(f"⚠ Skipping module {entry['id']} due to security: {error_msg}")
                        continue

                # Convert to Pydantic model
                module_create = ModuleCatalogCreate(**entry)

                # Upsert to database
                result = module_repository.upsert(module_create)
                logger.info(f"✓ Synced module: {entry['id']} ({entry['name']})")
                success_count += 1

            except Exception as e:
                logger.error(f"✗ Failed to sync module {entry['id']}: {e}")
                error_count += 1

        # Summary
        logger.info(f"\nSync complete: {success_count} succeeded, {error_count} failed")

        if error_count > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error during sync: {e}")
        sys.exit(1)


def clear_module_catalog():
    """
    Clear all modules from the database catalog
    Useful for clean refresh
    """
    try:
        logger.info("Clearing module catalog...")

        # Initialize database connection
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            sys.exit(1)

        connection_manager = DatabaseConnectionManager(database_url)
        connection_manager.initialize_connection()  # Initialize the connection
        module_repository = ModuleCatalogRepository(connection_manager)

        # Get all modules and soft-delete them
        modules = module_repository.get_all(only_active=False)
        count = 0

        for module in modules:
            try:
                module_repository.delete(module.id, module.version)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {module.id}:{module.version}: {e}")

        logger.info(f"Cleared {count} modules from catalog")

    except Exception as e:
        logger.error(f"Failed to clear catalog: {e}")
        sys.exit(1)


def list_registered_modules():
    """
    List all modules that would be synced (without database interaction)
    Useful for debugging module discovery
    """
    try:
        logger.info("Discovering modules...")

        # Clear the registry and module cache to force fresh reload
        registry = get_registry()
        registry.clear()

        # Also clear Python's module cache for our modules
        import sys
        modules_to_clear = [
            key for key in sys.modules.keys()
            if key.startswith("src.features.modules.")
        ]
        for module_name in modules_to_clear:
            del sys.modules[module_name]

        # Auto-discover modules
        packages_to_scan = [
            "src.features.modules.transform",
            "src.features.modules.action",
            "src.features.modules.logic",
        ]
        auto_discover_modules(packages_to_scan)

        # Get registry and list modules
        registry = get_registry()
        modules = registry.get_all()

        if not modules:
            logger.warning("No modules found!")
            return

        logger.info(f"\nFound {len(modules)} modules:")
        logger.info("-" * 60)

        for module_id, module_class in modules.items():
            logger.info(
                f"  {module_id:30} | {module_class.kind:10} | {module_class.title}"
            )

        # Group by kind
        logger.info("\nModules by kind:")
        for kind in ["transform", "action", "logic"]:
            kind_modules = registry.get_by_kind(kind)
            logger.info(f"  {kind}: {len(kind_modules)} modules")

    except Exception as e:
        logger.error(f"Failed to list modules: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Module Sync CLI")
    parser.add_argument(
        "command",
        choices=["sync", "clear", "list"],
        help="Command to execute"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Clear catalog before sync (only with 'sync' command)"
    )

    args = parser.parse_args()

    if args.command == "sync":
        if args.refresh:
            clear_module_catalog()
        sync_modules_to_database()
    elif args.command == "clear":
        clear_module_catalog()
    elif args.command == "list":
        list_registered_modules()