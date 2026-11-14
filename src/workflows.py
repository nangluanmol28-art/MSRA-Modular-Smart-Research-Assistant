"""
MSRA Workflows Module
======================
Deterministic, structured academic research workflows for suggested prompt pills:
1. Summarize Key Methodologies
2. Compare Findings Across Papers
3. Identify Research Gaps & Limitations
4. Core Research Questions

Retrieval uses fixed domain sub-queries (0 LLM calls before generation),
metadata-aware balancing across indexed documents, deduplication, and
standardized [n] citations mapping to the Sources panel.
"""

from typing import Dict, Any, List, Tuple
from src.llm import get_llm, stream_llm
from src.prompts import (
    workflow_methodologies_prompt,
    workflow_compare_prompt,
    workflow_gaps_prompt,
    workflow_core_questions_prompt
)
from src.citations import normalize_citations, filter_sources_by_citations, generate_snippet


WORKFLOW_REGISTRY = {
    "methodologies": {
        "key": "methodologies",
        "label": "Summarize Key Methodologies",
        "min_papers": 1,
        "prompt": workflow_methodologies_prompt,
        "sub_queries": [
            "methodology approach framework architecture system design",
            "data dataset sources corpus empirical samples",
            "model technique algorithm tool instrument used",
            "evaluation experimental setup validation benchmarks metrics"
        ]
    },
    "compare": {
        "key": "compare",
        "label": "Compare Findings Across Papers",
        "min_papers": 2,
        "prompt": workflow_compare_prompt,
        "sub_queries": [
            "findings empirical results discoveries metrics outcomes",
            "conclusion main contributions summary analysis",
            "limitations challenges scope comparison"
        ]
    },
    "gaps": {
        "key": "gaps",
        "label": "Identify Research Gaps & Limitations",
        "min_papers": 1,
        "prompt": workflow_gaps_prompt,
        "sub_queries": [
            "limitations weaknesses constraints acknowledged challenges",
            "future work future research scope open problems further study"
        ]
    },
    "core_questions": {
        "key": "core_questions",
        "label": "Core Research Questions",
        "min_papers": 1,
        "prompt": workflow_core_questions_prompt,
        "sub_queries": [
            "central research question hypothesis aims objectives",
            "introduction purpose scope problem statement conclusion"
        ]
    }
}


def get_workflow_definition(workflow_key: str) -> Dict[str, Any]:
    """Retrieves workflow configuration by key."""
    return WORKFLOW_REGISTRY.get(workflow_key)


def retrieve_workflow_context(
    vectorstore,
    sub_queries: List[str],
    target_k: int = 12
) -> List[Any]:
    """
    Retrieves balanced, deduplicated chunks across uploaded documents for fixed workflow sub-queries.
    Uses zero LLM calls before retrieval.
    """
    if vectorstore is None:
        return []

    candidates_with_scores = []
    seen_keys = set()

    for q in sub_queries:
        try:
            results = vectorstore.similarity_search_with_relevance_scores(q, k=6)
        except Exception:
            results = [(d, 0.5) for d in vectorstore.similarity_search(q, k=6)]

        for doc, score in results:
            src = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page_label", doc.metadata.get("page", "1"))
            chunk_idx = doc.metadata.get("chunk_index", 0)
            dedupe_key = (src, str(page), chunk_idx)

            if dedupe_key not in seen_keys:
                seen_keys.add(dedupe_key)
                candidates_with_scores.append((doc, score))

    if not candidates_with_scores:
        return []

    # Balance chunks across sources
    by_source = {}
    for doc, score in candidates_with_scores:
        src = doc.metadata.get("source", "doc")
        by_source.setdefault(src, []).append((doc, score))

    # Sort candidates per source by score descending
    for src in by_source:
        by_source[src].sort(key=lambda x: x[1], reverse=True)

    selected_docs = []
    while len(selected_docs) < target_k and any(by_source.values()):
        for src in list(by_source.keys()):
            if by_source[src] and len(selected_docs) < target_k:
                doc, _ = by_source[src].pop(0)
                selected_docs.append(doc)

    return selected_docs


def execute_workflow(
    workflow_key: str,
    vectorstore,
    research_focus: str = "",
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True,
    stream: bool = False
):
    """
    Executes a structured research workflow with deterministic retrieval,
    citation normalization, and optional streaming output.
    """
    wf = get_workflow_definition(workflow_key)
    if not wf:
        err_msg = f"Unknown workflow key '{workflow_key}'."
        if stream:
            def err_gen():
                yield err_msg, provider, False
            return err_gen(), [], provider, False
        return err_msg, [], provider, False

    documents = retrieve_workflow_context(vectorstore, wf["sub_queries"], target_k=12)
    if not documents:
        refusal = "I couldn't find sufficient evidence in the uploaded documents to run this workflow."
        if stream:
            def ref_gen():
                yield refusal, provider, False
            return ref_gen(), [], provider, False
        return refusal, [], provider, False

    # Format citations list & context blocks
    citations_list = []
    context_blocks = []

    for idx, doc in enumerate(documents, start=1):
        source_name = doc.metadata.get("source", "Unknown Document")
        page_label = doc.metadata.get("page_label")
        if not page_label and "page" in doc.metadata and doc.metadata["page"] is not None:
            page_label = str(doc.metadata["page"] + 1)

        page_str = f"Page {page_label}" if page_label else "Page N/A"
        page_num = int(page_label) if page_label and page_label.isdigit() else None
        snippet = generate_snippet(doc.page_content, max_chars=200)

        citations_list.append({
            "id": idx,
            "citation_label": f"[{idx}]",
            "source": source_name,
            "page": page_str,
            "page_num": page_num,
            "snippet": snippet,
            "content": doc.page_content.strip()
        })

        p_label = f"p. {page_label}" if page_label else "p. N/A"
        context_blocks.append(
            f"[{idx}] ({source_name}, {p_label}):\n{doc.page_content.strip()}"
        )

    context_text = "\n\n".join(context_blocks)

    focus_line = ""
    if research_focus and research_focus.strip():
        focus_line = f"Active Research Focus: {research_focus.strip()}\n"

    prompt_template = wf["prompt"]
    formatted_prompt = prompt_template.format(
        context=context_text,
        research_focus_line=focus_line
    )

    if stream:
        token_stream = stream_llm(
            formatted_prompt,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        return token_stream, citations_list, provider, False

    raw_answer, provider_used, is_fallback = get_llm(
        formatted_prompt,
        provider=provider,
        model_name=model_name,
        enable_fallback=enable_fallback
    )

    valid_ids = {c["id"] for c in citations_list}
    clean_answer, cited_ids = normalize_citations(raw_answer, valid_ids=valid_ids)
    active_citations = filter_sources_by_citations(citations_list, cited_ids)

    return clean_answer, active_citations, provider_used, is_fallback
