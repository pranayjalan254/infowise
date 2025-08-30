"""
Centralized error handling for the application.
All custom exceptions and error handlers are defined here.
"""

from typing import Dict, Any, Optional
from flask import jsonify, request, current_app
from werkzeug.exceptions import HTTPException
import traceback


class AppError(Exception):
    """Base application error class."""
    
    def __init__(
        self, 
        message: str, 
        code: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BadRequestError(AppError):
    """400 Bad Request errors."""
    
    def __init__(self, message: str = "Bad request", code: str = "BAD_REQUEST", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 400, details)


class UnauthorizedError(AppError):
    """401 Unauthorized errors."""
    
    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 401, details)


class ForbiddenError(AppError):
    """403 Forbidden errors."""
    
    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 403, details)


class NotFoundError(AppError):
    """404 Not Found errors."""
    
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 404, details)


class ConflictError(AppError):
    """409 Conflict errors."""
    
    def __init__(self, message: str = "Conflict", code: str = "CONFLICT", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 409, details)


class ValidationError(BadRequestError):
    """Validation-specific errors."""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class RateLimitError(AppError):
    """429 Rate Limit errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", code: str = "RATE_LIMIT_EXCEEDED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 429, details)


class InternalServerError(AppError):
    """500 Internal Server errors."""
    
    def __init__(self, message: str = "Internal server error", code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 500, details)


def create_error_response(
    status: str,
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> tuple:
    """Create standardized error response."""
    response = {
        "status": status,
        "data": None,
        "error": {
            "code": error_code,
            "message": message
        },
        "meta": {
            "request_id": request_id,
            "timestamp": str(current_app.config.get('CURRENT_TIME', ''))
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    return jsonify(response), status_code


def register_error_handlers(app):
    """Register all error handlers with the Flask app."""
    
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """Handle custom application errors."""
        request_id = getattr(request, 'request_id', None)
        
        current_app.logger.error(
            f"AppError: {error.code} - {error.message}",
            extra={
                'request_id': request_id,
                'error_code': error.code,
                'status_code': error.status_code,
                'details': error.details
            }
        )
        
        return create_error_response(
            status="error",
            error_code=error.code,
            message=error.message,
            status_code=error.status_code,
            details=error.details,
            request_id=request_id
        )
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        """Handle HTTP exceptions."""
        request_id = getattr(request, 'request_id', None)
        
        current_app.logger.warning(
            f"HTTPError: {error.code} - {error.description}",
            extra={'request_id': request_id}
        )
        
        return create_error_response(
            status="error",
            error_code=f"HTTP_{error.code}",
            message=error.description or f"HTTP {error.code} error",
            status_code=error.code or 500,
            request_id=request_id
        )
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Handle Pydantic validation errors."""
        request_id = getattr(request, 'request_id', None)
        
        current_app.logger.warning(
            f"ValidationError: {error.message}",
            extra={
                'request_id': request_id,
                'details': error.details
            }
        )
        
        return create_error_response(
            status="error",
            error_code="VALIDATION_ERROR",
            message=error.message,
            status_code=400,
            details=error.details,
            request_id=request_id
        )
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        """Handle unexpected errors."""
        request_id = getattr(request, 'request_id', None)
        
        current_app.logger.error(
            f"Unexpected error: {str(error)}",
            extra={
                'request_id': request_id,
                'traceback': traceback.format_exc()
            }
        )
        
        # Don't expose internal errors in production
        if current_app.config.get('DEBUG'):
            message = str(error)
            details = {'traceback': traceback.format_exc()}
        else:
            message = "An unexpected error occurred"
            details = None
        
        return create_error_response(
            status="error",
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=500,
            details=details,
            request_id=request_id
        )
