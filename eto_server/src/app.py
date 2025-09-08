"""
Unified ETO Server - Flask Application Factory
Combines email/template processing with transformation pipelines
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
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
    
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Load configuration
    app.config.from_object(get_config_class(config_name))
    
    # Initialize database
    try:
        from .database import init_unified_database
        database_url = os.getenv('DATABASE_URL', app.config.get('DATABASE_URL'))
        if database_url:
            init_unified_database(database_url)
            logger.info("Unified database initialized successfully")
        else:
            logger.warning("No database URL configured")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Initialize module registry
    try:
        from .modules import get_module_registry, populate_database_with_modules
        registry = get_module_registry()
        
        # Registry automatically discovers modules during initialization
        module_count = registry.get_registered_module_count()
        if module_count > 0:
            populate_database_with_modules()
            logger.info(f"Module registry initialized with {module_count} modules")
        else:
            logger.warning("No modules discovered in registry")
    except Exception as e:
        logger.error(f"Failed to initialize module registry: {e}")
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'unified-eto-server',
            'version': '1.0.0'
        })
    
    logger.info("Unified ETO server application created successfully")
    return app

def register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints"""
    try:
        # Import blueprints
        from .blueprints.health import health_bp
        from .blueprints.modules import modules_bp
        from .blueprints.emails import emails_bp
        from .blueprints.pdfs import pdfs_bp
        from .blueprints.templates import templates_bp
        from .blueprints.pipelines import pipelines_bp
        from .blueprints.processing import processing_bp
        
        # Register blueprints
        app.register_blueprint(health_bp)
        app.register_blueprint(modules_bp)
        app.register_blueprint(emails_bp)
        app.register_blueprint(pdfs_bp)
        app.register_blueprint(templates_bp)
        app.register_blueprint(pipelines_bp)
        app.register_blueprint(processing_bp)
        
        logger.info("All blueprints registered successfully")
        
    except ImportError as e:
        logger.error(f"Failed to import blueprint: {e}")
        # Continue without the missing blueprint for now
    except Exception as e:
        logger.error(f"Failed to register blueprints: {e}")

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
        DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///eto_unified_dev.db')
        SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    class ProductionConfig:
        DEBUG = False
        DATABASE_URL = os.getenv('DATABASE_URL')
        SECRET_KEY = os.getenv('SECRET_KEY')
    
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

# For backwards compatibility
app = None

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)