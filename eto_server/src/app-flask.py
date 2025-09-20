"""
Unified ETO Server - Flask Application
Feature-based architecture with clean separation of concerns
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from .shared.database import init_database_connection
from .shared.utils.storage_config import get_storage_configuration
import sys
import os
# Add the src directory to Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.services import ServiceContainer

from .api import BLUEPRINTS
        
logger = logging.getLogger(__name__)


def initialize_database_connection(app: Flask) -> None:
    """Initialize database connection and verify connectivity"""
    try:
        database_url = os.getenv('DATABASE_URL', app.config.get('DATABASE_URL'))
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Initialize database connection
        connection_manager = init_database_connection(database_url)
        
        # Test connection
        if connection_manager.test_connection():
            logger.info("Database connection established and verified")
        else:
            logger.warning("Database connection established but test failed")
            
        # Store connection manager in app config for access by blueprints
        app.config['CONNECTION_MANAGER'] = connection_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        
        # Print available drivers for debugging
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            logger.debug(f"Available ODBC drivers: {drivers}")
        except ImportError:
            logger.warning("pyodbc not available for driver debugging")
        except Exception:
            pass
        
        # Re-raise to prevent app startup with broken database
        raise


def initialize_services(app: Flask) -> None:
    """Initialize all services using the ServiceContainer singleton"""
    try:
        logger.debug("Initializing services via ServiceContainer...")

        # Get connection manager from app config
        connection_manager = app.config.get('CONNECTION_MANAGER')
        if not connection_manager:
            raise RuntimeError("Database connection manager not available")

        # Get PDF storage path from app config
        pdf_storage_path = app.config['PDF_STORAGE_ROOT']
        logger.debug(f"PDF storage path configured: {pdf_storage_path}")

        # Initialize the service container with all services
        logger.info("Creating ServiceContainer singleton instance...")

        # Import the private getter to ensure we set the module-level instance
        from eto_server.src.shared.services.service_container import _get_container

        service_container = _get_container()
        logger.info(f"ServiceContainer instance created (ID: {id(service_container)}), calling initialize with cm={type(connection_manager)}")
        service_container.initialize(connection_manager, pdf_storage_path)
        logger.info("ServiceContainer.initialize() completed successfully")

        # Store references in Flask app config for blueprint access
        app.config['EMAIL_INGESTION_SERVICE'] = service_container.get_email_service()
        app.config['PDF_PROCESSING_SERVICE'] = service_container.get_pdf_service()
        app.config['ETO_PROCESSING_SERVICE'] = service_container.get_eto_service()
        app.config['PDF_TEMPLATE_SERVICE'] = service_container.get_pdf_template_service()

        logger.info("All services initialized successfully via ServiceContainer")

        # Auto-start email ingestion if active config exists
        try:
            email_service = service_container.get_email_service()
            active_config = email_service.config_service.get_active_config()

            if active_config:
                logger.info(f"Found active configuration: {active_config.name} (ID: {active_config.id})")
                result = email_service.start(active_config.id)

                if result.success:
                    logger.info(f"Email ingestion service started successfully for config: {active_config.name}")
                else:
                    logger.warning(f"Failed to start email ingestion: {result.message}")
            else:
                logger.info("No active email ingestion configuration found - service ready for configuration")

        except Exception as service_error:
            logger.warning(f"Email ingestion auto-connect failed: {service_error}")

        # Auto-start ETO processing if enabled
        try:
            worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
            if worker_enabled:
                eto_service = service_container.get_eto_service()
                eto_service.start()
                logger.info("ETO processing background worker started")
            else:
                logger.info("ETO processing service initialized but worker not started (ETO_WORKER_ENABLED=false)")
        except Exception as eto_error:
            logger.warning(f"ETO processing auto-start failed: {eto_error}")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Don't re-raise - allow app to continue with limited functionality
        logger.info("Application will continue with limited functionality")


def register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints from the feature-based API structure"""
    try:
        for blueprint in BLUEPRINTS:
            app.register_blueprint(blueprint)
            logger.debug(f"Registered blueprint: {blueprint.name}")
        
        logger.info(f"Successfully registered {len(BLUEPRINTS)} blueprints")
        
    except ImportError as e:
        logger.error(f"Failed to import blueprints: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to register blueprints: {e}")
        raise


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers for consistent error responses"""
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors with consistent JSON response"""
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'message': 'The requested resource does not exist',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors with consistent JSON response"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'success': False,
            'error': 'Internal server error', 
            'message': 'An unexpected error occurred on the server',
            'status_code': 500
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors with consistent JSON response"""
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'The request was malformed or contained invalid data',
            'status_code': 400
        }), 400
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors with consistent JSON response"""
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'message': 'The HTTP method is not allowed for this endpoint',
            'status_code': 405
        }), 405
    
    @app.errorhandler(422)
    def validation_error(error):
        """Handle 422 validation errors with consistent JSON response"""
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'message': 'The request data failed validation',
            'status_code': 422
        }), 422


def register_info_endpoint(app: Flask) -> None:
    """Register application info endpoint"""
    
    @app.route('/', methods=['GET'])
    def app_info():
        """Application information endpoint"""
        return jsonify({
            'service': 'Unified ETO Server',
            'description': 'Email-to-Order processing system with feature-based architecture',
            'version': '2.0.0',
            'architecture': 'feature-based',
            'api_prefix': '/api',
            'endpoints': {
                'health': '/api/health',
                'email_configuration': '/api/email-configuration',
                'eto_processing': '/api/eto-runs',
            },
            'documentation': {
                'health': 'Service health and status monitoring',
                'email_configuration': 'Email ingestion configuration management',
                'eto_processing': 'ETO processing run management and results'
            }
        })


def get_config_class():
    """Get configuration class based on environment"""

    class Config:
        DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
        DATABASE_URL = os.getenv('DATABASE_URL')
        PDF_STORAGE_ROOT = get_storage_configuration()

    logger.debug(f"Using simplified configuration (DEBUG={Config.DEBUG})")
    return Config


def create_app(config_name: str = 'development') -> Flask:
    """
    Flask application factory with feature-based architecture
    Creates and configures the Flask app with all blueprints and services
    """
    app = Flask(__name__)
    
    # Configure CORS - Allow all origins for development
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
            "expose_headers": ["Content-Range", "X-Content-Range"],
            "supports_credentials": False,
            "max_age": 86400
        }
    })
    
    # Load configuration
    app.config.from_object(get_config_class())

    # Initialize database and services
    initialize_database_connection(app)
    initialize_services(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_info_endpoint(app)


    logger.info("Unified ETO Server application created successfully")
    return app