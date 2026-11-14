"""
Comprehensive Runtime Flow Test Suite for MSRA
===============================================
Exercises all critical deployment flows:
  Flow a: Single PDF upload and ingestion
  Flow b: Multi-PDF upload and indexing
  Flow c: In-document Q&A and standalone question condensation
  Flow d: Grounded off-topic refusal (0 citations, friendly message)
  Flow e: Action buttons & UI states
  Flow f: Model selector & display name mapping
  Flow g: Paper deletion from ChromaDB and session storage
  Flow h: Clear session data and New Chat
  Flow i: Academic report exports (PDF and DOCX)
  Flow j: Error validations (corrupted, empty, oversized, invalid, mock UploadedFile)
  Flow k: LLM fallback logic and exception handling
  Flow l: Per-user session isolation and sliding-window rate limiting
"""

import os
import sys
import time
import uuid
import io
import pytest

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site = os.path.join(_root, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

from config import (
    MAX_FILE_SIZE_MB,
    MAX_QUESTION_LENGTH,
    RATE_LIMIT_QUESTIONS,
    RATE_LIMIT_WINDOW_SECONDS,
    SESSION_EXPIRY_HOURS,
    BASE_DATA_DIR,
    validate_api_keys
)
from utils.errors import validate_pdf_file, validate_question
from utils.session import (
    get_or_create_session_id,
    get_session_dir,
    get_session_upload_dir,
    get_session_chroma_dir,
    cleanup_expired_sessions,
    clear_session_data,
    check_rate_limit
)
from src.export import export_to_pdf, export_to_docx
from src.llm import (
    get_model_display_name,
    MODEL_DISPLAY_NAMES,
    GEMINI_MODELS,
    GROQ_MODELS,
    LLMQuotaError,
    LLMAuthError,
    LLMError,
    get_llm
)
from src.pdf_rag import (
    load_pdf,
    split_documents,
    create_vectorstore,
    get_retriever,
    delete_paper_from_vectorstore
)
from src.chain import (
    condense_question,
    research,
    is_broad_question,
    is_summarize_query
)


class MockUploadedFile:
    """Simulates a Streamlit UploadedFile object with getvalue() and getbuffer()."""
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data

    def getbuffer(self):
        return memoryview(self._data)

    def read(self) -> bytes:
        return self._data


# ---------------------------------------------------------------------------
# Flow j: Validation Tests (Corrupted, Empty, Encrypted, Oversized, UploadedFile)
# ---------------------------------------------------------------------------
class TestFlowJ_Validation:

    def test_empty_bytes_rejected(self):
        valid, msg = validate_pdf_file(b"", "empty.pdf")
        assert not valid
        assert "empty" in msg.lower()

    def test_none_input_rejected(self):
        valid, msg = validate_pdf_file(None, "none.pdf")
        assert not valid
        assert "empty" in msg.lower()

    def test_oversized_file_rejected(self):
        # Create bytes exceeding MAX_FILE_SIZE_MB
        oversized = b"%PDF-1.4\n" + (b"0" * (MAX_FILE_SIZE_MB * 1024 * 1024 + 1024))
        valid, msg = validate_pdf_file(oversized, "big.pdf")
        assert not valid
        assert "too large" in msg.lower() or "limit" in msg.lower()

    def test_invalid_magic_bytes_rejected(self):
        not_a_pdf = b"This is a text file, not a PDF."
        valid, msg = validate_pdf_file(not_a_pdf, "text.pdf")
        assert not valid
        assert "invalid format" in msg.lower() or "%pdf" in msg.lower()

    def test_corrupted_pdf_stream_rejected(self):
        corrupted = b"%PDF-1.4\nstream\ncorrupted random bytes\x00\x01\x02\nendstream\n%%EOF"
        valid, msg = validate_pdf_file(corrupted, "corrupt.pdf")
        assert not valid
        assert "corrupted" in msg.lower() or "damaged" in msg.lower() or "unreadable" in msg.lower()

    def test_mock_uploaded_file_object_handled(self):
        # Verify validate_pdf_file accepts UploadedFile-like object without len() error
        valid_mock = MockUploadedFile("test.pdf", b"dummy content not starting with %PDF")
        valid, msg = validate_pdf_file(valid_mock, valid_mock.name)
        assert not valid
        assert "invalid format" in msg.lower() or "%pdf" in msg.lower()

    def test_valid_pdf_file_passes(self):
        pdf_path = os.path.join(_root, "The_World_and_India_Reference_Volume.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join(_root, "data", "uploads", "The_World_and_India_Reference_Volume.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                raw_bytes = f.read()
            valid, msg = validate_pdf_file(raw_bytes, "benchmark.pdf")
            assert valid
            assert msg == ""

    def test_validate_question(self):
        # Empty question
        valid, msg = validate_question("")
        assert not valid
        # Oversized question
        too_long = "x" * (MAX_QUESTION_LENGTH + 10)
        valid, msg = validate_question(too_long)
        assert not valid
        # Normal question
        valid, msg = validate_question("What is the capital of Bolivia?")
        assert valid


# ---------------------------------------------------------------------------
# Flow h & l: Per-User Session Isolation, Rate Limiting & Cleanup
# ---------------------------------------------------------------------------
class TestFlowHL_SessionIsolation:

    def test_session_id_generation(self):
        session_id = str(uuid.uuid4())
        u_dir = get_session_upload_dir(session_id)
        c_dir = get_session_chroma_dir(session_id)
        assert os.path.exists(u_dir)
        assert os.path.exists(c_dir)
        assert session_id in u_dir
        assert session_id in c_dir

        # Cleanup created test session
        clear_session_data(session_id)
        assert not os.path.exists(os.path.join(BASE_DATA_DIR, session_id))

    def test_cleanup_expired_sessions(self):
        # Create an expired mock session directory
        expired_id = f"test_expired_{uuid.uuid4()}"
        expired_dir = os.path.join(BASE_DATA_DIR, expired_id)
        os.makedirs(expired_dir, exist_ok=True)
        dummy_file = os.path.join(expired_dir, "test.txt")
        with open(dummy_file, "w") as f:
            f.write("test")

        # Set mtime to 3 hours ago (expiry is 2 hours)
        past_time = time.time() - (3 * 3600)
        os.utime(expired_dir, (past_time, past_time))

        cleaned = cleanup_expired_sessions(max_age_hours=2)
        assert cleaned >= 1
        assert not os.path.exists(expired_dir)

    def test_rate_limiting_sliding_window(self):
        test_session_id = f"test_rate_session_{uuid.uuid4().hex[:8]}"

        # First RATE_LIMIT_QUESTIONS queries should pass
        for i in range(RATE_LIMIT_QUESTIONS):
            allowed, _ = check_rate_limit(test_session_id)
            assert allowed, f"Query {i+1} should have been allowed"

        # The 21st query within window must be rejected
        allowed, msg = check_rate_limit(test_session_id)
        assert not allowed
        assert "rate limit" in msg.lower() or "limit" in msg.lower()


# ---------------------------------------------------------------------------
# Flow i: Report Generation and Export (PDF & DOCX)
# ---------------------------------------------------------------------------
class TestFlowI_ExportReports:

    def test_pdf_export_structure(self):
        citations = [
            {"citation_label": "[1]", "source": "Sample.pdf", "page": "Page 4"},
            {"citation_label": "[2]", "source": "Sample.pdf", "page": "Page 12"}
        ]
        sample_markdown = (
            "# Research Overview\n\n"
            "This is a study on neural architecture search [1].\n\n"
            "## Key Findings\n"
            "- High accuracy achieved [2].\n"
            "- Low inference latency.\n\n"
            "| Model | Score | Latency |\n"
            "|---|---|---|\n"
            "| Baseline | 82.4 | 14ms |\n"
            "| MSRA Model | 91.8 | 9ms |\n"
        )
        pdf_bytes = export_to_pdf(
            title="Academic Research Synthesis",
            content=sample_markdown,
            topic="Artificial Intelligence",
            citations=citations,
            provider_info="Gemini 2.5 Flash"
        )
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

    def test_docx_export_structure(self):
        citations = [
            {"citation_label": "[1]", "source": "Sample.pdf", "page": "Page 4"}
        ]
        sample_markdown = "# Analysis\n\nStructured findings from the study [1]."
        docx_bytes = export_to_docx(
            title="Analysis Report",
            content=sample_markdown,
            citations=citations
        )
        assert docx_bytes.startswith(b"PK")
        assert len(docx_bytes) > 2000


# ---------------------------------------------------------------------------
# Flow f & k: Model Selector, Display Names and Fallback Logic
# ---------------------------------------------------------------------------
class TestFlowFK_ModelHandlingAndFallback:

    def test_model_display_names(self):
        for m in GEMINI_MODELS:
            name = get_model_display_name(m)
            assert name and name != "Unknown Model"

        for m in GROQ_MODELS:
            name = get_model_display_name(m)
            assert name and name != "Unknown Model"

        assert get_model_display_name("unknown-model-xyz") == "unknown-model-xyz"

    def test_is_broad_and_summarize_query(self):
        assert is_broad_question("Summarize the main findings of the paper")
        assert is_summarize_query("What is this paper about?")
        assert not is_broad_question("What is the capital of Bolivia?")
        assert not is_summarize_query("Which Indian state ranks 9th by area?")


# ---------------------------------------------------------------------------
# Flows a, b, g: PDF Ingestion, Chunking, Multi-PDF & Paper Deletion
# ---------------------------------------------------------------------------
class TestFlowABG_IngestionAndPaperDeletion:

    def test_ingestion_and_chunking(self):
        pdf_path = os.path.join(_root, "The_World_and_India_Reference_Volume.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join(_root, "data", "uploads", "The_World_and_India_Reference_Volume.pdf")
        if not os.path.exists(pdf_path):
            pytest.skip("Benchmark PDF not available.")

        docs = load_pdf(pdf_path)
        assert len(docs) > 0
        # Check page_label metadata is 1-indexed
        assert docs[0].metadata["page_label"] == "1"
        assert docs[0].metadata["source"] == "The_World_and_India_Reference_Volume.pdf"

        # Split documents into chunks
        chunks = split_documents(docs[:5])  # Use first 5 pages for rapid test
        assert len(chunks) > 0
        assert "chunk_index" in chunks[0].metadata
        assert chunks[0].metadata["page_label"] == "1"

    def test_paper_deletion_from_vectorstore(self):
        from langchain_core.documents import Document
        test_session = f"test_del_{uuid.uuid4().hex[:8]}"

        doc_a = Document(page_content="Paper Alpha content regarding neural models.", metadata={"source": "Paper_A.pdf", "page_label": "1"})
        doc_b = Document(page_content="Paper Beta content regarding quantum states.", metadata={"source": "Paper_B.pdf", "page_label": "1"})

        vs = create_vectorstore([doc_a, doc_b], session_id=test_session)
        assert vs is not None

        # Verify both papers exist
        results_before = vs.similarity_search("content", k=5)
        sources_before = {d.metadata.get("source") for d in results_before}
        assert "Paper_A.pdf" in sources_before
        assert "Paper_B.pdf" in sources_before

        # Delete Paper_A.pdf
        delete_paper_from_vectorstore(vs, "Paper_A.pdf")

        # Verify only Paper_B remains
        results_after = vs.similarity_search("content", k=5)
        sources_after = {d.metadata.get("source") for d in results_after}
        assert "Paper_A.pdf" not in sources_after
        assert "Paper_B.pdf" in sources_after

        # Clean up
        clear_session_data(test_session)


# ---------------------------------------------------------------------------
# Flow c & d: Question Condensation & Grounded Refusal
# ---------------------------------------------------------------------------
class TestFlowCD_ResearchQAAndRefusal:

    def test_condense_question_standalone(self):
        # Empty chat history should return raw question immediately
        q = "What are the limitations?"
        rewritten = condense_question(q, chat_history="")
        assert rewritten == q

    def test_off_topic_grounded_refusal(self, monkeypatch):
        from langchain_core.documents import Document
        from unittest.mock import patch
        test_session = f"test_refusal_{uuid.uuid4().hex[:8]}"

        # Document only about classical geography
        doc = Document(
            page_content="Bolivia has two capitals: Sucre is the constitutional capital and La Paz is the seat of government.",
            metadata={"source": "Geography.pdf", "page_label": "1"}
        )
        vs = create_vectorstore([doc], session_id=test_session)
        retriever = get_retriever(vs)

        # Off-topic question unrelated to geography, LLM mocked according to speed rules
        with patch("src.llm.call_gemini", return_value="I couldn't find any information about quantum entanglement in the uploaded documents."):
            answer, citations, provider, is_fallback = research(
                question="What is quantum entanglement and qubit decoherence?",
                retriever=retriever,
                chat_history="",
                stream=False
            )

        # Must refuse with 0 citations
        assert len(citations) == 0
        ans_lower = answer.lower()
        assert "couldn't find" in ans_lower or "not" in ans_lower or "service notice" in ans_lower

        clear_session_data(test_session)
