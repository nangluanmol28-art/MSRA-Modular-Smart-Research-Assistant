from config import NOT_FOUND_PREFIX
from src.llm import get_llm, stream_llm, LLMQuotaError, LLMAuthError, LLMError
from src.prompts import (
    research_prompt,
    condense_question_prompt,
    broad_query_prompt,
    summary_prompt,
    comparison_prompt,
    gap_detection_prompt,
    literature_review_prompt
)
from src.citations import normalize_citations, filter_sources_by_citations, generate_snippet


def is_broad_question(query: str) -> bool:
    """Detects whether a user query is broad or overview-oriented."""
    q_lower = query.lower().strip()
    broad_indicators = [
        "summarize", "summary", "overview", "main findings", "key findings",
        "explain this paper", "explain the paper", "what does the paper say",
        "what is this paper about", "key concepts", "main points", "conclusions",
        "methodology and findings", "everything about", "tell me about this paper"
    ]
    return any(ind in q_lower for ind in broad_indicators)


def is_summarize_query(query: str) -> bool:
    """Detects if query is an open-ended document summarization request."""
    q_lower = query.lower().strip()
    return any(ind in q_lower for ind in [
        "summarize", "summary", "overview", "what is this paper about",
        "explain this paper", "explain the paper", "tell me about this paper"
    ])


def get_paper_titles(vectorstore) -> list[str]:
    """Extracts uploaded paper titles from the vectorstore metadata."""
    if vectorstore is None:
        return []
    try:
        data = vectorstore.get()
        metadatas = data.get("metadatas", [])
        titles = []
        for m in metadatas:
            src = m.get("source")
            if src:
                clean_name = src.replace(".pdf", "").replace(".PDF", "").strip()
                if clean_name not in titles:
                    titles.append(clean_name)
        return titles
    except Exception:
        return []


def generate_query_variants(
    question: str,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True,
    paper_titles: list[str] = None
) -> list[str]:
    """Generates 2-3 specific sub-queries for broad or overview questions."""
    topic = ", ".join(paper_titles) if paper_titles else question
    prompt = broad_query_prompt.format(question=f"{question} on {topic}")
    try:
        response, _, _ = get_llm(
            prompt,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        variants = [
            line.strip().lstrip("123456789.-*• ")
            for line in response.split("\n")
            if line.strip() and len(line.strip()) > 5
        ]
        if variants:
            return variants[:3]
    except Exception as e:
        print(f"Notice: Query variant generation fallback: {e}")

    return [
        f"{topic} core concepts and background",
        f"{topic} methodology and applications",
        f"{topic} findings, challenges, and conclusions"
    ]


def condense_question(
    question: str,
    chat_history: str,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
) -> str:
    """Rewrites a follow-up question into a standalone academic search query."""
    if not chat_history or not chat_history.strip():
        return question

    formatted_message = condense_question_prompt.format(
        chat_history=chat_history,
        question=question
    )
    try:
        standalone_question, _, _ = get_llm(
            formatted_message,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        clean_q = standalone_question.strip().strip('"\'')
        if clean_q:
            return clean_q
        return question
    except Exception as e:
        print(f"Warning: Failed to condense question ({e}). Falling back to original question.")
        return question


def research(
    question: str,
    retriever,
    chat_history: str = "",
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True,
    stream: bool = False,
    research_focus: str = ""
):
    """
    Executes grounded RAG research with query rewriting, MMR retrieval,
    per-claim citations, and streaming or synchronous generation.
    """
    standalone_q = question
    if chat_history and chat_history.strip():
        standalone_q = condense_question(question, chat_history, provider, model_name, enable_fallback)
        print("STANDALONE QUESTION:", standalone_q)

    # Retrieval Quality: Top-k (k=8) chunks with calibrated relevance threshold & balanced multi-PDF sampling
    RELEVANCE_THRESHOLD = 0.05
    TARGET_K = 8

    vectorstore = getattr(retriever, "vectorstore", None)
    paper_titles = get_paper_titles(vectorstore)
    documents = []

    # Query expansion for broad/overview questions
    queries_to_search = [standalone_q]
    if is_summarize_query(standalone_q):
        if paper_titles:
            queries_to_search = [
                f"{t} abstract introduction overview" for t in paper_titles
            ] + [
                f"{t} methodology applications findings" for t in paper_titles
            ] + [
                f"{t} challenges future scope conclusion" for t in paper_titles
            ]
        else:
            queries_to_search = [
                f"{standalone_q} core concepts and background",
                f"{standalone_q} methodology and findings",
                f"{standalone_q} challenges and conclusion"
            ]
        print(f"Summarization query detected. Searching: {queries_to_search}")
    elif is_broad_question(standalone_q):
        variants = generate_query_variants(standalone_q, provider, model_name, enable_fallback, paper_titles)
        queries_to_search.extend(variants[:2])
        print(f"Broad query detected. Searching {len(queries_to_search)} variants: {queries_to_search}")

    if vectorstore is not None:
        try:
            candidates_with_scores = []
            seen_texts = set()

            for q in queries_to_search:
                # Fetch candidate pool (k=8) to keep search focused and fast
                batch = vectorstore.similarity_search_with_relevance_scores(q, k=8)
                for doc, score in batch:
                    # Deduplicate by content prefix
                    content_key = doc.page_content.strip()[:100]
                    if content_key not in seen_texts:
                        seen_texts.add(content_key)
                        candidates_with_scores.append((doc, score))

            # Filter candidates below relevance score threshold
            relevant_candidates = [
                (doc, score) for doc, score in candidates_with_scores if score >= RELEVANCE_THRESHOLD
            ]

            if not relevant_candidates and candidates_with_scores:
                # All retrieved chunks are below the relevance threshold
                print(f"All retrieved chunks fell below relevance threshold {RELEVANCE_THRESHOLD}.")
                topics_str = ", ".join(paper_titles) if paper_titles else "the uploaded documents"
                refusal_msg = f"{NOT_FOUND_PREFIX} The uploaded documents cover: {topics_str}."
                if stream:
                    def _refusal_gen():
                        yield refusal_msg, provider, False
                    return _refusal_gen(), [], provider, False
                return refusal_msg, [], provider, False

            if relevant_candidates:
                # Sort primarily by relevance score descending
                relevant_candidates.sort(key=lambda x: x[1], reverse=True)

                # Group by document source to prevent one paper from dominating
                papers_map = {}
                for doc, score in relevant_candidates:
                    src = doc.metadata.get("source", "Unknown Document")
                    papers_map.setdefault(src, []).append((doc, score))

                # Round-robin selection across unique papers up to TARGET_K
                while len(documents) < TARGET_K and any(papers_map.values()):
                    for src in list(papers_map.keys()):
                        if papers_map[src] and len(documents) < TARGET_K:
                            doc, score = papers_map[src].pop(0)
                            documents.append(doc)
            else:
                documents = []
        except Exception as e:
            print(f"Score-based retrieval fallback due to: {e}")
            documents = retriever.invoke(standalone_q)[:TARGET_K]
    else:
        documents = retriever.invoke(standalone_q)[:TARGET_K]

    print("RETRIEVED DOCUMENTS:", len(documents))
    if not documents:
        topics_str = ", ".join(paper_titles) if paper_titles else "the uploaded documents"
        refusal_msg = f"{NOT_FOUND_PREFIX} The uploaded documents cover: {topics_str}."
        if stream:
            def _refusal_gen():
                yield refusal_msg, provider, False
            return _refusal_gen(), [], provider, False
        return refusal_msg, [], provider, False

    # Map retrieved chunks to numbered citations [1], [2], ...
    citations_list = []
    context_blocks = []

    for idx, doc in enumerate(documents, start=1):
        source_name = doc.metadata.get("source", "Unknown Document")

        # Handle page metadata (page_label or 0-indexed page)
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

        # Numbered label: [n] (Title, p. X): text
        p_label = f"p. {page_label}" if page_label else "p. N/A"
        context_blocks.append(
            f"[{idx}] ({source_name}, {p_label}):\n{doc.page_content.strip()}"
        )

    context_text = "\n\n".join(context_blocks)

    focus_line = ""
    if research_focus and research_focus.strip():
        focus_line = f"Active Research Focus: {research_focus.strip()}\n"

    formatted_message = research_prompt.format(
        context=context_text,
        question=question,
        research_focus_line=focus_line
    )

    if stream:
        # Return generator for live streaming in Streamlit
        token_stream = stream_llm(
            formatted_message,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        return token_stream, citations_list, provider, False

    try:
        raw_answer, provider_used, is_fallback = get_llm(
            formatted_message,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
    except (LLMQuotaError, LLMAuthError, LLMError) as e:
        return f"⚠️ **Service Notice**: {str(e)}", [], provider, False

    # Check for insufficient evidence response
    lower_ans = raw_answer.lower()
    if (
        "couldn't find this in the uploaded papers" in lower_ans or
        "do not contain sufficient evidence" in lower_ans or
        "does not contain sufficient evidence" in lower_ans or
        ("not mentioned in the provided" in lower_ans and len(raw_answer.split()) < 30)
    ):
        topics_str = ", ".join(paper_titles) if paper_titles else "the uploaded documents"
        ans_text = raw_answer.strip()
        if "cover:" not in ans_text.lower() and paper_titles:
            if not ans_text.endswith("."):
                ans_text += "."
            ans_text = f"{ans_text} The uploaded documents cover: {topics_str}."
        return ans_text, [], provider_used, is_fallback

    # Normalize citation syntax and remove invalid IDs
    valid_ids = {c["id"] for c in citations_list}
    clean_answer, cited_ids = normalize_citations(raw_answer, valid_ids=valid_ids)

    # Filter sources to only those actually cited in the clean answer
    active_citations = filter_sources_by_citations(citations_list, cited_ids)

    return clean_answer, active_citations, provider_used, is_fallback


def generate_paper_summary(
    documents: list,
    target_filename: str = None,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
) -> tuple[str, list, str, bool]:
    if not documents:
        return "⚠️ **No document content provided for summarization.**", [], provider, False

    # Filter documents by target_filename if provided
    if target_filename:
        filtered_docs = [
            doc for doc in documents
            if doc.metadata.get("source") == target_filename
        ]
        if not filtered_docs:
            filtered_docs = documents
    else:
        filtered_docs = documents

    context_blocks = []
    seen_pages = set()
    citations_list = []
    max_context_chars = 14000
    accumulated_chars = 0
    cite_idx = 1

    for doc in filtered_docs:
        source_name = doc.metadata.get("source", target_filename or "Uploaded Paper")
        page_label = doc.metadata.get("page_label")
        if not page_label and "page" in doc.metadata and doc.metadata["page"] is not None:
            page_label = str(doc.metadata["page"] + 1)

        page_str = f"Page {page_label}" if page_label else "Page N/A"
        page_num = int(page_label) if page_label and page_label.isdigit() else None
        snippet = generate_snippet(doc.page_content, max_chars=200)

        key = (source_name, page_str)
        if key not in seen_pages:
            seen_pages.add(key)
            citations_list.append({
                "id": cite_idx,
                "citation_label": f"[{cite_idx}]",
                "source": source_name,
                "page": page_str,
                "page_num": page_num,
                "snippet": snippet
            })

            block = f"[{cite_idx}] Source: {source_name} ({page_str})\n{doc.page_content}"
            if accumulated_chars + len(block) > max_context_chars:
                break

            context_blocks.append(block)
            accumulated_chars += len(block)
            cite_idx += 1

    context_text = "\n\n".join(context_blocks)
    paper_title = target_filename or (filtered_docs[0].metadata.get("source") if filtered_docs else "Research Paper")
    formatted_prompt = summary_prompt.format(
        context=context_text,
        paper_title=paper_title,
        research_focus_line=""
    )

    try:
        summary_result, provider_used, is_fallback = get_llm(
            formatted_prompt,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        valid_ids = {c["id"] for c in citations_list}
        clean_res, cited_ids = normalize_citations(summary_result, valid_ids=valid_ids)
        active_citations = filter_sources_by_citations(citations_list, cited_ids)
        if not active_citations and citations_list:
            active_citations = citations_list
        return clean_res, active_citations, provider_used, is_fallback
    except (LLMQuotaError, LLMAuthError, LLMError) as e:
        return f"⚠️ **Service Notice**: Failed to generate summary — {str(e)}", [], provider, False


def generate_paper_comparison(
    documents: list,
    selected_filenames: list,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
) -> tuple[str, list, str, bool]:
    if not documents or not selected_filenames or len(selected_filenames) < 2:
        return "⚠️ **Please select at least two uploaded research papers to generate a comparison matrix.**", [], provider, False

    # Filter documents by selected_filenames
    filtered_docs = [
        doc for doc in documents
        if doc.metadata.get("source") in selected_filenames
    ]
    if not filtered_docs:
        return "⚠️ **No document content found for selected papers.**", [], provider, False

    context_blocks = []
    seen_pages = set()
    citations_list = []
    max_context_chars = 16000
    accumulated_chars = 0
    cite_idx = 1

    # Group docs by paper source for balanced allocation
    paper_docs_map = {}
    for doc in filtered_docs:
        src = doc.metadata.get("source", "Uploaded Paper")
        paper_docs_map.setdefault(src, []).append(doc)

    for src, doc_list in paper_docs_map.items():
        for doc in doc_list:
            page_label = doc.metadata.get("page_label")
            if not page_label and "page" in doc.metadata and doc.metadata["page"] is not None:
                page_label = str(doc.metadata["page"] + 1)

            page_str = f"Page {page_label}" if page_label else "Page N/A"
            page_num = int(page_label) if page_label and page_label.isdigit() else None
            snippet = generate_snippet(doc.page_content, max_chars=200)

            key = (src, page_str)
            if key not in seen_pages:
                seen_pages.add(key)
                citations_list.append({
                    "id": cite_idx,
                    "citation_label": f"[{cite_idx}]",
                    "source": src,
                    "page": page_str,
                    "page_num": page_num,
                    "snippet": snippet
                })

                block = f"[{cite_idx}] Paper: {src} ({page_str})\n{doc.page_content}"
                if accumulated_chars + len(block) > max_context_chars:
                    break

                context_blocks.append(block)
                accumulated_chars += len(block)
                cite_idx += 1

    context_text = "\n\n".join(context_blocks)
    paper_list_str = ", ".join(selected_filenames)

    formatted_prompt = comparison_prompt.format(
        context=context_text,
        paper_list=paper_list_str,
        research_focus_line=""
    )

    try:
        comparison_result, provider_used, is_fallback = get_llm(
            formatted_prompt,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        valid_ids = {c["id"] for c in citations_list}
        clean_res, cited_ids = normalize_citations(comparison_result, valid_ids=valid_ids)
        active_citations = filter_sources_by_citations(citations_list, cited_ids)
        if not active_citations and citations_list:
            active_citations = citations_list
        return clean_res, active_citations, provider_used, is_fallback
    except (LLMQuotaError, LLMAuthError, LLMError) as e:
        return f"⚠️ **Service Notice**: Failed to generate comparison — {str(e)}", [], provider, False


def detect_research_gaps(
    documents: list,
    selected_filenames: list = None,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
) -> tuple[str, list, str, bool]:
    if not documents:
        return "⚠️ **No document content provided for research gap analysis.**", [], provider, False

    if selected_filenames:
        filtered_docs = [
            doc for doc in documents
            if doc.metadata.get("source") in selected_filenames
        ]
        if not filtered_docs:
            filtered_docs = documents
    else:
        filtered_docs = documents

    context_blocks = []
    seen_pages = set()
    citations_list = []
    max_context_chars = 16000
    accumulated_chars = 0
    cite_idx = 1

    paper_docs_map = {}
    for doc in filtered_docs:
        src = doc.metadata.get("source", "Uploaded Paper")
        paper_docs_map.setdefault(src, []).append(doc)

    for src, doc_list in paper_docs_map.items():
        for doc in doc_list:
            page_label = doc.metadata.get("page_label")
            if not page_label and "page" in doc.metadata and doc.metadata["page"] is not None:
                page_label = str(doc.metadata["page"] + 1)

            page_str = f"Page {page_label}" if page_label else "Page N/A"
            page_num = int(page_label) if page_label and page_label.isdigit() else None
            snippet = generate_snippet(doc.page_content, max_chars=200)

            key = (src, page_str)
            if key not in seen_pages:
                seen_pages.add(key)
                citations_list.append({
                    "id": cite_idx,
                    "citation_label": f"[{cite_idx}]",
                    "source": src,
                    "page": page_str,
                    "page_num": page_num,
                    "snippet": snippet
                })

                block = f"[{cite_idx}] Paper: {src} ({page_str})\n{doc.page_content}"
                if accumulated_chars + len(block) > max_context_chars:
                    break

                context_blocks.append(block)
                accumulated_chars += len(block)
                cite_idx += 1

    context_text = "\n\n".join(context_blocks)
    paper_list_str = ", ".join(list(paper_docs_map.keys()))

    formatted_prompt = gap_detection_prompt.format(
        context=context_text,
        paper_list=paper_list_str,
        research_focus_line=""
    )

    try:
        gap_result, provider_used, is_fallback = get_llm(
            formatted_prompt,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        valid_ids = {c["id"] for c in citations_list}
        clean_res, cited_ids = normalize_citations(gap_result, valid_ids=valid_ids)
        active_citations = filter_sources_by_citations(citations_list, cited_ids)
        if not active_citations and citations_list:
            active_citations = citations_list
        return clean_res, active_citations, provider_used, is_fallback
    except (LLMQuotaError, LLMAuthError, LLMError) as e:
        return f"⚠️ **Service Notice**: Failed to detect research gaps — {str(e)}", [], provider, False


def generate_literature_review(
    documents: list,
    topic: str = "General Academic Synthesis",
    selected_filenames: list = None,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
) -> tuple[str, list, str, bool]:
    if not documents:
        return "⚠️ **No document content provided for literature review.**", [], provider, False

    if selected_filenames:
        filtered_docs = [
            doc for doc in documents
            if doc.metadata.get("source") in selected_filenames
        ]
        if not filtered_docs:
            filtered_docs = documents
    else:
        filtered_docs = documents

    context_blocks = []
    seen_pages = set()
    citations_list = []
    max_context_chars = 16000
    accumulated_chars = 0
    cite_idx = 1

    paper_docs_map = {}
    for doc in filtered_docs:
        src = doc.metadata.get("source", "Uploaded Paper")
        paper_docs_map.setdefault(src, []).append(doc)

    for src, doc_list in paper_docs_map.items():
        for doc in doc_list:
            page_label = doc.metadata.get("page_label")
            if not page_label and "page" in doc.metadata and doc.metadata["page"] is not None:
                page_label = str(doc.metadata["page"] + 1)

            page_str = f"Page {page_label}" if page_label else "Page N/A"
            page_num = int(page_label) if page_label and page_label.isdigit() else None
            snippet = generate_snippet(doc.page_content, max_chars=200)

            key = (src, page_str)
            if key not in seen_pages:
                seen_pages.add(key)
                citations_list.append({
                    "id": cite_idx,
                    "citation_label": f"[{cite_idx}]",
                    "source": src,
                    "page": page_str,
                    "page_num": page_num,
                    "snippet": snippet
                })

                block = f"[{cite_idx}] Paper: {src} ({page_str})\n{doc.page_content}"
                if accumulated_chars + len(block) > max_context_chars:
                    break

                context_blocks.append(block)
                accumulated_chars += len(block)
                cite_idx += 1

    context_text = "\n\n".join(context_blocks)
    paper_list_str = ", ".join(list(paper_docs_map.keys()))

    formatted_prompt = literature_review_prompt.format(
        topic=topic or "General Academic Synthesis",
        context=context_text,
        paper_list=paper_list_str,
        research_focus_line=""
    )

    try:
        review_result, provider_used, is_fallback = get_llm(
            formatted_prompt,
            provider=provider,
            model_name=model_name,
            enable_fallback=enable_fallback
        )
        valid_ids = {c["id"] for c in citations_list}
        clean_res, cited_ids = normalize_citations(review_result, valid_ids=valid_ids)
        active_citations = filter_sources_by_citations(citations_list, cited_ids)
        if not active_citations and citations_list:
            active_citations = citations_list
        return clean_res, active_citations, provider_used, is_fallback
    except (LLMQuotaError, LLMAuthError, LLMError) as e:
        return f"⚠️ **Service Notice**: Failed to generate literature review — {str(e)}", [], provider, False
