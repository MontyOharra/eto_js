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

from .features.email_ingestion.service import EmailIngestionService
from .features.pdf_processing import PdfProcessingService
from .features.eto_processing import EtoProcessingService

from .api import BLUEPRINTS
        
logger = logging.getLogger(__name__)


def initialize_database(app: Flask) -> None:
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


def initialize_pdf_processing(app: Flask) -> None:
    """Initialize PDF processing service"""
    try:
        logger.debug("Initializing PDF Processing Service...")
        
        # Get PDF storage path from app config
        pdf_storage_path = app.config['PDF_STORAGE_ROOT']
        logger.debug(f"PDF storage path configured: {pdf_storage_path}")
        
        pdf_service = PdfProcessingService(pdf_storage_path)
        
        # Store PDF service in app config for global access
        app.config['PDF_PROCESSING_SERVICE'] = pdf_service
        logger.info("PDF Processing Service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize PDF processing service: {e}")
        # Don't re-raise - allow app to continue without PDF processing
        logger.info("Application will continue without PDF processing service")


def initialize_email_ingestion(app: Flask) -> None:
    """Initialize email ingestion service with PDF support and attempt auto-connection"""
    try:
        logger.debug("Initializing Email Ingestion Service...")
        
        pdf_service = app.config.get('PDF_PROCESSING_SERVICE')
        if not pdf_service:
            logger.error("PDF processing service not available for email ingestion")
            return
        
        # Import and create the email ingestion service
        email_service = EmailIngestionService()
        
        # Store only the service in app config for global access
        app.config['EMAIL_INGESTION_SERVICE'] = email_service
        
        # Check for active configuration and attempt auto-connect
        try:
            active_config = email_service.config_service.get_active_configuration()
            
            if not active_config:
                logger.info("No active email ingestion configuration found - service ready for configuration")
                return
            logger.info(f"Found active configuration: {active_config.name} (ID: {active_config.id})")
            
            # Attempt to connect to Outlook using the active configuration
            connection_config = {
                'email_address': active_config.email_address,
                'folder_name': active_config.folder_name
            }
            
            # Start the email ingestion service
            result = email_service.start(active_config.id)
            
            if result.get('success'):
                logger.info(f"Email ingestion service started successfully for config: {active_config.name}")
            else:
                logger.warning(f"Failed to start email ingestion: {result.get('message')}")
                
        except Exception as service_error:
            logger.warning(f"Email ingestion auto-connect failed: {service_error}")
            logger.info("Email ingestion service initialized but not connected - waiting for configuration")
        
    except Exception as e:
        logger.error(f"Failed to initialize email ingestion service: {e}")
        # Don't re-raise - allow app to continue without email service
        logger.info("Application will continue without email ingestion service")


def initialize_eto_processing(app: Flask) -> None:
    """Initialize ETO processing service with background worker"""
    try:
        logger.debug("Initializing ETO Processing Service...")

        # Initialize ETO processing service (creates dependent services internally)
        eto_service = EtoProcessingService(
            poll_interval=int(os.getenv('ETO_POLL_INTERVAL', '10')),
            batch_size=int(os.getenv('ETO_BATCH_SIZE', '5'))
        )

        # Store service in app config for global access
        app.config['ETO_PROCESSING_SERVICE'] = eto_service

        # Start the background worker if enabled
        worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
        if worker_enabled:
            eto_service.start()
            logger.info("ETO processing background worker started")
        else:
            logger.info("ETO processing service initialized but worker not started (ETO_WORKER_ENABLED=false)")

        logger.info("ETO processing service initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize ETO processing service: {e}")
        # Don't re-raise - allow app to continue without ETO processing
        logger.info("Application will continue without ETO processing service")


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
    
    initialize_database(app)
    initialize_pdf_processing(app)
    initialize_email_ingestion(app)
    initialize_eto_processing(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_info_endpoint(app)
    
    logger.info("Unified ETO Server application created successfully")
    return app