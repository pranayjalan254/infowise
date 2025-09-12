"""
Streaming PII Detection service.
Provides real-time updates during PII detection process using Server-Sent Events (SSE).
"""

import os
import tempfile
import json
from typing import Dict, Any, List, Generator
from flask import Blueprint, request, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.responses import success_response, error_response
from utils.helpers import get_current_timestamp
from mongodb import get_mongo_db
from enhanced_pii_detector import EnhancedPIIDetector

pii_streaming_bp = Blueprint('pii_streaming', __name__)

# MongoDB instance
mongo_db = get_mongo_db()


class StreamingPIIDetectionService:
    """Service for detecting PII in documents with streaming progress updates."""
    
    def __init__(self):
        # Get Google API key from environment
        google_api_key = os.getenv('GOOGLE_API_KEY')
        self.detector = EnhancedPIIDetector(google_api_key=google_api_key)
    
    def detect_pii_with_streaming(self, document_id: str, user_id: str) -> Generator[str, None, None]:
        """
        Detect PII in a document and yield streaming progress updates.
        
        Args:
            document_id: MongoDB document ID
            user_id: User ID for authorization
            
        Yields:
            Server-sent events with progress updates
        """
        try:
            print(f"Starting PII detection for document {document_id}, user {user_id}")
            
            # Get document from MongoDB
            document = mongo_db.get_file(document_id, user_id)
            if not document:
                print(f"Document {document_id} not found for user {user_id}")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Document not found'})}\n\n"
                return
            
            print(f"Document found: {document['original_name']}, type: {document['mime_type']}")
            
            # Check if it's a PDF
            if not document['mime_type'] == 'application/pdf':
                yield f"data: {json.dumps({'type': 'error', 'message': 'Only PDF documents are supported'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Initializing PII detection...', 'document_name': document['original_name']})}\n\n"
            
            # Save file temporarily for processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(document['file_data'])
                temp_pdf_path = temp_file.name
            
            print(f"Temporary file created: {temp_pdf_path}")
            
            try:
                # Extract text and detect PII with streaming updates
                print("Extracting text with coordinates...")
                pages_data = self.detector.extract_text_with_coordinates(temp_pdf_path)
                all_detected_pii = []
                total_pages = len(pages_data)
                
                print(f"Found {total_pages} pages to process")
                yield f"data: {json.dumps({'type': 'info', 'message': f'Processing {total_pages} pages...', 'total_pages': total_pages})}\n\n"
                
                for page_text, page_num, doc in pages_data:
                    if page_text.strip():  # Only process pages with text
                        # Yield progress update before processing page
                        yield f"data: {json.dumps({'type': 'progress', 'message': f'Analyzing page {page_num + 1}...', 'page': page_num + 1, 'total_pages': total_pages})}\n\n"
                        
                        # Get the page object for coordinate detection
                        page_obj = doc[page_num] if doc else None
                        page_pii = self.detector.detect_all_pii(page_text, page_num, page_obj)
                        all_detected_pii.extend(page_pii)
                        
                        # Yield page completion update
                        page_message = f"Page {page_num + 1}: Found {len(page_pii)} PII entities with coordinates"
                        print(page_message)
                        yield f"data: {json.dumps({'type': 'page_complete', 'message': page_message, 'page': page_num + 1, 'pii_count': len(page_pii), 'total_found': len(all_detected_pii)})}\n\n"
                    else:
                        # Empty page
                        yield f"data: {json.dumps({'type': 'page_complete', 'message': f'Page {page_num + 1}: No text found', 'page': page_num + 1, 'pii_count': 0, 'total_found': len(all_detected_pii)})}\n\n"
                
                # Close the document
                if pages_data and len(pages_data) > 0:
                    pages_data[0][2].close()
                
                yield f"data: {json.dumps({'type': 'status', 'message': 'Processing detection results...'})}\n\n"
                
                # Convert PIIEntity objects to dictionaries for JSON response
                pii_results = []
                for idx, pii in enumerate(all_detected_pii):
                    # Generate a consistent, positive, unique ID
                    id_components = f"{pii.text}_{pii.page_num}_{pii.x0:.2f}_{pii.y0:.2f}_{pii.pii_type}"
                    id_string = f"pii_{abs(hash(id_components))}"
                    
                    # Map severity to display format
                    severity_mapping = {
                        "high": "high",
                        "medium": "medium", 
                        "low": "low"
                    }
                    
                    pii_results.append({
                        'id': id_string,
                        'type': pii.pii_type,
                        'text': pii.text,
                        'confidence': float(pii.confidence),
                        'location': f"Page {pii.page_num + 1}",  # Add 1 for display
                        'severity': severity_mapping.get(pii.severity, 'medium'),
                        'suggested_strategy': pii.suggested_strategy,
                        'source': pii.source,  # Show detection source
                        'verified_by_llm': pii.verified_by_llm,
                        'coordinates': {
                            'page': int(pii.page_num),  # Store as 0-based for internal use
                            'x0': float(pii.x0),
                            'y0': float(pii.y0),
                            'x1': float(pii.x1),
                            'y1': float(pii.y1)
                        }
                    })
                
                # Generate detection report
                detection_report = self.detector.generate_detection_report(all_detected_pii)
                
                # Update document metadata with enhanced PII detection results
                detection_metadata = {
                    'pii_detection': {
                        'status': 'completed',
                        'detected_count': len(pii_results),
                        'detection_date': get_current_timestamp(),
                        'results': pii_results,
                        'detection_report': detection_report,
                        'methods_used': {
                            'bert': self.detector.bert_pipeline is not None,
                            'presidio': self.detector.presidio_analyzer is not None,
                            'regex': True,
                            'llm_verification': self.detector.gemini_llm is not None
                        }
                    }
                }
                
                mongo_db.update_document_metadata(document_id, user_id, detection_metadata)
                
                # Send final completion event
                final_result = {
                    'document_id': document_id,
                    'document_name': document['original_name'],
                    'total_pii_detected': len(pii_results),
                    'pii_items': pii_results,
                    'detection_date': detection_metadata['pii_detection']['detection_date']
                }
                
                yield f"data: {json.dumps({'type': 'complete', 'message': f'Detection complete! Found {len(pii_results)} PII entities across {total_pages} pages.', 'result': final_result})}\n\n"
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                    
        except Exception as e:
            # Use a simple print for debugging since we might not have app context
            print(f"Streaming PII detection error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Detection failed: {str(e)}'})}\n\n"


# Initialize service
streaming_pii_service = StreamingPIIDetectionService()


@pii_streaming_bp.route('/detect-stream/<document_id>', methods=['GET'])
def detect_pii_stream(document_id: str):
    """Stream PII detection progress for a specific document."""
    current_app.logger.info(f"Streaming PII detection endpoint called for document: {document_id}")
    
    # Get token from query parameter since EventSource doesn't support headers
    token = request.args.get('token')
    if not token:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': 'No authentication token provided'})}\n\n",
            mimetype='text/event-stream',
            status=401
        )
    
    # Verify JWT token manually
    from flask_jwt_extended import decode_token
    try:
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        current_app.logger.info(f"User ID from JWT: {user_id}")
    except Exception as e:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': 'Invalid authentication token'})}\n\n",
            mimetype='text/event-stream',
            status=401
        )
    
    def generate():
        try:
            for event in streaming_pii_service.detect_pii_with_streaming(document_id, user_id):
                yield event
        except Exception as e:
            # Log the error within the generator where we have access to the app context
            yield f"data: {json.dumps({'type': 'error', 'message': f'Detection failed: {str(e)}'})}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )


@pii_streaming_bp.route('/batch-detect-stream', methods=['POST'])
@jwt_required()
def batch_detect_pii_stream():
    """Stream batch PII detection progress for multiple documents."""
    try:
        current_app.logger.info("Streaming batch PII detection endpoint called")
        user_id = get_jwt_identity()
        
        data = request.get_json()
        if not data or 'document_ids' not in data:
            return error_response("VALIDATION_ERROR", "document_ids field is required", 400)
        
        document_ids = data['document_ids']
        
        def generate():
            total_docs = len(document_ids)
            yield f"data: {json.dumps({'type': 'batch_start', 'message': f'Starting batch detection for {total_docs} documents', 'total_documents': total_docs})}\n\n"
            
            for doc_index, document_id in enumerate(document_ids):
                yield f"data: {json.dumps({'type': 'document_start', 'message': f'Processing document {doc_index + 1} of {total_docs}', 'document_index': doc_index + 1, 'document_id': document_id})}\n\n"
                
                # Stream detection for this document
                for event in streaming_pii_service.detect_pii_with_streaming(document_id, user_id):
                    yield event
                
                yield f"data: {json.dumps({'type': 'document_complete', 'message': f'Document {doc_index + 1} processing complete', 'document_index': doc_index + 1})}\n\n"
            
            yield f"data: {json.dumps({'type': 'batch_complete', 'message': f'Batch processing complete for all {total_docs} documents'})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Batch streaming PII detection endpoint error: {str(e)}")
        return error_response("STREAMING_ERROR", "Failed to stream batch PII detection", 500)
