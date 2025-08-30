"""
Utility functions for common operations.
Small, reusable functions that are used across the application.
"""

import os
import hashlib
import secrets
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from werkzeug.utils import secure_filename


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """Hash a password using a secure method."""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """Sanitize and secure a filename."""
    return secure_filename(filename)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and size_index < len(size_names) - 1:
        size /= 1024.0
        size_index += 1
    
    return f"{size:.1f} {size_names[size_index]}"


def extract_file_metadata(file_path: str, original_filename: str) -> dict:
    """Extract metadata from uploaded file."""
    stat = os.stat(file_path)
    return {
        "filename": original_filename,
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "content_type": _guess_content_type(original_filename),
        "hash": calculate_file_hash(file_path),
        "created_at": get_current_timestamp()
    }


def _guess_content_type(filename: str) -> str:
    """Guess content type from filename extension."""
    import mimetypes
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or 'application/octet-stream'


def create_file_upload_path(upload_folder: str, file_id: str, filename: str) -> str:
    """Create a safe file upload path."""
    safe_filename = sanitize_filename(filename)
    # Use first 2 chars of file_id for directory structure
    subdir = file_id[:2]
    upload_dir = os.path.join(upload_folder, subdir)
    os.makedirs(upload_dir, exist_ok=True)
    return os.path.join(upload_dir, f"{file_id}_{safe_filename}")


def paginate_list(items: List, page: int = 1, per_page: int = 20) -> tuple:
    """Paginate a list of items."""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    return items[start:end], total


def mask_sensitive_data(text: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data leaving only a few characters visible."""
    if len(text) <= visible_chars:
        return mask_char * len(text)
    
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start
    
    if visible_end == 0:
        return text[:visible_start] + mask_char * (len(text) - visible_start)
    else:
        return text[:visible_start] + mask_char * (len(text) - visible_chars) + text[-visible_end:]


def clean_text_for_analysis(text: str) -> str:
    """Clean text for PII analysis."""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
    return text


def get_file_extension(filename: str) -> Optional[str]:
    """Get file extension from filename."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return None


def is_text_file(filename: str) -> bool:
    """Check if file is a text-based file."""
    text_extensions = {'txt', 'csv', 'json', 'xml', 'md', 'yaml', 'yml'}
    ext = get_file_extension(filename)
    return ext in text_extensions if ext else False


def is_document_file(filename: str) -> bool:
    """Check if file is a document file."""
    doc_extensions = {'pdf', 'doc', 'docx', 'odt', 'rtf'}
    ext = get_file_extension(filename)
    return ext in doc_extensions if ext else False


def is_spreadsheet_file(filename: str) -> bool:
    """Check if file is a spreadsheet file."""
    sheet_extensions = {'xlsx', 'xls', 'csv', 'ods'}
    ext = get_file_extension(filename)
    return ext in sheet_extensions if ext else False
