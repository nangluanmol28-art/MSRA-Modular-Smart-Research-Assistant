import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from src.chain import (
    generate_paper_summary,
    generate_paper_comparison,
    detect_research_gaps
)
from src.export import export_to_pdf


@pytest.fixture
def sample_documents():
    return [
        Document(
            page_content="Deep learning in medical diagnostics shows 94% accuracy on chest X-rays. The model uses CNNs.",
            metadata={"source": "Paper_A.pdf", "page": 0, "page_label": "1"}
        ),
        Document(
            page_content="Limitations include high computational overhead and reliance on labeled data.",
            metadata={"source": "Paper_A.pdf", "page": 1, "page_label": "2"}
        ),
        Document(
            page_content="Vision Transformers achieve 96.5% accuracy but require 10x more training data and lack interpretability.",
            metadata={"source": "Paper_B.pdf", "page": 0, "page_label": "1"}
        ),
        Document(
            page_content="Future work will explore self-supervised pretraining for low-resource clinics.",
            metadata={"source": "Paper_B.pdf", "page": 2, "page_label": "3"}
        )
    ]


class TestFeature1PaperSummarization:
    def test_summary_empty_docs(self):
        result, citations, provider, is_fallback = generate_paper_summary([])
        assert "No document content" in result
        assert citations == []

    @patch("src.chain.get_llm")
    def test_summary_single_paper(self, mock_llm, sample_documents):
        mock_llm.return_value = (
            "### 1. Paper Overview\nCNN diagnostics [1].\n\n### 2. Research Problem\nDetect disease [1].\n\n### 8. Limitations\nRequires compute [2].",
            "Google Gemini",
            False
        )
        result, citations, provider, is_fallback = generate_paper_summary(
            sample_documents,
            target_filename="Paper_A.pdf",
            provider="Google Gemini"
        )
        assert "Paper Overview" in result
        assert len(citations) > 0
        assert citations[0]["source"] == "Paper_A.pdf"
        assert provider == "Google Gemini"
        assert is_fallback is False


class TestFeature2MultiPaperComparison:
    def test_comparison_requires_at_least_two_papers(self, sample_documents):
        result, citations, provider, is_fallback = generate_paper_comparison(
            sample_documents,
            selected_filenames=["Paper_A.pdf"]
        )
        assert "at least two uploaded research papers" in result
        assert citations == []

    @patch("src.chain.get_llm")
    def test_comparison_two_papers(self, mock_llm, sample_documents):
        mock_llm.return_value = (
            "### 1. Comparative Analysis Matrix\n| Dimension | Paper_A | Paper_B |\n|---|---|---|\n| **1. Research Problem** | CNN [1] | ViT [2] |\n\n### 2. Key Similarities\nBoth focus on vision [1][2].",
            "Groq",
            False
        )
        result, citations, provider, is_fallback = generate_paper_comparison(
            sample_documents,
            selected_filenames=["Paper_A.pdf", "Paper_B.pdf"],
            provider="Groq"
        )
        assert "Comparative Analysis Matrix" in result
        assert len(citations) >= 2
        assert provider == "Groq"


class TestFeature3ResearchGapDetection:
    def test_gap_detection_empty_docs(self):
        result, citations, provider, is_fallback = detect_research_gaps([])
        assert "No document content" in result
        assert citations == []

    @patch("src.chain.get_llm")
    def test_gap_detection_multi_papers(self, mock_llm, sample_documents):
        mock_llm.return_value = (
            "### 1. Identified Research Gaps\nData scarcity [1].\n\n### 2. Existing Limitations (Author-Stated)\nCompute overhead [2].\n\n### 5. Potential Research Opportunities (Inferred)\nSelf-supervised methods [3].",
            "Google Gemini",
            False
        )
        result, citations, provider, is_fallback = detect_research_gaps(
            sample_documents,
            selected_filenames=["Paper_A.pdf", "Paper_B.pdf"],
            provider="Google Gemini"
        )
        assert "Identified Research Gaps" in result
        assert "Existing Limitations (Author-Stated)" in result
        assert len(citations) >= 2


class TestFeature4ExportToPDF:
    def test_export_pdf_basic(self):
        content = (
            "### 1. Paper Overview\n"
            "This paper introduces medical image classification using CNNs [1].\n\n"
            "### 2. Research Problem\n"
            "Manual diagnostics suffer from high error rates [2]."
        )
        citations = [
            {"id": 1, "citation_label": "[1]", "source": "Paper_A.pdf", "page": "Page 1", "snippet": "Deep learning..."},
            {"id": 2, "citation_label": "[2]", "source": "Paper_A.pdf", "page": "Page 2", "snippet": "Manual errors..."}
        ]
        pdf_bytes = export_to_pdf(
            title="MSRA Academic Paper Summary",
            content=content,
            topic="Medical AI",
            citations=citations,
            provider_info="Google Gemini"
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")

    def test_export_pdf_with_table(self):
        content = (
            "### 1. Comparative Analysis Matrix\n\n"
            "| Dimension | Paper A | Paper B |\n"
            "|---|---|---|\n"
            "| **Research Problem** | Chest X-ray [1] | Vision Transformers [2] |\n"
            "| **Accuracy** | 94% [1] | 96.5% [2] |\n\n"
            "### 2. Key Similarities\n"
            "- Both apply deep learning [1][2]."
        )
        pdf_bytes = export_to_pdf(
            title="MSRA Multi-Paper Comparison Report",
            content=content,
            topic="Deep Learning Models"
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
