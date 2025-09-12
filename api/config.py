"""
Application configuration classes.
Simple configuration for hackathon prototype.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    
    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '36000'))  # 10 hours
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '86400'))  # 24 hours
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8081').split(',')
    
    # Frontend URL
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8081')
    
    # Google OAuth settings
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/v1/auth/google/callback')
    
    # Google AI settings for LLM verification
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '50')) * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'data', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'xlsx', 'csv', 'json', 'xml'}
    
    # Application settings
    APP_NAME = os.getenv('APP_NAME', 'Data Guardians API')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    
    # MongoDB settings
    MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'infowise')
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize app-specific configuration."""
        # Create upload directory
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = False
    CORS_ORIGINS = ['http://localhost:8080', 'http://localhost:8081', 'http://localhost:3000']


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    JWT_ACCESS_TOKEN_EXPIRES = 900  # 15 minutes


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    JWT_ACCESS_TOKEN_EXPIRES = 60  # Short-lived for tests
    UPLOAD_FOLDER = '/tmp/test_uploads'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
