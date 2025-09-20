#!/usr/bin/env python3
"""
Unified ETO Server - FastAPI Main Entry Point
Starts the FastAPI application with all services using uvicorn
"""
import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

# Add both src and current directory to Python path for proper module resolution
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()


def get_log_level() -> int:
    """Get logging level from environment variable"""
    log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_mapping.get(log_level, logging.INFO)


def setup_logging():
    """Setup logging configuration"""
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)

    logging.basicConfig(
        level=get_log_level(),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/eto_server_fastapi.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point for the FastAPI ETO Server"""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting Unified ETO Server (FastAPI)...")

        # Get configuration from environment
        port = int(os.getenv('PORT', 8080))
        host = os.getenv('HOST', '0.0.0.0')
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        reload = os.getenv('RELOAD', str(debug)).lower() == 'true'
        workers = int(os.getenv('WORKERS', 1))

        logger.info(f"Server starting on {host}:{port}")

        if debug:
            logger.warning("Running in DEBUG mode - not suitable for production!")

        if workers > 1 and reload:
            logger.warning("Running with multiple workers and reload enabled - disabling reload")
            reload = False

        # Configure uvicorn settings
        uvicorn_config = {
            "app": "src.app-fastapi:create_app",
            "factory": True,
            "host": host,
            "port": port,
            "reload": reload,
            "log_level": "debug" if debug else "info",
            "access_log": True,
            "use_colors": True,
            "loop": "auto",
        }

        # Add workers only in production (no reload)
        if not reload and workers > 1:
            uvicorn_config["workers"] = workers
            logger.info(f"Starting with {workers} workers")

        # Start the FastAPI application with uvicorn
        logger.info("Starting uvicorn server...")
        uvicorn.run(**uvicorn_config)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start ETO Server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()