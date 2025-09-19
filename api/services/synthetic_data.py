"""
Simple synthetic data generation service.
Clean, minimal implementation that works.
"""

import os
import tempfile
import re
import uuid
from typing import Dict, Any, List
from flask import Blueprint, request, current_app, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from langchain_ollama import ChatOllama
from utils.responses import success_response, error_response
from utils.validation import validate_required_fields
from utils.helpers import get_current_timestamp
from mongodb import get_mongo_db
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import SystemMessage, HumanMessage
import operator
from dotenv import load_dotenv
import fitz  # PyMuPDF
import threading
import time
from bson import ObjectId

# Load environment
load_dotenv()

synthetic_data_bp = Blueprint('synthetic_data', __name__)

# Initialize LLM
llm = ChatOllama(model="phi3:latest")

# Simple State
class SyntheticState(TypedDict):
    original_text: str
    chunks: List[str]
    synthetic_chunks: Annotated[List[str], operator.add]
    final_text: str
    current_dataset: int
    total_datasets: int
    job_id: str

# Extract text from files
def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n\n"
    doc.close()
    return text.strip()

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text from file."""
    if file_type.lower() == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_type.lower() in ['.txt', '.md']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

# Simple chunking
def chunk_text(text: str) -> List[str]:
    """Chunk text into manageable pieces while preserving structure."""
    current_app.logger.info(f"Chunking text of {len(text)} characters")
    
    # Use smaller chunk size and good separators to maintain coherence
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,  # Smaller chunks for better coherence
        chunk_overlap=150,  # Reduced overlap
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        keep_separator=True  # Keep separators to maintain structure
    )
    
    chunks = splitter.split_text(text)
    current_app.logger.info(f"Created {len(chunks)} chunks")
    
    # Log chunk previews to verify order
    for i, chunk in enumerate(chunks[:3]):  # First 3 chunks only
        current_app.logger.debug(f"Chunk {i+1} preview: {chunk[:150]}...")
    
    return chunks

# Workflow functions
def generate_synthetic_chunks(state: SyntheticState):
    """Generate synthetic versions of text chunks."""
    chunks = state["chunks"]
    synthetic_chunks = []
    
    current_app.logger.info(f"Processing {len(chunks)} chunks for synthetic generation")
    
    for i, chunk in enumerate(chunks):
        try:
            current_app.logger.info(f"Processing chunk {i+1}: {len(chunk)} characters")
            current_app.logger.debug(f"Original chunk: {chunk[:100]}...")
            
            messages = [
                SystemMessage(content="""You are a data anonymization expert. Create synthetic data that:

CRITICAL REQUIREMENTS:
1. MAINTAIN EXACT STRUCTURE: Keep the same paragraph breaks, sentence order, and flow as the original
2. PRESERVE NARRATIVE FLOW: The synthetic text should read naturally in the same sequence
3. REPLACE PII CONSISTENTLY: Replace all names, addresses, phones, emails, SSNs, etc. with realistic fake data
4. KEEP FORMAT IDENTICAL: Same document type, tone, and formatting
5. MAINTAIN LENGTH: Keep approximately the same length as the original

IMPORTANT: Return ONLY the synthetic version with the exact same structure and flow. Do not add explanations, headers, or change the narrative order."""),
                
                HumanMessage(content=f"Convert this text to synthetic data while preserving exact structure and flow:\n\n{chunk}")
            ]
            
            response = llm.invoke(messages)
            synthetic_chunk = response.content.strip()
            
            current_app.logger.info(f"Generated synthetic chunk {i+1}: {len(synthetic_chunk)} characters")
            current_app.logger.debug(f"Synthetic chunk: {synthetic_chunk[:100]}...")
            
            # Clean up any unwanted formatting
            synthetic_chunk = re.sub(r'```[\w]*\n', '', synthetic_chunk)
            synthetic_chunk = re.sub(r'\n```', '', synthetic_chunk)
            
            if not synthetic_chunk.strip():
                current_app.logger.warning(f"Empty synthetic chunk generated for chunk {i+1}, using fallback")
                synthetic_chunk = anonymize_text(chunk)
            
            synthetic_chunks.append(synthetic_chunk)
            
            # Update progress
            progress = ((i + 1) / len(chunks)) * 90  # 90% for processing chunks
            update_progress(state["job_id"], progress, f"Processing chunk {i+1}/{len(chunks)}")
            
        except Exception as e:
            current_app.logger.error(f"Failed to process chunk {i}: {e}")
            # Fallback: basic anonymization
            synthetic_chunk = anonymize_text(chunk)
            current_app.logger.info(f"Using fallback for chunk {i+1}: {len(synthetic_chunk)} characters")
            synthetic_chunks.append(synthetic_chunk)
    
    current_app.logger.info(f"Generated {len(synthetic_chunks)} synthetic chunks")
    return {"synthetic_chunks": synthetic_chunks}

def anonymize_text(text: str) -> str:
    """Basic text anonymization fallback."""
    replacements = [
        (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 'John Smith'),
        (r'\b\d{3}-\d{2}-\d{4}\b', '123-45-6789'),
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '555-123-4567'),
        (r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', 'example@email.com'),
        (r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', '$1,234.56'),
        (r'\b\d{1,5}\s+[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd)\b', '123 Main Street'),
    ]
    
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    return result

def assemble_final_text(state: SyntheticState):
    """Assemble chunks into final synthetic document maintaining order."""
    synthetic_chunks = state["synthetic_chunks"]
    
    current_app.logger.info(f"Assembling {len(synthetic_chunks)} chunks into final text")
    
    # Log chunk info for debugging
    for i, chunk in enumerate(synthetic_chunks):
        current_app.logger.debug(f"Chunk {i+1} length: {len(chunk)} chars")
        current_app.logger.debug(f"Chunk {i+1} preview: {chunk[:100]}...")
    
    # Join chunks with double newlines to preserve paragraph structure
    final_text = "\n\n".join(chunk.strip() for chunk in synthetic_chunks if chunk.strip())
    
    current_app.logger.info(f"Final assembled text length: {len(final_text)} characters")
    current_app.logger.debug(f"Final text preview: {final_text[:300]}...")
    
    # Clean up excessive newlines but preserve paragraph breaks
    final_text = re.sub(r'\n{4,}', '\n\n\n', final_text)  # Max 3 newlines
    final_text = final_text.strip()
    
    current_app.logger.info(f"Final text after cleanup: {len(final_text)} characters")
    
    if not final_text.strip():
        current_app.logger.error("Final text is empty after assembly!")
        # Emergency fallback
        final_text = "Synthetic data generation completed, but content appears to be empty. Please check the original document and try again."
    
    # Update progress
    update_progress(state["job_id"], 95, f"Assembling dataset {state['current_dataset']}")
    
    return {"final_text": final_text}

# Simple workflow
def create_workflow():
    """Create simple workflow."""
    graph = StateGraph(SyntheticState)
    
    graph.add_node("generate_chunks", generate_synthetic_chunks)
    graph.add_node("assemble_text", assemble_final_text)
    
    graph.add_edge(START, "generate_chunks")
    graph.add_edge("generate_chunks", "assemble_text")
    graph.add_edge("assemble_text", END)
    
    return graph.compile()

# Helper functions
def update_progress(job_id: str, progress: float, message: str):
    """Update job progress."""
    try:
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        db.synthetic_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "progress": min(100, max(0, progress)),
                    "status_message": message,
                    "updated_at": get_current_timestamp()
                }
            }
        )
    except Exception as e:
        current_app.logger.error(f"Progress update failed: {e}")

def update_job_status(job_id: str, status: str, datasets: List[Dict] = None, error: str = None):
    """Update job status."""
    try:
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        update_data = {
            "status": status,
            "completed_at": get_current_timestamp(),
            "updated_at": get_current_timestamp()
        }
        
        if datasets:
            update_data["generated_datasets"] = datasets
            update_data["progress"] = 100.0
        
        if error:
            update_data["error"] = error
        
        db.synthetic_jobs.update_one(
            {"job_id": job_id},
            {"$set": update_data}
        )
    except Exception as e:
        current_app.logger.error(f"Status update failed: {e}")

def create_pdf(text_content: str) -> bytes:
    """Create PDF from text content - simple and direct."""
    current_app.logger.info(f"create_pdf called with text length: {len(text_content)}")
    current_app.logger.info(f"Text preview (first 200 chars): {text_content[:200]}")
    
    try:
        if not text_content or not text_content.strip():
            current_app.logger.warning("create_pdf received empty or whitespace-only content")
            return b""
        
        # Create new PDF document
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)  # Letter size
        
        # Simple settings
        font_size = 11
        line_height = 14
        margin = 50
        max_width = 612 - 2 * margin
        
        # Clean text - preserve structure
        clean_text = text_content.strip().replace('\r\n', '\n').replace('\r', '\n')
        
        # Insert text using PyMuPDF's built-in text insertion with automatic wrapping
        text_rect = fitz.Rect(margin, margin, 612 - margin, 792 - margin)
        
        current_app.logger.info("Inserting text into PDF with automatic formatting")
        
        # Use insert_textbox for automatic line wrapping and page management
        text_length = page.insert_textbox(
            text_rect,
            clean_text,
            fontsize=font_size,
            fontname="helv",  # Helvetica
            color=(0, 0, 0),
            align=0,  # Left align
            morph=None
        )
        
        current_app.logger.info(f"Text inserted, used length: {text_length}")
        
        # If text doesn't fit on one page, handle overflow
        if text_length < 0:  # Text overflow
            current_app.logger.info("Text overflowed, creating multiple pages")
            
            # Split text into smaller chunks and create multiple pages
            words = clean_text.split()
            chunk_size = len(words) // 3  # Rough estimate for 3 pages
            
            doc = fitz.open()  # Start fresh
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = ' '.join(chunk_words)
                
                page = doc.new_page(width=612, height=792)
                text_rect = fitz.Rect(margin, margin, 612 - margin, 792 - margin)
                
                page.insert_textbox(
                    text_rect,
                    chunk_text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(0, 0, 0),
                    align=0
                )
        
        # Generate PDF bytes
        pdf_bytes = doc.write()
        doc.close()
        
        current_app.logger.info(f"PDF created successfully with {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        current_app.logger.error(f"PDF creation failed: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # Return empty bytes instead of text fallback
        return b""

# Main generator class
class SimpleDataGenerator:
    @staticmethod
    def get_document(document_id: str, user_id: str) -> tuple[str, str, str]:
        """Get document content."""
        mongo_db = get_mongo_db()
        document_data = mongo_db.get_file(document_id, user_id)
        
        if not document_data:
            raise ValueError("Document not found")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=document_data["file_type"]) as temp_file:
            temp_file.write(document_data["file_data"])
            temp_path = temp_file.name
        
        try:
            text_content = extract_text_from_file(temp_path, document_data["file_type"])
            return text_content, document_data["original_name"], document_data["file_type"]
        finally:
            os.unlink(temp_path)
    
    @staticmethod
    def generate_datasets(document_id: str, user_id: str, num_datasets: int, job_id: str):
        """Generate synthetic datasets."""
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            try:
                # Get document
                text_content, original_name, file_type = SimpleDataGenerator.get_document(
                    document_id, user_id
                )
                
                current_app.logger.info(f"Starting generation for {original_name} ({len(text_content)} chars)")
                
                # Create workflow
                workflow = create_workflow()
                datasets = []
                
                for dataset_num in range(1, num_datasets + 1):
                    current_app.logger.info(f"Generating dataset {dataset_num}/{num_datasets}")
                    
                    # Chunk the text
                    chunks = chunk_text(text_content)
                    current_app.logger.info(f"Created {len(chunks)} chunks")
                    
                    # Prepare state
                    initial_state = {
                        "original_text": text_content,
                        "chunks": chunks,
                        "current_dataset": dataset_num,
                        "total_datasets": num_datasets,
                        "job_id": job_id
                    }
                    
                    # Run workflow
                    result = workflow.invoke(initial_state)
                    
                    # Store result
                    dataset_info = store_dataset(
                        user_id=user_id,
                        original_document_id=document_id,
                        original_name=original_name,
                        synthetic_content=result["final_text"],
                        dataset_number=dataset_num,
                        job_id=job_id,
                        file_type=file_type
                    )
                    
                    datasets.append(dataset_info)
                    
                    # Update progress
                    progress = (dataset_num / num_datasets) * 100
                    update_progress(job_id, progress, f"Completed dataset {dataset_num}")
                
                # Mark as completed
                update_job_status(job_id, "completed", datasets)
                current_app.logger.info(f"Successfully generated {num_datasets} datasets")
                
            except Exception as e:
                current_app.logger.error(f"Generation failed: {str(e)}")
                update_job_status(job_id, "failed", [], str(e))

def store_dataset(user_id: str, original_document_id: str, original_name: str,
                 synthetic_content: str, dataset_number: int, job_id: str, file_type: str) -> Dict[str, Any]:
    """Store synthetic dataset."""
    
    current_app.logger.info(f"Storing dataset {dataset_number} with {len(synthetic_content)} characters")
    current_app.logger.debug(f"Content preview: {synthetic_content[:200]}...")
    
    if not synthetic_content.strip():
        current_app.logger.error(f"WARNING: Trying to store empty synthetic content for dataset {dataset_number}")
    
    mongo_db = get_mongo_db()
    db = mongo_db.get_database()
    
    synthetic_doc = {
        "user_id": user_id,
        "original_document_id": original_document_id,
        "original_name": original_name,
        "synthetic_name": f"synthetic_{dataset_number}_{original_name}",
        "dataset_number": dataset_number,
        "job_id": job_id,
        "content": synthetic_content,
        "original_file_type": file_type,
        "original_mime_type": "application/pdf" if file_type.lower() == ".pdf" else "text/plain",
        "created_at": get_current_timestamp(),
        "size": len(synthetic_content.encode('utf-8'))
    }
    
    result = db.synthetic_datasets.insert_one(synthetic_doc)
    current_app.logger.info(f"Stored dataset with ID: {result.inserted_id}")
    
    return {
        "id": str(result.inserted_id),
        "name": synthetic_doc["synthetic_name"],
        "dataset_number": dataset_number,
        "size": synthetic_doc["size"],
        "created_at": synthetic_doc["created_at"]
    }

# API Routes
@synthetic_data_bp.route('/generate', methods=['POST'])
@jwt_required()
def start_generation():
    """Start synthetic data generation."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate
        required_fields = ['document_id', 'num_datasets']
        validation_result = validate_required_fields(data, required_fields)
        if not validation_result['valid']:
            return error_response(
                code="VALIDATION_ERROR",
                message="Missing required fields",
                details=validation_result['missing_fields']
            )
        
        document_id = data['document_id']
        num_datasets = data['num_datasets']
        
        if not isinstance(num_datasets, int) or num_datasets < 1 or num_datasets > 10:
            return error_response(
                code="VALIDATION_ERROR",
                message="num_datasets must be between 1 and 10"
            )
        
        # Check document exists
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        document = db.documents.find_one({
            "_id": ObjectId(document_id),
            "user_id": user_id
        })
        
        if not document:
            return error_response(
                code="DOCUMENT_NOT_FOUND",
                message="Document not found"
            )
        
        # Create job
        job_id = f"job_{int(time.time())}_{user_id}"
        
        job_record = {
            "job_id": job_id,
            "user_id": user_id,
            "document_id": document_id,
            "document_name": document["original_name"],
            "num_datasets": num_datasets,
            "status": "processing",
            "progress": 0.0,
            "status_message": "Starting generation...",
            "created_at": get_current_timestamp(),
            "updated_at": get_current_timestamp()
        }
        
        db.synthetic_jobs.insert_one(job_record)
        
        # Start background generation
        thread = threading.Thread(
            target=SimpleDataGenerator.generate_datasets,
            args=(document_id, user_id, num_datasets, job_id)
        )
        thread.daemon = True
        thread.start()
        
        return success_response(
            message="Generation started",
            data={"job_id": job_id, "status": "processing"}
        )
        
    except Exception as e:
        current_app.logger.error(f"Generation start failed: {str(e)}")
        return error_response(
            code="START_ERROR",
            message="Failed to start generation",
            details=str(e)
        )

@synthetic_data_bp.route('/status/<job_id>', methods=['GET'])
@jwt_required()
def get_status(job_id: str):
    """Get generation status."""
    try:
        user_id = get_jwt_identity()
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        job = db.synthetic_jobs.find_one({
            "job_id": job_id,
            "user_id": user_id
        })
        
        if not job:
            return error_response(
                code="JOB_NOT_FOUND",
                message="Job not found"
            )
        
        return success_response(
            message="Job status retrieved",
            data={
                "job_id": job_id,
                "status": job["status"],
                "progress": job.get("progress", 0),
                "status_message": job.get("status_message", ""),
                "generated_datasets": job.get("generated_datasets", []),
                "error": job.get("error"),
                "created_at": job["created_at"],
                "updated_at": job.get("updated_at")
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Status check failed: {str(e)}")
        return error_response(
            code="STATUS_ERROR",
            message="Failed to get status",
            details=str(e)
        )

@synthetic_data_bp.route('/datasets/<dataset_id>/download', methods=['GET'])
@jwt_required()
def download_dataset(dataset_id: str):
    """Download synthetic dataset."""
    try:
        user_id = get_jwt_identity()
        current_app.logger.info(f"Download request for dataset {dataset_id} by user {user_id}")
        
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        dataset = db.synthetic_datasets.find_one({
            "_id": ObjectId(dataset_id),
            "user_id": user_id
        })
        
        if not dataset:
            current_app.logger.warning(f"Dataset {dataset_id} not found for user {user_id}")
            return error_response(
                code="DATASET_NOT_FOUND",
                message="Dataset not found"
            )
        
        current_app.logger.info(f"Found dataset: {dataset.get('synthetic_name')} with content length: {len(dataset.get('content', ''))}")
        
        # Get file info
        original_file_type = dataset.get("original_file_type", ".txt")
        synthetic_name = dataset['synthetic_name']
        content = dataset.get("content", "")
        
        current_app.logger.info(f"Original file type: {original_file_type}")
        current_app.logger.info(f"Content length: {len(content)}")
        current_app.logger.info(f"Content preview (first 100 chars): {content[:100]}")
        
        # Ensure proper file extension
        if not synthetic_name.endswith(original_file_type):
            base_name = synthetic_name
            for ext in ['.pdf', '.txt', '.md']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break
            synthetic_name = base_name + original_file_type
        
        # Convert to appropriate format
        if original_file_type.lower() == '.pdf':
            current_app.logger.info("Creating PDF from content")
            file_content = create_pdf(content)
            current_app.logger.info(f"PDF created with {len(file_content)} bytes")
            content_type = "application/pdf"
        else:
            current_app.logger.info("Using text format")
            file_content = content.encode('utf-8')
            content_type = "text/plain; charset=utf-8"
        
        current_app.logger.info(f"Final file content length: {len(file_content)} bytes")
        
        # Create response
        response = make_response(file_content)
        response.headers["Content-Type"] = content_type
        response.headers["Content-Disposition"] = f"attachment; filename=\"{synthetic_name}\""
        response.headers["Content-Length"] = str(len(file_content))
        
        current_app.logger.info(f"Download response created for {synthetic_name}")
        return response
        
    except Exception as e:
        current_app.logger.error(f"Download failed: {str(e)}")
        return error_response(
            code="DOWNLOAD_ERROR",
            message="Failed to download dataset",
            details=str(e)
        )

@synthetic_data_bp.route('/datasets', methods=['GET'])
@jwt_required()
def list_datasets():
    """List synthetic datasets."""
    try:
        user_id = get_jwt_identity()
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        datasets = list(db.synthetic_datasets.find(
            {"user_id": user_id},
            {"_id": 1, "synthetic_name": 1, "original_name": 1, 
             "dataset_number": 1, "size": 1, "created_at": 1, "original_file_type": 1}
        ).sort("created_at", -1))
        
        # Convert ObjectId to string
        for dataset in datasets:
            dataset["id"] = str(dataset["_id"])
            del dataset["_id"]
        
        return success_response(
            message="Datasets retrieved",
            data={"datasets": datasets}
        )
        
    except Exception as e:
        current_app.logger.error(f"List datasets failed: {str(e)}")
        return error_response(
            code="LIST_ERROR",
            message="Failed to list datasets",
            details=str(e)
        )

@synthetic_data_bp.route('/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    """List generation jobs."""
    try:
        user_id = get_jwt_identity()
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        jobs = list(db.synthetic_jobs.find(
            {"user_id": user_id},
            {"job_id": 1, "document_name": 1, "num_datasets": 1, 
             "status": 1, "progress": 1, "created_at": 1}
        ).sort("created_at", -1).limit(20))
        
        # Convert ObjectId to string if present
        for job in jobs:
            if "_id" in job:
                del job["_id"]  # Remove _id since we have job_id
        
        return success_response(
            message="Jobs retrieved",
            data={"jobs": jobs}
        )
        
    except Exception as e:
        current_app.logger.error(f"List jobs failed: {str(e)}")
        return error_response(
            code="LIST_ERROR",
            message="Failed to list jobs",
            details=str(e)
        )

@synthetic_data_bp.route('/datasets/<dataset_id>/preview', methods=['GET'])
@jwt_required()
def preview_dataset(dataset_id: str):
    """Preview synthetic dataset content."""
    try:
        user_id = get_jwt_identity()
        current_app.logger.info(f"Preview request for dataset {dataset_id} by user {user_id}")
        
        mongo_db = get_mongo_db()
        db = mongo_db.get_database()
        
        dataset = db.synthetic_datasets.find_one({
            "_id": ObjectId(dataset_id),
            "user_id": user_id
        })
        
        if not dataset:
            current_app.logger.warning(f"Dataset {dataset_id} not found for user {user_id}")
            return error_response(
                code="DATASET_NOT_FOUND",
                message="Dataset not found"
            )
        
        current_app.logger.info(f"Found dataset: {dataset.get('synthetic_name')} with content length: {len(dataset.get('content', ''))}")
        
        # Return full content for preview (no truncation)
        content = dataset.get("content", "")
        current_app.logger.info(f"Content preview (first 100 chars): {content[:100]}")
        
        content_preview = content  # Return full content, no truncation
        
        response_data = {
            "id": str(dataset["_id"]),
            "name": dataset["synthetic_name"],
            "original_name": dataset["original_name"],
            "size": dataset["size"],
            "content_preview": content_preview,
            "created_at": dataset["created_at"]
        }
        
        current_app.logger.info(f"Returning preview with content_preview length: {len(content_preview)}")
        
        return success_response(
            message="Dataset preview retrieved",
            data=response_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Preview failed: {str(e)}")
        return error_response(
            code="PREVIEW_ERROR",
            message="Failed to preview dataset",
            details=str(e)
        )
