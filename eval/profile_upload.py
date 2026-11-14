"""
MSRA Upload and Query Performance Profiler
==========================================
Measures precise perf_counter timings for each stage without Streamlit:
1. PDF Loading
2. Text Splitting / Chunking
3. Embedding Model Load
4. Vectorstore Creation / Embedding & Storage
5. Query Condensation / Rewriting
6. Candidate Chunk Retrieval & MMR
7. LLM Generation
8. Citation Post-processing & Source Filtering
9. Follow-up Generation
"""

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site = os.path.join(_root, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

from src.pdf_rag import load_pdf, split_documents, create_vectorstore, get_retriever, get_embeddings
from src.chain import condense_question, research, normalize_citations, filter_sources_by_citations
from utils.session import clear_session_data


PDF_FILENAME = "The_World_and_India_Reference_Volume.pdf"
PROFILE_SESSION_ID = "profile_benchmark_session"


def profile_pipeline():
    print("=" * 70)
    print("⏱️ MSRA PIPELINE PERFORMANCE PROFILER")
    print("=" * 70)

    pdf_path = os.path.abspath(PDF_FILENAME)
    if not os.path.exists(pdf_path):
        alt = os.path.join(_root, "data", "uploads", PDF_FILENAME)
        if os.path.exists(alt):
            pdf_path = alt
        else:
            print(f"Error: {PDF_FILENAME} not found.")
            return

    file_size_kb = os.path.getsize(pdf_path) / 1024
    print(f"Target PDF: {pdf_path} ({file_size_kb:.1f} KB)")
    clear_session_data(PROFILE_SESSION_ID)

    timings = {}

    # Stage 1: PDF Loading
    t0 = time.perf_counter()
    docs = load_pdf(pdf_path)
    timings["1_pdf_load"] = time.perf_counter() - t0
    print(f"[Stage 1] PDF Load: {timings['1_pdf_load']:.3f}s ({len(docs)} pages)")

    # Stage 2: Chunking
    t0 = time.perf_counter()
    chunks = split_documents(docs)
    timings["2_chunking"] = time.perf_counter() - t0
    print(f"[Stage 2] Chunking: {timings['2_chunking']:.3f}s ({len(chunks)} chunks)")

    # Stage 3: Embedding Model Load
    t0 = time.perf_counter()
    emb = get_embeddings()
    timings["3_embed_model_load"] = time.perf_counter() - t0
    print(f"[Stage 3] Embedding Model Load: {timings['3_embed_model_load']:.3f}s")

    # Stage 4: Embedding generation & ChromaDB Write
    t0 = time.perf_counter()
    vs = create_vectorstore(chunks, session_id=PROFILE_SESSION_ID)
    retriever = get_retriever(vs)
    timings["4_chroma_embed_and_write"] = time.perf_counter() - t0
    print(f"[Stage 4] ChromaDB Index & Embed: {timings['4_chroma_embed_and_write']:.3f}s")

    total_upload_time = (
        timings["1_pdf_load"] + timings["2_chunking"] +
        timings["3_embed_model_load"] + timings["4_chroma_embed_and_write"]
    )
    print(f"\n📊 TOTAL INGESTION / UPLOAD TIME: {total_upload_time:.3f}s\n")

    # Stage 5: Query Condensation
    test_question = "What is the capital of Bolivia?"
    t0 = time.perf_counter()
    # With empty history, this should be instantaneous
    condensed_q = condense_question(test_question, chat_history="")
    timings["5_query_condense_empty_history"] = time.perf_counter() - t0
    print(f"[Stage 5] Query Condensation (empty history): {timings['5_query_condense_empty_history']:.5f}s")

    # Stage 6: Retrieval
    t0 = time.perf_counter()
    retrieved_docs = vs.similarity_search(condensed_q, k=8)
    timings["6_retrieval_k8"] = time.perf_counter() - t0
    print(f"[Stage 6] Similarity Search (k=8): {timings['6_retrieval_k8']:.3f}s ({len(retrieved_docs)} docs)")

    # Stage 7: End-to-End Research Call (includes offline fallback handling)
    t0 = time.perf_counter()
    answer, citations, provider, is_fb = research(
        question=test_question,
        retriever=retriever,
        chat_history="",
        stream=False
    )
    timings["7_research_call"] = time.perf_counter() - t0
    print(f"[Stage 7] Research Query Flow: {timings['7_research_call']:.3f}s (Provider: {provider})")
    print(f"         Citations: {len(citations)}")
    print(f"         Answer prefix: {answer[:120].strip()}...")

    # Stage 8: Normalization & Sources Filtering
    t0 = time.perf_counter()
    norm_text, cited_ids = normalize_citations(answer, valid_ids={1, 2, 3})
    filtered_sources = filter_sources_by_citations(citations, cited_ids)
    timings["8_citation_post_process"] = time.perf_counter() - t0
    print(f"[Stage 8] Citation Normalization & Filtering: {timings['8_citation_post_process']:.5f}s")

    print("\n" + "=" * 70)
    print("PROFILING COMPLETED SUCCESSFULLY")
    print("=" * 70)

    clear_session_data(PROFILE_SESSION_ID)
    return timings


if __name__ == "__main__":
    profile_pipeline()
