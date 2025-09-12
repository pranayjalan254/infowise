"""
Flask application factory.
Creates and configures the Flask application with all extensions and blueprints.
"""

from flask import Flask
from config import config
from extensions import init_all_extensions
from utils.errors import register_error_handlers
from typing import Optional
import os


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory function.
    Creates a Flask app with the specified configuration.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
    
    Returns:
        Configured Flask application
    """
    
    # Determine configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    init_all_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Log startup info
    app.logger.info(f"Application started - Environment: {config_name}")
    
    return app


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    
    # Health check
    from services.health import health_bp
    app.register_blueprint(health_bp, url_prefix='/api/v1')
    
    # Authentication
    from services.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    
    # Document management
    from services.documents import documents_bp
    app.register_blueprint(documents_bp, url_prefix='/api/v1/documents')
    
    # PII detection
    from services.pii_detection import pii_detection_bp
    app.register_blueprint(pii_detection_bp, url_prefix='/api/v1/pii')
    
    # PII detection streaming
    from services.pii_detection_streaming import pii_streaming_bp
    app.register_blueprint(pii_streaming_bp, url_prefix='/api/v1/pii')
    
    # PII masking
    from services.pii_masking import pii_masking_bp
    app.register_blueprint(pii_masking_bp, url_prefix='/api/v1/masking')
    
    # Synthetic data generation
    from services.synthetic_data import synthetic_data_bp
    app.register_blueprint(synthetic_data_bp, url_prefix='/api/v1/synthetic')
    
    # Compliance checking (TODO)
    # from services.compliance import compliance_bp
    # app.register_blueprint(compliance_bp, url_prefix='/api/v1')
    
    # Data masking (TODO)
    # from services.masking import masking_bp
    # app.register_blueprint(masking_bp, url_prefix='/api/v1')
    
    # Quality assurance (TODO)
    # from services.qa import qa_bp
    # app.register_blueprint(qa_bp, url_prefix='/api/v1')
    
    # Dashboard (TODO)
    # from services.dashboard import dashboard_bp
    # app.register_blueprint(dashboard_bp, url_prefix='/api/v1')
    
    # Reports (TODO)
    # from services.reports import reports_bp
    # app.register_blueprint(reports_bp, url_prefix='/api/v1')
    
    # Sandbox/Chat (TODO)
    # from services.sandbox import sandbox_bp
    # app.register_blueprint(sandbox_bp, url_prefix='/api/v1')


# Create app instance for direct execution
app = create_app()


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config.get('DEBUG', False)
    )