"""
Document management service.
Handles file upload, storage, and retrieval with user-specific folders.
"""

import os
import sqlite3
import uuid
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from utils.responses import success_response, error_response
from utils.validation import validate_file_upload
from utils.helpers import get_current_timestamp

documents_bp = Blueprint('documents', __name__)


class DocumentDatabase:
    """Database operations for document management."""
    
    def __init__(self, db_path: str = 'data/documents.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize document database tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    mime_type TEXT,
                    upload_date TEXT NOT NULL,
                    status TEXT DEFAULT 'uploaded',
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_documents_user_id 
                ON documents(user_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_documents_upload_date 
                ON documents(upload_date)
            ''')
            
            conn.commit()
    
    def save_document(self, document_data: Dict[str, Any]) -> str:
        """Save document information to database."""
        doc_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO documents 
                (id, user_id, original_name, stored_name, file_path, 
                 file_size, file_type, mime_type, upload_date, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id,
                document_data['user_id'],
                document_data['original_name'],
                document_data['stored_name'],
                document_data['file_path'],
                document_data['file_size'],
                document_data['file_type'],
                document_data.get('mime_type'),
                document_data['upload_date'],
                document_data.get('status', 'uploaded'),
                document_data.get('metadata', '{}')
            ))
            conn.commit()
        
        return doc_id
    
    def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM documents 
                WHERE user_id = ? 
                ORDER BY upload_date DESC
            ''', (user_id,))
            
            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                # Parse metadata if it exists
                if doc['metadata']:
                    try:
                        doc['metadata'] = eval(doc['metadata'])
                    except:
                        doc['metadata'] = {}
                documents.append(doc)
            
            return documents
    
    def get_document_by_id(self, doc_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID (ensuring it belongs to the user)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM documents 
                WHERE id = ? AND user_id = ?
            ''', (doc_id, user_id))
            
            row = cursor.fetchone()
            if row:
                doc = dict(row)
                if doc['metadata']:
                    try:
                        doc['metadata'] = eval(doc['metadata'])
                    except:
                        doc['metadata'] = {}
                return doc
            
            return None
    
    def delete_document(self, doc_id: str, user_id: str) -> bool:
        """Delete a document from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM documents 
                WHERE id = ? AND user_id = ?
            ''', (doc_id, user_id))
            conn.commit()
            
            return cursor.rowcount > 0


# Initialize database
doc_db = DocumentDatabase()


class DocumentManager:
    """File management operations."""
    
    @staticmethod
    def get_user_upload_folder(user_id: str) -> str:
        """Get or create user-specific upload folder."""
        base_folder = current_app.config['UPLOAD_FOLDER']
        user_folder = os.path.join(base_folder, f"user_{user_id}")
        os.makedirs(user_folder, exist_ok=True)
        return user_folder
    
    @staticmethod
    def save_uploaded_file(file: FileStorage, user_id: str) -> Dict[str, Any]:
        """Save uploaded file to user's folder."""
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        # Secure the filename
        original_name = secure_filename(file.filename)
        if not original_name:
            raise ValueError("Invalid filename")
        
        # Generate unique filename
        file_extension = os.path.splitext(original_name)[1]
        stored_name = f"{uuid.uuid4()}{file_extension}"
        
        # Get user folder and save file
        user_folder = DocumentManager.get_user_upload_folder(user_id)
        file_path = os.path.join(user_folder, stored_name)
        
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        return {
            'original_name': original_name,
            'stored_name': stored_name,
            'file_path': file_path,
            'file_size': file_size,
            'file_type': file_extension.lower(),
            'mime_type': file.mimetype
        }
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete file from filesystem."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False


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
                
                # Save to database
                document_data = {
                    'user_id': user_id,
                    'upload_date': get_current_timestamp(),
                    **file_info
                }
                
                doc_id = doc_db.save_document(document_data)
                
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
        documents = doc_db.get_user_documents(user_id)
        
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
        document = doc_db.get_document_by_id(doc_id, user_id)
        
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
        
        # Get document info first
        document = doc_db.get_document_by_id(doc_id, user_id)
        if not document:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Delete from filesystem
        DocumentManager.delete_file(document['file_path'])
        
        # Delete from database
        success = doc_db.delete_document(doc_id, user_id)
        
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
        documents = doc_db.get_user_documents(user_id)
        
        # Calculate stats
        total_count = len(documents)
        total_size = sum(doc['file_size'] for doc in documents)
        
        # Group by file type
        type_stats = {}
        for doc in documents:
            file_type = doc['file_type'] or 'unknown'
            if file_type not in type_stats:
                type_stats[file_type] = {'count': 0, 'size': 0}
            type_stats[file_type]['count'] += 1
            type_stats[file_type]['size'] += doc['file_size']
        
        return success_response(
            data={
                'total_documents': total_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': type_stats
            },
            message="Document statistics retrieved successfully"
        )
    
    except Exception as e:
        current_app.logger.error(f"Document stats error: {str(e)}")
        return error_response("STATS_ERROR", "Failed to retrieve statistics", 500)
