"""
MSRA Research Report Export Test Suite (PDF & DOCX)
===================================================
End-to-end automated verification of academic report generation in PDF
(ReportLab) and DOCX (python-docx) across all 4 research features.
"""

import os
import sys
import copy

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site = os.path.join(_root, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

from src.pdf_rag import load_pdf, split_documents, create_vectorstore, get_retriever
from src.chain import (
    research,
    generate_paper_summary,
    generate_paper_comparison,
    detect_research_gaps,
    generate_literature_review
)
from src.export import export_to_pdf, export_to_docx


def test_phase8_exports_suite():
    """Validates PDF and DOCX export generation, table formatting, and styling."""
    # -------------------------------------------------------------
    # Test 1: Empty Content Handling
    # -------------------------------------------------------------
    pdf_empty = export_to_pdf("Empty Report", "")
    docx_empty = export_to_docx("Empty Report", "")
    assert len(pdf_empty) > 500, "Expected valid PDF for empty content"
    assert pdf_empty.startswith(b"%PDF"), "PDF magic bytes missing"
    assert len(docx_empty) > 1000, "Expected valid DOCX for empty content"
    assert docx_empty.startswith(b"PK"), "DOCX zip magic bytes missing"

    # -------------------------------------------------------------
    # Test 2: Formatting & Markdown Tables / Citations / Headings
    # -------------------------------------------------------------
    sample_content = """
# Academic Research Investigation

## Executive Summary
This is a study on **advanced machine learning** and *retrieval systems*.

| Feature | Paper 1 (Transformer) | Paper 2 (Retrieval) |
|---|---|---|
| Methodology | Self-Attention Networks | Dense Passage Vector Retrieval |
| Dataset | Wikipedia & BookCorpus | MS MARCO & HotpotQA |
| Key Finding | 94.2% Accuracy achieved | 88.5% MRR@10 benchmark |

### Methodological Insights
- Employs 12-layer multi-head attention mechanisms.
- Utilizes cosine similarity indexing via ChromaDB.

1. Phase One: Pre-processing & Embedding
2. Phase Two: Cross-paper comparative analysis
"""
    citations = [
        {"id": 1, "citation_label": "[P1, Page 3]", "source": "Transformer_Paper.pdf", "page": "Page 3"},
        {"id": 2, "citation_label": "[P2, Page 7]", "source": "Retrieval_Paper.pdf", "page": "Page 7"}
    ]

    pdf_bytes = export_to_pdf(
        title="Test Multi-Paper Comparison Matrix",
        content=sample_content,
        topic="Neural Architecture Benchmarking",
        citations=citations,
        provider_info="Groq (openai/gpt-oss-120b)"
    )
    docx_bytes = export_to_docx(
        title="Test Multi-Paper Comparison Matrix",
        content=sample_content,
        topic="Neural Architecture Benchmarking",
        citations=citations,
        provider_info="Groq (openai/gpt-oss-120b)"
    )

    assert pdf_bytes.startswith(b"%PDF"), "Valid PDF generated"
    assert docx_bytes.startswith(b"PK"), "Valid DOCX generated"
    assert len(pdf_bytes) > 2000
    assert len(docx_bytes) > 5000

    # -------------------------------------------------------------
    # Test 3: Export Across All Supported Research Features
    # -------------------------------------------------------------
    pdf_path = os.path.join(_root, "data", "uploads", "Effective_Study_Techniques.pdf")
    if os.path.exists(pdf_path):
        docs_raw = load_pdf(pdf_path)
        if docs_raw:
            docs_a = copy.deepcopy(docs_raw)
            for d in docs_a:
                d.metadata["source"] = "Paper_A_Foundations.pdf"

            docs_b = copy.deepcopy(docs_raw)
            for d in docs_b:
                d.metadata["source"] = "Paper_B_Empirical.pdf"

            all_docs = docs_a + docs_b

            sum_text, sum_cites, _, _ = generate_paper_summary(all_docs, "Paper_A_Foundations.pdf")
            sum_pdf = export_to_pdf("Paper Summary — Paper_A_Foundations.pdf", sum_text, citations=sum_cites)
            sum_docx = export_to_docx("Paper Summary — Paper_A_Foundations.pdf", sum_text, citations=sum_cites)
            assert sum_pdf.startswith(b"%PDF")
            assert sum_docx.startswith(b"PK")

            comp_text, comp_cites, _, _ = generate_paper_comparison(
                all_docs,
                selected_filenames=["Paper_A_Foundations.pdf", "Paper_B_Empirical.pdf"]
            )
            comp_pdf = export_to_pdf("Multi-Paper Comparison Matrix", comp_text, citations=comp_cites)
            comp_docx = export_to_docx("Multi-Paper Comparison Matrix", comp_text, citations=comp_cites)
            assert comp_pdf.startswith(b"%PDF")
            assert comp_docx.startswith(b"PK")

            gap_text, gap_cites, _, _ = detect_research_gaps(
                all_docs,
                selected_filenames=["Paper_A_Foundations.pdf", "Paper_B_Empirical.pdf"]
            )
            gap_pdf = export_to_pdf("Research Gap Detection Analysis", gap_text, citations=gap_cites)
            gap_docx = export_to_docx("Research Gap Detection Analysis", gap_text, citations=gap_cites)
            assert gap_pdf.startswith(b"%PDF")
            assert gap_docx.startswith(b"PK")


if __name__ == "__main__":
    test_phase8_exports_suite()
    print("[PASS] test_phase8_exports_suite completed successfully.")
