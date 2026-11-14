"""
Unit Tests for MSRA Citation Engine & Source Filtering
=====================================================
Tests citation normalization, bracket cleaning, whitespace fixing,
unmapped citation removal, and source dropdown filtering.
"""

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site = os.path.join(_root, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

import pytest
from src.citations import (
    normalize_citations,
    filter_sources_by_citations,
    generate_snippet
)


class TestCitationNormalization:
    """Tests for normalize_citations()."""

    def test_standard_bracket_preservation(self):
        text = "Transformer architecture revolutionized NLP [1]."
        cleaned, cited = normalize_citations(text, valid_ids={1, 2})
        assert "[1]." in cleaned
        assert cited == [1]

    def test_odd_bracket_normalization(self):
        # Full-width brackets 【 】, ［ ］, 〔 〕, 〖 〗
        text = "First claim 【1】. Second claim ［2］. Third claim 〔3〕. Fourth claim 〖4〗."
        cleaned, cited = normalize_citations(text, valid_ids={1, 2, 3, 4})
        assert "[1]." in cleaned
        assert "[2]." in cleaned
        assert "[3]." in cleaned
        assert "[4]." in cleaned
        assert cited == [1, 2, 3, 4]

    def test_parenthesized_citation_conversion(self):
        text = "This result was confirmed by previous studies (1)."
        cleaned, cited = normalize_citations(text, valid_ids={1})
        assert "[1]." in cleaned
        assert cited == [1]

    def test_comma_separated_citation_expansion(self):
        text = "Multiple studies support this conclusion [1, 2]."
        cleaned, cited = normalize_citations(text, valid_ids={1, 2})
        assert "[1][2]." in cleaned
        assert cited == [1, 2]

        text2 = "Three sources cite this [1, 2, 3]."
        cleaned2, cited2 = normalize_citations(text2, valid_ids={1, 2, 3})
        assert "[1][2][3]." in cleaned2
        assert cited2 == [1, 2, 3]

    def test_stray_whitespace_before_punctuation(self):
        text = "Findings demonstrate significance [2] ."
        cleaned, cited = normalize_citations(text, valid_ids={2})
        assert "[2]." in cleaned
        assert "[2] ." not in cleaned

        text_multi = "Double source reference [1][2] ."
        cleaned_m, cited_m = normalize_citations(text_multi, valid_ids={1, 2})
        assert "[1][2]." in cleaned_m

    def test_misplaced_citation_after_punctuation(self):
        text = "The model achieves high accuracy. [1]"
        cleaned, cited = normalize_citations(text, valid_ids={1})
        assert "high accuracy [1]." in cleaned

    def test_unmapped_hallucinated_citation_removal(self):
        # Chunks 1 and 2 exist, but LLM hallucinates [99] and [5]
        text = "Claim A [1]. Claim B [99]. Claim C [2][5]."
        cleaned, cited = normalize_citations(text, valid_ids={1, 2})
        assert "[1]." in cleaned
        assert "[2]." in cleaned
        assert "[99]" not in cleaned
        assert "[5]" not in cleaned
        assert cited == [1, 2]

    def test_empty_input(self):
        cleaned, cited = normalize_citations("", valid_ids={1})
        assert cleaned == ""
        assert cited == []


class TestSourceFiltering:
    """Tests for filter_sources_by_citations()."""

    @pytest.fixture
    def sample_sources(self):
        return [
            {
                "id": 1,
                "citation_label": "[1]",
                "source": "Attention_Is_All_You_Need.pdf",
                "page": "Page 3",
                "page_num": 3,
                "snippet": "The Transformer allows for significantly more parallelization..."
            },
            {
                "id": 2,
                "citation_label": "[2]",
                "source": "BERT_Paper.pdf",
                "page": "Page 5",
                "page_num": 5,
                "snippet": "BERT is designed to pre-train deep bidirectional representations..."
            },
            {
                "id": 3,
                "citation_label": "[3]",
                "source": "GPT3_Paper.pdf",
                "page": "Page 12",
                "page_num": 12,
                "snippet": "Recent work has demonstrated substantial gains on many NLP tasks..."
            }
        ]

    def test_filter_matching_citations(self, sample_sources):
        cited_ids = [2, 1]
        filtered = filter_sources_by_citations(sample_sources, cited_ids)
        assert len(filtered) == 2
        filtered_ids = [s["id"] for s in filtered]
        # Preserves ascending chunk order
        assert filtered_ids == [1, 2]

    def test_filter_single_citation(self, sample_sources):
        cited_ids = [3]
        filtered = filter_sources_by_citations(sample_sources, cited_ids)
        assert len(filtered) == 1
        assert filtered[0]["id"] == 3
        assert filtered[0]["source"] == "GPT3_Paper.pdf"

    def test_filter_empty_when_no_citations(self, sample_sources):
        filtered = filter_sources_by_citations(sample_sources, [])
        assert filtered == []

    def test_preserves_page_and_snippet_fields(self, sample_sources):
        filtered = filter_sources_by_citations(sample_sources, [1])
        assert len(filtered) == 1
        source = filtered[0]
        assert source["page"] == "Page 3"
        assert source["page_num"] == 3
        assert len(source["snippet"]) > 0


class TestSnippetGeneration:
    """Tests for generate_snippet()."""

    def test_short_text_preserved(self):
        text = "This is a brief excerpt from the methodology."
        snippet = generate_snippet(text, max_chars=200)
        assert snippet == text

    def test_long_text_truncated_with_ellipsis(self):
        long_text = "Word " * 60
        snippet = generate_snippet(long_text, max_chars=100)
        assert len(snippet) <= 103  # 100 + "..."
        assert snippet.endswith("...")

    def test_whitespace_collapsing(self):
        messy_text = "Line 1\n\n\n   Line 2   with    spaces"
        snippet = generate_snippet(messy_text, max_chars=200)
        assert "\n" not in snippet
        assert "    " not in snippet
