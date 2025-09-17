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
            
            # Check for supported file types
            supported_extensions = ['.pdf', '.docx', '.txt']
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension not in supported_extensions:
                raise ValueError("Only PDF, Word (.docx), and text (.txt) files are supported")
            
            # Generate unique document ID
            doc_id = self.generate_document_id()
            
            # Create unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{doc_id}_{filename}"
            
            # Determine MIME type based on extension
            mime_type_map = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.txt': 'text/plain'
            }
            mime_type = mime_type_map.get(file_extension.lower(), 'application/octet-stream')
            
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
                        'status': 'uploaded',
                        'file_type': file_extension,
                        'mime_type': mime_type,
                        'user_id': 'a6b781b1-401b-435b-aaec-8821a38cf731', 
                        'upload_date': get_current_timestamp(),
                        'metadata': {
                            'local_path': str(local_path),
                            'document_id': doc_id
                        }
                    }
                )
                current_app.logger.info(f"Original file stored in MongoDB with ID: {mongo_doc_id}")
            except Exception as e:
                current_app.logger.error(f"MongoDB storage failed: {e}")
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
            # Find the uploaded file - support multiple extensions
            supported_extensions = ['*.pdf', '*.docx', '*.txt']
            uploaded_files = []
            for ext in supported_extensions:
                uploaded_files.extend(list(UPLOADS_DIR.glob(f"{document_id}_{ext}")))
            
            if not uploaded_files:
                raise ValueError(f"Document file not found for document_id: {document_id}")
            
            document_path = uploaded_files[0]
            
            # Generate config file path
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            # Run pii_detector_config_generator.py
            current_app.logger.info(f"Running PII detection on: {document_path}")
            
            result = subprocess.run([
                'python', 'pii_detector_config_generator.py',
                str(document_path),
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
            # Find input document - support multiple extensions
            supported_extensions = ['*.pdf', '*.docx', '*.txt']
            input_files = []
            for ext in supported_extensions:
                input_files.extend(list(UPLOADS_DIR.glob(f"{document_id}_{ext}")))
            
            if not input_files:
                raise ValueError(f"Document file not found for document_id: {document_id}")
            
            input_document = input_files[0]
            
            # Find config file
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            if not config_path.exists():
                raise ValueError("Config file not found. Generate config first.")
            
            # For non-PDF documents, convert to PDF first
            file_extension = input_document.suffix.lower()
            if file_extension != '.pdf':
                # Convert to PDF format for masking
                temp_pdf_path = UPLOADS_DIR / f"{document_id}_converted.pdf"
                
                current_app.logger.info(f"Converting {file_extension} document to PDF for masking")
                
                # Import and use the document converter
                from document_converter import DocumentConverter
                converter = DocumentConverter()
                
                if not converter.convert_to_pdf(str(input_document), str(temp_pdf_path)):
                    raise ValueError(f"Failed to convert {file_extension} document to PDF for masking")
                
                # Use the converted PDF for masking
                masking_input = temp_pdf_path
            else:
                masking_input = input_document
            
            # Create output path
            output_filename = f"{document_id}_masked.pdf"
            output_path = RESULTS_DIR / output_filename
            
            # Run bert_pii_masker.py
            current_app.logger.info(f"Applying PII masking: {masking_input} -> {output_path}")
            
            result = subprocess.run([
                'python', 'bert_pii_masker.py',
                str(masking_input),
                str(output_path),
                str(config_path)
            ], capture_output=True, text=True, cwd=current_app.root_path)
            
            if result.returncode != 0:
                raise ValueError(f"PII masking failed: {result.stderr}")
            
            current_app.logger.info(f"PII masking completed: {result.stdout}")
            
            # Verify output file exists
            if not output_path.exists():
                raise ValueError("Masked PDF was not generated")
            
            # Clean up temporary converted PDF if it was created
            if file_extension != '.pdf':
                try:
                    temp_pdf_path.unlink()  # Delete the temporary PDF
                    current_app.logger.info("Cleaned up temporary converted PDF")
                except Exception as e:
                    current_app.logger.warning(f"Failed to clean up temporary PDF: {e}")
            
            # Store masked PDF in MongoDB
            try:
                with open(output_path, 'rb') as f:
                    masked_data = f.read()
                
                mongo_doc_id = mongo_db.store_file(
                    file_data=masked_data,
                    file_info={
                        'original_name': output_filename,
                        'file_size': len(masked_data),
                        'status': 'masked',
                        'file_type': '.pdf',
                        'mime_type': 'application/pdf',
                        'user_id': 'a6b781b1-401b-435b-aaec-8821a38cf731',
                        'upload_date': get_current_timestamp(),
                        'metadata': {
                            'original_document_id': document_id,
                            'document_id': document_id,  # Add this for consistent querying
                            'local_path': str(output_path),
                            'processing_type': 'pii_masking',
                            'config_file': str(config_path)
                        }
                    }
                )
                current_app.logger.info(f"Masked file stored in MongoDB with ID: {mongo_doc_id}")
            except Exception as e:
                current_app.logger.error(f"MongoDB storage failed for masked file: {e}")
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
    
    def get_document_info_from_mongo(self, document_id: str, status: str = None) -> Dict[str, Any]:
        """
        Retrieve document information from MongoDB.
        
        Args:
            document_id: Document ID
            status: Filter by status ('uploaded', 'masked', etc.)
            
        Returns:
            Dictionary with document info from MongoDB
        """
        try:
            query = {'metadata.document_id': document_id}
            if status:
                query['status'] = status
            
            files = mongo_db.get_files(query)
            
            return {
                'document_id': document_id,
                'files': files,
                'total_files': len(files)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to retrieve document info: {str(e)}")

    def cleanup_processing_data(self, document_id: str) -> Dict[str, Any]:
        """
        Clean up all processing data for a document after masking is complete.
        This removes:
        1. Input documents from MongoDB (status='uploaded')
        2. Input files from local storage
        3. Config files from local storage
        
        Keeps:
        1. Masked documents in MongoDB (status='masked')
        2. Masked files in local storage (for redundancy)
        
        Args:
            document_id: Document ID to clean up
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            cleanup_results = {
                'document_id': document_id,
                'mongodb_input_deleted': 0,
                'local_input_files_deleted': [],
                'config_files_deleted': [],
                'errors': []
            }
            
            # 1. Remove input documents from MongoDB (keep masked ones)
            try:
                deleted_count = mongo_db.delete_documents_by_document_id(document_id, status='uploaded')
                cleanup_results['mongodb_input_deleted'] = deleted_count
                current_app.logger.info(f"Deleted {deleted_count} input documents from MongoDB for document_id: {document_id}")
            except Exception as e:
                error_msg = f"Failed to delete MongoDB input documents: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            # 2. Remove input files from local storage
            try:
                supported_extensions = ['*.pdf', '*.docx', '*.txt']
                for ext in supported_extensions:
                    input_files = list(UPLOADS_DIR.glob(f"{document_id}_{ext}"))
                    for file_path in input_files:
                        try:
                            file_path.unlink()  # Delete the file
                            cleanup_results['local_input_files_deleted'].append(str(file_path))
                            current_app.logger.info(f"Deleted local input file: {file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete local file {file_path}: {str(e)}"
                            cleanup_results['errors'].append(error_msg)
                            current_app.logger.error(error_msg)
                            
                # Also remove any converted temporary files
                temp_files = list(UPLOADS_DIR.glob(f"{document_id}_converted.pdf"))
                for file_path in temp_files:
                    try:
                        file_path.unlink()
                        cleanup_results['local_input_files_deleted'].append(str(file_path))
                        current_app.logger.info(f"Deleted temporary converted file: {file_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete temp file {file_path}: {str(e)}"
                        cleanup_results['errors'].append(error_msg)
                        current_app.logger.error(error_msg)
                        
            except Exception as e:
                error_msg = f"Error during local file cleanup: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            # 3. Remove config files from local storage
            try:
                config_patterns = [
                    f"{document_id}_pii_config.txt",
                    f"{document_id}_pii_config_detection_report.txt"
                ]
                
                for pattern in config_patterns:
                    config_files = list(CONFIGS_DIR.glob(pattern))
                    for file_path in config_files:
                        try:
                            file_path.unlink()
                            cleanup_results['config_files_deleted'].append(str(file_path))
                            current_app.logger.info(f"Deleted config file: {file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete config file {file_path}: {str(e)}"
                            cleanup_results['errors'].append(error_msg)
                            current_app.logger.error(error_msg)
                            
            except Exception as e:
                error_msg = f"Error during config file cleanup: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            # Log summary
            total_deleted = (cleanup_results['mongodb_input_deleted'] + 
                           len(cleanup_results['local_input_files_deleted']) + 
                           len(cleanup_results['config_files_deleted']))
            
            current_app.logger.info(f"Cleanup summary for {document_id}: "
                                  f"MongoDB: {cleanup_results['mongodb_input_deleted']}, "
                                  f"Local files: {len(cleanup_results['local_input_files_deleted'])}, "
                                  f"Config files: {len(cleanup_results['config_files_deleted'])}, "
                                  f"Errors: {len(cleanup_results['errors'])}")
            
            return cleanup_results
            
        except Exception as e:
            raise ValueError(f"Cleanup failed: {str(e)}")

    def force_cleanup_all_processing_data(self, document_id: str) -> Dict[str, Any]:
        """
        Force cleanup of ALL data related to a document (including masked data).
        This is for complete removal when needed.
        
        Args:
            document_id: Document ID to completely clean up
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            cleanup_results = {
                'document_id': document_id,
                'mongodb_all_deleted': 0,
                'local_files_deleted': [],
                'config_files_deleted': [],
                'results_deleted': [],
                'errors': []
            }
            
            # 1. Remove ALL documents from MongoDB (both uploaded and masked)
            try:
                deleted_count = mongo_db.delete_documents_by_document_id(document_id)  # No status filter
                cleanup_results['mongodb_all_deleted'] = deleted_count
                current_app.logger.info(f"Deleted {deleted_count} documents from MongoDB for document_id: {document_id}")
            except Exception as e:
                error_msg = f"Failed to delete MongoDB documents: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            # 2. Remove all local files
            try:
                # Input files
                supported_extensions = ['*.pdf', '*.docx', '*.txt']
                for ext in supported_extensions:
                    files = list(UPLOADS_DIR.glob(f"{document_id}_{ext}"))
                    for file_path in files:
                        try:
                            file_path.unlink()
                            cleanup_results['local_files_deleted'].append(str(file_path))
                            current_app.logger.info(f"Deleted local file: {file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete file {file_path}: {str(e)}"
                            cleanup_results['errors'].append(error_msg)
                            current_app.logger.error(error_msg)
                
                # Temp files
                temp_files = list(UPLOADS_DIR.glob(f"{document_id}_converted.pdf"))
                for file_path in temp_files:
                    try:
                        file_path.unlink()
                        cleanup_results['local_files_deleted'].append(str(file_path))
                        current_app.logger.info(f"Deleted temp file: {file_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete temp file {file_path}: {str(e)}"
                        cleanup_results['errors'].append(error_msg)
                        current_app.logger.error(error_msg)
                        
            except Exception as e:
                error_msg = f"Error during local file cleanup: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            # 3. Remove config files
            try:
                config_patterns = [
                    f"{document_id}_pii_config.txt",
                    f"{document_id}_pii_config_detection_report.txt"
                ]
                
                for pattern in config_patterns:
                    config_files = list(CONFIGS_DIR.glob(pattern))
                    for file_path in config_files:
                        try:
                            file_path.unlink()
                            cleanup_results['config_files_deleted'].append(str(file_path))
                            current_app.logger.info(f"Deleted config file: {file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete config file {file_path}: {str(e)}"
                            cleanup_results['errors'].append(error_msg)
                            current_app.logger.error(error_msg)
                            
            except Exception as e:
                error_msg = f"Error during config file cleanup: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            # 4. Remove result files
            try:
                result_patterns = [
                    f"{document_id}_masked.pdf",
                    f"{document_id}_masked_masking_report.txt"
                ]
                
                for pattern in result_patterns:
                    result_files = list(RESULTS_DIR.glob(pattern))
                    for file_path in result_files:
                        try:
                            file_path.unlink()
                            cleanup_results['results_deleted'].append(str(file_path))
                            current_app.logger.info(f"Deleted result file: {file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete result file {file_path}: {str(e)}"
                            cleanup_results['errors'].append(error_msg)
                            current_app.logger.error(error_msg)
                            
            except Exception as e:
                error_msg = f"Error during result file cleanup: {str(e)}"
                cleanup_results['errors'].append(error_msg)
                current_app.logger.error(error_msg)
            
            return cleanup_results
            
        except Exception as e:
            raise ValueError(f"Force cleanup failed: {str(e)}")


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
            'masking_completed': False,
            'mongo_files': {}
        }
        
        # Check if uploaded
        supported_extensions = ['*.pdf', '*.docx', '*.txt']
        uploaded_files = []
        for ext in supported_extensions:
            uploaded_files.extend(list(UPLOADS_DIR.glob(f"{document_id}_{ext}")))
        
        if uploaded_files:
            status['uploaded'] = True
        
        # Check if config exists
        config_path = CONFIGS_DIR / f"{document_id}_pii_config.txt"
        if config_path.exists():
            status['config_generated'] = True
        
        # Check if masked file exists
        masked_path = RESULTS_DIR / f"{document_id}_masked.pdf"
        if masked_path.exists():
            status['masking_completed'] = True
        
        # Get MongoDB file information
        try:
            mongo_info = processor.get_document_info_from_mongo(document_id)
            status['mongo_files'] = {
                'total': mongo_info['total_files'],
                'files': mongo_info['files']
            }
            
            # Check if we have both original and masked files in MongoDB
            uploaded_files = [f for f in mongo_info['files'] if f.get('status') == 'uploaded']
            masked_files = [f for f in mongo_info['files'] if f.get('status') == 'masked']
            
            status['mongo_files']['uploaded_count'] = len(uploaded_files)
            status['mongo_files']['masked_count'] = len(masked_files)
            status['mongo_files']['has_original'] = len(uploaded_files) > 0
            status['mongo_files']['has_masked'] = len(masked_files) > 0
            
        except Exception as e:
            current_app.logger.warning(f"Failed to get MongoDB info: {e}")
            status['mongo_files'] = {'error': str(e)}
        
        return success_response(status)
        
    except Exception as e:
        current_app.logger.error(f"Status check error: {str(e)}")
        return error_response('Status check failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/preview/<document_id>', methods=['GET'])
def preview_original_document(document_id: str):
    """Serve the original document for preview."""
    try:
        # Find the uploaded file - support multiple extensions
        supported_extensions = ['*.pdf', '*.docx', '*.txt']
        uploaded_files = []
        for ext in supported_extensions:
            uploaded_files.extend(list(UPLOADS_DIR.glob(f"{document_id}_{ext}")))
        
        if not uploaded_files:
            return error_response('Document not found', 'NOT_FOUND'), 404
        
        document_path = uploaded_files[0]
        
        # Determine MIME type based on extension
        file_extension = document_path.suffix.lower()
        mime_type_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain'
        }
        mime_type = mime_type_map.get(file_extension, 'application/octet-stream')
        
        response = send_file(
            document_path, 
            mimetype=mime_type,
            as_attachment=False,
            download_name=document_path.name
        )
        
        # Allow iframe embedding for document preview (mainly for PDFs)
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


@simple_processing_bp.route('/debug-mongo', methods=['GET'])
def debug_mongo_contents():
    """Debug endpoint to see all documents in MongoDB."""
    try:
        # Get all files from MongoDB
        all_files = mongo_db.get_files({})  # Empty query to get all files
        
        return success_response({
            'total_files': len(all_files),
            'files': all_files
        })
        
    except Exception as e:
        current_app.logger.error(f"Debug mongo error: {str(e)}")
        return error_response('Debug failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/mongo-info/<document_id>', methods=['GET'])
def get_mongo_document_info(document_id: str):
    """Get document information from MongoDB."""
    try:
        status_filter = request.args.get('status')  # Optional status filter
        result = processor.get_document_info_from_mongo(document_id, status_filter)
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'MONGO_ERROR')
    except Exception as e:
        current_app.logger.error(f"MongoDB info error: {str(e)}")
        return error_response('Failed to get MongoDB info', 'INTERNAL_ERROR')


@simple_processing_bp.route('/download-from-mongo/<document_id>', methods=['GET'])
def download_from_mongo(document_id: str):
    """Download a file from MongoDB by document_id and status."""
    try:
        status = request.args.get('status', 'masked')  # Default to masked files
        
        current_app.logger.info(f"Attempting to download from MongoDB: document_id={document_id}, status={status}")
        
        # Since the existing MongoDB documents might not have document_id in metadata,
        # let's try to find files by status first and then filter by any available identifier
        files = mongo_db.get_files({'status': status})
        current_app.logger.info(f"Found {len(files)} files with status '{status}'")
        
        # If no files with status, try to get all files and filter
        if not files:
            all_files = mongo_db.get_files({})
            current_app.logger.info(f"Found {len(all_files)} total files in MongoDB")
            
            # Log the structure of files for debugging
            if all_files:
                sample_file = all_files[0]
                current_app.logger.info(f"Sample file structure: {list(sample_file.keys())}")
                if 'metadata' in sample_file:
                    current_app.logger.info(f"Sample metadata keys: {list(sample_file['metadata'].keys())}")
            
            return error_response(f'No {status} files found in MongoDB', 'FILE_NOT_FOUND')
        
        # For now, just return the first file with the matching status
        # In a real implementation, you'd want to match the document_id properly
        file_info = files[0]
        current_app.logger.info(f"Selected file: {file_info.get('original_name', 'unknown')}")
        
        # Retrieve file data from MongoDB
        file_data = mongo_db.get_file_data(file_info['_id'])
        
        if not file_data:
            return error_response('Failed to retrieve file data from MongoDB', 'RETRIEVAL_ERROR')
        
        # Create a temporary file response
        from io import BytesIO
        file_stream = BytesIO(file_data)
        
        return send_file(
            file_stream,
            as_attachment=True,
            download_name=file_info.get('original_name', f'{document_id}_{status}.pdf'),
            mimetype=file_info.get('mime_type', 'application/pdf')
        )
        
    except Exception as e:
        current_app.logger.error(f"MongoDB download error: {str(e)}")
        return error_response('MongoDB download failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/debug/mongo-all', methods=['GET'])
def debug_mongo_all():
    """Debug endpoint to see all documents in MongoDB."""
    try:
        # Get all files from MongoDB
        all_files = mongo_db.get_files({})
        
        # Format the response for better readability
        formatted_files = []
        for file_doc in all_files:
            formatted_files.append({
                'id': str(file_doc.get('_id')),
                'original_name': file_doc.get('original_name'),
                'status': file_doc.get('status'),
                'file_size': file_doc.get('file_size'),
                'upload_date': file_doc.get('upload_date'),
                'metadata': file_doc.get('metadata', {}),
                'user_id': file_doc.get('user_id')
            })
        
        return success_response({
            'total_files': len(formatted_files),
            'files': formatted_files
        })
        
    except Exception as e:
        current_app.logger.error(f"Debug MongoDB error: {str(e)}")
        return error_response('Debug failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/cleanup/<document_id>', methods=['POST'])
def cleanup_document_data(document_id: str):
    """
    Clean up input data and config files after masking is complete.
    Removes input documents from MongoDB and local storage, keeps masked data.
    """
    try:
        result = processor.cleanup_processing_data(document_id)
        
        # Check if there were any errors
        if result['errors']:
            current_app.logger.warning(f"Cleanup completed with errors for {document_id}: {result['errors']}")
            return success_response(result, message="Cleanup completed with some errors")
        else:
            return success_response(result, message="Cleanup completed successfully")
        
    except ValueError as e:
        return error_response(str(e), 'CLEANUP_ERROR')
    except Exception as e:
        current_app.logger.error(f"Cleanup error: {str(e)}")
        return error_response('Cleanup failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/cleanup/<document_id>/force', methods=['POST'])
def force_cleanup_document_data(document_id: str):
    """
    Force cleanup of ALL data related to a document (including masked data).
    This removes everything - use with caution.
    """
    try:
        result = processor.force_cleanup_all_processing_data(document_id)
        
        # Check if there were any errors
        if result['errors']:
            current_app.logger.warning(f"Force cleanup completed with errors for {document_id}: {result['errors']}")
            return success_response(result, message="Force cleanup completed with some errors")
        else:
            return success_response(result, message="Force cleanup completed successfully")
        
    except ValueError as e:
        return error_response(str(e), 'CLEANUP_ERROR')
    except Exception as e:
        current_app.logger.error(f"Force cleanup error: {str(e)}")
        return error_response('Force cleanup failed', 'INTERNAL_ERROR')


# ============================================================================
# SIMPLIFIED API ENDPOINTS FOR EXTERNAL USE
# ============================================================================

@simple_processing_bp.route('/process-document', methods=['POST'])
def process_document_complete():
    """
    Simplified API endpoint that handles the complete PII detection and masking pipeline.
    
    This endpoint combines all the steps into one seamless process:
    1. Upload document
    2. Generate PII detection configuration with suggested strategies
    3. Apply masking using suggested strategies
    4. Return the masked document
    
    Supports: PDF, DOCX, TXT files
    
    Request:
        - Multipart form data with 'document' file
        
    Response:
        - Success: Returns the masked document as a file download
        - Error: JSON with error details
    
    Usage Example:
        curl -X POST http://localhost:5000/api/v1/simple/process-document \
             -F "document=@your_document.pdf" \
             -o masked_document.pdf
    """
    try:
        # Validate request
        if 'document' not in request.files:
            return error_response('No document file provided', 'MISSING_FILE')
        
        file = request.files['document']
        if file.filename == '':
            return error_response('No file selected', 'NO_FILE_SELECTED')
        
        current_app.logger.info(f"Starting complete document processing for: {file.filename}")
        
        # Step 1: Upload document
        current_app.logger.info("Step 1: Uploading document...")
        upload_result = processor.upload_document(file)
        document_id = upload_result['document_id']
        
        current_app.logger.info(f"Document uploaded with ID: {document_id}")
        
        try:
            # Step 2: Generate PII detection config with suggested strategies
            current_app.logger.info("Step 2: Generating PII detection configuration...")
            config_result = processor.generate_pii_config(document_id)
            
            current_app.logger.info(f"PII detection completed. Found {config_result['total_pii']} PII entities")
            
            # Step 3: Apply masking using suggested strategies (no manual intervention)
            current_app.logger.info("Step 3: Applying PII masking with suggested strategies...")
            masking_result = processor.apply_masking(document_id)
            
            current_app.logger.info("PII masking completed successfully")
            
            # Step 4: Return the masked document
            current_app.logger.info("Step 4: Preparing masked document for download...")
            
            # Find the masked document
            supported_extensions = ['*.pdf', '*.docx', '*.txt']
            masked_files = []
            for ext in supported_extensions:
                masked_files.extend(list(RESULTS_DIR.glob(f"{document_id}_masked.{ext.replace('*.', '')}")))
            
            if not masked_files:
                raise ValueError("Masked document not found")
            
            masked_file = masked_files[0]
            original_filename = upload_result.get('filename', 'document')
            
            # Create a meaningful filename for the masked document
            name_parts = original_filename.rsplit('.', 1)
            if len(name_parts) == 2:
                masked_filename = f"{name_parts[0]}_masked.{name_parts[1]}"
            else:
                masked_filename = f"{original_filename}_masked.pdf"
            
            # Prepare response with metadata
            response_headers = {
                'X-Document-ID': document_id,
                'X-PII-Count': str(config_result['total_pii']),
                'X-Processing-Status': 'completed',
                'X-Original-Filename': original_filename
            }
            
            # Create the file response
            response = send_file(
                masked_file,
                as_attachment=True,
                download_name=masked_filename,
                mimetype='application/octet-stream'
            )
            
            # Add custom headers
            for header, value in response_headers.items():
                response.headers[header] = value
            
            # Automatically cleanup intermediate files after successful processing
            try:
                # Keep only the final masked document, clean up intermediate files
                current_app.logger.info(f"Auto-cleanup: Removing intermediate files for document {document_id}")
                # Clean up uploads and configs, but keep the result
                upload_files = list(UPLOADS_DIR.glob(f"{document_id}_*"))
                config_files = list(CONFIGS_DIR.glob(f"{document_id}_*"))
                
                for file_to_remove in upload_files + config_files:
                    try:
                        file_to_remove.unlink()
                        current_app.logger.debug(f"Removed intermediate file: {file_to_remove}")
                    except Exception as e:
                        current_app.logger.warning(f"Failed to remove {file_to_remove}: {e}")
                        
            except Exception as cleanup_error:
                current_app.logger.warning(f"Auto-cleanup warning for {document_id}: {cleanup_error}")
            
            current_app.logger.info(f"Complete document processing finished successfully for document {document_id}")
            return response
            
        except Exception as processing_error:
            # If any step fails, clean up the uploaded document
            current_app.logger.error(f"Processing failed for document {document_id}: {processing_error}")
            try:
                processor.cleanup_processing_data(document_id)
            except:
                pass  # Ignore cleanup errors during error handling
            raise processing_error
            
    except ValueError as e:
        return error_response(str(e), 'PROCESSING_ERROR')
    except Exception as e:
        current_app.logger.error(f"Complete document processing error: {str(e)}")
        return error_response('Document processing failed', 'INTERNAL_ERROR')

