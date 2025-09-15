#!/usr/bin/env python3
"""
Unified ETO Server - Main Entry Point
Starts the Flask application with all services
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Configure logging with environment variable support
def get_log_level() -> int:
    """Get logging level from environment variable"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_mapping.get(log_level, logging.INFO)

logging.basicConfig(
    level=get_log_level(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/eto_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Log the configured logging level
log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
logger.info(f"Main logging configured at {log_level_name} level")

def main():
    """Main entry point for the ETO Server"""
    try:
        logger.info("Starting Unified ETO Server...")
        
        # Import and create the Flask app
        from src.app import create_app
        
        # Get configuration from environment
        config_name = os.getenv('FLASK_ENV', 'development')
        app = create_app(config_name)
        
        # Get port from environment or default to 8080
        port = int(os.getenv('PORT', 8080))
        host = os.getenv('HOST', '0.0.0.0')
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        logger.info(f"Server starting on {host}:{port} (config: {config_name})")
        
        if debug:
            logger.warning("Running in DEBUG mode - not suitable for production!")
        
        # Start the Flask application
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,  # Enable threading for concurrent requests
            use_reloader=False  # Disable reloader in production
        )
        
    except Exception as e:
        logger.error(f"Failed to start ETO Server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()