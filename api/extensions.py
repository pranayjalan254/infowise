"""
Flask extensions initialization.
Simple setup for hackathon prototype.
"""

from typing import Optional
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging


# Global extension instances
cors: Optional[CORS] = None
jwt: Optional[JWTManager] = None


def init_sessions(app: Flask) -> None:
    """Initialize Flask sessions for OAuth state management."""
    # Configure session settings
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def init_cors(app: Flask) -> None:
    """Initialize CORS with minimal configuration."""
    global cors
    cors = CORS(
        app,
        origins=app.config.get('CORS_ORIGINS', ['http://localhost:8080']),
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization', 'X-Request-ID'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    )


def init_jwt(app: Flask) -> None:
    """Initialize JWT manager."""
    global jwt
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'status': 'error',
            'data': None,
            'error': {
                'code': 'TOKEN_EXPIRED',
                'message': 'Token has expired'
            }
        }, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return {
            'status': 'error',
            'data': None,
            'error': {
                'code': 'INVALID_TOKEN',
                'message': 'Invalid token'
            }
        }, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return {
            'status': 'error',
            'data': None,
            'error': {
                'code': 'MISSING_TOKEN',
                'message': 'Authorization token is required'
            }
        }, 401
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check if JWT token has been revoked."""
        from services.auth import is_token_blacklisted
        jti = jwt_payload['jti']
        return is_token_blacklisted(jti)


def init_logging(app: Flask) -> None:
    """Initialize basic logging."""
    if not app.config.get('TESTING'):
        app.logger.setLevel(
            logging.DEBUG if app.config.get('DEBUG') else logging.INFO
        )


def setup_request_id_logging(app: Flask) -> None:
    """Add request ID to responses."""
    import uuid
    from flask import request, g
    
    @app.before_request
    def before_request():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
    @app.after_request
    def after_request(response):
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        return response


def init_security_headers(app: Flask) -> None:
    """Add basic security headers."""
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Check if this endpoint should allow iframe embedding
        if response.headers.get('X-Allow-Iframe') == 'true':
            # Remove the custom header (cleanup)
            response.headers.pop('X-Allow-Iframe', None)
            # Don't set X-Frame-Options to allow iframe embedding
        else:
            # Set X-Frame-Options to DENY for all other endpoints
            response.headers['X-Frame-Options'] = 'DENY'
        
        return response


def init_all_extensions(app: Flask) -> None:
    """Initialize all extensions in correct order."""
    init_logging(app)
    setup_request_id_logging(app)
    init_sessions(app)
    init_cors(app)
    init_jwt(app)
    init_security_headers(app)
    
    # Initialize MongoDB
    from mongodb import init_mongodb
    init_mongodb(app)
