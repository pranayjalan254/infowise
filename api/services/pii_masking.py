"""
PII Masking service.
Handles masking of PII in documents using enhanced coordinate-based configuration
with overlap resolution and multiple detection methods.
"""

import os
import tempfile
import subprocess
from typing import Dict, Any, List
from flask import Blueprint, request, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.responses import success_response, error_response
from utils.helpers import get_current_timestamp
from mongodb import get_mongo_db
from enhanced_pii_masker import EnhancedPIIMasker, MaskingConfig

pii_masking_bp = Blueprint('pii_masking', __name__)

# MongoDB instance
mongo_db = get_mongo_db()


class PIIMaskingService:
    """Enhanced service for masking PII in documents with coordinate overlap resolution."""
    
    def __init__(self):
        self.masker = EnhancedPIIMasker()
    
    def apply_masking_to_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """
        Apply PII masking to a document using enhanced methods and coordinate overlap resolution.
        
        Args:
            document_id: MongoDB document ID
            user_id: User ID for authorization
            
        Returns:
            Dictionary containing comprehensive masking results and masked file info
        """
        try:
            # Get document from MongoDB
            document = mongo_db.get_file(document_id, user_id)
            if not document:
                raise ValueError("Document not found")
            
            # Check if it's a PDF
            if not document['mime_type'] == 'application/pdf':
                raise ValueError("Only PDF documents are supported for PII masking")
            
            # Get document metadata to check for PII detection and masking config
            metadata = mongo_db.get_document_metadata(document_id, user_id)
            if not metadata:
                raise ValueError("Document metadata not found")
            
            # Check if PII detection has been run
            pii_detection = metadata.get('metadata', {}).get('pii_detection')
            if not pii_detection or pii_detection.get('status') != 'completed':
                raise ValueError("PII detection must be completed before masking")
            
            # Check if masking configuration exists
            masking_config = metadata.get('metadata', {}).get('masking_config')
            if not masking_config or masking_config.get('status') != 'configured':
                raise ValueError("Masking configuration not found. Please configure masking strategies first.")
            
            # Create temporary files for input and output PDFs
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as input_temp:
                input_temp.write(document['file_data'])
                input_pdf_path = input_temp.name
            
            output_pdf_path = tempfile.mktemp(suffix='_masked.pdf')
            
            try:
                # Generate enhanced masking configurations
                masking_configs = self._generate_enhanced_masking_configs(
                    pii_detection, masking_config
                )
                
                if not masking_configs:
                    raise ValueError("No PII configurations generated for masking")
                
                current_app.logger.info(f"Generated {len(masking_configs)} masking configurations")
                current_app.logger.info(f"Sample config: {masking_configs[0].__dict__ if masking_configs else 'None'}")
                
                # Apply enhanced masking with coordinate overlap resolution using pre-configured strategies
                masking_stats = self.masker.mask_pdf_with_preconfigured_strategies(
                    input_pdf_path, output_pdf_path, masking_configs
                )
                
                # Read the masked PDF
                if not os.path.exists(output_pdf_path):
                    raise ValueError("Masked PDF file was not created")
                
                with open(output_pdf_path, 'rb') as masked_file:
                    masked_pdf_data = masked_file.read()
                
                # Save masked document to MongoDB
                masked_filename = f"masked_{document['original_name']}"
                masked_document_id = mongo_db.store_file(
                    file_data=masked_pdf_data,
                    file_info={
                        'user_id': user_id,
                        'original_name': masked_filename,
                        'file_size': len(masked_pdf_data),
                        'file_type': 'pdf',
                        'mime_type': 'application/pdf',
                        'upload_date': get_current_timestamp(),
                        'status': 'masked',
                        'metadata': {
                            'original_document_id': document_id,
                            'masking_applied': True,
                            'masking_date': get_current_timestamp(),
                            'masking_stats': masking_stats,
                            'enhanced_masking': True,
                            'coordinate_overlaps_resolved': masking_stats.get('overlaps_resolved', 0),
                            'quality_score': masking_stats.get('quality_score', 0)
                        }
                    }
                )
                
                # Update original document metadata with enhanced masking results
                masking_metadata = {
                    'masking_results': {
                        'status': 'completed',
                        'masked_document_id': masked_document_id,
                        'masked_filename': masked_filename,
                        'masking_date': get_current_timestamp(),
                        'stats': masking_stats,
                        'total_pii_masked': masking_stats.get('successful_maskings', 0),
                        'strategies_used': masking_stats.get('strategies_used', {}),
                        'failed_maskings': masking_stats.get('failed_maskings', 0),
                        'overlaps_resolved': masking_stats.get('overlaps_resolved', 0),
                        'quality_score': masking_stats.get('quality_score', 0),
                        'enhanced_masking': True
                    }
                }
                
                mongo_db.update_document_metadata(document_id, user_id, masking_metadata)
                
                return {
                    'original_document_id': document_id,
                    'masked_document_id': masked_document_id,
                    'masked_filename': masked_filename,
                    'masking_stats': masking_stats,
                    'total_pii_masked': masking_stats.get('successful_maskings', 0),
                    'strategies_used': masking_stats.get('strategies_used', {}),
                    'overlaps_resolved': masking_stats.get('overlaps_resolved', 0),
                    'quality_score': masking_stats.get('quality_score', 0),
                    'masking_date': masking_metadata['masking_results']['masking_date']
                }
                
            finally:
                # Clean up temporary files
                for temp_path in [input_pdf_path, output_pdf_path]:
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass
                            
        except Exception as e:
            current_app.logger.error(f"Enhanced PII masking error: {str(e)}")
            raise
    
    def _generate_enhanced_masking_configs(self, pii_detection: Dict, masking_config: Dict) -> List[MaskingConfig]:
        """
        Generate enhanced MaskingConfig objects from PII detection results and masking configuration.
        
        Args:
            pii_detection: Enhanced PII detection metadata
            masking_config: Masking configuration metadata
            
        Returns:
            List of enhanced MaskingConfig objects
        """
        masking_configs = []
        pii_items = pii_detection.get('results', [])
        strategies = masking_config.get('strategies', {})
        
        current_app.logger.info(f"Generating enhanced masking configs - Found {len(pii_items)} PII items and {len(strategies)} strategies")
        current_app.logger.info(f"Strategy keys: {list(strategies.keys())}")
        current_app.logger.info(f"First few strategies: {dict(list(strategies.items())[:5])}")  # Log first 5 strategies
        
        for pii_item in pii_items:
            pii_id = pii_item.get('id')
            strategy = strategies.get(pii_id)
            
            current_app.logger.info(f"Processing PII item {pii_id} with strategy: {strategy} for text: '{pii_item.get('text', '')[:20]}...'")
            
            if not strategy:
                current_app.logger.warning(f"No strategy found for PII item {pii_id}, using suggested strategy")
                strategy = pii_item.get('suggested_strategy', 'redact')
            
            coordinates = pii_item.get('coordinates', {})
            
            # Create enhanced MaskingConfig object with priority
            priority = self._get_strategy_priority(strategy)
            
            config = MaskingConfig(
                text=pii_item.get('text', ''),
                pii_type=pii_item.get('type', ''),
                strategy=strategy,
                page_num=coordinates.get('page', 0),
                x0=coordinates.get('x0', 0.0),
                y0=coordinates.get('y0', 0.0),
                x1=coordinates.get('x1', 0.0),
                y1=coordinates.get('y1', 0.0),
                priority=priority
            )
            
            masking_configs.append(config)
            current_app.logger.debug(f"Created MaskingConfig: text='{config.text[:20]}...', type={config.pii_type}, strategy={config.strategy}")
        
        current_app.logger.info(f"Generated {len(masking_configs)} enhanced masking configurations")
        return masking_configs
    
    def _get_strategy_priority(self, strategy: str) -> int:
        """Get priority level for masking strategy for overlap resolution."""
        priorities = {
            "redact": 3,    # Highest priority - complete removal
            "mask": 2,      # Medium priority - character replacement
            "pseudo": 1     # Lowest priority - text replacement
        }
        return priorities.get(strategy, 1)
    
    def get_masked_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get masked document file data.
        
        Args:
            document_id: Original document ID
            user_id: User ID for authorization
            
        Returns:
            Dictionary containing masked document data
        """
        try:
            # Get original document metadata
            metadata = mongo_db.get_document_metadata(document_id, user_id)
            if not metadata:
                raise ValueError("Document not found")
            
            # Check if masking has been applied
            masking_results = metadata.get('metadata', {}).get('masking_results')
            if not masking_results or masking_results.get('status') != 'completed':
                raise ValueError("No masked document available. Please apply masking first.")
            
            masked_document_id = masking_results.get('masked_document_id')
            if not masked_document_id:
                raise ValueError("Masked document ID not found")
            
            # Get the masked document
            masked_document = mongo_db.get_file(masked_document_id, user_id)
            if not masked_document:
                raise ValueError("Masked document file not found")
            
            return {
                'file_data': masked_document['file_data'],
                'filename': masked_document['original_name'],
                'mime_type': masked_document['mime_type'],
                'size': len(masked_document['file_data']),
                'masking_date': masking_results.get('masking_date'),
                'stats': masking_results.get('stats', {})
            }
            
        except Exception as e:
            current_app.logger.error(f"Get masked document error: {str(e)}")
            raise


# Initialize service
masking_service = PIIMaskingService()


@pii_masking_bp.route('/apply/<document_id>', methods=['POST'])
@jwt_required()
def apply_masking(document_id: str):
    """Apply PII masking to a document."""
    try:
        current_app.logger.info(f"Apply masking endpoint called for document: {document_id}")
        user_id = get_jwt_identity()
        
        # Apply masking to the document
        masking_results = masking_service.apply_masking_to_document(document_id, user_id)
        
        return success_response(
            data=masking_results,
            message=f"PII masking completed. Masked {masking_results['total_pii_masked']} PII items."
        )
        
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Apply masking endpoint error: {str(e)}")
        return error_response("MASKING_ERROR", "Failed to apply PII masking", 500)


@pii_masking_bp.route('/download/<document_id>', methods=['GET'])
@jwt_required()
def download_masked_document(document_id: str):
    """Download the masked version of a document."""
    try:
        current_app.logger.info(f"Download masked document endpoint called for document: {document_id}")
        user_id = get_jwt_identity()
        
        # Get masked document data
        masked_doc = masking_service.get_masked_document(document_id, user_id)
        
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(masked_doc['file_data'])
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=masked_doc['filename'],
            mimetype=masked_doc['mime_type']
        )
        
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Download masked document error: {str(e)}")
        return error_response("DOWNLOAD_ERROR", "Failed to download masked document", 500)


@pii_masking_bp.route('/preview/<document_id>', methods=['GET'])
@jwt_required()
def preview_masked_document(document_id: str):
    """Get masked document for preview (returns file data in response)."""
    try:
        current_app.logger.info(f"Preview masked document endpoint called for document: {document_id}")
        user_id = get_jwt_identity()
        
        # Get masked document data
        masked_doc = masking_service.get_masked_document(document_id, user_id)
        
        # Create temporary file for preview
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(masked_doc['file_data'])
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            mimetype=masked_doc['mime_type'],
            as_attachment=False
        )
        
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Preview masked document error: {str(e)}")
        return error_response("PREVIEW_ERROR", "Failed to preview masked document", 500)


@pii_masking_bp.route('/debug/<document_id>', methods=['GET'])
@jwt_required()
def debug_masking_config(document_id: str):
    """Debug endpoint to check PII detection and masking configuration alignment."""
    try:
        user_id = get_jwt_identity()
        
        # Get document metadata
        metadata = mongo_db.get_document_metadata(document_id, user_id)
        if not metadata:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Get PII detection results
        pii_detection = metadata.get('metadata', {}).get('pii_detection')
        masking_config = metadata.get('metadata', {}).get('masking_config')
        
        debug_info = {
            'has_pii_detection': bool(pii_detection),
            'has_masking_config': bool(masking_config),
            'pii_detection_status': pii_detection.get('status') if pii_detection else None,
            'masking_config_status': masking_config.get('status') if masking_config else None,
        }
        
        if pii_detection:
            pii_items = pii_detection.get('results', [])
            debug_info['pii_items_count'] = len(pii_items)
            debug_info['pii_item_ids'] = [item.get('id') for item in pii_items[:10]]  # First 10
        
        if masking_config:
            strategies = masking_config.get('strategies', {})
            debug_info['strategy_count'] = len(strategies)
            debug_info['strategy_ids'] = list(strategies.keys())[:10]  # First 10
            
            # Check for matches
            if pii_detection:
                pii_ids = set(item.get('id') for item in pii_detection.get('results', []))
                strategy_ids = set(strategies.keys())
                debug_info['matching_ids'] = len(pii_ids & strategy_ids)
                debug_info['missing_strategies'] = list(pii_ids - strategy_ids)[:5]
                debug_info['extra_strategies'] = list(strategy_ids - pii_ids)[:5]
        
        return success_response(data=debug_info, message="Debug information retrieved")
        
    except Exception as e:
        current_app.logger.error(f"Debug masking config error: {str(e)}")
        return error_response("DEBUG_ERROR", "Failed to retrieve debug information", 500)


@pii_masking_bp.route('/preview-original/<document_id>', methods=['GET'])
@jwt_required()
def preview_original_document(document_id: str):
    """Get original document for preview comparison."""
    try:
        current_app.logger.info(f"Preview original document endpoint called for document: {document_id}")
        user_id = get_jwt_identity()
        
        # Get original document data
        document = mongo_db.get_file(document_id, user_id)
        if not document:
            raise ValueError("Document not found")
        
        # Create temporary file for preview
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(document['file_data'])
            temp_path = temp_file.name
        
        return send_file(
            temp_path,
            mimetype=document['mime_type'],
            as_attachment=False
        )
        
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Preview original document error: {str(e)}")
        return error_response("PREVIEW_ERROR", "Failed to preview original document", 500)


@pii_masking_bp.route('/status/<document_id>', methods=['GET'])
@jwt_required()
def get_masking_status(document_id: str):
    """Get masking status and results for a document."""
    try:
        user_id = get_jwt_identity()
        
        # Get document metadata
        metadata = mongo_db.get_document_metadata(document_id, user_id)
        if not metadata:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Get masking results
        masking_results = metadata.get('metadata', {}).get('masking_results')
        if not masking_results:
            return success_response(
                data={
                    'document_id': document_id,
                    'status': 'not_started',
                    'message': 'Masking has not been applied to this document'
                },
                message="No masking results found"
            )
        
        return success_response(
            data={
                'document_id': document_id,
                'status': masking_results['status'],
                'masked_document_id': masking_results.get('masked_document_id'),
                'masked_filename': masking_results.get('masked_filename'),
                'masking_date': masking_results.get('masking_date'),
                'total_pii_masked': masking_results.get('total_pii_masked', 0),
                'strategies_used': masking_results.get('strategies_used', {}),
                'failed_maskings': masking_results.get('failed_maskings', 0),
                'stats': masking_results.get('stats', {})
            },
            message="Masking status retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Get masking status error: {str(e)}")
        return error_response("STATUS_ERROR", "Failed to retrieve masking status", 500)
    """Get masking status and results for a document."""
    try:
        user_id = get_jwt_identity()
        
        # Get document metadata
        metadata = mongo_db.get_document_metadata(document_id, user_id)
        if not metadata:
            return error_response("NOT_FOUND", "Document not found", 404)
        
        # Get masking results
        masking_results = metadata.get('metadata', {}).get('masking_results')
        if not masking_results:
            return success_response(
                data={
                    'document_id': document_id,
                    'status': 'not_started',
                    'message': 'Masking has not been applied to this document'
                },
                message="No masking results found"
            )
        
        return success_response(
            data={
                'document_id': document_id,
                'status': masking_results['status'],
                'masked_document_id': masking_results.get('masked_document_id'),
                'masked_filename': masking_results.get('masked_filename'),
                'masking_date': masking_results.get('masking_date'),
                'total_pii_masked': masking_results.get('total_pii_masked', 0),
                'strategies_used': masking_results.get('strategies_used', {}),
                'failed_maskings': masking_results.get('failed_maskings', 0),
                'stats': masking_results.get('stats', {})
            },
            message="Masking status retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Get masking status error: {str(e)}")
        return error_response("STATUS_ERROR", "Failed to retrieve masking status", 500)
