"""
MSRA System Configuration & Limits
===================================
Production limits, timeout settings, and environment loading helpers.
"""

import os
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

# --- Configurable Limits ---
MAX_FILE_SIZE_MB = 25
MAX_PDFS_PER_SESSION = 5
MAX_TOTAL_PAGES = 300
MAX_QUESTION_LENGTH = 1000

# Rate limits: 20 questions per 10 minutes (600 seconds)
RATE_LIMIT_QUESTIONS = 20
RATE_LIMIT_WINDOW_SECONDS = 600

# Pipeline Status Constants & Standard Messages
NOT_FOUND_PREFIX = "I couldn't find this in the uploaded papers."
STATUS_OK = "ok"
STATUS_NOT_FOUND = "not_found"
STATUS_ERROR = "error"

# Session Cleanup
SESSION_EXPIRY_HOURS = 2

# Base directories
BASE_DATA_DIR = os.path.join("data", "sessions")
os.makedirs(BASE_DATA_DIR, exist_ok=True)


def get_api_key(key_name: str) -> str:
    """
    Safely retrieves an API key from st.secrets first, then os.environ.
    Never logs or prints the actual key value.
    """
    # 1. Try Streamlit Secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets is not None and key_name in st.secrets:
            val = str(st.secrets[key_name]).strip()
            if val and not val.startswith("your_"):
                return val
    except Exception:
        pass

    # 2. Try os.environ / .env
    val = os.getenv(key_name, "").strip()
    if val and not val.startswith("your_"):
        return val

    # Backwards compatibility check: API_KEY for Gemini
    if key_name == "GEMINI_API_KEY":
        alt = os.getenv("API_KEY", "").strip()
        if alt and not alt.startswith("your_"):
            return alt

    return ""


def validate_api_keys() -> tuple[bool, str]:
    """
    Checks if at least one LLM provider has an API key configured.
    Returns (is_valid, user_friendly_error_message).
    """
    gemini_key = get_api_key("GEMINI_API_KEY")
    groq_key = get_api_key("GROQ_API_KEY")

    if not gemini_key and not groq_key:
        return False, (
            "⚠️ **API Configuration Required**: Neither `GEMINI_API_KEY` nor `GROQ_API_KEY` was found. "
            "Please configure your API key in Streamlit secrets or in your environment variables."
        )
    return True, ""
