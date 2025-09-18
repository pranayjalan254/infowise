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
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def upload_multiple_documents(self, files: List[FileStorage]) -> Dict[str, Any]:
        """
        Upload multiple documents and store them locally and in MongoDB.
        
        Args:
            files: List of uploaded file objects
            
        Returns:
            Dictionary with bulk upload results
        """
        try:
            if not files or len(files) == 0:
                raise ValueError("No files provided")
            
            uploaded_documents = []
            failed_uploads = []
            
            for file in files:
                try:
                    result = self.upload_document(file)
                    uploaded_documents.append(result)
                    current_app.logger.info(f"Successfully uploaded: {result['filename']}")
                except Exception as e:
                    failed_uploads.append({
                        'filename': file.filename if file and file.filename else 'unknown',
                        'error': str(e)
                    })
                    current_app.logger.error(f"Failed to upload {file.filename if file and file.filename else 'unknown'}: {str(e)}")
            
            return {
                'uploaded_documents': uploaded_documents,
                'failed_uploads': failed_uploads,
                'total_files': len(files),
                'successful_uploads': len(uploaded_documents),
                'failed_count': len(failed_uploads),
                'upload_date': get_current_timestamp(),
                'status': 'completed' if len(failed_uploads) == 0 else 'partial_success'
            }
            
        except Exception as e:
            raise ValueError(f"Bulk upload failed: {str(e)}")
    
    def process_scanned_pdf_with_ocr(self, document_id: str) -> Dict[str, Any]:
        """
        Process a scanned PDF through OCR to create a text file.
        
        Args:
            document_id: Document ID from upload
            
        Returns:
            Dictionary with OCR processing results
        """
        try:
            # Find the uploaded PDF file
            uploaded_files = list(UPLOADS_DIR.glob(f"{document_id}_*.pdf"))
            
            if not uploaded_files:
                raise ValueError(f"PDF file not found for document_id: {document_id}")
            
            original_pdf_path = uploaded_files[0]
            
            # Create OCR output path (text file)
            ocr_filename = f"{document_id}_ocr_extracted.txt"
            ocr_output_path = UPLOADS_DIR / ocr_filename
            
            current_app.logger.info(f"Processing scanned PDF with OCR: {original_pdf_path} -> {ocr_output_path}")
            
            # Import and use the OCR processor from scripts directory
            from scripts.ocr import process_pdf
            
            # Process PDF with OCR to generate text file
            success = process_pdf(str(original_pdf_path), str(ocr_output_path))
            
            if not success or not ocr_output_path.exists():
                raise ValueError("OCR processing failed - no output file generated")
            
            current_app.logger.info(f"OCR text extraction completed: {ocr_output_path}")
            
            # Backup original scanned PDF
            backup_filename = f"{document_id}_original_scanned.pdf"
            backup_path = UPLOADS_DIR / backup_filename
            original_pdf_path.rename(backup_path)
            current_app.logger.info(f"Original scanned PDF backed up as: {backup_path}")
            
            # Store OCR text file in MongoDB
            try:
                with open(ocr_output_path, 'r', encoding='utf-8') as f:
                    text_data = f.read()
                
                # Store as binary data for consistency with other files
                text_bytes = text_data.encode('utf-8')
                
                mongo_doc_id = mongo_db.store_file(
                    file_data=text_bytes,
                    file_info={
                        'original_name': ocr_filename,
                        'file_size': len(text_bytes),
                        'status': 'ocr_processed',
                        'file_type': '.txt',
                        'mime_type': 'text/plain',
                        'user_id': 'a6b781b1-401b-435b-aaec-8821a38cf731',
                        'upload_date': get_current_timestamp(),
                        'metadata': {
                            'local_path': str(ocr_output_path),
                            'document_id': document_id,
                            'processing_type': 'ocr_extracted_text',
                            'original_scanned_backup': str(backup_path)
                        }
                    }
                )
                current_app.logger.info(f"OCR text file stored in MongoDB with ID: {mongo_doc_id}")
            except Exception as e:
                current_app.logger.error(f"MongoDB storage of OCR text failed: {e}")
                mongo_doc_id = None
            
            return {
                'document_id': document_id,
                'ocr_output_path': str(ocr_output_path),
                'original_backup_path': str(backup_path),
                'mongo_id': mongo_doc_id,
                'status': 'ocr_completed',
                'output_type': 'text_file',
                'processing_date': get_current_timestamp()
            }
            
        except Exception as e:
            raise ValueError(f"OCR processing failed: {str(e)}")

    def generate_pii_config(self, document_id: str) -> Dict[str, Any]:
        """
        Generate PII configuration using pii_detector_config_generator.py
        This method now includes automatic scanned PDF detection and OCR processing.
        
        Args:
            document_id: Document ID from upload
            
        Returns:
            Dictionary with config generation results
        """
        try:
            # Find the uploaded file - support multiple extensions
            # Look for files that start with document_id_ (original naming pattern)
            uploaded_files = list(UPLOADS_DIR.glob(f"{document_id}_*"))
            
            # Filter to only include supported file types
            supported_extensions = ['.pdf', '.docx', '.txt']
            uploaded_files = [f for f in uploaded_files if f.suffix.lower() in supported_extensions]
            
            if not uploaded_files:
                raise ValueError(f"Document file not found for document_id: {document_id}")
            
            document_path = uploaded_files[0]
            
            # Check if PDF is scanned and needs OCR processing
            ocr_processed = False
            if document_path.suffix.lower() == '.pdf':
                current_app.logger.info(f"Checking if PDF is scanned: {document_path}")
                
                # Import and use the PDF scan detector  
                from scripts.pdf_scan_detector import PDFScanDetector
                detector = PDFScanDetector()
                
                # Analyze PDF to determine if it's scanned
                analysis = detector.analyze_pdf(str(document_path))
                
                current_app.logger.info(f"PDF scan analysis: {analysis['analysis_details']}")
                
                if analysis['is_scanned']:
                    current_app.logger.info(f"PDF detected as SCANNED (confidence: {analysis['confidence']:.1%}). Processing with OCR...")
                    
                    # Process with OCR to generate text file
                    ocr_result = self.process_scanned_pdf_with_ocr(document_id)
                    current_app.logger.info(f"OCR processing completed: {ocr_result['status']}")
                    
                    # Update document_path to use OCR generated text file
                    document_path = Path(ocr_result['ocr_output_path'])
                    ocr_processed = True
                else:
                    current_app.logger.info(f"PDF detected as TEXT-BASED (confidence: {analysis['confidence']:.1%}). Proceeding with normal processing...")
            
            # Generate config file path
            config_filename = f"{document_id}_pii_config.txt"
            config_path = CONFIGS_DIR / config_filename
            
            # Run pii_detector_config_generator.py
            current_app.logger.info(f"Running PII detection on: {document_path}")
            
            # Use absolute path to ensure the file is found correctly
            absolute_document_path = document_path.resolve()
            absolute_config_path = config_path.resolve()
            
            current_app.logger.info(f"Absolute document path: {absolute_document_path}")
            current_app.logger.info(f"Document exists: {absolute_document_path.exists()}")
            
            result = subprocess.run([
                'python', 'scripts/pii_detector_config_generator.py',
                str(absolute_document_path),
                str(absolute_config_path)
            ], capture_output=True, text=True, cwd=current_app.root_path)
            
            if result.returncode != 0:
                raise ValueError(f"PII detection failed: {result.stderr}")
            
            current_app.logger.info(f"PII detection completed: {result.stdout}")
            
            # Read and parse the generated config
            if not config_path.exists():
                raise ValueError("Config file was not generated")
            
            config_data = self._parse_config_file(config_path)
            
            # Include OCR processing info in response
            response_data = {
                'document_id': document_id,
                'config_path': str(config_path),
                'config_data': config_data,
                'total_pii': len(config_data),
                'status': 'config_generated'
            }
            
            # Add OCR processing information if it was performed
            if ocr_processed:
                response_data['ocr_processed'] = True
                response_data['processing_note'] = 'Document was detected as scanned and processed through OCR to extract text before PII detection'
                response_data['processing_type'] = 'ocr_to_text'
            else:
                response_data['ocr_processed'] = False
                response_data['processing_note'] = 'Document processed directly for PII detection (text-based PDF or non-PDF format)'
                response_data['processing_type'] = 'direct'
            
            return response_data
            
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
            # Find input document - look for files that start with document_id_
            input_files = list(UPLOADS_DIR.glob(f"{document_id}_*"))
            
            # Filter to only include supported file types
            supported_extensions = ['.pdf', '.docx', '.txt']
            input_files = [f for f in input_files if f.suffix.lower() in supported_extensions]
            
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
            
            # Use absolute paths to ensure files are found correctly
            absolute_masking_input = Path(masking_input).resolve()
            absolute_output_path = output_path.resolve()
            absolute_config_path = config_path.resolve()
            
            current_app.logger.info(f"Absolute masking input: {absolute_masking_input}")
            current_app.logger.info(f"Input exists: {absolute_masking_input.exists()}")
            
            result = subprocess.run([
                'python', 'scripts/bert_pii_masker.py',
                str(absolute_masking_input),
                str(absolute_output_path),
                str(absolute_config_path)
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

    def generate_pii_config_bulk(self, document_ids: List[str]) -> Dict[str, Any]:
        """
        Generate PII configuration for multiple documents using parallel processing.
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            Dictionary with bulk config generation results
        """
        try:
            successful_configs = []
            failed_configs = []
            
            # Capture current Flask app context for worker threads
            app = current_app._get_current_object()
            
            def generate_config_with_context(document_id: str):
                """Wrapper function that preserves Flask app context."""
                with app.app_context():
                    return self.generate_pii_config(document_id)
            
            # Use ThreadPoolExecutor for parallel PII detection
            max_workers = min(len(document_ids), 5)  # Limit concurrent workers to prevent overload
            current_app.logger.info(f"Starting parallel PII detection for {len(document_ids)} documents using {max_workers} workers")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all detection tasks with app context preservation
                future_to_document_id = {
                    executor.submit(generate_config_with_context, document_id): document_id 
                    for document_id in document_ids
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_document_id):
                    document_id = future_to_document_id[future]
                    try:
                        result = future.result()
                        successful_configs.append({
                            'document_id': document_id,
                            'config_data': result['config_data'],
                            'total_pii': result['total_pii'],
                            'status': 'config_generated'
                        })
                        current_app.logger.info(f"Generated config for document: {document_id}")
                    except Exception as e:
                        failed_configs.append({
                            'document_id': document_id,
                            'error': str(e)
                        })
                        current_app.logger.error(f"Failed to generate config for {document_id}: {str(e)}")
            
            current_app.logger.info(f"Parallel PII detection completed: {len(successful_configs)} successful, {len(failed_configs)} failed")
            
            return {
                'successful_configs': successful_configs,
                'failed_configs': failed_configs,
                'total_documents': len(document_ids),
                'successful_count': len(successful_configs),
                'failed_count': len(failed_configs),
                'status': 'completed' if len(failed_configs) == 0 else 'partial_success'
            }
            
        except Exception as e:
            raise ValueError(f"Bulk config generation failed: {str(e)}")

    def apply_masking_bulk(self, document_ids: List[str]) -> Dict[str, Any]:
        """
        Apply PII masking to multiple documents using parallel processing.
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            Dictionary with bulk masking results
        """
        try:
            successful_maskings = []
            failed_maskings = []
            
            # Capture current Flask app context for worker threads
            app = current_app._get_current_object()
            
            def apply_masking_with_context(document_id: str):
                """Wrapper function that preserves Flask app context."""
                with app.app_context():
                    return self.apply_masking(document_id)
            
            # Use ThreadPoolExecutor for parallel PII masking
            max_workers = min(len(document_ids), 4)  # Limit concurrent workers for masking (more resource intensive)
            current_app.logger.info(f"Starting parallel PII masking for {len(document_ids)} documents using {max_workers} workers")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all masking tasks with app context preservation
                future_to_document_id = {
                    executor.submit(apply_masking_with_context, document_id): document_id 
                    for document_id in document_ids
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_document_id):
                    document_id = future_to_document_id[future]
                    try:
                        result = future.result()
                        successful_maskings.append({
                            'document_id': document_id,
                            'masked_document_id': result['masked_document_id'],
                            'output_filename': result['output_filename'],
                            'file_size': result['file_size'],
                            'status': 'masking_completed'
                        })
                        current_app.logger.info(f"Applied masking for document: {document_id}")
                    except Exception as e:
                        failed_maskings.append({
                            'document_id': document_id,
                            'error': str(e)
                        })
                        current_app.logger.error(f"Failed to apply masking for {document_id}: {str(e)}")
            
            current_app.logger.info(f"Parallel PII masking completed: {len(successful_maskings)} successful, {len(failed_maskings)} failed")
            
            return {
                'successful_maskings': successful_maskings,
                'failed_maskings': failed_maskings,
                'total_documents': len(document_ids),
                'successful_count': len(successful_maskings),
                'failed_count': len(failed_maskings),
                'status': 'completed' if len(failed_maskings) == 0 else 'partial_success'
            }
            
        except Exception as e:
            raise ValueError(f"Bulk masking failed: {str(e)}")


# Initialize processor
processor = SimpleDocumentProcessor()


# API Endpoints

@simple_processing_bp.route('/upload', methods=['POST'])
def upload_documents():
    """Upload documents (single or multiple files)."""
    try:
        files = []
        
        # Handle both 'file' (single) and 'files' (multiple) fields
        if 'files' in request.files:
            files = request.files.getlist('files')
        elif 'file' in request.files:
            files = [request.files['file']]
        else:
            return error_response('No file provided', 'FILE_REQUIRED')
        
        if not files or len(files) == 0:
            return error_response('No files provided', 'FILES_REQUIRED')
        
        # Always use the bulk upload method (works for single files too)
        result = processor.upload_multiple_documents(files)
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'UPLOAD_ERROR')
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return error_response('Upload failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/generate-config', methods=['POST'])
def generate_config():
    """Generate PII configuration for documents (single or multiple)."""
    try:
        data = request.get_json()
        if not data or 'document_ids' not in data:
            return error_response('Document IDs required', 'DATA_REQUIRED')
        
        document_ids = data['document_ids']
        if not isinstance(document_ids, list):
            # Convert single document_id to list for consistency
            document_ids = [document_ids]
        
        if len(document_ids) == 0:
            return error_response('Valid document IDs required', 'INVALID_DATA')
        
        # Always use bulk processing (works for single documents too)
        result = processor.generate_pii_config_bulk(document_ids)
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


@simple_processing_bp.route('/apply-masking', methods=['POST'])
def apply_masking():
    """Apply PII masking to documents (single or multiple)."""
    try:
        data = request.get_json()
        if not data or 'document_ids' not in data:
            return error_response('Document IDs required', 'DATA_REQUIRED')
        
        document_ids = data['document_ids']
        if not isinstance(document_ids, list):
            # Convert single document_id to list for consistency
            document_ids = [document_ids]
        
        if len(document_ids) == 0:
            return error_response('Valid document IDs required', 'INVALID_DATA')
        
        # Always use bulk processing (works for single documents too)
        result = processor.apply_masking_bulk(document_ids)
        return success_response(result)
        
    except ValueError as e:
        return error_response(str(e), 'MASKING_ERROR')
    except Exception as e:
        current_app.logger.error(f"Masking error: {str(e)}")
        return error_response('Masking failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/generate-config/bulk', methods=['POST'])
def generate_config_bulk():
    """Generate PII configuration for multiple documents (legacy endpoint - redirects to unified endpoint)."""
    return generate_config()


@simple_processing_bp.route('/apply-masking/bulk', methods=['POST'])
def apply_masking_bulk():
    """Apply PII masking to multiple documents (legacy endpoint - redirects to unified endpoint)."""
    return apply_masking()


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

@simple_processing_bp.route('/process-documents', methods=['POST'])
def process_documents():
    """
    Unified API endpoint that handles complete PII detection and masking pipeline for single or multiple documents.
    
    This endpoint combines all the steps into one seamless process:
    1. Upload documents (single or multiple)
    2. Generate PII detection configurations with suggested strategies (parallel processing)
    3. Apply masking using suggested strategies (parallel processing)
    4. Return processing summary with download links
    
    Supports: PDF, DOCX, TXT files
    
    Request:
        - Multipart form data with 'documents' files (single file or array)
        - Also supports 'document' for backward compatibility
        
    Response:
        - JSON response with processing summary and download information
    
    Usage Examples:
        # Single document
        curl -X POST http://localhost:5000/api/v1/simple/process-documents \
             -F "document=@your_document.pdf"
             
        # Multiple documents
        curl -X POST http://localhost:5000/api/v1/simple/process-documents \
             -F "documents=@document1.pdf" \
             -F "documents=@document2.docx" \
             -F "documents=@document3.txt"
    """
    try:
        # Handle both single and multiple file uploads
        files = []
        
        if 'documents' in request.files:
            files = request.files.getlist('documents')
        elif 'document' in request.files:
            files = [request.files['document']]
        else:
            return error_response('No document files provided', 'MISSING_FILES')
        
        if not files or len(files) == 0:
            return error_response('No files selected', 'NO_FILES_SELECTED')
        
        current_app.logger.info(f"Starting document processing for {len(files)} file(s)")
        
        # Step 1: Upload all documents
        current_app.logger.info("Step 1: Uploading documents...")
        upload_result = processor.upload_multiple_documents(files)
        
        if upload_result['successful_uploads'] == 0:
            return error_response('All document uploads failed', 'ALL_UPLOADS_FAILED')
        
        # Get document IDs from successful uploads
        document_ids = [doc['document_id'] for doc in upload_result['uploaded_documents']]
        current_app.logger.info(f"Documents uploaded successfully: {len(document_ids)} file(s)")
        
        try:
            # Step 2: Generate PII detection configs with parallel processing
            current_app.logger.info("Step 2: Generating PII detection configurations...")
            config_result = processor.generate_pii_config_bulk(document_ids)
            
            if config_result['successful_count'] == 0:
                raise ValueError("All PII detection configurations failed")
            
            # Get document IDs that successfully generated configs
            successful_config_document_ids = [config['document_id'] for config in config_result['successful_configs']]
            current_app.logger.info(f"PII detection completed for {len(successful_config_document_ids)} document(s)")
            
            # Step 3: Apply masking with parallel processing
            current_app.logger.info("Step 3: Applying PII masking...")
            masking_result = processor.apply_masking_bulk(successful_config_document_ids)
            
            current_app.logger.info(f"PII masking completed for {masking_result['successful_count']} document(s)")
            
            # Step 4: Prepare response with processing summary
            current_app.logger.info("Step 4: Preparing processing summary...")
            
            # Create detailed processing summary
            processing_summary = {
                'total_files_submitted': len(files),
                'upload_summary': {
                    'successful_uploads': upload_result['successful_uploads'],
                    'failed_uploads': upload_result['failed_count'],
                    'upload_failures': upload_result['failed_uploads']
                },
                'detection_summary': {
                    'successful_detections': config_result['successful_count'],
                    'failed_detections': config_result['failed_count'],
                    'detection_failures': config_result['failed_configs']
                },
                'masking_summary': {
                    'successful_maskings': masking_result['successful_count'],
                    'failed_maskings': masking_result['failed_count'],
                    'masking_failures': masking_result['failed_maskings']
                },
                'processed_documents': [],
                'download_links': {}
            }
            
            # Add information about successfully processed documents
            for masking in masking_result['successful_maskings']:
                document_id = masking['document_id']
                
                # Find the corresponding upload and config info
                upload_info = next((doc for doc in upload_result['uploaded_documents'] if doc['document_id'] == document_id), None)
                config_info = next((config for config in config_result['successful_configs'] if config['document_id'] == document_id), None)
                
                if upload_info and config_info:
                    processed_doc = {
                        'document_id': document_id,
                        'original_filename': upload_info['filename'],
                        'file_size': upload_info['size'],
                        'pii_count': config_info['total_pii'],
                        'masked_filename': masking['output_filename'],
                        'masked_file_size': masking['file_size'],
                        'status': 'completed'
                    }
                    processing_summary['processed_documents'].append(processed_doc)
                    
                    # Add download link
                    processing_summary['download_links'][document_id] = {
                        'masked_document': f"/api/v1/simple/download/{document_id}",
                        'preview_original': f"/api/v1/simple/preview/{document_id}",
                        'preview_masked': f"/api/v1/simple/preview-masked/{document_id}"
                    }
            
            # Automatically cleanup intermediate files for successfully processed documents
            try:
                current_app.logger.info("Auto-cleanup: Removing intermediate files for processed documents")
                for document_id in [doc['document_id'] for doc in processing_summary['processed_documents']]:
                    # Clean up uploads and configs, but keep the results
                    upload_files = list(UPLOADS_DIR.glob(f"{document_id}_*"))
                    config_files = list(CONFIGS_DIR.glob(f"{document_id}_*"))
                    
                    for file_to_remove in upload_files + config_files:
                        try:
                            file_to_remove.unlink()
                            current_app.logger.debug(f"Removed intermediate file: {file_to_remove}")
                        except Exception as e:
                            current_app.logger.warning(f"Failed to remove {file_to_remove}: {e}")
                            
            except Exception as cleanup_error:
                current_app.logger.warning(f"Auto-cleanup warning: {cleanup_error}")
            
            # Determine overall status
            if masking_result['successful_count'] == len(files):
                overall_status = 'completed'
                message = f'All {len(files)} document(s) processed successfully'
            elif masking_result['successful_count'] > 0:
                overall_status = 'partial_success'
                message = f'Processed {masking_result["successful_count"]} out of {len(files)} document(s)'
            else:
                overall_status = 'failed'
                message = 'No documents were successfully processed'
            
            processing_summary['overall_status'] = overall_status
            processing_summary['message'] = message
            
            # For single document, also include direct file response headers for backward compatibility
            if len(files) == 1 and masking_result['successful_count'] == 1:
                processed_doc = processing_summary['processed_documents'][0]
                processing_summary['single_document_response'] = {
                    'document_id': processed_doc['document_id'],
                    'pii_count': processed_doc['pii_count'],
                    'original_filename': processed_doc['original_filename'],
                    'masked_filename': processed_doc['masked_filename']
                }
            
            current_app.logger.info(f"Document processing completed: {overall_status}")
            return success_response(processing_summary, message=message)
            
        except Exception as processing_error:
            # If any step fails, clean up uploaded documents
            current_app.logger.error(f"Processing failed: {processing_error}")
            try:
                for document_id in document_ids:
                    processor.cleanup_processing_data(document_id)
            except:
                pass  # Ignore cleanup errors during error handling
            raise processing_error
            
    except ValueError as e:
        return error_response(str(e), 'PROCESSING_ERROR')
    except Exception as e:
        current_app.logger.error(f"Document processing error: {str(e)}")
        return error_response('Document processing failed', 'INTERNAL_ERROR')


@simple_processing_bp.route('/analyze-pdf/<document_id>', methods=['GET'])
def analyze_pdf_scan_status(document_id: str):
    """
    Analyze a PDF to determine if it's scanned or text-based.
    
    Args:
        document_id: Document ID from upload
        
    Returns:
        JSON response with PDF analysis results
    """
    try:
        processor = SimpleDocumentProcessor()
        
        # Find the PDF file
        uploaded_files = list(UPLOADS_DIR.glob(f"{document_id}_*.pdf"))
        
        if not uploaded_files:
            return error_response('PDF_NOT_FOUND', f'PDF file not found for document_id: {document_id}', 404)
        
        pdf_path = uploaded_files[0]
        
        # Import and use the PDF scan detector
        from scripts.pdf_scan_detector import PDFScanDetector
        detector = PDFScanDetector()
        
        # Analyze PDF
        analysis = detector.analyze_pdf(str(pdf_path))
        
        response_data = {
            'document_id': document_id,
            'pdf_path': str(pdf_path),
            'analysis': analysis,
            'recommendation': {
                'needs_ocr': analysis['is_scanned'],
                'action': 'Process with OCR before PII detection' if analysis['is_scanned'] else 'Process directly for PII detection'
            }
        }
        
        return success_response(
            data=response_data,
            message=f"PDF analysis completed - {'SCANNED' if analysis['is_scanned'] else 'TEXT-BASED'}"
        )
        
    except Exception as e:
        current_app.logger.error(f"PDF analysis error: {str(e)}")
        return error_response('ANALYSIS_ERROR', f'PDF analysis failed: {str(e)}', 500)


@simple_processing_bp.route('/process-ocr/<document_id>', methods=['POST'])
def process_ocr_manually(document_id: str):
    """
    Manually trigger OCR processing for a scanned PDF.
    
    Args:
        document_id: Document ID from upload
        
    Returns:
        JSON response with OCR processing results
    """
    try:
        processor = SimpleDocumentProcessor()
        
        # Process with OCR
        result = processor.process_scanned_pdf_with_ocr(document_id)
        
        return success_response(
            data=result,
            message="OCR processing completed successfully"
        )
        
    except ValueError as e:
        return error_response('OCR_ERROR', str(e), 400)
    except Exception as e:
        current_app.logger.error(f"OCR processing error: {str(e)}")
        return error_response('PROCESSING_ERROR', f'OCR processing failed: {str(e)}', 500)


# Legacy endpoints for backward compatibility
@simple_processing_bp.route('/process-document', methods=['POST'])
def process_document():
    """Legacy endpoint - redirects to unified process-documents endpoint."""
    return process_documents()


@simple_processing_bp.route('/process-documents-bulk', methods=['POST'])  
def process_documents_bulk():
    """Legacy endpoint - redirects to unified process-documents endpoint."""
    return process_documents()

