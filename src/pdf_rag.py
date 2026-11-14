import os
import sys

# Auto-link project virtualenv site-packages if running outside venv
_proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_venv_site = os.path.join(_proj_dir, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

# Prevent Windows Application Control DLL load failure on gRPC telemetry and avoid HF network checks
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

try:
    import grpc  # noqa: F401
except (ImportError, OSError):
    from unittest.mock import MagicMock
    _grpc_mock = MagicMock()
    _grpc_mock.__version__ = "1.60.0"
    sys.modules["grpc"] = _grpc_mock
    sys.modules["grpc._cython"] = _grpc_mock
    sys.modules["grpc._cython.cygrpc"] = _grpc_mock

import pypdf
from langchain_core.documents import Document

# Embeddings loader with optional Streamlit caching
_cached_embeddings_instance = None


def _load_embeddings():
    """Initializes HuggingFace sentence transformer embeddings with batch_size=64, local cache, and resilient fallbacks."""
    encode_kwargs = {"batch_size": 64, "normalize_embeddings": True}

    # Attempt 1: Standard langchain_huggingface with local files only
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"local_files_only": True},
            encode_kwargs=encode_kwargs
        )
    except Exception:
        pass

    # Attempt 2: langchain_huggingface without local_files_only
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            encode_kwargs=encode_kwargs
        )
    except Exception:
        pass

    # Attempt 3: Direct SentenceTransformer instance wrapper (zero langchain_huggingface dependency)
    try:
        from sentence_transformers import SentenceTransformer
        st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        class DirectSentenceTransformerEmbeddings:
            def __init__(self, model):
                self.model = model

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                if not texts:
                    return []
                clean_texts = [x.replace("\n", " ") for x in texts]
                return self.model.encode(clean_texts, batch_size=64, normalize_embeddings=True).tolist()

            def embed_query(self, text: str) -> list[float]:
                clean_text = text.replace("\n", " ")
                return self.model.encode([clean_text], normalize_embeddings=True)[0].tolist()

        return DirectSentenceTransformerEmbeddings(st_model)
    except Exception as e3:
        raise ImportError(
            f"Failed to load sentence_transformers embeddings: {e3}. "
            "Please activate your virtual environment: '.\\.myenv\\Scripts\\Activate.ps1'"
        ) from e3


try:
    import streamlit as st
    @st.cache_resource(show_spinner=False)
    def get_embeddings():
        return _load_embeddings()
except Exception:
    def get_embeddings():
        global _cached_embeddings_instance
        if _cached_embeddings_instance is None:
            _cached_embeddings_instance = _load_embeddings()
        return _cached_embeddings_instance


class _LazyEmbeddings:
    """Lazy proxy so importing pdf_rag does not block on model initialization."""
    def __init__(self):
        self._inst = None

    def _get_instance(self):
        if self._inst is None:
            self._inst = get_embeddings()
        return self._inst

    def embed_documents(self, texts):
        return self._get_instance().embed_documents(texts)

    def embed_query(self, text):
        return self._get_instance().embed_query(text)

    def __getattr__(self, name):
        return getattr(self._get_instance(), name)


# For backward compatibility without import-time freeze
embeddings = _LazyEmbeddings()


def load_pdf(pdf_path: str, file_hash: str = ""):
    """
    Loads and normalizes metadata for an uploaded PDF paper.
    Preserves 1-indexed page_label and attaches file_hash.
    """
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        return []
    documents = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        filename = os.path.basename(pdf_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            metadata = {
                "source": filename,
                "page": i,
                "page_label": str(i + 1)
            }
            if file_hash:
                metadata["file_hash"] = file_hash
            documents.append(Document(page_content=text, metadata=metadata))
    except Exception as e:
        print(f"Warning: Failed to load '{pdf_path}': {e}")
        return []

    return documents


def _split_text_recursively(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """Pure-Python recursive chunk splitter with paragraph and sentence preservation without external torch/hf dependencies."""
    if not text:
        return []
    separators = ["\n\n\n", "\n\n", "\n", ". ", " ", ""]

    def _split(t: str, seps: list[str]) -> list[str]:
        if len(t) <= chunk_size or not seps:
            return [t] if t.strip() else []
        sep = seps[0]
        parts = t.split(sep) if sep else list(t)
        chunks = []
        cur = ""
        for p in parts:
            piece = p + (sep if sep else "")
            if len(cur) + len(piece) <= chunk_size:
                cur += piece
            else:
                if cur.strip():
                    chunks.append(cur.strip())
                if len(piece) > chunk_size and len(seps) > 1:
                    chunks.extend(_split(piece, seps[1:]))
                    cur = ""
                else:
                    cur = piece
        if cur.strip():
            chunks.append(cur.strip())
        return chunks

    raw = _split(text, separators)
    if chunk_overlap <= 0 or len(raw) <= 1:
        return raw

    result = []
    for i, piece in enumerate(raw):
        if i > 0 and chunk_overlap > 0:
            prev = raw[i - 1]
            overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            combined = overlap_text + " " + piece
            if len(combined) <= chunk_size + chunk_overlap:
                result.append(combined)
            else:
                result.append(piece)
        else:
            result.append(piece)
    return result


def split_documents(documents, file_hash: str = ""):
    """
    Splits documents into overlapping chunks using paragraph & section boundaries first.
    """
    if not documents:
        return []
    chunks = []
    chunk_counter = 0
    for doc in documents:
        text = doc.page_content or ""
        splits = _split_text_recursively(text, chunk_size=1000, chunk_overlap=150)
        for s in splits:
            meta = dict(doc.metadata)
            meta["chunk_index"] = chunk_counter
            if file_hash:
                meta["file_hash"] = file_hash
            elif "file_hash" not in meta and "file_hash" in documents[0].metadata:
                meta["file_hash"] = documents[0].metadata.get("file_hash", "")
            chunk_counter += 1
            chunks.append(Document(page_content=s, metadata=meta))

    return chunks


def get_or_create_vectorstore(session_id: str = None):
    """
    Initializes or retrieves an isolated Chroma collection for a session.
    Avoids recreating or clobbering collections on each upload.
    """
    from langchain_chroma import Chroma
    emb = get_embeddings()
    persist_dir = None
    collection_name = "msra_research"

    if session_id:
        from utils.session import get_session_chroma_dir
        persist_dir = get_session_chroma_dir(session_id)
        clean_id = session_id.replace("-", "")[:24]
        collection_name = f"msra_{clean_id}"

    return Chroma(
        collection_name=collection_name,
        embedding_function=emb,
        persist_directory=persist_dir
    )


def add_chunks_to_vectorstore(vectorstore, chunks, batch_size: int = 64, progress_callback=None):
    """
    Adds document chunks to Chroma in batches of ~64 with optional progress callback.
    """
    if vectorstore is None or not chunks:
        return
    total = len(chunks)
    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        vectorstore.add_documents(batch)
        if progress_callback:
            pct = min(100, int((i + len(batch)) / total * 100))
            progress_callback(pct)


def create_vectorstore(chunks, session_id: str = None):
    """
    Creates or updates an isolated Chroma vectorstore for the given session.
    Maintains full backward compatibility.
    """
    if not chunks:
        return None
    vs = get_or_create_vectorstore(session_id=session_id)
    add_chunks_to_vectorstore(vs, chunks, batch_size=64)
    return vs


def delete_paper_from_vectorstore(vectorstore, filename: str = None, file_hash: str = None):
    """
    Removes all chunks associated with a specific paper from ChromaDB using hash or filename.
    """
    if vectorstore is None:
        return
    try:
        if file_hash:
            vectorstore.delete(where={"file_hash": file_hash})
        elif filename:
            vectorstore.delete(where={"source": filename})
    except Exception as e:
        print(f"Notice: Failed to delete chunks: {e}")


def get_retriever(vectorstore):
    """
    Creates an MMR retriever with k=8, fetch_k=20 for diverse, high-relevance chunk retrieval.
    """
    if vectorstore is None:
        return None
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 8, "fetch_k": 20, "lambda_mult": 0.5}
    )
    return retriever


def has_ready_papers(indexed_papers: dict, vectorstore) -> bool:
    """
    Single source of truth helper: Returns True if session has at least one indexed paper and a live vectorstore.
    """
    return bool(indexed_papers) and (vectorstore is not None)


# Backwards compatibility alias
get_retiever = get_retriever
