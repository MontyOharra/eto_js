"""
Module Watcher for Development
Watches module files for changes and automatically re-syncs
"""
import logging
import time
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from sync_modules import sync_modules_to_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModuleChangeHandler(FileSystemEventHandler):
    """Handle changes to module files"""

    def __init__(self):
        self.last_sync_time = 0
        self.debounce_seconds = 2  # Wait 2 seconds after last change

    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith('.py'):
            logger.info(f"Module file changed: {event.src_path}")
            self.schedule_sync()

    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith('.py'):
            logger.info(f"New module file created: {event.src_path}")
            self.schedule_sync()

    def schedule_sync(self):
        """Schedule a sync with debouncing"""
        current_time = time.time()
        if current_time - self.last_sync_time > self.debounce_seconds:
            logger.info("Triggering module sync...")
            try:
                sync_modules_to_database()
                logger.info("Sync completed successfully")
            except Exception as e:
                logger.error(f"Sync failed: {e}")
            self.last_sync_time = current_time


def watch_modules():
    """Watch module directories for changes"""
    # Directories to watch
    watch_dirs = [
        Path("src/features/modules/transform"),
        Path("src/features/modules/action"),
        Path("src/features/modules/logic"),
    ]

    # Create observer
    observer = Observer()
    handler = ModuleChangeHandler()

    # Add watchers for each directory
    for watch_dir in watch_dirs:
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)
            logger.info(f"Watching: {watch_dir}")
        else:
            logger.warning(f"Directory not found: {watch_dir}")

    # Start watching
    observer.start()
    logger.info("Module watcher started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Module watcher stopped.")

    observer.join()


if __name__ == "__main__":
    watch_modules()