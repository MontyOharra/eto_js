"""
Unified ETO Server - Main Entry Point
"""
import os
from src.app import create_app

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.getenv('FLASK_ENV', 'development')
    port = int(os.getenv('PORT', 8080))
    
    # Create Flask app
    app = create_app(config_name)
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=(config_name == 'development')
    )