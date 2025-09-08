"""
Configuration management for the unified ETO server

This module defines configuration classes that read from environment variables.
Environment variables are loaded from .env file by load_dotenv() in app.py.

Usage in services:
    from flask import current_app
    database_url = current_app.config['DATABASE_URL']
    email_server = current_app.config['EMAIL_SERVER']
"""
import os
from typing import Dict, Any

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///eto_unified.db')
    
    # Email service configuration
    EMAIL_SERVER = os.getenv('EMAIL_SERVER', 'outlook.office365.com')
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    
    # PDF storage configuration
    PDF_STORAGE_PATH = os.getenv('PDF_STORAGE_PATH', 'storage/pdfs')
    MAX_PDF_SIZE_MB = int(os.getenv('MAX_PDF_SIZE_MB', 50))
    
    # Processing configuration
    MAX_CONCURRENT_RUNS = int(os.getenv('MAX_CONCURRENT_RUNS', 5))
    PROCESSING_TIMEOUT_MINUTES = int(os.getenv('PROCESSING_TIMEOUT_MINUTES', 30))
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///eto_unified_dev.db')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
    WTF_CSRF_ENABLED = False

config: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}