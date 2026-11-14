"""
MSRA Question-Answering Quality & Multi-Turn Benchmark
======================================================
Tests multi-turn follow-up question answering, contextual condensation,
and citation tracking against 'Artificial Intelligence in Education.pdf'.
"""

import os
import sys

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


def run_quality_tests():
    pdf_path = os.path.join(_root, "data", "uploads", "Artificial Intelligence in Education.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: Target PDF not found at {pdf_path}")
        return

    print(f"Loading '{pdf_path}'...")
    docs = load_pdf(pdf_path)
    chunks = split_documents(docs)
    vectorstore = create_vectorstore(chunks, session_id="eval_qa_quality_session")
    retriever = get_retriever(vectorstore)

    results = {}

    # Question A
    print("\n" + "=" * 65)
    print("TEST A: 'what is ai in education'")
    print("=" * 65)
    ans_a, cites_a, prov_a, fb_a = research(
        question="what is ai in education",
        retriever=retriever,
        chat_history=""
    )
    print("ANSWER A:\n", ans_a)
    print(f"\nProvider: {prov_a} | Citations: {len(cites_a)}")
    results["a"] = {"answer": ans_a, "citations": cites_a, "provider": prov_a}

    # Question B: Follow-up
    print("\n" + "=" * 65)
    print("TEST B: 'what are the challenges?' (Follow-up to Test A)")
    print("=" * 65)
    history_b = f"User: what is ai in education\nAssistant: {ans_a}"
    ans_b, cites_b, prov_b, fb_b = research(
        question="what are the challenges?",
        retriever=retriever,
        chat_history=history_b
    )
    print("ANSWER B:\n", ans_b)
    print(f"\nProvider: {prov_b} | Citations: {len(cites_b)}")
    results["b"] = {"answer": ans_b, "citations": cites_b, "provider": prov_b}

    print("\n" + "=" * 65)
    print("Q&A QUALITY EVALUATION COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    run_quality_tests()
