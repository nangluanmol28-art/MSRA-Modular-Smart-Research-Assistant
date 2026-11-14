import os
import io
import pypdf
import pytest
from unittest.mock import patch

from src.pdf_rag import (
    load_pdf,
    split_documents,
    get_or_create_vectorstore,
    add_chunks_to_vectorstore,
    get_retriever,
    delete_paper_from_vectorstore
)
from src.chain import (
    research,
    generate_paper_summary,
    generate_paper_comparison,
    detect_research_gaps
)
from src.export import export_to_pdf
from utils.session import clear_session_data


class TestFullSystemLifecycle:
    """End-to-end integration test verifying the 10-step full research workflow."""

    @pytest.fixture
    def test_session_id(self):
        sid = "lifecycle_test_session_99"
        yield sid
        clear_session_data(sid)

    def test_complete_10_step_research_lifecycle(self, test_session_id):
        # -------------------------------------------------------------
        # STEP 1: Upload and index multiple real PDFs
        # -------------------------------------------------------------
        p1_path = os.path.join("data", "uploads", "Effective_Study_Techniques.pdf")
        p2_path = os.path.join("data", "uploads", "Renewable_Energy_Overview.pdf")
        assert os.path.exists(p1_path)
        assert os.path.exists(p2_path)

        docs_p1 = load_pdf(p1_path, file_hash="hash_p1")
        docs_p2 = load_pdf(p2_path, file_hash="hash_p2")
        assert len(docs_p1) > 0
        assert len(docs_p2) > 0

        chunks_p1 = split_documents(docs_p1, file_hash="hash_p1")
        chunks_p2 = split_documents(docs_p2, file_hash="hash_p2")
        assert len(chunks_p1) > 0
        assert len(chunks_p2) > 0

        vectorstore = get_or_create_vectorstore(session_id=test_session_id)
        add_chunks_to_vectorstore(vectorstore, chunks_p1, batch_size=32)
        add_chunks_to_vectorstore(vectorstore, chunks_p2, batch_size=32)

        retriever = get_retriever(vectorstore)
        assert retriever is not None

        all_docs = docs_p1 + docs_p2

        # -------------------------------------------------------------
        # STEP 2: Ask a Question in Research Chat
        # -------------------------------------------------------------
        with patch("src.chain.get_llm") as mock_get_llm:
            mock_get_llm.return_value = (
                "Spaced repetition improves memory retention significantly over massed practice [1].",
                "Google Gemini",
                False
            )
            clean_answer, citations, provider_used, is_fallback = research(
                "How does spaced repetition impact learning?",
                retriever,
                provider="Google Gemini",
                stream=False
            )
            assert "Spaced repetition" in clean_answer
            assert len(citations) > 0
            assert citations[0]["citation_label"] == "[1]"
            chat_citations = citations

        # -------------------------------------------------------------
        # STEP 3 & 4: Research Paper Summarization (9 Sections)
        # -------------------------------------------------------------
        with patch("src.chain.get_llm") as mock_sum_llm:
            mock_sum_llm.return_value = (
                "### 1. Paper Overview\nFocuses on cognitive learning methods [1].\n\n"
                "### 2. Research Problem\nRetention loss during cramming [1].\n\n"
                "### 3. Objectives\nEvaluate active recall [1].\n\n"
                "### 4. Proposed Methodology\nLongitudinal testing schedules [1].\n\n"
                "### 5. Dataset & Technologies\nStudent exam cohorts [1].\n\n"
                "### 6. Key Findings & Results\n35% retention improvement [1].\n\n"
                "### 7. Conclusion\nSpaced recall is effective [1].\n\n"
                "### 8. Limitations\nRequires self-discipline [1].\n\n"
                "### 9. Future Scope\nAI-driven scheduling algorithms [1].",
                "Google Gemini",
                False
            )
            summary_res, sum_cites, sum_prov, sum_fb = generate_paper_summary(
                all_docs,
                target_filename="Effective_Study_Techniques.pdf",
                provider="Google Gemini"
            )
            assert "Paper Overview" in summary_res
            assert "Key Findings & Results" in summary_res
            assert "Limitations" in summary_res
            assert len(sum_cites) > 0

        # -------------------------------------------------------------
        # STEP 5 & 6: Multi-Paper Comparison (9 Dimensions)
        # -------------------------------------------------------------
        with patch("src.chain.get_llm") as mock_comp_llm:
            mock_comp_llm.return_value = (
                "### 1. Comparative Analysis Matrix\n"
                "| Dimension | Effective Study | Renewable Energy |\n"
                "|---|---|---|\n"
                "| **1. Research Problem** | Learning retention [1] | Carbon emissions [2] |\n"
                "| **2. Objectives** | Memory recall [1] | Clean power [2] |\n"
                "| **3. Methodology** | Spaced practice [1] | Solar conversion [2] |\n"
                "| **4. Algorithms / Techniques** | Leitner system [1] | Photovoltaic cells [2] |\n"
                "| **5. Dataset** | Academic trials [1] | Grid measurements [2] |\n"
                "| **6. Results** | +35% retention [1] | +22% efficiency [2] |\n"
                "| **7. Strengths** | Highly replicable [1] | Scalable [2] |\n"
                "| **8. Limitations** | Behavioral adherence [1] | Intermittent generation [2] |\n"
                "| **9. Contributions** | Memory optimization [1] | Decarbonization [2] |\n\n"
                "### 2. Key Similarities\n- Both target efficiency optimizations [1][2].\n\n"
                "### 3. Key Differences\n- Domain disparity: Cognitive psychology vs Energy systems [1][2].\n\n"
                "### 4. Comparative Synthesis & Research Takeaways\n- Distinct domains demonstrating empirical methods.",
                "Groq",
                False
            )
            comp_res, comp_cites, comp_prov, comp_fb = generate_paper_comparison(
                all_docs,
                selected_filenames=["Effective_Study_Techniques.pdf", "Renewable_Energy_Overview.pdf"],
                provider="Groq"
            )
            assert "Comparative Analysis Matrix" in comp_res
            assert "Key Similarities" in comp_res
            assert "Key Differences" in comp_res
            assert len(comp_cites) >= 2

        # -------------------------------------------------------------
        # STEP 7 & 8: Research Gap Detection (6 Categories)
        # -------------------------------------------------------------
        with patch("src.chain.get_llm") as mock_gap_llm:
            mock_gap_llm.return_value = (
                "### 1. Identified Research Gaps\nAbsence of long-term retention trials [1].\n\n"
                "### 2. Existing Limitations (Author-Stated)\nCohort size was limited [1].\n\n"
                "### 3. Unexplored Areas & Open Questions\nApplication to neurodivergent populations [1].\n\n"
                "### 4. Methodological Gaps\nReliance on self-reported compliance [1].\n\n"
                "### 5. Potential Research Opportunities (Inferred)\nAutomated flashcard generation with LLMs [1].\n\n"
                "### 6. Suggested Future Directions\nClinical neural imaging studies during recall [1].",
                "Google Gemini",
                False
            )
            gap_res, gap_cites, gap_prov, gap_fb = detect_research_gaps(
                all_docs,
                selected_filenames=["Effective_Study_Techniques.pdf", "Renewable_Energy_Overview.pdf"],
                provider="Google Gemini"
            )
            assert "Identified Research Gaps" in gap_res
            assert "Existing Limitations (Author-Stated)" in gap_res
            assert "Potential Research Opportunities (Inferred)" in gap_res
            assert len(gap_cites) > 0

        # -------------------------------------------------------------
        # STEP 9: PDF Export Verification on all 4 Outputs
        # -------------------------------------------------------------
        outputs = [
            ("Chat Answer Report", clean_answer, chat_citations),
            ("Paper Summary Report", summary_res, sum_cites),
            ("Multi-Paper Comparison Report", comp_res, comp_cites),
            ("Research Gap Analysis Report", gap_res, gap_cites)
        ]

        for title, content, cites in outputs:
            pdf_bytes = export_to_pdf(
                title=title,
                content=content,
                topic="Comprehensive Research Validation",
                citations=cites,
                provider_info="MSRA Verification Suite"
            )
            assert isinstance(pdf_bytes, bytes)
            assert len(pdf_bytes) > 1000
            assert pdf_bytes.startswith(b"%PDF-")

            # Verify with pypdf parser that PDF is structurally sound
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            assert len(reader.pages) >= 1
            extracted_text = "".join(p.extract_text() or "" for p in reader.pages)
            assert "MSRA" in extracted_text
            assert title in extracted_text

        # -------------------------------------------------------------
        # STEP 10: Paper Removal and Vectorstore Isolation
        # -------------------------------------------------------------
        delete_paper_from_vectorstore(
            vectorstore,
            filename="Renewable_Energy_Overview.pdf",
            file_hash="hash_p2"
        )
        # Vectorstore should still be operational for Paper 1
        remaining_retriever = get_retriever(vectorstore)
        assert remaining_retriever is not None
