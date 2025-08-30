"""
Document management service.
Handles file upload, storage, and retrieval using MongoDB GridFS.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, current_app, make_response, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, decode_token
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from utils.responses import success_response, error_response
from utils.validation import validate_file_upload
from utils.helpers import get_current_timestamp
from mongodb import get_mongo_db

documents_bp = Blueprint('documents', __name__)


class DocumentManager:
    """File management operations using MongoDB GridFS."""
    
    @staticmethod
    def save_uploaded_file(file: FileStorage, user_id: str) -> Dict[str, Any]:
        """Save uploaded file to MongoDB GridFS."""
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        # Secure the filename
        original_name = secure_filename(file.filename)
        if not original_name:
            raise ValueError("Invalid filename")
        
        # Read file data
        file_data = file.read()
        file_size = len(file_data)
        
        # Get file info
        file_extension = os.path.splitext(original_name)[1]
        
        return {
            'original_name': original_name,
            'file_data': file_data,
            'file_size': file_size,
            'file_type': file_extension.lower(),
            'mime_type': file.mimetype
        }


# MongoDB instance
mongo_db = get_mongo_db()


@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_documents():
    """Upload one or more documents."""
    try:
        user_id = get_jwt_identity()
        
        # Check if files are present
        if 'files' not in request.files:
            return error_response("INVALID_REQUEST", "No files provided", 400)
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return error_response("INVALID_REQUEST", "No files selected", 400)
        
        uploaded_documents = []
        errors = []
        
        for file in files:
            try:
                # Validate file
                validation_error = validate_file_upload(file, current_app.config)
                if validation_error:
                    errors.append(f"{file.filename}: {validation_error}")
                    continue
                
                # Save file
                file_info = DocumentManager.save_uploaded_file(file, user_id)
                
                # Store in MongoDB
                document_data = {
                    'user_id': user_id,
                    'upload_date': get_current_timestamp(),
                    **file_info
                }
                
                doc_id = mongo_db.store_file(file_info['file_data'], document_data)
                
                uploaded_documents.append({
                    'id': doc_id,
                    'name': file_info['original_name'],
                    'size': file_info['file_size'],
                    'type': file_info['file_type'],
                    'upload_date': document_data['upload_date']
                })
                
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
        
        response_data = {
            'uploaded_documents': uploaded_documents,
            'total_uploaded': len(uploaded_documents)
        }
        
        if errors:
            response_data['errors'] = errors
        
        if uploaded_documents:
            return success_response(
                data=response_data,
                message="Documents uploaded successfully"
            )
        else:
            return error_response(
                "UPLOAD_FAILED",
                "No documents could be uploaded", 
                400, 
                {'errors': errors}
            )
    
    except Exception as e:
        current_app.logger.error(f"Document upload error: {str(e)}")
        return error_response("UPLOAD_ERROR", "Upload failed", 500)


@documents_bp.route('/list', methods=['GET'])
@jwt_required()
def list_documents():
    """Get list of user's documents."""
    try:
        user_id = get_jwt_identity()
        documents = mongo_db.list_user_documents(user_id)
        
        # Format response
        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                'id': doc['id'],
                'name': doc['original_name'],
                'size': doc['file_size'],
                'type': doc['file_type'],
                'mime_type': doc['mime_type'],
                'upload_date': doc['upload_date'],
                'status': doc['status']
            })
        
        return success_response(
            data={
                'documents': formatted_docs,
                'total_count': len(formatted_docs)
            },
            message="Documents retrieved successfully"
        )
    
    except Exception as e:
        current_app.logger.error(f"Document list error: {str(e)}")
        return error_response("LIST_ERROR", "Failed to retrieve documents", 500)


@documents_bp.route('/<doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id: str):
    """Get specific document details."""
    try:
        user_id = get_jwt_identity()
        document = mongo_db.get_document_metadata(doc_id, user_id)
        
        if not document:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        return success_response(
            data={
                'id': document['id'],
                'name': document['original_name'],
                'size': document['file_size'],
                'type': document['file_type'],
                'mime_type': document['mime_type'],
                'upload_date': document['upload_date'],
                'status': document['status'],
                'metadata': document.get('metadata', {})
            },
            message="Document retrieved successfully"
        )
    
    except Exception as e:
        current_app.logger.error(f"Document get error: {str(e)}")
        return error_response("GET_ERROR", "Failed to retrieve document", 500)


@documents_bp.route('/<doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id: str):
    """Delete a document."""
    try:
        user_id = get_jwt_identity()
        
        # Delete from MongoDB
        success = mongo_db.delete_document(doc_id, user_id)
        
        if success:
            return success_response(message="Document deleted successfully")
        else:
            return error_response("DELETE_ERROR", "Failed to delete document", 500)
    
    except Exception as e:
        current_app.logger.error(f"Document delete error: {str(e)}")
        return error_response("DELETE_ERROR", "Failed to delete document", 500)


@documents_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_document_stats():
    """Get user's document statistics."""
    try:
        user_id = get_jwt_identity()
        stats = mongo_db.get_user_stats(user_id)
        
        return success_response(
            data=stats,
            message="Document statistics retrieved successfully"
        )
    
    except Exception as e:
        current_app.logger.error(f"Document stats error: {str(e)}")
        return error_response("STATS_ERROR", "Failed to retrieve statistics", 500)


@documents_bp.route('/<doc_id>/view', methods=['GET'])
def view_document(doc_id: str):
    """Serve document content for viewing in iframe."""
    try:
        # Check for token in query parameter (for iframe access)
        token = request.args.get('token')
        user_id = None
        
        if token:
            try:
                # Verify the token manually for iframe access
                from flask_jwt_extended import decode_token
                decoded = decode_token(token)
                user_id = decoded['sub']
            except Exception as e:
                current_app.logger.error(f"Token verification failed: {str(e)}")
                return error_response("UNAUTHORIZED", "Invalid token", 401)
        else:
            # Try JWT from header
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
            except Exception as e:
                return error_response("UNAUTHORIZED", "Authentication required", 401)
        
        document = mongo_db.get_file(doc_id, user_id)
        
        if not document:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Create response with file data
        response = make_response(document['file_data'])
        response.headers['Content-Type'] = document['mime_type'] or 'application/octet-stream'
        response.headers['Content-Disposition'] = f'inline; filename="{document["original_name"]}"'
        
        # Add CORS headers for iframe access
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        # Use a custom header to signal that this endpoint should allow iframe embedding
        response.headers['X-Allow-Iframe'] = 'true'
        
        current_app.logger.info(f"Document {doc_id} viewed by user {user_id}")
        return response
    
    except Exception as e:
        current_app.logger.error(f"Document view error: {str(e)}")
        return error_response("VIEW_ERROR", "Failed to view document", 500)


@documents_bp.route('/<doc_id>/download', methods=['GET'])
@jwt_required()
def download_document(doc_id: str):
    """Download document as attachment."""
    try:
        user_id = get_jwt_identity()
        document = mongo_db.get_file(doc_id, user_id)
        
        if not document:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Create response with file data
        response = make_response(document['file_data'])
        response.headers['Content-Type'] = document['mime_type'] or 'application/octet-stream'
        response.headers['Content-Disposition'] = f'attachment; filename="{document["original_name"]}"'
        
        current_app.logger.info(f"Document {doc_id} downloaded by user {user_id}")
        return response
    
    except Exception as e:
        current_app.logger.error(f"Document download error: {str(e)}")
        return error_response("DOWNLOAD_ERROR", "Failed to download document", 500)