"""
Session Management & Per-User Isolation
========================================
Manages per-session UUIDs, isolated directories for files and vectors,
rate limiting, automatic expiration cleanup, and data erasure.
"""

import os
import shutil
import time
import uuid
from typing import Tuple
import streamlit as st
from config import (
    BASE_DATA_DIR,
    SESSION_EXPIRY_HOURS,
    RATE_LIMIT_QUESTIONS,
    RATE_LIMIT_WINDOW_SECONDS
)


def get_or_create_session_id() -> str:
    """
    Returns the unique UUID4 string for the current browser session.
    Stored in st.session_state.
    """
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    return st.session_state["session_id"]


def get_session_dir(session_id: str) -> str:
    """Returns the root directory for a given session."""
    session_dir = os.path.join(BASE_DATA_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def get_session_upload_dir(session_id: str) -> str:
    """Returns the per-session upload directory for PDFs."""
    upload_dir = os.path.join(get_session_dir(session_id), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def get_session_chroma_dir(session_id: str) -> str:
    """Returns the per-session persistence directory for ChromaDB."""
    chroma_dir = os.path.join(get_session_dir(session_id), "chroma")
    os.makedirs(chroma_dir, exist_ok=True)
    return chroma_dir


def _safe_rmtree(path: str, max_retries: int = 3, delay: float = 0.2):
    """Safely removes a directory tree on Windows, handling open SQLite/Chroma file locks."""
    import gc
    if not os.path.exists(path):
        return
    gc.collect()
    for _ in range(max_retries):
        try:
            shutil.rmtree(path, ignore_errors=False)
            return
        except (PermissionError, OSError):
            gc.collect()
            time.sleep(delay)
    shutil.rmtree(path, ignore_errors=True)


def cleanup_expired_sessions(max_age_hours: int = SESSION_EXPIRY_HOURS) -> int:
    """
    Scans the session directory and safely removes directories older than max_age_hours.
    Returns the count of cleaned up sessions.
    """
    if not os.path.exists(BASE_DATA_DIR):
        return 0

    now = time.time()
    cutoff_time = now - (max_age_hours * 3600)
    cleaned_count = 0

    try:
        for entry in os.listdir(BASE_DATA_DIR):
            entry_path = os.path.join(BASE_DATA_DIR, entry)
            if os.path.isdir(entry_path):
                try:
                    mtime = os.path.getmtime(entry_path)
                    if mtime < cutoff_time:
                        _safe_rmtree(entry_path)
                        cleaned_count += 1
                except Exception:
                    pass
    except Exception:
        pass

    return cleaned_count


def clear_session_data(session_id: str):
    """
    Completely purges a user session's uploaded files, Chroma vectorstore,
    and resets session state with Windows file-lock handling.
    """
    import gc
    # 1. Release active in-memory session objects so Windows unlocks files
    try:
        if "vectorstore" in st.session_state and st.session_state["vectorstore"] is not None:
            try:
                vs = st.session_state["vectorstore"]
                if hasattr(vs, "_client"):
                    if hasattr(vs._client, "clear_system_cache"):
                        vs._client.clear_system_cache()
                    if hasattr(vs._client, "reset"):
                        vs._client.reset()
                del vs
            except Exception:
                pass

        st.session_state["retriever"] = None
        st.session_state["vectorstore"] = None
        st.session_state["indexed_papers"] = {}
        st.session_state["pdf_sources"] = []
        st.session_state["processed_files"] = []
        st.session_state["processed_signatures"] = []
        st.session_state["processed_file_hashes"] = []
        st.session_state["messages"] = []
        st.session_state["last_failed_query"] = None
        st.session_state["pending"] = None
        st.session_state["uploader_nonce"] = st.session_state.get("uploader_nonce", 0) + 1
        st.session_state["doc_stats"] = {
            "num_files": 0,
            "num_pages": 0,
            "num_chunks": 0,
            "file_list": []
        }
        st.session_state["paper_summaries"] = {}
        st.session_state["paper_comparisons"] = {}
        st.session_state["research_gaps"] = {}
        st.session_state["literature_reviews"] = {}
    except Exception:
        pass

    gc.collect()

    # 2. Safely purge disk directory
    session_dir = os.path.join(BASE_DATA_DIR, session_id)
    if os.path.exists(session_dir):
        _safe_rmtree(session_dir)


_session_query_timestamps = {}


def check_rate_limit(session_id: str = None) -> Tuple[bool, str]:
    """
    Enforces a sliding window rate limit of 20 questions per 10 minutes per session.
    Accepts optional session_id for call-site compatibility.
    Returns (is_allowed, friendly_message).
    """
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    sid = session_id or "default"

    # Synchronize with in-memory dict strictly isolated by session_id
    if sid not in _session_query_timestamps:
        _session_query_timestamps[sid] = []
    _session_query_timestamps[sid] = [
        t for t in _session_query_timestamps[sid] if t > cutoff
    ]
    history = _session_query_timestamps[sid]

    # Also sync into st.session_state if available, keyed by session_id
    try:
        if "query_timestamps_by_session" not in st.session_state:
            st.session_state["query_timestamps_by_session"] = {}
        st_hist = st.session_state["query_timestamps_by_session"].setdefault(sid, [])
        st.session_state["query_timestamps_by_session"][sid] = [t for t in st_hist if t > cutoff]
        st.session_state["query_timestamps"] = st.session_state["query_timestamps_by_session"][sid]
    except Exception:
        pass

    count = len(history)
    if count >= RATE_LIMIT_QUESTIONS:
        oldest = history[0]
        wait_seconds = int((oldest + RATE_LIMIT_WINDOW_SECONDS) - now)
        wait_minutes = max(1, (wait_seconds + 59) // 60)
        return False, (
            f"⏳ **Rate limit reached**: You have submitted {RATE_LIMIT_QUESTIONS} questions in the last 10 minutes. "
            f"Please wait about {wait_minutes} minute{'s' if wait_minutes != 1 else ''} before submitting another question."
        )

    # Record timestamp in both stores
    history.append(now)
    try:
        if sid in st.session_state.get("query_timestamps_by_session", {}):
            st.session_state["query_timestamps_by_session"][sid].append(now)
    except Exception:
        pass

    return True, ""
