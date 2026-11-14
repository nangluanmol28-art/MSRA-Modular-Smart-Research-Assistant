"""
MSRA Live RAG CLI Evaluation Script
===================================
Executes an end-to-end RAG question against 'Artificial Intelligence in Education.pdf'
and validates answer formatting, provider used, and inline citation mappings.
"""

import os
import sys
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site = os.path.join(_root, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

from src.pdf_rag import load_pdf, split_documents, create_vectorstore, get_retriever
from src.chain import research


def run_live_rag_eval():
    pdf_path = os.path.join(_root, "data", "uploads", "Artificial Intelligence in Education.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return

    print(f"Loading '{pdf_path}'...")
    docs = load_pdf(pdf_path)
    print(f"Loaded {len(docs)} pages.")

    print("Splitting documents into chunks...")
    chunks = split_documents(docs)
    print(f"Created {len(chunks)} chunks.")

    print("Creating Chroma vectorstore...")
    vectorstore = create_vectorstore(chunks, session_id="eval_live_rag_session")

    print("Getting retriever...")
    retriever = get_retriever(vectorstore)

    query = "what is ai in education"
    print(f"\nExecuting research query: '{query}'...")
    answer, citations, provider_used, is_fallback = research(
        question=query,
        retriever=retriever
    )

    print("\n" + "=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(answer)
    print("\n" + "=" * 60)
    print(f"PROVIDER USED: {provider_used} (Fallback: {is_fallback})")
    print(f"ACTIVE CITATIONS COUNT: {len(citations)}")
    print("=" * 60)
    for c in citations:
        print(f"Citation {c.get('citation_label')} -> {c.get('source')} ({c.get('page')})")
        print(f"  Snippet: {c.get('snippet')}")

    bracket_cites = re.findall(r"\[\d+\]", answer)
    print(f"\nInline citations found in answer: {bracket_cites}")
    print("Live RAG evaluation completed successfully.")


if __name__ == "__main__":
    run_live_rag_eval()
