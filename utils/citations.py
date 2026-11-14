"""
Citation Utility Module Re-export
=================================
Exposes citation normalization and source filtering utilities for MSRA.
"""

from src.citations import (
    normalize_citations,
    filter_sources_by_citations,
    generate_snippet
)

__all__ = [
    "normalize_citations",
    "filter_sources_by_citations",
    "generate_snippet"
]
