"""
Standardized response utilities.
All API responses should use these functions for consistency.
"""

from typing import Any, Optional, Dict
from flask import jsonify, g
from datetime import datetime, timezone


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> tuple:
    """Create a successful API response."""
    response = {
        "status": "success",
        "data": data,
        "error": None,
        "meta": _create_meta(meta, message)
    }
    return jsonify(response), status_code


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> tuple:
    """Create an error API response."""
    response = {
        "status": "error",
        "data": None,
        "error": {
            "code": code,
            "message": message
        },
        "meta": _create_meta(meta)
    }
    
    if details:
        response["error"]["details"] = details
    
    return jsonify(response), status_code


def paginated_response(
    data: Any,
    page: int,
    per_page: int,
    total: int,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> tuple:
    """Create a paginated response."""
    pagination_meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
        "has_next": page * per_page < total,
        "has_prev": page > 1
    }
    
    if meta:
        pagination_meta.update(meta)
    
    return success_response(
        data=data,
        message=message,
        meta=pagination_meta
    )


def _create_meta(
    meta: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Create metadata for response."""
    base_meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(g, 'request_id', 'unknown')
    }
    
    if message:
        base_meta["message"] = message
    
    if meta:
        base_meta.update(meta)
    
    return base_meta


def validate_request_json(schema_class, data: dict):
    """Validate request data against Pydantic schema."""
    try:
        return schema_class(**data)
    except Exception as e:
        from .errors import ValidationError
        raise ValidationError(
            message="Invalid request data",
            details={"validation_errors": str(e)}
        )
