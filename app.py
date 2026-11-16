"""
MSRA – Modular Smart Research Assistant
Premium ChatGPT-Style Dark Research Workspace
"""

import os
import sys

# Auto-link project virtualenv site-packages if running outside venv
_proj_dir = os.path.dirname(os.path.abspath(__file__))
_venv_site = os.path.join(_proj_dir, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

import uuid
import time
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List

# Prevent Windows Application Control DLL load failure on gRPC telemetry and HF hub checks
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

try:
    import grpc  # noqa: F401
except (ImportError, OSError) as grpc_err:
    sys.stderr.write(f"[MSRA_STARTUP] Non-critical gRPC telemetry mock active: {type(grpc_err).__name__}\n")
    from unittest.mock import MagicMock
    _grpc_mock = MagicMock()
    _grpc_mock.__version__ = "1.60.0"
    sys.modules["grpc"] = _grpc_mock
    sys.modules["grpc._cython"] = _grpc_mock
    sys.modules["grpc._cython.cygrpc"] = _grpc_mock

import streamlit as st

# Backend Module Imports
from config import (
    validate_api_keys,
    MAX_FILE_SIZE_MB,
    MAX_PDFS_PER_SESSION,
    MAX_TOTAL_PAGES,
    MAX_QUESTION_LENGTH,
    SESSION_EXPIRY_HOURS,
    NOT_FOUND_PREFIX,
    STATUS_OK,
    STATUS_NOT_FOUND,
    STATUS_ERROR
)
from utils.session import (
    get_or_create_session_id,
    get_session_upload_dir,
    cleanup_expired_sessions,
    clear_session_data,
    check_rate_limit,
)
from utils.errors import (
    validate_pdf_file,
    validate_question,
    safe_log
)
from src.chain import (
    research,
    generate_paper_summary,
    generate_paper_comparison,
    detect_research_gaps,
    generate_literature_review
)
from src.workflows import (
    WORKFLOW_REGISTRY,
    execute_workflow,
    get_workflow_definition
)
from src.citations import normalize_citations, filter_sources_by_citations
from src.llm import (
    GEMINI_MODELS,
    GROQ_MODELS,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    get_model_display_name
)
from src.pdf_rag import (
    load_pdf,
    split_documents,
    get_or_create_vectorstore,
    add_chunks_to_vectorstore,
    get_retriever,
    delete_paper_from_vectorstore,
    has_ready_papers
)
from src.export import export_to_pdf

# Automatic cleanup of expired session directories safely at startup
try:
    cleanup_expired_sessions(max_age_hours=SESSION_EXPIRY_HOURS)
except Exception as _e:
    pass

# Scope flag: Research Q&A workspace active
SHOW_EXTRA_FEATURES = False

# ------------------------------------------------------------------------------
# LOGO MARK CONSTANT (Crisp 44x44 Emerald Hexagon with Connected Nodes)
# ------------------------------------------------------------------------------
MSRA_LOGO_SVG = """<svg width="44" height="44" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <polygon points="24,3 42,13.5 42,34.5 24,45 6,34.5 6,13.5" stroke="#10A37F" stroke-width="2" stroke-linejoin="round"/>
  <polyline points="14,32 14,16 24,27 34,16 34,32" stroke="#ECECEC" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="14" cy="16" r="3" fill="#10A37F"/>
  <circle cx="24" cy="27" r="3" fill="#10A37F"/>
  <circle cx="34" cy="16" r="3" fill="#10A37F"/>
  <circle cx="14" cy="32" r="2" fill="#ECECEC"/>
  <circle cx="34" cy="32" r="2" fill="#ECECEC"/>
</svg>"""

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & BACKGROUND HOOK
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="MSRA – Modular Smart Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.background_3d import render_background_effect
render_background_effect()


# ------------------------------------------------------------------------------
# 2. SCOPED CUSTOM CSS
# ------------------------------------------------------------------------------
def inject_custom_css():
    """Applies carefully scoped styling for the pure black ChatGPT research workspace."""
    st.markdown("""
<style>
/* 1. Global Viewport & Base Canvas Surfaces */
html, body {
    margin: 0 !important;
    padding: 0 !important;
    width: 100vw !important;
    max-width: 100vw !important;
    overflow-x: hidden !important;
    background-color: #000000 !important;
}

[data-testid="stAppViewContainer"],
.stApp {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
    background-color: #000000 !important;
}

header[data-testid="stHeader"],
.stAppHeader {
    background: transparent !important;
    background-color: transparent !important;
    height: 0px !important;
    min-height: 0px !important;
}

/* 2. Left Sidebar (Flush at left screen edge x=0, no 80px gap) */
section[data-testid="stSidebar"] {
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    margin: 0 !important;
    padding-left: 0 !important;
    width: 260px !important;
    min-width: 260px !important;
    background-color: #171717 !important;
    border-right: 1px solid #262626 !important;
    z-index: 100 !important;
}

section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
    padding-bottom: 0px !important;
}

section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    padding-top: 1rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
}

/* Sidebar action buttons */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background-color: transparent !important;
    border: 1px solid #333333 !important;
    color: #ECECEC !important;
    border-radius: 8px !important;
    transition: all 0.15s ease !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 0.5rem 0.75rem !important;
}

section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background-color: #212121 !important;
    border-color: #444444 !important;
    color: #FFFFFF !important;
}

/* 3. Main Workspace Container */
section[data-testid="stMain"] {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
}

section[data-testid="stMain"] > div:first-child {
    padding-top: 0.5rem !important;
}

/* 4. Desktop Layout (>1100px): Wide Chat + Fixed Right Tools Panel */
@media (min-width: 1101px) {
    .block-container,
    [data-testid="stMainBlockContainer"] {
        width: 100% !important;
        max-width: none !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-left: 2rem !important;
        padding-right: calc(340px + 2rem) !important;
        padding-top: 1rem !important;
        padding-bottom: 9.5rem !important;
        box-sizing: border-box !important;
    }

    /* Chat takes all available horizontal space up to the right panel */
    div.st-key-chat_history_container {
        width: 100% !important;
        max-width: none !important;
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }

    /* Fixed right-side Research Tools panel */
    div.st-key-fixed_research_tools {
        position: fixed !important;
        top: 0 !important;
        right: 0 !important;
        width: 340px !important;
        height: 100vh !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        background-color: #0e0e0e !important;
        border-left: 1px solid #262626 !important;
        z-index: 99 !important;
        padding: 1.5rem 1rem 3rem 1rem !important;
        box-sizing: border-box !important;
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.45) !important;
    }

    /* Subtle custom scrollbar for fixed panel */
    div.st-key-fixed_research_tools::-webkit-scrollbar {
        width: 5px;
    }
    div.st-key-fixed_research_tools::-webkit-scrollbar-track {
        background: transparent;
    }
    div.st-key-fixed_research_tools::-webkit-scrollbar-thumb {
        background: #2a2a2a;
        border-radius: 4px;
    }

    /* Bottom Model Selector & Chat Input alignment */
    div[data-testid="stBottom"] .block-container,
    div[data-testid="stBottom"] [data-testid="stMainBlockContainer"] {
        width: 100% !important;
        max-width: none !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding-left: 2rem !important;
        padding-right: calc(340px + 2rem) !important;
        box-sizing: border-box !important;
    }
}

/* 5. Responsive Fallback (<=1100px): Tools Panel Stacked Above Chat */
@media (max-width: 1100px) {
    .block-container,
    [data-testid="stMainBlockContainer"] {
        width: 100% !important;
        max-width: none !important;
        margin: 0 !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        padding-bottom: 9.5rem !important;
        display: flex !important;
        flex-direction: column !important;
        box-sizing: border-box !important;
    }

    div[data-testid="stBottom"] .block-container,
    div[data-testid="stBottom"] [data-testid="stMainBlockContainer"] {
        width: 100% !important;
        max-width: none !important;
        margin: 0 !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        box-sizing: border-box !important;
    }

    div.st-key-fixed_research_tools {
        order: -1 !important; /* Positions tools panel above chat */
        position: static !important;
        width: 100% !important;
        max-width: 100% !important;
        height: auto !important;
        max-height: 480px !important;
        overflow-y: auto !important;
        border-left: none !important;
        border-bottom: 1px solid #262626 !important;
        padding: 0 0 1rem 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        margin-bottom: 1.5rem !important;
    }

    div.st-key-chat_history_container {
        order: 1 !important;
        width: 100% !important;
        max-width: 100% !important;
    }
}

/* 6. Chat Messages & Normal Sentence Text Wrapping */
div[data-testid="stChatMessage"] {
    background-color: transparent !important;
    padding: 1rem 0 !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
    width: 100% !important;
    max-width: none !important;
    box-sizing: border-box !important;
}

div[data-testid="stChatMessageContent"],
div[data-testid="stChatMessage"] > div:nth-child(2),
div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    width: 100% !important;
    max-width: none !important;
    white-space: normal !important;
    word-break: normal !important;
    overflow-wrap: break-word !important;
}

div[data-testid="stChatMessage"] p,
div[data-testid="stChatMessage"] li,
div[data-testid="stChatMessage"] span,
div[data-testid="stChatMessage"] div {
    white-space: normal !important;
    word-break: normal !important;
    overflow-wrap: break-word !important;
    font-size: 15px !important;
    line-height: 1.65 !important;
    color: #D1D5DB !important;
}

/* Markdown tables (Multi-Paper Comparison matrix) fit without horizontal squishing; allow overflow-x: auto */
div[data-testid="stChatMessage"] table,
div[data-testid="stMarkdownContainer"] table {
    width: 100% !important;
    display: block !important;
    overflow-x: auto !important;
    white-space: nowrap !important;
    border-collapse: collapse !important;
    margin: 1rem 0 !important;
    -webkit-overflow-scrolling: touch;
}

div[data-testid="stChatMessage"] table th,
div[data-testid="stMarkdownContainer"] table th {
    background-color: #1a1a1a !important;
    color: #ECECEC !important;
    font-weight: 600 !important;
    padding: 8px 14px !important;
    border: 1px solid #333333 !important;
}

div[data-testid="stChatMessage"] table td,
div[data-testid="stMarkdownContainer"] table td {
    padding: 8px 14px !important;
    border: 1px solid #262626 !important;
    color: #D1D5DB !important;
}

/* 7. Prompt Pills Container & Buttons */
.st-key-prompt_pills button,
div[data-testid="stVerticalBlock"]:has(> div.st-key-prompt_pills) button,
div.st-key-prompt_pills button {
    background-color: #0F0F0F !important;
    border: 1px solid #262626 !important;
    border-radius: 12px !important;
    color: #ECECEC !important;
    text-align: left !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 14px 16px !important;
    min-height: 54px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
}

.st-key-prompt_pills button:hover:not(:disabled) {
    background-color: #171717 !important;
    border-color: #383838 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    color: #FFFFFF !important;
}

.st-key-prompt_pills button:disabled {
    opacity: 0.35 !important;
    cursor: not-allowed !important;
    border-color: #1F1F1F !important;
    background-color: #0A0A0A !important;
    box-shadow: none !important;
}

/* 8. Sources Expander */
[data-testid="stExpander"] {
    border: 1px solid #262626 !important;
    background: #0D0D0D !important;
    border-radius: 8px !important;
    margin-top: 0.5rem !important;
}

/* 9. Bottom Sticky Bar & Elements */
div[data-testid="stBottom"] {
    background: linear-gradient(180deg, rgba(0,0,0,0) 0%, #000000 35%, #000000 100%) !important;
    padding-bottom: 1.25rem !important;
    z-index: 90 !important;
}

div[data-testid="stChatInput"] {
    width: 100% !important;
    max-width: none !important;
}

div.st-key-model_selector {
    width: 100% !important;
    max-width: none !important;
}

div.st-key-model_selector button {
    border-radius: 20px !important;
    font-size: 12px !important;
    padding: 4px 12px !important;
    background-color: #1A1A1A !important;
    border: 1px solid #333333 !important;
    color: #A1A1AA !important;
}
</style>
""", unsafe_allow_html=True)

inject_custom_css()


# ------------------------------------------------------------------------------
# 3. SINGLE SOURCE OF TRUTH: SESSION STATE INITIALIZATION
# ------------------------------------------------------------------------------
def init_session_state():
    """Initializes per-user session state keys."""
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "indexed_papers" not in st.session_state:
        # {sha256_hash: {"name": str, "pages": int, "chunks": int, "size": int}}
        st.session_state["indexed_papers"] = {}
    if "uploader_nonce" not in st.session_state:
        st.session_state["uploader_nonce"] = 0
    if "vectorstore" not in st.session_state:
        st.session_state["vectorstore"] = None
    if "retriever" not in st.session_state:
        st.session_state["retriever"] = None
    if "pdf_sources" not in st.session_state:
        st.session_state["pdf_sources"] = []
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "pending" not in st.session_state:
        st.session_state["pending"] = None  # None or {"id": str, "mode": str, "query": str}
    if "executing_pending_id" not in st.session_state:
        st.session_state["executing_pending_id"] = None
    if "last_failed_query" not in st.session_state:
        st.session_state["last_failed_query"] = None
    if "research_topic" not in st.session_state:
        st.session_state["research_topic"] = ""
    if "is_indexing" not in st.session_state:
        st.session_state["is_indexing"] = False
    if "indexing_error" not in st.session_state:
        st.session_state["indexing_error"] = None
    if "selected_provider" not in st.session_state:
        st.session_state["selected_provider"] = "Google Gemini"
    if "gemini_model" not in st.session_state:
        st.session_state["gemini_model"] = DEFAULT_GEMINI_MODEL
    if "groq_model" not in st.session_state:
        st.session_state["groq_model"] = DEFAULT_GROQ_MODEL
    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = DEFAULT_GEMINI_MODEL
    if "enable_fallback" not in st.session_state:
        st.session_state["enable_fallback"] = True
    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = "💬 Research Q&A"
    if "paper_summaries" not in st.session_state:
        st.session_state["paper_summaries"] = {}
    if "paper_comparisons" not in st.session_state:
        st.session_state["paper_comparisons"] = {}
    if "research_gaps" not in st.session_state:
        st.session_state["research_gaps"] = {}
    if "literature_reviews" not in st.session_state:
        st.session_state["literature_reviews"] = {}

init_session_state()


# ------------------------------------------------------------------------------
# 4. INCREMENTAL, HASH-BASED DOCUMENT INGESTION (Single shared function)
# ------------------------------------------------------------------------------
def ingest_files(uploaded_files):
    """
    Ingests and indexes only newly added PDFs based on SHA-256 hash.
    Preserves existing indexed papers, writes chunks in batches of 64,
    and updates indexed_papers only upon successful completion.
    """
    if not uploaded_files:
        return

    session_id = get_or_create_session_id()
    session_upload_dir = get_session_upload_dir(session_id)
    indexed_map = st.session_state["indexed_papers"]

    # Deduplicate and extract bytes
    new_files_to_index = []
    seen_names = [info["name"] for info in indexed_map.values()]

    for uploaded_file in uploaded_files:
        if hasattr(uploaded_file, "getvalue"):
            file_bytes = uploaded_file.getvalue()
        elif hasattr(uploaded_file, "getbuffer"):
            file_bytes = bytes(uploaded_file.getbuffer())
        else:
            file_bytes = b""

        file_hash = hashlib.sha256(file_bytes).hexdigest()
        if file_hash in indexed_map:
            continue  # Already indexed

        # Handle duplicate filenames with numerical suffix
        base_name = uploaded_file.name
        display_name = base_name
        suffix = 1
        while display_name in seen_names:
            name_part, ext_part = os.path.splitext(base_name)
            display_name = f"{name_part} ({suffix}){ext_part}"
            suffix += 1
        seen_names.append(display_name)

        new_files_to_index.append((display_name, file_bytes, file_hash))

    if not new_files_to_index:
        return

    # Check session paper limits
    if len(indexed_map) + len(new_files_to_index) > MAX_PDFS_PER_SESSION:
        st.error(f"⚠️ Limit exceeded: Maximum {MAX_PDFS_PER_SESSION} PDFs allowed per session (currently {len(indexed_map)} indexed).")
        return

    st.session_state["is_indexing"] = True
    st.session_state["indexing_error"] = None

    with st.status("Processing research papers...", expanded=True) as status_box:
        progress_bar = st.progress(0, text="Validating research papers...")
        total_indexed_new = 0

        # Retrieve or initialize the session vectorstore once
        vectorstore = get_or_create_vectorstore(session_id=session_id)

        for idx, (filename, file_bytes, file_hash) in enumerate(new_files_to_index, 1):
            pct_base = int((idx - 1) / len(new_files_to_index) * 80)
            progress_bar.progress(pct_base, text=f"Processing paper {idx} of {len(new_files_to_index)}: {filename}")
            status_box.update(label=f"Extracting PDF: {filename} ({idx}/{len(new_files_to_index)})...", state="running")
            st.write(f"📄 **Extracting PDF**: Reading text from `{filename}`...")

            # 1. Validation
            val_res = validate_pdf_file(file_bytes, filename)
            if isinstance(val_res, (tuple, list)) and len(val_res) >= 2:
                is_valid, error_msg = bool(val_res[0]), str(val_res[1])
            elif isinstance(val_res, (tuple, list)) and len(val_res) == 1:
                is_valid, error_msg = bool(val_res[0]), ""
            elif isinstance(val_res, bool):
                is_valid, error_msg = val_res, ""
            else:
                is_valid, error_msg = False, "Validation failed."

            if not is_valid:
                st.warning(f"⚠️ {filename}: {error_msg}")
                continue

            # 2. Save temporary file
            pdf_path = os.path.join(session_upload_dir, filename)
            try:
                with open(pdf_path, "wb") as f:
                    f.write(file_bytes)
            except Exception as io_err:
                st.error(f"⚠️ Failed to save {filename}: {str(io_err)}")
                continue

            # 3. Load PDF
            loaded_docs = load_pdf(pdf_path, file_hash=file_hash)
            if not loaded_docs:
                st.warning(f"⚠️ {filename} contained no readable text layer.")
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
                continue

            # Enforce total pages cap
            current_total_pages = sum(info["pages"] for info in indexed_map.values())
            if current_total_pages + len(loaded_docs) > MAX_TOTAL_PAGES:
                allowed = MAX_TOTAL_PAGES - current_total_pages
                if allowed <= 0:
                    st.warning(f"⚠️ Maximum total page limit ({MAX_TOTAL_PAGES}) reached. Skipping '{filename}'.")
                    try:
                        os.remove(pdf_path)
                    except Exception:
                        pass
                    continue
                loaded_docs = loaded_docs[:allowed]
                st.warning(f"⚠️ Truncated '{filename}' to {allowed} page(s) to respect max page limit.")

            # 4. Chunk document
            chunks = split_documents(loaded_docs, file_hash=file_hash)
            if not chunks:
                continue

            st.write(f"✂️ **Splitting Text**: Generated {len(chunks)} chunks across {len(loaded_docs)} pages.")

            # 5. Embed and add chunks in batches of 64
            status_box.update(label=f"Generating Embeddings & Indexing: {filename}...", state="running")
            st.write(f"⚡ **Generating Embeddings & Indexing**: Storing {len(chunks)} chunks into ChromaDB...")
            try:
                def batch_progress(sub_pct):
                    actual_pct = min(95, pct_base + int(sub_pct * 0.2))
                    progress_bar.progress(actual_pct, text=f"Indexing `{filename}` ({sub_pct}%)...")

                add_chunks_to_vectorstore(vectorstore, chunks, batch_size=64, progress_callback=batch_progress)

                # 6. Commit to indexed_papers ONLY after chunks successfully written
                indexed_map[file_hash] = {
                    "name": filename,
                    "pages": len(loaded_docs),
                    "chunks": len(chunks),
                    "size": len(file_bytes)
                }
                st.session_state["pdf_sources"].extend(loaded_docs)
                total_indexed_new += 1
            except Exception as write_err:
                safe_log(f"Failed indexing {filename}", write_err)
                st.session_state["indexing_error"] = str(write_err)
                delete_paper_from_vectorstore(vectorstore, file_hash=file_hash)
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
                st.error(f"⚠️ Error indexing `{filename}`: {str(write_err)}")

        if total_indexed_new > 0:
            total_new_chunks = sum(info["chunks"] for h, info in indexed_map.items() if h in [f[2] for f in new_files_to_index])
            st.session_state["vectorstore"] = vectorstore
            st.session_state["retriever"] = get_retriever(vectorstore)
            progress_bar.progress(100, text="Indexing complete!")
            status_box.update(label=f"Indexed {total_indexed_new} document(s) ({total_new_chunks} chunks). Paper ready.", state="complete", expanded=False)
            st.success(f"✅ Processed {total_indexed_new} document(s) into {total_new_chunks} chunks. Ready for research questions.")
            st.toast(f"Successfully indexed {total_indexed_new} paper(s) ({total_new_chunks} chunks)!", icon="✅")
        elif not indexed_map:
            status_box.update(label="Failed to index papers", state="error", expanded=True)

    st.session_state["is_indexing"] = False


@st.dialog("Upload Papers")
def show_upload_dialog():
    st.write("Upload academic research papers in PDF format to index with citations.")
    st.caption("🔒 *Privacy Note*: Papers are processed temporarily and deleted when you clear data or your session expires.")
    nonce = st.session_state.get("uploader_nonce", 0)
    uploaded_files = st.file_uploader(
        "Drop PDFs here",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"dialog_uploader_{nonce}",
        help=f"Upload up to {MAX_PDFS_PER_SESSION} PDFs (max {MAX_FILE_SIZE_MB}MB each, up to {MAX_TOTAL_PAGES} total pages)."
    )
    if uploaded_files:
        ingest_files(uploaded_files)
    if st.button("Close", type="primary", use_container_width=True):
        st.rerun()


# ------------------------------------------------------------------------------
# 5. SIDEBAR BRANDING & DATA MANAGEMENT
# ------------------------------------------------------------------------------
def render_brand():
    """Renders the top sidebar brand lockup with crisp SVG icon and bold wordmark."""
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1.1rem; margin-top: 0.2rem;">
        <div style="flex-shrink: 0; display: flex; align-items: center; justify-content: center; width: 44px; height: 44px;">
            {MSRA_LOGO_SVG}
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
            <span style="font-size: 31px; font-weight: 700; letter-spacing: 0.06em; color: #ECECEC; line-height: 1.1;">MSRA</span>
            <span style="font-size: 12px; color: #8E8E8E; font-weight: 400; margin-top: 2px;">Modular Smart Research Assistant</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        # 1. Brand Lockup
        render_brand()

        # 2. + New Research Chat (Clears messages and pending query, preserves papers)
        if st.button("+ New Research Chat", use_container_width=True, type="secondary"):
            st.session_state["messages"] = []
            st.session_state["last_failed_query"] = None
            st.session_state["pending"] = None
            st.rerun()

        # 3. Upload Papers Popover
        with st.popover("Upload Papers", icon=":material/upload_file:", use_container_width=True):
            st.caption("🔒 *Privacy Note*: Papers are processed temporarily and deleted when you clear data or your session expires.")
            nonce = st.session_state.get("uploader_nonce", 0)
            uploaded_files = st.file_uploader(
                "Drop PDFs here",
                type=["pdf"],
                accept_multiple_files=True,
                key=f"sidebar_uploader_{nonce}",
                help=f"Upload up to {MAX_PDFS_PER_SESSION} PDFs (max {MAX_FILE_SIZE_MB}MB each, up to {MAX_TOTAL_PAGES} total pages)."
            )
            if uploaded_files:
                ingest_files(uploaded_files)

        # 4. Indexed Papers Status & Paper Chips
        indexed_map = st.session_state.get("indexed_papers", {})
        num_ready = len(indexed_map)

        if num_ready == 0:
            st.markdown("<div style='font-size: 12px; color: #6B6B6B; margin: 4px 0 8px 4px;'>No papers yet</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="font-size: 12px; color: #10A37F; display: flex; align-items: center; gap: 6px; margin: 6px 0 6px 4px; font-weight: 500;">
                <span style="width: 7px; height: 7px; border-radius: 50%; background-color: #10A37F; display: inline-block;"></span>
                {num_ready} paper{'s' if num_ready != 1 else ''} ready
            </div>
            """, unsafe_allow_html=True)

            for file_hash, info in list(indexed_map.items()):
                fname = info["name"]
                short_name = fname[:16] + "..." if len(fname) > 19 else fname
                size_kb = info.get("size", 0) / 1024
                size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.0f} KB"

                c_row1, c_row2 = st.columns([5, 1])
                with c_row1:
                    st.caption(f":material/description: {short_name} • {size_str}")
                with c_row2:
                    if st.button("✕", key=f"del_h_{file_hash[:10]}", help=f"Remove {fname}"):
                        # 1. Delete paper chunks from ChromaDB
                        if st.session_state.get("vectorstore"):
                            delete_paper_from_vectorstore(st.session_state["vectorstore"], filename=fname, file_hash=file_hash)

                        # 2. Delete file from session upload directory
                        session_id = get_or_create_session_id()
                        session_dir = get_session_upload_dir(session_id)
                        target_path = os.path.join(session_dir, fname)
                        if os.path.exists(target_path):
                            try:
                                os.remove(target_path)
                            except Exception:
                                pass

                        # 3. Update state
                        del st.session_state["indexed_papers"][file_hash]
                        st.session_state["pdf_sources"] = [
                            doc for doc in st.session_state["pdf_sources"]
                            if doc.metadata.get("file_hash") != file_hash and doc.metadata.get("source") != fname
                        ]

                        if not st.session_state["indexed_papers"]:
                            st.session_state["retriever"] = None
                            st.session_state["vectorstore"] = None
                        else:
                            st.session_state["retriever"] = get_retriever(st.session_state["vectorstore"])

                        st.session_state["uploader_nonce"] = st.session_state.get("uploader_nonce", 0) + 1
                        st.rerun()

        # 5. Clear all my data button
        if st.button("🗑️ Clear all my data", use_container_width=True, help="Permanently delete all session files, vectors, and chat history."):
            session_id = st.session_state.get("session_id")
            if session_id:
                clear_session_data(session_id)
            st.toast("All session files and data cleared.", icon="🗑️")
            st.rerun()

        st.divider()

        # 6. Research Focus Setting
        with st.expander(":material/tune: Research Focus (optional)", expanded=False):
            st.session_state["research_topic"] = st.text_input(
                "Research Focus / Scope",
                value=st.session_state.get("research_topic", ""),
                placeholder="e.g. Transformers in Education",
                help="Tell MSRA your topic so answers stay on scope."
            )

        st.markdown("""
        <div style="font-size: 11px; color: #5A5A5A; margin-top: 1.5rem; text-align: left; padding-left: 4px;">
            🔬 MSRA – Modular Smart Research Assistant
        </div>
        """, unsafe_allow_html=True)

render_sidebar()


# ------------------------------------------------------------------------------
# 6. PENDING-QUERY DISPATCHER & STREAMING PROCESSOR
# ------------------------------------------------------------------------------
def queue_query(query_or_workflow: str, mode: str = "qa", extra_payload: Any = None):
    """
    Unified query dispatcher. Appends user message and queues execution via st.session_state['pending'].
    """
    if mode == "workflow":
        wf = get_workflow_definition(query_or_workflow)
        display_label = wf["label"] if wf else query_or_workflow
        st.session_state["messages"].append({
            "role": "user",
            "content": display_label
        })
    elif mode == "summary":
        target = extra_payload or query_or_workflow
        st.session_state["messages"].append({
            "role": "user",
            "content": f"📝 Generate Academic Summary: `{target}`"
        })
    elif mode == "comparison":
        papers = extra_payload if isinstance(extra_payload, list) else [query_or_workflow]
        st.session_state["messages"].append({
            "role": "user",
            "content": f"⚖️ Multi-Paper Comparison Matrix: {', '.join(f'`{p}`' for p in papers)}"
        })
    elif mode == "gaps":
        papers = extra_payload if isinstance(extra_payload, list) else ([query_or_workflow] if query_or_workflow and query_or_workflow != "gaps" else [])
        scope_str = ", ".join(f"`{p}`" for p in papers) if papers else "All Uploaded Papers"
        st.session_state["messages"].append({
            "role": "user",
            "content": f"🔍 Detect Research Gaps & Limitations: {scope_str}"
        })
    elif mode == "qa":
        st.session_state["messages"].append({
            "role": "user",
            "content": query_or_workflow
        })
    elif mode == "regenerate":
        pass

    st.session_state["pending"] = {
        "id": str(uuid.uuid4()),
        "mode": mode,
        "query": query_or_workflow,
        "extra_payload": extra_payload
    }
    st.rerun()


def extract_follow_ups(text: str) -> List[str]:
    """Extracts 2-3 follow-up questions from the end of the text if present."""
    if not text:
        return []
    for header in ["### 💡 Suggested Follow-ups", "Suggested Follow-ups"]:
        pos = text.find(header)
        if pos != -1:
            follow_up_section = text[pos:]
            lines = follow_up_section.split("\n")
            questions = []
            for line in lines[1:]:
                cleaned = line.strip().lstrip("-*•0123456789.[]() ").strip()
                if cleaned and "?" in cleaned:
                    questions.append(cleaned)
            return questions[:3]
    return []


def strip_follow_ups(text: str) -> str:
    """Strips the 'Suggested Follow-ups' block from the saved message content."""
    if not text:
        return ""
    for header in ["### 💡 Suggested Follow-ups", "Suggested Follow-ups"]:
        pos = text.find(header)
        if pos != -1:
            return text[:pos].strip()
    return text.strip()


def format_chat_history(messages: List[Dict[str, Any]]) -> str:
    """Formats last 6 messages (each ~300 chars) with follow-ups & citations stripped."""
    if not messages:
        return ""
    recent = messages[-6:]
    formatted_turns = []
    for m in recent:
        role = m.get("role", "user").capitalize()
        content = strip_follow_ups(m.get("content", ""))
        clean_c = re.sub(r'\[\d+\]', '', content).strip()
        if len(clean_c) > 300:
            clean_c = clean_c[:300] + "..."
        if clean_c:
            formatted_turns.append(f"{role}: {clean_c}")
    return "\n".join(formatted_turns)


def process_pending():
    """
    Executes the pending research or workflow query at the top-level chat container.
    Guards against duplicate runs, streams tokens, extracts follow-ups, and normalizes citations.
    """
    pending = st.session_state.get("pending")
    if not pending:
        return

    pending_id = pending.get("id")
    if st.session_state.get("executing_pending_id") == pending_id:
        return
    st.session_state["executing_pending_id"] = pending_id

    mode = pending.get("mode")
    query_val = pending.get("query")
    session_id = get_or_create_session_id()

    # 1. Check API keys
    has_keys, key_err = validate_api_keys()
    if not has_keys:
        st.session_state["messages"].append({
            "role": "assistant",
            "content": f"⚠️ **API Configuration Required**: {key_err}\n\nPlease add `GEMINI_API_KEY` or `GROQ_API_KEY` to your environment or secrets.",
            "citations": [],
            "provider_info": "",
            "status": STATUS_ERROR,
            "follow_ups": []
        })
        st.session_state["last_failed_query"] = query_val
        st.session_state["pending"] = None
        st.session_state["executing_pending_id"] = None
        st.rerun()
        return

    # 2. Check papers readiness
    if not has_ready_papers(st.session_state.get("indexed_papers", {}), st.session_state.get("vectorstore")):
        if st.session_state.get("is_indexing"):
            reason = "Papers are currently indexing. Please wait a moment."
        elif st.session_state.get("indexing_error"):
            reason = f"Indexing failed: {st.session_state['indexing_error']}"
        else:
            reason = "Please upload at least one research paper PDF in the sidebar drawer before asking questions."

        st.session_state["messages"].append({
            "role": "assistant",
            "content": reason,
            "citations": [],
            "provider_info": "",
            "status": STATUS_NOT_FOUND,
            "follow_ups": []
        })
        st.session_state["pending"] = None
        st.session_state["executing_pending_id"] = None
        st.rerun()
        return

    # 3. Check rate limiting
    allowed, rate_msg = check_rate_limit(session_id)
    if not allowed:
        st.session_state["messages"].append({
            "role": "assistant",
            "content": f"⚠️ **Rate Limit**: {rate_msg}",
            "citations": [],
            "provider_info": "",
            "status": STATUS_ERROR,
            "follow_ups": []
        })
        st.session_state["last_failed_query"] = query_val
        st.session_state["pending"] = None
        st.session_state["executing_pending_id"] = None
        st.rerun()
        return

    # 4. Stream response inside top-level assistant chat message
    prov = st.session_state.get("selected_provider", "Google Gemini")
    mod = st.session_state.get("selected_model", None)
    fb = st.session_state.get("enable_fallback", True)
    research_focus = st.session_state.get("research_topic", "")
    vectorstore = st.session_state.get("vectorstore")
    retriever = st.session_state.get("retriever")

    with st.chat_message("assistant", avatar="🔬"):
        provider_used = prov
        is_fallback = False
        try:
            if mode == "workflow":
                stream_res, citations, provider_used, is_fallback = execute_workflow(
                    query_val,
                    vectorstore,
                    research_focus=research_focus,
                    provider=prov,
                    model_name=mod,
                    enable_fallback=fb,
                    stream=True
                )
            elif mode == "summary":
                docs = st.session_state.get("pdf_sources", [])
                target_filename = pending.get("extra_payload") or (query_val if query_val != "summary" else None)
                stream_res, citations, provider_used, is_fallback = generate_paper_summary(
                    docs,
                    target_filename=target_filename,
                    provider=prov,
                    model_name=mod,
                    enable_fallback=fb
                )
            elif mode == "comparison":
                docs = st.session_state.get("pdf_sources", [])
                selected_files = pending.get("extra_payload") or ([f.strip() for f in query_val.split(",")] if query_val else [])
                stream_res, citations, provider_used, is_fallback = generate_paper_comparison(
                    docs,
                    selected_filenames=selected_files,
                    provider=prov,
                    model_name=mod,
                    enable_fallback=fb
                )
            elif mode == "gaps":
                docs = st.session_state.get("pdf_sources", [])
                selected_files = pending.get("extra_payload") or ([f.strip() for f in query_val.split(",")] if query_val and query_val != "gaps" else None)
                stream_res, citations, provider_used, is_fallback = detect_research_gaps(
                    docs,
                    selected_filenames=selected_files,
                    provider=prov,
                    model_name=mod,
                    enable_fallback=fb
                )
            else:
                recent_history = format_chat_history(st.session_state["messages"][:-1])
                stream_res, citations, provider_used, is_fallback = research(
                    query_val,
                    retriever,
                    chat_history=recent_history,
                    provider=prov,
                    model_name=mod,
                    enable_fallback=fb,
                    stream=True,
                    research_focus=research_focus
                )

            # Consume stream
            if isinstance(stream_res, str):
                raw_answer = stream_res
                st.markdown(raw_answer)
            else:
                def token_generator():
                    nonlocal provider_used, is_fallback
                    for item in stream_res:
                        if isinstance(item, (tuple, list)):
                            if len(item) >= 3:
                                token, p_used, f_back = item[0], item[1], item[2]
                                provider_used = p_used
                                is_fallback = f_back
                                yield token
                            elif len(item) == 2:
                                token, p_used = item[0], item[1]
                                provider_used = p_used
                                yield token
                            elif len(item) == 1:
                                yield item[0]
                        elif isinstance(item, str):
                            yield item
                        else:
                            yield str(item)

                raw_answer = st.write_stream(token_generator())

            if not raw_answer or not str(raw_answer).strip():
                raise Exception("Language model returned an empty response.")

            follow_ups = extract_follow_ups(raw_answer)
            clean_answer = strip_follow_ups(raw_answer)

            valid_ids = {c["id"] for c in citations if isinstance(c, dict) and "id" in c}
            if valid_ids:
                normalized_answer, cited_ids = normalize_citations(clean_answer, valid_ids=valid_ids)
                filtered_citations = filter_sources_by_citations(citations, cited_ids)
                if not filtered_citations and citations:
                    filtered_citations = citations
            else:
                normalized_answer = clean_answer
                filtered_citations = citations

            if normalized_answer.startswith(NOT_FOUND_PREFIX):
                status = STATUS_NOT_FOUND
                filtered_citations = []
            else:
                status = STATUS_OK

            provider_info = f"Generated using {provider_used}"
            st.session_state["last_failed_query"] = None

        except Exception as e:
            safe_log("process_pending execution failed", e)
            normalized_answer = f"⚠️ **Service Notice**: Failed to generate answer ({str(e)}). Please click Retry Question or switch model."
            st.markdown(normalized_answer)
            filtered_citations = []
            provider_info = prov
            status = STATUS_ERROR
            follow_ups = []
            st.session_state["last_failed_query"] = query_val

    st.session_state["messages"].append({
        "role": "assistant",
        "content": normalized_answer,
        "citations": filtered_citations,
        "provider_info": provider_info,
        "status": status,
        "follow_ups": follow_ups
    })

    st.session_state["pending"] = None
    st.session_state["executing_pending_id"] = None
    st.rerun()


# ------------------------------------------------------------------------------
# 7. CHAT EXPERIENCE & CITATIONS COMPONENTS
# ------------------------------------------------------------------------------
def render_citations(citations: List[Dict[str, Any]]):
    """Renders trustworthy page-level source references with badges and chunk snippets."""
    if not citations:
        return

    with st.expander(f":material/menu_book: Sources ({len(citations)})", expanded=False):
        for cite in citations:
            label = cite.get("citation_label", f"[{cite.get('id', '')}]")
            source = cite.get("source", "Unknown Document")
            page = cite.get("page", "Page N/A")
            snippet = cite.get("snippet", "")

            st.markdown(f"**`{label}`** :material/description: **{source}** • `{page}`")
            if snippet:
                st.markdown(
                    f"<div style='font-size: 12px; color: #A1A1AA; background: rgba(255, 255, 255, 0.03); border-left: 2px solid #2DD4BF; padding: 6px 10px; margin-top: 4px; margin-bottom: 10px; border-radius: 0 4px 4px 0; font-style: italic; line-height: 1.4;'>"
                    f"\"{snippet}\""
                    f"</div>",
                    unsafe_allow_html=True
                )


def render_message(message: Dict[str, Any], idx: int, is_last_assistant: bool = False):
    """Renders a single message bubble with action controls."""
    role = message["role"]
    content = message["content"]

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🔬"):
            st.markdown(content)

            # Sources drawer (only if citations exist)
            if message.get("citations"):
                render_citations(message["citations"])

            # Model attribution label
            if message.get("provider_info"):
                st.markdown(
                    f"<div style='font-size: 11.5px; color: #8E8E8E; margin-top: 6px; margin-bottom: 8px; display: flex; align-items: center; gap: 5px;'>"
                    f"<span style='color: #2DD4BF;'>⚡</span> {message['provider_info']}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            # Action Row: Copy, Regenerate (ONLY for the last assistant message), PDF Download, Thumbs Feedback
            col_actions, col_fb = st.columns([3, 1])
            with col_actions:
                sub_c1, sub_c2, sub_c3 = st.columns([1, 1.4, 1.2])
                with sub_c1:
                    with st.popover(":material/content_copy: Copy"):
                        st.code(content, language="markdown")
                with sub_c2:
                    if is_last_assistant:
                        if st.button(":material/refresh: Regenerate", key=f"regen_{idx}"):
                            # Find the last user query
                            prev_q = None
                            for m in reversed(st.session_state["messages"][:idx]):
                                if m["role"] == "user":
                                    prev_q = m["content"]
                                    break
                            if prev_q:
                                st.session_state["messages"].pop(idx)
                                queue_query(prev_q, mode="regenerate")
                with sub_c3:
                    try:
                        pdf_data = export_to_pdf(
                            title="MSRA Research Finding",
                            content=content,
                            topic=st.session_state.get("research_topic", ""),
                            citations=message.get("citations", []),
                            provider_info=message.get("provider_info", "")
                        )
                        st.download_button(
                            label=":material/picture_as_pdf: PDF",
                            data=pdf_data,
                            file_name=f"MSRA_Research_Finding_{idx}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_msg_{idx}",
                            help="Export this finding as a formatted PDF report"
                        )
                    except Exception as e:
                        safe_log("PDF generation for message failed", e)

            with col_fb:
                st.feedback("thumbs", key=f"feedback_{idx}")


def render_empty_state():
    """Renders clean onboarding and the 4 suggested-prompt workflow pills."""
    indexed_map = st.session_state.get("indexed_papers", {})
    num_ready = len(indexed_map)

    # Header with strict typography & 8px grid
    st.markdown("""
    <div style="text-align: center; margin-top: 0.5rem; margin-bottom: 32px;">
        <h1 style="font-size: 42px; font-weight: 700; letter-spacing: -0.03em; color: #ECECEC; margin: 0 0 12px 0; line-height: 1.15;">
            What are you researching today?
        </h1>
        <div style="font-size: 16px; color: #A1A1A1; line-height: 1.5; margin: 0;">
            MSRA – Modular Smart Research Assistant with grounded citations.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3 Step Cards in st.columns(3, gap="small")
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        with st.container(key="card_1"):
            if st.button(
                ":material/upload_file: **1. Upload Papers**\n\nDrop academic PDFs to index with citations",
                key="btn_card_upload",
                use_container_width=True,
                help="Click to upload research papers"
            ):
                show_upload_dialog()

    with c2:
        with st.container(key="card_2", border=True):
            st.markdown("""
            <div class="card-content">
                <div class="card-title"><span class="card-icon">💬</span> 2. Ask Anything</div>
                <div class="card-desc">Query methodologies, findings, datasets, or conclusions.</div>
            </div>
            """, unsafe_allow_html=True)

    with c3:
        with st.container(key="card_3", border=True):
            st.markdown("""
            <div class="card-content">
                <div class="card-title"><span class="card-icon">🛡️</span> 3. Cited Answers</div>
                <div class="card-desc">Every claim is mapped to page-level verified sources.</div>
            </div>
            """, unsafe_allow_html=True)

    # Consistent 24px vertical space
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # 2x2 Grid of Suggested Prompt Pills wrapped in st.container(key="prompt_pills")
    all_disabled = (num_ready == 0)
    all_help = "Upload at least one paper first" if all_disabled else None

    compare_disabled = (num_ready < 2)
    compare_help = "Upload at least one paper first" if all_disabled else ("Needs 2 or more papers" if compare_disabled else None)

    with st.container(key="prompt_pills"):
        p1, p2 = st.columns(2, gap="small")
        with p1:
            if st.button(
                ":material/lightbulb: Summarize Key Methodologies",
                use_container_width=True,
                key="pill_methodologies",
                disabled=all_disabled,
                help=all_help
            ):
                queue_query("methodologies", mode="workflow")

            if st.button(
                ":material/balance: Compare Findings Across Papers",
                use_container_width=True,
                key="pill_findings",
                disabled=compare_disabled,
                help=compare_help
            ):
                queue_query("compare", mode="workflow")

        with p2:
            if st.button(
                ":material/search: Identify Research Gaps & Limitations",
                use_container_width=True,
                key="pill_gaps",
                disabled=all_disabled,
                help=all_help
            ):
                queue_query("gaps", mode="workflow")

            if st.button(
                ":material/help_outline: Core Research Questions",
                use_container_width=True,
                key="pill_questions",
                disabled=all_disabled,
                help=all_help
            ):
                queue_query("core_questions", mode="workflow")


def render_chat_history():
    """Renders active conversation thread."""
    if len(st.session_state["messages"]) == 0:
        render_empty_state()
    else:
        if st.session_state.get("research_topic"):
            st.caption(f":material/bookmark: Active Research Focus: **{st.session_state['research_topic']}**")

        last_assistant_idx = None
        for i in range(len(st.session_state["messages"]) - 1, -1, -1):
            if st.session_state["messages"][i]["role"] == "assistant":
                last_assistant_idx = i
                break

        for idx, msg in enumerate(st.session_state["messages"]):
            render_message(msg, idx, is_last_assistant=(idx == last_assistant_idx))

        # Retry button if previous query resulted in an error status
        if st.session_state.get("last_failed_query"):
            retry_q = st.session_state["last_failed_query"]
            col_retry, _ = st.columns([1, 2])
            with col_retry:
                if st.button("🔄 Retry Question", key="btn_retry_failed", type="primary", use_container_width=True):
                    if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "assistant":
                        st.session_state["messages"].pop()
                    st.session_state["last_failed_query"] = None
                    queue_query(retry_q, mode="regenerate")

        # Dynamic follow-ups rendering ONLY for the last assistant message
        if last_assistant_idx is not None:
            last_msg = st.session_state["messages"][last_assistant_idx]
            msg_status = last_msg.get("status", STATUS_OK)

            if msg_status == STATUS_NOT_FOUND:
                st.write("")
                st.markdown("<div style='font-size: 11.5px; font-weight: 600; color: #8E8E8E; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;'>Suggested Follow-up:</div>", unsafe_allow_html=True)
                if st.button("💡 What topics does this document cover?", key="fup_topics", use_container_width=True):
                    queue_query("What topics and sections does this document cover?", mode="qa")
            elif msg_status == STATUS_OK:
                fups = last_msg.get("follow_ups", [])
                if fups:
                    st.write("")
                    st.markdown("<div style='font-size: 11.5px; font-weight: 600; color: #8E8E8E; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;'>Suggested Follow-ups:</div>", unsafe_allow_html=True)
                    cols = st.columns(len(fups))
                    for c_idx, f_query in enumerate(fups):
                        with cols[c_idx]:
                            if st.button(f"💡 {f_query}", key=f"dyn_fup_{c_idx}", use_container_width=True):
                                queue_query(f_query, mode="qa")


def on_provider_change():
    """Resets selected_model to the default model when provider is switched."""
    new_provider = st.session_state.get("selected_provider", "Google Gemini")
    if new_provider == "Google Gemini":
        st.session_state["selected_model"] = DEFAULT_GEMINI_MODEL
    else:
        st.session_state["selected_model"] = DEFAULT_GROQ_MODEL


def render_chat_input():
    """Renders bottom model selector, bottom-anchored chat input, and disclaimer."""
    provider = st.session_state.get("selected_provider", "Google Gemini")
    model = st.session_state.get("selected_model", DEFAULT_GEMINI_MODEL)
    short_model = get_model_display_name(model)
    selector_label = f":material/auto_awesome: {short_model}"

    with st.bottom:
        with st.container(key="model_selector"):
            with st.popover(selector_label):
                st.markdown("<div style='font-size: 11px; font-weight: 600; color: #8E8E8E; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;'>Model Settings</div>", unsafe_allow_html=True)
                st.radio(
                    "Primary Provider",
                    ["Google Gemini", "Groq"],
                    key="selected_provider",
                    on_change=on_provider_change
                )
                if st.session_state["selected_provider"] == "Google Gemini":
                    cur_gem = st.session_state.get("gemini_model", DEFAULT_GEMINI_MODEL)
                    gem_idx = GEMINI_MODELS.index(cur_gem) if cur_gem in GEMINI_MODELS else 0
                    chosen_model = st.selectbox(
                        "Gemini Model",
                        GEMINI_MODELS,
                        index=gem_idx,
                        format_func=get_model_display_name,
                        key="gemini_model"
                    )
                    st.session_state["selected_model"] = chosen_model
                else:
                    cur_groq = st.session_state.get("groq_model", DEFAULT_GROQ_MODEL)
                    groq_idx = GROQ_MODELS.index(cur_groq) if cur_groq in GROQ_MODELS else 0
                    chosen_model = st.selectbox(
                        "Groq Model",
                        GROQ_MODELS,
                        index=groq_idx,
                        format_func=get_model_display_name,
                        key="groq_model"
                    )
                    st.session_state["selected_model"] = chosen_model
                st.checkbox(
                    "Auto-Provider Fallback",
                    key="enable_fallback",
                    help="Automatically switch to the alternate provider if quota or rate limits occur."
                )

        input_disabled = (st.session_state.get("pending") is not None or st.session_state.get("is_indexing", False))
        user_query = st.chat_input("Ask a question across your loaded research papers...", disabled=input_disabled)

        st.markdown(
            "<div style='text-align: center; color: #6B6B6B; font-size: 12px; margin-top: 8px; margin-bottom: 4px;'>"
            "MSRA – Modular Smart Research Assistant can make mistakes. Verify important citations."
            "</div>",
            unsafe_allow_html=True
        )

    if user_query and user_query.strip():
        queue_query(user_query.strip(), mode="qa")


def render_research_tools_panel():
    """
    Dedicated Research Tools panel on the right side of the main workspace.
    Provides one-click action buttons and popovers for:
    1. Research Paper Summarization (9-part structured summary)
    2. Multi-Paper Comparison (9 dimensions matrix)
    3. Research Gap Detection (6 categorized dimensions)
    4. Export Research Output to PDF
    """
    indexed_map = st.session_state.get("indexed_papers", {})
    paper_names = [info["name"] for info in indexed_map.values()]
    num_ready = len(paper_names)
    is_busy = (st.session_state.get("pending") is not None or st.session_state.get("is_indexing", False))

    with st.container(border=True):
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
            <span style="font-size: 18px;">🔬</span>
            <span style="font-size: 16px; font-weight: 700; color: #ECECEC;">Research Tools</span>
        </div>
        <div style="font-size: 11.5px; color: #8E8E8E; margin-bottom: 14px;">
            Structured analyses &amp; PDF reports
        </div>
        """, unsafe_allow_html=True)

        # ----------------------------------------------------
        # FEATURE 1: Research Paper Summarization
        # ----------------------------------------------------
        st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #ECECEC; margin-bottom: 2px;'>📝 Paper Summarization</div>", unsafe_allow_html=True)
        st.caption("9-part academic summary: Problem, Objectives, Methodology, Dataset, Findings, Limits & Future Scope.")

        if num_ready == 0:
            st.button(":material/summarize: Summarize Paper", key="btn_sum_empty", disabled=True, use_container_width=True, help="Upload a research paper first.")
        elif num_ready == 1:
            short_p = paper_names[0][:16] + "..." if len(paper_names[0]) > 19 else paper_names[0]
            if st.button(f":material/summarize: Summarize `{short_p}`", key="btn_panel_sum_single", disabled=is_busy, use_container_width=True):
                queue_query(paper_names[0], mode="summary", extra_payload=paper_names[0])
        else:
            with st.popover(":material/summarize: Summarize Paper...", use_container_width=True):
                st.markdown("<div style='font-size: 12px; font-weight: 600; color: #ECECEC; margin-bottom: 6px;'>Select Paper to Summarize:</div>", unsafe_allow_html=True)
                target_paper = st.selectbox("Choose paper", paper_names, key="pop_sel_sum_paper", label_visibility="collapsed")
                if st.button("Generate Academic Summary", type="primary", use_container_width=True, key="btn_run_pop_sum", disabled=is_busy):
                    queue_query(target_paper, mode="summary", extra_payload=target_paper)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # FEATURE 2: Multi-Paper Comparison
        # ----------------------------------------------------
        st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #ECECEC; margin-bottom: 2px;'>⚖️ Multi-Paper Comparison</div>", unsafe_allow_html=True)
        st.caption("Compare 2+ papers across 9 dimensions in a Markdown matrix with similarities & differences.")

        if num_ready < 2:
            st.button(
                ":material/compare: Compare Papers",
                key="btn_comp_disabled",
                disabled=True,
                use_container_width=True,
                help="Upload at least 2 papers to compare."
            )
            if num_ready == 1:
                st.caption("ℹ️ *Upload at least 1 more paper to enable.*")
        else:
            with st.popover(":material/compare: Compare Papers...", use_container_width=True):
                st.markdown("<div style='font-size: 12px; font-weight: 600; color: #ECECEC; margin-bottom: 6px;'>Select Papers to Compare (min 2):</div>", unsafe_allow_html=True)
                selected_for_comp = []
                for p_idx, p_name in enumerate(paper_names):
                    if st.checkbox(p_name, value=True, key=f"chk_comp_{p_idx}"):
                        selected_for_comp.append(p_name)

                can_run_comp = len(selected_for_comp) >= 2
                if not can_run_comp:
                    st.caption("⚠️ Select at least 2 papers.")
                if st.button("Generate Comparison Matrix", type="primary", disabled=(not can_run_comp or is_busy), use_container_width=True, key="btn_run_comp_matrix"):
                    queue_query(", ".join(selected_for_comp), mode="comparison", extra_payload=selected_for_comp)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # FEATURE 3: Research Gap Detection
        # ----------------------------------------------------
        st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #ECECEC; margin-bottom: 2px;'>🔍 Research Gap Detection</div>", unsafe_allow_html=True)
        st.caption("6 categorized gap dimensions distinguishing author-stated limits vs inferred opportunities.")

        if num_ready == 0:
            st.button(":material/troubleshoot: Detect Gaps", key="btn_gaps_disabled", disabled=True, use_container_width=True, help="Upload a paper first.")
        elif num_ready == 1:
            short_p = paper_names[0][:16] + "..." if len(paper_names[0]) > 19 else paper_names[0]
            if st.button(f":material/troubleshoot: Detect Gaps (`{short_p}`)", key="btn_panel_gap_single", disabled=is_busy, use_container_width=True):
                queue_query(paper_names[0], mode="gaps", extra_payload=[paper_names[0]])
        else:
            with st.popover(":material/troubleshoot: Detect Gaps...", use_container_width=True):
                st.markdown("<div style='font-size: 12px; font-weight: 600; color: #ECECEC; margin-bottom: 6px;'>Analyze Gaps Across:</div>", unsafe_allow_html=True)
                gap_mode = st.radio("Scope", ["All Uploaded Papers", "Specific Papers"], key="gap_scope_radio")
                selected_for_gaps = []
                if gap_mode == "Specific Papers":
                    for g_idx, p_name in enumerate(paper_names):
                        if st.checkbox(p_name, value=True, key=f"chk_gap_{g_idx}"):
                            selected_for_gaps.append(p_name)
                else:
                    selected_for_gaps = paper_names

                can_run_gaps = len(selected_for_gaps) > 0
                if st.button("Detect Research Gaps", type="primary", disabled=(not can_run_gaps or is_busy), use_container_width=True, key="btn_run_gaps_action"):
                    queue_query(", ".join(selected_for_gaps), mode="gaps", extra_payload=selected_for_gaps)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # FEATURE 4: Export Research Output to PDF
        # ----------------------------------------------------
        st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #ECECEC; margin-bottom: 2px;'>📥 Export Research Output</div>", unsafe_allow_html=True)
        st.caption("Download structured academic PDF reports with MSRA branding and verified citations.")

        assistant_messages = [m for m in st.session_state.get("messages", []) if m.get("role") == "assistant" and m.get("content")]

        if not assistant_messages:
            st.button(":material/picture_as_pdf: Export Report (PDF)", key="btn_exp_disabled", disabled=True, use_container_width=True, help="Ask a question or run an analysis first to export.")
        else:
            with st.popover(":material/picture_as_pdf: Export Report (PDF)...", use_container_width=True):
                st.markdown("<div style='font-size: 12px; font-weight: 600; color: #ECECEC; margin-bottom: 6px;'>Select Export Content:</div>", unsafe_allow_html=True)
                export_options = ["Latest Research Output", "Full Session Transcript"]
                export_choice = st.radio("Choose Content", export_options, key="export_pdf_choice")

                report_title = st.text_input("Report Title", value="MSRA Research Analysis Report", key="pdf_report_title")

                if export_choice == "Latest Research Output":
                    latest_msg = assistant_messages[-1]
                    export_content = latest_msg["content"]
                    export_citations = latest_msg.get("citations", [])
                    export_prov = latest_msg.get("provider_info", "")
                else:
                    sections = []
                    all_cites = []
                    for idx, m in enumerate(st.session_state.get("messages", []), 1):
                        role_str = "Researcher Question" if m["role"] == "user" else "MSRA Analysis"
                        sections.append(f"### {role_str}\n{m['content']}")
                        if m.get("citations"):
                            all_cites.extend(m["citations"])
                    export_content = "\n\n".join(sections)
                    export_citations = all_cites
                    export_prov = "MSRA Modular Smart Research Assistant"

                try:
                    pdf_bytes = export_to_pdf(
                        title=report_title,
                        content=export_content,
                        topic=st.session_state.get("research_topic", ""),
                        citations=export_citations,
                        provider_info=export_prov
                    )
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"MSRA_Research_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="btn_download_exported_pdf",
                        type="primary",
                        use_container_width=True
                    )
                except Exception as export_err:
                    safe_log("Panel PDF export generation failed", export_err)
                    st.error(f"Failed to generate PDF: {export_err}")


# ------------------------------------------------------------------------------
# 8. TOP-LEVEL WORKSPACE EXECUTION FLOW
# ------------------------------------------------------------------------------
with st.container(key="chat_history_container"):
    render_chat_history()

with st.container(key="fixed_research_tools"):
    render_research_tools_panel()

render_chat_input()

# Process pending queries at the top level
process_pending()
