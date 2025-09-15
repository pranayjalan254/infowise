"""
Simplified Document Processing Service for Hackathon Prototype.
Handles the entire PII workflow without JWT/complex MongoDB setup.

Flow:
1. Upload PDF -> local storage + MongoDB
2. Generate config using pii_detector_config_generator.py 
3. Allow config editing via API endpoints
4. Apply masking using bert_pii_masker.py
5. Return masked PDF from local storage
"""

import os
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from flask import Blueprint, request, current_app, send_file
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from utils.responses import success_response, error_response
from utils.helpers import get_current_timestamp
from mongodb import get_mongo_db

simple_processing_bp = Blueprint('simple_processing', __name__)

# Directory paths - use absolute paths from app root
UPLOADS_DIR = Path("data/uploads")
CONFIGS_DIR = Path("configs")
RESULTS_DIR = Path("results")

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# MongoDB instance (still used for data persistence)
mongo_db = get_mongo_db()


class SimpleDocumentProcessor:
    """Simplified document processing without JWT complexity."""
    
    @staticmethod
    def generate_document_id() -> str:
        """Generate a simple document ID."""
        return str(uuid.uuid4())
    
    def upload_document(self, file: FileStorage) -> Dict[str, Any]:
        """
        Upload and store document locally and in MongoDB.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dictionary with document info
        """
        try:
            # Validate file
            if not file or not file.filename:
                raise ValueError("No file provided")
            
            # Security check
            filename = secure_filename(file.filename)
            if not filename:
                raise ValueError("Invalid filename")
            
            if not filename.lower().endswith('.pdf'):
                raise ValueError("Only PDF files are supported")
            
            # Generate unique document ID
            doc_id = self.generate_document_id()
            
            # Create unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{doc_id}_{filename}"
            
            # Save locally
            local_path = UPLOADS_DIR / unique_filename
            file.save(str(local_path))
            
            # Read file data for MongoDB
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Store in MongoDB
            try:
                mongo_doc_id = mongo_db.store_file(
                    file_data=file_data,
                    file_info={
                        'original_name': filename,
                        'file_size': len(file_data),
                        'file_type': file_extension,
                        'mime_type': 'application/pdf',
                        'user_id': 'a6b781b1-401b-435b-aaec-8821a38cf731', 
                        'upload_date': get_current_timestamp(),
                        'metadata': {'local_path': str(local_path)}
                    }
                )
            except Exception as e:
                current_app.logger.warning(f"MongoDB storage failed: {e}")
                mongo_doc_id = None
            
            return {
                'document_id': doc_id,
                'filename': filename,
                'original_name': filename,
                'size': len(file_data),
                'local_path': str(local_path),
                'mongo_id': mongo_doc_id,
                'upload_date': get_current_timestamp(),
                'status': 'uploaded'
            }
            
        except Exception as e:
            raise ValueError(f"Upload failed: {str(e)}")
    
    def generate_pii_config(self, document_id: str) -> Dict[str, Any]:
        """
        Generate PII configuration using pii_detector_config_generator.py
        
        Args:
            document_id: Document ID from upload
            
        Returns:
            Dictionary with config generation results
        """
        try:
            # Find the uploaded PDF
            pdf_files = list(UPLOADS_DIR.glob(f"{document_id}_*.pdf"))
            if not pdf_files:
                raise ValueError(f"PDF file not found for document_id: {document_id}")
            
            pdf_path = pdf_files[0]
            
            # Generate config file path
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            # Run pii_detector_config_generator.py
            current_app.logger.info(f"Running PII detection on: {pdf_path}")
            
            result = subprocess.run([
                'python', 'pii_detector_config_generator.py',
                str(pdf_path),
                str(config_path)
            ], capture_output=True, text=True, cwd=current_app.root_path)
            
            if result.returncode != 0:
                raise ValueError(f"PII detection failed: {result.stderr}")
            
            current_app.logger.info(f"PII detection completed: {result.stdout}")
            
            # Read and parse the generated config
            if not config_path.exists():
                raise ValueError("Config file was not generated")
            
            config_data = self._parse_config_file(config_path)
            
            return {
                'document_id': document_id,
                'config_path': str(config_path),
                'config_data': config_data,
                'total_pii': len(config_data),
                'status': 'config_generated'
            }
            
        except Exception as e:
            raise ValueError(f"Config generation failed: {str(e)}")
    
    def _parse_config_file(self, config_path: Path) -> List[Dict[str, Any]]:
        """Parse the PII config file into structured data."""
        config_data = []
        
        with open(config_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                try:
                    # Parse format: PII_TEXT:TYPE:STRATEGY:PAGE:X0:Y0:X1:Y1
                    # Handle cases where PII text might contain colons (like URLs, times, etc.)
                    parts = line.split(':')
                    if len(parts) >= 8:
                        # Standard format with all coordinates
                        # Reconstruct text in case it contains colons
                        text = ':'.join(parts[:-7])  # Everything except last 7 parts
                        pii_item = {
                            'id': f"pii_{line_num}",
                            'text': text,
                            'type': parts[-7],
                            'strategy': parts[-6],
                            'page': int(parts[-5]),
                            'coordinates': {
                                'x0': float(parts[-4]),
                                'y0': float(parts[-3]),
                                'x1': float(parts[-2]),
                                'y1': float(parts[-1]),
                            }
                        }
                    elif len(parts) >= 3:
                        # Minimal format: TEXT:TYPE:STRATEGY
                        text = ':'.join(parts[:-2])  # Everything except last 2 parts
                        pii_item = {
                            'id': f"pii_{line_num}",
                            'text': text,
                            'type': parts[-2],
                            'strategy': parts[-1],
                            'page': 0,
                            'coordinates': {
                                'x0': 0.0,
                                'y0': 0.0,
                                'x1': 0.0,
                                'y1': 0.0,
                            }
                        }
                    else:
                        continue  # Skip lines with insufficient parts
                    
                    config_data.append(pii_item)
                        
                except (ValueError, IndexError) as e:
                    current_app.logger.warning(f"Failed to parse config line {line_num}: {line} - Error: {e}")
        
        return config_data
    
    def get_config_data(self, document_id: str) -> Dict[str, Any]:
        """Get the current config data for a document."""
        try:
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            if not config_path.exists():
                raise ValueError("Config file not found")
            
            config_data = self._parse_config_file(config_path)
            
            return {
                'document_id': document_id,
                'config_data': config_data,
                'total_pii': len(config_data)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get config: {str(e)}")
    
    def update_config_data(self, document_id: str, config_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update the config file with new data from UI."""
        try:
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            # Write updated config file
            with open(config_path, 'w') as f:
                f.write("# Updated PII Masking Configuration File\n")
                f.write("# Format: PII_TEXT:TYPE:STRATEGY:PAGE:X0:Y0:X1:Y1\n")
                f.write("#\n")
                
                for pii_item in config_data:
                    coords = pii_item.get('coordinates', {})
                    # Handle both 'strategy' and 'suggested_strategy' fields
                    strategy = pii_item.get('strategy', pii_item.get('suggested_strategy', 'redact'))
                    line = (f"{pii_item['text']}:{pii_item['type']}:{strategy}:"
                           f"{pii_item.get('page', 0)}:{coords.get('x0', 0.0)}:"
                           f"{coords.get('y0', 0.0)}:{coords.get('x1', 0.0)}:{coords.get('y1', 0.0)}\n")
                    f.write(line)
            
            return {
                'document_id': document_id,
                'status': 'config_updated',
                'total_pii': len(config_data)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to update config: {str(e)}")
    
    def apply_masking(self, document_id: str) -> Dict[str, Any]:
        """
        Apply PII masking using bert_pii_masker.py
        
        Args:
            document_id: Document ID
            
        Returns:
            Dictionary with masking results
        """
        try:
            # Find input PDF
            pdf_files = list(UPLOADS_DIR.glob(f"{document_id}_*.pdf"))
            if not pdf_files:
                raise ValueError(f"PDF file not found for document_id: {document_id}")
            
            input_pdf = pdf_files[0]
            
            # Find config file
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            if not config_path.exists():
                raise ValueError("Config file not found. Generate config first.")
            
            # Create output path
            output_filename = f"{document_id}_masked.pdf"
            output_path = RESULTS_DIR / output_filename
            
            # Run bert_pii_masker.py
            current_app.logger.info(f"Applying PII masking: {input_pdf} -> {output_path}")
            
            result = subprocess.run([
                'python', 'bert_pii_masker.py',
                str(input_pdf),
                str(output_path),
                str(config_path)
            ], capture_output=True, text=True, cwd=current_app.root_path)
            
            if result.returncode != 0:
                raise ValueError(f"PII masking failed: {result.stderr}")
            
            current_app.logger.info(f"PII masking completed: {result.stdout}")
            
            # Verify output file exists
            if not output_path.exists():
                raise ValueError("Masked PDF was not generated")
            
            # Store masked PDF in MongoDB
            try:
                with open(output_path, 'rb') as f:
                    masked_data = f.read()
                
                mongo_doc_id = mongo_db.store_file(
                    file_data=masked_data,
                    file_info={
                        'original_name': output_filename,
                        'file_size': len(masked_data),
                        'file_type': '.pdf',
                        'mime_type': 'application/pdf',
                        'user_id': 'hackathon_user',
                        'upload_date': get_current_timestamp(),
                        'metadata': {
                            'original_document_id': document_id, 
                            'local_path': str(output_path)
                        }
                    }
                )
            except Exception as e:
                current_app.logger.warning(f"MongoDB storage failed for masked file: {e}")
                mongo_doc_id = None
            
            return {
                'document_id': document_id,
                'masked_document_id': f"{document_id}_masked",
                'output_path': str(output_path),
                'output_filename': output_filename,
                'mongo_id': mongo_doc_id,
                'file_size': output_path.stat().st_size,
                'status': 'masking_completed'
            }
            
        except Exception as e:
            raise ValueError(f"Masking failed: {str(e)}")


# Initialize processor
processor = SimpleDocumentProcessor()


# API Endpoints

@simple_processing_bp.route('/upload', methods=['POST'])
def upload_document():
    """Upload a PDF document."""
    try:
        if 'file' not in request.files:
            return error_response('No file provided', 'FILE_REQUIRED')
        
        file = request.files['file']
        result = processor.upload_document(file)
        
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'UPLOAD_ERROR')
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return error_response('Upload failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/generate-config/<document_id>', methods=['POST'])
def generate_config(document_id: str):
    """Generate PII configuration for a document."""
    try:
        result = processor.generate_pii_config(document_id)
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'CONFIG_ERROR')
    except Exception as e:
        current_app.logger.error(f"Config generation error: {str(e)}")
        return error_response('Config generation failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/config/<document_id>', methods=['GET'])
def get_config(document_id: str):
    """Get current PII configuration for a document."""
    try:
        result = processor.get_config_data(document_id)
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'CONFIG_ERROR')
    except Exception as e:
        current_app.logger.error(f"Get config error: {str(e)}")
        return error_response('Failed to get config', 'INTERNAL_ERROR')


@simple_processing_bp.route('/config/<document_id>', methods=['PUT'])
def update_config(document_id: str):
    """Update PII configuration for a document."""
    try:
        config_data = request.get_json()
        if not config_data or 'config_data' not in config_data:
            return error_response('Config data required', 'DATA_REQUIRED')
        
        result = processor.update_config_data(document_id, config_data['config_data'])
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'CONFIG_ERROR')
    except Exception as e:
        current_app.logger.error(f"Update config error: {str(e)}")
        return error_response('Failed to update config', 'INTERNAL_ERROR')


@simple_processing_bp.route('/apply-masking/<document_id>', methods=['POST'])
def apply_masking(document_id: str):
    """Apply PII masking to a document."""
    try:
        result = processor.apply_masking(document_id)
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'MASKING_ERROR')
    except Exception as e:
        current_app.logger.error(f"Masking error: {str(e)}")
        return error_response('Masking failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/download/<document_id>', methods=['GET'])
def download_masked_document(document_id: str):
    """Download the masked PDF document."""
    try:
        # Check if it's a masked document request
        if document_id.endswith('_masked'):
            output_filename = f"{document_id}.pdf"
            output_path = RESULTS_DIR / output_filename
        else:
            output_filename = f"{document_id}_masked.pdf"
            output_path = RESULTS_DIR / output_filename
        
        if not output_path.exists():
            return error_response('Masked document not found', 'FILE_NOT_FOUND')
        
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Download error: {str(e)}")
        return error_response('Download failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/status/<document_id>', methods=['GET'])
def get_document_status(document_id: str):
    """Get the processing status of a document."""
    try:
        status = {
            'document_id': document_id,
            'uploaded': False,
            'config_generated': False,
            'masking_completed': False
        }
        
        # Check if uploaded
        pdf_files = list(UPLOADS_DIR.glob(f"{document_id}_*.pdf"))
        if pdf_files:
            status['uploaded'] = True
        
        # Check if config exists
        config_path = CONFIGS_DIR / f"{document_id}_pii_config.txt"
        if config_path.exists():
            status['config_generated'] = True
        
        # Check if masked file exists
        masked_path = RESULTS_DIR / f"{document_id}_masked.pdf"
        if masked_path.exists():
            status['masking_completed'] = True
        
        return success_response(status)
        
    except Exception as e:
        current_app.logger.error(f"Status check error: {str(e)}")
        return error_response('Status check failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/preview/<document_id>', methods=['GET'])
def preview_original_document(document_id: str):
    """Serve the original PDF for preview."""
    try:
        pdf_files = list(UPLOADS_DIR.glob(f"{document_id}_*.pdf"))
        if not pdf_files:
            return error_response('Document not found', 'NOT_FOUND'), 404
        
        pdf_path = pdf_files[0]
        response = send_file(
            pdf_path, 
            mimetype='application/pdf',
            as_attachment=False,
            download_name=pdf_path.name
        )
        # Allow iframe embedding for PDF preview
        response.headers['X-Allow-Iframe'] = 'true'
        return response
        
    except Exception as e:
        current_app.logger.error(f"Preview error: {str(e)}")
        return error_response('Preview failed', 'INTERNAL_ERROR'), 500


@simple_processing_bp.route('/preview-masked/<document_id>', methods=['GET'])
def preview_masked_document(document_id: str):
    """Serve the masked PDF for preview."""
    try:
        masked_path = RESULTS_DIR / f"{document_id}_masked.pdf"
        if not masked_path.exists():
            return error_response('Masked document not found', 'NOT_FOUND'), 404
        
        response = send_file(
            masked_path, 
            mimetype='application/pdf',
            as_attachment=False,
            download_name=masked_path.name
        )
        # Allow iframe embedding for PDF preview
        response.headers['X-Allow-Iframe'] = 'true'
        return response
        
    except Exception as e:
        current_app.logger.error(f"Masked preview error: {str(e)}")
        return error_response('Masked preview failed', 'INTERNAL_ERROR'), 500
