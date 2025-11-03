#!/usr/bin/env python3
"""
Transformation Pipeline Server - FastAPI Main Entry Point
Starts the FastAPI application using uvicorn
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


# Logging configuration is now handled by app.py configure_logging()


def main():
    """Main entry point for the FastAPI Transformation Pipeline Server"""
    # Basic logger for startup messages (detailed logging configured in app.py)
    logger = logging.getLogger(__name__)

    try:
        print("Starting Transformation Pipeline Server (FastAPI)...")  # Use print for initial startup

        # Get configuration from environment
        port = int(os.getenv('PORT', 8000))
        host = os.getenv('HOST', '0.0.0.0')
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        reload = os.getenv('RELOAD', str(debug)).lower() == 'true'
        workers = int(os.getenv('WORKERS', 1))

        print(f"Server starting on {host}:{port}")

        if debug:
            print("Running in DEBUG mode - not suitable for production!")

        if workers > 1 and reload:
            print("Running with multiple workers and reload enabled - disabling reload")
            reload = False

        # Configure uvicorn settings
        uvicorn_config = {
            "app": "src.app:create_app",
            "factory": True,
            "host": host,
            "port": port,
            "reload": reload,
            "log_level": "debug" if debug else "info",
            "access_log": True,
            "use_colors": True,
            "loop": "auto",
            "reload_delay": 1.0,  # Delay between reload checks
            "reload_excludes": [
                "*.log", "*.pyc", "__pycache__", ".git",
                "storage/*", "logs/*", "data/*", "*.pdf", "*.csv", "*.json"
            ],  # Exclude files that trigger reload
        }

        # Add specific directory watching in reload mode
        if reload:
            uvicorn_config["reload_dirs"] = ["./src"]  # Only watch src directory

        # Add workers only in production (no reload)
        if not reload and workers > 1:
            uvicorn_config["workers"] = workers
            print(f"Starting with {workers} workers")

        # Start the FastAPI application with uvicorn
        print("Starting uvicorn server...")
        uvicorn.run(**uvicorn_config)

    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Failed to start Transformation Pipeline Server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()