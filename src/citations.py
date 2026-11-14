"""
MSRA Citation Normalization and Filtering Module
================================================
Provides robust post-processing for LLM inline citations:
- Normalizes irregular bracket characters (e.g. 【2】, ［2］, (2)) to standard [2].
- Cleans stray whitespace before punctuation (e.g. "[2] ." -> "[2].").
- Expands comma/semicolon combined citations (e.g. "[1, 2]" -> "[1][2]").
- Removes hallucinated citation IDs that do not exist in retrieved chunks.
- Filters source entries so only actually cited sources appear in the UI.
"""

import re
from typing import List, Dict, Any, Tuple, Set, Optional


def normalize_citations(
    text: str,
    valid_ids: Optional[Set[int]] = None
) -> Tuple[str, List[int]]:
    """
    Normalizes inline citations in text, strips stray whitespace before punctuation,
    removes citations not present in valid_ids, and returns the cleaned text along
    with an ordered, deduplicated list of cited citation IDs.

    Args:
        text: Raw answer string from the LLM.
        valid_ids: Set of valid integer chunk IDs available in the retrieval context.

    Returns:
        Tuple of (cleaned_text, cited_ids_list)
    """
    if not text:
        return "", []

    cleaned = text

    # 1. Normalize full-width and non-standard brackets to standard square brackets
    bracket_replacements = {
        '【': '[', '】': ']',
        '［': '[', '］': ']',
        '〔': '[', '〕': ']',
        '〖': '[', '〗': ']',
        '〚': '[', '〛': ']',
        '「': '[', '」': ']',
    }
    for old_b, new_b in bracket_replacements.items():
        cleaned = cleaned.replace(old_b, new_b)

    # 2. Convert parenthesized citations: e.g. (1) or (1, 2) when appearing as citations
    # Match numbers inside parentheses following word characters or at sentence end
    def replace_parens_citation(match):
        inner = match.group(1).strip()
        # Check if comma/semicolon separated numbers
        parts = [p.strip() for p in re.split(r'[,; ]+', inner) if p.strip()]
        if parts and all(p.isdigit() for p in parts):
            return "".join(f"[{p}]" for p in parts)
        return match.group(0)

    cleaned = re.sub(r'\(([\d\s,;]+)\)', replace_parens_citation, cleaned)

    # 3. Expand multiple comma/semicolon-separated citations inside brackets:
    # e.g., "[1, 2]" -> "[1][2]" or "[1, 3, 5]" -> "[1][3][5]"
    def expand_bracket_citations(match):
        inner = match.group(1).strip()
        parts = [p.strip() for p in re.split(r'[,; ]+', inner) if p.strip()]
        if parts and all(p.isdigit() for p in parts):
            return "".join(f"[{p}]" for p in parts)
        return match.group(0)

    cleaned = re.sub(r'\[([\d\s,;]+)\]', expand_bracket_citations, cleaned)

    # 4. Filter against valid citation IDs (if provided)
    if valid_ids is not None:
        valid_set = set(valid_ids)
        def validate_id(match):
            cid = int(match.group(1))
            if cid in valid_set:
                return f"[{cid}]"
            return ""  # Remove hallucinated citation ID

        cleaned = re.sub(r'\[(\d+)\]', validate_id, cleaned)

    # 5. Fix misplaced citations placed AFTER punctuation:
    # e.g. "claim. [1]" or "claim.[1]" -> "claim [1]."
    cleaned = re.sub(r'([a-zA-Z0-9])\.\s*(\[(\d+)\](?:\[(\d+)\])*)', r'\1 \2.', cleaned)
    cleaned = re.sub(r'([a-zA-Z0-9]),\s*(\[(\d+)\](?:\[(\d+)\])*)', r'\1 \2,', cleaned)

    # 6. Remove stray whitespace between multiple adjacent citations:
    # e.g. "[1] [2]" -> "[1][2]"
    cleaned = re.sub(r'\[(\d+)\]\s+\[(\d+)\]', r'[\1][\2]', cleaned)
    cleaned = re.sub(r'\[(\d+)\]\s+\[(\d+)\]', r'[\1][\2]', cleaned)

    # 7. Remove stray whitespace before punctuation:
    # e.g. "[2] ." -> "[2].", "[1] ," -> "[1],"
    cleaned = re.sub(r'\[(\d+)\]\s+([\.,;!?])', r'[\1]\2', cleaned)
    # Also handle multiple adjacent citations before punctuation: e.g. "[1][2] ." -> "[1][2]."
    cleaned = re.sub(r'(\](?:\[\d+\])*)\s+([\.,;!?])', r'\1\2', cleaned)

    # 8. Collapse duplicate periods created by punctuation cleanup:
    cleaned = re.sub(r'\.\s*\.', '.', cleaned)

    # 9. Clean up any leftover empty brackets
    cleaned = re.sub(r'\[\s*\]', '', cleaned)

    # 10. Normalize multiple consecutive spaces
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

    # 11. Extract all cited IDs in appearance order (deduplicated)
    found_ids_raw = re.findall(r'\[(\d+)\]', cleaned)
    cited_ids = []
    seen = set()
    for raw_id in found_ids_raw:
        cid = int(raw_id)
        if valid_ids is None or cid in valid_ids:
            if cid not in seen:
                seen.add(cid)
                cited_ids.append(cid)

    return cleaned.strip(), cited_ids


def filter_sources_by_citations(
    sources_list: List[Dict[str, Any]],
    cited_ids: List[int]
) -> List[Dict[str, Any]]:
    """
    Filters the retrieved sources to ONLY entries that were actually cited in the answer.
    Preserves natural citation order (or original index order if desired).

    Args:
        sources_list: List of source dictionaries from the retriever.
        cited_ids: List of integer citation IDs found in the answer.

    Returns:
        Filtered list of source dictionaries matching cited_ids.
    """
    if not sources_list or not cited_ids:
        return []

    cited_set = set(cited_ids)
    # Return sources in ascending numerical ID order
    source_by_id = {s["id"]: s for s in sources_list if "id" in s}
    filtered = [source_by_id[cid] for cid in sorted(cited_set) if cid in source_by_id]

    return filtered


def generate_snippet(content: str, max_chars: int = 200, **kwargs) -> str:
    """
    Generates a clean ~200-character snippet of the exact retrieved chunk.

    Args:
        content: The text content of the chunk.
        max_chars: Maximum character length for snippet.

    Returns:
        Truncated snippet string with ellipsis if necessary.
    """
    limit = kwargs.get("max_length", max_chars)
    if not content:
        return ""
    # Flatten multiple whitespace and newlines for clean snippet display
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    # Truncate at last word boundary before limit
    truncated = normalized[:limit]
    last_space = truncated.rfind(" ")
    if last_space > limit * 0.75:
        truncated = truncated[:last_space]
    return truncated + "..."
