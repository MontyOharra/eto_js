"""
Unified ETO Server - Flask Application
Combines email/template processing with transformation pipelines
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name: str = 'development') -> Flask:
    """
    Flask application factory
    Creates and configures the Flask app with all blueprints
    """
    app = Flask(__name__)
    
    # Configure CORS - Allow all origins for development
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Load configuration
    app.config.from_object(get_config_class(config_name))
    
    # Initialize database with SQL Server
    try:
        database_url = os.getenv('DATABASE_URL', app.config.get('DATABASE_URL'))
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Initialize database connection with new architecture
        from .database import init_database_connection
        connection_manager = init_database_connection(database_url)
        logger.info(f"Database connection configured: {database_url.split('://')[0]}://***")
        
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
        raise
    
    # TODO: Initialize services (modules, processing worker, etc.)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    logger.info("Unified ETO server application created successfully")
    return app

def register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints"""
    try:
        # Import blueprints
        from .blueprints.health import health_bp
        from .blueprints.emails import emails_bp
        from .blueprints.templates import templates_bp
        from .blueprints.pdfs import pdfs_bp
        from .blueprints.eto_runs import eto_runs_bp
        from .blueprints.modules import modules_bp
        from .blueprints.pipelines import pipelines_bp
        from .blueprints.processing import processing_bp
        from .blueprints.email_ingestion import email_ingestion_bp
        
        # Register blueprints
        app.register_blueprint(health_bp)
        app.register_blueprint(emails_bp)
        app.register_blueprint(templates_bp)
        app.register_blueprint(pdfs_bp)
        app.register_blueprint(eto_runs_bp)
        app.register_blueprint(modules_bp)
        app.register_blueprint(pipelines_bp)
        app.register_blueprint(processing_bp)
        app.register_blueprint(email_ingestion_bp)
        
        logger.info("All blueprints registered successfully")
        
    except ImportError as e:
        logger.error(f"Failed to import blueprint: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to register blueprints: {e}")
        raise

def register_error_handlers(app: Flask) -> None:
    """Register global error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'message': 'The requested resource does not exist'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'The request was malformed or invalid'
        }), 400

def get_config_class(config_name: str):
    """Get configuration class based on environment"""
    
    class DevelopmentConfig:
        DEBUG = True
        DATABASE_URL = os.getenv('DATABASE_URL', 'mssql+pyodbc://test:testing@localhost:1433/eto_unified?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes')
        # SECRET_KEY not needed for our REST API, but Flask requires it
        SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-not-used-for-sessions')
    
    class ProductionConfig:
        DEBUG = False
        DATABASE_URL = os.getenv('DATABASE_URL')
        # For production, allow a default since we don't actually use sessions/cookies
        SECRET_KEY = os.getenv('SECRET_KEY', 'production-secret-key-placeholder')
        
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is required for production")
        # Remove SECRET_KEY requirement since we don't use Flask sessions
    
    class TestingConfig:
        TESTING = True
        DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
        SECRET_KEY = 'test-secret-key'
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(config_name, DevelopmentConfig)

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)