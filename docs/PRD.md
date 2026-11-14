# MSRA — Modular Smart Research Assistant
## Product Requirements Document (PRD) & Architecture Handoff

---

### 1. Executive Summary
- **Product Name**: MSRA — Modular Smart Research Assistant.
- **Product Positioning**: A specialized research copilot for students, scholars, and researchers that goes beyond basic "chat with PDF" tools.
- **Core Workflow**: Research Question → Source Documents → Multi-Vector Retrieval → Grounded LLM Reasoning → Cited Synthesis → Downloadable Report.
- **Primary Source**: Research papers / PDF documents. Multi-document corpus support with per-page metadata tracking.
- **Differentiators**: Multi-paper comparative matrices, structured paper summaries, literature reviews, research gap detection, verified inline citations, and academic report exports (PDF & DOCX).

---

### 2. Product Vision
MSRA empowers researchers to transition seamlessly from *"I have a pile of papers"* to *"I understand the evidence, can compare methodology across papers, identify unexplored research gaps, and export a cited academic dossier."*

**Key Questions MSRA Resolves:**
1. What are the key findings, methodologies, datasets, and limitations of this paper?
2. How do these multiple papers compare across structured dimensions?
3. What themes, consensus, or contradictions emerge across the corpus?
4. What unexplored research gaps and limitations can be inferred from the evidence?
5. Where exactly in the source literature does each claim originate?
6. Can the entire synthesis be exported into a publication-ready PDF/DOCX report?

---

### 3. Technology Stack

| Layer | Component | Technology / Library |
|---|---|---|
| **Frontend UI** | Web Interface & Workspace | Streamlit (`>=1.35.0`) + Custom 3D Particle Canvas |
| **Language** | Runtime Environment | Python (`3.11` / `3.12`) |
| **RAG Orchestration** | Document Flow & Prompting | LangChain (`>=0.2.0`) |
| **PDF Ingestion** | Text Extraction & Metadata | PyPDF / LangChain PyPDFLoader |
| **Text Chunking** | Chunk Partitioning | `RecursiveCharacterTextSplitter` (chunk_size: 1000, overlap: 200) |
| **Embeddings** | Dense Vector Representation | HuggingFace `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector Database** | Vector Store & Similarity Index | ChromaDB (`>=0.5.0`) with per-session collection isolation |
| **Primary LLMs** | Cloud Inference & Quota Fallback | Google Gemini API (`gemini-2.5-flash`) & Groq API (`llama-3.3-70b-versatile`) |
| **Document Export** | Publication Reports | ReportLab (PDF) & python-docx (DOCX) |
| **Test Framework** | Automated & Stress Testing | pytest (`>=8.0.0`) + DOOM Resilience Suite |

---

### 4. Core Features & Capabilities

#### P0 — Verified Citation Engine
- Document metadata (`source`, `page`, `page_label`) is strictly preserved across all ingestion, indexing, and retrieval stages.
- LLM outputs are strictly instructed to ground every claim with inline bracket markers `[1]`, `[2]`.
- Post-processing pipeline parses, normalizes, and validates all citation references against actual retrieved chunks.
- Interactive **Sources** expander renders verified excerpts, page references, and similarity snippets.

#### P1 — Structured Paper Summarization
- Generates 9-part structured academic summaries:
  1. Paper Title & Overview
  2. Research Objective & Core Motivation
  3. Methodology & System Architecture
  4. Datasets, Benchmarks & Baselines
  5. Key Findings & Empirical Results
  6. Theoretical & Practical Contributions
  7. Limitations & Threats to Validity
  8. Future Research Directions
  9. Critical Takeaway & Synthesis

#### P1 — Multi-Paper Comparative Analysis
- Dynamic paper selection (minimum 2 papers).
- 9-dimension comparative analysis:
  1. Research Objectives & Problem Formulations
  2. Theoretical Foundations & Assumptions
  3. Methodological Architectures
  4. Datasets, Benchmarks & Experimental Scope
  5. Quantitative Performance Metrics
  6. Computational Complexity
  7. Key Insights & Novel Discoveries
  8. Documented Limitations & Constraints
  9. Practical Applicability & Deployment Viability
- Formatted Markdown comparative synthesis matrix.

#### P2 — Research Gap & Limitation Detection
- Analyzes author-stated constraints vs. cross-paper inferred gaps across 6 dimensions:
  1. Methodological & Architectural Limitations
  2. Dataset, Benchmark & Evaluation Scope Limitations
  3. Scalability, Latency & Resource Constraints
  4. Unresolved Questions & Conflicting Results
  5. Under-Explored Domains & Novel Synthesis Opportunities
  6. Prioritized Future Research Agenda

#### P2 — Publication-Ready Report Export
- Instant 1-click export of any response or synthesis into:
  - **Academic PDF**: Styled with ReportLab (header, metadata block, executive summary, tables, bibliography).
  - **Word DOCX**: Formatted with python-docx (native Word styles, callouts, tables, references).

---

### 5. Architectural Principles & Safety
- **Strict Grounding**: Never fabricate citations or hallucinate claims. If retrieved context is insufficient, explicitly state: *"I couldn't find this in the uploaded papers."*
- **Provider Redundancy**: Automatic zero-downtime failover from Gemini to Groq (or vice-versa) when quota or rate limits are reached.
- **Session Isolation**: Each user session receives a unique UUID directory under `data/sessions/<uuid>/` containing its own vectorstore and uploads, completely isolated from other users.
- **Security**: API keys are loaded via environment variables (`.env`) or Streamlit secrets; keys are never logged or exposed.
