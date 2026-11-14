"""
Error Handling & Validation Utilities
======================================
Robust checks for PDF integrity, corruption, password protection,
scanned pages, limit enforcement, and sanitized server-side error logging.
"""

import io
import sys
from typing import Tuple

try:
    import pypdf
except ImportError:
    try:
        import PyPDF2 as pypdf
    except ImportError:
        pypdf = None

from config import (
    MAX_FILE_SIZE_MB,
    MAX_QUESTION_LENGTH
)


def validate_pdf_file(file_input, filename: str = "document.pdf") -> Tuple[bool, str]:
    """
    Validates a PDF's integrity and structure.
    Accepts bytes, bytearray, or an UploadedFile-like object (with getvalue() or getbuffer()).
    Detects empty, oversized, encrypted, corrupted, or scanned (no text layer) files.

    Returns:
        (is_valid: bool, user_friendly_error_message: str)
    """
    try:
        if file_input is None:
            return False, f"📄 **Empty File**: `{filename}` is completely empty (0 bytes)."

        # Extract raw bytes safely from bytes or Streamlit UploadedFile
        if hasattr(file_input, "getvalue") and callable(file_input.getvalue):
            try:
                file_bytes = file_input.getvalue()
            except Exception as e:
                return False, f"⚠️ **Read Error**: Could not read `{filename}`: {str(e)}"
        elif hasattr(file_input, "getbuffer") and callable(file_input.getbuffer):
            try:
                file_bytes = bytes(file_input.getbuffer())
            except Exception as e:
                return False, f"⚠️ **Read Error**: Could not read `{filename}`: {str(e)}"
        elif isinstance(file_input, (bytes, bytearray)):
            file_bytes = bytes(file_input)
        elif hasattr(file_input, "read") and callable(file_input.read):
            try:
                file_bytes = file_input.read()
            except Exception as e:
                return False, f"⚠️ **Read Error**: Could not read `{filename}`: {str(e)}"
        else:
            return False, f"⚠️ **Invalid File**: Expected bytes or file stream, got {type(file_input).__name__}."

        # 1. Empty Check
        if not file_bytes or len(file_bytes) == 0:
            return False, f"📄 **Empty File**: `{filename}` is completely empty (0 bytes)."

        # 2. File Size Limit
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            return False, f"📦 **File Too Large**: `{filename}` exceeds the maximum file size limit of {MAX_FILE_SIZE_MB} MB."

        # 3. PDF Header Magic Bytes
        if not file_bytes.startswith(b"%PDF"):
            return False, f"⚠️ **Invalid Format**: `{filename}` does not appear to be a valid PDF document (missing %PDF signature)."

        # 4. Parsing, Password & Corruption Checks
        if pypdf is None:
            # Graceful fallback if pypdf is not installed
            return True, ""

        stream = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(stream)

        # Password protected check
        if reader.is_encrypted:
            return False, f"🔒 **Password Protected**: `{filename}` is encrypted with a password. Please remove the password and re-upload."

        num_pages = len(reader.pages)
        if num_pages == 0:
            return False, f"📄 **No Pages**: `{filename}` contains 0 pages."

        # Scanned PDF / No text layer check
        text_samples = []
        sample_indices = set([0, num_pages // 2, num_pages - 1])
        for idx in sample_indices:
            if idx < num_pages:
                try:
                    txt = reader.pages[idx].extract_text() or ""
                    text_samples.append(txt.strip())
                except Exception:
                    pass

        combined_sample = "".join(text_samples)
        if len(combined_sample.strip()) < 10:
            # Check entire document if sample was dry
            full_text = "".join(p.extract_text() or "" for p in reader.pages).strip()
            if len(full_text) < 15:
                return False, f"📷 **Scanned Document**: `{filename}` contains images without a readable text layer. Please upload a text-based or OCR-processed PDF."

        return True, ""

    except Exception as e:
        err_str = str(e)
        if "PdfReadError" in type(e).__name__ or "PdfReadError" in err_str:
            return False, f"⚠️ **Corrupted PDF**: `{filename}` cannot be read or is damaged: {err_str}"
        return False, f"⚠️ **Unreadable PDF**: `{filename}` could not be processed: {err_str}"


def validate_question(question: str, max_length: int = MAX_QUESTION_LENGTH) -> Tuple[bool, str]:
    """
    Validates question length against max_length.
    """
    if not question or not question.strip():
        return False, "Please enter a valid research question."
    if len(question.strip()) > max_length:
        return False, f"⚠️ Question exceeds the maximum limit of {max_length} characters (current length: {len(question.strip())})."
    return True, ""


def safe_log(context: str, err: Exception):
    """
    Safely logs an error message server-side without exposing API keys or document contents.
    """
    err_type = type(err).__name__
    err_msg = str(err)
    # Sanitize any potential keys from message
    for secret_prefix in ["AIza", "gsk_"]:
        if secret_prefix in err_msg:
            err_msg = "[REDACTED_API_KEY]"
    sys.stderr.write(f"[MSRA_SERVER_LOG] {context}: {err_type} - {err_msg}\n")
