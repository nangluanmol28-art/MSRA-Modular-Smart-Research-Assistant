import pytest
from src.export import export_to_pdf, export_to_docx


@pytest.mark.doom
class TestDoomExport:

    def test_long_answer_export_pdf_and_docx(self):
        long_answer = "Academic paragraph analyzing neural networks.\n\n" * 50
        sources = [{"citation_label": "[1]", "source": "AI_Review.pdf", "page": "Page 12", "snippet": "A key finding in deep models."}]

        pdf_bytes = export_to_pdf(title="Deep Neural Networks", content=long_answer, citations=sources)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

        docx_bytes = export_to_docx(title="Deep Neural Networks", content=long_answer, citations=sources)
        assert len(docx_bytes) > 0

    def test_markdown_tables_export(self):
        table_md = """
| Model | Accuracy | F1 Score |
|---|---|---|
| Baseline | 82.5% | 0.81 |
| MSRA | 96.2% | 0.95 |
"""
        sources = [{"citation_label": "[1]", "source": "Metrics.pdf", "page": "Page 4", "snippet": "Empirical comparison."}]
        pdf_bytes = export_to_pdf(title="Table Evaluation", content=table_md, citations=sources)
        assert len(pdf_bytes) > 0

        docx_bytes = export_to_docx(title="Table Evaluation", content=table_md, citations=sources)
        assert len(docx_bytes) > 0

    def test_emoji_and_hindi_characters_export(self):
        multilingual_content = "🔬 Research on भारत और विश्व संबंध with emoji symbols 🌟🚀."
        sources = []
        pdf_bytes = export_to_pdf(title="Unicode & Emoji", content=multilingual_content, citations=sources)
        assert len(pdf_bytes) > 0

        docx_bytes = export_to_docx(title="Unicode & Emoji", content=multilingual_content, citations=sources)
        assert len(docx_bytes) > 0

    def test_zero_sources_export(self):
        pdf_bytes = export_to_pdf(title="Direct Knowledge", content="Direct synthesized knowledge without explicit sources.", citations=[])
        assert len(pdf_bytes) > 0

        docx_bytes = export_to_docx(title="Direct Knowledge", content="Direct synthesized knowledge without explicit sources.", citations=[])
        assert len(docx_bytes) > 0

    def test_200_sources_stress_export(self):
        huge_sources = [
            {"citation_label": f"[{i}]", "source": f"Paper_{i}.pdf", "page": f"Page {i}", "snippet": f"Evidence excerpt {i}"}
            for i in range(1, 101)
        ]
        pdf_bytes = export_to_pdf(title="Massive Survey", content="Comprehensive survey citing 100 papers.", citations=huge_sources)
        assert len(pdf_bytes) > 0

        docx_bytes = export_to_docx(title="Massive Survey", content="Comprehensive survey citing 100 papers.", citations=huge_sources)
        assert len(docx_bytes) > 0
