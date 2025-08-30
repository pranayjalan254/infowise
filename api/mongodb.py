"""
MongoDB database module for document storage using GridFS.
Handles file storage and retrieval with MongoDB GridFS.
"""
import gridfs
import gridfs.errors
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from typing import Dict, Any, Optional, List, BinaryIO
from flask import current_app
from bson import ObjectId


class MongoDatabase:
    """MongoDB database operations with GridFS for file storage."""
    
    def __init__(self):
        """Initialize MongoDB connection."""
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._fs: Optional[gridfs.GridFS] = None
        self._documents_collection: Optional[Collection] = None
    
    def init_app(self, app):
        """Initialize MongoDB with Flask app."""
        self.connection_string = app.config['MONGODB_CONNECTION_STRING']
        self.database_name = app.config['MONGODB_DATABASE']
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection."""
        try:
            self._client = MongoClient(self.connection_string)
            self._db = self._client[self.database_name]
            self._fs = gridfs.GridFS(self._db)
            self._documents_collection = self._db.documents
            
            # Create indexes for better performance
            self._documents_collection.create_index("user_id")
            self._documents_collection.create_index("upload_date")
            self._documents_collection.create_index([("user_id", 1), ("upload_date", -1)])
            
        except Exception as e:
            current_app.logger.error(f"MongoDB connection error: {str(e)}")
            raise
    
    def store_file(self, file_data: bytes, file_info: Dict[str, Any]) -> str:
        """
        Store file in GridFS and metadata in documents collection.
        
        Args:
            file_data: Binary file data
            file_info: File metadata information
            
        Returns:
            Document ID string
        """
        if self._fs is None or self._documents_collection is None:
            raise RuntimeError("MongoDB not properly initialized")
            
        try:
            # Store file in GridFS
            file_id = self._fs.put(
                file_data,
                filename=file_info['original_name'],
                content_type=file_info.get('mime_type'),
                metadata={
                    'user_id': file_info['user_id'],
                    'original_name': file_info['original_name'],
                    'upload_date': file_info['upload_date']
                }
            )
            
            # Store document metadata
            document_data = {
                'user_id': file_info['user_id'],
                'file_id': file_id,
                'original_name': file_info['original_name'],
                'file_size': file_info['file_size'],
                'file_type': file_info['file_type'],
                'mime_type': file_info.get('mime_type'),
                'upload_date': file_info['upload_date'],
                'status': file_info.get('status', 'uploaded'),
                'metadata': file_info.get('metadata', {})
            }
            
            result = self._documents_collection.insert_one(document_data)
            return str(result.inserted_id)
            
        except Exception as e:
            current_app.logger.error(f"File storage error: {str(e)}")
            raise
    
    def get_file(self, doc_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve file and its metadata.
        
        Args:
            doc_id: Document ID
            user_id: User ID for authorization
            
        Returns:
            Dictionary with file data and metadata or None if not found
        """
        if self._fs is None or self._documents_collection is None:
            raise RuntimeError("MongoDB not properly initialized")
            
        try:
            # Get document metadata
            document = self._documents_collection.find_one({
                '_id': ObjectId(doc_id),
                'user_id': user_id
            })
            
            if not document:
                return None
            
            # Get file from GridFS
            try:
                file_data = self._fs.get(document['file_id'])
                return {
                    'id': str(document['_id']),
                    'user_id': document['user_id'],
                    'file_id': document['file_id'],
                    'original_name': document['original_name'],
                    'file_size': document['file_size'],
                    'file_type': document['file_type'],
                    'mime_type': document['mime_type'],
                    'upload_date': document['upload_date'],
                    'status': document['status'],
                    'metadata': document.get('metadata', {}),
                    'file_data': file_data.read()
                }
            except gridfs.errors.NoFile:
                current_app.logger.error(f"File not found in GridFS for doc_id: {doc_id}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"File retrieval error: {str(e)}")
            return None
    
    def get_document_metadata(self, doc_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata without file data.
        
        Args:
            doc_id: Document ID
            user_id: User ID for authorization
            
        Returns:
            Document metadata or None if not found
        """
        if self._documents_collection is None:
            raise RuntimeError("MongoDB not properly initialized")
            
        try:
            document = self._documents_collection.find_one({
                '_id': ObjectId(doc_id),
                'user_id': user_id
            })
            
            if document:
                return {
                    'id': str(document['_id']),
                    'user_id': document['user_id'],
                    'original_name': document['original_name'],
                    'file_size': document['file_size'],
                    'file_type': document['file_type'],
                    'mime_type': document['mime_type'],
                    'upload_date': document['upload_date'],
                    'status': document['status'],
                    'metadata': document.get('metadata', {})
                }
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Document metadata retrieval error: {str(e)}")
            return None
    
    def list_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of document metadata
        """
        if self._documents_collection is None:
            raise RuntimeError("MongoDB not properly initialized")
            
        try:
            documents = self._documents_collection.find(
                {'user_id': user_id}
            ).sort('upload_date', -1)
            
            result = []
            for doc in documents:
                result.append({
                    'id': str(doc['_id']),
                    'user_id': doc['user_id'],
                    'original_name': doc['original_name'],
                    'file_size': doc['file_size'],
                    'file_type': doc['file_type'],
                    'mime_type': doc['mime_type'],
                    'upload_date': doc['upload_date'],
                    'status': doc['status'],
                    'metadata': doc.get('metadata', {})
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Document list error: {str(e)}")
            return []
    
    def delete_document(self, doc_id: str, user_id: str) -> bool:
        """
        Delete document and its file from MongoDB.
        
        Args:
            doc_id: Document ID
            user_id: User ID for authorization
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if self._fs is None or self._documents_collection is None:
            raise RuntimeError("MongoDB not properly initialized")
            
        try:
            # Get document to find file_id
            document = self._documents_collection.find_one({
                '_id': ObjectId(doc_id),
                'user_id': user_id
            })
            
            if not document:
                return False
            
            # Delete file from GridFS
            try:
                self._fs.delete(document['file_id'])
            except gridfs.errors.NoFile:
                current_app.logger.warning(f"File not found in GridFS for deletion: {doc_id}")
            
            # Delete document metadata
            result = self._documents_collection.delete_one({
                '_id': ObjectId(doc_id),
                'user_id': user_id
            })
            
            return result.deleted_count > 0
            
        except Exception as e:
            current_app.logger.error(f"Document deletion error: {str(e)}")
            return False
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get user document statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with statistics
        """
        if self._documents_collection is None:
            raise RuntimeError("MongoDB not properly initialized")
            
        try:
            pipeline = [
                {'$match': {'user_id': user_id}},
                {'$group': {
                    '_id': None,
                    'total_documents': {'$sum': 1},
                    'total_size': {'$sum': '$file_size'},
                    'file_types': {'$push': '$file_type'}
                }}
            ]
            
            result = list(self._documents_collection.aggregate(pipeline))
            
            if not result:
                return {
                    'total_documents': 0,
                    'total_size_bytes': 0,
                    'total_size_mb': 0,
                    'file_types': {}
                }
            
            stats = result[0]
            
            # Count file types
            file_type_counts = {}
            for file_type in stats['file_types']:
                file_type = file_type or 'unknown'
                file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1
            
            return {
                'total_documents': stats['total_documents'],
                'total_size_bytes': stats['total_size'],
                'total_size_mb': round(stats['total_size'] / (1024 * 1024), 2),
                'file_types': file_type_counts
            }
            
        except Exception as e:
            current_app.logger.error(f"User stats error: {str(e)}")
            return {
                'total_documents': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'file_types': {}
            }


# Global MongoDB instance
mongo_db = MongoDatabase()


def init_mongodb(app):
    """Initialize MongoDB with Flask app."""
    mongo_db.init_app(app)


def get_mongo_db() -> MongoDatabase:
    """Get MongoDB database instance."""
    return mongo_db
