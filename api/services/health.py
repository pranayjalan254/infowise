"""
Health check service.
Simple health endpoint for monitoring.
"""

from flask import Blueprint, current_app
from utils.responses import success_response
from utils.helpers import get_current_timestamp


health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    Returns basic application status.
    """
    try:
        health_data = {
            "status": "healthy",
            "timestamp": get_current_timestamp(),
            "application": {
                "name": current_app.config.get('APP_NAME', 'Data Guardians API'),
                "version": current_app.config.get('APP_VERSION', '1.0.0'),
                "environment": current_app.config.get('ENV', 'development'),
                "debug": current_app.config.get('DEBUG', False)
            }
        }
        
        return success_response(health_data)
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return success_response({
            "status": "unhealthy",
            "timestamp": get_current_timestamp(),
            "error": str(e)
        }, status_code=503)
