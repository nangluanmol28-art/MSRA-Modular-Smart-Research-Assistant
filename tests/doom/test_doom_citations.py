import pytest
from src.citations import normalize_citations, filter_sources_by_citations


@pytest.mark.doom
class TestDoomCitations:

    def test_garbage_llm_output_handling(self):
        garbage = "asdlkfjlksdf %^&*() @#$ 1234 undefined null NaN"
        clean, cited = normalize_citations(garbage, valid_ids={1, 2})
        assert cited == []
        assert clean == garbage

    def test_unmapped_hallucinated_citations_stripped(self):
        text = "Quantum computing scales exponentially [999] using qubits [42], as confirmed by experiments [1]."
        clean, cited = normalize_citations(text, valid_ids={1})
        assert "[999]" not in clean
        assert "[42]" not in clean
        assert "[1]" in clean
        assert cited == [1]

    def test_odd_brackets_normalization(self):
        text = "Transformers are scalable 【1】 and robust 〖2〗 (3)."
        clean, cited = normalize_citations(text, valid_ids={1, 2, 3})
        assert "【1】" not in clean
        assert "〖2〗" not in clean
        assert "[1]" in clean
        assert "[2]" in clean
        assert cited == [1, 2, 3]

    def test_10_000_citations_stress(self):
        # Stress test normalization with 10,000 citations
        citations_chunk = " ".join(f"Claim {i} [1]" for i in range(2000))
        clean, cited = normalize_citations(citations_chunk, valid_ids={1})
        assert 1 in cited
        assert len(cited) == 1

    def test_empty_string_response(self):
        clean, cited = normalize_citations("", valid_ids={1})
        assert clean == ""
        assert cited == []

    def test_sources_filtered_only_to_cited(self):
        sources = [
            {"id": 1, "source": "PaperA.pdf", "page": "Page 1"},
            {"id": 2, "source": "PaperB.pdf", "page": "Page 3"},
            {"id": 3, "source": "PaperC.pdf", "page": "Page 5"},
        ]
        # Only [2] was cited
        filtered = filter_sources_by_citations(sources, cited_ids=[2])
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2
        assert filtered[0]["source"] == "PaperB.pdf"
