"""
Unified ETO Server - Flask Application
Feature-based architecture with clean separation of concerns
"""
import os
import logging
from typing import Optional
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log the configured logging level
log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
logger.info(f"Logging configured at {log_level_name} level")

# Import storage configuration utilities
from .shared.utils.storage_config import get_storage_configuration, get_development_storage_path, get_default_storage_path


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
    app.config.from_object(get_config_class(config_name))
    logger.info(f"Application configured for {config_name} environment")
    
    # Initialize database connection
    initialize_database(app)
    
    # Initialize email ingestion service
    initialize_email_ingestion(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers  
    register_error_handlers(app)
    
    # Add startup info endpoint
    register_info_endpoint(app)
    
    logger.info("Unified ETO Server application created successfully")
    return app


def initialize_database(app: Flask) -> None:
    """Initialize database connection and verify connectivity"""
    try:
        database_url = os.getenv('DATABASE_URL', app.config.get('DATABASE_URL'))
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Initialize database connection
        from .shared.database import init_database_connection
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
            logger.info(f"Available ODBC drivers: {drivers}")
        except ImportError:
            logger.warning("pyodbc not available for driver debugging")
        except Exception:
            pass
        
        # Re-raise to prevent app startup with broken database
        raise


def initialize_email_ingestion(app: Flask) -> None:
    """Initialize email ingestion service with PDF support and attempt auto-connection"""
    try:
        logger.info("Initializing Email Ingestion Service with PDF processing...")
        
        # Create PDF storage service with configured path from app config
        from .features.pdf_processing.storage_service import PdfStorageService
        pdf_storage_service = PdfStorageService(app.config['PDF_STORAGE_ROOT'])
        
        # Log storage information
        storage_info = pdf_storage_service.get_storage_info()
        logger.info(f"PDF storage initialized: {storage_info['current_root']}")
        if storage_info.get('fallback_used'):
            logger.warning(f"PDF storage using fallback location (original: {storage_info['original_root']})")
        
        # Import and create the email ingestion service with PDF support
        from .features.email_ingestion.service import EmailIngestionService
        email_service = EmailIngestionService(pdf_storage_service=pdf_storage_service)
        
        # Store services in app config for global access
        app.config['EMAIL_INGESTION_SERVICE'] = email_service
        app.config['PDF_STORAGE_SERVICE'] = pdf_storage_service
        app.config['PDF_REPOSITORY'] = email_service.pdf_repo  # For API access
        
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
            result = email_service.start_ingestion(active_config.id)
            
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


def register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints from the feature-based API structure"""
    try:
        # Import all blueprints from the API package
        from .api import BLUEPRINTS
        
        # Register each blueprint
        for blueprint in BLUEPRINTS:
            app.register_blueprint(blueprint)
            logger.info(f"Registered blueprint: {blueprint.name}")
        
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


def get_config_class(config_name: str):
    """Get configuration class based on environment"""
    
    class BaseConfig:
        """Base configuration with common settings"""
        # Flask settings
        SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-not-used-for-sessions')
        JSON_SORT_KEYS = False
        JSONIFY_PRETTYPRINT_REGULAR = True
        
        # Database settings
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        # API settings
        API_TITLE = 'Unified ETO Server API'
        API_VERSION = 'v1'
        
        # PDF Storage settings - cross-platform defaults
        PDF_STORAGE_ROOT = os.getenv('PDF_STORAGE_ROOT', get_storage_configuration())
        PDF_STORAGE_MAX_SIZE_MB = int(os.getenv('PDF_STORAGE_MAX_SIZE_MB', '100'))
        PDF_STORAGE_CLEANUP_ENABLED = os.getenv('PDF_STORAGE_CLEANUP_ENABLED', 'true').lower() == 'true'
    
    class DevelopmentConfig(BaseConfig):
        """Development environment configuration"""
        DEBUG = True
        TESTING = False
        DATABASE_URL = os.getenv(
            'DATABASE_URL',
            'mssql+pyodbc://test:testing@localhost:1433/eto_unified?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes'
        )
        
        # Development-specific settings
        CORS_ORIGINS = ["*"]  # Allow all origins in development
        
        # Development PDF storage - use current C:/apps/eto/ for testing
        PDF_STORAGE_ROOT = os.getenv('PDF_STORAGE_ROOT', get_development_storage_path())
    
    class ProductionConfig(BaseConfig):
        """Production environment configuration"""
        DEBUG = False
        TESTING = False
        
        # Require DATABASE_URL in production
        if not os.getenv('DATABASE_URL'):
            raise ValueError("DATABASE_URL environment variable is required for production")
        
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        # Production-specific settings
        CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
        SECRET_KEY = os.getenv('SECRET_KEY', 'production-secret-key-placeholder')
        
        # Production PDF storage - use platform-specific defaults or configured path
        PDF_STORAGE_ROOT = os.getenv('PDF_STORAGE_ROOT', get_default_storage_path())
        PDF_STORAGE_MAX_SIZE_MB = int(os.getenv('PDF_STORAGE_MAX_SIZE_MB', '1000'))  # Larger for production
    
    class TestingConfig(BaseConfig):
        """Testing environment configuration"""
        DEBUG = False
        TESTING = True
        DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
        SECRET_KEY = 'test-secret-key'
        
        # Testing-specific settings
        WTF_CSRF_ENABLED = False
        
        # Testing PDF storage - use temp directory
        import tempfile
        PDF_STORAGE_ROOT = os.path.join(tempfile.gettempdir(), 'eto_test_storage')
    
    class PortableAppConfig(BaseConfig):
        """Portable application configuration for executable distributions"""
        DEBUG = False
        TESTING = False
        
        # Portable apps typically use SQLite for simplicity
        DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/eto_portable.db')
        
        # Security
        SECRET_KEY = os.getenv('SECRET_KEY', 'portable-app-secret-change-in-production')
        
        # Portable PDF storage - relative to executable
        from .shared.utils.storage_config import get_portable_storage_path
        PDF_STORAGE_ROOT = os.getenv('PDF_STORAGE_ROOT', get_portable_storage_path())
        PDF_STORAGE_MAX_SIZE_MB = int(os.getenv('PDF_STORAGE_MAX_SIZE_MB', '500'))
        
        # Portable-specific settings
        CORS_ORIGINS = ["*"]  # More permissive for local usage
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
        'portable': PortableAppConfig
    }
    
    config_class = configs.get(config_name, DevelopmentConfig)
    logger.info(f"Using configuration: {config_class.__name__}")
    return config_class


def get_app_info() -> dict:
    """Get application information for monitoring and debugging"""
    try:
        from .shared.database import get_connection_manager
        connection_manager = get_connection_manager()
        db_status = "connected" if connection_manager and connection_manager.test_connection() else "disconnected"
    except Exception:
        db_status = "error"
    
    return {
        'service': 'Unified ETO Server',
        'version': '2.0.0',
        'architecture': 'feature-based',
        'environment': os.getenv('FLASK_ENV', 'development'),
        'database_status': db_status,
        'features': {
            'email_configuration': 'Available',
            'eto_processing': 'Available', 
            'pdf_processing': 'Planned',
            'pipeline_execution': 'Planned'
        }
    }


if __name__ == '__main__':
    """Run the Flask application directly for development"""
    # Get configuration from environment
    config_name = os.getenv('FLASK_ENV', 'development')
    
    # Create application
    app = create_app(config_name)
    
    # Run application
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    debug = config_name == 'development'
    
    logger.info(f"Starting Unified ETO Server on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)