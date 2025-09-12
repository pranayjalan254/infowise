"""
PII Detection service.
Handles detection of PII in uploaded documents using enhanced multi-method detection.
Combines BERT, Presidio/spaCy, regex patterns, and optional LLM verification.
"""

import os
import tempfile
from typing import Dict, Any, List
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.responses import success_response, error_response
from utils.helpers import get_current_timestamp
from mongodb import get_mongo_db
from enhanced_pii_detector import EnhancedPIIDetector

pii_detection_bp = Blueprint('pii_detection', __name__)

# MongoDB instance
mongo_db = get_mongo_db()


class PIIDetectionService:
    """Enhanced service for detecting PII in documents using multiple methods."""
    
    def __init__(self):
        # Get Google API key from environment
        google_api_key = os.getenv('GOOGLE_API_KEY')
        self.detector = EnhancedPIIDetector(google_api_key=google_api_key)
    
    def detect_pii_in_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """
        Detect PII in a document using enhanced multi-method detection.
        
        Args:
            document_id: MongoDB document ID
            user_id: User ID for authorization
            
        Returns:
            Dictionary containing comprehensive PII detection results
        """
        try:
            # Get document from MongoDB
            document = mongo_db.get_file(document_id, user_id)
            if not document:
                raise ValueError("Document not found")
            
            # Check if it's a PDF
            if not document['mime_type'] == 'application/pdf':
                raise ValueError("Only PDF documents are supported for PII detection")
            
            # Save file temporarily for processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(document['file_data'])
                temp_pdf_path = temp_file.name
            
            try:
                # Extract text and detect PII using enhanced detector
                pages_data = self.detector.extract_text_with_coordinates(temp_pdf_path)
                all_detected_pii = []
                
                for page_text, page_num, doc in pages_data:
                    if page_text.strip():  # Only process pages with text
                        page = doc[page_num]
                        page_pii = self.detector.detect_all_pii(page_text, page_num, page)
                        all_detected_pii.extend(page_pii)
                
                # Close the document
                if pages_data and len(pages_data) > 0:
                    pages_data[0][2].close()
                
                # Convert PIIEntity objects to dictionaries for JSON response
                pii_results = []
                for idx, pii in enumerate(all_detected_pii):
                    # Generate a consistent, unique ID
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
                        'location': f"Page {pii.page_num + 1}",  # Display as 1-based
                        'severity': severity_mapping.get(pii.severity, 'medium'),
                        'suggested_strategy': pii.suggested_strategy,
                        'source': pii.source,  # Show detection source
                        'verified_by_llm': pii.verified_by_llm,
                        'coordinates': {
                            'page': int(pii.page_num),  # Store as 0-based
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
                
                return {
                    'document_id': document_id,
                    'document_name': document['original_name'],
                    'total_pii_detected': len(pii_results),
                    'pii_items': pii_results,
                    'detection_date': detection_metadata['pii_detection']['detection_date']
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                    
        except Exception as e:
            current_app.logger.error(f"PII detection error: {str(e)}")
            raise
    
    def _determine_severity(self, pii_type: str) -> str:
        """Determine severity level based on PII type."""
        high_risk_types = [
            'SSN', 'CREDIT_CARD', 'BANK_ACCOUNT', 'AADHAAR'
        ]
        medium_risk_types = [
            'EMAIL', 'PHONE', 'DATE_OF_BIRTH', 'PAN', 'INDIAN_VOTER_ID'
        ]
        
        if pii_type in high_risk_types:
            return 'high'
        elif pii_type in medium_risk_types:
            return 'medium'
        else:
            return 'low'


# Initialize service
pii_service = PIIDetectionService()


@pii_detection_bp.route('/detect/<document_id>', methods=['POST'])
@jwt_required()
def detect_pii(document_id: str):
    """Detect PII in a specific document."""
    try:
        current_app.logger.info(f"PII detection endpoint called for document: {document_id}")
        user_id = get_jwt_identity()
        current_app.logger.info(f"User ID from JWT: {user_id}")
        
        # Detect PII in the document
        detection_results = pii_service.detect_pii_in_document(document_id, user_id)
        
        return success_response(
            data=detection_results,
            message=f"PII detection completed. Found {detection_results['total_pii_detected']} PII items."
        )
        
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        current_app.logger.error(f"PII detection endpoint error: {str(e)}")
        return error_response("DETECTION_ERROR", "Failed to detect PII", 500)


@pii_detection_bp.route('/save-config/<document_id>', methods=['POST'])
@jwt_required()
def save_masking_config(document_id: str):
    """Save masking configuration for a document."""
    try:
        current_app.logger.info(f"Save masking config endpoint called for document: {document_id}")
        user_id = get_jwt_identity()
        
        data = request.get_json()
        if not data or 'masking_strategies' not in data:
            return error_response("VALIDATION_ERROR", "masking_strategies field is required", 400)
        
        masking_strategies = data['masking_strategies']
        
        # Update document metadata with masking configuration
        config_metadata = {
            'masking_config': {
                'status': 'configured',
                'config_date': get_current_timestamp(),
                'strategies': masking_strategies,
                'total_items': len(masking_strategies)
            }
        }
        
        mongo_db.update_document_metadata(document_id, user_id, config_metadata)
        
        return success_response(
            data={
                'document_id': document_id,
                'total_items': len(masking_strategies)
            },
            message="Masking configuration saved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Save masking config error: {str(e)}")
        return error_response("CONFIG_SAVE_ERROR", str(e), 500)


@pii_detection_bp.route('/results/<document_id>', methods=['GET'])
@jwt_required()
def get_pii_results(document_id: str):
    """Get previously detected PII results for a document."""
    try:
        user_id = get_jwt_identity()
        
        # Get document metadata
        document = mongo_db.get_document_metadata(document_id, user_id)
        if not document:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Check if PII detection has been run
        pii_detection = document.get('metadata', {}).get('pii_detection')
        if not pii_detection:
            return error_response("NOT_FOUND", "No PII detection results found", 404)
        
        return success_response(
            data={
                'document_id': document_id,
                'document_name': document['original_name'],
                'detection_status': pii_detection['status'],
                'total_pii_detected': pii_detection['detected_count'],
                'pii_items': pii_detection['results'],
                'detection_date': pii_detection['detection_date']
            },
            message="PII detection results retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Get PII results error: {str(e)}")
        return error_response("RETRIEVAL_ERROR", "Failed to retrieve PII results", 500)


@pii_detection_bp.route('/batch-detect', methods=['POST'])
@jwt_required()
def batch_detect_pii():
    """Detect PII in multiple documents."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'document_ids' not in data:
            return error_response("INVALID_REQUEST", "document_ids required", 400)
        
        document_ids = data['document_ids']
        if not isinstance(document_ids, list) or not document_ids:
            return error_response("INVALID_REQUEST", "document_ids must be a non-empty list", 400)
        
        results = []
        errors = []
        
        for doc_id in document_ids:
            try:
                detection_result = pii_service.detect_pii_in_document(doc_id, user_id)
                results.append(detection_result)
            except Exception as e:
                errors.append(f"Document {doc_id}: {str(e)}")
        
        response_data = {
            'results': results,
            'total_processed': len(results),
            'total_requested': len(document_ids)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return success_response(
            data=response_data,
            message=f"Batch PII detection completed. Processed {len(results)} out of {len(document_ids)} documents."
        )
        
    except Exception as e:
        current_app.logger.error(f"Batch PII detection error: {str(e)}")
        return error_response("BATCH_DETECTION_ERROR", "Failed to process batch PII detection", 500)
